//! Running the selected tests: `cargo nextest run -p <pkg> -E '<filter>'` through gob-exec.

use std::collections::BTreeMap;
use std::path::PathBuf;
use std::time::Duration;

use frob_evidence::provider::{Capture, run_nextest};
use gob_exec::Runner;

use crate::error::Result;
use crate::select::TestTarget;

/// How to run: where, how long, and whether to run everything.
#[derive(Debug, Clone)]
pub struct RunOptions {
    /// The work tree root cargo runs in.
    pub root: PathBuf,
    /// Wall-clock limit for the nextest process.
    pub timeout: Duration,
    /// `--profile` for nextest; empty passes none.
    pub profile: String,
    /// Run the whole workspace instead of the selection.
    pub all: bool,
}

/// What a run produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunReport {
    /// The nextest filter arguments that were used (after `cargo nextest run`).
    pub args: Vec<String>,
    /// Verdict, executed test names and the redacted transcript.
    pub capture: Capture,
}

/// The filter arguments for `selected`: `-p` per package plus one `-E` filterset.
///
/// The filterset pairs each package with its own tests, so equal test names in
/// different packages do not drag each other in:
/// `(package(=a) & (test(=x) | test(=y))) | (package(=b) & test(=z))`.
pub fn nextest_args(selected: &[TestTarget]) -> Vec<String> {
    let mut by_pkg: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for t in selected {
        by_pkg.entry(&t.package).or_default().push(&t.test_path);
    }
    let mut args = Vec::new();
    for pkg in by_pkg.keys() {
        args.extend(["-p".to_owned(), (*pkg).to_owned()]);
    }
    let expr = by_pkg
        .iter()
        .map(|(pkg, tests)| {
            let any = tests
                .iter()
                .map(|t| format!("test(={t})"))
                .collect::<Vec<_>>()
                .join(" | ");
            format!("(package(={pkg}) & ({any}))")
        })
        .collect::<Vec<_>>()
        .join(" | ");
    args.extend(["-E".to_owned(), expr]);
    args
}

/// Quote `args` so [`frob_evidence::provider::split_args`] reads them back unchanged.
pub fn join_args(args: &[String]) -> String {
    args.iter()
        .map(|a| {
            if a.is_empty() || a.contains(char::is_whitespace) || a.contains(['\'', '"']) {
                format!("'{a}'")
            } else {
                a.clone()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Run `selected` (or the whole workspace with `opts.all`) with cargo nextest.
///
/// # Errors
///
/// [`crate::TestsError::Evidence`] or [`crate::TestsError::Exec`] when cargo cannot be started.
pub fn run(runner: &Runner, selected: &[TestTarget], opts: &RunOptions) -> Result<RunReport> {
    let args = if opts.all {
        vec!["--workspace".to_owned()]
    } else {
        nextest_args(selected)
    };
    tracing::info!(all = opts.all, tests = selected.len(), "running nextest");
    let capture = run_nextest(runner, &opts.root, &args, &opts.profile, opts.timeout)?;
    Ok(RunReport { args, capture })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(package: &str, test_path: &str) -> TestTarget {
        TestTarget {
            package: package.into(),
            test_path: test_path.into(),
            symref: String::new(),
        }
    }

    #[test]
    fn filters_pair_each_package_with_its_tests() {
        let args = nextest_args(&[t("a", "tests::x"), t("a", "tests::y"), t("b", "tests::x")]);
        assert_eq!(
            args,
            [
                "-p",
                "a",
                "-p",
                "b",
                "-E",
                "(package(=a) & (test(=tests::x) | test(=tests::y))) | (package(=b) & (test(=tests::x)))"
            ]
        );
        let joined = join_args(&args);
        assert_eq!(frob_evidence::provider::split_args(&joined).unwrap(), args);
    }
}
