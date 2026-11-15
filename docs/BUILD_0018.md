# Private QA candidate 0.1.0-build0018

Created **2026-11-15 07:55:59 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. Private publication has
no receipt; native FFXI P0 and Game QA remain **NOT_RUN**. Features remain OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0018/banshee-bot-core-0.1.0-build0018.tar.gz` |
| SHA256 | `508ca3863fae576558ed719797d9a887146c323c4c1b31e690c7a4013ef03fc2` |
| Bytes | `1197956` |
| Source commit | `8153d3be6f1d986a173601bb758fa9361ad3cae1` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds [typed native query refusals](NAV_QUERY_REFUSALS.md), opt-in wrapper
`--diagnostic-refusals` and [probe format v2](NAV_ROUTE_PROBES.md). Missing nearby
polygons and a nonempty incomplete corridor can be recorded as specific spatial
observations. Query-budget exhaustion remains separate and always fails a probe
list as ERROR; it can never be a passing disconnected-route expectation. Invalid
files, ABI/grid errors and unclassified failures keep stderr/exit 2. Existing
commands retain their output behavior in the focused comparison. No world-level
unreachability or movement acceptance is claimed.

VERIFIED: both reference ABIs pass **21 checks /33 native commands**. Legacy
exit/stdout/stderr and successful report output match exactly in those cases.
An original synthetic 300-polygon fixture proves connectivity with a 512-slot
buffer and truncation at 256 without node exhaustion, then verifies the report
mode's budget classification. Wrong ABI, malformed files and missing selected
tiles remain ordinary errors. The wrapper/probe smoke passes **18 outer commands
across both ABIs**, with 16 runner commands per ABI, including actual budget
ERROR and a later NOT_RUN probe. **17 pure tests** pass. Node exhaustion,
straight-path buffer exhaustion and filesystem/resource-termination fault
injection remain unrun; no native FFXI job or Game QA ran.

Fresh readback passes **149 payloads /14 startup invocations**. Both packaged
backend helps expose the new report modes; both wrapper query helps expose the
opt-in flag. All **128 tracked source files**, log and Rust binaries join to the
fresh producer and current test identities. The native compiler flags and all
31 external source inputs match the retained baseline; only the original bridge
changes. New native hashes are distinct producer identities, not new FFXI
allowlist entries. The two Rust executables and all 22 shared-core inputs remain
unchanged; no C1 comparison or prior benchmark was replayed.

| Executable | SHA256 |
| --- | --- |
| `bnav-extract` | `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30` |
| `bot-soak` | `e17985b458b79cdba36f6c4c20086d875d83edd19460decea8e2d24d947568c1` |
| `bnav-recast` (32) | `b7c1475b2558ae3362c9deef11e277b382c1a4232f404b161f8a91e80e90732d` |
| `bnav-recast64` | `d378b4a865926c49e28a7b55b639a2839cef5fe328ac6891da582d77d3bdde6f` |

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/query-refusals-20261115/verification-join.json` | `552dea3c13e2122e9e5a378a1a26f546f8020f444b15cd78c3749190c997c384` |
| `evidence/query-refusals-20261115/pure-v1/result.json` | `57b246d1e2faa2fad477f9bf49b447ac214ff9059098ec462aeb04eabd0a3640` |
| `evidence/query-refusals-20261115/native32-v1/result.json` | `2d40af6e97f815164017ac0f391be701ade79cc3f6c053289ff4f758625a9423` |
| `evidence/query-refusals-20261115/native64-v1/result.json` | `55a091e517d254f4e5ebc7aa9f3a5f022c9df7e59d881235ac360f96438ee3e8` |
| `evidence/query-refusals-20261115/wrapper-v1/result.json` | `8e0ab08f75bb02d1e7c55d1a6df3c48af3e249c3225d40432d3b0524a56cde25` |
| `evidence/build0018-readback/result.json` | `ec5a81cc08a2928a76ab3ff3b68e2b28b67b3d48476ccede6340e69b86d80d97` |
| `evidence/build0018-readback/source-producer-join.json` | `67c503c3b2b317ac76a073998149272562c8c39c3a1cf2978c8c128d68b67acd` |
| Embedded `provenance/rust-build-manifest.json` | `e1bcebbd3fe5914314bf3d54a7160220f66fa559af72dbeb8b53c7062859219e` |

The verification join also pins the independent corridor fixture builds, backend
build records, actual command logs and unchanged metric algorithms. Synthetic
data, binaries and evidence remain outside Git; only original code is packaged.

**Supersedes proposed build0017 TOOL/SOURCE for the private publisher only.**
Retain prior candidates for rollback. Existing publisher
`claude-banshee-realm-client`, task `3f9392ca5d00`, owns the private feed and
uploaded identity/launch/update/rollback readback for this Linux x86-64/Python
3.11 developer kit. A queued intake is not publication or Game QA acceptance.

C1 remains PARTIAL, independent of maps. The last bounded owning summary
reports native claim-passing work and an unrun observer, with no shared-core
API defect or current P0 acceptance. Existing native jobs, source intake and
producer allowlists stay intact. **NEVER restart FFXI**, including at zero
players. No install/reload/live-action authority follows from this package.
