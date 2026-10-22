//! The GX014 rule page of `tests/mdtest/gx014.md` as an mdtest corpus.

// frob:ticket 01M4CXSD8DEYB69E5J7Q1ABGXK

use crunk_check::{CheckOptions, run};

/// Run `crunk check` over the case's file in a fresh repository holding the default preset.
fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/crunk-check/src/ugui.rs::Gx014
    // frob:tests crates/crunk-check/src/ugui.rs::UguiLiteralCheck
    let dir = tempfile::tempdir().expect("tempdir");
    let preset = crunk_spec::presets::preset("default").expect("default preset");
    std::fs::write(dir.path().join("crunk.toml"), preset).expect("write config");
    let path = dir.path().join(&case.file_name);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(&path, &case.text).expect("write source");
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
