# Private QA candidate 0.1.0-build0016

Created **2026-11-15 07:23:19 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. No private publication
receipt is available; native FFXI P0 and Game QA remain **NOT_RUN**. Features OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0016/banshee-bot-core-0.1.0-build0016.tar.gz` |
| SHA256 | `1c4461e1066760ec9d766a2cd7d09b3f674ce616dc0146b481e82a26d6a8f953` |
| Bytes | `1159026` |
| Source commit | `0946e621811233eb2ba328fc03685a60df4973ea` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds **`bake_nav_collection.py bake --batch-cells N`**, N from 1 through 16.
The default individual-cell format and invocations are preserved. Explicit
batch mode uses `bnav-collection-batch-v1`: deterministic rectangular groups,
one actual command receipt per group, bound native request/result files and
per-tile hashes. A failed batch keeps its files and contributes no accepted
coverage. Complete batches must pass the existing tile/header/ABI guards and
new receipt/inventory checks before the collection can be queried. See
[collection usage and limits](NAV_COLLECTION.md).

VERIFIED: **32 checks /38 commands separately per reference ABI**. Default and
batch tiles are byte-identical; their projected two-tile wall detour is equal.
Checks cover mixed built/empty output, ragged all-empty coverage, relocation,
invalid limits, 23 tamper refusals and one failed batch retaining partial output.
Resealed metadata reaches the intended semantic guard. Six existing legacy
integrity tests also pass against the final wrapper. This does not claim later
batch failure after an earlier success, resource exhaustion, process-crash
recovery, real-game geometry or gameplay verification. No benchmark was replayed
and these functional results imply no general performance gain.

Readback verifies **139 payloads and 13 startup invocations**. A separate
packaged `bake --help` invocation verifies the new flag. All **120 tracked source
files**, build log and Rust outputs join to the fresh producer. The archived
wrapper, metrics module and smoke script match the tested identities. The
embedded verification join also hashes all 76 command receipts, which remain
external with synthetic fixtures. All **22 shared-core input hashes** retain
the prior role-comparison identity; no C1 comparison or native job was replayed.

All four executables are byte-identical to build0015 despite the fresh Rust
build. The new behavior resides in the Python collection wrapper.

| Executable | SHA256 |
| --- | --- |
| `bnav-extract` | `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30` |
| `bot-soak` | `e17985b458b79cdba36f6c4c20086d875d83edd19460decea8e2d24d947568c1` |
| `bnav-recast` (32) | `551e4b79ff2e19e1184a3de663f4e5d2885ec6e81ce970bb880030c3fec65171` |
| `bnav-recast64` | `5df03d5f45f53d57f19d085793d599b03e816106a63faae430c3591be36daefe` |

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/collection-batch-20261115/smoke32-v1/result.json` | `5255ebbcd2bfa52d934b2ddc1c37ed3d13f12b5e578950ad7fc76f753cb1b65b` |
| `evidence/collection-batch-20261115/smoke64-v1/result.json` | `ac9507ffe6b9bf213d669a0561214a75a284e198f4d458eb82dde475ff5520ff` |
| `evidence/collection-batch-20261115/legacy-v2/result.json` | `05e55dd1abb534ac696fd23502036f2b5d2e5188222bd685748b176b40c377f5` |
| `evidence/collection-batch-20261115/verification-join.json` | `d9c86e143d81cdeaea82220d1f771deb2db71e57ec660da5193b10bee64d60f7` |
| `evidence/build0016-readback/result.json` | `bf79bd2f018a0ca4114add9dbfe8deba51d38550fa6528506252ca7f97e55f50` |
| `evidence/build0016-readback/bake-help.json` | `cba43b42de213374fe4996bf44dec731b71dd375dcd56bbc52cbd09a1cbb7853` |
| `evidence/build0016-readback/source-producer-join.json` | `b865517ebe6ea19b13bd741bdb1570c6a7c6ab14220d66c82bf3384a4e79565b` |
| Embedded `provenance/rust-build-manifest.json` | `acb9c7e82bdb81aff54eaef03ff7ff11c7de48c08992bb7d772e5c70e60d61d2` |

**Supersedes proposed build0015 TOOL/SOURCE for the private publisher only.**
Retain prior artifacts for rollback. Same Linux x86-64/Python 3.11 developer kit.
Existing publisher `claude-banshee-realm-client`, task `3f9392ca5d00`, owns feed
publication and uploaded identity/launch/update/rollback checks. An intake is
not publication or Game QA acceptance.

The [07:15 native Pull report](FFXI_OFFLINE_INTAKE.md#h-reported-single-pull-diagnostic-failure--0715-bounded-refresh)
is a separate observation, with one failed diagnostic and a reported fixture
initialization cause. It supplies no current C1/P0 acceptance or shared API defect.
The coherent 04b/shared6ead C1 intake, existing native jobs and producer allowlists
remain unchanged. C1 has no map gate; C2+ stays gated. **NEVER restart FFXI**,
including at zero players. This package grants no installation/reload authority.
