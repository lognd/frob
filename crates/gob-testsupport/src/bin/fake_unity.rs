//! A stand-in Unity editor for the unity evidence provider tests (no Unity install needed).
//!
//! It reads its behaviour from files in the directory named by `-projectPath` (the current directory
//! when absent): `fake-unity.log` is printed to stdout (a license failure, say); `fake-unity.lock`
//! makes it print Unity's "another instance is running with this project open" line and exit 1;
//! `fake-unity.<Platform>.xml` (else `fake-unity.xml`) is copied to `-testResults` (no such file means
//! no results, as when a filter matches nothing); `fake-unity.exit` is the exit code (0 when absent).
//! Its argument vector is echoed to stdout first.

use std::path::PathBuf;
use std::process::ExitCode;

/// The value following `flag` in `args`.
fn value_of<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
    let at = args.iter().position(|a| a == flag)?;
    args.get(at + 1).map(String::as_str)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    println!("fake-unity args: {}", args.join(" "));
    let project = PathBuf::from(value_of(&args, "-projectPath").unwrap_or("."));
    if let Ok(log) = std::fs::read_to_string(project.join("fake-unity.log")) {
        println!("{log}");
    }
    if project.join("fake-unity.lock").exists() {
        println!("It looks like another Unity instance is running with this project open.");
        return ExitCode::from(1);
    }
    let platform = value_of(&args, "-testPlatform").unwrap_or("EditMode");
    let xml = std::fs::read(project.join(format!("fake-unity.{platform}.xml")))
        .or_else(|_| std::fs::read(project.join("fake-unity.xml")));
    if let (Ok(xml), Some(results)) = (xml, value_of(&args, "-testResults"))
        && let Err(e) = std::fs::write(results, xml)
    {
        eprintln!("fake-unity: cannot write the results: {e}");
        return ExitCode::from(2);
    }
    let code = std::fs::read_to_string(project.join("fake-unity.exit"))
        .ok()
        .and_then(|t| t.trim().parse::<u8>().ok())
        .unwrap_or(0);
    ExitCode::from(code)
}
