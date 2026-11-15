# Adapter telemetry recording

`bot_soak::recording::{RecordingWriter, Sample, RecordError}` provides the shared
CSV writer for in-process adapters. It accepts observations, writes the existing
[CSV v1 format](BOT_SOAK.md), and stops on invalid input or output failure.
It does not run a server, spawn bots, read a clock or collect process metrics.
It adds no native FFXI call site and does not advance the C1/P0 or C3 gates.

## Usage

Create a `Sample` containing the producer's observed source, sequence, elapsed
time, zone, cohort count and optional metrics. Construct
`RecordingWriter::new(sink, baseline)` with a **new, empty** `std::io::Write`
sink. The writer checks the entire baseline before writing the header and first
row. Baseline tick, elapsed time and tick duration must be zero. Call
`record(sample)` for each completed tick, then require `finish()` to succeed.
Successful finish flushes and returns the sink; it adds no timestamp-only row.

The original [`record_synthetic.rs`](../crates/bot-soak/examples/record_synthetic.rs)
example writes two seconds of explicitly synthetic observations to stdout:

```sh
cargo run --offline --locked -p bot-soak --example record_synthetic
```

Its output replays as `INCOMPLETE`, never as a server soak. Keep saved output
and all actual captures outside Git under the private evidence root. The adapter
owns exclusive file creation, private destinations, disk synchronization and
the final capture receipt. For a file, use `OpenOptions::create_new(true)` and
retain any failed output; this API deliberately does not open or truncate files.
When using `BufWriter`, explicitly finish it and synchronize its underlying file
after this writer finishes. A sink's flush is not a durability guarantee.

## Preserved observations and failures

The writer uses the actual replay row parser for schema validation, including
finite nonnegative numbers, negative-zero refusal, positive measured RSS and
stuck counts bounded by the cohort. Optional `None` remains an empty CSV field.
It requires a stable source/zone/count, consecutive producer tick indices and
strictly increasing elapsed milliseconds. Cumulative deaths and human-target
conflicts cannot decrease, including across missing observations. The existing
10,000,000 completed-tick and 4096-byte line limits also apply.

It does **not** fill gaps, renumber ticks, replace unavailable measurements with
zero, clamp values, or omit observed policy failures. Long elapsed gaps, missing
metrics, zero bots, nonzero stuck/death/conflict observations and currency drift
are valid data when structurally correct. Replay separately reports their
incomplete/failure verdict using the chosen policy. CPU remains measured server
process usage with 100% per logical core, and may exceed 100%.

`InvalidSample` or `Io` permanently closes the writer. Subsequent `record`,
`flush` and `finish` calls return `Failed` without another sink call, even if the
sink would now work. The writer commits its sequence/counter state only after a
whole row has been accepted by the sink. An output error may leave partial
bytes: preserve the failed capture and its failure receipt, and start any later
attempt as a distinct run. Do not reopen the same sink to continue it.

There is no writer `Drop` implementation that flushes or seals a run; an
underlying sink may still have its own drop behavior. Dropping this writer is
not successful finish. A retained valid prefix can still parse and can even meet
replay thresholds after a later capture failure. Therefore a passing replay is
never a substitute for the adapter's separately retained successful capture
receipt. The CSV format has no completion seal or authentication field.

## Scope and execution cost

Only one encoded row and constant-sized state are retained. No tick history,
sorting or policy calculation occurs during export. Each call formats and parses
a bounded row and performs synchronous writes; a supplied sink can block or
panic. The writer provides no CPU deadline, background thread, queue or runtime
instrumentation. The native owner must choose how to export without overrunning
its tick budget; no live-thread timing measurement has been made here.

`Source::Adapter` is a producer declaration, not evidence of a real server run.
Successful finish does not prove observation accuracy, uninterrupted sampling,
disk durability, headless behavior or Game QA. Existing feature switches remain
OFF and **NEVER restart FFXI**, including at zero players. Native adapter/P0
acceptance remains independent of navigation and this telemetry groundwork.
