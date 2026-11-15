//! Explicit two-second synthetic example, never a live capture or soak pass.
use bot_soak::recording::{RecordingWriter, Sample};
use bot_soak::Source;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let baseline = Sample {
        source: Source::Synthetic,
        tick: 0,
        elapsed_ms: 0,
        zone_id: 100,
        bots: 20,
        tick_ms: 0.0,
        cpu_percent: None,
        rss_bytes: Some(1_048_576),
        stuck_bots: Some(0),
        deaths_total: Some(7),
        bot_currency_units: Some(1_000),
        human_target_conflicts_total: Some(3),
    };
    let mut writer = RecordingWriter::new(std::io::stdout().lock(), baseline)?;
    for tick in 1..=2 {
        writer.record(Sample {
            tick,
            elapsed_ms: tick * 1_000,
            tick_ms: 10.0,
            cpu_percent: Some(125.0),
            ..baseline
        })?;
    }
    writer.finish()?;
    Ok(())
}
