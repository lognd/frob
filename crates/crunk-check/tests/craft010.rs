//! CRAFT010 through `crunk check`: a project that deletes its motion to pass the motion rules is
//! reported by the paired presence rule.

// frob:ticket 01M4CXT7KWGP62H0CRCDTBY8Q0

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The CRAFT010 messages `crunk check` reports for one stylesheet in a default-preset project.
fn craft010(source: &str) -> Vec<String> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "crunk.toml",
        crunk_spec::presets::preset("default").expect("default preset"),
    );
    write(dir.path(), "styles/a.css", source);
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "CRAFT010")
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/craft010.rs::Craft010
#[test]
fn a_project_that_deleted_its_motion_reports_the_missing_motion_policy() {
    let found = craft010(".a { color: #1b1b1b; }\n");
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("no motion policy"), "{}", found[0]);
}

// frob:tests crates/crunk-rules/src/rules/craft010.rs::Craft010
#[test]
fn motion_with_a_reduced_motion_twin_is_clean() {
    let found = craft010(
        ".a { transition: opacity 200ms ease; }\n@media (prefers-reduced-motion: reduce) { .a { transition: none; } }\n",
    );
    assert!(found.is_empty(), "{found:?}");
}
