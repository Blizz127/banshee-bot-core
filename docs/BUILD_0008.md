# Private QA candidate 0.1.0-build0008

Created **2026-11-15 03:18:04 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. Publication has no
receipt; native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0008/banshee-bot-core-0.1.0-build0008.tar.gz` |
| SHA-256 | `5c800fe7bab050053cc1d96e35f9e90795fa31d41aa0a63b40d3eb21c2c8ac0b` |
| Bytes | `1011108` |
| Source commit | `71fdbc3eb6674dadb904919fd9f9447238b168b3` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Retains build0007's [endpoint projection policy](NAV_ROUTE_METRICS.md), and
automates packaged query-wrapper imports/help in the [archive checker](BUILD_READBACK.md).
Only fixed Python entry points run, after complete archive/sidecar verification.
Missing required imports fail startup; legacy candidates remain supported.
Shared Rust and native Recast/Detour bytes are unchanged.

VERIFIED: all **103 payloads** and **13 packaged invocations** pass, including
four Python startup checks. Six focused synthetic checker cases pass, covering
packaged imports, fixed extraction paths, missing modules, ignored PYTHONPATH,
late corruption before execution, legacy support and missing query options.
The earlier ten synthetic projection outcomes and 19 metrics tests remain
separate completed checks, with identical packaged source bytes. No native
platform job, C1 comparison or game query was replayed for this increment.

The archive's 18 core/workspace files match the completed `ffxi-5c73a875`
comparison. Three projection sources and two checker/test sources match their
completed receipts. Native authority-only adoption remains separately observed
at 756eb165; it does not establish remaining adapter/P0 or Game QA acceptance.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA-256 |
| --- | --- |
| `evidence/build0008-readback/result.json` | `cad796eed48247cc6336f25ade7a6b03661466c8e38636e19aa0fe2cfc00061e` |
| `evidence/build0008-readback/source-evidence-join.json` | `3ea831c6db92a27648485713ee0bb58ea0ee19aeddc5b732ace0a727a138ff31` |
| `evidence/build-python-readback-tests/integrated-20261115/result.json` | `55619ca5f855075812424ef0c400c546d79b9c8d4a5851b418670cbce21321de` |

**Supersedes proposed build0007 for the existing private publisher only.** Keep
all earlier artifacts for rollback. Same Linux x86-64/Python 3.11 developer tool
contract and entry points as [build0007](BUILD_0007.md); keep the shared metrics
module beside the query wrappers. Route through existing coordinator task
`dcc9a63a40ab` to publisher `claude-banshee-realm-client`, task `3f9392ca5d00`,
for its private channel, uploaded identity, launch/update and rollback checks.
The FFXI source/adoption intake is unchanged; no duplicate native request.

Physical calibration, whole-zone maps, live bot soak and Game QA remain pending.
No client assets or maps are packaged. **Never restart FFXI**, including at
zero players; the manifest grants no installation/reload authority.
