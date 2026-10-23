//! The CYCLE001, LARGE001, DEAD001, VIS001 and DUP001 rule pages as an mdtest corpus, plus the acceptance tests.

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
    run_dup(root, large_lines, 50, 3)
}

/// Analyze the repository at `root` with every knob.
fn run_dup(
    root: &Path,
    large_lines: usize,
    dup_min_tokens: usize,
    dup_min_occurrences: usize,
) -> Vec<ArchFinding> {
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
        dup_min_tokens,
        dup_min_occurrences,
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
    // frob:tests crates/grimble-arch/src/rules/vis001.rs::Vis001
    // frob:tests crates/grimble-arch/src/rules/dup001.rs::Dup001
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
    assert_eq!(grimble_arch::rules::bind::<Fixed>().len(), 5);
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

/// A repository with no source units marks all five rules not applicable instead of vacuous.
#[test]
fn empty_repository_makes_the_rules_not_applicable() {
    let dir = tempfile::tempdir().expect("tempdir");
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).expect("walk");
    let code = Code::build(dir.path(), &walked.files);
    let graph = grimble_bind::edges::build_graph(dir.path(), &code);
    let crates = BTreeMap::new();
    let read = |_: &str| None;
    let report = analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines: 100,
        dup_min_tokens: 50,
        dup_min_occurrences: 3,
        read: &read,
    });
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(ids, ["CYCLE001", "DEAD001", "DUP001", "LARGE001", "VIS001"]);
}

/// A repository with only TypeScript units makes `VIS001` (Rust-only) not applicable, and nothing else.
// frob:tests crates/grimble-arch/src/lib.rs::analyze
#[test]
fn a_repository_without_rust_makes_only_vis001_not_applicable() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/a.ts",
        "import { b } from \"./b\";\nexport function a(): number { return b(); }\n",
    );
    write(
        dir.path(),
        "src/b.ts",
        "export function b(): number { return 1; }\n",
    );
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).expect("walk");
    let code = Code::build(dir.path(), &walked.files);
    let graph = grimble_bind::edges::build_graph(dir.path(), &code);
    let crates = BTreeMap::new();
    let read = |_: &str| None;
    let report = analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines: 100,
        dup_min_tokens: 50,
        dup_min_occurrences: 3,
        read: &read,
    });
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(ids, ["VIS001"]);
}

/// The findings of `rule` over the repository at `root`.
fn of_rule(root: &Path, rule: &str) -> Vec<ArchFinding> {
    run(root, 0)
        .into_iter()
        .filter(|f| f.rule == rule)
        .collect()
}

/// A package `a` whose `helper` sits in a private module, used only inside `a`.
fn narrow(root: &Path) {
    krate(root, "a", None);
    write(
        root,
        "a/src/lib.rs",
        "mod inner {\n    pub fn helper() {}\n}\n\npub fn api() {\n    inner::helper();\n}\n",
    );
}

#[test]
fn vis_fires_when_only_its_own_package_uses_the_item() {
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let dir = tempfile::tempdir().expect("tempdir");
    narrow(dir.path());
    let found = of_rule(dir.path(), "VIS001");
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Advisory);
}

#[test]
fn vis_is_unresolved_on_an_unknown_edge_from_outside() {
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let dir = tempfile::tempdir().expect("tempdir");
    narrow(dir.path());
    krate(dir.path(), "b", None);
    write(
        dir.path(),
        "b/src/lib.rs",
        "pub fn q(x: u8) {\n    x.helper();\n}\n",
    );
    let found = of_rule(dir.path(), "VIS001");
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Unresolved);
    assert_eq!(found[0].reason, Some(UnresolvedReason::EdgeUnknown));
}

#[test]
fn vis_is_clean_for_an_item_re_exported_from_the_crate_root() {
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let dir = tempfile::tempdir().expect("tempdir");
    krate(dir.path(), "a", None);
    write(
        dir.path(),
        "a/src/lib.rs",
        "mod inner {\n    pub fn helper() {}\n}\n\npub use crate::inner::helper;\n",
    );
    assert!(of_rule(dir.path(), "VIS001").is_empty());
}

/// Six lines of arithmetic, valid as TypeScript and Python, with `n` to tell copies apart in name only.
fn block(n: usize) -> String {
    use std::fmt::Write as _;
    let mut out = String::new();
    for i in 1..=6 {
        let _ = writeln!(
            out,
            "x{n}{i} = alpha{n} + beta{n} * gamma{n} - delta{n} + {i};"
        );
    }
    out
}

/// The same six lines for every copy, so the copies are exact.
fn exact_block() -> String {
    use std::fmt::Write as _;
    let mut out = String::new();
    for i in 1..=6 {
        let _ = writeln!(out, "x{i} = alpha + beta * gamma - delta + {i};");
    }
    out
}

/// The `DUP001` findings over the repository at `root`.
fn dup_findings(root: &Path) -> Vec<ArchFinding> {
    of_rule(root, "DUP001")
}

/// Three copies of a block of about 60 tokens across a TypeScript and a Python file give one finding listing every site.
// frob:tests crates/grimble-arch/src/dup.rs::check
// frob:tests crates/grimble-arch/src/lib.rs::analyze
#[test]
fn three_copies_across_two_languages_make_one_dup_finding() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/a.ts",
        &format!("export function a() {{}}\n{}", exact_block()),
    );
    write(
        dir.path(),
        "src/b.ts",
        &format!("export function b() {{}}\n{}", exact_block()),
    );
    write(
        dir.path(),
        "tools/c.py",
        &format!("def c():\n    pass\n{}", exact_block()),
    );
    let found = dup_findings(dir.path());
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].severity, Severity::Advisory);
    for site in ["src/a.ts:2", "src/b.ts:2", "tools/c.py:3"] {
        assert!(found[0].message.contains(site), "{site} missing: {found:?}");
    }
    assert!(found[0].message.starts_with("3 copies"), "{found:?}");
}

/// Two copies are below the default of three occurrences and give no finding.
// frob:tests crates/grimble-arch/src/dup.rs::check
// frob:tests crates/grimble-arch/src/lib.rs::analyze
#[test]
fn two_copies_make_no_dup_finding() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/a.ts",
        &format!("export function a() {{}}\n{}", exact_block()),
    );
    write(
        dir.path(),
        "src/b.ts",
        &format!("export function b() {{}}\n{}", exact_block()),
    );
    assert!(dup_findings(dir.path()).is_empty());
}

/// Copies that only rename identifiers are found once, at the renamed rung.
// frob:tests crates/grimble-arch/src/dup.rs::check
#[test]
fn renamed_copies_are_reported_at_r2() {
    let dir = tempfile::tempdir().expect("tempdir");
    for (i, n) in [1, 2, 3].into_iter().enumerate() {
        write(dir.path(), &format!("src/f{i}.ts"), &block(n));
    }
    let found = dup_findings(dir.path());
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].anchor.starts_with("R2:"), "{found:?}");
}

/// Test files, comments and import lines do not count toward a clone.
// frob:tests crates/grimble-arch/src/dup.rs::check
#[test]
fn tests_are_not_lexed() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "src/a.ts", &exact_block());
    write(dir.path(), "src/b.ts", &exact_block());
    write(dir.path(), "tests/c.test.ts", &exact_block());
    assert!(dup_findings(dir.path()).is_empty());
}

/// The `DUP001` thresholds come from the input: two copies fire at 2 occurrences, and 0 tokens or a huge window turns the rule off.
// frob:tests crates/grimble-arch/src/dup.rs::check
// frob:tests crates/grimble-arch/src/lib.rs::analyze
#[test]
fn dup_thresholds_come_from_the_input() {
    let dir = tempfile::tempdir().expect("tempdir");
    for name in ["a", "b"] {
        write(
            dir.path(),
            &format!("src/{name}.ts"),
            &format!("export function f() {{}}\n{}", exact_block()),
        );
    }
    let count = |tokens, occ| {
        run_dup(dir.path(), 400, tokens, occ)
            .iter()
            .filter(|f| f.rule == "DUP001")
            .count()
    };
    assert_eq!(count(50, 3), 0);
    let two = run_dup(dir.path(), 400, 50, 2);
    assert_eq!(two.len(), 1, "{two:?}");
    assert_eq!(count(0, 2), 0);
    assert_eq!(count(50, 1), 0);
    assert_eq!(count(usize::MAX, 2), 0);
    assert_eq!(count(50, usize::MAX), 0);
}
