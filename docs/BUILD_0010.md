# Private QA candidate 0.1.0-build0010

Created **2026-11-15 03:54:40 CST**. **QA_CANDIDATE, not released.**
Build, readback and packaged startup: **PASS**. Publication has no receipt;
native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0010/banshee-bot-core-0.1.0-build0010.tar.gz` |
| SHA256 | `3d2b583c73eb6d5e99e205d190d2a8a738989337afe6e04c57f3df489c43332c` |
| Bytes | `1029589` |
| Source commit | `438853d2abaef27ea70f474190a2a2519f69f977` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Adds the pure [Rust navigation measurements](NAV_CORE_METRICS.md): endpoint
projection distances, separation and route length for supplied complete paths.
The optional explicit projection limit produces an outcome without claiming
route legality. Incomplete, malformed and oversized input is refused. Existing
navigation types and native buffer requirements are unchanged. No runtime call
site, native query, movement or gameplay authority is added.

VERIFIED: **eight new focused navigation tests pass**. All **111 payloads** and
**13 packaged startup invocations** pass. The archive's 20 current core inputs
and new test match that completed receipt. The decision module and test retain
the bytes from their separate earlier 11-test result; those tests were not
replayed or aggregated. All four packaged executables retain build0009 hashes.

The historical C1 comparison retains its exact scope: 16 of its 18 inputs remain
byte-identical; only brain/nav module exports were added to existing files.
Existing C1 primitive implementations, feature flags, manifests and lock retain
their bytes. No whole-current-crate C1 equivalence or new native acceptance is
claimed; native tests and previous comparison jobs were not replayed.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/nav-core-metrics-integrated-20261115-01/result.json` | `74db0915cf325d5dc09f10748903924c63989b2150106e7893bc9b83e3d46b54` |
| `evidence/build0010-readback/result.json` | `9728537b6f0ff91ef0e2494294019cfaa959b66dc4e010b461d0546c4f2448db` |
| `evidence/build0010-readback/source-evidence-join.json` | `7ca217a4b636389511b641a935266d640dc57506a717ac25d2d96b478de5f196` |

**Supersedes proposed build0009 for the private publisher only.** Retain earlier
candidates for rollback. Same Linux x86-64/Python 3.11 developer tool/source-kit
contract and entry points; native32/native64 remain distinct unchanged binaries.
Keep the Python metrics module beside its query wrappers. Existing publisher
`claude-banshee-realm-client`, task `3f9392ca5d00`, owns the private feed,
uploaded identity, launch/update detection and rollback checks.

The owning FFXI 04b/shared6ead source candidate remains canonical. This is not a
replacement native intake or a producer adoption proposal; the allowlist is
unchanged. Native P0/Game QA and C2+ rollout gates persist; C1 has no map gate.
**Never restart FFXI**, including at zero players. The manifest grants no
installation/reload authority.
