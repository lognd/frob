//! The shared coverage runner against a fake provider in a temporary repository.

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q

use std::path::{Path, PathBuf};

use frob_evidence::Workspace;
use frob_evidence::coverage::{
    CoverageError, CoveragePlan, CoverageProvider, language_report, run_provider,
};
use frob_evidence::record::{CoverageStatus, Provider};
use gob_exec::Program;

/// A provider whose "tool" is `sh` writing a canned lcov file (or nothing).
struct Fake {
    language: &'static str,
    tool: &'static str,
    script: &'static str,
}

impl CoverageProvider for Fake {
    fn provider(&self) -> Provider {
        Provider::Nextest
    }
    fn language(&self) -> &'static str {
        self.language
    }
    fn required_tool(&self) -> &'static str {
        self.tool
    }
    fn has_tests(&self, _root: &Path) -> bool {
        true
    }
    fn plan(
        &self,
        ws: &Workspace,
        _reference: &str,
        out_dir: &Path,
    ) -> Result<CoveragePlan, CoverageError> {
        Ok(CoveragePlan {
            program: Program::Tool {
                name: "sh".to_owned(),
            },
            args: vec!["-c".to_owned(), self.script.to_owned()],
            cwd: ws.root.clone(),
            env: Vec::new(),
            report: out_dir.join("raw.info"),
        })
    }
    fn to_lcov(&self, _ws: &Workspace, plan: &CoveragePlan) -> Result<String, CoverageError> {
        std::fs::read_to_string(&plan.report)
            .map_err(|_| CoverageError::NoReport(gob_path::Shown::of(&plan.report).to_string()))
    }
}

fn workspace() -> (tempfile::TempDir, Workspace) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p: PathBuf = dir.path().to_path_buf();
    gob_git::Repo::init(&p).expect("init");
    std::fs::write(
        p.join("frob.toml"),
        "[evidence]\nallowed_tools = [\"sh\"]\n",
    )
    .expect("toml");
    let ws = Workspace::open(&p, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace");
    (dir, ws)
}

// frob:tests run_provider
#[test]
fn two_languages_merge_into_one_lcov_file() {
    let (dir, ws) = workspace();
    let a = Fake {
        language: "alpha",
        tool: "sh",
        script: "printf 'SF:src/a.rs\\nDA:1,1\\nend_of_record\\n' > .frob/coverage/raw/alpha/raw.info",
    };
    let b = Fake {
        language: "beta",
        tool: "sh",
        script: "printf 'SF:src/b.py\\nDA:2,0\\nend_of_record\\n' > .frob/coverage/raw/beta/raw.info",
    };
    let sa = run_provider(&ws, &a, "x");
    let sb = run_provider(&ws, &b, "x");
    assert_eq!(sa.status, CoverageStatus::Measured, "{sa:?}");
    assert_eq!(sb.status, CoverageStatus::Measured, "{sb:?}");
    assert!(language_report(dir.path(), "alpha").is_file());
    let merged = std::fs::read_to_string(dir.path().join("lcov.info")).expect("merged");
    assert!(
        merged.contains("SF:src/a.rs") && merged.contains("SF:src/b.py"),
        "{merged}"
    );
    assert_eq!((sb.lines_hit, sb.lines_found), (0, 1));
}

// frob:tests run_provider
#[test]
fn a_missing_tool_is_not_run() {
    let (_dir, ws) = workspace();
    let p = Fake {
        language: "gamma",
        tool: "frob-no-such-coverage-tool",
        script: "true",
    };
    let s = run_provider(&ws, &p, "x");
    assert_eq!(s.status, CoverageStatus::NotRun, "{s:?}");
}

// frob:tests run_provider
#[test]
fn a_tool_that_leaves_no_report_is_a_missing_report() {
    let (dir, ws) = workspace();
    let p = Fake {
        language: "delta",
        tool: "sh",
        script: "true",
    };
    let s = run_provider(&ws, &p, "x");
    assert_eq!(s.status, CoverageStatus::MissingReport, "{s:?}");
    assert!(!language_report(dir.path(), "delta").exists());
}

fn parse(args: &[&str]) -> Result<frob_evidence::verbs::CaptureArgs, gob_cli::CliError> {
    let cmd = frob_evidence::verbs::capture_args(gob_cli::clap::Command::new("t"));
    let m = cmd
        .try_get_matches_from(std::iter::once("t").chain(args.iter().copied()))
        .expect("clap");
    frob_evidence::verbs::CaptureArgs::from_matches(&m)
}

// frob:tests CaptureArgs.from_flags
#[test]
fn the_coverage_flag_is_accepted_for_test_providers_only() {
    let ok = parse(&["--provider", "nextest", "--ref", "-p x", "--coverage"]).expect("nextest");
    assert!(ok.coverage);
    assert!(
        !parse(&["--provider", "nextest", "--ref", "-p x"])
            .expect("plain")
            .coverage
    );
    assert!(parse(&["--provider", "file", "--ref", "a", "--coverage"]).is_err());
    assert!(parse(&["--provider", "command", "--ref", "a", "--coverage"]).is_err());
}
