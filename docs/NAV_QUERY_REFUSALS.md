# Explicit native query refusal diagnostics

The optional native commands `query-report`, `query-tiles-report` and
`query-map-report` take the same arguments as `query`, `query-tiles` and
`query-map`. Successful JSON and exit 0 remain the same. The existing commands
retain their original error text and exit 2; they never silently change to the
new diagnostic protocol.

Only the new commands return a typed refusal as JSON with exit 3. Invalid files,
ABI or grid disagreements, missing selected tiles, initialization failures and
other unclassified errors remain stderr/exit 2. An error message alone is never
converted into evidence that a route is blocked.

```json
{
  "format": "bnav-query-refusal-v1",
  "complete": false,
  "reference_bits": 32,
  "reason": "NO_COMPLETE_CORRIDOR",
  "stage": "find_path",
  "node_limit": 2048,
  "path_limit": 256,
  "nearest_extents": [2, 4, 2]
}
```

| Reason | Stage | Observed native condition |
| --- | --- | --- |
| `START_POLYGON_NOT_FOUND` | `nearest_start` | Nearest-polygon call succeeded but found no start polygon within the existing extents and flag policy. |
| `END_POLYGON_NOT_FOUND` | `nearest_end` | Start resolved; nearest-polygon call succeeded but found no end polygon. |
| `NO_COMPLETE_CORRIDOR` | `find_path` | Detour returned a successful, nonempty corridor ending at a different polygon, without either query resource flag. |
| `QUERY_BUDGET_EXCEEDED` | `find_path` or `straight_path` | The path query reports node/buffer exhaustion, or the straight-path query reports a full output buffer. |

The resource checks take precedence over a partial corridor. A truncated path
therefore cannot masquerade as disconnected geometry. Failed or empty path
results without those flags remain errors. Failed nearest-polygon calls remain
errors rather than missing-polygon diagnostics. No query/node limit, filter,
endpoint, loader or geometry rule changes.

These observations concern only the loaded mesh, selected polygon flags and
fixed nearby-search extents. A missing polygon can reflect incomplete coverage
or the chosen coordinate frame. No complete corridor in a selected region does
not establish that every route in the game world is unavailable. These are not
dynamic collision, physical calibration, player movement or Game QA results.

## Collection and selected-map wrappers

Add `--diagnostic-refusals` to the existing wrapper's `query` command to use the
corresponding native report command. The exact backend identity recorded by
the collection or selection must still match; this option is not permission to
substitute a new binary into an older map receipt. The wrappers do not retry an
unsupported command against another backend or weaken identity checks.

The wrapper validates the closed diagnostic schema, reason/stage pair, ABI and
fixed limits. It rechecks the same map and backend identities after a refusal
as after a successful query. A valid refusal is reported as `QUERY_REFUSED`,
with `diagnostic`, the requested endpoints, existing coverage/context and
`game_qa: NOT_RUN`, returning exit 3. It contains no fabricated route metrics.
Malformed/truncated diagnostics remain errors.

Exit 3 already represents `PROJECTION_LIMIT_EXCEEDED` for a complete projected
path. Consumers must inspect the explicit `status`; these two outcomes are not
equivalent. Omitting the new option preserves the prior CLI behavior.

## Named probes

[Probe format v2](NAV_ROUTE_PROBES.md) opts into report commands and can match
the three spatial refusals using their explicit codes. Budget exhaustion is
always an error, never an expected spatial refusal. Probe format v1 continues
to use the original query commands. Neither format infers global unreachability.

## Implementation and verification boundary

The bridge classifies the existing Detour return status and polygon reference;
it does not parse error text or catch arbitrary exceptions as spatial failures.
Legacy commands still reach the original outer error handler. Only the report
commands consume the typed exception and serialize the closed diagnostic record.
The producer hash changes with this bridge increment. Existing game producer
allowlists and native integration remain owned by their server leads.

VERIFIED locally, 2026-11-15 CST: both reference ABIs pass **21 checks /33 native
commands**, including exact legacy exit/stdout/stderr equality, unchanged success
JSON in report mode, missing endpoints, disconnected islands through all three
query modes, malformed tiles, a wrong ABI and a missing selected tile. The
original 300-quad fixture proves a full 300-polygon route with capacity 512 and
buffer exhaustion with capacity 256, without node exhaustion. Production report
mode classifies that truncation as a budget error before considering connectivity.

The actual wrapper/probe smoke passes **18 outer commands across both ABIs**,
with 16 runner commands per ABI. New synthetic island collections and selected
imports match complete/projection and all three spatial expectations. Legacy
default success agrees with report mode and a missing endpoint still produces
the original exit-2 error. The actual long-corridor budget result stops a v2
probe list with ERROR and a remaining NOT_RUN probe. Seventeen pure tests cover
the schema, type guards, v1 compatibility and refusal assessment.

All native dependency inputs and compiler flags match the retained baseline;
only the original bridge source changes. These are scoped comparisons, not a
claim of equivalence for every input or producer admission. Node exhaustion,
straight-path buffer exhaustion, filesystem faults and resource termination
were not separately injected. No native FFXI/P0 or Game QA check ran.

Receipts beneath `~/.local/share/banshee-bot-core/evidence/query-refusals-20261115/`:

| Receipt | SHA256 |
| --- | --- |
| `backend-scope-join.json` | `57624f6b377433bf228f211cca4fb392bf39b12b95946e15644b030163e9ff49` |
| `pure-v1/result.json` | `57b246d1e2faa2fad477f9bf49b447ac214ff9059098ec462aeb04eabd0a3640` |
| `native32-v1/result.json` | `2d40af6e97f815164017ac0f391be701ade79cc3f6c053289ff4f758625a9423` |
| `native64-v1/result.json` | `55a091e517d254f4e5ebc7aa9f3a5f022c9df7e59d881235ac360f96438ee3e8` |
| `corridor32-v1/result.json` | `fa0883e5c63ca2cd4ef2b3c5989637629a0709a9190d0f3f7aba9da0efbc066b` |
| `corridor64-v1/result.json` | `21284a284b4ea2f67b2df2e95b219ccb852d91da029fe3ce612ae8d5112549e6` |
| `wrapper-v1/result.json` | `8e0ab08f75bb02d1e7c55d1a6df3c48af3e249c3225d40432d3b0524a56cde25` |

Source, commands, compiler evidence, generated fixture data and all partial
outputs remain private. Only original source/test code enters Git.
