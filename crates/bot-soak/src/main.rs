use bot_soak::{replay, Policy};
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

const HELP: &str = "bot-soak 0.1.0 — offline per-tick telemetry validation\n\nUsage: bot-soak replay FILE --zone ID [OPTIONS]\n\nOptions:\n  --expected-bots N                 Required constant load (default: 20)\n  --min-duration-secs N             At least 3600 (default: 3600)\n  --max-gap-ms N                    Coverage gap, 1..1000 (default: 1000)\n  --tick-budget-ms N                Maximum recorded tick time (default: 50)\n  --max-abs-currency-drift N        Maximum deviation from baseline (default: 0)\n  --help                           Print this help\n  --version                        Print the version\n\nReads a strict bot-soak-v1 CSV; see docs/BOT_SOAK.md. CPU/RAM come from\nthe recording. No bots are spawned and no live server is contacted.\nExit: 0 telemetry within limits; 2 input/usage error; 3 incomplete; 4 failed.\nA telemetry pass never verifies recording authenticity or live Game QA.\n";

fn main() {
    match run() {
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("bot-soak: {error}");
            std::process::exit(2);
        }
    }
}

fn run() -> Result<i32, String> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() == 1 && args[0] == "--help" {
        print!("{HELP}");
        return Ok(0);
    }
    if args.len() == 1 && args[0] == "--version" {
        println!("bot-soak {}", env!("CARGO_PKG_VERSION"));
        return Ok(0);
    }
    if args.len() < 4 || args[0] != "replay" {
        return Err("expected replay FILE --zone ID; use --help for the telemetry contract".into());
    }
    let path = PathBuf::from(&args[1]);
    let mut policy = Policy::for_zone(0);
    let mut seen = std::collections::HashSet::new();
    let mut index = 2;
    while index < args.len() {
        let key = args[index].to_str().ok_or("option name must be UTF-8")?;
        if !seen.insert(key.to_owned()) {
            return Err(format!("duplicate option {key}"));
        }
        let value = args
            .get(index + 1)
            .and_then(|arg| arg.to_str())
            .ok_or_else(|| format!("missing numeric value for {key}"))?;
        match key {
            "--zone" => policy.zone_id = number(value, key)?,
            "--expected-bots" => policy.expected_bots = number(value, key)?,
            "--min-duration-secs" => {
                policy.min_duration_ms = number::<u64>(value, key)?
                    .checked_mul(1000)
                    .ok_or("duration is out of range")?;
            }
            "--max-gap-ms" => policy.max_gap_ms = number(value, key)?,
            "--tick-budget-ms" => policy.max_tick_ms = number(value, key)?,
            "--max-abs-currency-drift" => policy.max_abs_currency_drift = number(value, key)?,
            _ => return Err(format!("unknown option {key}")),
        }
        index += 2;
    }
    if !seen.contains("--zone") {
        return Err("--zone is required".into());
    }
    policy.validate()?;
    let file = File::open(&path).map_err(|error| format!("{}: {error}", path.display()))?;
    let report = replay(BufReader::new(file), &policy)?;
    report
        .write_text(&policy, std::io::stdout().lock())
        .map_err(|error| format!("writing report: {error}"))?;
    Ok(report.verdict().exit_code())
}

fn number<T: std::str::FromStr>(value: &str, option: &str) -> Result<T, String> {
    value
        .parse()
        .map_err(|_| format!("invalid numeric value for {option}"))
}
