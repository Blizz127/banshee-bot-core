# Private QA candidate 0.1.0-build0017

Created **2026-11-15 07:44:31 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. Publication has no
receipt; native FFXI P0 and Game QA remain **NOT_RUN**. Features remain OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0017/banshee-bot-core-0.1.0-build0017.tar.gz` |
| SHA256 | `1436afa61ec5b7c2feaf91aea60cb2424792c19c339332d221bc082296085d3c` |
| Bytes | `1168931` |
| Source commit | `5576d1eb08c2c7db270f87db55a05da20bad846b` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds the [named route probe runner](NAV_ROUTE_PROBES.md), binding 1..32 explicit
expectations to an exact retained collection or selected-map manifest. Every
probe has a projection limit and ray/tile observations. Actual commands and logs
are retained and hashed, metrics are recomputed, and mismatches are distinct
from errors. Query failures never count as unreachable/blocked expectations.
There is no game integration, geometry rebake or new producer admission.

VERIFIED: **10 pure tests**, **7 archive-startup fixture tests**, and **12 outer
CLI commands across both reference ABIs** pass. Each ABI records 15 runner
commands covering matched collection and synthetic selected-map routes, a
projection refusal, deliberate mismatch, actual missing-polygon error with a
remaining NOT_RUN probe, and wrong-manifest refusal before output. Existing
synthetic tiles were reused; no game asset, native C1 job or benchmark was run.
Timeout/log exhaustion, filesystem faults and hard interruption were not injected.

Fresh readback verifies **143 payloads /14 startup invocations**, including
packaged probe help. All **124 tracked source files**, build log and Rust outputs
join to the fresh producer. The new runner/checker/tests and unchanged wrappers
match the exact tested identities. All four executables remain byte-identical
to build0016; all 22 shared-core inputs retain their saved role-comparison pins.
Existing collection proofs retain their original scope and matching source/tool
identities; they were not replayed.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/route-probes-20261115/pure-v1/result.json` | `e1f990cdf6981a40fefe02b2aa6e18e95f2bfc93f9e82dd6bc2f2ad7a26bfb1a` |
| `evidence/route-probes-20261115/readback-v1/result.json` | `d6b02e05bc928b74c432bcd08cb39c8e6af057103ff39357232df84d8678472d` |
| `evidence/route-probes-20261115/cli-v1/result.json` | `6f396493e9ae4658b19516b240d1e493ca51de0bd75906661b8fd5b8418919e7` |
| `evidence/route-probes-20261115/verification-join.json` | `4b8ccb53237563f074c52c5d1ab483b1a0e2c8d3b2d54da77ea652754e3f36d6` |
| `evidence/build0017-readback/result.json` | `9761bfe6560fe2130cf067d76e7b747fa10d0e2dcdfddaf0c435a075b53f3e5b` |
| `evidence/build0017-readback/source-producer-join.json` | `ca0a113cd50a03f2aedd9c30aeb85fbf9fccbd8effd3691d3dc100c7fa78579a` |
| Embedded `provenance/rust-build-manifest.json` | `6d0c6fb3baeeb10433aeba3d0c8c782f4271fb922ced9c0e971f04e41d1e0c20` |

**Supersedes proposed build0016 TOOL/SOURCE for the private publisher only.**
Retain old artifacts for rollback. This is a Linux x86-64/Python 3.11 developer
kit; the existing publisher `claude-banshee-realm-client`, task `3f9392ca5d00`,
owns feed publication and uploaded identity/launch/update/rollback readback.
A queued intake is not publication or Game QA acceptance.

The [07:42 owning native summary](FFXI_OFFLINE_INTAKE.md#i-reported-native-claim-passing-gap--0742-bounded-refresh)
is separate: a claim-passing port gap is reported, with observer compiler/tests
UNRUN. No new C1/P0 acceptance or shared-core defect is identified. Existing
native jobs, coherent 04b/shared6ead intake and producer allowlists stay intact.
C1 has no map gate and C2+ stays gated. **NEVER restart FFXI**, including at zero
players; this package grants no install/reload or live-action authority.
