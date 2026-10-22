//! The GX014-GX021 rule pages of `tests/mdtest` as one mdtest corpus (the pages share a directory,
//! so one runner serves every page).

// frob:ticket 01M4CXSD8DEYB69E5J7Q1ABGXK
// frob:ticket 01M4CXSEFJEZDQFGESPKDEW049

use crunk_check::{CheckOptions, run};

/// Name of the project config; a case file with this name extends the preset instead of replacing it.
const CONFIG: &str = "crunk.toml";

/// Run `crunk check` over the case's files in a fresh repository holding the default preset, the
/// case's section config (a `[game]` table) appended to `crunk.toml`.
fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/crunk-check/src/ugui.rs::Gx014
    // frob:tests crates/crunk-check/src/ugui.rs::UguiLiteralCheck
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx015
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx016
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx017
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx018
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx019
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx020
    // frob:tests crates/crunk-check/src/gx_pack.rs::Gx021
    // frob:tests crates/crunk-check/src/gx_pack.rs::group
    // frob:tests crates/crunk-check/src/gx_pack.rs::decide
    let dir = tempfile::tempdir().expect("tempdir");
    let mut config = crunk_spec::presets::preset("default")
        .expect("default preset")
        .to_string();
    let sources = std::iter::once((&case.file_name, &case.text)).chain(
        case.files
            .iter()
            .filter(|f| f.file_name != case.file_name)
            .map(|f| (&f.file_name, &f.text)),
    );
    if let Some(section) = &case.config {
        config.push('\n');
        config.push_str(section);
    }
    for (name, text) in sources {
        if name == CONFIG {
            config.push('\n');
            config.push_str(text);
        } else {
            let path = dir.path().join(name);
            std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
            std::fs::write(&path, text).expect("write source");
        }
    }
    std::fs::write(dir.path().join(CONFIG), config).expect("write config");
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
