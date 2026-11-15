# Private QA candidate 0.1.0-build0013

Created **2026-11-15 05:21:48 CST**. **QA_CANDIDATE, not released.**
Build, readback and packaged startup: **PASS**. Publication has no receipt;
native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0013/banshee-bot-core-0.1.0-build0013.tar.gz` |
| SHA256 | `6895722f13eac10bdd57b76fa3f2f80b287b2744ef4a31c4b64d017116a3a47b` |
| Bytes | `1070828` |
| Source commit | `20baf49ea3a33738225a3097a997bfaef3c66f9c` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Adds an original [pure role-election helper](ROLE_ELECTION.md) and focused
comparison tooling. The core accepts adapter-supplied preferences, preserving
manual choices, Tank ranking, primary/fallback healers and per-owner Puller
selection. Game job mapping, authenticated bindings, retained facts/manual
choices, role setters, atomic clock updates and native orders remain native.
This is an additive unadopted C1 source candidate; no gameplay call site changes.

VERIFIED: **8,498 comparisons** against exact pinned pure FFXI functions pass,
along with **19 separate generic checks** and **two CLI refusal checks**. The
reference file is identical at 04b and f7c. The comparison uses a documented
minimal data/enum shim, not native World or Session code. No native P0, earlier
comparison suite or current FFXI job was replayed. Finite pure comparisons do
not establish whole-program equivalence, native adoption or gameplay acceptance.

The fresh one-job build and archive readback pass: **127 payloads** and
**13 startup checks**. All **111 tracked source files**, build log and two Rust
outputs join to the fresh producer receipt. Five saved compiler invocations use
its pinned compiler path. `provenance/rust-build-manifest.json` has SHA256
`d69d866e8cb1b64da5391cfc31f49b99e122c02815a9fb65b3da9ee6586ad04d`.
All four packaged executables retain build0012 hashes. The new helper is supplied
as original library source. External native source/reference fragments are not
in the archive.

The 22 current core inputs and original checker/driver match the completed
role receipt. Existing Role/PolicyRole definitions and strategy/decision/nav
source/test bytes retain their prior identities. Of the historical C1
comparison's 18 inputs, 15 remain unchanged; brain/nav/roles files gained module
exports. No whole-current-crate C1 comparison claim or aggregate native test
count is made.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/role-election-compat-20261115-01/result.json` | `872e5f917fd60f7867cfd650c4ce083b9426531b5d1a89676cf48d1ed709498a` |
| `evidence/role-election-refusals-20261115-01/result.json` | `7e2abef2cb4bd53f8729a637938456af3bc218953a362b63ee700d0c7cd9cef5` |
| `evidence/role-election-compat-20261115-01/scope-join.json` | `9b9b6fc43a69b09cdd1685ec7dfbd75a66b9cc49c25a73474409ebb3630a18b8` |
| `evidence/build0013-readback/result.json` | `cda54c91d3dd3bb29702401ffed1616fe8954d0dfba812968a9c2c98a17c3886` |
| `evidence/build0013-readback/source-producer-join.json` | `147e21c15a81006b56e4c2714d67b80ffeebfbea7f894aab0cb5a983d5e5055a` |

The [closed native compile update](FFXI_OFFLINE_INTAKE.md#f-closed-native-cover-compile-evidence--0514-bounded-refresh)
is separate evidence: Cover07ba compilation failed with all three selected
checks unrun, and its successor remains unaccepted in this bounded snapshot.
Those diagnostics identify no shared-core API failure. Their owning work and
the separate source-only Follow MP change were not duplicated or altered.

**Supersedes proposed build0012 for the private publisher only.** Retain earlier
candidates for rollback. Same Linux x86-64/Python 3.11 developer tool/source-kit
contract and entry points; separate native32/native64 executables and sibling
Python metrics module. Existing publisher `claude-banshee-realm-client`, task
`3f9392ca5d00`, owns feed publication, uploaded identity and launch/update/rollback
checks. A queued intake alone is not publication.

The existing FFXI 04b/shared6ead native intake remains canonical; this does not
replace it or request a duplicate native job. Role-helper adoption still needs
the owning adapter's mapping/commit review and native P0. Producer allowlists
and C2+ rollout gates are unchanged; C1 has no map prerequisite. **Never restart
FFXI**, including at zero players. This package grants no install/reload authority.
