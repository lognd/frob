//! Markdown corpora for the `MDL` rules, run through the whole `grimble check`.
//!
//! A block is a small repository: text before the first `=== path` line is the block's own file, and
//! each `=== path` line starts a further file (text up to the next `===` line). A repository without a
//! `grimble.toml` gets an empty one, so every file declaring `module` is a model root.

// frob:ticket 01M4YBK89X612WGJ1QEAVEK5C9

use std::path::Path;

use gob_mdtest::Case;
use gob_rules::Finding;
use grimble_check::{CheckOptions, run};

/// Split a block into `(path, text)` files; text before the first `===` line is the block's own file.
fn files(case: &Case) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut current = (case.file_name.clone(), String::new());
    for line in case.text.split_inclusive('\n') {
        if let Some(head) = line.strip_prefix("=== ") {
            if !current.1.is_empty() {
                out.push(current);
            }
            current = (head.trim().to_owned(), String::new());
        } else {
            current.1.push_str(line);
        }
    }
    if !current.1.is_empty() {
        out.push(current);
    }
    out
}

/// Write one file under `root`, creating its directories.
fn write_file(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

/// Build the block's repository, check it and keep the findings of the rule under test.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let files = files(case);
    if !files.iter().any(|(p, _)| p == "grimble.toml") {
        write_file(root, "grimble.toml", "");
    }
    for (path, text) in &files {
        write_file(root, path, text);
    }
    tracing::debug!(rule = %case.rule, files = files.len(), "MDL corpus block");
    run(root, &CheckOptions::default())
        .expect("check runs")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
