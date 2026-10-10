//! Selection, dry-run and a real nextest run against a tiny two-crate cargo workspace.

use std::path::Path;

use frob_evidence::events;
use frob_evidence::guard::EvidenceGuard;
use frob_ledger::model::{Outcome, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use frob_tests::{TestTarget, build_repo_graph, select_tests, touched_set};
use gob_git::Repo;

mod common;
use common::{git, write};

const ALPHA: &str = r"pub fn double(x: i32) -> i32 {
    x * 2
}

pub fn triple(x: i32) -> i32 {
    x * 3
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doubles() {
        assert_eq!(double(2), 4);
    }

    #[test]
    fn triples() {
        assert_eq!(triple(2), 6);
    }
}
";

const BETA: &str = r"pub fn quad(x: i32) -> i32 {
    alpha::double(alpha::double(x))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quads() {
        assert_eq!(quad(1), 4);
    }

    #[test]
    fn unrelated() {
        assert!(true);
    }
}
";

const BETA_IT: &str = r"#[test]
fn integration_quad() {
    assert_eq!(beta::quad(2), 8);
}
";

/// Two crates (`beta` depends on `alpha`), committed on `main`; returns the dir and the base commit.
fn fixture() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(p, ".gitignore", "target/\n");
    write(
        p,
        "Cargo.toml",
        "[workspace]\nmembers = [\"alpha\", \"beta\"]\nresolver = \"2\"\n",
    );
    write(
        p,
        "alpha/Cargo.toml",
        "[package]\nname = \"alpha\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
    );
    write(p, "alpha/src/lib.rs", ALPHA);
    write(
        p,
        "beta/Cargo.toml",
        "[package]\nname = \"beta\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\nalpha = { path = \"../alpha\" }\n",
    );
    write(p, "beta/src/lib.rs", BETA);
    write(p, "beta/tests/it.rs", BETA_IT);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

fn change_double(root: &Path) {
    write(root, "alpha/src/lib.rs", &ALPHA.replace("x * 2", "x + x"));
}

fn names(selected: &[TestTarget]) -> Vec<String> {
    selected.iter().map(TestTarget::plan_line).collect()
}

#[test]
fn only_tests_reaching_the_changed_function_are_selected() {
    let (dir, base) = fixture();
    change_double(dir.path());
    let repo = Repo::discover(dir.path()).expect("repo");
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert_eq!(touched.files, ["alpha/src/lib.rs"]);
    assert!(touched.unresolved_files.is_empty());
    assert!(touched.selection_findings().is_empty());
    let symbols: Vec<String> = touched.symbols.iter().map(ToString::to_string).collect();
    assert_eq!(
        symbols,
        ["alpha/src/lib.rs::double"],
        "only `double` changed"
    );
    let selected = select_tests(dir.path(), &graph, &touched);
    assert_eq!(
        names(&selected),
        [
            "alpha tests::doubles",
            "beta integration_quad",
            "beta tests::quads"
        ],
        "triples and unrelated must not be selected"
    );
}

// frob:tests crates/frob-tests/src/touched.rs::selection_findings
#[test]
fn a_changed_file_with_no_adapter_is_unresolved_not_ignored() {
    let (dir, base) = fixture();
    write(dir.path(), "tools/gen.lua", "print(1)\n");
    write(dir.path(), "README.md", "# Notes\n");
    let repo = Repo::discover(dir.path()).expect("repo");
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert_eq!(
        touched.unresolved_files,
        ["tools/gen.lua"],
        "markdown has an adapter"
    );
    let findings = touched.selection_findings();
    assert_eq!(findings.len(), 1);
    assert_eq!(findings[0].rule.as_str(), "TEST001");
    assert_eq!(findings[0].severity, gob_rules::Severity::Unresolved);
    assert!(findings[0].message.contains("tools/gen.lua"));
}

#[test]
fn an_untouched_tree_selects_nothing_and_a_touched_test_file_selects_its_tests() {
    let (dir, base) = fixture();
    let repo = Repo::discover(dir.path()).expect("repo");
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert!(touched.files.is_empty());
    assert!(select_tests(dir.path(), &graph, &touched).is_empty());

    write(
        dir.path(),
        "beta/tests/it.rs",
        &format!("{BETA_IT}\n// touched\n"),
    );
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert_eq!(
        names(&select_tests(dir.path(), &graph, &touched)),
        ["beta integration_quad"]
    );
}

fn cli() -> gob_cli::Cli {
    frob_tests::register(frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0")))
}

#[test]
fn dry_run_prints_the_selection_and_runs_nothing() {
    let (dir, base) = fixture();
    change_double(dir.path());
    let (code, out, err) = gob_cli::run_for_test(
        &cli(),
        &["--text", "test", "--base", &base, "--dry-run"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    for line in [
        "alpha tests::doubles",
        "beta tests::quads",
        "beta integration_quad",
    ] {
        assert!(out.contains(&format!("- {line}")), "missing {line}:\n{out}");
    }
    assert!(
        !out.contains("tests::triples") && !out.contains("unrelated"),
        "{out}"
    );
    assert!(out.contains("ran: false"), "{out}");
    assert!(
        !dir.path().join("target").exists(),
        "dry run must not build"
    );
}

#[test]
fn test_verb_runs_the_selection_and_appends_evidence_in_a_leased_worktree() {
    let (dir, base) = fixture();
    let p = dir.path();
    let ledger = Ledger::open(
        Repo::discover(p).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut req = NewTicket::new("Speed up double", TicketType::Task);
    req.acceptance = vec!["double is fast".into()];
    let applied = ledger.new_ticket(req).expect("ticket");
    let id = applied.ticket.front.id;
    // A lease file shaped like frob-lease's: `ticket` and `holder.worktree`.
    let leases = p.join(".git/frob/leases");
    std::fs::create_dir_all(&leases).expect("leases dir");
    std::fs::write(
        leases.join("lease.toml"),
        // A TOML literal string: a Windows path's backslashes are not escapes in it.
        format!(
            "ticket = \"{id}\"\n\n[holder]\nworktree = '{}'\n",
            p.display()
        ),
    )
    .expect("lease");
    // The outer `cargo nextest run --profile ci` leaks NEXTEST_PROFILE into the child, and
    // the fixture has no such profile, so pin the profile through the config knob.
    write(
        p,
        "frob.toml",
        "[evidence]\nnextest_profile = \"default\"\n",
    );
    change_double(p);

    let cli = cli();
    let (code, out, err) = gob_cli::run_for_test(&cli, &["--json", "test", "--base", &base], p);
    assert_eq!(code, 0, "{out}{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(v["data"]["passed"], true, "{out}");
    let executed: Vec<&str> = v["data"]["executed"]
        .as_array()
        .expect("executed")
        .iter()
        .filter_map(|n| n.as_str())
        .collect();
    assert!(executed.contains(&"tests::doubles"), "{executed:?}");
    assert!(executed.contains(&"tests::quads"), "{executed:?}");
    assert!(executed.contains(&"integration_quad"), "{executed:?}");
    assert!(!executed.contains(&"tests::triples"), "{executed:?}");
    assert!(!executed.contains(&"tests::unrelated"), "{executed:?}");
    assert!(v["data"]["evidence"]["event"].is_string(), "{out}");

    let stored = events::list(&ledger, id).expect("evidence");
    assert_eq!(stored.len(), 1);
    assert_eq!(stored[0].record.passed, Some(true));
    assert!(
        stored[0]
            .record
            .tests
            .contains(&"tests::doubles".to_owned())
    );

    // The recorded run now satisfies the close guard.
    let store = frob_evidence::Workspace::open(p, std::sync::Arc::new(gob_time::SystemClock))
        .expect("ws")
        .store;
    let guard = EvidenceGuard::for_ticket(&ledger, &store, id).expect("guard");
    ledger
        .close(id, Some(Outcome::Done), None, &[&guard])
        .expect("close with measured evidence");
}

const CALC: &str = "def double(x):
    return x * 2


def triple(x):
    return x * 3
";

const TEST_CALC: &str = "from pkg.calc import double, triple


def test_double():
    assert double(2) == 4


def test_triple():
    assert triple(2) == 6


class TestKit:
    def test_method(self):
        assert double(1) == 2

    def test_other(self):
        assert triple(1) == 3
";

/// A Python project (`pkg/calc.py`, `tests/test_calc.py`), committed on `main`; returns the dir and the base commit.
fn python_fixture() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    write(p, "pkg/__init__.py", "");
    write(p, "conftest.py", "");
    write(p, "pkg/calc.py", CALC);
    write(p, "tests/test_calc.py", TEST_CALC);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    let base = git(p, &["rev-parse", "HEAD"]);
    (dir, base)
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
#[test]
fn a_changed_python_function_selects_the_pytest_tests_reaching_it() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = python_fixture();
    write(dir.path(), "pkg/calc.py", &CALC.replace("x * 2", "x + x"));
    let repo = Repo::discover(dir.path()).expect("repo");
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert_eq!(touched.files, ["pkg/calc.py"]);
    assert!(
        touched.unresolved_files.is_empty(),
        "Python files are resolved now: {:?}",
        touched.unresolved_files
    );
    assert!(touched.selection_findings().is_empty());
    let selected = select_tests(dir.path(), &graph, &touched);
    assert_eq!(
        names(&selected),
        [
            "pytest tests/test_calc.py::TestKit::test_method",
            "pytest tests/test_calc.py::test_double"
        ],
        "triple tests must not be selected"
    );
    assert!(
        selected
            .iter()
            .all(|t| t.framework == frob_tests::Framework::Pytest)
    );
    assert_eq!(
        frob_tests::pytest_args(&selected),
        [
            "tests/test_calc.py::TestKit::test_method",
            "tests/test_calc.py::test_double"
        ]
    );
    assert!(frob_tests::nextest_args(&selected).is_empty());
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
#[test]
fn a_touched_python_test_file_selects_its_tests() {
    // frob:tests crates/frob-tests/src/select.rs::select_tests
    let (dir, base) = python_fixture();
    write(
        dir.path(),
        "tests/test_calc.py",
        &format!("{TEST_CALC}\n# touched\n"),
    );
    let repo = Repo::discover(dir.path()).expect("repo");
    let graph = build_repo_graph(dir.path()).expect("graph");
    let touched = touched_set(&repo, &graph, &base).expect("touched");
    assert_eq!(select_tests(dir.path(), &graph, &touched).len(), 4);
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
#[test]
fn python_dry_run_lists_pytest_node_ids_and_runs_nothing() {
    // frob:tests crates/frob-tests/src/verb.rs::TestVerb
    let (dir, base) = python_fixture();
    write(
        dir.path(),
        "pkg/calc.py",
        &CALC.replace("x * 3", "x + x + x"),
    );
    let (code, out, err) = gob_cli::run_for_test(
        &cli(),
        &["--text", "test", "--base", &base, "--dry-run"],
        dir.path(),
    );
    assert_eq!(code, 0, "{out}{err}");
    assert!(
        out.contains("- pytest tests/test_calc.py::test_triple"),
        "{out}"
    );
    assert!(
        out.contains("- pytest tests/test_calc.py::TestKit::test_other"),
        "{out}"
    );
    assert!(!out.contains("test_double"), "{out}");
    assert!(out.contains("ran: false"), "{out}");
}

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
#[test]
fn dry_run_prints_the_resolved_pytest_runner() {
    // frob:tests crates/frob-tests/src/verb.rs::TestVerb
    let (dir, base) = python_fixture();
    write(
        dir.path(),
        "pkg/calc.py",
        &CALC.replace("x * 3", "x + x + x"),
    );
    let dry = |dir: &Path| {
        let (code, out, err) = gob_cli::run_for_test(
            &cli(),
            &["--json", "test", "--base", &base, "--dry-run"],
            dir,
        );
        assert_eq!(code, 0, "{out}{err}");
        let v: serde_json::Value = serde_json::from_str(&out).expect("json");
        v["data"]["pytest_runner"]
            .as_str()
            .expect("runner")
            .to_owned()
    };
    assert_eq!(dry(dir.path()), "pytest");
    write(dir.path(), ".venv/bin/python", "");
    assert_eq!(dry(dir.path()), ".venv/bin/python -m pytest");
    write(
        dir.path(),
        "frob.toml",
        "[tests]\npython = \"python3.12\"\n",
    );
    assert_eq!(dry(dir.path()), "python3.12 -m pytest");
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
#[test]
fn test_verb_runs_selected_pytest_tests_and_appends_pytest_evidence() {
    // frob:tests crates/frob-tests/src/verb.rs::TestVerb
    if !gob_testsupport::python_test_prerequisites(
        "test_verb_runs_selected_pytest_tests_and_appends_pytest_evidence",
    ) {
        return;
    }
    let (dir, base) = python_fixture();
    let p = dir.path();
    let ledger = Ledger::open(
        Repo::discover(p).expect("repo"),
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut req = NewTicket::new("Speed up double", TicketType::Task);
    req.acceptance = vec!["double is fast".into()];
    let id = ledger.new_ticket(req).expect("ticket").ticket.front.id;
    let leases = p.join(".git/frob/leases");
    std::fs::create_dir_all(&leases).expect("leases dir");
    std::fs::write(
        leases.join("lease.toml"),
        format!(
            "ticket = \"{id}\"\n\n[holder]\nworktree = '{}'\n",
            p.display()
        ),
    )
    .expect("lease");
    write(p, "pkg/calc.py", &CALC.replace("x * 2", "x + x"));

    let (code, out, err) = gob_cli::run_for_test(&cli(), &["--json", "test", "--base", &base], p);
    assert_eq!(code, 0, "{out}{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(v["data"]["passed"], true, "{out}");
    let executed: Vec<&str> = v["data"]["executed"]
        .as_array()
        .expect("executed")
        .iter()
        .filter_map(|n| n.as_str())
        .collect();
    assert_eq!(
        executed,
        [
            "tests/test_calc.py::TestKit::test_method",
            "tests/test_calc.py::test_double"
        ],
        "{out}"
    );
    let stored = events::list(&ledger, id).expect("evidence");
    assert_eq!(stored.len(), 1);
    assert_eq!(
        stored[0].record.provider,
        frob_evidence::record::Provider::Pytest
    );
    assert_eq!(stored[0].record.passed, Some(true));
}
