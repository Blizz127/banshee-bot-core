# Private QA candidate 0.1.0-build0019

Created **2026-11-15 08:17:23 CST**. **QA_CANDIDATE, not released.**
Build, focused writer/replay checks and packaged startup: **PASS**. Publication
has no receipt; native FFXI P0 and Game QA remain **NOT_RUN**. Features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0019/banshee-bot-core-0.1.0-build0019.tar.gz` |
| SHA256 | `aa9768571bbd9b595e54489394a59b8500f648ce1fd3e984d6fe259e2e357271` |
| Bytes | `1192411` |
| Source commit | `43b214567c1a7a8ddf19b33fa2f1a0ae91cf36cc` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds the original [typed telemetry writer](BOT_SOAK_RECORDING.md) for adapters:
explicit supplied samples, shared replay row validation, preserved missing
metrics and policy failures, and permanent input/output failure handling.
The included Rust example writes two seconds of synthetic observations. No clock,
process measurement, file, session, bot or game action is created by the writer.
This is source groundwork for owning adapters, not a live headless runner.

VERIFIED offline: **11 new writer tests and six existing replay tests** pass.
Tests cover synthetic round trips, strict input/sequence checks, counters across
missing observations, numeric extremes, partial writes and flush failures. The
example emits actual CSV that the CLI accepts as **INCOMPLETE / exit 3**.
An example-only unused-lock warning was corrected; its build and smoke were
repeated with identical output, without replaying unchanged tests. The packaged
release CLI separately consumes that same output with an identical report.

Archive readback passes **148 payloads /14 startup invocations**. All **133
tracked source files**, build log and Rust outputs join the fresh producer. The
writer and tests match their executed source; the example matches its corrected
smoke. Replay implementation is unchanged except its module export. All **22
shared-core input pins** and navigation source/tooling remain unchanged. Native
navigation checks and C1 comparisons were not replayed.

| Executable | SHA256 |
| --- | --- |
| `bin/bnav-extract` | `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30` |
| `bin/bnav-recast` | `b7c1475b2558ae3362c9deef11e277b382c1a4232f404b161f8a91e80e90732d` |
| `bin/bnav-recast64` | `d378b4a865926c49e28a7b55b639a2839cef5fe328ac6891da582d77d3bdde6f` |
| `bin/bot-soak` | `cb7f2fca48511f69b2823dc5286df5e54bc39200202ee78eff10de7a32ea382a` |

Only `bot-soak` binary identity changes. All three navigation executables retain
their build0018 identities; no producer allowlist or native adoption changes.
No native FFXI/P0, Game QA, live recording or server integration ran. Writer tick
limit exhaustion, sink panics and real filesystem failure/durability remain
unexercised; synchronous sink timing on a game thread remains unmeasured.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/soak-recording-20261115-01/result.json` | `db4553657ffec6df1bbadcffd36374ccbecfaf63a95e28457d19c6b760a13a99` |
| `evidence/soak-recording-20261115-01/example-v2/result.json` | `b1f258bad51f8b45b50ac2f83735e615231e7803263afddbca00b1ba569593f9` |
| `evidence/soak-recording-20261115-01/scope-join.json` | `28353b88c3b3aabd4470d08cff6d2410e21777b6991c3ea13aac349046e27551` |
| `evidence/build0019-readback/result.json` | `66c0e4f8f980a49eff29985c1bb3160a589ab12ce96416cdba78d0352b769342` |
| `evidence/build0019-readback/source-producer-join.json` | `c0d1ef3121b7e8ad8f729a8868dfde929aa4e94b792743df182a47e8670a7d85` |
| `evidence/build0019-readback/writer-release-replay.json` | `7891602785280e891a683733bab5753cd69520e25b02be6fc1a31dae4e55566d` |
| Embedded `provenance/rust-build-manifest.json` | `84cf167333538a15edb1c6a48f882082fcfbfb81f2a2562515f118ca3b30ba55` |

A post-readback join summary initially used `len` on an integer count; its error
record is retained. Correcting only summary construction produced the join above;
no source, tests, native command or archive readback was repeated for that error.

**Supersedes proposed build0018 TOOL/SOURCE for the existing private publisher
only.** Retain earlier artifacts for rollback. Publisher
`claude-banshee-realm-client`, task `3f9392ca5d00`, owns the feed, upload identity
and launch/update/rollback readback for this Linux x86-64/Python 3.11 developer
kit. A queued intake is not publication or Game QA acceptance.

The one 08:12 owning-summary snapshot reports native compile success with Pull
behavior counts still unknown/running; the separately retained parent 0bc
failure remains separate. No shared-core repair is requested. C1 remains PARTIAL
and independent of maps. Current native jobs and the coherent 04b/shared6ead
source intake are unchanged. **NEVER restart FFXI**, including at zero players.
No install/reload/live-action authority follows from this package.
