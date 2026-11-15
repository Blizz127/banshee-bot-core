use bnav_extract::{inspect_mmap, inspect_mmtile, read_obj, Error, Profile};
use std::fs::File;
use std::io::Read;

const MAX_INPUT_BYTES: u64 = 64 * 1024 * 1024;
const HELP: &str = "bnav-extract 0.1.0 — offline navigation preflight (builder pending)
Usage:
  bnav-extract inspect-mmap PATH
  bnav-extract inspect-mmtile <cmangos-v8|acore-v20> PATH
  bnav-extract check-obj PATH

Read-only; little-endian WoW profiles only. Maximum input: 64 MiB.
Tile inspection checks headers and section lengths, not connectivity or walkability.
check-obj accepts triangulated geometry without transforms; it does not build navmesh.
FFXI DAT, FFXIV sqpack and geometry-to-Recast generation are not implemented.";

fn read(path: &str) -> Result<Vec<u8>, Error> {
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
        ["check-obj", path] => {
            let bytes = read(path)?;
            let text =
                std::str::from_utf8(&bytes).map_err(|e| Error(format!("OBJ is not UTF-8: {e}")))?;
            let mesh = read_obj(text)?;
            let (min, max) = mesh.bounds()?;
            println!("status=OBSERVED scope=triangle-geometry vertices={} triangles={} bounds_min={:?} bounds_max={:?} coordinates=unchanged navmesh_generated=false",
                mesh.vertices.len(), mesh.triangles.len(), min, max);
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
