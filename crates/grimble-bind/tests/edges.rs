//! SYS013 walks the import and call edges of the snapshot between owners (binding.md B6, 6):
//! the shared web fixture (ui imports and calls api) fires without a flow, is quiet with a
//! flow in either direction, and an Unknown edge is Unresolved.

// frob:ticket 01M48FXAG32KFM90XWVFS8AX88

use std::path::Path;

use grimble_bind::{BindInput, Binding, reason_of_message};
use grimble_model::ModelFiles;

const FIXTURE: &str = "../gob-symbols/tests/corpus/web/repo";

const NODES: &str = "grimble = \"2\";\nmodule web;\n\nnode ui : trusted {\n  kind component;\n  owns \"src/components/**\";\n}\nnode api : trusted {\n  kind component;\n  owns \"src/api/**\";\n}\n";

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).unwrap();
    for e in std::fs::read_dir(from).unwrap().flatten() {
        let dest = to.join(e.file_name());
        if e.path().is_dir() {
            copy_tree(&e.path(), &dest);
        } else {
            std::fs::copy(e.path(), dest).unwrap();
        }
    }
}

/// Bind the web fixture under `model`, after `patch` rewrites files of the copy.
fn bind_web(model: &str, patch: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    copy_tree(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join(FIXTURE),
        dir.path(),
    );
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::write(dir.path().join("design/web.grmb"), model).unwrap();
    for (rel, text) in patch {
        std::fs::write(dir.path().join(rel), text).unwrap();
    }
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/web.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn sys013(b: &Binding) -> Vec<&grimble_bind::BindFinding> {
    b.findings.iter().filter(|f| f.rule == "SYS013").collect()
}

// frob:tests crates/grimble-bind/src/edges.rs::sys013
#[test]
fn a_cross_owner_import_and_call_with_no_flow_fires() {
    let b = bind_web(NODES, &[]);
    assert!(!b.not_applicable.contains_key("SYS013"));
    assert!(b.subjects.get("SYS013").copied().unwrap_or(0) >= 1);
    let f = sys013(&b);
    let fired: Vec<_> = f
        .iter()
        .filter(|f| reason_of_message(&f.message).is_none())
        .collect();
    assert_eq!(fired.len(), 1, "{f:?}");
    assert_eq!(fired[0].anchor, "edge/node/ui->node/api");
    assert!(
        fired[0].message.contains("fetchUser"),
        "{}",
        fired[0].message
    );
    assert_eq!(
        fired[0].file.as_deref(),
        Some("src/components/App.tsx"),
        "the finding points at the importing file"
    );
}

// frob:tests crates/grimble-bind/src/edges.rs::sys013
#[test]
fn a_flow_in_either_direction_between_the_owners_allows_the_edges() {
    for flow in ["flow uses : ui -> api { }", "flow back : api -> ui { }"] {
        let b = bind_web(&format!("{NODES}{flow}\n"), &[]);
        assert!(b.subjects.get("SYS013").copied().unwrap_or(0) >= 1);
        assert!(
            sys013(&b).iter().all(|f| f.message.starts_with('[')),
            "{flow}: no firing finding: {:?}",
            sys013(&b)
        );
    }
}

// frob:tests crates/grimble-bind/src/edges.rs::sys013
#[test]
fn an_unknown_edge_is_unresolved_never_clean() {
    let model = format!("{NODES}flow uses : ui -> api {{ }}\n");
    let app = "import { Button } from \"./Button\";\nconst handlers: Record<string, () => void> = {};\nexport function App(name: string) {\n  handlers[name]();\n  return <Button label=\"x\" />;\n}\n";
    let b = bind_web(&model, &[("src/components/App.tsx", app)]);
    let soft: Vec<_> = sys013(&b)
        .into_iter()
        .filter(|f| reason_of_message(&f.message) == Some("unresolved-edge"))
        .filter(|f| f.anchor.starts_with("edge/node/ui"))
        .collect();
    assert_eq!(soft.len(), 1, "{:?}", sys013(&b));
    assert!(
        soft[0].anchor.starts_with("edge/node/ui"),
        "{}",
        soft[0].anchor
    );
}

// frob:tests crates/grimble-bind/src/edges.rs::sys013_inapplicable
#[test]
fn one_code_owning_node_leaves_sys013_not_applicable() {
    let model = "grimble = \"2\";\nmodule web;\n\nnode ui : trusted {\n  kind component;\n  owns \"src/**\";\n}\n";
    let b = bind_web(model, &[]);
    assert!(b.not_applicable.contains_key("SYS013"));
    assert!(!b.subjects.contains_key("SYS013"));
    assert!(sys013(&b).is_empty());
}
