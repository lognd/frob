//! GX002 and GX003 across screens through `crunk check`: scene files joined by flow files.

// frob:ticket 01M7HDSZSHJ9DCR3DDVXZA5PCM

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A flow file over `screens` with one click edge per `(from, to)` pair.
fn flow(screens: &[&str], edges: &[(&str, &str)]) -> String {
    let nodes: Vec<String> = screens.iter().map(|s| format!("\"{s}:default\"")).collect();
    let edges = edges
        .iter()
        .map(|(from, to)| {
            format!(
                "[[edges]]\nfrom = \"{from}:default\"\nto = \"{to}:default\"\ntrigger = \"click\"\n"
            )
        })
        .collect::<Vec<_>>()
        .concat();
    format!("name = \"main\"\nnodes = [{}]\n{edges}", nodes.join(", "))
}

/// The cross-screen `rule` findings of a project with one focusable scene per screen and `edges`.
fn scene_findings(rule: &str, screens: &[&str], edges: &[(&str, &str)]) -> Vec<String> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "crunk.toml",
        crunk_spec::presets::preset("default").expect("default preset"),
    );
    for screen in screens {
        write(
            dir.path(),
            &format!("design/scenes/{screen}.scene.html"),
            "<button data-id=\"go\" data-focus-default></button>\n",
        );
    }
    write(
        dir.path(),
        "design/flows/main.flow.toml",
        &flow(screens, edges),
    );
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == rule && f.message.starts_with("scene '"))
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn a_scene_cycle_no_entry_reaches_fires_gx002() {
    let found = scene_findings(
        "GX002",
        &["home", "about", "ghost", "haunt"],
        &[("home", "about"), ("ghost", "haunt"), ("haunt", "ghost")],
    );
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(found.iter().any(|m| m.starts_with("scene 'ghost'")));
    assert!(found.iter().any(|m| m.starts_with("scene 'haunt'")));
}

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn a_connected_flow_is_clean_for_gx002() {
    let found = scene_findings("GX002", &["home", "about"], &[("home", "about")]);
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn scenes_that_never_return_to_an_entry_fire_gx003() {
    let found = scene_findings(
        "GX003",
        &["home", "loop_a", "loop_b"],
        &[
            ("home", "loop_a"),
            ("loop_a", "loop_b"),
            ("loop_b", "loop_a"),
        ],
    );
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(found.iter().any(|m| m.starts_with("scene 'loop_a'")));
    assert!(found.iter().any(|m| m.starts_with("scene 'loop_b'")));
}

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn a_flow_that_ends_is_not_a_trap_for_gx003() {
    let found = scene_findings("GX003", &["home", "done"], &[("home", "done")]);
    assert!(found.is_empty(), "{found:?}");
}
