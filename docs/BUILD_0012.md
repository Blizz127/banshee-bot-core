# Private QA candidate 0.1.0-build0012

Created **2026-11-15 04:31:39 CST**. **QA_CANDIDATE, not released.**
Build, readback and packaged startup: **PASS**. Publication has no receipt;
native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0012/banshee-bot-core-0.1.0-build0012.tar.gz` |
| SHA256 | `ba5768378c3df12b3406a4f234b2d2e738327029fb7d67102b3b11cb74a1048b` |
| Bytes | `1052951` |
| Source commit | `3d4dc8ef1ff9647c451855549cd5adaeb291a9d8` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Adds the pure [strategy-frame interface](STRATEGY_FRAMES.md). Up to 32 uniquely
identified strategies evaluate one supplied snapshot through a bounded proposal
writer. Binding priorities are fixed; unknown IDs and the global 256-proposal
limit produce sticky errors. Any preparation failure returns no partial frame.
Successful declarations freeze before optional advice, which uses the existing
decision policy without rerunning callbacks. No native call site, model request
or gameplay action is added.

VERIFIED: **eight new strategy-frame tests pass**. The fresh one-job Rust build
and archive readback pass: **120 payloads**, **13 startup calls**. The archive's
21 current core inputs and strategy test match the completed focused receipt.
Existing decision/navigation modules and test sources retain their saved hashes;
their earlier checks and native/C1 comparisons were not replayed or aggregated.

All **106 tracked source files**, build log and two Rust binaries join to the
fresh producer record. Five saved Cargo compiler invocations use its pinned
compiler path. `provenance/rust-build-manifest.json` has SHA256
`b54ed420571885a30e3f54a6e9cb35f2306349abd5d1bd295dccb05996ced9dc`.
All four packaged executables retain build0011 hashes. The new API is supplied
as original library source; this does not establish native integration.

Existing C1 primitive implementations, feature flags, manifests and lock retain
their bytes. Of the historical C1 comparison's 18 inputs, 16 are unchanged;
brain/nav module files gained exports. No whole-current-crate C1 equivalence is
claimed. Callback count/output limits do not enforce callback CPU deadlines or
undo improperly performed side effects; native execution revalidation remains
mandatory.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/strategy-frames-integrated-20261115-01/result.json` | `7c857a92b15c5594c1e67925a7aadbc9c06b6a7ae09e733949a268e54655300b` |
| `evidence/build0012-readback/result.json` | `e69f77ae40546d262149a42e5d097d577ba66a7341391c4b6ee1902e7d31dcaf` |
| `evidence/build0012-readback/source-producer-join.json` | `94ab0d357101ba45018364e0ddf524ea294643d05365fce93ef6608994d3b562` |

The bounded [04:28 readiness refresh](BOT-READINESS.md) is included. No attributed
score changes, current native P0 acceptance or bot-core publication receipt were
found in that single snapshot. New E&B visual geometry remains unverified for
native collision, flight calibration and complete-sector coverage.

**Supersedes proposed build0011 for the private publisher only.** Retain earlier
candidates for rollback. Same Linux x86-64/Python 3.11 developer tool/source-kit
contract and entry points; separate native32/native64 executables and sibling
Python metrics module. Existing publisher `claude-banshee-realm-client`, task
`3f9392ca5d00`, owns feed publication, uploaded identity and launch/update/rollback
checks. No publication follows merely from submitting this intake.

The existing FFXI 04b/shared6ead native intake remains canonical. No replacement
native worker/job/intake, producer adoption or allowlist change is proposed.
Native P0/Game QA and C2+ rollout gates persist; C1 has no map prerequisite.
**Never restart FFXI**, including at zero players. The package grants no
installation/reload authority.
