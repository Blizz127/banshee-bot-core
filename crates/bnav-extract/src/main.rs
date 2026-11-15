use bnav_extract::{inspect_detour, inspect_mmap, inspect_mmtile, read_obj, Error, Profile};
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Read, Write};
use std::process::{Command, Stdio};

const MAX_INPUT_BYTES: u64 = 64 * 1024 * 1024;
const HELP: &str = "bnav-extract 0.1.0 — offline navigation builder and preflight
Usage:
  bnav-extract inspect-mmap PATH
  bnav-extract inspect-mmtile <cmangos-v8|acore-v20> PATH
  bnav-extract inspect-detour <32|64> PATH
  bnav-extract check-obj PATH
  bnav-extract build-obj BACKEND INPUT OUTPUT [CELL_SIZE CELL_HEIGHT HEIGHT RADIUS CLIMB SLOPE]

Inspection is read-only; little-endian profiles only. Maximum input: 64 MiB.
Tile inspection checks headers and section lengths, not connectivity or walkability.
check-obj accepts triangulated geometry without transforms; it does not build navmesh.
build-obj writes a new raw Detour v7 tile via an explicit external Recast backend.
Input must be Y-up; all agent dimensions use the geometry's world units.
Default settings: 0.3 0.2 2.0 0.6 0.9 45. Outputs are never overwritten.
Build the backend with scripts/build_bnav_backend.py; see docs/BNAV_EXTRACT.md.
FFXI DAT and FFXIV sqpack readers and multi-tile stitching are not implemented.";

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

fn build_obj(backend: &str, input: &str, output: &str, config: &[&str]) -> Result<(), Error> {
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
    let mut child = Command::new(backend)
        .arg("build")
        .args(settings)
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
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output)
        .map_err(|e| Error(format!("cannot create new output: {e}")))?;
    file.write_all(&data[16..])
        .and_then(|_| file.sync_all())
        .map_err(|e| Error(format!("output write failed: {e}")))?;
    eprint!("{}", String::from_utf8_lossy(&result.stderr));
    println!("status=OBSERVED scope=single-tile-recast-build format=raw-detour-v7 reference_bits={} bytes={} polygons={} vertices={} coordinates=y-up settings={:?} game_qa=unverified",
        tile.reference_bits, tile.payload_bytes, tile.polygons, tile.vertices, settings);
    Ok(())
}

fn run(args: &[String]) -> Result<(), Error> {
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
            build_obj(backend, input, output, config)?
        }
        _ => return Err(Error(format!("unsupported command or arguments\n{HELP}"))),
    }
    Ok(())
}

fn main() {
    if let Err(e) = run(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("bnav-extract: {e}");
        std::process::exit(2);
    }
}
