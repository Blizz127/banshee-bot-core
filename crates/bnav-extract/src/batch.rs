//! Bounded, opt-in reuse of decoded geometry. The batch stream is private IPC;
//! saved tiles remain ordinary raw Detour payloads, not a new navmesh format.
use super::{read, TileGrid, MAX_INPUT_BYTES};
use bnav_extract::{inspect_detour, read_obj, Error, TriangleMesh};
use std::fs::{self, OpenOptions};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

const MAX_CELLS: usize = 16;
const MAX_BATCH_BYTES: usize = 128 * 1024 * 1024;
const HEADER_MAGIC: u32 = 0x5442_4e42;
const FOOTER_MAGIC: u32 = 0x444e_4542;

#[derive(Clone, Copy)]
enum State {
    Missing,
    Empty,
    Built(usize),
}

fn io_error(context: &str, error: std::io::Error) -> Error {
    Error(format!("{context}: {error}"))
}

fn new_file(path: &Path, data: &[u8]) -> Result<(), Error> {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| io_error("cannot create new batch output", e))?;
    file.write_all(data)
        .and_then(|_| file.sync_all())
        .map_err(|e| io_error("batch write failed; partial output retained", e))
}

fn destination(output: &str) -> Result<PathBuf, Error> {
    let path = Path::new(output);
    let name = path
        .file_name()
        .ok_or_else(|| Error("batch output must name a new directory".into()))?;
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."))
        .canonicalize()
        .map_err(|e| io_error("batch output parent must exist", e))?;
    if parent.ancestors().any(|p| p.join(".git").exists()) {
        return Err(Error(
            "batch outputs must remain outside Git repositories".into(),
        ));
    }
    let path = parent.join(name);
    if fs::symlink_metadata(&path).is_ok() {
        return Err(Error(
            "batch output already exists; choose a new directory".into(),
        ));
    }
    Ok(path)
}

fn index(value: &str) -> Result<i32, Error> {
    if value.is_empty() || !value.bytes().all(|b| b.is_ascii_digit()) {
        return Err(Error(
            "batch indices must be unsigned decimal integers".into(),
        ));
    }
    value
        .parse::<i32>()
        .ok()
        .filter(|v| (0..=4095).contains(v))
        .ok_or_else(|| Error("batch indices must be in 0..4095".into()))
}

fn words(input: &mut impl Read) -> Result<[u32; 4], Error> {
    let mut bytes = [0; 16];
    input
        .read_exact(&mut bytes)
        .map_err(|e| io_error("truncated batch stream", e))?;
    Ok(std::array::from_fn(|i| {
        u32::from_le_bytes(bytes[i * 4..i * 4 + 4].try_into().unwrap())
    }))
}

fn receive(
    input: &mut impl Read,
    cells: &[TileGrid],
    output: &Path,
) -> Result<(u32, Vec<State>), Error> {
    let [magic, version, bits, count] = words(input)?;
    if magic != HEADER_MAGIC
        || version != 1
        || !matches!(bits, 32 | 64)
        || count as usize != cells.len()
    {
        return Err(Error(
            "unsupported batch header or requested cell count mismatch".into(),
        ));
    }
    let mut states = Vec::with_capacity(cells.len());
    let mut total = 0usize;
    let mut built = 0u32;
    let mut empty = 0u32;
    for cell in cells {
        let [x, z, status, length] = words(input)?;
        if x != cell.x as u32 || z != cell.z as u32 {
            return Err(Error(
                "batch cell order or coordinates differ from request".into(),
            ));
        }
        let path = output.join(format!("{x}_{z}.navtile"));
        match (status, length) {
            (3, 0) => {
                if fs::symlink_metadata(&path).is_ok() {
                    return Err(Error(
                        "empty batch cell unexpectedly has an output file".into(),
                    ));
                }
                states.push(State::Empty);
                empty += 1;
            }
            (0, length) if (100..=MAX_INPUT_BYTES).contains(&u64::from(length)) => {
                total += length as usize;
                if total > MAX_BATCH_BYTES {
                    return Err(Error("batch exceeds 128 MiB payload budget".into()));
                }
                let mut payload = vec![0; length as usize];
                input
                    .read_exact(&mut payload)
                    .map_err(|e| io_error("truncated batch tile", e))?;
                let tile = inspect_detour(&payload, bits)?;
                if tile.coordinates != [cell.x, cell.z, 0] {
                    return Err(Error(
                        "batch payload coordinates differ from requested cell".into(),
                    ));
                }
                new_file(&path, &payload)?;
                states.push(State::Built(payload.len()));
                built += 1;
            }
            _ => return Err(Error("invalid batch cell status or payload length".into())),
        }
    }
    if words(input)? != [FOOTER_MAGIC, count, built, empty] {
        return Err(Error(
            "batch completion footer does not match received cells".into(),
        ));
    }
    let mut trailing = [0];
    if input
        .read(&mut trailing)
        .map_err(|e| io_error("batch stream end check failed", e))?
        != 0
    {
        return Err(Error("trailing bytes after batch completion footer".into()));
    }
    Ok((bits, states))
}

fn send_geometry(stdin: impl Write, mesh: &TriangleMesh) -> std::io::Result<()> {
    let mut input = BufWriter::new(stdin);
    writeln!(
        input,
        "BNAV_TRIANGLES_V1 {} {}",
        mesh.vertices.len(),
        mesh.triangles.len()
    )?;
    for v in &mesh.vertices {
        writeln!(input, "{} {} {}", v[0], v[1], v[2])?;
    }
    for t in &mesh.triangles {
        writeln!(input, "{} {} {}", t[0], t[1], t[2])?;
    }
    input.flush()
}

fn manifest(
    cells: &[TileGrid],
    states: &[State],
    bits: Option<u32>,
    grid: &[f32],
    settings: &[f32],
    mesh: &TriangleMesh,
) -> String {
    let tiles = cells
        .iter()
        .zip(states)
        .map(|(cell, state)| {
            let detail = match state {
                State::Missing => "\"status\":\"missing\"".into(),
                State::Empty => "\"status\":\"empty\"".into(),
                State::Built(bytes) => format!(
                    "\"status\":\"built\",\"path\":\"{}_{}.navtile\",\"bytes\":{bytes}",
                    cell.x, cell.z
                ),
            };
            format!("{{\"x\":{},\"z\":{},{detail}}}", cell.x, cell.z)
        })
        .collect::<Vec<_>>()
        .join(",");
    let built = states
        .iter()
        .filter(|s| matches!(s, State::Built(_)))
        .count();
    let empty = states.iter().filter(|s| matches!(s, State::Empty)).count();
    let status = if bits.is_some() {
        "COMPLETE"
    } else {
        "INCOMPLETE"
    };
    let bits = bits.map_or_else(|| "null".into(), |v| v.to_string());
    format!(
        "{{\"format\":\"bnav-tile-batch-v1\",\"status\":\"{status}\",\"reference_bits\":{bits},\"requested_cells\":{},\"built\":{built},\"empty\":{empty},\"origin\":[{},{}],\"vertical_bounds\":[{},{}],\"tile_cells\":{},\"settings\":{settings:?},\"geometry_vertices\":{},\"geometry_triangles\":{},\"tiles\":[{tiles}],\"game_qa\":\"NOT_RUN\",\"coverage_meaning\":\"requested cells evaluated only; no source identity, whole-zone or gameplay proof\"}}\n",
        cells.len(), grid[0], grid[1], grid[2], grid[3], grid[4], mesh.vertices.len(), mesh.triangles.len()
    )
}

pub fn build(
    backend: &str,
    input: &str,
    output: &str,
    grid: &[&str; 9],
    config: &[&str],
) -> Result<i32, Error> {
    let defaults = ["0.3", "0.2", "2.0", "0.6", "0.9", "45"];
    let settings = match config.len() {
        0 => &defaults[..],
        6 => config,
        _ => {
            return Err(Error(
                "provide all six build settings, or omit them for defaults".into(),
            ))
        }
    };
    let [xmin, xmax, zmin, zmax] = [
        index(grid[5])?,
        index(grid[6])?,
        index(grid[7])?,
        index(grid[8])?,
    ];
    if xmin > xmax || zmin > zmax || (xmax - xmin + 1) * (zmax - zmin + 1) > MAX_CELLS as i32 {
        return Err(Error(
            "batch rectangle must contain 1..16 cells without inverted ranges".into(),
        ));
    }
    let mut cells = Vec::new();
    for x in xmin..=xmax {
        for z in zmin..=zmax {
            cells.push(TileGrid::parse(
                &[
                    grid[0],
                    grid[1],
                    grid[2],
                    grid[3],
                    grid[4],
                    &x.to_string(),
                    &z.to_string(),
                ],
                settings,
            )?);
        }
    }
    // TileGrid has already checked these values for finite, valid configuration.
    let numbers = |values: &[&str]| -> Result<Vec<f32>, Error> {
        values
            .iter()
            .map(|v| {
                v.parse::<f32>()
                    .map_err(|_| Error("invalid batch setting".into()))
            })
            .collect()
    };
    let grid_numbers = numbers(&grid[..5])?;
    let setting_numbers = numbers(settings)?;
    let output = destination(output)?;
    let bytes = read(input)?;
    let text = std::str::from_utf8(&bytes).map_err(|e| Error(format!("OBJ is not UTF-8: {e}")))?;
    let mesh = read_obj(text)?;
    if mesh.vertices.len() > 1_000_000 || mesh.triangles.len() > 1_000_000 {
        return Err(Error(
            "batch supports at most one million vertices and triangles".into(),
        ));
    }
    fs::create_dir(&output).map_err(|e| io_error("cannot create new batch directory", e))?;
    let requested = manifest(
        &cells,
        &vec![State::Missing; cells.len()],
        None,
        &grid_numbers,
        &setting_numbers,
        &mesh,
    );
    new_file(&output.join("requested.json"), requested.as_bytes())?;
    let mut command = Command::new(backend);
    command.arg("build-tiles").args(settings).args(&grid[..5]);
    for cell in &cells {
        command.arg(cell.x.to_string()).arg(cell.z.to_string());
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| io_error("cannot start explicit batch backend", e))?;
    let transfer = send_geometry(child.stdin.take().expect("piped stdin"), &mesh);
    let result = match transfer {
        Ok(()) => receive(
            &mut child.stdout.take().expect("piped stdout"),
            &cells,
            &output,
        ),
        Err(e) => Err(io_error("batch geometry transfer failed", e)),
    };
    if result.is_err() {
        // Stop/reap only our spawned helper after malformed output or broken IPC.
        // All partial files and requested.json remain; no completed manifest.
        let _ = child.kill();
    }
    let status = child
        .wait()
        .map_err(|e| io_error("batch backend wait failed", e))?;
    let (bits, states) = result?;
    if !status.success() {
        return Err(Error(format!(
            "batch backend failed after stream readback: {status}"
        )));
    }
    let complete = manifest(
        &cells,
        &states,
        Some(bits),
        &grid_numbers,
        &setting_numbers,
        &mesh,
    );
    new_file(&output.join("manifest.json"), complete.as_bytes())?;
    print!("{complete}");
    Ok(0)
}
