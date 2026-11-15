# Private QA candidate 0.1.0-build0015

Created **2026-11-15 06:24:27 CST**. **QA_CANDIDATE, not released.**
Build, archive readback and packaged startup: **PASS**. Publication has no
receipt; native FFXI P0 and Game QA remain **NOT_RUN**. Features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0015/banshee-bot-core-0.1.0-build0015.tar.gz` |
| SHA256 | `7c8b21b540123f23462b62c7c60901bdb78833d262f0f81a540c6ed55ad93029` |
| Bytes | `1136790` |
| Source commit | `73cd8da930137278bdf2cf7a2b6028f2ccb6ce04` |
| Manifest/checksum | Adjacent `manifest.json` and `SHA256SUMS` |

Adds opt-in [bounded tile batches](NAV_BATCH.md). The Rust front end decodes
OBJ once and transfers geometry once to a native helper, which reuses it for
up to 16 cells. Per-cell Recast work and source order remain intact. Output
frames, raw tile headers, footer, EOF and child status are validated before a
final manifest is written. Failures retain partial output and the historical
request. The existing single-cell command and collection format are unchanged;
the new batch manifest is a separate contract without source/output hashes.

VERIFIED: **29 checks / 32 commands separately per reference ABI** pass, including
mixed built/empty cells, a two-tile wall query, the 16-cell upper boundary,
front-end/native guards and 16 malformed-stream cases. One ordinary single-tile
control per ABI matches retained build0014 bytes after the native refactor.
No old baseline was rebaked for those controls. Aggregate 128 MiB exhaustion,
filesystem fault injection, process crashes and gameplay were not exercised.

A separate single four-cell observation uses **0.288889 CPU seconds**, compared
with the retained separate-build baseline's **1.496237 CPU seconds**. All four
tile bytes match. This deliberately sparse synthetic fixture has 32,768 triangles;
host load changed between observations. It establishes no general or real-game
performance gain. The baseline was not replayed; [the batch notes](NAV_BATCH.md)
retain timing methodology, limits and exact receipts.

Fresh packaging/readback passes **138 payloads** and **13 startup invocations**.
All **118 tracked source files**, log and Rust outputs join to the fresh producer.
The packaged extractor, both backends and original smoke script match the tested
identities; the cost observation uses that same extractor and reference32 helper.
Bot-soak remains byte-identical to build0014. All **22 shared-core input hashes**
retain their saved role-comparison identity, with no core/native C1 test replay.
Synthetic geometry, generated tiles, fake backends and game data stay external.

| Executable | SHA256 |
| --- | --- |
| `bnav-extract` | `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30` |
| `bnav-recast` (32) | `551e4b79ff2e19e1184a3de663f4e5d2885ec6e81ce970bb880030c3fec65171` |
| `bnav-recast64` | `5df03d5f45f53d57f19d085793d599b03e816106a63faae430c3591be36daefe` |

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA256 |
| --- | --- |
| `evidence/tile-batch-20261115/smoke32-v1/result.json` | `9259645221940d686fc90477b242359015005b8a8c432a2134aa6ce90d6027a9` |
| `evidence/tile-batch-20261115/smoke64-v1/result.json` | `a82680063560fbdc59b253fb84a15c47859df63e7ac212afa100e1b6bae6ea70` |
| `evidence/tile-batch-20261115/single-compat-v1/result.json` | `7eabceba0c7c17f7e89a54705c3a357167f855b009defd6a06fa2bffdc380f9a` |
| `evidence/tile-batch-cost-20261115-phofq9td/result.json` | `4d73e7f03235679ad489806755d161bb2d2640525174fd20656b1cfe5bc8842d` |
| `evidence/build0015-readback/result.json` | `b96ee42234727041b75b104309b8f567620107717bf7353ae36bc2c40353e393` |
| `evidence/build0015-readback/source-producer-join.json` | `5902d4c0b64978cf3f41831733517bf0f7a4fe1c5d11a66ffbe0e54c2f3a76fa` |
| Embedded `provenance/rust-build-manifest.json` | `961301e05827f7675ce48b8bf3796c8fd65c947b44f8847d7e85a3654bc26b0a` |

**Supersedes proposed build0014 for the private publisher only.** Retain prior
artifacts for rollback. Same Linux x86-64/Python 3.11 developer tool/source kit,
with an additive CLI command and separately identified native32/native64 helpers.
Existing publisher `claude-banshee-realm-client`, task `3f9392ca5d00`, owns feed
publication and uploaded identity/launch/update/rollback checks. Queuing an
intake is not publication or Game QA acceptance.

The [06:23 native report](FFXI_OFFLINE_INTAKE.md#g-reported-native-four-check-compile-failure--0623-bounded-refresh)
is separate: native compilation failed and all four selected checks were unrun.
Its reported test-only correction does not identify a shared API defect or prove
acceptance. Existing 04b/shared6ead C1 intake, native jobs, producer allowlists
and all holds remain unchanged. No new producer adoption is requested. C1 has
no map prerequisite; C2+ stays gated. **NEVER restart FFXI**, including at zero
players. This package grants no installation or reload authority.
