//! CAP005 end to end over real temp repositories: a new or widened `may` grant is a finding
//! until an attester's approval is in `grimble.grants.toml`; narrowing and removal need none.

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use std::path::Path;

use grimble_bind::grant_ack::{self, Approval, Kind};
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const ME: &str = "me@example.com";
const AT: &str = "2026-10-02T00:00:00Z";

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    std::fs::create_dir_all(p.parent().expect("parent")).expect("mkdir");
    std::fs::write(p, text).expect("write");
}

/// A repository with a model `body` for node `a` (owning `src/**`) and three source files.
fn repo(body: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    for f in ["src/lib.rs", "src/loose.rs", "src/deep/x.rs"] {
        write(root, f, "pub fn f() {}\n");
    }
    write(
        root,
        "frob.toml",
        &format!("[evidence]\nattesters = [\"{ME}\"]\n"),
    );
    write(
        root,
        "design/m.grmb",
        &format!(
            "grimble = \"2\";\nmodule m;\n{body}\nnode d : trusted {{ owns \"design/**\"; }}\n"
        ),
    );
    dir
}

fn bind(root: &Path) -> Binding {
    let walked = gob_walk::walk(root, &gob_walk::WalkConfig::default()).expect("walk");
    let model = ModelFiles::new().with_file(
        "design/m.grmb",
        std::fs::read(root.join("design/m.grmb")).expect("read"),
    );
    grimble_bind::bind(&BindInput {
        root,
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn cap005(b: &Binding) -> Vec<String> {
    b.findings
        .iter()
        .filter(|f| f.rule == "CAP005")
        .map(|f| f.message.clone())
        .collect()
}

/// Record an ack as `grimble ack --grants` does: approve everything pending, write the ledger.
fn ack(root: &Path, who: &str) {
    let b = bind(root);
    let old = grant_ack::load(root).expect("load").unwrap_or_default();
    let next = grant_ack::approve(&b.grants, &old, who, "reviewed", AT);
    write(root, grant_ack::LEDGER_FILE, &grant_ack::render(&next));
}

// frob:tests crates/grimble-bind/src/grant_ack.rs::evaluate
#[test]
fn grant_changes_need_a_human_ack() {
    let dir = repo("node a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }");
    let root = dir.path();
    assert!(cap005(&bind(root)).is_empty(), "no ledger means opted out");

    ack(root, ME);
    assert!(cap005(&bind(root)).is_empty(), "acked grant is quiet");

    // A new atom on the same node.
    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; may fs.write at \"src/lib.rs\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    let found = cap005(&bind(root));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("fs.write"), "{found:?}");
    assert!(found[0].contains("grimble ack --grants"), "{found:?}");
    ack(root, ME);
    assert!(cap005(&bind(root)).is_empty());

    // A broader `at`.
    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/**\"; may fs.write at \"src/lib.rs\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    let b = bind(root);
    assert_eq!(cap005(&b).len(), 1);
    assert_eq!(b.grants.pending[0].kind, Kind::Widened);
    ack(root, ME);
    assert!(cap005(&bind(root)).is_empty());

    // Narrowing needs no ack.
    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; may fs.write at \"src/lib.rs\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    assert!(cap005(&bind(root)).is_empty(), "narrowing is quiet");

    // A new node grant.
    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; may fs.write at \"src/lib.rs\"; }\nnode b : trusted { owns \"src/deep/**\"; may net.connect; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    let found = cap005(&bind(root));
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("node/b"), "{found:?}");
    ack(root, ME);
    assert!(cap005(&bind(root)).is_empty());

    // Removing a grant needs no ack, and the next ack prunes its approval.
    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }\nnode b : trusted { owns \"src/deep/**\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    assert!(cap005(&bind(root)).is_empty(), "removal is quiet");
    ack(root, ME);
    let left = grant_ack::load(root).expect("load").expect("ledger");
    assert_eq!(left.len(), 1, "{left:?}");
}

// frob:tests crates/grimble-bind/src/grant_ack.rs::pending
#[test]
fn an_approval_by_a_non_attester_is_no_approval() {
    let dir = repo("node a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }");
    let root = dir.path();
    ack(root, "stranger@example.com");
    let found = cap005(&bind(root));
    assert_eq!(found.len(), 1, "{found:?}");
}

// frob:tests crates/grimble-bind/src/grant_ack.rs::pending
#[test]
fn a_renamed_node_is_a_new_identity_and_reack_is_idempotent() {
    let dir = repo("node a : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }");
    let root = dir.path();
    ack(root, ME);
    let first = std::fs::read_to_string(root.join(grant_ack::LEDGER_FILE)).expect("ledger");
    ack(root, ME);
    let again = std::fs::read_to_string(root.join(grant_ack::LEDGER_FILE)).expect("ledger");
    assert_eq!(
        first, again,
        "re-ack with nothing pending rewrites the same bytes"
    );

    write(
        root,
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode renamed : trusted { owns \"src/**\"; may fs.read at \"src/lib.rs\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    assert_eq!(cap005(&bind(root)).len(), 1);
}

// frob:tests crates/grimble-bind/src/grant_ack.rs::render
#[test]
fn the_ledger_round_trips() {
    let dir = tempfile::tempdir().expect("tempdir");
    let rows = vec![Approval {
        node: "node/a".into(),
        atom: "fs.read".into(),
        args: vec!["x".into()],
        selectors: vec!["\"src/**\"".into()],
        attester: ME.into(),
        reason: "why \"quoted\"".into(),
        at: AT.into(),
    }];
    write(
        dir.path(),
        grant_ack::LEDGER_FILE,
        &grant_ack::render(&rows),
    );
    assert_eq!(grant_ack::load(dir.path()).expect("load"), Some(rows));
}
