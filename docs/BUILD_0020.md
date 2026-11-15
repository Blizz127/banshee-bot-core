# Private QA candidate 0.1.0-build0020

Created **2026-11-15 08:46:32 CST**. **QA_CANDIDATE, not released.**
Focused shared-brain checks, build and archive startup: **PASS**. Publication has
no receipt; native FFXI P0, Game QA and model-service integration are **NOT_RUN**.
Feature switches remain OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0020/banshee-bot-core-0.1.0-build0020.tar.gz` |
| SHA256 | `e69e6821415a1a4652a23e35bc695122c7853f2f4557869c744d8acadc7340b1` |
| Bytes | `1199906` |
| Source commit | `c8d44b9085412ad01c174ab25e533246556371da` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds the original [shared advice window](ADVICE_WINDOW.md) around a frozen
strategy frame. Safety/owner/no-choice decisions are immediate. Optional ordinary
ties can await a ranking without blocking, with an explicit inclusive deadline,
stale-reply handling and deterministic fallback on invalid advice or model
failure. Cancellation and clock regression discard the frame; each window
returns at most one intent. It starts no timer, thread, model call or game action.

The adapter must cancel stale work on world/order/ownership changes, route
replies to the correct bot/session/frame and revalidate legality before execution.
A deadline does not refresh game facts. This is an unadopted shared interface;
existing native C1 primitives and the coherent 04b/shared6ead candidate are
unchanged. C1 has no advice or navigation prerequisite, and C2+ stays gated.

VERIFIED: **eight focused integration tests** pass, using the existing strategy
preparer and selector. They cover immediate decisions, matching/invalid/stale
rankings, exact/late/zero deadlines, unavailability, one-result consumption,
cancellation, equal/regressing time and overflow. Source/toolchain hashes stayed
stable and compilation emitted no warnings. One compiler job was used under
measured host pressure. No earlier C1/native comparison or routine full suite
was replayed.

Archive readback passes **151 payloads /14 startup invocations**. All **137
tracked source files**, build log and Rust outputs join the fresh producer;
all **30 focused core input hashes** match the tested source. Of the prior
22-input role-election snapshot, 21 retain their exact bytes; `brain/mod.rs`
adds only this module's export. Existing C1 primitive, flag, selector and strategy
implementations remain unchanged. This does not broaden historical C1 evidence.

All four tool executable hashes are unchanged from build0019. Navigation,
telemetry and packaging-tool source also retain their bytes. The new functionality
is delivered as shared-library source for owning adapters, not as an installed
server change or a new model service.

| Executable | SHA256 |
| --- | --- |
| `bin/bnav-extract` | `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30` |
| `bin/bnav-recast` | `b7c1475b2558ae3362c9deef11e277b382c1a4232f404b161f8a91e80e90732d` |
| `bin/bnav-recast64` | `d378b4a865926c49e28a7b55b639a2839cef5fe328ac6891da582d77d3bdde6f` |
| `bin/bot-soak` | `cb7f2fca48511f69b2823dc5286df5e54bc39200202ee78eff10de7a32ea382a` |

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/advice-window-20261115-01/result.json` | `29294bcafdf862571f4dedf7f6024b82288349b8a315ee9f06459dc820689bb6` |
| `evidence/build0020-readback/result.json` | `db47b8fdc1df924cb710324e08dc5f3c6a0bb5b14077545ac4158fac6a69592b` |
| `evidence/build0020-readback/source-producer-join.json` | `73d2537e9dce7e8ccca87e992c69d94efd7181d08da5a8e10656ec256e5b4b08` |
| `evidence/c1-metadata-refresh-20261115-084242cst/delta-summary.json` | `6de885aa5b4e817418496e43bef079a00c75097be3335a820c3bdf08baa05dae` |
| Embedded `provenance/rust-build-manifest.json` | `a1b8f7ece0cd77ee01b3133db06bac65a779576d8530177a27c3a37a82b19623` |

**Supersedes proposed build0019 TOOL/SOURCE for the existing private publisher
only.** Retain older artifacts for rollback. Publisher
`claude-banshee-realm-client`, task `3f9392ca5d00`, owns the feed, upload identity
and launch/update/rollback readback for this Linux x86-64/Python 3.11 developer
kit. A queued intake is not publication or Game QA acceptance.

The one new 08:42 CST owning-summary observation reports scoped rc186/08ed
Pull1 PASS, OFFLINE/UNSEALED, separately from native7 compile failure/all seven
checks NOT_RUN. It supplies no full C1/P0 or shared-core repair request. No
native job, terminal, source/test body or old packet was opened or duplicated.
**NEVER restart FFXI**, including at zero players. No install/reload/live-action
or model-service authority follows from this package; all holds persist.
