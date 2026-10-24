//! Corpus tests for the PATH rules: each ~G5RJY40 Windows bug fires, each fix is quiet.

// frob:ticket 01M41RV691XZQ5W2EW821PHK3V

use gob_languages::Language;
use grimble_lints::path::{Kind, Options, Report, scan};

fn run(language: Language, src: &str) -> Report {
    scan(language, src, &Options::default()).expect("corpus file parses")
}

fn kinds(r: &Report) -> Vec<Kind> {
    r.sites.iter().map(|s| s.kind).collect()
}

macro_rules! pair {
    ($name:ident, $bug:literal, $fixed:literal, $kind:expr) => {
        // frob:tests crates/grimble-lints/src/path.rs::scan
        #[test]
        fn $name() {
            let bug = run(Language::Rust, include_str!(concat!("corpus/path/", $bug)));
            assert_eq!(kinds(&bug), vec![$kind], "bug fires: {bug:?}");
            let fixed = run(
                Language::Rust,
                include_str!(concat!("corpus/path/", $fixed)),
            );
            assert!(fixed.sites.is_empty(), "fix is quiet: {fixed:?}");
        }
    };
}

pair!(
    merge_driver_format_fires_path003,
    "merge_driver_bug.rs",
    "merge_driver_fixed.rs",
    Kind::PathInCommandLine
);
pair!(
    allowlist_prefix_fires_path002,
    "allowlist_bug.rs",
    "allowlist_fixed.rs",
    Kind::StringPathSeparator
);
pair!(
    cwd_compare_fires_path002,
    "cwd_bug.rs",
    "cwd_fixed.rs",
    Kind::StringPathSeparator
);
pair!(
    absolute_fixture_fires_path001,
    "absolute_bug.rs",
    "absolute_fixed.rs",
    Kind::AbsoluteHostPath
);

// frob:tests crates/grimble-lints/src/path.rs::scan
#[test]
fn python_path_str_startswith_fires_and_fix_is_quiet() {
    let bug = run(Language::Python, include_str!("corpus/path/py_bug.py"));
    assert_eq!(kinds(&bug), vec![Kind::StringPathSeparator], "{bug:?}");
    let fixed = run(Language::Python, include_str!("corpus/path/py_fixed.py"));
    assert!(fixed.sites.is_empty(), "{fixed:?}");
}

// frob:tests crates/grimble-lints/src/path.rs::scan
#[test]
fn repo_relative_path_type_with_slash_is_quiet() {
    for (lang, src) in [
        (
            Language::Rust,
            include_str!("corpus/path/repo_path_quiet.rs"),
        ),
        (
            Language::Python,
            include_str!("corpus/path/repo_path_quiet.py"),
        ),
    ] {
        let r = run(lang, src);
        assert!(r.sites.is_empty(), "{lang:?}: {r:?}");
        assert!(r.unresolved.is_empty());
    }
}

// frob:tests crates/grimble-lints/src/path.rs::scan
#[test]
fn language_without_path_roles_is_unresolved_not_clean() {
    let r = run(
        Language::TypeScript,
        include_str!("corpus/path/roles_missing.ts"),
    );
    assert!(r.unresolved.contains(&Kind::StringPathSeparator));
    assert!(r.unresolved.contains(&Kind::PathInCommandLine));
}

// frob:tests crates/grimble-lints/src/path.rs::scan
#[test]
fn newline_escape_in_a_message_is_not_a_separator() {
    let src = "use std::path::Path;\nfn note(p: &Path) -> String {\n    format!(\"config: {}\\n  done\", p.display())\n}\n";
    let report = run(Language::Rust, src);
    assert!(report.sites.is_empty(), "{report:?}");
}
