//! Offline preflight only. This crate does not yet generate or query navmeshes.
//! All binary layouts are explicitly selected, little-endian profiles.

use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Error(pub String);

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for Error {}

type Result<T> = std::result::Result<T, Error>;

fn require(ok: bool, message: &str) -> Result<()> {
    if ok {
        Ok(())
    } else {
        Err(Error(message.into()))
    }
}

fn word(bytes: &[u8], offset: usize) -> Result<u32> {
    let raw = bytes
        .get(offset..offset + 4)
        .ok_or_else(|| Error(format!("truncated 32-bit field at offset {offset}")))?;
    Ok(u32::from_le_bytes(raw.try_into().unwrap()))
}

fn scalar(bytes: &[u8], offset: usize) -> Result<f32> {
    let value = f32::from_bits(word(bytes, offset)?);
    require(value.is_finite(), "non-finite coordinate or dimension")?;
    Ok(value)
}

fn point(bytes: &[u8], offset: usize) -> Result<[f32; 3]> {
    Ok([
        scalar(bytes, offset)?,
        scalar(bytes, offset + 4)?,
        scalar(bytes, offset + 8)?,
    ])
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Profile {
    /// cMaNGOS v8, 32-bit Detour polygon references, native wrapper size 20.
    CmangosV8,
    /// AzerothCore v20, 64-bit Detour polygon references, native wrapper size 56.
    AzerothCoreV20,
}

impl Profile {
    pub fn parse(name: &str) -> Result<Self> {
        match name {
            "cmangos-v8" => Ok(Self::CmangosV8),
            "acore-v20" => Ok(Self::AzerothCoreV20),
            _ => Err(Error(
                "unsupported profile; use cmangos-v8 or acore-v20".into(),
            )),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::CmangosV8 => "cmangos-v8",
            Self::AzerothCoreV20 => "acore-v20",
        }
    }
    pub fn reference_bits(self) -> u32 {
        match self {
            Self::CmangosV8 => 32,
            Self::AzerothCoreV20 => 64,
        }
    }
    fn wrapper(self) -> (usize, u32) {
        match self {
            Self::CmangosV8 => (20, 8),
            Self::AzerothCoreV20 => (56, 20),
        }
    }
}

#[derive(Debug, PartialEq)]
pub struct MapParams {
    pub origin: [f32; 3],
    pub tile_width: f32,
    pub tile_height: f32,
    pub max_tiles: u32,
    pub max_polygons: u32,
}

/// Reads the 28-byte native dtNavMeshParams layout. A .mmap has no magic/version;
/// the caller must establish the producer separately before trusting these fields.
pub fn inspect_mmap(bytes: &[u8]) -> Result<MapParams> {
    require(
        bytes.len() == 28,
        "expected exactly 28 bytes of little-endian dtNavMeshParams",
    )?;
    let p = MapParams {
        origin: point(bytes, 0)?,
        tile_width: scalar(bytes, 12)?,
        tile_height: scalar(bytes, 16)?,
        max_tiles: word(bytes, 20)?,
        max_polygons: word(bytes, 24)?,
    };
    require(
        p.tile_width > 0.0 && p.tile_height > 0.0,
        "tile dimensions must be positive",
    )?;
    require(
        p.max_tiles > 0 && p.max_tiles <= i32::MAX as u32,
        "invalid maximum tile count",
    )?;
    require(
        p.max_polygons > 0 && p.max_polygons <= i32::MAX as u32,
        "invalid maximum polygon count",
    )?;
    Ok(p)
}

#[derive(Debug, PartialEq)]
pub struct TileInspection {
    pub profile: Profile,
    pub uses_liquids: bool,
    pub payload_bytes: usize,
    pub coordinates: [i32; 3],
    pub polygons: u32,
    pub vertices: u32,
    pub bounds_min: [f32; 3],
    pub bounds_max: [f32; 3],
}

/// Checks the wrapper, dtMeshHeader and complete section lengths. This is NOT a
/// complete validator of polygon indices, adjacency, walkability or connectivity.
pub fn inspect_mmtile(bytes: &[u8], profile: Profile) -> Result<TileInspection> {
    let (wrapper_len, version) = profile.wrapper();
    require(
        bytes.len() >= wrapper_len + 100,
        "truncated mmap wrapper or Detour header",
    )?;
    require(
        word(bytes, 0)? == 0x4d4d4150,
        "invalid little-endian MMAP magic",
    )?;
    require(
        word(bytes, 4)? == 7,
        "unsupported Detour version; expected 7",
    )?;
    require(
        word(bytes, 8)? == version,
        "mmap version does not match selected profile",
    )?;
    let payload_bytes = word(bytes, 12)? as usize;
    require(
        payload_bytes == bytes.len() - wrapper_len,
        "declared tile size differs from file length",
    )?;
    let liquid_flag = match profile {
        Profile::CmangosV8 => word(bytes, 16)?,
        Profile::AzerothCoreV20 => bytes[16] as u32,
    };
    require(liquid_flag <= 1, "invalid usesLiquids flag")?;
    if profile == Profile::AzerothCoreV20 {
        // Recast generation settings are recorded by v20; inspect finite fields
        // without claiming that the caller's desired build settings match them.
        for offset in [20, 40, 44, 48, 52] {
            scalar(bytes, offset)?;
        }
    }
    let data = &bytes[wrapper_len..];
    require(
        word(data, 0)? == 0x444e4156,
        "invalid little-endian Detour DNAV magic",
    )?;
    require(
        word(data, 4)? == 7,
        "Detour payload version differs from supported version 7",
    )?;
    // Counts occupy offsets 24..60; signed negative counts are invalid.
    let mut counts = [0u32; 9];
    for (i, count) in counts.iter_mut().enumerate() {
        *count = word(data, 24 + 4 * i)?;
        require(*count <= i32::MAX as u32, "negative Detour count")?;
    }
    let [polygons, vertices, links, details, detail_vertices, detail_triangles, bv_nodes, connections, off_mesh_base] =
        counts;
    require(
        polygons > 0 && vertices > 0,
        "empty tile is not a usable navmesh tile",
    )?;
    require(
        off_mesh_base <= polygons && connections == polygons - off_mesh_base,
        "off-mesh counts do not partition the polygons",
    )?;
    require(
        details == off_mesh_base,
        "detail mesh count differs from base polygon count",
    )?;
    let bounds_min = point(data, 72)?;
    let bounds_max = point(data, 84)?;
    require(
        (0..3).all(|i| bounds_min[i] <= bounds_max[i]),
        "inverted Detour bounds",
    )?;
    for offset in [60, 64, 68, 96] {
        require(
            scalar(data, offset)? >= 0.0,
            "negative Detour agent dimension or quantization",
        )?;
    }
    // Native sections use dtAlign4; all these element sizes are already 4-aligned.
    // dtLink is 12 bytes with 32-bit references and 16 bytes with 64-bit references.
    let link_size = if profile.reference_bits() == 32 {
        12
    } else {
        16
    };
    let sections = [
        (vertices, 12u64),
        (polygons, 32),
        (links, link_size),
        (details, 12),
        (detail_vertices, 12),
        (detail_triangles, 4),
        (bv_nodes, 16),
        (connections, 36),
    ];
    let expected = 100u64
        + sections
            .iter()
            .map(|(count, size)| u64::from(*count) * size)
            .sum::<u64>();
    require(
        expected == payload_bytes as u64,
        "Detour section lengths do not match selected ABI and payload size",
    )?;
    Ok(TileInspection {
        profile,
        uses_liquids: liquid_flag == 1,
        payload_bytes,
        coordinates: [
            word(data, 8)? as i32,
            word(data, 12)? as i32,
            word(data, 16)? as i32,
        ],
        polygons,
        vertices,
        bounds_min,
        bounds_max,
    })
}

/// Canonical triangle input for a future Recast backend. Coordinates are passed
/// through unchanged: the game extractor owns units, handedness and up-axis.
#[derive(Debug, PartialEq)]
pub struct TriangleMesh {
    pub vertices: Vec<[f32; 3]>,
    pub triangles: Vec<[usize; 3]>,
}

impl TriangleMesh {
    pub fn validate(&self) -> Result<()> {
        require(
            !self.vertices.is_empty() && !self.triangles.is_empty(),
            "geometry must contain vertices and triangles",
        )?;
        require(
            self.vertices.iter().flatten().all(|v| v.is_finite()),
            "non-finite geometry coordinate",
        )?;
        for triangle in &self.triangles {
            require(
                triangle.iter().all(|i| *i < self.vertices.len()),
                "triangle vertex index out of range",
            )?;
            let a = self.vertices[triangle[0]].map(f64::from);
            let b = self.vertices[triangle[1]].map(f64::from);
            let c = self.vertices[triangle[2]].map(f64::from);
            let u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
            let v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
            let cross = [
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            ];
            require(cross.iter().any(|v| *v != 0.0), "degenerate triangle")?;
        }
        Ok(())
    }
    pub fn bounds(&self) -> Result<([f32; 3], [f32; 3])> {
        self.validate()?;
        let mut min = self.vertices[0];
        let mut max = min;
        for vertex in &self.vertices {
            for axis in 0..3 {
                min[axis] = min[axis].min(vertex[axis]);
                max[axis] = max[axis].max(vertex[axis]);
            }
        }
        Ok((min, max))
    }
}

/// Strict geometry-only OBJ subset. Faces must already be triangles; no implicit
/// triangulation, surface conversion, transforms, or external material loads.
pub fn read_obj(text: &str) -> Result<TriangleMesh> {
    let mut mesh = TriangleMesh {
        vertices: Vec::new(),
        triangles: Vec::new(),
    };
    for (line_index, line) in text.lines().enumerate() {
        let line = line.split('#').next().unwrap_or("");
        let mut fields = line.split_whitespace();
        let Some(kind) = fields.next() else { continue };
        let parts: Vec<_> = fields.collect();
        let line_error = |message: &str| Error(format!("OBJ line {}: {message}", line_index + 1));
        match kind {
            "v" => {
                if parts.len() != 3 {
                    return Err(line_error("expected v x y z (no homogeneous coordinate)"));
                }
                let mut vertex = [0.0; 3];
                for (axis, part) in parts.iter().enumerate() {
                    vertex[axis] = part
                        .parse::<f32>()
                        .map_err(|_| line_error("invalid vertex coordinate"))?;
                }
                mesh.vertices.push(vertex);
            }
            "f" => {
                if parts.len() != 3 {
                    return Err(line_error("only triangulated faces are supported"));
                }
                let mut triangle = [0; 3];
                for (corner, part) in parts.iter().enumerate() {
                    let raw = part
                        .split('/')
                        .next()
                        .unwrap_or("")
                        .parse::<i64>()
                        .map_err(|_| line_error("invalid face vertex index"))?;
                    let index = if raw > 0 {
                        raw - 1
                    } else if raw < 0 {
                        mesh.vertices.len() as i64 + raw
                    } else {
                        return Err(line_error("OBJ vertex indices cannot be zero"));
                    };
                    if index < 0 || index as usize >= mesh.vertices.len() {
                        return Err(line_error(
                            "face refers to missing vertex; forward references are unsupported",
                        ));
                    }
                    triangle[corner] = index as usize;
                }
                mesh.triangles.push(triangle);
            }
            // These records have no effect on triangle collision geometry.
            "o" | "g" | "s" | "usemtl" | "mtllib" | "vn" | "vt" => {}
            _ => return Err(line_error("unsupported OBJ record")),
        }
    }
    mesh.validate()?;
    Ok(mesh)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn put(bytes: &mut [u8], offset: usize, value: u32) {
        bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    }
    fn tile(profile: Profile) -> Vec<u8> {
        let (wrapper, version) = profile.wrapper();
        let link_size = if profile.reference_bits() == 32 {
            12
        } else {
            16
        };
        let size = 100 + 3 * 12 + 32 + link_size + 12 + 4;
        let mut bytes = vec![0; wrapper + size];
        for (offset, value) in [(0, 0x4d4d4150), (4, 7), (8, version), (12, size as u32)] {
            put(&mut bytes, offset, value);
        }
        for (offset, value) in [
            (0, 0x444e4156),
            (4, 7),
            (24, 1),
            (28, 3),
            (32, 1),
            (36, 1),
            (44, 1),
            (56, 1),
        ] {
            put(&mut bytes, wrapper + offset, value);
        }
        bytes
    }

    #[test]
    fn rejects_version_mismatch_truncation_and_wrong_abi() {
        for profile in [Profile::CmangosV8, Profile::AzerothCoreV20] {
            let mut bytes = tile(profile);
            assert_eq!(inspect_mmtile(&bytes, profile).unwrap().polygons, 1);
            assert!(inspect_mmtile(&bytes[..bytes.len() - 1], profile).is_err());
            let (wrapper, _) = profile.wrapper();
            put(&mut bytes, wrapper + 32, 2);
            assert!(inspect_mmtile(&bytes, profile)
                .unwrap_err()
                .0
                .contains("section lengths"));
            put(&mut bytes, 8, 999);
            assert!(inspect_mmtile(&bytes, profile)
                .unwrap_err()
                .0
                .contains("version"));
        }
    }

    #[test]
    fn malformed_headers_are_rejected_without_allocation() {
        let mut bytes = tile(Profile::CmangosV8);
        put(&mut bytes, 20 + 24, u32::MAX);
        assert!(inspect_mmtile(&bytes, Profile::CmangosV8).is_err());
        let mut bytes = tile(Profile::CmangosV8);
        put(&mut bytes, 20 + 72, f32::NAN.to_bits());
        assert!(inspect_mmtile(&bytes, Profile::CmangosV8).is_err());
        for n in 0..120 {
            assert!(inspect_mmtile(&vec![0; n], Profile::CmangosV8).is_err());
        }
    }

    #[test]
    fn mmap_needs_exact_length_positive_dimensions_and_finite_values() {
        let mut bytes = vec![0; 28];
        for offset in [12, 16] {
            put(&mut bytes, offset, 533.3333f32.to_bits());
        }
        for offset in [20, 24] {
            put(&mut bytes, offset, 1024);
        }
        assert_eq!(inspect_mmap(&bytes).unwrap().max_tiles, 1024);
        put(&mut bytes, 0, f32::INFINITY.to_bits());
        assert!(inspect_mmap(&bytes).is_err());
        assert!(inspect_mmap(&[0; 28]).is_err());
        assert!(inspect_mmap(&[0; 29]).is_err());
    }

    #[test]
    fn triangle_input_supports_negative_indices_but_rejects_bad_geometry() {
        let vertices = "v 0 0 0\nv 2 0 0\nv 0 0 2\n";
        let mesh = read_obj(&format!("{vertices}f -3 -2 -1\n")).unwrap();
        assert_eq!(mesh.triangles, vec![[0, 1, 2]]);
        assert_eq!(mesh.bounds().unwrap(), ([0.0; 3], [2.0, 0.0, 2.0]));
        for face in ["f 1 2 4", "f 1 2 2", "f 1 2 3 1", "f 0 1 2", "f -4 -2 -1"] {
            assert!(read_obj(&format!("{vertices}{face}")).is_err(), "{face}");
        }
        assert!(read_obj("v NaN 0 0\nv 1 0 0\nv 0 0 1\nf 1 2 3").is_err());
        assert!(read_obj("v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3").is_err());
    }
}
