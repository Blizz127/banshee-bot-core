# bot-soak telemetry groundwork

Status: **PARTIAL**. This is an offline validator and summary tool. It does not
spawn headless sessions, drive a server, or establish C3 Game QA. The owning game
adapter must run the bots in process and export its measurements. No server,
client, network protocol, or other project's repository is touched by this tool.

All implementation here is original Rust using only the standard library. There
are no third-party runtime dependencies or imported game data. The checked-in
example and test inputs are synthetic.

## Run

```sh
cargo build -p bot-soak -j2
target/debug/bot-soak --help
target/debug/bot-soak replay crates/bot-soak/examples/synthetic-short.csv --zone 100
```

The example returns **3 (INCOMPLETE)**: it is synthetic and covers only two
seconds. It is a startup smoke, never an hour-long server soak. Keep real captures
outside git, under `~/.local/share/banshee-bot-core/evidence/`.

For an adapter's recording:

```sh
target/debug/bot-soak replay /absolute/private/path/soak.csv \
  --zone 100 --expected-bots 20 --tick-budget-ms 50
```

The tick budget is a configurable validation threshold, not a claim that any
particular server can meet it. `--min-duration-secs` defaults to 3600 and may only
increase. `--max-gap-ms` defaults to 1000 and may only decrease to a positive
integer. `--max-abs-currency-drift` defaults to zero and uses integer game currency
units. All effective policy values are printed with the report.

## CSV v1 contract

The first line must exactly match this unquoted header:

```csv
source,tick,elapsed_ms,zone_id,bots,tick_ms,cpu_percent,rss_bytes,stuck_bots,deaths_total,bot_currency_units,human_target_conflicts_total
```

Each following line has exactly twelve columns. LF and CRLF are supported. There
are no comments, quoting, blank rows, or extra columns. A missing optional metric
is an empty field, not zero or NaN. Limits are 4096 bytes per line and 10,000,000
completed ticks. The file is streamed; tick durations are retained for exact p95.

| Column | Meaning |
| --- | --- |
| `source` | `adapter` or `synthetic`, constant throughout the file. `adapter` is a declaration, not authentication. |
| `tick` | Recording-local sequence: baseline 0, then 1, 2, 3, with no gaps. |
| `elapsed_ms` | Monotonic milliseconds since the baseline; baseline 0, then strictly increasing. |
| `zone_id` | Unsigned 32-bit game-adapter zone identifier, constant and matching `--zone`. |
| `bots` | Unsigned 32-bit headless bot count actually present in that zone, constant throughout the run. Must match the requested load to qualify. |
| `tick_ms` | Finite, nonnegative server tick execution duration in milliseconds. Baseline must be 0. |
| `cpu_percent` | Optional measured server-process CPU over the preceding interval; 100% means one fully occupied logical core, so values over 100% are valid. Baseline is ignored and should be empty. |
| `rss_bytes` | Optional positive server-process resident memory in bytes, including the baseline. Zero means invalid data, not an unavailable sample. |
| `stuck_bots` | Optional current count, no greater than `bots`. The adapter defines and records its stuck criterion in accompanying evidence. |
| `deaths_total` | Optional cumulative bot deaths. Nondecreasing, even across missing observations. Baseline need not be zero. |
| `bot_currency_units` | Optional nonnegative sum of bot-only currency in the cohort, in the game's integer units. Baseline, final delta, and maximum absolute deviation are reported. |
| `human_target_conflicts_total` | Optional cumulative attempts to claim or steal a human's target, including attempts blocked by guards. Nondecreasing; adapter instrumentation and human-target definition belong in accompanying evidence. |

The baseline captures counters and gauges before the measured period. Every
subsequent row represents one completed server tick. The baseline contributes
no tick or CPU sample, but its RSS/stuck/currency values are real gauge samples.
Clock resets, counter resets, source/zone/load changes, nonfinite numbers,
negative values, impossible counts, malformed rows, and sequence gaps are input
errors. A long elapsed span with sparse observations cannot qualify: adjacent
timestamps must stay within the configured gap limit. Export must flush the last
completed tick rather than append a timestamp-only end marker.

Metrics are always supplied by the recording. The tool never reports the replay
process's CPU or RAM as game-server measurements. Tick p95 is the nearest-rank
95th percentile of completed ticks. Mean and maximum CPU/RSS are computed from
available observations; their sample and missing counts are printed. CPU/RSS
means are observation means, not time-weighted integrals.

Death and human-conflict deltas subtract the baseline from the final counter.
Missing endpoints produce `UNKNOWN`; missing interior observations still make the
recording incomplete. Counter decreases are detected across missing rows. A
reported violation before a missing final observation remains a failure. Currency
uses overflow-safe integer differences and checks the largest deviation from the
baseline, including excursions that return to zero at the end. This measures
cohort currency drift only; it does not verify auction prices, price floors,
listing age, bot-only ownership, or the full economy policy.

## Verdicts and exit status

| Exit | Verdict | Meaning |
| --- | --- | --- |
| 0 | `TELEMETRY_PASS` | Declared adapter recording covers at least one hour with continuous samples, expected bots and zone, all required metrics, and all configured checks satisfied. |
| 2 | Input/usage error | The recording or command is invalid; no success report is printed. |
| 3 | `INCOMPLETE` | Valid recording, but synthetic source, short/sparse coverage, wrong requested load, or missing metrics prevents qualification. |
| 4 | `FAIL` | A recorded tick exceeded the budget, a bot was stuck or died, a human-target conflict occurred, or currency deviation exceeded the limit. Known failures take precedence over incompleteness; both reasons are still reported. |

Every report includes `live_game_qa=NOT_RUN` and
`recording_authenticity=NOT_VERIFIED`, even on `TELEMETRY_PASS`. A CSV declaration
cannot prove that the run happened, the adapter measured correctly, or that game
behavior was safe between samples. Game QA still owns the real client/server
verdict and feature-enable decision. This tool imposes no server CPU or memory
budget yet; those metrics are reported for the owning lead to assess.

## Adapter integration still required

The additive [`recording` writer](BOT_SOAK_RECORDING.md) supplies typed streaming
CSV export for adapter observations. It shares the replay row validator and
never generates clocks, tick indices or process measurements. Invalid samples
and output failures permanently close that writer. This is source groundwork;
no native adapter has adopted it and no live capture follows from its presence.

The server lead must supply the headless runner, constant N-bot cohort in one
zone, tick/counter instrumentation, a monotonic recording clock, process metric
collection, and private provenance (server build, feature flags, map identity,
instrumentation definitions, start/end times in CST). No live run has been
performed for this groundwork. Respect real-player protection and the owner's
deployment/backup rules in the owning repository. Do not enable population bots
or claim C3 completion from a local replay alone.

Focused validation command: `nice -n 19 cargo test -p bot-soak -j2`. Tests cover
the one-hour boundary, missing/sparse/synthetic data, baseline exclusion, CPU
values over 100%, transient currency drift, human conflicts, malformed inputs,
counter resets across missing observations, and percentile/budget behavior.
