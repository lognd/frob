//! Trunk-mode ticket verbs on a feature branch say which ref they read and commit to.
// frob:ticket 01M4FG552GZ9FMB000B76AS8XH

mod common;

use std::path::Path;

use serde_json::Value;

fn git(dir: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

fn run(dir: &Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(dir)
        .arg("--json")
        .args(args)
        .output()
        .expect("frob");
    serde_json::from_slice(&out.stdout).expect("json")
}

fn notices(v: &Value) -> Vec<String> {
    v["warnings"]
        .as_array()
        .expect("warnings")
        .iter()
        .filter_map(|w| w.as_str())
        .filter(|w| w.starts_with("ticket ledger:"))
        .map(str::to_owned)
        .collect()
}

// frob:tests crates/frob/src/workspace.rs::ledger_site_notice
#[test]
fn list_and_new_on_a_feature_branch_name_the_trunk_ref_but_main_stays_quiet() {
    let dir = common::git_repo();
    let root = dir.path();
    run(root, &["init"]);
    git(root, &["add", "-A"]);
    git(root, &["commit", "-q", "-m", "base"]);

    assert!(notices(&run(root, &["ticket", "list"])).is_empty());

    git(root, &["checkout", "-q", "-b", "feat/x"]);
    let list = notices(&run(root, &["ticket", "list"]));
    assert_eq!(list.len(), 1, "{list:?}");
    assert!(
        list[0].contains("refs/heads/main") && list[0].contains("feat/x"),
        "{list:?}"
    );
    assert!(list[0].contains("not the ledger"), "{list:?}");

    let new = run(
        root,
        &["ticket", "new", "--title", "t", "--acceptance", "ok"],
    );
    assert_eq!(
        notices(&new).len(),
        1,
        "a writing verb says it commits to main: {new}"
    );
}
