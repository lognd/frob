//! The phase 6 exit, end to end: a small hullbreach game UI (a USS sheet, a uGUI prefab generator
//! and a HUD scene on a console profile) is checked through `crunk_check::run`, and the USS token
//! rule (COLOR001), the uGUI generator literal check (GX014) and a GX rule (GX015) each report a
//! finding carrying evidence.

// frob:ticket 01M4CXSAG0YPF18FX3KAPVX45C

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The default preset plus one console profile.
fn config() -> String {
    format!(
        "{}\n[game]\ncoverage = []\n\n[[game.profile]]\nid = \"tv\"\nkind = \"console\"\nwidth = 1920\nheight = 1080\n",
        crunk_spec::presets::preset("default").expect("default preset")
    )
}

// frob:tests crates/crunk-check/src/lib.rs::run
// frob:tests crates/crunk-check/src/ugui.rs::Gx014
// frob:tests crates/crunk-check/src/gx_pack.rs::Gx015
#[test]
fn hullbreach_game_ui_reports_uss_token_ugui_literal_and_gx_findings() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", &config());
    write(
        dir.path(),
        "styles/hud.uss",
        ".hull-warning { color: #e63327; -unity-font-style: bold; }\n",
    );
    write(
        dir.path(),
        "Editor/HudPrefabBuilder.cs",
        "using UnityEditor;\nclass HudPrefabBuilder {\n  void Build() {\n    img.color = new Color(0.9f, 0.2f, 0.15f, 1f);\n    PrefabUtility.SaveAsPrefabAsset(go, \"Hud.prefab\");\n  }\n}\n",
    );
    write(
        dir.path(),
        "design/scenes/hud.scene.json",
        r#"{"viewport":{"width":1920,"height":1080},"root":{"id":"root","kind":"box","style":{"width":1920,"height":1080},"children":[{"id":"pause","kind":"box","interactive":true,"style":{"width":200,"height":60}}]}}"#,
    );
    let found = run(dir.path(), &CheckOptions::default()).expect("run");
    let of = |id: &str| -> Vec<(String, String)> {
        found
            .report
            .findings
            .iter()
            .filter(|f| f.rule.as_str() == id)
            .map(|f| {
                let file = f
                    .span
                    .and_then(|s| found.report.files.path(s.file))
                    .unwrap_or("")
                    .to_owned();
                (file, f.message.clone())
            })
            .collect()
    };

    let uss = of("COLOR001");
    assert!(
        uss.iter()
            .any(|(file, m)| file == "styles/hud.uss" && m.contains("nearest is")),
        "{uss:?}"
    );
    let ugui = of("GX014");
    assert!(
        ugui.iter()
            .any(|(file, m)| file == "Editor/HudPrefabBuilder.cs"
                && m.contains("generated token constant")),
        "{ugui:?}"
    );
    let gx = of("GX015");
    assert!(
        gx.iter()
            .any(|(file, m)| file == "design/scenes/hud.scene.json" && !m.is_empty()),
        "{gx:?}"
    );
}
