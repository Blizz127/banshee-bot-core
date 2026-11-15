//! Offline telemetry validation, not a server driver or proof of live game QA.
//!
//! All process metrics come from the recording. This crate never attaches to a
//! game server, spawns bots, or substitutes its own CPU/RAM for server metrics.

use std::fmt;
use std::io::{BufRead, Read};

pub mod recording;

pub const CSV_HEADER: &str = "source,tick,elapsed_ms,zone_id,bots,tick_ms,cpu_percent,rss_bytes,stuck_bots,deaths_total,bot_currency_units,human_target_conflicts_total";
pub const ONE_HOUR_MS: u64 = 3_600_000;
const MAX_LINE_BYTES: u64 = 4096;
const MAX_TICKS: usize = 10_000_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Source {
    Adapter,
    Synthetic,
}

impl fmt::Display for Source {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Adapter => "adapter_declared_unverified",
            Self::Synthetic => "synthetic",
        })
    }
}

/// The one-hour minimum cannot be shortened to turn a smoke into a soak pass.
#[derive(Clone, Debug)]
pub struct Policy {
    pub expected_bots: u32,
    pub zone_id: u32,
    pub min_duration_ms: u64,
    /// At most one second between consecutive per-tick observations.
    pub max_gap_ms: u64,
    pub max_tick_ms: f64,
    pub max_abs_currency_drift: u64,
}

impl Policy {
    pub fn for_zone(zone_id: u32) -> Self {
        Self {
            expected_bots: 20,
            zone_id,
            min_duration_ms: ONE_HOUR_MS,
            max_gap_ms: 1000,
            max_tick_ms: 50.0,
            max_abs_currency_drift: 0,
        }
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.expected_bots == 0 {
            return Err("expected bot count must be positive".into());
        }
        if self.min_duration_ms < ONE_HOUR_MS {
            return Err("minimum duration must be at least 3600 seconds".into());
        }
        if !(1..=1000).contains(&self.max_gap_ms) {
            return Err("maximum telemetry gap must be between 1 and 1000 ms".into());
        }
        if !self.max_tick_ms.is_finite() || self.max_tick_ms <= 0.0 {
            return Err("tick budget must be finite and positive".into());
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Verdict {
    TelemetryPass,
    Incomplete,
    Fail,
}

impl Verdict {
    pub fn exit_code(self) -> i32 {
        match self {
            Self::TelemetryPass => 0,
            Self::Incomplete => 3,
            Self::Fail => 4,
        }
    }
}

impl fmt::Display for Verdict {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::TelemetryPass => "TELEMETRY_PASS",
            Self::Incomplete => "INCOMPLETE",
            Self::Fail => "FAIL",
        })
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub struct Metric {
    pub samples: usize,
    pub missing: usize,
    pub mean: f64,
    pub max: f64,
}

impl Metric {
    fn observe(&mut self, value: Option<f64>) {
        match value {
            Some(value) => {
                self.samples += 1;
                self.mean += (value - self.mean) / self.samples as f64;
                self.max = self.max.max(value);
            }
            None => self.missing += 1,
        }
    }
}

#[derive(Debug)]
pub struct Report {
    pub source: Source,
    pub zone_id: u32,
    pub bots: u32,
    pub ticks: usize,
    pub duration_ms: u64,
    pub max_gap_ms: u64,
    pub tick_ms: Metric,
    pub tick_p95_ms: Option<f64>,
    pub cpu_percent: Metric,
    pub rss_bytes: Metric,
    pub max_stuck_bots: Option<u32>,
    pub deaths_baseline: Option<u64>,
    pub deaths_total: Option<u64>,
    pub deaths_delta: Option<u64>,
    pub currency_baseline: Option<u64>,
    pub currency_final: Option<u64>,
    pub currency_delta: Option<i128>,
    pub max_abs_currency_drift: Option<u64>,
    pub human_conflicts_baseline: Option<u64>,
    pub human_conflicts_total: Option<u64>,
    pub human_conflicts_delta: Option<u64>,
    pub missing_stuck_samples: usize,
    pub missing_death_samples: usize,
    pub missing_currency_samples: usize,
    pub missing_human_conflict_samples: usize,
    pub incomplete_reasons: Vec<String>,
    pub failure_reasons: Vec<String>,
}

impl Report {
    pub fn verdict(&self) -> Verdict {
        if !self.failure_reasons.is_empty() {
            Verdict::Fail
        } else if !self.incomplete_reasons.is_empty() {
            Verdict::Incomplete
        } else {
            Verdict::TelemetryPass
        }
    }

    pub fn write_text(&self, policy: &Policy, mut out: impl std::io::Write) -> std::io::Result<()> {
        writeln!(out, "format=bot-soak-report-v1")?;
        writeln!(out, "verdict={}", self.verdict())?;
        writeln!(out, "source={}", self.source)?;
        writeln!(out, "live_game_qa=NOT_RUN")?;
        writeln!(out, "recording_authenticity=NOT_VERIFIED")?;
        writeln!(out, "zone_id={}", self.zone_id)?;
        writeln!(out, "bots={}", self.bots)?;
        writeln!(out, "expected_bots={}", policy.expected_bots)?;
        writeln!(out, "completed_ticks={}", self.ticks)?;
        writeln!(out, "duration_ms={}", self.duration_ms)?;
        writeln!(out, "required_duration_ms={}", policy.min_duration_ms)?;
        writeln!(out, "max_gap_ms={}", self.max_gap_ms)?;
        writeln!(out, "allowed_gap_ms={}", policy.max_gap_ms)?;
        writeln!(out, "tick_budget_ms={}", policy.max_tick_ms)?;
        write_metric(&mut out, "tick_ms", &self.tick_ms)?;
        writeln!(out, "tick_ms_p95={}", display_option(self.tick_p95_ms))?;
        write_metric(&mut out, "server_cpu_percent", &self.cpu_percent)?;
        writeln!(out, "cpu_basis=100_percent_per_logical_core")?;
        write_metric(&mut out, "server_rss_bytes", &self.rss_bytes)?;
        writeln!(
            out,
            "max_stuck_bots={}",
            display_option(self.max_stuck_bots)
        )?;
        writeln!(out, "missing_stuck_samples={}", self.missing_stuck_samples)?;
        writeln!(
            out,
            "deaths_baseline={}",
            display_option(self.deaths_baseline)
        )?;
        writeln!(out, "deaths_total={}", display_option(self.deaths_total))?;
        writeln!(out, "deaths_delta={}", display_option(self.deaths_delta))?;
        writeln!(out, "missing_death_samples={}", self.missing_death_samples)?;
        writeln!(
            out,
            "bot_currency_baseline={}",
            display_option(self.currency_baseline)
        )?;
        writeln!(
            out,
            "bot_currency_final={}",
            display_option(self.currency_final)
        )?;
        writeln!(
            out,
            "bot_currency_delta={}",
            display_option(self.currency_delta)
        )?;
        writeln!(
            out,
            "max_abs_bot_currency_drift={}",
            display_option(self.max_abs_currency_drift)
        )?;
        writeln!(
            out,
            "allowed_abs_bot_currency_drift={}",
            policy.max_abs_currency_drift
        )?;
        writeln!(
            out,
            "missing_currency_samples={}",
            self.missing_currency_samples
        )?;
        writeln!(
            out,
            "human_conflicts_baseline={}",
            display_option(self.human_conflicts_baseline)
        )?;
        writeln!(
            out,
            "human_conflicts_total={}",
            display_option(self.human_conflicts_total)
        )?;
        writeln!(
            out,
            "human_conflicts_delta={}",
            display_option(self.human_conflicts_delta)
        )?;
        writeln!(
            out,
            "missing_human_conflict_samples={}",
            self.missing_human_conflict_samples
        )?;
        for reason in &self.incomplete_reasons {
            writeln!(out, "incomplete={reason}")?;
        }
        for reason in &self.failure_reasons {
            writeln!(out, "failure={reason}")?;
        }
        Ok(())
    }
}

fn write_metric(out: &mut impl std::io::Write, name: &str, metric: &Metric) -> std::io::Result<()> {
    writeln!(out, "{name}_samples={}", metric.samples)?;
    writeln!(out, "{name}_missing={}", metric.missing)?;
    let mean = (metric.samples > 0).then_some(metric.mean);
    let max = (metric.samples > 0).then_some(metric.max);
    writeln!(out, "{name}_mean={}", display_option(mean))?;
    writeln!(out, "{name}_max={}", display_option(max))
}

fn display_option(value: Option<impl fmt::Display>) -> String {
    value.map_or_else(|| "UNKNOWN".into(), |value| value.to_string())
}

#[derive(Debug)]
struct Row {
    source: Source,
    tick: u64,
    elapsed_ms: u64,
    zone_id: u32,
    bots: u32,
    tick_ms: f64,
    cpu_percent: Option<f64>,
    rss_bytes: Option<u64>,
    stuck_bots: Option<u32>,
    deaths_total: Option<u64>,
    currency: Option<u64>,
    human_conflicts_total: Option<u64>,
}

impl Row {
    fn parse(line: &str) -> Result<Self, String> {
        let values: Vec<_> = line.split(',').collect();
        if values.len() != 12 {
            return Err("expected exactly 12 unquoted CSV columns".into());
        }
        let row = Self {
            source: match values[0] {
                "adapter" => Source::Adapter,
                "synthetic" => Source::Synthetic,
                _ => return Err("source must be adapter or synthetic".into()),
            },
            tick: unsigned(values[1], "tick")?,
            elapsed_ms: unsigned(values[2], "elapsed_ms")?,
            zone_id: unsigned(values[3], "zone_id")?,
            bots: unsigned(values[4], "bots")?,
            tick_ms: finite_nonnegative(values[5], "tick_ms")?,
            cpu_percent: optional(values[6], |s| finite_nonnegative(s, "cpu_percent"))?,
            rss_bytes: optional(values[7], |s| unsigned(s, "rss_bytes"))?,
            stuck_bots: optional(values[8], |s| unsigned(s, "stuck_bots"))?,
            deaths_total: optional(values[9], |s| unsigned(s, "deaths_total"))?,
            currency: optional(values[10], |s| unsigned(s, "bot_currency_units"))?,
            human_conflicts_total: optional(values[11], |s| {
                unsigned(s, "human_target_conflicts_total")
            })?,
        };
        if row.rss_bytes == Some(0) {
            return Err(
                "measured rss_bytes must be positive; leave unavailable metrics empty".into(),
            );
        }
        if row.stuck_bots.is_some_and(|stuck| stuck > row.bots) {
            return Err("stuck_bots exceeds bots".into());
        }
        Ok(row)
    }
}

fn unsigned<T: std::str::FromStr>(value: &str, name: &str) -> Result<T, String> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(format!("{name} must be an unsigned integer"));
    }
    value.parse().map_err(|_| format!("{name} is out of range"))
}

fn finite_nonnegative(value: &str, name: &str) -> Result<f64, String> {
    let parsed: f64 = value
        .parse()
        .map_err(|_| format!("{name} must be a number"))?;
    if !parsed.is_finite() || parsed.is_sign_negative() {
        return Err(format!("{name} must be finite and nonnegative"));
    }
    Ok(parsed)
}

fn optional<T>(
    value: &str,
    parse: impl FnOnce(&str) -> Result<T, String>,
) -> Result<Option<T>, String> {
    if value.is_empty() {
        Ok(None)
    } else {
        parse(value).map(Some)
    }
}

fn read_line(reader: &mut impl BufRead, buffer: &mut String, line: usize) -> Result<bool, String> {
    buffer.clear();
    let count = reader
        .take(MAX_LINE_BYTES + 1)
        .read_line(buffer)
        .map_err(|error| format!("line {line}: {error}"))?;
    if count == 0 {
        return Ok(false);
    }
    if count as u64 > MAX_LINE_BYTES {
        return Err(format!("line {line}: line exceeds {MAX_LINE_BYTES} bytes"));
    }
    if buffer.ends_with('\n') {
        buffer.pop();
        if buffer.ends_with('\r') {
            buffer.pop();
        }
    }
    Ok(true)
}

/// Validate a recording and compute metrics. An accepted source declaration is
/// not authentication: callers must keep Game QA and adapter provenance separate.
pub fn replay(mut reader: impl BufRead, policy: &Policy) -> Result<Report, String> {
    policy.validate()?;
    let mut line = String::new();
    if !read_line(&mut reader, &mut line, 1)? || line != CSV_HEADER {
        return Err("line 1: missing or unsupported bot-soak CSV header".into());
    }
    if !read_line(&mut reader, &mut line, 2)? {
        return Err("recording contains no baseline row".into());
    }
    let baseline = Row::parse(&line).map_err(|error| format!("line 2: {error}"))?;
    if baseline.tick != 0 || baseline.elapsed_ms != 0 || baseline.tick_ms != 0.0 {
        return Err("line 2: baseline requires tick=0, elapsed_ms=0, tick_ms=0".into());
    }
    if baseline.zone_id != policy.zone_id {
        return Err("line 2: zone_id does not match the requested zone".into());
    }
    let mut report = Report {
        source: baseline.source,
        zone_id: baseline.zone_id,
        bots: baseline.bots,
        ticks: 0,
        duration_ms: 0,
        max_gap_ms: 0,
        tick_ms: Metric::default(),
        tick_p95_ms: None,
        cpu_percent: Metric::default(),
        rss_bytes: Metric::default(),
        max_stuck_bots: None,
        deaths_baseline: baseline.deaths_total,
        deaths_total: baseline.deaths_total,
        deaths_delta: None,
        currency_baseline: baseline.currency,
        currency_final: baseline.currency,
        currency_delta: None,
        max_abs_currency_drift: baseline.currency.map(|_| 0),
        human_conflicts_baseline: baseline.human_conflicts_total,
        human_conflicts_total: baseline.human_conflicts_total,
        human_conflicts_delta: None,
        missing_stuck_samples: 0,
        missing_death_samples: 0,
        missing_currency_samples: 0,
        missing_human_conflict_samples: 0,
        incomplete_reasons: Vec::new(),
        failure_reasons: Vec::new(),
    };
    observe_gauges(&mut report, &baseline);
    let mut last_deaths = baseline.deaths_total;
    let mut last_conflicts = baseline.human_conflicts_total;
    let mut tick_durations = Vec::new();
    let mut line_number = 3;
    while read_line(&mut reader, &mut line, line_number)? {
        let row = Row::parse(&line).map_err(|error| format!("line {line_number}: {error}"))?;
        if report.ticks == MAX_TICKS {
            return Err(format!("recording exceeds {MAX_TICKS} completed ticks"));
        }
        if row.source != report.source || row.zone_id != report.zone_id || row.bots != report.bots {
            return Err(format!(
                "line {line_number}: source, zone_id and bots must stay constant"
            ));
        }
        if row.tick != report.ticks as u64 + 1 || row.elapsed_ms <= report.duration_ms {
            return Err(format!(
                "line {line_number}: ticks must be consecutive and elapsed_ms must increase"
            ));
        }
        monotonic_counter("deaths_total", &mut last_deaths, row.deaths_total)
            .map_err(|error| format!("line {line_number}: {error}"))?;
        monotonic_counter(
            "human_target_conflicts_total",
            &mut last_conflicts,
            row.human_conflicts_total,
        )
        .map_err(|error| format!("line {line_number}: {error}"))?;
        report.ticks += 1;
        report.max_gap_ms = report.max_gap_ms.max(row.elapsed_ms - report.duration_ms);
        report.duration_ms = row.elapsed_ms;
        report.tick_ms.observe(Some(row.tick_ms));
        report.cpu_percent.observe(row.cpu_percent);
        tick_durations.push(row.tick_ms);
        observe_gauges(&mut report, &row);
        report.deaths_total = row.deaths_total;
        report.human_conflicts_total = row.human_conflicts_total;
        report.currency_final = row.currency;
        line_number += 1;
    }
    if !tick_durations.is_empty() {
        tick_durations.sort_unstable_by(f64::total_cmp);
        let rank = (tick_durations.len() * 95).div_ceil(100);
        report.tick_p95_ms = Some(tick_durations[rank - 1]);
    }
    report.deaths_delta = report
        .deaths_total
        .zip(report.deaths_baseline)
        .map(|(end, start)| end - start);
    report.human_conflicts_delta = report
        .human_conflicts_total
        .zip(report.human_conflicts_baseline)
        .map(|(end, start)| end - start);
    report.currency_delta = report
        .currency_final
        .zip(report.currency_baseline)
        .map(|(end, start)| i128::from(end) - i128::from(start));
    evaluate(&mut report, policy, last_deaths, last_conflicts);
    Ok(report)
}

fn monotonic_counter(
    name: &str,
    previous: &mut Option<u64>,
    next: Option<u64>,
) -> Result<(), String> {
    if let Some(next) = next {
        if previous.is_some_and(|previous| next < previous) {
            return Err(format!(
                "{name} decreased; counters cannot reset within a recording"
            ));
        }
        *previous = Some(next);
    }
    Ok(())
}

fn observe_gauges(report: &mut Report, row: &Row) {
    report
        .rss_bytes
        .observe(row.rss_bytes.map(|value| value as f64));
    if let Some(stuck) = row.stuck_bots {
        report.max_stuck_bots = Some(report.max_stuck_bots.unwrap_or(0).max(stuck));
    } else {
        report.missing_stuck_samples += 1;
    }
    if row.deaths_total.is_none() {
        report.missing_death_samples += 1;
    }
    if row.human_conflicts_total.is_none() {
        report.missing_human_conflict_samples += 1;
    }
    if let Some((value, baseline)) = row.currency.zip(report.currency_baseline) {
        let drift = value.abs_diff(baseline);
        report.max_abs_currency_drift = Some(report.max_abs_currency_drift.unwrap_or(0).max(drift));
    }
    if row.currency.is_none() {
        report.missing_currency_samples += 1;
    }
}

fn evaluate(
    report: &mut Report,
    policy: &Policy,
    last_deaths: Option<u64>,
    last_conflicts: Option<u64>,
) {
    if report.source == Source::Synthetic {
        report
            .incomplete_reasons
            .push("synthetic input cannot qualify as server telemetry".into());
    }
    if report.ticks == 0 {
        report
            .incomplete_reasons
            .push("baseline has no completed ticks".into());
    }
    if report.bots != policy.expected_bots {
        report
            .incomplete_reasons
            .push("recorded bot count differs from requested load".into());
    }
    if report.duration_ms < policy.min_duration_ms {
        report
            .incomplete_reasons
            .push("recording does not cover the required duration".into());
    }
    if report.max_gap_ms > policy.max_gap_ms {
        report
            .incomplete_reasons
            .push("gap between adjacent ticks exceeds coverage limit".into());
    }
    for (name, count) in [
        ("server CPU", report.cpu_percent.missing),
        ("server RSS", report.rss_bytes.missing),
        ("stuck bots", report.missing_stuck_samples),
        ("deaths", report.missing_death_samples),
        ("bot currency", report.missing_currency_samples),
        (
            "human target conflicts",
            report.missing_human_conflict_samples,
        ),
    ] {
        if count > 0 {
            report
                .incomplete_reasons
                .push(format!("{name} missing from {count} observations"));
        }
    }
    if report.tick_ms.max > policy.max_tick_ms {
        report
            .failure_reasons
            .push("recorded tick duration exceeds configured budget".into());
    }
    if report.max_stuck_bots.is_some_and(|value| value > 0) {
        report
            .failure_reasons
            .push("one or more bots were reported stuck".into());
    }
    if last_deaths
        .zip(report.deaths_baseline)
        .is_some_and(|(end, start)| end > start)
    {
        report
            .failure_reasons
            .push("one or more bot deaths were reported during the run".into());
    }
    if last_conflicts
        .zip(report.human_conflicts_baseline)
        .is_some_and(|(end, start)| end > start)
    {
        report
            .failure_reasons
            .push("one or more human target conflicts were reported during the run".into());
    }
    if report
        .max_abs_currency_drift
        .is_some_and(|drift| drift > policy.max_abs_currency_drift)
    {
        report
            .failure_reasons
            .push("bot currency deviated beyond the configured absolute limit".into());
    }
}
