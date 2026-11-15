use bnav_extract::{
    inspect_detour, inspect_mmap, inspect_mmap_profile, inspect_mmtile, read_obj, Error, Profile,
};
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Read, Write};
use std::process::{Command, Stdio};

const MAX_INPUT_BYTES: u64 = 64 * 1024 * 1024;
const HELP: &str = "bnav-extract 0.1.0 — offline navigation builder and preflight
Usage:
  bnav-extract inspect-mmap PATH
  bnav-extract inspect-mmap <cmangos-v8|cmangos-v8-ref64|acore-v20> PATH
  bnav-extract inspect-mmtile <cmangos-v8|cmangos-v8-ref64|acore-v20> PATH
  bnav-extract inspect-detour <32|64> PATH
  bnav-extract check-obj PATH
  bnav-extract build-obj BACKEND INPUT OUTPUT [CELL_SIZE CELL_HEIGHT HEIGHT RADIUS CLIMB SLOPE]
  bnav-extract build-tile-obj BACKEND INPUT OUTPUT ORIGIN_X ORIGIN_Z MIN_Y MAX_Y TILE_CELLS TILE_X TILE_Z [CELL_SIZE CELL_HEIGHT HEIGHT RADIUS CLIMB SLOPE]

Inspection is read-only; little-endian profiles only. Maximum input: 64 MiB.
Tile inspection checks headers and section lengths, not connectivity or walkability.
cmangos-v8 keeps its 32-bit ABI; cmangos-v8-ref64 explicitly selects the 64-bit ABI.
Only profiled cmangos-v8-ref64 map inspection permits the fixed 31-bit capacity field.
check-obj accepts triangulated geometry without transforms; it does not build navmesh.
build-obj writes a new raw Detour v7 tile via an explicit external Recast backend.
Input must be Y-up; all agent dimensions use the geometry's world units.
Default settings: 0.3 0.2 2.0 0.6 0.9 45. Outputs are never overwritten.
Build the backend with scripts/build_bnav_backend.py; see docs/BNAV_EXTRACT.md.
build-tile-obj uses a fixed grid; TILE_CELLS is 8..1024 and tile indices are 0..4095.
Exit 3 means a successfully processed empty tile; no output file is created.
Tiled manifests and coverage checks are handled by the region orchestration tool.
FFXI bounded export uses scripts/export_ffxi_geometry.py, a pinned-source offline wrapper.
FFXIV sqpack reader is not implemented.";

fn read(path: &str) -> Result<Vec<u8>, Error> {
    if !std::fs::metadata(path)
        .map_err(|e| Error(format!("{path}: {e}")))?
        .is_file()
    {
        return Err(Error("input must be a regular file".into()));
    }
    let file = File::open(path).map_err(|e| Error(format!("{path}: {e}")))?;
    if !file.metadata().map_err(|e| Error(e.to_string()))?.is_file() {
        return Err(Error("input must be a regular file".into()));
    }
    let mut bytes = Vec::new();
    file.take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| Error(e.to_string()))?;
    if bytes.len() as u64 > MAX_INPUT_BYTES {
        return Err(Error("input exceeds 64 MiB preflight limit".into()));
    }
    Ok(bytes)
}

#[derive(Clone, Copy, Debug)]
struct TileGrid {
    x: i32,
    z: i32,
}

impl TileGrid {
    fn parse(args: &[&str], settings: &[&str]) -> Result<Self, Error> {
        if args.len() != 7 {
            return Err(Error("expected seven tile-grid fields".into()));
        }
        let number = |value: &str| -> Result<f32, Error> {
            let value = value
                .parse::<f32>()
                .map_err(|_| Error("invalid tile-grid or build number".into()))?;
            if !value.is_finite() {
                return Err(Error("tile-grid and build settings must be finite".into()));
            }
            Ok(value)
        };
        let origin_x = number(args[0])?;
        let origin_z = number(args[1])?;
        let min_y = number(args[2])?;
        let max_y = number(args[3])?;
        if min_y > max_y {
            return Err(Error("tile MIN_Y must not exceed MAX_Y".into()));
        }
        let integer = |value: &str| -> Result<i32, Error> {
            if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(Error(
                    "tile cells and indices must be unsigned decimal integers".into(),
                ));
            }
            value
                .parse()
                .map_err(|_| Error("tile-grid integer is out of range".into()))
        };
        let cells = integer(args[4])?;
        let x = integer(args[5])?;
        let z = integer(args[6])?;
        if !(8..=1024).contains(&cells) || !(0..=4095).contains(&x) || !(0..=4095).contains(&z) {
            return Err(Error(
                "tile cells must be 8..1024 and tile indices 0..4095".into(),
            ));
        }
        let values = settings
            .iter()
            .map(|value| number(value))
            .collect::<Result<Vec<_>, _>>()?;
        let [cell_size, cell_height, height, radius, climb, slope] = values.as_slice() else {
            return Err(Error("expected six build settings".into()));
        };
        if *cell_size <= 0.0
            || *cell_height <= 0.0
            || *height <= 0.0
            || *radius < 0.0
            || *climb < 0.0
            || !(0.0..90.0).contains(slope)
        {
            return Err(Error("invalid tile voxel or agent dimensions".into()));
        }
        // Compute bounds without integer arithmetic overflow, then ensure the
        // backend's f32 coordinates retain a finite, nonempty tile interval.
        let width = f64::from(*cell_size) * f64::from(cells);
        for (origin, index) in [(origin_x, x), (origin_z, z)] {
            let low = (f64::from(origin) + f64::from(index) * width) as f32;
            let high = (f64::from(origin) + f64::from(index + 1) * width) as f32;
            if !low.is_finite() || !high.is_finite() || low >= high {
                return Err(Error(
                    "tile bounds overflow or lose precision at this origin/scale".into(),
                ));
            }
        }
        Ok(Self { x, z })
    }
}

fn build_obj(
    backend: &str,
    input: &str,
    output: &str,
    config: &[&str],
    grid: Option<&[&str]>,
) -> Result<i32, Error> {
    if std::path::Path::new(output).exists() {
        return Err(Error("output already exists; choose a new path".into()));
    }
    let bytes = read(input)?;
    let text = std::str::from_utf8(&bytes).map_err(|e| Error(format!("OBJ is not UTF-8: {e}")))?;
    let mesh = read_obj(text)?;
    if mesh.vertices.len() > 1_000_000 || mesh.triangles.len() > 1_000_000 {
        return Err(Error(
            "single-tile backend supports at most one million vertices and triangles".into(),
        ));
    }
    let defaults = ["0.3", "0.2", "2.0", "0.6", "0.9", "45"];
    let settings = if config.is_empty() {
        &defaults[..]
    } else if config.len() == 6 {
        config
    } else {
        return Err(Error(
            "provide all six build settings, or omit them for defaults".into(),
        ));
    };
    let tile_grid = grid
        .map(|grid| TileGrid::parse(grid, settings))
        .transpose()?;
    let mut command = Command::new(backend);
    command
        .arg(if tile_grid.is_some() {
            "build-tile"
        } else {
            "build"
        })
        .args(settings);
    if let Some(grid) = grid {
        command.args(grid);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| Error(format!("cannot start explicit Recast backend: {e}")))?;
    let send = (|| -> std::io::Result<()> {
        let mut stdin = BufWriter::new(child.stdin.take().expect("piped stdin"));
        writeln!(
            stdin,
            "BNAV_TRIANGLES_V1 {} {}",
            mesh.vertices.len(),
            mesh.triangles.len()
        )?;
        for v in &mesh.vertices {
            writeln!(stdin, "{} {} {}", v[0], v[1], v[2])?;
        }
        for t in &mesh.triangles {
            writeln!(stdin, "{} {} {}", t[0], t[1], t[2])?;
        }
        stdin.flush()
    })();
    // Always reap the child, including broken-pipe failures on early rejection.
    let result = child
        .wait_with_output()
        .map_err(|e| Error(format!("backend wait failed: {e}")))?;
    if result.status.code() == Some(3) && tile_grid.is_some() {
        send.map_err(|e| Error(format!("geometry transfer failed: {e}")))?;
        if !result.stdout.is_empty() {
            return Err(Error(
                "empty-tile backend result unexpectedly contains output bytes".into(),
            ));
        }
        eprint!("{}", String::from_utf8_lossy(&result.stderr));
        let grid = tile_grid.expect("checked tiled operation");
        println!("status=EMPTY scope=tiled-cell tile_x={} tile_z={} output_created=false game_qa=unverified", grid.x, grid.z);
        return Ok(3);
    }
    if !result.status.success() {
        return Err(Error(format!(
            "backend failed: {}",
            String::from_utf8_lossy(&result.stderr).trim()
        )));
    }
    send.map_err(|e| Error(format!("geometry transfer failed: {e}")))?;
    let data = &result.stdout;
    if data.len() < 16 || data.len() > MAX_INPUT_BYTES as usize + 16 {
        return Err(Error("invalid backend output length".into()));
    }
    let word = |offset| u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap());
    if word(0) != 0x56414e42 || word(4) != 7 || word(12) as usize != data.len() - 16 {
        return Err(Error("unsupported backend IPC envelope".into()));
    }
    let tile = inspect_detour(&data[16..], word(8))?;
    if let Some(grid) = tile_grid {
        if tile.coordinates != [grid.x, grid.z, 0] {
            return Err(Error(
                "backend tile coordinates do not match the requested grid cell".into(),
            ));
        }
    }
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output)
        .map_err(|e| Error(format!("cannot create new output: {e}")))?;
    file.write_all(&data[16..])
        .and_then(|_| file.sync_all())
        .map_err(|e| Error(format!("output write failed: {e}")))?;
    eprint!("{}", String::from_utf8_lossy(&result.stderr));
    if let Some(grid) = tile_grid {
        println!("status=OBSERVED scope=tiled-cell-recast-build format=raw-detour-v7 tile_x={} tile_z={} layer=0 reference_bits={} bytes={} polygons={} vertices={} coordinates=y-up settings={:?} game_qa=unverified",
            grid.x, grid.z, tile.reference_bits, tile.payload_bytes, tile.polygons, tile.vertices, settings);
    } else {
        println!("status=OBSERVED scope=single-tile-recast-build format=raw-detour-v7 reference_bits={} bytes={} polygons={} vertices={} coordinates=y-up settings={:?} game_qa=unverified",
            tile.reference_bits, tile.payload_bytes, tile.polygons, tile.vertices, settings);
    }
    Ok(0)
}

fn run(args: &[String]) -> Result<i32, Error> {
    match args
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>()
        .as_slice()
    {
        [] | ["--help"] | ["-h"] => println!("{HELP}"),
        ["--version"] => println!("bnav-extract {}", env!("CARGO_PKG_VERSION")),
        ["inspect-mmap", path] => {
            let p = inspect_mmap(&read(path)?)?;
            println!("status=OBSERVED format=dtNavMeshParams-le scope=header-only origin={:?} tile_width={} tile_height={} max_tiles={} max_polygons={} producer_identity=unverified",
                p.origin, p.tile_width, p.tile_height, p.max_tiles, p.max_polygons);
        }
        ["inspect-mmap", profile, path] => {
            let profile = Profile::parse(profile)?;
            let p = inspect_mmap_profile(&read(path)?, profile)?;
            let semantics = if p.max_polygons == 0x8000_0000 {
                "fixed-31bit-capacity"
            } else {
                "positive-i32"
            };
            println!("status=OBSERVED format=dtNavMeshParams-le scope=header-only profile={} reference_bits={} origin={:?} tile_width={} tile_height={} max_tiles={} max_polygons={} max_polygons_signed={} max_polygons_semantics={} producer_identity=unverified",
                profile.name(), profile.reference_bits(), p.origin, p.tile_width, p.tile_height, p.max_tiles, p.max_polygons, p.max_polygons as i32, semantics);
        }
        ["inspect-mmtile", profile, path] => {
            let t = inspect_mmtile(&read(path)?, Profile::parse(profile)?)?;
            println!("status=OBSERVED scope=header-and-section-lengths profile={} detour_version=7 reference_bits={} payload_bytes={} coordinates={:?} polygons={} vertices={} uses_liquids={} bounds_min={:?} bounds_max={:?} connectivity=unverified walkability=unverified",
                t.profile.name(), t.profile.reference_bits(), t.payload_bytes, t.coordinates, t.polygons, t.vertices, t.uses_liquids, t.bounds_min, t.bounds_max);
        }
        ["inspect-detour", bits, path] => {
            let bits = bits
                .parse::<u32>()
                .map_err(|_| Error("reference width must be 32 or 64".into()))?;
            let tile = inspect_detour(&read(path)?, bits)?;
            println!("status=OBSERVED scope=header-and-section-lengths format=raw-detour-v7 reference_bits={} bytes={} polygons={} vertices={} connectivity=unverified walkability=unverified",
                tile.reference_bits, tile.payload_bytes, tile.polygons, tile.vertices);
        }
        ["check-obj", path] => {
            let bytes = read(path)?;
            let text =
                std::str::from_utf8(&bytes).map_err(|e| Error(format!("OBJ is not UTF-8: {e}")))?;
            let mesh = read_obj(text)?;
            let (min, max) = mesh.bounds()?;
            println!("status=OBSERVED scope=triangle-geometry vertices={} triangles={} bounds_min={:?} bounds_max={:?} coordinates=unchanged navmesh_generated=false",
                mesh.vertices.len(), mesh.triangles.len(), min, max);
        }
        ["build-obj", backend, input, output, config @ ..] => {
            return build_obj(backend, input, output, config, None)
        }
        ["build-tile-obj", backend, input, output, origin_x, origin_z, min_y, max_y, cells, tile_x, tile_z, config @ ..] => {
            return build_obj(
                backend,
                input,
                output,
                config,
                Some(&[origin_x, origin_z, min_y, max_y, cells, tile_x, tile_z]),
            )
        }
        _ => return Err(Error(format!("unsupported command or arguments\n{HELP}"))),
    }
    Ok(0)
}

fn main() {
    match run(&std::env::args().skip(1).collect::<Vec<_>>()) {
        Ok(code) => std::process::exit(code),
        Err(e) => {
            eprintln!("bnav-extract: {e}");
            std::process::exit(2);
        }
    }
}
