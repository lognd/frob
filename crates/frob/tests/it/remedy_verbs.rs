//! Every `RemedyCommand::new("frob", "<verb>")` written in a crate's source names a real frob verb.
//!
//! The remedy a refusal prints is a command the reader runs; a verb renamed or removed must fail
//! here rather than leave a remedy pointing at nothing.
#![allow(
    clippy::disallowed_methods,
    reason = "a workspace-wide source scan reads the disk, not a walked Core"
)]

// frob:ticket 01M7X35W2WATD06TP58JC8MS7H
use std::fs;
use std::path::{Path, PathBuf};

use gob_diagnostics::RemedyCommand;

/// Collect every `.rs` file under `dir`.
fn rust_sources(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_sources(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// The string literal opening `text` after optional whitespace, with the text after its closing quote.
fn literal(text: &str) -> Option<(&str, &str)> {
    let rest = text.trim_start().strip_prefix('"')?;
    let end = rest.find('"')?;
    Some((&rest[..end], &rest[end + 1..]))
}

/// The `verb` of every `RemedyCommand::new("frob", "verb")` in `text`; a non-literal verb is skipped.
fn frob_verbs(text: &str) -> Vec<String> {
    const OPEN: &str = "RemedyCommand::new(";
    let mut out = Vec::new();
    for (at, _) in text.match_indices(OPEN) {
        let rest = &text[at + OPEN.len()..];
        let Some((product, rest)) = literal(rest) else {
            continue;
        };
        let Some(rest) = rest.trim_start().strip_prefix(',') else {
            continue;
        };
        if let (Some((verb, _)), "frob") = (literal(rest), product) {
            out.push(verb.to_owned());
        }
    }
    out
}

#[test]
fn the_scanner_reads_a_verb_across_lines_and_skips_other_products() {
    let text = "RemedyCommand::new(\"frob\",\n \"cycle new\").arg(x); RemedyCommand::new(\"git\", \"init\"); RemedyCommand::new(\"frob\", v)";
    assert_eq!(frob_verbs(text), ["cycle new"]);
}

// frob:tests Cli.check_remedy
#[test]
fn every_frob_remedy_names_a_real_verb() {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let cli = frob_cli::cli();
    let mut seen = 0;
    let mut bad = Vec::new();
    for entry in fs::read_dir(&crates).expect("crates dir").flatten() {
        let mut files = Vec::new();
        rust_sources(&entry.path().join("src"), &mut files);
        for file in files {
            let text = fs::read_to_string(&file).unwrap_or_default();
            for verb in frob_verbs(&text) {
                seen += 1;
                if let Err(why) = cli.check_remedy(&RemedyCommand::new("frob", &verb)) {
                    bad.push(format!(
                        "{}: frob {verb}: {why}",
                        file.strip_prefix(&crates)
                            .unwrap_or(&file)
                            .to_string_lossy()
                    ));
                }
            }
        }
    }
    assert!(
        seen >= 30,
        "the scan found only {seen} literal frob remedies"
    );
    assert!(
        bad.is_empty(),
        "remedies naming no real verb:\n{}",
        bad.join("\n")
    );
}
