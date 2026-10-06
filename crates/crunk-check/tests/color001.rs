//! COLOR001 over the shared `style` capability: the mdtest corpus (`tests/mdtest/color001.md`) and
//! the end-to-end behaviours the corpus cannot express.

// frob:ticket 01M48FXB2PXX2FBXFKCFWSQYH1

use std::path::Path;

use crunk_check::{CheckOptions, run};

/// The default preset as `crunk.toml`.
fn spec() -> &'static str {
    crunk_spec::presets::preset("default").expect("default preset")
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// Run crunk over one source file of a fresh repository holding the default preset.
fn findings_of(spec_text: &str, rel: &str, source: &str) -> Vec<gob_rules::Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", spec_text);
    write(dir.path(), rel, source);
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
}

fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/crunk-check/src/rules/color001.rs::group
    findings_of(spec(), &case.file_name, &case.text)
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

// frob:tests crates/crunk-check/src/rules/color001.rs::group
#[test]
fn the_message_names_the_nearest_palette_token_and_the_distance() {
    let f = findings_of(spec(), "a.css", ".a { color: #1b1b1b; }\n");
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(
        f[0].message.contains("nearest is --color-ink (distance"),
        "{}",
        f[0].message
    );
}

// frob:tests crates/crunk-check/src/rules/color001.rs::group
#[test]
fn off_in_lint_silences_the_rule() {
    let off = format!(
        "{}\n",
        spec().replace("[lint]", "[lint]\nCOLOR001 = \"off\"")
    );
    assert!(findings_of(&off, "a.css", ".a { color: #ff0000; }\n").is_empty());
}

// frob:tests crates/crunk-check/src/rules/color001.rs::group
#[test]
fn without_a_valid_spec_the_rule_does_not_apply() {
    assert!(findings_of("", "a.css", ".a { color: #ff0000; }\n").is_empty());
}
