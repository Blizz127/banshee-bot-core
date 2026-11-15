//! Original offline entry point; the pinned owning project supplies the reader.
use forever_audit::geometry_export::{self, Bounds, Limits, Provenance, Request};
use forever_audit::Client;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str, String> {
    v[key].as_str().ok_or_else(|| format!("missing text field {key}"))
}

fn point(v: &Value) -> Result<[f32; 3], String> {
    let a = v.as_array().filter(|a| a.len() == 3).ok_or("expected three bounds coordinates")?;
    let mut p = [0.0; 3];
    for i in 0..3 {
        p[i] = a[i].as_f64().ok_or("invalid bounds coordinate")? as f32;
        if !p[i].is_finite() { return Err("non-finite bounds coordinate".into()); }
    }
    Ok(p)
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    OpenOptions::new().write(true).create_new(true).open(path)
        .and_then(|mut f| f.write_all(bytes)).map_err(|e| format!("{}: {e}", path.display()))
}

fn run(path: &Path) -> Result<(), String> {
    let request_bytes = fs::read(path).map_err(|e| e.to_string())?;
    if request_bytes.len() > 64 * 1024 { return Err("request exceeds 64 KiB".into()); }
    let q: Value = serde_json::from_slice(&request_bytes).map_err(|e| e.to_string())?;
    let root = Path::new(text(&q, "snapshot_root")?);
    let output = Path::new(text(&q, "output_dir")?);
    let zone = q["zone_id"].as_u64().and_then(|n| u16::try_from(n).ok()).ok_or("invalid zone id")?;
    let client = Client::open(root)?;
    let relative = client.dat_path(zone).ok_or("zone absent from snapshot ROM tables")?;
    if relative != text(&q, "asset_relative")? {
        return Err(format!("resolved DAT {relative} differs from explicitly staged selection"));
    }
    let bytes = fs::read(root.join(&relative)).map_err(|e| e.to_string())?;
    let asset_hash: [u8; 32] = Sha256::digest(&bytes).into();
    let hex: String = asset_hash.iter().map(|b| format!("{b:02x}")).collect();
    if hex != text(&q, "asset_sha256")? { return Err("staged DAT SHA256 mismatch".into()); }
    let raw = client.raw_collision(zone)?;
    let mut kinds = BTreeMap::<u8, usize>::new();
    for kind in &raw.kinds { *kinds.entry(*kind).or_default() += 1; }
    let degenerate = raw.tris.iter().filter(|t| {
        let a = (t[1] - t[0]).as_dvec3();
        let b = (t[2] - t[0]).as_dvec3();
        a.cross(b).length_squared() == 0.0
    }).count();
    let diagnostic = json!({
        "status": "OBSERVED", "scope": "existing decoder output only; not complete collision or walkability",
        "resolved_relative_path": relative, "asset_sha256": hex,
        "input_triangles": raw.tris.len(), "normals": raw.normals.len(),
        "kinds": raw.kinds.len(), "object_flags": raw.obj_flags.len(),
        "source_grid": raw.grid, "surface_kind_counts": kinds,
        "degenerate_triangles": degenerate,
        "decoder_revision": text(&q, "source_revision")?,
    });
    write_new(&output.join("raw-observation.json"), &serde_json::to_vec_pretty(&diagnostic).map_err(|e| e.to_string())?)?;
    let request = Request {
        region: Bounds { min: point(&q["bounds_min"])? , max: point(&q["bounds_max"])? },
        limits: Limits { input_triangles: 1_000_000, output_triangles: 333_333, obj_bytes: 64 * 1024 * 1024 },
        provenance: Provenance {
            server_lane: "banshee-bot-core offline interoperability".into(), zone_id: zone,
            zone_name: text(&q, "zone_name")?.into(), region_name: text(&q, "region_name")?.into(),
            instance_and_floor: "static source AABB only; floor and dynamic coverage unresolved".into(),
            asset_path: text(&q, "owner_asset_path")?.into(), asset_sha256: Some(asset_hash),
            source_build: Some("owner full-1.2.2 directory label; not independently version-authenticated".into()),
            exporter_revision: text(&q, "source_revision")?.into(),
            invocation: vec!["bnav-ffxi-export-driver".into(), path.display().to_string()],
            format_evidence: vec![text(&q, "format_evidence")?.into()],
            unit_name: "FFXI source world unit".into(),
            metres_per_unit: q["metres_per_unit_assumption"].as_f64().ok_or("missing explicit scale assumption")?,
            unit_evidence: "caller assumption only; physical scale uncalibrated; no coordinate rescale applied".into(),
        },
    };
    let export = geometry_export::export_region(&raw, &request).map_err(|e| e.to_string())?;
    write_new(&output.join("region.obj"), export.obj.as_bytes())?;
    write_new(&output.join("export-manifest.json"), &serde_json::to_vec_pretty(&export.manifest.json()).map_err(|e| e.to_string())?)?;
    println!("{}", json!({"status":"OBSERVED", "included_triangles":export.manifest.included_triangles,
        "obj_bytes":export.obj.len(), "collision_complete":false, "game_qa":"unverified"}));
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).is_some_and(|a| a == "--help") {
        println!("bnav-ffxi-export-driver REQUEST.json\nOffline pinned-library export; no game process or network.");
        return;
    }
    if args.len() != 2 {
        eprintln!("expected one private REQUEST.json path");
        std::process::exit(2);
    }
    if let Err(e) = run(Path::new(&args[1])) {
        eprintln!("FFXI export refused: {e}");
        std::process::exit(1);
    }
}
