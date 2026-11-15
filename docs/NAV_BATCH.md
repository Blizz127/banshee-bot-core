# Bounded geometry reuse for tile batches

`bnav-extract build-tiles-obj` is an opt-in offline builder for a rectangle of
**1 through 16 cells**. It validates and decodes the OBJ once, transfers canonical
geometry once, and starts one native helper that reuses that immutable geometry.
Each cell still runs the ordinary padded selection and Recast/Detour pipeline,
including its global bounds checks. Source triangle order, grid, padded borders
and raw tile format stay intact.

## Run

Use a fresh output directory under the private data root; its parent must exist.
The explicit helper must support the batch protocol. For a two-cell window:

```text
bnav-extract build-tiles-obj /absolute/path/to/bnav-recast \
  /absolute/private/geometry.obj /absolute/private/new-batch \
  0 0 0 3 40 0 1 0 0 0.5 0.2 2 0.6 0.9 45
```

Arguments after the output directory are:

```text
ORIGIN_X ORIGIN_Z MIN_Y MAX_Y TILE_CELLS X_MIN X_MAX Z_MIN Z_MAX
[CELL_SIZE CELL_HEIGHT HEIGHT RADIUS CLIMB SLOPE]
```

The optional settings use the existing defaults `0.3 0.2 2.0 0.6 0.9 45` when
omitted; supply all six to override them. These are demonstration values,
not game calibration. Origins and dimensions use the input's declared Y-up
coordinate system. `MIN_Y..MAX_Y` must contain the whole geometry, including
faces outside the requested window. Tile indices are inclusive and in
`0..4095`; tile width is `8..1024` cells. Cells are processed with X as the
outer loop and Z as the inner loop. Inverted ranges and more than 16 cells fail
before dispatching the backend.

The existing single-cell command and collection orchestrator remain available.
This batch manifest has a separate format from `bnav-collection-v1` and is
not accepted by `bake_nav_collection.py check/query`. Keep using the collection
tool for its source hashes, receipt validation and complete-collection checks.
Batch integration into that stronger collection contract is separate work.

## Outputs and completion

- `requested.json` records the requested cells as `missing`, with historical
  status `INCOMPLETE`. It remains unchanged even after success.
- `X_Z.navtile` is created exclusively for each built cell. Its bytes are the
  ordinary raw Detour payload, with no batch framing or custom navmesh container.
- `manifest.json` is created only after the complete stream, final counters,
  end-of-stream and successful helper exit have been verified. It records
  format `bnav-tile-batch-v1`, status `COMPLETE`, reference ABI, requested/built/
  empty counts, grid/settings, geometry counts and each cell's state. Built
  entries name their relative file and byte length. The same JSON goes to stdout.

Exit **0** means all requested cells were processed, including an all-empty
batch. Exit **2** means failure. Empty cells have no tile file; batch mode does
not use the individual-cell exit 3 convention. Native stderr identifies one
geometry decode, the requested cell count and each cell before its usual
selection/build diagnostics.

Output directories and files are never reused or overwritten. Invalid input,
bad framing, a truncated tile, mismatched coordinates/ABI, inconsistent footer,
trailing bytes, write failure or unsuccessful child exit prevents completion.
Any partial files and the historical request remain for diagnosis; choose a new
directory for a corrected attempt. An invalid stream stops and reaps only the
helper process spawned by this command. It does not act on a game process.
A filesystem write failure can leave a partial manifest file; acceptance also
requires exit 0 and successful file readback, not just the presence of a filename.

Manifest counts are processing evidence, not source authentication or game
coverage. This std-only front end does not add cryptographic hashes to its
manifest. Retain source/tool identities separately when using a batch as
evidence, and verify output identities before downstream adoption. Structural
tile inspection and the helper's native reload do not establish calibrated
movement, collision completeness, dynamic objects or Game QA.

## Resource and IPC bounds

Input stays at most 64 MiB of OBJ, one million vertices and one million triangles.
The native helper retains one decoded geometry and one cell result at a time;
the front end validates and writes each received cell before reading the next.
Each payload is at most 64 MiB and a batch totals at most 128 MiB. These are payload
limits, not a total process-memory limit: decoded geometry and Recast working
memory also contribute. Every existing per-cell grid/heightfield limit remains.

The private little-endian IPC stream uses four-u32 records:

| Record | Fields |
| --- | --- |
| Header | `0x54424e42` (`BNBT`), version 1, reference bits 32 or 64, cell count |
| Cell | X, Z, status, payload bytes; status 0 carries raw Detour, status 3 requires zero bytes |
| Footer | `0x444e4542` (`BEND`), cell count, built count, empty count |

Cell order must exactly match the requested rectangle; each built payload must
also carry the expected X/Z/layer 0 header. The final footer is required even for
an all-empty batch. An error may leave a valid prefix, so consumers must also
require EOF and exit 0. Native direct callers can submit 1..16 unique coordinate
pairs to `build-tiles`; the Rust front end supplies these from its rectangle.

## Measurement scope

One low-priority synthetic observation on 2026-11-15 used 32,768 triangles, of
which two contributed to each of four cells. Four extractor builds consumed
1.496237 CPU seconds; four direct-native builds consumed 1.028619. A native
intentional global-Y refusal after input parsing/validation/bounds consumed
0.241333 CPU seconds, 93.8% of the mean successful native tile CPU on this
fixture. This motivated reuse of decoded geometry before adding a spatial index.
It does not isolate parsing from validation/bounds work or imply a universal
speedup. Native bounds and candidate scans still repeat for every cell.

Baseline evidence: `~/.local/share/banshee-bot-core/evidence/tile-cost-20261115-skzmpfno/result.json`,
SHA256 `e79a6123cff278250d0bfeb538e338a625fb9991820cf3b261652414b9ca8618`.
That closed baseline is retained for the new batch comparison without replay.

The first new four-cell batch completed at the same settings with all four
tiles byte-identical to that retained baseline. It used **0.288889 CPU seconds**
and **0.372212 wall seconds**, compared with the earlier four extractor builds'
1.496237 CPU / 3.965708 wall seconds. Input/tool hashes stayed fixed; stderr
reported one decode and all four cells built. The final manifest was COMPLETE
while the historical requested inventory remained INCOMPLETE. This was one
nice19 command with no baseline replay. CPU includes the waited backend process.
Host load fell from about 185.9 to 86.7 on 48 CPUs, so elapsed ratios include
different scheduling conditions. These sparse-fixture observations establish
no general or real-game speedup.

New evidence: `~/.local/share/banshee-bot-core/evidence/tile-batch-cost-20261115-phofq9td/result.json`,
SHA256 `4d73e7f03235679ad489806755d161bb2d2640525174fd20656b1cfe5bc8842d`.
The recorded extractor is `57813bc63cc6b57155c98c80374bd1292867a8ce569f22de18644119c3909a30`,
and the backend is `551e4b79ff2e19e1184a3de663f4e5d2885ec6e81ce970bb880030c3fec65171`.

## Focused validation

**VERIFIED, 2026-11-15 06:21 CST:** the original synthetic smoke passes
**29 checks / 32 commands separately for reference32 and reference64**. A
negative-origin batch matches two retained-per-command built tiles and two
empty outcomes; its two-tile wall-detour query matches the old helper. An
all-empty default-settings rectangle covers the accepted 16-cell boundary.
Direct native duplicate/over-limit guards emit no protocol. Front-end range,
existing-output and Git-ancestor refusals dispatch no backend.

Sixteen small malformed-response cases cover header/version/ABI/count,
coordinate/status/length, truncation, footer, trailing data and child exit.
The partial-output case retains its first tile byte-exact while refusing a
completed manifest. Input, fake-response, script and tool identities remain
unchanged. The aggregate 128 MiB boundary, filesystem write faults, process
crashes and real-game integration were not exercised; no resource stress suite
was run. Separately, one ordinary `build-obj` control per ABI matches its retained
build0014 raw bytes after the native refactor, without rerunning that baseline.

Entry point, run only after a relevant change:

```text
python3 crates/bnav-extract/tests/smoke_tile_batch.py \
  --extractor /absolute/path/to/new/bnav-extract \
  --backend /absolute/path/to/new/bnav-recast \
  --baseline-backend /absolute/path/to/retained/build0014/bnav-recast \
  --output-dir /absolute/private/path/to/fresh-smoke
```

Receipts below `~/.local/share/banshee-bot-core/evidence/tile-batch-20261115/`:

| Receipt | SHA256 |
| --- | --- |
| `smoke32-v1/result.json` | `9259645221940d686fc90477b242359015005b8a8c432a2134aa6ce90d6027a9` |
| `smoke64-v1/result.json` | `a82680063560fbdc59b253fb84a15c47859df63e7ac212afa100e1b6bae6ea70` |
| `single-compat-v1/result.json` | `7eabceba0c7c17f7e89a54705c3a357167f855b009defd6a06fa2bffdc380f9a` |

Both native builds use one low-priority compiler job and complete 19 compilation
commands plus link without diagnostics. Manifests and build logs remain in
`backend32-v1/` and `backend64-v1/`; the fresh Rust build association is in
`rust-v1/manifest.json`, SHA256
`3ad973b7b9dc3bde03159ba8ac90fb057e4e1c189d097f21319622ead4c41628`.
Reference64 helper SHA256 is
`5df03d5f45f53d57f19d085793d599b03e816106a63faae430c3591be36daefe`.

No FFXI producer allowlist, shared C1 interface, game feature switch or later
rollout phase is changed by this tool. New helper hashes require their own
owning-adapter acceptance. **NEVER restart FFXI** remains in force.
