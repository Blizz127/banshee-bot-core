# Offline endpoint projection policy

`bake_nav_collection.py query` and `import_wow_nav.py query` now report the
distance from each requested endpoint to its returned polyline endpoint. A
native complete-path result establishes a corridor between projected positions;
it does not establish arrival at the requested coordinates.

The separate opt-in [native refusal diagnostics](NAV_QUERY_REFUSALS.md) cover
queries that cannot return a complete route. They contain no invented projection
measurements and are distinct from a complete path exceeding a projection limit.

Append `--max-projection-distance 0.5`, for example, to either query command
to require each endpoint to project by at most 0.5 input coordinate units.
The threshold is caller policy, not a calibrated game default. The tools
validate it as finite and nonnegative before any backend call, including
`--version`. They apply it after native completion and retain the existing
post-query checks of backend, input and manifest identities.

| Condition | Status / exit | `within_projection_limit` |
| --- | --- | --- |
| Option omitted, valid complete native path | Existing success status / 0 | `null` |
| Both distances at or below the explicit limit | Existing success status / 0 | `true` |
| Either distance exceeds the explicit limit | `PROJECTION_LIMIT_EXCEEDED` / 3 | `false` |
| Invalid limit, malformed result or failed integrity check | Diagnostic on stderr / 2 | No success result |

The shared original module `scripts/nav_route_metrics.py` validates an explicit
native `complete: true`, 2..256 finite 3D points and an integer corridor count
of 1..256. Booleans cannot substitute for numeric fields. Derived nonfinite
distances and overflowing sums fail closed. The original native `result` is
retained alongside the new `route_metrics` object, including on a policy failure.

Measurements use the serialized polyline's first and last points consistently.
The object includes requested/reported endpoints, start/end/maximum projection
distances, requested/reported endpoint separation, the sum of segment lengths,
point count, corridor polygon count, the limit and its outcome.
`multi_polygon_corridor` means the reported count exceeds one; it does not prove
obstacle avoidance or gameplay traversal. `reported_endpoints_equal_requested`
compares the reported coordinates, not a character's position in the game.

The basis is `serialized-native-polyline`. Distances include rounding in the
native JSON representation: generated queries currently print six significant
digits; imported-map queries print nine. A zero limit therefore requires exact
equality of the represented coordinates; there is no implicit epsilon waiver.
Any optional native `snapped_start`/`snapped_end` fields remain unchanged and do
not replace this consistent measurement basis. All distances use input
coordinate units; no physical-unit, agent-size or coordinate calibration is
asserted.

This is an offline diagnostic contract. It changes neither the Rust shared
core nor native Recast/Detour code, terrain masks, producer pins or FFXI adapter
behavior. Native C1/P0 and Game QA remain independent and incomplete.

Future in-process adapters can use the separate
[Rust navigation measurements](NAV_CORE_METRICS.md). That API measures supplied
`Point3` values; this tool measures serialized JSON coordinates. Their input
precision differs, and neither establishes game movement legality.

## Focused verification, 2026-11-15 CST

VERIFIED: a fresh original synthetic floor built using the retained build0006
extractor/backend32 and was queried through both collection and synthetic WoW
wrappers. Each projected both endpoints by approximately 0.8 source units.
Omitting the limit preserved the prior status; a limit of 2 passed; 0.01
returned `PROJECTION_LIMIT_EXCEEDED` and exit 3. NaN and negative limits failed
before backend path resolution. All ten query checks passed, with source/tool
hashes unchanged. This is a new feature smoke, not a replay of platform tests.

Receipt: `~/.local/share/banshee-bot-core/evidence/nav-projection-wrappers-20261115/`
`synthetic-smoke-b_ytdxo8/run-dov1bihp/result.json`, SHA256
`75388d164cf6e8c79b496f77b1ae45ff028fba95ffcc83270f48479917ec2012`.
The fixture contains no game data. No FFXI job or game runtime was invoked.

VERIFIED separately: 19 focused pure-Python checks pass, including 3D distances,
bent paths, both endpoints, zero/exact-boundary policy, omitted policy, numeric
overflow, incomplete results and size limits. Receipt:
`~/.local/share/banshee-bot-core/evidence/nav-route-metrics-tests/run-uounrt9s/result.json`,
SHA256 `4e15bf54926eeadf19a1f04e7f2bca5c997f89ac266a51d49dcad9c902a98ac7`.
