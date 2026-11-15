//! Streaming CSV export for adapter-supplied observations. No clocks, process
//! measurements, bots or game actions are created here. A completed write is
//! not recording authentication, disk durability or a passing soak verdict.

use crate::{monotonic_counter, Row, Source, CSV_HEADER, MAX_LINE_BYTES, MAX_TICKS};
use std::fmt;
use std::io::{self, Write};

/// One observed baseline or completed tick. Sequence numbers and timestamps
/// belong to the producer: the writer never fills gaps or renumbers samples.
#[derive(Clone, Copy, Debug)]
pub struct Sample {
    pub source: Source,
    pub tick: u64,
    pub elapsed_ms: u64,
    pub zone_id: u32,
    pub bots: u32,
    pub tick_ms: f64,
    pub cpu_percent: Option<f64>,
    pub rss_bytes: Option<u64>,
    pub stuck_bots: Option<u32>,
    pub deaths_total: Option<u64>,
    pub bot_currency_units: Option<u64>,
    pub human_target_conflicts_total: Option<u64>,
}

impl Sample {
    fn encode(self) -> Result<String, RecordError> {
        fn optional(value: Option<impl fmt::Display>) -> String {
            value.map_or_else(String::new, |value| value.to_string())
        }
        let source = match self.source {
            Source::Adapter => "adapter",
            Source::Synthetic => "synthetic",
        };
        let mut line = format!(
            "{source},{},{},{},{},{},{},{},{},{},{},{}",
            self.tick,
            self.elapsed_ms,
            self.zone_id,
            self.bots,
            self.tick_ms,
            optional(self.cpu_percent),
            optional(self.rss_bytes),
            optional(self.stuck_bots),
            optional(self.deaths_total),
            optional(self.bot_currency_units),
            optional(self.human_target_conflicts_total),
        );
        // Use the actual replay row parser, including negative-zero, finite
        // number, optional metric and gauge rules. Avoid a second schema.
        Row::parse(&line).map_err(RecordError::InvalidSample)?;
        line.push('\n');
        if line.len() as u64 > MAX_LINE_BYTES {
            return Err(RecordError::InvalidSample(
                "sample exceeds CSV line limit".into(),
            ));
        }
        Ok(line)
    }
}

#[derive(Debug)]
pub enum RecordError {
    InvalidSample(String),
    Io(io::Error),
    /// An earlier input or output failure permanently closed this writer.
    Failed,
}

impl fmt::Display for RecordError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidSample(reason) => write!(f, "invalid telemetry sample: {reason}"),
            Self::Io(error) => write!(f, "telemetry output: {error}"),
            Self::Failed => f.write_str("telemetry writer is closed after an earlier failure"),
        }
    }
}

impl std::error::Error for RecordError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            _ => None,
        }
    }
}

/// Owns a caller-supplied output sink. The caller must supply a new empty sink,
/// keep failed captures and their error receipts, and require successful finish.
/// There is no append/resume, file opening, recovery, implicit flush or seal here.
///
/// Input and I/O failures are sticky. A partial output failure may leave a
/// truncated row; no further writer call can append, flush or finish it.
/// Even a parseable retained prefix is not proof that capture finished.
pub struct RecordingWriter<W: Write> {
    output: W,
    previous: Sample,
    last_deaths: Option<u64>,
    last_conflicts: Option<u64>,
    failed: bool,
}

impl<W: Write> RecordingWriter<W> {
    /// Validate before writing any bytes. Baseline-only output remains valid
    /// but incomplete telemetry; tick/elapsed/tick duration must all be zero.
    pub fn new(mut output: W, baseline: Sample) -> Result<Self, RecordError> {
        let line = baseline.encode()?;
        if baseline.tick != 0 || baseline.elapsed_ms != 0 || baseline.tick_ms != 0.0 {
            return Err(RecordError::InvalidSample(
                "baseline requires tick=0, elapsed_ms=0, tick_ms=0".into(),
            ));
        }
        let initial = format!("{CSV_HEADER}\n{line}");
        output
            .write_all(initial.as_bytes())
            .map_err(RecordError::Io)?;
        Ok(Self {
            output,
            previous: baseline,
            last_deaths: baseline.deaths_total,
            last_conflicts: baseline.human_target_conflicts_total,
            failed: false,
        })
    }

    /// Write one completed tick. Missing metrics, long gaps and observed policy
    /// violations remain in the recording; replay evaluates their verdict.
    pub fn record(&mut self, sample: Sample) -> Result<(), RecordError> {
        self.ensure_open()?;
        // Set first so a caller catching a sink panic cannot continue this run.
        self.failed = true;
        let line = sample.encode()?;
        if self.previous.tick >= MAX_TICKS as u64 {
            return Err(RecordError::InvalidSample(format!(
                "recording exceeds {MAX_TICKS} completed ticks"
            )));
        }
        if sample.source != self.previous.source
            || sample.zone_id != self.previous.zone_id
            || sample.bots != self.previous.bots
        {
            return Err(RecordError::InvalidSample(
                "source, zone_id and bots must stay constant".into(),
            ));
        }
        if sample.tick != self.previous.tick + 1 || sample.elapsed_ms <= self.previous.elapsed_ms {
            return Err(RecordError::InvalidSample(
                "ticks must be consecutive and elapsed_ms must increase".into(),
            ));
        }
        let mut deaths = self.last_deaths;
        let mut conflicts = self.last_conflicts;
        monotonic_counter("deaths_total", &mut deaths, sample.deaths_total)
            .map_err(RecordError::InvalidSample)?;
        monotonic_counter(
            "human_target_conflicts_total",
            &mut conflicts,
            sample.human_target_conflicts_total,
        )
        .map_err(RecordError::InvalidSample)?;
        self.output
            .write_all(line.as_bytes())
            .map_err(RecordError::Io)?;
        self.previous = sample;
        self.last_deaths = deaths;
        self.last_conflicts = conflicts;
        self.failed = false;
        Ok(())
    }

    /// Flush the supplied sink. This is not fsync or a game acceptance receipt.
    pub fn flush(&mut self) -> Result<(), RecordError> {
        self.ensure_open()?;
        self.failed = true;
        self.output.flush().map_err(RecordError::Io)?;
        self.failed = false;
        Ok(())
    }

    /// Flush and return the sink only after successful recording. Does not
    /// invent an end sample, evaluate a policy, or attest capture completeness.
    pub fn finish(mut self) -> Result<W, RecordError> {
        self.flush()?;
        Ok(self.output)
    }

    fn ensure_open(&self) -> Result<(), RecordError> {
        if self.failed {
            Err(RecordError::Failed)
        } else {
            Ok(())
        }
    }
}
