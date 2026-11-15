//! Generated in-memory samples exercise the adapter-facing writer contract.
//! An adapter source declaration in these fixtures is not evidence of a live run.

use bot_soak::recording::{RecordError, RecordingWriter, Sample};
use bot_soak::{replay, Policy, Source, Verdict, CSV_HEADER, ONE_HOUR_MS};
use std::cell::RefCell;
use std::io::{self, Cursor, Write};
use std::rc::Rc;

fn baseline(source: Source) -> Sample {
    Sample {
        source,
        tick: 0,
        elapsed_ms: 0,
        zone_id: 100,
        bots: 20,
        tick_ms: 0.0,
        cpu_percent: None,
        rss_bytes: Some(1_048_576),
        stuck_bots: Some(0),
        deaths_total: Some(7),
        bot_currency_units: Some(1000),
        human_target_conflicts_total: Some(3),
    }
}

fn completed(tick: u64, source: Source) -> Sample {
    Sample {
        tick,
        elapsed_ms: tick * 1000,
        tick_ms: 12.5,
        cpu_percent: Some(125.25),
        rss_bytes: Some(2_097_152),
        ..baseline(source)
    }
}

#[test]
fn supplied_one_hour_round_trips_without_invented_ticks_or_measurements() {
    let mut writer = RecordingWriter::new(Vec::new(), baseline(Source::Adapter)).unwrap();
    for tick in 1..=3600 {
        writer.record(completed(tick, Source::Adapter)).unwrap();
    }
    writer.flush().unwrap();
    let bytes = writer.finish().unwrap();
    let csv = std::str::from_utf8(&bytes).unwrap();
    assert_eq!(csv.lines().next(), Some(CSV_HEADER));
    assert_eq!(csv.lines().count(), 3602); // Header, baseline, supplied ticks.
    assert!(csv.lines().skip(1).all(|line| line.starts_with("adapter,")));

    let policy = Policy::for_zone(100);
    let report = replay(Cursor::new(&bytes), &policy).unwrap();
    assert_eq!(report.verdict(), Verdict::TelemetryPass);
    assert_eq!(report.source, Source::Adapter);
    assert_eq!(report.ticks, 3600);
    assert_eq!(report.duration_ms, ONE_HOUR_MS);
    assert_eq!(report.tick_ms.samples, 3600);
    assert_eq!(report.tick_ms.mean, 12.5);
    assert_eq!(report.tick_p95_ms, Some(12.5));
    assert_eq!(report.cpu_percent.samples, 3600);
    assert_eq!(report.cpu_percent.mean, 125.25);
    assert_eq!(report.rss_bytes.max, 2_097_152.0);
    assert_eq!(report.deaths_delta, Some(0));
    assert_eq!(report.currency_delta, Some(0));
    assert_eq!(report.human_conflicts_delta, Some(0));

    let mut text = Vec::new();
    report.write_text(&policy, &mut text).unwrap();
    let text = String::from_utf8(text).unwrap();
    assert!(text.contains("source=adapter_declared_unverified\n"));
    assert!(text.contains("recording_authenticity=NOT_VERIFIED\n"));
    assert!(text.contains("live_game_qa=NOT_RUN\n"));
}

#[test]
fn synthetic_baseline_and_short_recordings_remain_incomplete() {
    for ticks in [0, 2] {
        let mut writer = RecordingWriter::new(Vec::new(), baseline(Source::Synthetic)).unwrap();
        for tick in 1..=ticks {
            writer.record(completed(tick, Source::Synthetic)).unwrap();
        }
        let bytes = writer.finish().unwrap();
        let report = replay(Cursor::new(&bytes), &Policy::for_zone(100)).unwrap();
        assert_eq!(report.source, Source::Synthetic);
        assert_eq!(report.verdict(), Verdict::Incomplete);
        assert_eq!(report.ticks, ticks as usize);
        assert_eq!(report.duration_ms, ticks * 1000);
        assert_eq!(
            std::str::from_utf8(&bytes).unwrap().lines().count(),
            ticks as usize + 2
        );
    }
}

#[test]
fn writer_preserves_missing_metrics_gaps_and_zero_load_for_replay_policy() {
    let start = Sample {
        bots: 0,
        rss_bytes: None,
        stuck_bots: None,
        deaths_total: None,
        bot_currency_units: None,
        human_target_conflicts_total: None,
        ..baseline(Source::Adapter)
    };
    let mut writer = RecordingWriter::new(Vec::new(), start).unwrap();
    writer
        .record(Sample {
            tick: 1,
            elapsed_ms: ONE_HOUR_MS,
            tick_ms: 8.0,
            ..start
        })
        .unwrap();
    let report = replay(
        Cursor::new(writer.finish().unwrap()),
        &Policy::for_zone(100),
    )
    .unwrap();
    assert_eq!(report.verdict(), Verdict::Incomplete);
    assert_eq!(report.bots, 0);
    assert_eq!(report.ticks, 1);
    assert_eq!(report.duration_ms, ONE_HOUR_MS);
    assert_eq!(report.max_gap_ms, ONE_HOUR_MS);
    assert_eq!(report.cpu_percent.samples, 0);
    assert_eq!(report.cpu_percent.missing, 1);
    assert_eq!(report.rss_bytes.samples, 0);
    assert_eq!(report.rss_bytes.missing, 2);
    assert_eq!(report.max_stuck_bots, None);
    assert_eq!(report.deaths_delta, None);
    assert_eq!(report.currency_delta, None);
    assert_eq!(report.human_conflicts_delta, None);
}

#[test]
fn recorded_violations_and_transient_currency_drift_reach_the_report() {
    let mut writer = RecordingWriter::new(Vec::new(), baseline(Source::Adapter)).unwrap();
    writer
        .record(Sample {
            tick_ms: 80.0,
            stuck_bots: Some(2),
            deaths_total: Some(8),
            bot_currency_units: Some(1150),
            human_target_conflicts_total: Some(4),
            ..completed(1, Source::Adapter)
        })
        .unwrap();
    writer
        .record(Sample {
            deaths_total: Some(8),
            human_target_conflicts_total: Some(4),
            ..completed(2, Source::Adapter)
        })
        .unwrap();
    let report = replay(
        Cursor::new(writer.finish().unwrap()),
        &Policy::for_zone(100),
    )
    .unwrap();
    assert_eq!(report.verdict(), Verdict::Fail);
    assert_eq!(report.ticks, 2);
    assert_eq!(report.tick_ms.max, 80.0);
    assert_eq!(report.max_stuck_bots, Some(2));
    assert_eq!(report.deaths_delta, Some(1));
    assert_eq!(report.currency_delta, Some(0));
    assert_eq!(report.max_abs_currency_drift, Some(150));
    assert_eq!(report.human_conflicts_delta, Some(1));
}

#[test]
fn finite_float_and_unsigned_counter_extremes_survive_serialization() {
    let start = Sample {
        rss_bytes: Some(u64::MAX),
        deaths_total: Some(u64::MAX),
        bot_currency_units: Some(u64::MAX),
        human_target_conflicts_total: Some(u64::MAX),
        ..baseline(Source::Adapter)
    };
    let mut writer = RecordingWriter::new(Vec::new(), start).unwrap();
    writer
        .record(Sample {
            tick: 1,
            elapsed_ms: 1000,
            tick_ms: f64::MAX,
            cpu_percent: Some(f64::MAX),
            bot_currency_units: Some(0),
            ..start
        })
        .unwrap();
    let smallest_positive = f64::from_bits(1);
    writer
        .record(Sample {
            tick: 2,
            elapsed_ms: 2000,
            tick_ms: smallest_positive,
            cpu_percent: Some(smallest_positive),
            ..start
        })
        .unwrap();
    let bytes = writer.finish().unwrap();
    let csv = std::str::from_utf8(&bytes).unwrap();
    let rows: Vec<Vec<&str>> = csv
        .lines()
        .skip(1)
        .map(|line| line.split(',').collect())
        .collect();
    assert_eq!(rows.len(), 3);
    for row in &rows {
        assert_eq!(row[7].parse::<u64>().unwrap(), u64::MAX);
        assert_eq!(row[9].parse::<u64>().unwrap(), u64::MAX);
        assert_eq!(row[11].parse::<u64>().unwrap(), u64::MAX);
    }
    for field in [5, 6] {
        assert_eq!(
            rows[1][field].parse::<f64>().unwrap().to_bits(),
            f64::MAX.to_bits()
        );
        assert_eq!(
            rows[2][field].parse::<f64>().unwrap().to_bits(),
            smallest_positive.to_bits()
        );
    }
    assert_eq!(rows[0][10].parse::<u64>().unwrap(), u64::MAX);
    assert_eq!(rows[1][10].parse::<u64>().unwrap(), 0);
    assert_eq!(rows[2][10].parse::<u64>().unwrap(), u64::MAX);

    let report = replay(Cursor::new(&bytes), &Policy::for_zone(100)).unwrap();
    assert_eq!(report.verdict(), Verdict::Fail);
    assert_eq!(report.tick_ms.max, f64::MAX);
    assert_eq!(report.cpu_percent.max, f64::MAX);
    assert!(report.tick_ms.mean.is_finite());
    assert!(report.cpu_percent.mean.is_finite());
    assert_eq!(report.deaths_delta, Some(0));
    assert_eq!(report.human_conflicts_delta, Some(0));
    assert_eq!(report.currency_delta, Some(0));
    assert_eq!(report.max_abs_currency_drift, Some(u64::MAX));
}

#[test]
fn invalid_baselines_emit_no_header_or_data() {
    let start = baseline(Source::Adapter);
    let invalid = [
        Sample { tick: 1, ..start },
        Sample {
            elapsed_ms: 1,
            ..start
        },
        Sample {
            tick_ms: 1.0,
            ..start
        },
        Sample {
            tick_ms: -0.0,
            ..start
        },
        Sample {
            tick_ms: f64::NAN,
            ..start
        },
        Sample {
            cpu_percent: Some(f64::INFINITY),
            ..start
        },
        Sample {
            cpu_percent: Some(-0.0),
            ..start
        },
        Sample {
            rss_bytes: Some(0),
            ..start
        },
        Sample {
            stuck_bots: Some(21),
            ..start
        },
    ];
    for (index, sample) in invalid.into_iter().enumerate() {
        let sink = ProbeSink::default();
        let result = RecordingWriter::new(sink.clone(), sample);
        assert!(
            matches!(result, Err(RecordError::InvalidSample(_))),
            "baseline case {index}"
        );
        assert_eq!(sink.snapshot(), (Vec::new(), 0, 0), "baseline case {index}");
    }
}

#[test]
fn invalid_samples_are_not_written_and_permanently_poison_the_writer() {
    let first = completed(1, Source::Adapter);
    let invalid = [
        Sample { tick: 0, ..first },
        Sample { tick: 2, ..first },
        Sample {
            elapsed_ms: 0,
            ..first
        },
        Sample {
            source: Source::Synthetic,
            ..first
        },
        Sample {
            zone_id: 101,
            ..first
        },
        Sample { bots: 19, ..first },
        Sample {
            tick_ms: f64::NAN,
            ..first
        },
        Sample {
            tick_ms: f64::INFINITY,
            ..first
        },
        Sample {
            tick_ms: -1.0,
            ..first
        },
        Sample {
            tick_ms: -0.0,
            ..first
        },
        Sample {
            cpu_percent: Some(f64::NAN),
            ..first
        },
        Sample {
            cpu_percent: Some(-1.0),
            ..first
        },
        Sample {
            cpu_percent: Some(-0.0),
            ..first
        },
        Sample {
            rss_bytes: Some(0),
            ..first
        },
        Sample {
            stuck_bots: Some(21),
            ..first
        },
    ];
    for (index, sample) in invalid.into_iter().enumerate() {
        let sink = ProbeSink::default();
        let mut writer = RecordingWriter::new(sink.clone(), baseline(Source::Adapter)).unwrap();
        let before = sink.snapshot();
        assert!(
            matches!(writer.record(sample), Err(RecordError::InvalidSample(_))),
            "sample case {index}"
        );
        assert_eq!(sink.snapshot(), before, "sample case {index}");
        assert_poisoned(writer, &sink, first);
    }
}

#[test]
fn counter_regressions_are_rejected_even_after_missing_observations() {
    for lower_deaths in [true, false] {
        let sink = ProbeSink::default();
        let mut writer = RecordingWriter::new(sink.clone(), baseline(Source::Adapter)).unwrap();
        writer
            .record(Sample {
                deaths_total: Some(9),
                human_target_conflicts_total: Some(5),
                ..completed(1, Source::Adapter)
            })
            .unwrap();
        writer
            .record(Sample {
                deaths_total: None,
                human_target_conflicts_total: None,
                ..completed(2, Source::Adapter)
            })
            .unwrap();
        let lower = Sample {
            deaths_total: lower_deaths.then_some(8),
            human_target_conflicts_total: (!lower_deaths).then_some(4),
            ..completed(3, Source::Adapter)
        };
        let before = sink.snapshot();
        assert!(matches!(
            writer.record(lower),
            Err(RecordError::InvalidSample(_))
        ));
        assert_eq!(sink.snapshot(), before);
        assert_poisoned(writer, &sink, completed(3, Source::Adapter));
    }
}

#[test]
fn partial_write_error_cannot_be_followed_by_another_row_or_flush() {
    let sink = ProbeSink::default();
    let mut writer = RecordingWriter::new(sink.clone(), baseline(Source::Adapter)).unwrap();
    let before = sink.snapshot();
    sink.0.borrow_mut().bytes_until_error = Some(5);
    assert!(matches!(
        writer.record(completed(1, Source::Adapter)),
        Err(RecordError::Io(_))
    ));
    let after = sink.snapshot();
    assert_eq!(after.0.len(), before.0.len() + 5);
    assert!(after.1 > before.1);
    // The sink now recovers; only the writer's poisoned state can prevent I/O.
    assert_eq!(sink.0.borrow().bytes_until_error, None);
    assert_poisoned(writer, &sink, completed(2, Source::Adapter));
}

#[test]
fn a_single_flush_error_permanently_poisons_the_writer() {
    let sink = ProbeSink::default();
    let mut writer = RecordingWriter::new(sink.clone(), baseline(Source::Adapter)).unwrap();
    writer.record(completed(1, Source::Adapter)).unwrap();
    sink.0.borrow_mut().fail_next_flush = true;
    assert!(matches!(writer.flush(), Err(RecordError::Io(_))));
    assert!(!sink.0.borrow().fail_next_flush);
    assert_poisoned(writer, &sink, completed(2, Source::Adapter));
}

#[test]
fn finish_reports_flush_failure_instead_of_returning_a_successful_recording() {
    let sink = ProbeSink::default();
    let mut writer = RecordingWriter::new(sink.clone(), baseline(Source::Adapter)).unwrap();
    writer.record(completed(1, Source::Adapter)).unwrap();
    let before = sink.snapshot();
    sink.0.borrow_mut().fail_next_flush = true;
    assert!(matches!(writer.finish(), Err(RecordError::Io(_))));
    let after = sink.snapshot();
    assert_eq!(after.0, before.0);
    assert_eq!(after.1, before.1);
    assert_eq!(after.2, before.2 + 1);
}

fn assert_poisoned(mut writer: RecordingWriter<ProbeSink>, sink: &ProbeSink, next: Sample) {
    let before = sink.snapshot();
    assert!(matches!(writer.record(next), Err(RecordError::Failed)));
    assert!(matches!(writer.flush(), Err(RecordError::Failed)));
    assert!(matches!(writer.finish(), Err(RecordError::Failed)));
    assert_eq!(sink.snapshot(), before, "poisoned writer touched its sink");
}

#[derive(Clone, Default)]
struct ProbeSink(Rc<RefCell<SinkState>>);

#[derive(Default)]
struct SinkState {
    bytes: Vec<u8>,
    write_calls: usize,
    flush_calls: usize,
    bytes_until_error: Option<usize>,
    fail_next_flush: bool,
}

impl ProbeSink {
    fn snapshot(&self) -> (Vec<u8>, usize, usize) {
        let state = self.0.borrow();
        (state.bytes.clone(), state.write_calls, state.flush_calls)
    }
}

impl Write for ProbeSink {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        let mut state = self.0.borrow_mut();
        state.write_calls += 1;
        let count = match state.bytes_until_error {
            Some(0) => {
                state.bytes_until_error = None;
                return Err(io::Error::other("injected one-time write failure"));
            }
            Some(remaining) => {
                let count = bytes.len().min(remaining);
                state.bytes_until_error = Some(remaining - count);
                count
            }
            None => bytes.len(),
        };
        state.bytes.extend_from_slice(&bytes[..count]);
        Ok(count)
    }

    fn flush(&mut self) -> io::Result<()> {
        let mut state = self.0.borrow_mut();
        state.flush_calls += 1;
        if state.fail_next_flush {
            state.fail_next_flush = false;
            Err(io::Error::other("injected one-time flush failure"))
        } else {
            Ok(())
        }
    }
}
