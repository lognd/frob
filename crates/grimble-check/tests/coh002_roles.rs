//! COH002 reads a unit's role from `grimble:core` / `grimble:shell` directives.

// frob:ticket 01M5HJ078MGFERVXX3DSJT111F

#![allow(unused_crate_dependencies)]

use gob_languages::Language;
use gob_symbols::{Folded, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_check::coh_pass::analyze;
use grimble_check::coh002::{Coh002Options, UnitRole};
use grimble_check::unit_role::{declared_roles, resolve_role};
use grimble_lints::pass::{PathFile, PathFinding};

const BODY: &str = "    x = compute(a)\n    if x > 3:\n        sink.send(x)\n    return x\n";

fn py(prefix: &str) -> String {
    format!("{prefix}def f(a, sink):\n{BODY}")
}

fn fold(path: &str, text: &str) -> Folded {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    fold_file(&entry, text).expect("fold")
}

fn roles(path: &str, language: Language, text: &str) -> Vec<UnitRole> {
    let folded = fold(path, text);
    let mut found: Vec<UnitRole> = declared_roles(&folded, language, text)
        .into_values()
        .collect();
    found.sort_by_key(|r| format!("{r:?}"));
    found
}

fn findings(path: &str, language: Language, text: &str) -> Vec<PathFinding> {
    let file = PathFile {
        path,
        language,
        text,
    };
    analyze(&[file], &Coh002Options::default()).findings
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_core_directive_declares_the_core_role() {
    let src = py("# grimble:core\n");
    assert_eq!(roles("a.py", Language::Python, &src), [UnitRole::Core]);
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_shell_directive_declares_an_unverified_shell() {
    let src = py("# grimble:shell\n");
    assert_eq!(
        roles("a.py", Language::Python, &src),
        [UnitRole::Shell { verified: false }]
    );
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_rust_function_reads_its_role_too() {
    let src = "// grimble:core\npub fn f(a: u32) -> u32 {\n    a\n}\n\nfn g() {}\n";
    assert_eq!(roles("a.rs", Language::Rust, src), [UnitRole::Core]);
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn the_pass_judges_a_core_directive_as_core_and_a_shell_directive_as_unresolved() {
    let plain = findings("a.py", Language::Python, &py(""));
    assert_eq!(plain.len(), 1, "{plain:?}");
    let core = findings("a.py", Language::Python, &py("# grimble:core\n"));
    assert_eq!(core.len(), 1, "{core:?}");
    assert_eq!(core[0].severity, gob_rules::Severity::Advisory);
    let shell = findings("a.py", Language::Python, &py("# grimble:shell\n"));
    assert_eq!(shell.len(), 1, "{shell:?}");
    assert_eq!(shell[0].severity, gob_rules::Severity::Unresolved);
    assert!(shell[0].message.contains("grimble:shell"), "{shell:?}");
}

// frob:tests crates/grimble-check/src/unit_role.rs::resolve_role
// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn without_a_directive_the_supplied_role_is_used_unchanged() {
    let src = py("");
    assert!(roles("a.py", Language::Python, &src).is_empty());
    assert_eq!(resolve_role(None, UnitRole::None), UnitRole::None);
    assert_eq!(resolve_role(None, UnitRole::Core), UnitRole::Core);
    let shell = UnitRole::Shell { verified: true };
    assert_eq!(resolve_role(None, shell), shell);
    assert_eq!(
        resolve_role(Some(UnitRole::Core), UnitRole::None),
        UnitRole::Core
    );
    let plain = findings("a.py", Language::Python, &src);
    assert_eq!(plain.len(), 1, "{plain:?}");
    assert_eq!(plain[0].severity, gob_rules::Severity::Advisory);
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn both_roles_on_one_unit_conflict_and_the_stricter_core_wins() {
    let src = py("# grimble:shell\n# grimble:core\n");
    assert_eq!(roles("a.py", Language::Python, &src), [UnitRole::Core]);
    let src = py("# grimble:core\n# grimble:shell\n");
    assert_eq!(roles("a.py", Language::Python, &src), [UnitRole::Core]);
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_directive_inside_a_string_or_with_junk_declares_nothing() {
    let in_string = format!("DOC = \"# grimble:core\"\n\n{}", py(""));
    assert!(roles("a.py", Language::Python, &in_string).is_empty());
    let docstring = "def f(a, sink):\n    \"\"\"grimble:core\"\"\"\n    return a\n";
    assert!(roles("a.py", Language::Python, docstring).is_empty());
    let junk = py("# grimble:core bogus=1 extra\n");
    assert!(roles("a.py", Language::Python, &junk).is_empty());
    let unknown = py("# grimble:coree\n");
    assert!(roles("a.py", Language::Python, &unknown).is_empty());
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_directive_on_a_class_or_detached_from_any_unit_declares_nothing() {
    let class = "# grimble:core\nclass C:\n    x = 1\n";
    assert!(roles("a.py", Language::Python, class).is_empty());
    let detached = format!("# grimble:core\n\nX = 1\n\n{}", py(""));
    assert!(roles("a.py", Language::Python, &detached).is_empty());
}

// frob:tests crates/grimble-check/src/unit_role.rs::declared_roles
#[test]
fn a_directive_applies_to_its_own_unit_only() {
    let src = format!(
        "{}\n{}",
        py("# grimble:core\n"),
        "def g(a, sink):\n    return a\n"
    );
    assert_eq!(roles("a.py", Language::Python, &src), [UnitRole::Core]);
}
