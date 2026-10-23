//! Scene document discovery through `crunk check`: unloadable `.scene.html` files become findings.

// frob:ticket 01M5H30AT7FM2BAXCTTDEGWV6J

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, bytes: &[u8]) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, bytes).expect("write");
}

fn scene005(files: &[(&str, &[u8])]) -> Vec<gob_rules::Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "crunk.toml",
        crunk_spec::presets::preset("default")
            .expect("default preset")
            .as_bytes(),
    );
    for (rel, bytes) in files {
        write(dir.path(), rel, bytes);
    }
    run(dir.path(), &CheckOptions::default())
        .expect("run does not fail")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "SCENE005")
        .collect()
}

// frob:tests crunk_check.run
// frob:tests SceneDocFacts.load
#[test]
fn a_non_utf8_nested_scene_is_a_finding_not_a_panic() {
    let found = scene005(&[
        ("design/scenes/ok.scene.html", b"<div data-id=\"a\"></div>"),
        ("design/scenes/x/bad.SCENE.html", &[0xff, 0xfe, 0x00]),
    ]);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].message.contains("UTF-8") || found[0].message.contains("utf"),
        "{found:?}"
    );
}

// frob:tests crunk_check.run
#[test]
fn well_formed_scenes_raise_no_scene005() {
    let found = scene005(&[("design/scenes/ok.scene.html", b"<div data-id=\"a\"></div>")]);
    assert!(found.is_empty(), "{found:?}");
}
