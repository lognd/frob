//! Multi-file scenarios, exceptions, registry facts and the per-file entry point.

mod common;

use frob_obligations::{InvariantsConfig, collect, evaluate_file};
use gob_lock::{LockEntry, LockFile};
use gob_rules::{ExceptionKind, Finding, Registry, Severity};
use gob_symbols::Symref;

const DEFER_PREFIX: &str = "/* frob:defer COV001 because=\"split after the parser lands\" ticket=";

fn count(findings: &[Finding], rule: &str) -> usize {
    findings.iter().filter(|f| f.rule.as_str() == rule).count()
}

fn defaults() -> InvariantsConfig {
    InvariantsConfig::load(tempfile::tempdir().expect("tempdir").path()).expect("defaults")
}

/// A lock holding a fresh entry for `symref` of the tree at `root`.
fn lock_for(root: &std::path::Path, symref: &Symref) -> LockFile {
    let collected = collect(root).expect("collect");
    let rec = collected.graph.get(symref).expect("symbol in graph");
    let mut lock = LockFile::default();
    lock.entries.insert(
        symref.to_string(),
        LockEntry::new(
            &rec.digests.sig.to_string(),
            &rec.digests.body.to_string(),
            &rec.digests.doc.to_string(),
            "tester",
            "2026-10-02T00:00:00Z",
        ),
    );
    lock
}

#[test]
fn defer_bound_to_a_done_ticket_raises_exc003_and_lists_the_suppressed_finding() {
    let t = common::shared_tickets();
    let dir = tempfile::tempdir().expect("tempdir");
    let text = format!(
        "{DEFER_PREFIX}{} */\n/// Does f.\npub fn f() {{}}\n",
        t.done
    );
    common::write_tree(dir.path(), &[("src/lib.rs", &text)]);
    let ev = common::evaluate_tree(dir.path(), Some(&t.ledger), &defaults(), None);
    assert_eq!(
        count(&ev.findings, "EXC003"),
        1,
        "{:?}",
        common::ids(&ev.findings)
    );
    assert_eq!(count(&ev.findings, "COV001"), 0);
    assert_eq!(ev.suppressed.len(), 1);
    let (finding, exception) = &ev.suppressed[0];
    assert_eq!(finding.rule.as_str(), "COV001");
    assert_eq!(exception.kind, ExceptionKind::Defer);
    assert_eq!(exception.ticket.as_deref(), Some(t.done.as_str()));
}

#[test]
fn defer_to_an_open_ticket_suppresses_quietly_and_a_missing_one_is_exc007() {
    let t = common::shared_tickets();
    let dir = tempfile::tempdir().expect("tempdir");
    let text = format!(
        "{DEFER_PREFIX}{} */\n/// Does f.\npub fn f() {{}}\n",
        t.open
    );
    common::write_tree(dir.path(), &[("src/lib.rs", &text)]);
    let ev = common::evaluate_tree(dir.path(), Some(&t.ledger), &defaults(), None);
    assert_eq!(ev.suppressed.len(), 1);
    assert_eq!(
        count(&ev.findings, "EXC003") + count(&ev.findings, "EXC007"),
        0
    );
    let text =
        format!("{DEFER_PREFIX}01J9QKX3M8Z4T7N2V5B6C0D1E2 */\n/// Does f.\npub fn f() {{}}\n");
    common::write_tree(dir.path(), &[("src/lib.rs", &text)]);
    let ev = common::evaluate_tree(dir.path(), Some(&t.ledger), &defaults(), None);
    assert_eq!(count(&ev.findings, "EXC007"), 1);
}

#[test]
fn accept_with_a_bad_reason_raises_exc001_but_still_suppresses() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "/* frob:accept COV001 because=\"temporary hack for now\" */\n/// Does f.\npub fn f() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    assert_eq!(
        count(&ev.findings, "EXC001"),
        1,
        "{:?}",
        common::ids(&ev.findings)
    );
    assert_eq!(
        ev.findings
            .iter()
            .find(|f| f.rule.as_str() == "EXC001")
            .map(|f| f.severity),
        Some(Severity::Error)
    );
    assert_eq!(ev.suppressed.len(), 1);
    assert_eq!(ev.suppressed[0].1.kind, ExceptionKind::Accept);
}

#[test]
fn accept_attestation_is_checked_against_frob_lock() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "/* frob:accept COV001 because=\"generated entry point, see ADR-0007\" */\n/// Does f.\npub fn f() {}\n",
        )],
    );
    let f = Symref::symbol("src/lib.rs", vec!["f".to_owned()]);
    let unattested = common::evaluate_tree(dir.path(), None, &defaults(), None);
    assert_eq!(count(&unattested.findings, "EXC005"), 1);
    assert!(
        unattested
            .findings
            .iter()
            .any(|x| x.message.contains("frob ack"))
    );

    let lock = lock_for(dir.path(), &f);
    let attested = common::evaluate_tree(dir.path(), None, &defaults(), Some(lock.clone()));
    assert_eq!(
        count(&attested.findings, "EXC005"),
        0,
        "{:?}",
        common::ids(&attested.findings)
    );
    assert_eq!(attested.suppressed.len(), 1);

    let mut stale = lock;
    stale.entries.get_mut("src/lib.rs::f").expect("entry").body = "0".repeat(64);
    let drifted = common::evaluate_tree(dir.path(), None, &defaults(), Some(stale));
    assert_eq!(count(&drifted.findings, "EXC005"), 1);
    assert!(
        drifted
            .findings
            .iter()
            .any(|x| x.message.contains("changed since"))
    );
}

#[test]
fn an_exception_covers_only_its_bound_symbol() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "/* frob:accept COV001 because=\"generated entry point, see ADR-0007\" */\n/// Does f.\npub fn f() {}\n\n/// Does g.\npub fn g() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    let cov: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .collect();
    assert_eq!(cov.len(), 1);
    assert!(cov[0].message.contains("src/lib.rs::g"));
    assert_eq!(ev.suppressed.len(), 1);
}

#[test]
fn file_level_accept_covers_the_whole_file() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "//! Generated bindings.\n//! frob:accept COV001 because=\"generated bindings, see ADR-0007\"\n\n/// Does f.\npub fn f() {}\n\n/// Does g.\npub fn g() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    assert_eq!(
        count(&ev.findings, "COV001"),
        0,
        "{:?}",
        common::ids(&ev.findings)
    );
    assert_eq!(ev.suppressed.len(), 2);
}

#[test]
fn inv002_reports_a_forbidden_import_from_frob_toml() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[
            (
                "frob.toml",
                "[invariants]\nforbid_imports = [{ from = \"crates/gob-text/**\", to = \"frob_ledger\", reason = \"gob crates never import frob crates\" }]\n",
            ),
            (
                "crates/gob-text/src/lib.rs",
                "//! Text.\nuse frob_ledger::Ledger;\n",
            ),
            (
                "crates/frob-x/src/lib.rs",
                "//! X.\nuse frob_ledger::Ledger;\n",
            ),
        ],
    );
    let config = InvariantsConfig::load(dir.path()).expect("config");
    assert_eq!(config.forbid_imports.len(), 1);
    let ev = common::evaluate_tree(dir.path(), None, &config, None);
    let inv: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "INV002")
        .collect();
    assert_eq!(inv.len(), 1, "{:?}", common::ids(&ev.findings));
    assert!(
        inv[0]
            .message
            .contains("gob crates never import frob crates")
    );
    assert!(inv[0].message.contains("crates/gob-text/src/lib.rs"));
}

#[test]
fn inv001_is_satisfied_by_a_directive_in_another_file() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[
            ("invariants/INV-0001.md", "# One\n"),
            ("invariants/INV-0002.md", "# Two\n"),
            (
                "src/a.rs",
                "// frob:invariant INV-0001\n/// Holds it.\npub fn holds() {}\n",
            ),
        ],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    let inv: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "INV001")
        .collect();
    assert_eq!(inv.len(), 1);
    assert!(inv[0].message.contains("INV-0002"));
}

#[test]
fn cov001_counts_a_test_in_another_file_and_a_cross_file_call() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[
            (
                "src/lib.rs",
                "/// Tripled.\npub fn triple_unique(x: i32) -> i32 { x * 3 }\n\n/// Never tested.\npub fn lonely_unique() {}\n",
            ),
            (
                "tests/it.rs",
                "#[test]\nfn triples() { assert_eq!(triple_unique(1), 3); }\n",
            ),
        ],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    let cov: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .collect();
    assert_eq!(cov.len(), 1, "{cov:?}");
    assert!(cov[0].message.contains("lonely_unique"));
}

#[test]
fn cov003_is_declared_but_never_emitted() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "/* frob:tests tests::missing */\n/// Does f.\npub fn f() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    assert_eq!(count(&ev.findings, "COV003"), 0);
    let reg = Registry::global();
    assert!(reg.by_id("COV003").is_some());
    assert_eq!(frob_obligations::COV003_ALIAS_OF, "TEST001");
    assert!(reg.verify_unique().is_ok());
}

#[test]
fn every_rule_is_registered_exactly_once() {
    let reg = Registry::global();
    for id in [
        "COV001", "COV003", "TODO001", "TODO002", "DOC001", "DOC002", "REF001", "INV001", "INV002",
        "EXC001", "EXC003", "EXC005", "EXC007",
    ] {
        assert!(reg.by_id(id).is_some(), "{id} not registered");
    }
    assert_eq!(
        reg.by_id("COV001").map(|m| m.severity),
        Some(Severity::Warn)
    );
    assert_eq!(
        reg.by_id("DOC002").map(|m| m.severity),
        Some(Severity::Error)
    );
}

#[test]
fn ledger_rules_stay_silent_without_a_ledger() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "// frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2\n// frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 later\n/// Does f.\npub fn f() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    for rule in ["REF001", "TODO002", "EXC003", "EXC007"] {
        assert_eq!(count(&ev.findings, rule), 0, "{rule}");
    }
}

#[test]
fn evaluate_file_runs_the_per_file_rules_on_toml_text() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("Cargo.toml", "a = 1 # FIXME pin\n")]);
    let mut collected = collect(dir.path()).expect("collect");
    let file = collected.files.intern("Cargo.toml");
    let config = defaults();
    let inputs = collected.inputs(dir.path(), None, &config);
    let found = evaluate_file(&inputs, file, "Cargo.toml", "a = 1 # FIXME pin\n");
    assert_eq!(common::ids(&found), ["TODO001"]);
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_is_unresolved_when_a_test_reaches_an_unresolved_call_naming_the_item() {
    let dir = tempfile::tempdir().expect("tempdir");
    let text = "/// Target.\npub fn target() {}\n\n/// Other target.\npub struct S;\n\nimpl S {\n    /// Same name.\n    pub fn target() {}\n}\n\n/// Plain.\npub fn plain() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn calls_out() {\n        other::target();\n    }\n}\n";
    common::write_tree(dir.path(), &[("src/lib.rs", text)]);
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    let cov: Vec<&Finding> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .collect();
    let by = |name: &str| cov.iter().find(|f| f.message.contains(name)).copied();
    let target = by("::target").expect("target is not silently covered");
    let _ = by("S.target").expect("the method is not silently covered either");
    assert_eq!(target.severity, Severity::Unresolved, "{}", target.message);
    let plain = by("::plain").expect("plain is uncovered");
    assert_eq!(plain.severity, Severity::Warn, "{}", plain.message);
}

/// The COV001 findings of a tree built from `files`.
fn cov_findings(files: &[(&str, &str)]) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), files);
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    ev.findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .collect()
}

/// Severity of the COV001 finding whose message names `what`.
fn severity_of(cov: &[Finding], what: &str) -> Option<Severity> {
    cov.iter()
        .find(|f| f.message.contains(what))
        .map(|f| f.severity)
}

const TWO_TYPES: &str = "/// A.\npub struct A;\n\nimpl A {\n    /// Makes.\n    pub fn new() -> A { A }\n}\n\n/// B.\npub struct B;\n\nimpl B {\n    /// Makes.\n    pub fn new() -> B { B }\n}\n\n/// Free.\npub fn run() {}\n\n/// A method named run.\npub struct R;\n\nimpl R {\n    /// Runs.\n    pub fn run(&self) {}\n}\n";

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_external_path_call_does_not_poison_same_named_methods() {
    let test = "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        let _ = Vec::new();\n    }\n}\n";
    let cov = cov_findings(&[("src/lib.rs", &format!("{TWO_TYPES}{test}"))]);
    assert_eq!(severity_of(&cov, "A.new"), Some(Severity::Warn), "{cov:?}");
    assert_eq!(severity_of(&cov, "B.new"), Some(Severity::Warn), "{cov:?}");
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_path_qualifier_poisons_only_the_named_type() {
    // The call is in another crate, so the graph cannot resolve it; its qualifier
    // `A` still rules out `B.new`.
    let test = "#[test]\nfn t() {\n    let _ = a_crate::A::new();\n}\n";
    let cov = cov_findings(&[("a/src/lib.rs", TWO_TYPES), ("b/tests/it.rs", test)]);
    let a = cov
        .iter()
        .find(|f| f.message.contains("A.new"))
        .expect("A.new");
    assert_eq!(a.severity, Severity::Unresolved, "{}", a.message);
    assert!(
        a.message.contains("b/tests/it.rs:3"),
        "names file:line: {}",
        a.message
    );
    assert!(
        a.message.contains("a_crate::A::new(..)"),
        "names the call: {}",
        a.message
    );
    assert_eq!(severity_of(&cov, "B.new"), Some(Severity::Warn), "{cov:?}");
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_unknown_receiver_poisons_methods_but_not_free_functions() {
    let test =
        "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        make().run();\n    }\n}\n";
    let cov = cov_findings(&[("src/lib.rs", &format!("{TWO_TYPES}{test}"))]);
    assert_eq!(
        severity_of(&cov, "R.run"),
        Some(Severity::Unresolved),
        "a method call on an unknown receiver may reach any method of that name: {cov:?}"
    );
    assert_eq!(
        severity_of(&cov, "::run`"),
        Some(Severity::Warn),
        "a method call can never be the free function: {cov:?}"
    );
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_unknown_receiver_is_never_falsely_covered() {
    let test = "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        let r = mystery();\n        r.run();\n    }\n}\n";
    let cov = cov_findings(&[("src/lib.rs", &format!("{TWO_TYPES}{test}"))]);
    // `mystery()` is declared nowhere: the receiver stays unknown, so the method is
    // Unresolved (never a false Covered).
    assert_eq!(
        severity_of(&cov, "R.run"),
        Some(Severity::Unresolved),
        "{cov:?}"
    );
}

// frob:ticket 01M3ZVQAA1DNM1BJ5TZG5B3CFR
// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_unit_struct_value_types_its_receiver_and_covers_the_method() {
    let test = "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        let r = R;\n        r.run();\n    }\n}\n";
    let cov = cov_findings(&[("src/lib.rs", &format!("{TWO_TYPES}{test}"))]);
    // `R` is the unit struct `R`: `r.run()` is `R::run`, so it is covered (no finding) and
    // the free function `run` is not.
    assert_eq!(severity_of(&cov, "R.run"), None, "{cov:?}");
    assert_eq!(severity_of(&cov, "::run`"), Some(Severity::Warn), "{cov:?}");
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_qualifierless_unknown_call_keeps_the_broad_match() {
    let test = "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        run();\n        mystery();\n    }\n}\n";
    let src = TWO_TYPES.replace(
        "pub fn run() {}",
        "pub fn run() {}\n\n/// Other.\npub fn mystery_twin() {}",
    );
    let cov = cov_findings(&[("src/lib.rs", &format!("{src}{test}"))]);
    assert_eq!(severity_of(&cov, "R.run"), Some(Severity::Warn), "{cov:?}");
    assert_eq!(
        severity_of(&cov, "mystery_twin"),
        Some(Severity::Warn),
        "{cov:?}"
    );
}

/// Writes a two-crate workspace: `a-lib` defines `Inputs::collect` twice over (inherent and trait),
/// `b-app` tests it through `use a_lib::Inputs`.
fn cross_crate_tree(a_inputs: &str, b_test: &str) -> Vec<Finding> {
    cov_findings(&[
        ("Cargo.toml", "[workspace]\nmembers = [\"crates/*\"]\n"),
        ("crates/a/Cargo.toml", "[package]\nname = \"a-lib\"\n"),
        (
            "crates/b/Cargo.toml",
            "[package]\nname = \"b-app\"\n\n[dependencies]\na-lib = { path = \"../a\" }\n",
        ),
        (
            "crates/a/src/lib.rs",
            "mod inputs;\npub use inputs::Inputs;\n",
        ),
        ("crates/a/src/inputs.rs", a_inputs),
        ("crates/b/tests/t.rs", b_test),
    ])
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_covers_a_cross_crate_path_call_through_a_use_import() {
    let a = "/// Inputs.\npub struct Inputs;\n\nimpl Inputs {\n    /// Collects.\n    pub fn collect() {}\n\n    /// Never called.\n    pub fn lonely() {}\n}\n";
    let t = "use a_lib::Inputs;\n#[test]\nfn t() {\n    Inputs::collect();\n}\n";
    let cov = cross_crate_tree(a, t);
    assert_eq!(
        severity_of(&cov, "Inputs.collect"),
        None,
        "covered: {cov:?}"
    );
    assert_eq!(
        severity_of(&cov, "Inputs.lonely"),
        Some(Severity::Warn),
        "{cov:?}"
    );
}

// frob:tests crates/frob-obligations/src/cov.rs::cov001
#[test]
fn cov001_never_covers_a_genuinely_ambiguous_cross_crate_call() {
    // `Inputs::collect` names an inherent and a trait implementation: either may be
    // the callee, so neither is claimed covered.
    let a = "/// Inputs.\npub struct Inputs;\n\nimpl Inputs {\n    /// Inherent.\n    pub fn collect() {}\n}\n\n/// Collects.\npub trait Collect {\n    /// Declared.\n    fn collect();\n}\n\nimpl Collect for Inputs {\n    fn collect() {}\n}\n";
    let t = "use a_lib::Inputs;\n#[test]\nfn t() {\n    Inputs::collect();\n}\n";
    let cov = cross_crate_tree(a, t);
    let inherent = severity_of(&cov, "Inputs.collect");
    assert_eq!(inherent, Some(Severity::Unresolved), "inherent: {cov:?}");
    let decl = severity_of(&cov, "Collect.collect");
    assert_ne!(
        decl, None,
        "the trait method is not silently covered: {cov:?}"
    );
    // And a call with an unknown receiver never covers two same-named methods.
    let two = "/// A.\npub struct A;\nimpl A {\n    /// Go.\n    pub fn go(&self) {}\n}\n\n/// B.\npub struct B;\nimpl B {\n    /// Go.\n    pub fn go(&self) {}\n}\n";
    let t2 = "#[test]\nfn t() {\n    make().go();\n}\n";
    let cov = cross_crate_tree(two, t2);
    assert_eq!(
        severity_of(&cov, "A.go"),
        Some(Severity::Unresolved),
        "{cov:?}"
    );
    assert_eq!(
        severity_of(&cov, "B.go"),
        Some(Severity::Unresolved),
        "{cov:?}"
    );
}

/// A git repository at `root` with `core.autocrlf=true`, as a Windows checkout would have.
fn init_autocrlf_repo(root: &std::path::Path) {
    gob_git::Repo::init(root).expect("git init");
    let config = root.join(".git/config");
    let mut text = std::fs::read_to_string(&config).expect("git config");
    text.push_str("[core]\n\tautocrlf = true\n");
    std::fs::write(config, text).expect("write git config");
}

// frob:tests crates/frob-obligations/src/rules.rs::Exc005
#[test]
fn crlf_checkout_under_autocrlf_keeps_an_accept_attested_but_a_real_edit_does_not() {
    let dir = tempfile::tempdir().expect("tempdir");
    init_autocrlf_repo(dir.path());
    let lf = "/* frob:accept COV001 because=\"generated entry point, see ADR-0007\" */\n/// Does f.\npub fn f() {}\n";
    common::write_tree(dir.path(), &[("src/lib.rs", lf)]);
    let f = Symref::symbol("src/lib.rs", vec!["f".to_owned()]);
    let lock = lock_for(dir.path(), &f);

    common::write_tree(dir.path(), &[("src/lib.rs", &lf.replace('\n', "\r\n"))]);
    let crlf = common::evaluate_tree(dir.path(), None, &defaults(), Some(lock.clone()));
    assert_eq!(
        count(&crlf.findings, "EXC005"),
        0,
        "{:?}",
        common::ids(&crlf.findings)
    );

    let edited = lf.replace("pub fn f() {}", "pub fn f() { drop(1) }");
    common::write_tree(dir.path(), &[("src/lib.rs", &edited.replace('\n', "\r\n"))]);
    let changed = common::evaluate_tree(dir.path(), None, &defaults(), Some(lock));
    assert_eq!(count(&changed.findings, "EXC005"), 1);
}

// frob:ticket 01M4FH86F1XAWKC7KQZSH5B4JE
#[test]
fn a_frob_doc_line_between_a_doc_block_and_its_item_does_not_raise_doc001() {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(
        dir.path(),
        &[(
            "src/lib.rs",
            "/// Does f.\n// frob:doc docs/f.md#f\npub fn f() {}\n\npub fn g() {}\n",
        )],
    );
    let ev = common::evaluate_tree(dir.path(), None, &defaults(), None);
    let docs: Vec<String> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DOC001")
        .map(|f| f.message.clone())
        .collect();
    assert_eq!(docs.len(), 1, "only the undocumented g: {docs:?}");
    assert!(docs[0].contains("::g"), "{docs:?}");
}
