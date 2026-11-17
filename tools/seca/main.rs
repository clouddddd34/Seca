mod ledger;
mod replay;

use serde_json::Value;
use std::{
    env,
    fs::OpenOptions,
    io::{Read, Write},
    path::Path,
};

type Result<T> = std::result::Result<T, String>;

fn read_json(path: &str) -> Result<Value> {
    let file = std::fs::File::open(path).map_err(|_| "Cannot read JSON file".to_string())?;
    let mut bytes = Vec::new();
    file.take(2 * 1024 * 1024 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "Cannot read JSON file")?;
    if bytes.len() > 2 * 1024 * 1024 {
        return Err("JSON input exceeds 2 MiB".into());
    }
    serde_json::from_slice(&bytes).map_err(|_| "Invalid JSON file".into())
}

fn write_new(path: &str, value: &Value) -> Result<()> {
    // Never replace a report, follow an existing symlink, or overwrite input.
    let data = serde_json::to_vec_pretty(value).map_err(|_| "Cannot encode JSON")?;
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options
        .open(Path::new(path))
        .map_err(|_| "Output must be a new writable file")?;
    file.write_all(&data)
        .and_then(|_| file.write_all(b"\n"))
        .and_then(|_| file.sync_all())
        .map_err(|_| "Cannot finish output file".into())
}

fn run(args: &[String]) -> Result<()> {
    match args.first().map(String::as_str) {
        Some("log-init") if args.len() == 4 => {
            let log = ledger::new_log(&args[2], &args[3]);
            ledger::validate_log(&log)?;
            write_new(&args[1], &log)
        }
        Some("log-check") if args.len() == 2 => {
            ledger::validate_log(&read_json(&args[1])?)?;
            println!("Record structure is valid; evidence truth has not been verified.");
            Ok(())
        }
        Some("log-add") if args.len() == 4 => {
            let mut log = read_json(&args[1])?;
            ledger::validate_log(&log)?;
            let finding = read_json(&args[2])?;
            ledger::validate_finding(&finding)?;
            log["findings"]
                .as_array_mut()
                .ok_or("Missing findings")?
                .push(finding);
            ledger::validate_log(&log)?;
            write_new(&args[3], &log)
        }
        Some("replay") if args.len() >= 3 => {
            let flags = &args[3..];
            if flags
                .iter()
                .any(|s| s != "--authorized" && s != "--allow-remote")
            {
                return Err("Unknown replay option".into());
            }
            if !flags.iter().any(|s| s == "--authorized") {
                return Err(
                    "Replay requires --authorized for a target you have permission to test".into(),
                );
            }
            if Path::new(&args[2]).symlink_metadata().is_ok() {
                return Err("Output already exists; no requests sent".into());
            }
            let config = read_json(&args[1])?;
            let report = replay::execute(config, flags.iter().any(|s| s == "--allow-remote"))?;
            let failed = report["observations"]
                .as_array()
                .unwrap()
                .iter()
                .any(|o| o.get("error").is_some());
            write_new(&args[2], &report)?;
            if failed {
                Err("One or more requests failed; see the report. This is not a clean scan.".into())
            } else {
                Ok(())
            }
        }
        _ => Err(concat!(
            "Usage:\n",
            "  seca replay CONFIG.json NEW-REPORT.json --authorized [--allow-remote]\n",
            "  seca log-init NEW-LOG.json TARGET SCOPE\n",
            "  seca log-add LOG.json FINDING.json NEW-LOG.json\n",
            "  seca log-check LOG.json\n",
            "Replay sends GET requests only. Flags declare scope; they do not establish ownership."
        )
        .into()),
    }
}

fn main() {
    if let Err(error) = run(&env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
