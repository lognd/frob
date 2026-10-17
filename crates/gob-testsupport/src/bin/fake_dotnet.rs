//! A stand-in `dotnet` executable for the dotnet evidence provider tests.
//!
//! `--version` prints a version and exits 0. `test ...` reads `fake-dotnet.trx` in the working
//! directory and copies it to `<--results-directory>/<LogFileName of --logger trx;LogFileName=...>`
//! (no such file means no report, as when a filter matches nothing), echoes its argument vector to
//! stdout and exits with the number in `fake-dotnet.exit` (0 when that file is absent).
//!
//! Also stands in for a Unity editor: `-runTests ...` copies `fake-unity.xml` (when present) to the
//! `-testResults` path and exits with the number in `fake-unity.exit` (0 when absent), leaving
//! `fake-dotnet.exit` to drive the license probe alone.

use std::path::PathBuf;
use std::process::ExitCode;

/// The value following `flag` in `args`.
fn value_of<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
    let at = args.iter().position(|a| a == flag)?;
    args.get(at + 1).map(String::as_str)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("--version") {
        println!("8.0.100");
        return ExitCode::SUCCESS;
    }
    if args.iter().any(|a| a == "-runTests") {
        println!("fake-unity args: {}", args.join(" "));
        if let (Ok(xml), Some(path)) = (
            std::fs::read("fake-unity.xml"),
            value_of(&args, "-testResults"),
        ) && let Err(e) = std::fs::write(path, xml)
        {
            eprintln!("fake-unity: cannot write the results: {e}");
            return ExitCode::from(2);
        }
        let code = std::fs::read_to_string("fake-unity.exit")
            .ok()
            .and_then(|t| t.trim().parse::<u8>().ok())
            .unwrap_or(0);
        return ExitCode::from(code);
    }
    println!("fake-dotnet args: {}", args.join(" "));
    if let Ok(trx) = std::fs::read("fake-dotnet.trx") {
        let file = value_of(&args, "--logger")
            .and_then(|l| l.split(';').find_map(|p| p.strip_prefix("LogFileName=")))
            .unwrap_or("fake.trx");
        let dir = PathBuf::from(value_of(&args, "--results-directory").unwrap_or("."));
        if let Err(e) = std::fs::write(dir.join(file), trx) {
            eprintln!("fake-dotnet: cannot write the report: {e}");
            return ExitCode::from(2);
        }
    } else {
        println!("No test matches the given testcase filter");
    }
    let code = std::fs::read_to_string("fake-dotnet.exit")
        .ok()
        .and_then(|t| t.trim().parse::<u8>().ok())
        .unwrap_or(0);
    ExitCode::from(code)
}
