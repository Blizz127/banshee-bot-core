//! Original external library smoke. Source positions come only from the
//! validated input tile at runtime and remain in external evidence.
#![allow(dead_code)]
mod detour_mset;

use detour_mset::{wrap_raw32, Producer, Provenance};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};

const BUFFER: usize = 512; // Owning shim uses this fixed capacity for both path APIs.
const EXTENTS: [f32; 3] = [2.5, 5.0, 2.5]; // Owning xi-map's POLY_PICK_EXT.

fn hex(data: &[u8]) -> String { data.iter().map(|v| format!("{v:02x}")).collect() }
fn hash(data: &[u8]) -> String { hex(&Sha256::digest(data)) }
fn unhex(value: &Value) -> Result<[u8; 32], String> {
    let text = value.as_str().ok_or("missing hash")?;
    if text.len() != 64 || !text.is_ascii() { return Err("invalid hash text".into()); }
    let mut bytes = [0; 32];
    for (i, out) in bytes.iter_mut().enumerate() {
        *out = u8::from_str_radix(&text[2*i..2*i+2], 16).map_err(|e| e.to_string())?;
    }
    Ok(bytes)
}
fn require(ok: bool, message: &str) -> Result<(), String> {
    if ok { Ok(()) } else { Err(message.into()) }
}
fn u16_at(raw: &[u8], at: usize) -> usize { u16::from_le_bytes(raw[at..at+2].try_into().unwrap()) as usize }
fn u32_at(raw: &[u8], at: usize) -> usize { u32::from_le_bytes(raw[at..at+4].try_into().unwrap()) as usize }
fn point(raw: &[u8], at: usize) -> [f32; 3] {
    std::array::from_fn(|axis| f32::from_le_bytes(raw[at+4*axis..at+4*axis+4].try_into().unwrap()))
}
fn distance2(a: &[f32; 3], b: &[f32; 3]) -> f32 { (0..3).map(|i| (a[i]-b[i]).powi(2)).sum() }

fn exercise(args: &[String], result: &mut Value) -> Result<(), String> {
    require(args.len() == 5, "usage: native-smoke PLAN CASE OUTPUTS RESULT")?;
    require(cfg!(target_endian = "little"), "native smoke requires the declared little-endian host ABI")?;
    let plan: Value = serde_json::from_slice(&fs::read(&args[1]).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    let case = plan["cases"].as_array().ok_or("missing cases")?.iter()
        .find(|case| case["name"] == args[2]).ok_or("selected case absent")?;
    require(case["expect"] == "accept" && case["mode"] == "pinned", "case must be pinned and expected to accept")?;
    let raw = fs::read(case["path"].as_str().ok_or("missing raw path")?).map_err(|e| e.to_string())?;
    require(hash(&raw) == case["sha256"], "raw input hash changed")?;
    let producer = &case["producer"];
    let adapted = wrap_raw32(&raw, Provenance {
        raw_sha256: unhex(&case["sha256"] )?,
        producer: Producer::BansheeAe73Raw32 {
            backend_sha256: unhex(&producer["backend_sha256"] )?,
            build_receipt_sha256: unhex(&producer["build_receipt_sha256"] )?,
            geometry_manifest_sha256: unhex(&producer["geometry_manifest_sha256"] )?,
            obj_sha256: unhex(&case["obj_sha256"] )?,
        },
    }).map_err(|e| e.to_string())?;
    let mset = fs::read(Path::new(&args[3]).join(format!("{}.mset", args[2]))).map_err(|e| e.to_string())?;
    require(mset == adapted.mset && mset[48..] == raw, "wrapper output differs or modified original payload")?;
    result["raw_sha256"] = json!(hash(&raw));
    result["mset_sha256"] = json!(hash(&mset));
    result["payload_unchanged"] = json!(true);
    result["wrapper_manifest"] = adapted.manifest.to_json();
    result["native_load_or_query_executed"] = json!(true);
    let (mut mesh, loaded) = detour_sys::Mesh::load(&mset).map_err(|e| format!("native load: {e:?}"))?;
    result["load"] = json!({"tiles_declared":loaded.tiles_declared,"tiles_added":loaded.tiles_added});
    require(loaded.tiles_declared == 1 && loaded.tiles_added == 1, "native did not load exactly one declared tile")?;

    // These offsets are read only AFTER the exact owning wrapper validated the
    // raw32 layout, every index and convexity. No repair or resampling occurs.
    let polygons = u32_at(&raw, 24);
    let vertices = u32_at(&raw, 28);
    let poly_start = 100 + vertices * 12;
    let mut picks = Vec::new();
    let mut nearest_records = Vec::new();
    for p in 0..polygons {
        let at = poly_start + p * 32;
        let count = raw[at + 30] as usize;
        let mut center = [0.0; 3];
        for j in 0..count {
            let v = point(&raw, 100 + 12 * u16_at(&raw, at + 4 + 2*j));
            for axis in 0..3 { center[axis] += v[axis] / count as f32; }
        }
        let range = adapted.checked_query_range(center, EXTENTS).map_err(|e| e.to_string())?;
        let mut nearest = [f32::NAN; 3];
        let (status, reference) = mesh.find_nearest_poly(&center, &EXTENTS, &mut nearest);
        let valid = reference != 0 && mesh.is_valid_poly_ref(reference);
        nearest_records.push(json!({"coarse_polygon_index":p,"center":center,"half_extents":EXTENTS,
            "preflight_tile_visits":range.visits,"status":status,"reference":reference,"valid":valid,
            "nearest":if nearest.iter().all(|v| v.is_finite()) { Some(nearest) } else { None }}));
        result["nearest_queries"] = json!(&nearest_records);
        require(status == detour_sys::DT_SUCCESS && valid && nearest.iter().all(|v| v.is_finite()),
                "native nearest query failed for a validated polygon centroid")?;
        picks.push((reference, nearest));
    }
    // Select the first actual adjacent pair with distinct native polygon refs.
    // This tests one bounded corridor, not a route to an invented game waypoint.
    let mut pair = None;
    for p in 0..polygons {
        let at = poly_start + p * 32;
        for edge in 0..raw[at+30] as usize {
            let neighbor = u16_at(&raw, at + 16 + 2*edge);
            if neighbor != 0 && picks[p].0 != picks[neighbor-1].0 && pair.is_none() { pair = Some((p, neighbor-1)); }
        }
    }
    let (start_index, end_index) = pair.ok_or("no distinct adjacent native polygon pair for path smoke")?;
    let (start_ref, start) = picks[start_index];
    let (end_ref, end) = picks[end_index];
    let (status, corridor) = mesh.find_path(start_ref, end_ref, &start, &end, BUFFER);
    result["corridor"] = json!({"start_polygon_index":start_index,"end_polygon_index":end_index,
        "start_ref":start_ref,"end_ref":end_ref,"status":status,"references":corridor,"capacity":BUFFER});
    require(status == detour_sys::DT_SUCCESS && corridor.first() == Some(&start_ref) && corridor.last() == Some(&end_ref),
            "native path is failed, partial, truncated, or does not reach the selected endpoint")?;
    let (status, straight) = mesh.find_straight_path(&start, &end, &corridor, BUFFER);
    result["straight_path"] = json!({"status":status,"points":straight,"capacity":BUFFER});
    require(status == detour_sys::DT_SUCCESS && straight.len() >= 2 && straight.iter().flatten().all(|v| v.is_finite())
        && distance2(straight.first().unwrap(), &start) <= 0.000001
        && distance2(straight.last().unwrap(), &end) <= 0.000001,
        "native straight path is failed, partial, nonfinite, or misses nearest endpoints")?;
    result["nearest_query_count"] = json!(nearest_records.len());
    result["verdict"] = json!("PASS");
    Ok(())
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    let mut result = json!({"verdict":"FAIL","scope":"Offline exact owning detour-sys load and bounded mesh-derived query",
        "native_load_or_query_executed":false,"coordinate_transform":"none; exporter already applied (x,-y,-z)",
        "query_source":"validated coarse polygon centroids and first adjacent pair; no game waypoints",
        "coverage_complete":false,"agent_calibration_verified":false,"native_server_p0":"NOT_RUN","game_qa":"NOT_RUN"});
    if let Err(error) = exercise(&args, &mut result) { result["error"] = json!(error); }
    let text = serde_json::to_string_pretty(&result).unwrap();
    if let Some(path) = args.get(4) {
        let mut output = fs::OpenOptions::new().write(true).create_new(true).open(path).expect("fresh receipt");
        output.write_all(text.as_bytes()).unwrap(); output.sync_all().unwrap();
    }
    println!("{text}");
    if result["verdict"] != "PASS" { std::process::exit(1); }
}
