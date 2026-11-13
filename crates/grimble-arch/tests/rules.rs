//! The CYCLE001, LARGE001, DEAD001, VIS001 and DUP001 rule pages as an mdtest corpus, plus the acceptance tests.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_symbols::CrateDeps;
use gob_text::FileInterner;
use grimble_arch::{ArchInput, Verdict, analyze};
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
fn run(root: &Path, large_lines: usize) -> Vec<Verdict> {
    run_dup(root, large_lines, 50, 3, &BTreeSet::new(), false)
}

/// Analyze the repository at `root` with every knob.
fn run_dup(
    root: &Path,
    large_lines: usize,
    dup_min_tokens: usize,
    dup_min_occurrences: usize,
    changed: &BTreeSet<String>,
    dup_scan: bool,
) -> Vec<Verdict> {
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
    let index = root.join(".git/frob/dup-index");
    analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines,
        dup_min_tokens,
        dup_min_occurrences,
        read: &read,
        dup_index: index.is_dir().then_some(index.as_path()),
        changed,
        dup_scan,
        is_engine_entry: &|_| false,
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
    // frob:tests crates/grimble-arch/src/rules/dup003.rs::Dup003
    // frob:tests crates/grimble-arch/src/rules/dup004.rs::Dup004
    // frob:tests crates/grimble-arch/src/rules/dup005.rs::Dup005
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
    // DUP004 is scoped to changed files: the example's own file is the changed one.
    let changed = BTreeSet::from([case.file_name.clone()]);
    run_dup(root, limit, 50, 3, &changed, true)
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
    // frob:tests crates/grimble-verdict/src/lib.rs::Verdict.into_finding
    assert_eq!(grimble_arch::rules::bind::<Fixed>().len(), 9);
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
        dup_index: None,
        changed: &BTreeSet::new(),
        dup_scan: false,
        is_engine_entry: &|_| false,
    });
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(
        ids,
        [
            "CYCLE001", "DEAD001", "DUP001", "DUP002", "DUP003", "DUP004", "DUP005", "LARGE001",
            "VIS001"
        ]
    );
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
        dup_index: None,
        changed: &BTreeSet::new(),
        dup_scan: false,
        is_engine_entry: &|_| false,
    });
    let ids: Vec<_> = report.not_applicable.keys().copied().collect();
    assert_eq!(ids, ["DUP004", "DUP005", "VIS001"]);
}

/// A Rust repository with no `pub` free function left to judge makes `VIS001` not applicable.
// frob:tests crates/grimble-arch/src/lib.rs::analyze
#[test]
fn a_rust_repository_without_pub_free_functions_makes_vis001_not_applicable() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "Cargo.toml",
        "[package]\nname = \"solo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
    );
    write(
        dir.path(),
        "src/lib.rs",
        "fn helper() {}\n\nfn other() {\n    helper();\n}\n",
    );
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).expect("walk");
    let code = Code::build(dir.path(), &walked.files);
    let graph = grimble_bind::edges::build_graph(dir.path(), &code);
    let mut deps = CrateDeps::new(dir.path());
    let crates: BTreeMap<String, String> = walked
        .files
        .iter()
        .filter_map(|f| deps.crate_of(&f.path).map(|c| (f.path.clone(), c)))
        .collect();
    let read = |_: &str| None;
    let report = analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines: 0,
        dup_min_tokens: 50,
        dup_min_occurrences: 3,
        read: &read,
        dup_index: None,
        changed: &BTreeSet::new(),
        dup_scan: false,
        is_engine_entry: &|_| false,
    });
    assert!(report.not_applicable.contains_key("VIS001"));
}

/// The findings of `rule` over the repository at `root`.
fn of_rule(root: &Path, rule: &str) -> Vec<Verdict> {
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
    assert_eq!(found[0].severity, Severity::Error);
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
        writeln!(
            out,
            "x{n}{i} = alpha{n} + beta{n} * gamma{n} - delta{n} + {i};"
        )
        .ok();
    }
    out
}

/// The same six lines for every copy, so the copies are exact.
fn exact_block() -> String {
    use std::fmt::Write as _;
    let mut out = String::new();
    for i in 1..=6 {
        writeln!(out, "x{i} = alpha + beta * gamma - delta + {i};").ok();
    }
    out
}

/// The `DUP001` findings over the repository at `root`.
fn dup_findings(root: &Path) -> Vec<Verdict> {
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
    assert_eq!(found[0].severity, Severity::Error);
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

/// Copies that only rename identifiers are found once, at the renamed rung, as DUP002 and not DUP001.
// frob:tests crates/grimble-arch/src/dup.rs::check
#[test]
fn renamed_copies_are_reported_at_r2() {
    let dir = tempfile::tempdir().expect("tempdir");
    for (i, n) in [1, 2, 3].into_iter().enumerate() {
        write(dir.path(), &format!("src/f{i}.ts"), &block(n));
    }
    let found = of_rule(dir.path(), "DUP002");
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].anchor.starts_with("R2:"), "{found:?}");
    assert_eq!(found[0].severity, Severity::Error);
    assert!(
        dup_findings(dir.path()).is_empty(),
        "renamed copies are not DUP001"
    );
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

/// How many `DUP001` findings the walk at `root` yields for a token and occurrence threshold.
fn dup001_count(root: &Path, tokens: usize, occ: usize) -> usize {
    run_dup(root, 400, tokens, occ, &BTreeSet::new(), false)
        .iter()
        .filter(|f| f.rule == "DUP001")
        .count()
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
    assert_eq!(dup001_count(dir.path(), 50, 3), 0);
    let two = run_dup(dir.path(), 400, 50, 2, &BTreeSet::new(), false);
    assert_eq!(two.len(), 1, "{two:?}");
    assert_eq!(dup001_count(dir.path(), 0, 2), 0);
    assert_eq!(dup001_count(dir.path(), 50, 1), 0);
    assert_eq!(dup001_count(dir.path(), usize::MAX, 2), 0);
    assert_eq!(dup001_count(dir.path(), 50, usize::MAX), 0);
}

/// The body shared by the `DUP004` acceptance tests, with its statements in the given order.
fn shaped(name: &str, order: [usize; 4]) -> String {
    let stmts = [
        "let v1 = a + b * c - a;",
        "let v2 = v1 * b + c - a;",
        "let v3 = v2 * v1 + b - c;",
        "let v4 = v3 + v2 * v1 - a + b;",
    ];
    let body: Vec<_> = order.iter().map(|&i| format!("    {}", stmts[i])).collect();
    format!(
        "pub fn {name}(a: i64, b: i64, c: i64) -> i64 {{\n{}\n    v4 * 2\n}}\n",
        body.join("\n")
    )
}

/// The `DUP004` findings of a repo with `a.rs` and `b.rs`, given which files count as changed.
fn dup004(changed: &[&str]) -> Vec<Verdict> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "src/a.rs", &shaped("first", [0, 1, 2, 3]));
    write(dir.path(), "src/b.rs", &shaped("second", [3, 2, 1, 0]));
    let changed: BTreeSet<String> = changed.iter().map(|c| (*c).to_owned()).collect();
    run_dup(dir.path(), 400, 20, 3, &changed, false)
        .into_iter()
        .filter(|f| f.rule == "DUP004")
        .collect()
}

#[test]
fn dup004_finds_a_reordered_copy_in_a_changed_file() {
    // frob:tests crates/grimble-arch/src/rules/dup004.rs::Dup004
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let found = dup004(&["src/b.rs"]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].file, "src/b.rs");
}

#[test]
fn dup004_is_silent_when_no_member_changed() {
    // frob:tests crates/grimble-arch/src/rules/dup004.rs::Dup004
    assert!(dup004(&["src/other.rs"]).is_empty());
    assert!(dup004(&[]).is_empty());
}

/// The `DUP005` findings of a repo with a reordered pair, with the scan on or off and nothing changed.
fn dup005(scan: bool) -> Vec<Verdict> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "src/a.rs", &shaped("first", [0, 1, 2, 3]));
    write(dir.path(), "src/b.rs", &shaped("second", [3, 2, 1, 0]));
    run_dup(dir.path(), 400, 20, 3, &BTreeSet::new(), scan)
        .into_iter()
        .filter(|f| f.rule == "DUP005")
        .collect()
}

#[test]
fn dup005_scans_the_whole_repo_without_a_changed_set() {
    // frob:tests crates/grimble-arch/src/rules/dup005.rs::Dup005
    // frob:tests crates/grimble-arch/src/lib.rs::analyze
    let found = dup005(true);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].file, "src/a.rs");
}

#[test]
fn dup005_is_off_unless_the_scan_is_requested() {
    // frob:tests crates/grimble-arch/src/rules/dup005.rs::Dup005
    assert!(dup005(false).is_empty());
}

#[test]
fn dup005_anchor_is_stable_so_a_baseline_keeps_matching() {
    // frob:tests crates/grimble-arch/src/rules/dup005.rs::Dup005
    let first = dup005(true);
    let second = dup005(true);
    assert_eq!(first[0].anchor, second[0].anchor);
    assert!(first[0].anchor.starts_with("S:"));
}

/// The `DEAD001` verdict messages over `root` when `is_entry` names the engine entry points.
fn dead_messages(root: &Path, is_entry: &dyn Fn(&str) -> bool) -> Vec<String> {
    let walked = gob_walk::walk(root, &gob_walk::WalkConfig::default()).expect("walk");
    let code = Code::build(root, &walked.files);
    let graph = grimble_bind::edges::build_graph(root, &code);
    let crates = BTreeMap::new();
    let read = |_: &str| None;
    let report = analyze(&ArchInput {
        graph: &graph,
        crates: &crates,
        large_lines: 0,
        dup_min_tokens: 0,
        dup_min_occurrences: 0,
        read: &read,
        dup_index: None,
        changed: &BTreeSet::new(),
        dup_scan: false,
        is_engine_entry: is_entry,
    });
    report
        .findings
        .into_iter()
        .filter(|f| f.rule == "DEAD001")
        .map(|f| f.message)
        .collect()
}

/// A C# message the engine calls (`Update`) is a live root, while an unreferenced helper still fires.
// frob:ticket 01M5F8MNMXE10ZQFN7BRA0V3XC
// frob:tests crates/grimble-arch/src/rules/dead001.rs::Dead001
#[test]
fn dead001_treats_engine_entry_points_as_live_roots() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "Assets/Player.cs",
        "class Player\n{\n    void Update() { }\n    void Helper() { }\n}\n",
    );
    let without = dead_messages(dir.path(), &|_| false);
    assert!(
        without.iter().any(|m| m.contains("`Update`")),
        "{without:?}"
    );
    let with = dead_messages(dir.path(), &|n| n == "Update");
    assert!(!with.iter().any(|m| m.contains("`Update`")), "{with:?}");
    assert!(with.iter().any(|m| m.contains("`Helper`")), "{with:?}");
}

/// The clone index directory is absent outside a git checkout.
// frob:tests crates/grimble-arch/src/lib.rs::dup_index_dir
#[test]
fn dup_index_dir_is_none_outside_git() {
    let tmp = tempfile::tempdir().expect("tmp");
    assert!(grimble_arch::dup_index_dir(tmp.path()).is_none());
}
