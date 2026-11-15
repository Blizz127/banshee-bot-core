use bot_soak::{replay, Policy, Source, Verdict, CSV_HEADER};
use std::io::Cursor;

fn recording(source: &str, ticks: u64) -> String {
    // Generated test input only; the adapter declaration is deliberately not
    // treated as evidence that this fixture came from a running game server.
    let mut csv = format!("{CSV_HEADER}\n{source},0,0,100,20,0,,1048576,0,7,1000,3\n");
    for tick in 1..=ticks {
        csv.push_str(&format!(
            "{source},{tick},{},100,20,10,125,2097152,0,7,1000,3\n",
            tick * 1000
        ));
    }
    csv
}

#[test]
fn one_hour_metrics_are_from_the_recording_and_baseline_is_not_a_tick() {
    let csv = recording("adapter", 3600);
    let policy = Policy::for_zone(100);
    let report = replay(Cursor::new(csv), &policy).unwrap();
    assert_eq!(report.verdict(), Verdict::TelemetryPass);
    assert_eq!(report.ticks, 3600);
    assert_eq!(report.duration_ms, 3_600_000);
    assert_eq!(report.tick_ms.samples, 3600);
    assert_eq!(report.tick_ms.mean, 10.0);
    assert_eq!(report.tick_p95_ms, Some(10.0));
    assert_eq!(report.cpu_percent.mean, 125.0);
    assert_eq!(report.rss_bytes.max, 2_097_152.0);
    assert_eq!(report.deaths_baseline, Some(7));
    assert_eq!(report.deaths_delta, Some(0));
    assert_eq!(report.human_conflicts_baseline, Some(3));
    assert_eq!(report.human_conflicts_delta, Some(0));
    let mut output = Vec::new();
    report.write_text(&policy, &mut output).unwrap();
    let output = String::from_utf8(output).unwrap();
    assert!(output.contains("source=adapter_declared_unverified\n"));
    assert!(output.contains("recording_authenticity=NOT_VERIFIED\n"));
    assert!(output.contains("live_game_qa=NOT_RUN\n"));
}

#[test]
fn synthetic_short_missing_metrics_or_sparse_endpoints_never_qualify() {
    let policy = Policy::for_zone(100);
    let synthetic = replay(Cursor::new(recording("synthetic", 3600)), &policy).unwrap();
    assert_eq!(synthetic.source, Source::Synthetic);
    assert_eq!(synthetic.verdict(), Verdict::Incomplete);

    let short = replay(Cursor::new(recording("adapter", 1)), &policy).unwrap();
    assert_eq!(short.verdict(), Verdict::Incomplete);

    let sparse = recording("adapter", 1).replace("adapter,1,1000,", "adapter,1,3600000,");
    let sparse = replay(Cursor::new(sparse), &policy).unwrap();
    assert_eq!(sparse.duration_ms, 3_600_000);
    assert_eq!(sparse.verdict(), Verdict::Incomplete);
    assert!(sparse
        .incomplete_reasons
        .iter()
        .any(|reason| reason.contains("gap")));

    let missing = recording("adapter", 3600).replacen(",10,125,2097152,", ",10,,,", 1);
    let missing = replay(Cursor::new(missing), &policy).unwrap();
    assert_eq!(missing.cpu_percent.missing, 1);
    assert_eq!(missing.rss_bytes.missing, 1);
    assert_eq!(missing.verdict(), Verdict::Incomplete);
    assert_eq!(missing.cpu_percent.mean, 125.0);

    let mut wrong_load = policy.clone();
    wrong_load.expected_bots = 21;
    assert_eq!(
        replay(Cursor::new(recording("adapter", 3600)), &wrong_load)
            .unwrap()
            .verdict(),
        Verdict::Incomplete
    );
    let mut shortened = policy;
    shortened.min_duration_ms = 2000;
    assert!(replay(Cursor::new(recording("adapter", 2)), &shortened).is_err());
}

#[test]
fn transient_currency_excursion_and_human_conflicts_cannot_hide() {
    let policy = Policy::for_zone(100);
    let mut csv = recording("adapter", 3600);
    csv = csv.replacen(
        "adapter,1,1000,100,20,10,125,2097152,0,7,1000,3",
        "adapter,1,1000,100,20,10,125,2097152,0,7,1150,3",
        1,
    );
    let report = replay(Cursor::new(csv), &policy).unwrap();
    assert_eq!(report.currency_delta, Some(0));
    assert_eq!(report.max_abs_currency_drift, Some(150));
    assert_eq!(report.verdict(), Verdict::Fail);

    let csv = recording("adapter", 2)
        .replace(",0,7,1000,3\n", ",0,7,1000,4\n")
        .replacen(
            "adapter,0,0,100,20,0,,1048576,0,7,1000,4",
            "adapter,0,0,100,20,0,,1048576,0,7,1000,3",
            1,
        );
    let report = replay(Cursor::new(csv), &policy).unwrap();
    assert_eq!(report.human_conflicts_delta, Some(1));
    // Known violations outrank an incomplete duration in the verdict.
    assert_eq!(report.verdict(), Verdict::Fail);
    assert!(!report.incomplete_reasons.is_empty());
}

#[test]
fn malformed_numbers_sequence_and_counter_resets_are_rejected() {
    let original = recording("adapter", 2);
    let policy = Policy::for_zone(100);
    for (old, new) in [
        (",10,125,", ",NaN,125,"),
        (",10,125,", ",10,inf,"),
        (",10,125,", ",10,-1,"),
        (",0,7,1000,3", ",21,7,1000,3"),
        (",0,7,1000,3", ",0,-1,1000,3"),
        ("adapter,2,2000,", "adapter,2,1000,"),
        ("adapter,2,2000,", "adapter,3,2000,"),
        ("adapter,2,2000,100,20,", "adapter,2,2000,100,19,"),
        ("adapter,2,2000,100,20,", "adapter,2,2000,101,20,"),
        ("adapter,2,2000,", "synthetic,2,2000,"),
        (
            "adapter,2,2000,100,20,10,125,2097152,0,7,1000,3",
            "adapter,2,2000,100,20,10,125,2097152,0,6,1000,3",
        ),
        (",2097152,", ",0,"),
        (",2097152,", ",18446744073709551616,"),
    ] {
        let malformed = original.replace(old, new);
        assert!(
            replay(Cursor::new(malformed), &policy).is_err(),
            "accepted replacement: {old} -> {new}"
        );
    }
    assert!(replay(Cursor::new(""), &policy).is_err());
    assert!(replay(Cursor::new(format!("{CSV_HEADER}\n")), &policy).is_err());
    assert!(replay(Cursor::new(format!("{original}\n")), &policy).is_err());
    assert!(replay(
        Cursor::new(format!("{CSV_HEADER}\n{}", "x".repeat(4097))),
        &policy
    )
    .is_err());
}

#[test]
fn counter_regressions_are_detected_across_missing_rows() {
    let csv = format!("{CSV_HEADER}\nadapter,0,0,100,20,0,,1048576,0,7,1000,3\nadapter,1,1000,100,20,10,100,1048576,0,,1000,\nadapter,2,2000,100,20,10,100,1048576,0,6,1000,3\n");
    let error = replay(Cursor::new(csv), &Policy::for_zone(100)).unwrap_err();
    assert!(error.contains("deaths_total decreased"));
}

#[test]
fn tick_percentile_and_budget_use_completed_ticks_and_nearest_rank() {
    let mut csv = recording("adapter", 20);
    csv = csv.replace(
        "adapter,20,20000,100,20,10,",
        "adapter,20,20000,100,20,100,",
    );
    let report = replay(Cursor::new(csv), &Policy::for_zone(100)).unwrap();
    assert_eq!(report.tick_ms.samples, 20);
    assert_eq!(report.tick_ms.mean, 14.5);
    assert_eq!(report.tick_p95_ms, Some(10.0));
    assert_eq!(report.tick_ms.max, 100.0);
    assert_eq!(report.verdict(), Verdict::Fail);
}
