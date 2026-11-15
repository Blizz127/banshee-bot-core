# Private QA candidate 0.1.0-build0009

Created **2026-11-15 03:47:31 CST**. **QA_CANDIDATE, not released.**
Build, readback and packaged startup: **PASS**. Publication has no receipt;
native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0009/banshee-bot-core-0.1.0-build0009.tar.gz` |
| SHA256 | `8a07a58e4de0f124ca24d5c9bcc1a9b294a3308f6f976ed8d6eab83bd8ce5bf4` |
| Bytes | `1022615` |
| Source commit | `9b91ed21eec457d1273ee685fcf0916865ec8700` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

Adds the pure [shared decision policy](DECISION_POLICY.md): bounded legal-action
selection, hard strategy priorities and restricted optional advice. Invalid or
stale advice retains a deterministic fallback. There is no native call site,
LLM/network invocation or gameplay mutation; frame/action IDs grant no authority.

VERIFIED: 11 focused new policy tests pass. All **107 payloads** and **13 packaged
startup invocations** pass. The archive's 19 current core inputs and policy test
match that completed receipt. The earlier C1 comparison is retained for its
exact source: 17 of its 18 inputs remain byte-identical; `brain/mod.rs` adds only
the new module export. Existing C1 primitive implementations, feature flags,
Cargo manifests and lock are unchanged. No whole-current-crate equivalence or
new native C1 acceptance is claimed, and no native test was replayed.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/decision-policy-20261115-01/result.json` | `a49f7f8b3ff8a22bb2a4fd44ee981cc7bdae2991129c66889508abb7d6ec2fa1` |
| `evidence/build0009-readback/result.json` | `a33aa8ff61fa398919583f4d57ac22e678699dfca7ba9ddf5390a766f20bba4b` |
| `evidence/build0009-readback/source-evidence-join.json` | `337df689aad2cfecb01c80b0c2225712f3266aae0322e51709b66b9cc7e87d52` |

**Supersedes proposed build0008 for the private publisher only.** Keep earlier
candidates for rollback. Same Linux x86-64/Python 3.11 developer tool/source-kit
contract and entry points; native32/native64 remain distinct unchanged binaries.
Keep the metrics module beside both Python query wrappers. Existing publisher
`claude-banshee-realm-client`, task `3f9392ca5d00`, owns the private feed,
uploaded identity, launch/update detection and rollback checks.

The owning FFXI 04b/shared6ead source candidate stays canonical; this is not a
replacement native intake. Original e519 failures/current P0 and Game QA remain
with that lane. C2+ is not opened, C1 has no map prerequisite, and the producer
allowlist is unchanged. **Never restart FFXI**, including at zero players.
The manifest grants no installation/reload authority.
