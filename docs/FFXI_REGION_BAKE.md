# Southern San d'Oria bounded offline navigation candidate

The later [corrected owning wrapper/native-library check](FFXI_NATIVE_CONSUMPTION.md)
now accepts and queries this same tile under the retained build0001 producer.
The original refusal diagnosis below remains historical evidence. Producer
updates, source/agent calibration and real server/client QA remain outstanding.

**VERIFIED offline, 2026-11-15 02:13 CST; Game QA NOT_RUN.** This is a small
static collision experiment around the existing source homepoint fixture. It
does not establish a complete walking map or authorize movement/deployment.

The [known-source export](FFXI_EXPORT.md) selects source-space
`[-110,-10,-90]..[-60,12,-40]` from zone230, applies `(x,-y,-z)` once and emits
1,821 whole triangles. Its actual Y-up bounds extend beyond the requested
region: `[-114.1289978,-2,34.6699982]..[-58.6599998,11.6000004,74.6699982]`.
Source units and character dimensions remain uncalibrated. Doors, moving
objects, omitted collision classes and malformed records remain limitations.

## Retained identities

All paths below are relative to
`~/.local/share/banshee-bot-core/evidence/`; no geometry is stored in Git.

| Artifact | Identity |
| --- | --- |
| Export sidecar | `ffxi-sandoria230-export-20261115-02/geometry.json`, SHA-256 `2d666d9698de1755be8b751e4fac8f5f98072a58062aacd1b2ec2d0a8fcf6396` |
| Input OBJ | Same directory, `region.obj`, 261651 bytes, SHA-256 `df8acf8bbb3f16386d07e4ad5d595dce12f432d220ca4b0e20d5b0d87fa1685a` |
| Single raw32 tile | `ffxi-sandoria230-nav-20261115-01/region.navtile`, 7856 bytes, SHA-256 `4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4` |
| Four-cell collection | Same directory, `collection/manifest.json`, SHA-256 `c993a76a4fb00f0e48ad430248d4fb9f8dd2dc9c7c88e146f3df1f8839e7630c` |
| Build/query receipt | Same directory, `result.json`, SHA-256 `dbf2608d1b0dfc4c023274f3f087abd734bd6e185d33ac4ca5fade7f3a49e711` |

The executable pair came from build0002 archive readback. Both the single tile
and four grid cells build, reload and pass inspection. The single tile has 46
polygons and 101 vertices. The collection records four built cells, zero empty
and zero missing; that inventory says nothing about complete zone coverage.

## Settings and observed routes

Experimental settings in source world units: cell size `0.25`, cell height
`0.2`, character height `2`, radius `0.5`, climb `0.5`, slope `45` degrees.
The tiled grid uses origin X/Z `(-110,40)`, 100 cells per side, indices `0..1`
on each axis and the entire actual output Y range. The requested grid clips
whole-triangle output at some outer edges and lacks complete neighboring
geometry padding there. Do not treat its outer boundary as a natural obstacle.

The query requests `(-85.554,-1,64.554)` to `(-75.554,-1,64.554)` in Y-up space.
Native nearest-polygon projection uses `[2,4,2]` extents. The single-tile result
ends at approximately `(-76.1524,-1.44775,63.8958)`; the tiled result ends near
`(-76.0519,-1.41077,63.9731)`. Both reach their **projected** endpoint, with a
four-tile, nine-polygon corridor for the collection. These are not proofs of
arrival at the requested game position. Different grid origins/quantization
also explain why single and tiled results are not asserted byte-equivalent.

Every exact command, exit code and tool response is retained in the receipt.
Use fresh output paths when reproducing; existing artifacts are never replaced.

## Existing FFXI consumer boundary

The current owning wrapper at `a13dabcd` requires the retained build0001 backend
hash `d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`.
It cannot honestly accept build0002 producer provenance, whose backend hash is
`e2d9f815d5354fc3612f4498ae424c76ef4ff461af3ad8fe293eb9ffb5c85818`.

The exact retained build0001 executable pair rebaked the same OBJ/settings to
byte-identical raw tile output. Receipt:
`ffxi-sandoria230-nav-build0001-compat/result.json`. This supplies an honest old
producer comparison; it does not waive the new producer check. The wrapper's
hardcoded `producer.commit` also needs distinction from the actual source
commit recorded in each build manifest. The owning lead controls any producer
metadata/allowlist update. Tiled portals and nonzero coordinates require a
separate native integration change.

**Native wrapper compatibility is currently FAIL/PARTIAL.** The unchanged
`a13dabcd` wrapper also rejects the honestly retained build0001 producer's real
tile with `detail vertex outside convex polygon`. Build0002 is rejected earlier
as `unrecognized producer backend`. The matching raw bytes load/query in the
native Detour helper, but that does not establish which geometric constraint
needs correction. No guard was relaxed and no MSET acceptance is claimed.
Receipt: `ffxi-nav-compat-20261115-owned/result.json`, SHA-256
`a563ffdf1278b4caeaad3f0dc1271a45d6e8f75d2265eeabd2698e81473898c1`.
The owning lead must resolve this point/edge validation disagreement before
native map adoption. The [source diagnosis](FFXI_NAV_COMPATIBILITY.md) localizes
one extra boundary vertex about `1.16e-6` source units outside an edge. A
floating-point boundary mismatch is INFERRED, not a confirmed safe correction.

Next acceptance remains with the FFXI lead: reconcile the loader/source baseline,
retain incomplete/calibration flags, verify character dimensions and real
collision behavior, then Game QA checks representative routes and failures.
Preserve all deployment holds, zero-player/backup/readback/rollback conditions
and the independent C1 `/fb` P0 gate. No server process has been touched here.
