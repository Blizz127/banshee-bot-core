# Shared navigation measurements

`nav::metrics::measure_complete_path` measures a route supplied through the
existing Rust `Point3`/`Path` boundary. It returns endpoint projection distances,
endpoint separation and polyline length with an explicit projection outcome.
It does not run a query, move a bot, authenticate geometry or grant permission
to execute movement. Existing navigation types and adapter methods are unchanged.

The adapter supplies requested start/end points, a borrowed `Path` and an
optional maximum 3D endpoint projection distance. Invalid limits or nonfinite
requested points fail before route inspection. Only `Path::Complete` is measured;
partial, unreachable and unavailable results are refused. A complete route
must contain 2..256 finite points. No missing route or malformed point is
converted into a straight-line fallback.

The point-count limit bounds this measurement function. It does **not** specify
native query buffer capacity. Keep the native adapter's own allocation and API
requirements, and never truncate native output to make a measurement pass.

| Limit / result | `ProjectionOutcome` |
| --- | --- |
| No limit supplied | `Unassessed` |
| Both endpoint distances at or below the explicit limit | `WithinLimit` |
| Either endpoint exceeds the limit | `LimitExceeded` |

Exceeding the limit returns the measurements with `LimitExceeded`, so the
adapter can report the displacement. It is not a malformed-input error. Limits
must be finite and nonnegative; zero requires equality of the supplied endpoint
coordinates. There is no implicit epsilon or game-specific default tolerance.
Two identical route points are measurable as a zero-length route, not proof of
movement or obstacle traversal.

Coordinates are promoted from `f32` to `f64` **before subtraction**. Distances
and sums remain finite for the bounded set of finite `Point3` values, including
opposite `f32` extremes. Measurements use input coordinate units and the supplied
`Point3` values; physical units and agent calibration remain adapter evidence.
The [Python query metrics](NAV_ROUTE_METRICS.md) instead use serialized native
polyline values, whose decimal rounding can differ. These are distinct bases;
do not assert cross-tool numerical identity without accounting for that input.

The result includes requested/reported start and end, both projection distances,
their maximum, requested/reported endpoint separation, path length, point count,
represented endpoint equality, the supplied limit and its outcome. This boundary
has no corridor references or terrain flags, so it makes no polygon-count,
topology, collision, ownership or walkability claim. `WithinLimit` establishes
only the stated distance check on supplied points.

This optional pure API is architecture groundwork with no native call site.
The owning FFXI source candidate, producer allowlist, native query checks and
current P0/Game QA work remain separate. C1 has no map prerequisite and C2+
rollout is not opened. All feature defaults and operational holds persist.

## Focused evidence

VERIFIED, 2026-11-15 CST: eight new Rust integration tests pass. They cover 3D
displacements and bent polylines, both endpoint limits, exact/zero/no limit,
every noncomplete variant, nonfinite inputs, 2..256 point boundaries, and
opposite finite `f32` extremes. Command: `nice -n 19 cargo test --offline
--locked -j2 -p banshee-bot-core --test nav_metrics`.

Receipt: `~/.local/share/banshee-bot-core/evidence/nav-core-metrics-integrated-20261115-01/result.json`,
SHA256 `74db0915cf325d5dc09f10748903924c63989b2150106e7893bc9b83e3d46b54`.
All 20 current source/workspace input hashes remain stable through the check.
Existing navigation definitions are byte-identical apart from the module
declaration. Decision-module/test bytes match their separate 11-test receipt;
those tests were not replayed or aggregated into a new result.

Of the historical C1 comparison's 18 inputs, 16 remain byte-identical. Only
`brain/mod.rs` and `nav/mod.rs` gained new module exports; existing C1 primitive
implementations, feature flags, manifests and lock retain their bytes. The
earlier comparison was not replayed or presented as whole-current-crate proof.
Native platform/P0, gameplay and live navigation checks remain unrun here.
