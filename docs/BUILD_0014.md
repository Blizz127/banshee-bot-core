# Private QA candidate 0.1.0-build0014

Created **2026-11-15 06:04:30 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. Private publication has
no receipt; native FFXI P0 and Game QA remain **NOT_RUN**. Features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0014/banshee-bot-core-0.1.0-build0014.tar.gz` |
| SHA256 | `a9b1b578b57e438b92565becb552a1a5a8a5fc42d52f42717bfe7398c5bae1f6` |
| Bytes | `1092864` |
| Source commit | `b50b18ebb2b93366fc4a4ae18b2cdd04fc084b72` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

The [tiled builder](TILED_NAV.md#padded-triangle-selection-comparison) now excludes
triangles strictly outside each padded X/Z cell before Recast slope marking and
rasterization. It preserves candidate order, source indices, touching/crossing
faces, global validation and the single-tile path. Stderr reports input,
candidate and culled counts. Full geometry parsing/scanning remains; elapsed
speed and whole-zone coverage are unmeasured.

VERIFIED separately for reference32 and reference64: **17 synthetic cases /
38 commands each** pass. Each profile matches 15 old/new raw tile pairs, one
empty outcome and one global-Y refusal. Seam-wall query JSON matches, with a
complete four-polygon path across two tiles. Exact padded contacts, one-float-step
outside probes, all-vertices-outside crossing faces, negative origin and
border-only obstacles are covered. A distant-face fixture sends 2 of 34 triangles
to Recast; each seam-wall cell sends 4 of 36. These fixtures establish neither
general producer equivalence nor game walkability.

The new native helpers each compile with one low-priority job and no diagnostics.
Their 31 dependency input hashes, compiler version and flags match the retained
helpers. Their bridge and executable identities change:

| Profile | Packaged executable SHA256 |
| --- | --- |
| reference32 | `a4837fe23d1620b430844172639707bc3719c86f939fb1faa0594aaf6f7d2ba7` |
| reference64 | `99a851c69bd6df420cebc2cd1515a929a162712cfffc15c943c16bda477ce842` |

Fresh Rust build and readback pass: **131 payloads**, **13 startup invocations**.
All **113 tracked source files**, build log and Rust outputs join to the fresh
producer receipt. The two Rust executable hashes match build0013. All 22 core
inputs retain their saved role-comparison identities; no core or native C1 tests
were replayed. The original selector test script and both new backend identities
match the packaged comparison receipts. Synthetic assets remain external and
are not packaged. Historical verification receipts retain their original scope.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/tile-selection-20261115/smoke32-v1/result.json` | `ce9717c44605c9ca4235f4478f416dfcc5ef401a61a77d72fe374d22d0b3cf61` |
| `evidence/tile-selection-20261115/smoke64-v1/result.json` | `76304b73d480cccc922a88a88e91df514964bbd5adc81641124f6a18f4a5ca72` |
| `evidence/tile-selection-20261115/build-input-association.json` | `e19340572af0bc3d0755755fa1ec66cd8563270f02b03d97299f4b4525ef1b00` |
| `evidence/build0014-readback/result.json` | `0183ce31988f7c0eee5434dcdb8f265774acf98765052b26731d73f29156402d` |
| `evidence/build0014-readback/source-producer-join.json` | `c1a333322e331fa615b64e0ea039beaef4e34e8d7be34f6dabc7345868c95edf` |
| Embedded `provenance/rust-build-manifest.json` | `b182c5a7b7fd6219f84119ebbc19e0875ecdcc60278898e724a9838cae8fa39c` |

**Supersedes proposed build0013 for the private publisher only.** Keep earlier
artifacts for rollback. The Linux x86-64/Python 3.11 developer tool/source-kit
contract, entry points and separate native32/native64 helpers remain. Existing
publisher `claude-banshee-realm-client`, task `3f9392ca5d00`, owns private feed
publication and uploaded identity/launch/update/rollback checks. A queued intake
is not publication or Game QA acceptance.

No FFXI producer allowlist is widened, and no new producer adoption is requested.
Existing 04b/shared6ead native C1 intake and owning runtime work remain independent
of this navigation change. The bounded 06:01 metadata refresh found no new native
P0 acceptance or publication receipt; running jobs were not inspected. C1 has
no map gate; C2+ rollout stays gated. **NEVER restart FFXI**, including at zero
players. This tool package grants no installation or reload authority.
