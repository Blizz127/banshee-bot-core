# Named offline navigation probes

`scripts/probe_nav_routes.py` runs 1..32 explicit route expectations against an
exact retained collection or selected WoW map. It calls the existing verified
query wrappers, records every command and hashes the input and output evidence.
It does not build geometry, search for neighboring files, drive a bot or establish
Game QA. Python 3.11 on Linux and the target's exact native backend are required.

This supports repeatable named checks such as a direct route, a detour around a
wall and an endpoint that projects too far. Unclassified query failures remain
errors: missing polygons, disconnected regions, exhausted resources and tool
faults are not interchangeable evidence of an impassable route. Format v1 uses
the original query contract. Opt-in format v2 adds the narrow typed spatial
refusals described below; expected `blocked`/`unreachable` outcomes remain
unsupported.

## Probe data and invocation

Save the probe JSON outside Git beside other private evidence. It binds the
exact target manifest SHA-256; a changed manifest requires an explicit revised
fixture. Coordinates and limits use the target's source coordinate system.
For a collection, `units` must equal its `coordinates.units` declaration. For a
WoW selection the units remain an explicit caller declaration, not calibration.

```json
{
  "format": "bnav-route-probes-v1",
  "target_kind": "collection",
  "manifest_sha256": "REPLACE_WITH_64_LOWERCASE_HEX_DIGITS",
  "units": "synthetic metres",
  "scope": "Original two-tile floor with a seam wall",
  "limitations": ["Synthetic fixture; no game calibration or runtime QA"],
  "probes": [
    {
      "name": "wall-detour",
      "start": [-18, 0, -10],
      "end": [18, 0, -10],
      "max_projection_distance": 1,
      "expect": {
        "outcome": "complete",
        "direct_path_blocked": true,
        "min_traversed_tiles": 2
      }
    }
  ]
}
```

```sh
python3 scripts/probe_nav_routes.py \
  --probes /absolute/private/probes.json \
  --manifest /absolute/private/collection/manifest.json \
  --backend /absolute/private/bnav-recast \
  --output-dir /absolute/private/new-probe-evidence
```

The destination must be fresh, outside every Git checkout and outside the target
collection. No existing source, collection, selection or receipt is overwritten.
The runner selects a fixed sibling query wrapper from `target_kind`; the JSON
cannot name a script or provide arbitrary command arguments.

For `target_kind: "wow-selection"`, add required top-level
`"query_flags": {"include": 1, "exclude": 0}`. These are explicit 16-bit masks
passed unchanged to the existing selected-map query; the runner assigns them no
game meaning. Collection suites must omit that field. Include must be nonzero,
and exclusion must leave at least one included bit.

All shown fields are required and unknown fields are rejected. Probe names must
be unique, at most 64 characters, begin with an ASCII letter/digit and contain
only letters, digits, underscores, dots or hyphens. Each point contains exactly
three finite numbers, with absolute coordinates at most 10,000,000. Booleans are
not numbers. Every probe needs an explicit finite nonnegative projection limit;
there is no implicit calibrated tolerance. Scope and limitations remain caller
declarations and cannot upgrade target coverage or authenticity.

## Expectations and actual outcomes

`expect.outcome` is one of:

- `complete`: the native corridor is complete and both serialized endpoint
  projection distances are within the supplied inclusive limit.
- `projection_limit_exceeded`: the native corridor is complete but at least one
  serialized endpoint projects farther than that limit. This is a matched
  negative projection check, not an unreachable route or arrival proof.

`direct_path_blocked` must match the native direct-ray boolean. A wall-detour
probe can require true while still expecting a complete route around the wall.
This records the backend's navigation observation, not collision behavior in a
running game. `min_traversed_tiles` is an integer from 1 through 256 and bounds
the observed distinct tiles in the corridor from below. It cannot turn a partial
or failed query into a match.

The runner recomputes [route measurements](NAV_ROUTE_METRICS.md) from the native
polyline and the requested endpoints. Declared metrics, ABI, counts, boolean
fields, status and exit code must agree; numeric booleans cannot masquerade as
measurements. A complete path may still end at projected coordinates. The
report retains those distances and the path length in source units.

## Opt-in typed refusals in format v2

Set `format` to `bnav-route-probes-v2` to request
[`--diagnostic-refusals`](NAV_QUERY_REFUSALS.md) from the query wrapper. The
recorded backend must support native report commands. There is no fallback or
producer substitution. Existing positive/projection expectation objects remain
valid. Three additional expectations have only an `outcome` field:

```json
"expect": {"outcome": "no_complete_corridor"}
```

The other values are `start_polygon_not_found` and `end_polygon_not_found`.
These assert only the typed native condition under the loaded mesh/flag/search
policy. They cannot also assert ray observations or traversed-tile counts,
because no complete route is available. Endpoints and a projection limit remain
required; the limit is used if a complete route is returned, and no projection
distance is invented for a refusal.

A valid different observation is a MISMATCH. A malformed diagnostic, different
requested endpoint, invalid ABI/stage/budget declaration or ordinary command
failure is ERROR. `QUERY_BUDGET_EXCEEDED` is always ERROR and stops later probes;
it cannot be listed as a passing expectation. Format v1 rejects typed refusals.
The report retains the validated diagnostic and still makes no whole-world
unreachability claim.

The [typed-diagnostic verification record](NAV_QUERY_REFUSALS.md) covers v2:
17 pure tests and actual wrapper/probe runs for both ABIs pass, including an
actual path-buffer exhaustion result that remains ERROR. The historical v1
proof below retains its original build0017 source/tool scope.

## Receipts, failures and limits

The output retains byte-exact `probes.json`, an initial `requested.json`, numbered
command JSON files and stdout/stderr logs, followed by `result.json`. The result
hashes each command record, which hashes its logs. It records input paths, sizes
and hashes before/after for the suite, target manifest, backend, runner, selected
wrapper, metrics module and Python interpreter. These are local consistency
checks, not signatures or complete toolchain authentication.

The target wrapper's existing integrity check runs before and after the probe
list. Each query retains its own before/after target checks. Inputs and tools
are rechecked before every probe. The original declared source coverage and
missing-geometry limits still apply. No flag, source artifact or saved tile is
altered by a probe.

| Exit | Result | Meaning |
| --- | --- | --- |
| 0 | `MATCHED_EXPECTATIONS` | Every explicit expectation matched valid offline observations. |
| 4 | `MISMATCH` | Valid observations differed from at least one expectation; all probes ran. |
| 2 | `ERROR` | Invalid input, changed identity, integrity failure, command error, timeout, truncated output or contradictory result. Remaining probes stay `NOT_RUN`. |

Invalid input before output creation leaves no new evidence directory. Errors
after creation retain available records. A hard interruption can leave only the
request and partial logs; it is not a completed report. Mismatches do not stop
subsequent probes; an error stops further queries. Every result keeps
`game_qa: NOT_RUN`, `native_adapter_compatibility: NOT_VERIFIED`,
`calibration: NOT_VERIFIED` and `unreachable_classification: NOT_SUPPORTED`.

Each command has a 180-second wall limit and 1 MiB per output stream. Timeout
handling terminates only that invocation's process group. These bounds are not
an execution sandbox or memory quota. The runner is for the owner's selected
local tools and data. Native diagnostic limits (2048 nodes, 256 path points and
nearby-polygon extents) remain unchanged. No new geometry or producer admission
is implied by a matched suite.

## Build0017 focused verification (format v1)

Ten pure tests cover schema bounds, explicit masks/limits, both target kinds and
ABIs, outcome mismatches, malformed results, typed metrics and error isolation.
Seven archive-startup tests include the optional runner and retain legacy archive
behavior. The new runner's package smoke uses help only, without a query replay.

A small actual CLI smoke reuses the build0016 synthetic seam-wall tiles, with no
rebake or game assets. Each ABI exercises matched collection probes, a deliberate
observation mismatch, a query error with a remaining unrun probe, and a manifest
identity refusal before output. The same raw synthetic tiles are wrapped in
documented WoW containers and queried through an explicit selected-map import.
Both target modes match a wall detour, strict projection refusal and direct route.
This is evidence for the runner, not a new real-game map or native C1 result.

Receipts under `~/.local/share/banshee-bot-core/evidence/route-probes-20261115/`:

| Receipt | SHA256 |
| --- | --- |
| `pure-v1/result.json` | `e1f990cdf6981a40fefe02b2aa6e18e95f2bfc93f9e82dd6bc2f2ad7a26bfb1a` |
| `readback-v1/result.json` | `d6b02e05bc928b74c432bcd08cb39c8e6af057103ff39357232df84d8678472d` |
| `cli-v1/result.json` | `6f396493e9ae4658b19516b240d1e493ca51de0bd75906661b8fd5b8418919e7` |

The CLI smoke records 12 outer commands across both ABIs, with 15 recorded runner
commands per ABI. All source/tool/fixture pins remain unchanged. Real timeout
termination, log-budget exhaustion, filesystem faults and process interruption
were not injected. Error classification is tested with pure refusal fixtures
and an actual missing-polygon query. Game QA remains separate.
