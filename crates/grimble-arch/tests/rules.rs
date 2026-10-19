//! The CYCLE001, LARGE001 and DEAD001 rule pages as an mdtest corpus, plus the acceptance tests.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use std::collections::BTreeMap;
use std::path::Path;

use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_symbols::CrateDeps;
use gob_text::FileInterner;
use grimble_arch::{ArchFinding, ArchInput, analyze};
use grimble_bind::code::Code;

/// Write `text` at `rel` under `root`.
fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    std::fs::create_dir_all(p.parent().expect("a file has a parent")).expect("mkdir");
    std::fs::write(p, text).expect("write");
}

/// A crate `name` depending on `dep` (when given) and calling its `f`.
fn krate(root: &Path, name: &str, dep: Option<&str>) {
    let deps = dep
        .map(|d| format!("{d} = {{ path = \"../{d}\" }}\n"))
        .unwrap_or_default();
    write(
        root,
        &format!("{name}/Cargo.toml"),
        &format!(
            "[package]\nname = \"{name}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\n{deps}"
        ),
    );
    let body = match dep {
        Some(d) => format!("use {d}::f;\n\npub fn g() {{\n    f();\n}}\n\npub fn f() {{}}\n"),
        None => "pub fn f() {}\n".to_owned(),
    };
    write(root, &format!("{name}/src/lib.rs"), &body);
}

/// Analyze the repository at `root` with the `large_lines` knob.
fn run(root: &Path, large_lines: usize) -> Vec<ArchFinding> {
    let walked = gob_walk::walk(root, &gob_walk::WalkConfig::default()).expect("walk");
    let code = Code::build(root, &walked.files);
    let graph = grimble_bind::edges::build_graph(root, &code);
    let mut deps = CrateDeps::new(root);
    let crates: BTreeMap<String, String> = walked
        .files
        .iter()
        .filter_map(|f| deps.crate_of(&f.path).map(|c| (f.path.clone(), c)))
        .collect();
    let read = |p: &str| std::fs::read_to_string(root.join(p)).ok();
    analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines,
        read: &read,
    })
    .findings
}

/// A repository where `a` and `b` import each other.
fn cyclic(root: &Path) {
    krate(root, "a", Some("b"));
    krate(root, "b", Some("a"));
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-arch/src/rules/cycle001.rs::Cycle001
    // frob:tests crates/grimble-arch/src/rules/large001.rs::Large001
    // frob:tests crates/grimble-arch/src/rules/dead001.rs::Dead001
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let words = case.config.as_deref().unwrap_or("");
    let has = |w: &str| words.split_whitespace().any(|x| x == w);
    if has("cycle") {
        cyclic(root);
    } else if has("chain") {
        krate(root, "a", Some("b"));
        krate(root, "b", None);
    }
    write(root, &case.file_name, &case.text);
    let limit = if has("small") || has("big") { 3 } else { 400 };
    let mut files = FileInterner::new();
    run(root, limit)
        .into_iter()
        .filter(|f| f.rule == case.rule.as_str())
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

#[test]
fn cycle_names_both_crates() {
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let dir = tempfile::tempdir().expect("tempdir");
    cyclic(dir.path());
    let found: Vec<_> = run(dir.path(), 0)
        .into_iter()
        .filter(|f| f.rule == "CYCLE001")
        .collect();
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Error);
    assert!(
        found[0].message.contains('a') && found[0].anchor.contains("a,b"),
        "{found:?}"
    );
}

#[test]
fn dead_through_may_edge_is_unresolved() {
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/m.py",
        "class A:\n    def _hook(self):\n        pass\n\nclass B:\n    def _hook(self):\n        pass\n\ndef run(x):\n    x._hook()\n",
    );
    let found: Vec<_> = run(dir.path(), 0)
        .into_iter()
        .filter(|f| f.rule == "DEAD001")
        .collect();
    assert!(!found.is_empty(), "no verdict at all");
    for f in &found {
        assert_eq!(f.severity, Severity::Unresolved, "{f:?}");
        assert!(matches!(
            f.reason,
            Some(UnresolvedReason::EdgeMay | UnresolvedReason::EdgeUnknown)
        ));
    }
}

/// A host with fixed subject counts.
struct Fixed;

impl grimble_arch::host::ArchHost for Fixed {
    fn arch_subjects_of(&self, id: &str) -> usize {
        id.len()
    }
}

#[test]
fn host_binds_and_converts() {
    // frob:tests crates/grimble-arch/src/rules/mod.rs::bind
    // frob:tests crates/grimble-arch/src/host.rs::ArchHost.arch_subjects_of
    // frob:tests crates/grimble-arch/src/finding.rs::ArchFinding.into_finding
    assert_eq!(grimble_arch::rules::bind::<Fixed>().len(), 3);
    assert_eq!(
        grimble_arch::host::ArchHost::arch_subjects_of(&Fixed, "DEAD001"),
        7
    );
    let dir = tempfile::tempdir().expect("tempdir");
    cyclic(dir.path());
    let mut files = FileInterner::new();
    let converted: Vec<_> = run(dir.path(), 0)
        .into_iter()
        .filter_map(|f| f.into_finding(&mut files))
        .collect();
    assert!(converted.iter().any(|f| f.rule.as_str() == "CYCLE001"));
}
