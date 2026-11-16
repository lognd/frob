//! GX002-GX005 over scene documents: the focus-graph rules, including the acceptance case.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use crate::support;

use crunk_rules::rules::{gx002::Gx002, gx003::Gx003, gx004::Gx004, gx005::Gx005};
use gob_rules::Finding;

const FILE: &str = "design/scenes/menu.scene.html";

fn msgs<R>(text: &str) -> Vec<String>
where
    R: gob_rules::RepoRule<support::Project> + Default,
{
    let host = support::project(FILE, text, None);
    let findings: Vec<Finding> = support::run::<R>(&host);
    findings.into_iter().map(|f| f.message).collect()
}

// frob:tests crates/crunk-rules/src/rules/gx002.rs::Gx002
#[test]
fn gx002_fires_naming_an_unreachable_button() {
    let text = "<button data-id=\"play\" data-focus-default data-nav-down=\"none\"></button>\n<button data-id=\"options\"></button>\n";
    let m = msgs::<Gx002>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("options"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
#[test]
fn gx003_fires_naming_a_trap() {
    let text = "<button data-id=\"play\" data-focus-default></button>\n<button data-id=\"options\" data-nav-up=\"none\"></button>\n";
    let m = msgs::<Gx003>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("options"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx004.rs::Gx004
#[test]
fn gx004_fires_without_a_default_and_is_quiet_with_one() {
    let none = "<button data-id=\"a\"></button>\n<button data-id=\"b\"></button>\n";
    assert_eq!(msgs::<Gx004>(none).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/gx004.rs::Gx004
#[test]
fn gx004_fires_without_a_default_and_is_quiet_with_one_part_2() {
    let one =
        "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n";
    assert!(msgs::<Gx004>(one).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/gx004.rs::Gx004
#[test]
fn gx004_fires_without_a_default_and_is_quiet_with_one_part_3() {
    let two = "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\" data-focus-default></button>\n";
    assert_eq!(msgs::<Gx004>(two).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/gx005.rs::Gx005
#[test]
fn gx005_fires_for_a_dangling_move() {
    let text = "<button data-id=\"a\" data-focus-default data-nav-down=\"ghost\"></button>\n<button data-id=\"b\"></button>\n";
    let m = msgs::<Gx005>(text);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("ghost"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFile.focus_graph
#[test]
fn focus_graph_lists_the_focusable_controls_of_a_scene() {
    let text =
        "<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n";
    let host = support::project(FILE, text, None);
    let facts = crunk_rules::CrunkHost::scene_docs(&host).expect("scene docs");
    assert_eq!(facts.files[0].focus_graph().nodes.len(), 2);
}

// frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
#[test]
fn gx003_resolves_grid_neighbours_and_exempts_a_modal_trap() {
    let grid = "<div data-focus-group style=\"display:grid;grid-template-columns:1fr 1fr\">\n<button data-id=\"a\" data-focus-default></button>\n<button data-id=\"b\"></button>\n<button data-id=\"c\"></button>\n<button data-id=\"d\"></button>\n</div>\n";
    assert!(msgs::<Gx003>(grid).is_empty());
    let trap = "<button data-id=\"open\" data-focus-default data-nav-down=\"ok\"></button>\n<div aria-modal=\"true\">\n<button data-id=\"ok\" data-nav-up=\"none\" data-nav-down=\"none\"></button>\n</div>\n";
    assert!(msgs::<Gx003>(trap).is_empty());
    let open = trap.replace(" aria-modal=\"true\"", "");
    assert_eq!(msgs::<Gx003>(&open).len(), 1);
}

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
const BTN: &str = "<button data-id=\"a\" data-focus-default></button>\n";

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
fn flow(edges: &[(&str, &str)]) -> String {
    let mut nodes: Vec<&str> = edges.iter().flat_map(|(a, b)| [*a, *b]).collect();
    nodes.sort_unstable();
    nodes.dedup();
    let list: Vec<String> = nodes.iter().map(|n| format!("\"{n}:default\"")).collect();
    let mut text = format!("name = \"main\"\nnodes = [{}]\n", list.join(", "));
    for (a, b) in edges {
        text.push_str(&format!(
            "[[edges]]\nfrom = \"{a}:default\"\nto = \"{b}:default\"\ntrigger = \"click\"\n"
        ));
    }
    text
}

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW
fn flow_msgs<R>(scenes: &[&str], edges: &[(&str, &str)]) -> Vec<String>
where
    R: gob_rules::RepoRule<support::Project> + Default,
{
    let first = format!("design/scenes/{}.scene.html", scenes[0]);
    let flow_text = flow(edges);
    let mut extra: Vec<(String, &str)> = scenes[1..]
        .iter()
        .map(|s| (format!("design/scenes/{s}.scene.html"), BTN))
        .collect();
    extra.push(("design/flows/main.flow.toml".to_owned(), flow_text.as_str()));
    let extra: Vec<(&str, &str)> = extra.iter().map(|(n, t)| (n.as_str(), *t)).collect();
    let host = support::project_files(&first, BTN, &extra, None);
    support::run::<R>(&host)
        .into_iter()
        .map(|f: Finding| f.message)
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/gx002.rs::Gx002
// frob:tests crates/crunk-rules/src/scene_docs.rs::focus_atlas
// frob:tests crates/crunk-rules/src/scene_docs.rs::focus_findings
// frob:tests crates/crunk-rules/src/scene_docs.rs::SceneDocFile::scene_name
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost::flows
#[test]
fn gx002_fires_for_a_scene_no_flow_transition_reaches() {
    let m = flow_msgs::<Gx002>(
        &["menu", "game", "a", "b"],
        &[("menu", "game"), ("a", "b"), ("b", "a")],
    );
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(m.iter().any(|s| s.contains("scene 'a'")), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx002.rs::Gx002
#[test]
fn gx002_is_quiet_when_every_scene_is_reachable_through_flows() {
    let m = flow_msgs::<Gx002>(&["menu", "game"], &[("menu", "game"), ("game", "menu")]);
    assert!(m.is_empty(), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
#[test]
fn gx003_fires_for_scenes_the_flow_never_leaves_back_to_an_entry() {
    let m = flow_msgs::<Gx003>(
        &["menu", "a", "b"],
        &[("menu", "a"), ("a", "b"), ("b", "a")],
    );
    assert_eq!(m.len(), 2, "{m:?}");
    assert!(m[0].contains("across screens"), "{m:?}");
}

// frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
#[test]
fn gx003_is_quiet_for_a_flow_that_ends_in_a_leaf_scene() {
    let m = flow_msgs::<Gx003>(&["menu", "credits"], &[("menu", "credits")]);
    assert!(m.is_empty(), "{m:?}");
}

// frob:tests crates/crunk-rules/src/flow_files.rs::FlowFacts.transitions
#[test]
fn transitions_drop_moves_between_states_of_one_screen() {
    let text = "name = \"m\"\nnodes = [\"a:x\", \"a:y\", \"b:x\"]\n[[edges]]\nfrom = \"a:x\"\nto = \"a:y\"\ntrigger = \"click\"\n[[edges]]\nfrom = \"a:y\"\nto = \"b:x\"\ntrigger = \"click\"\n";
    let flow = crunk_spec::parse_flow_file(text).expect("parses");
    let facts = crunk_rules::flow_files::FlowFacts {
        files: vec![("design/flows/m.flow.toml".to_owned(), flow)],
        problems: Vec::new(),
    };
    assert_eq!(facts.transitions(), vec![("a".to_owned(), "b".to_owned())]);
}
