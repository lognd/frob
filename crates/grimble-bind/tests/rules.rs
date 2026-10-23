//! The SYS rule pages of `src/rules/*.md` as an mdtest corpus. A `grmb` example is the model
//! of a small fixed repository; a `rust` example edits an end of an acked flow, so the drift
//! rules (SYS006 to SYS008) compare it with the lock the ack wrote.

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P

use std::path::Path;

use gob_lock::LockFile;
use gob_rules::Finding;
use gob_text::FileInterner;
use grimble_bind::ack::{AckRequest, plan_ack};
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

/// The model the drift examples start from: one flow between two owned crates.
const DRIFT_MODEL: &str = r#"grimble = "2";
module m;

node p : trusted { owns "p/**"; }
node c : trusted { owns "c/**"; }
node d : trusted { owns "design/**"; }

flow f : p -> c {
  producer "p/lib.rs::emit";
  consumer "c/lib.rs::take";
}
"#;

/// A body big enough to be a stable binding unit.
const BIG: &str = "{ let mut total = x; for i in 0..x { total = total + i * 2; } if total > 10 { total - 1 } else { total + 1 } }";

/// A Python file that opens a file, spawns a process and listens on a socket.
const PY: &str = "import socket\nimport subprocess\n\ndef go():\n    with open(\"/etc/hosts\") as f:\n        f.read()\n    subprocess.run([\"ls\"])\n    s = socket.socket()\n    s.listen()\n";

/// A ledger approving `fs.read` of node `a` on `src/lib.rs` only.
const GRANT_LEDGER: &str = r#"[[grant]]
node = "node/a"
atom = "fs.read"
args = []
selectors = ['"src/lib.rs"']
attester = "me@example.com"
reason = "initial"
at = "2026-10-02T00:00:00Z"
"#;

/// The files every `grmb` example finds beside its model.
fn fixed_files(web: bool) -> Vec<(&'static str, String)> {
    let mut files = vec![
        ("src/lib.rs", "pub fn run() {}\n".to_owned()),
        ("src/loose.rs", "pub fn loose() {}\n".to_owned()),
        ("a/lib.rs", "pub fn send() {}\n".to_owned()),
        ("b/lib.rs", "pub fn recv() {}\n".to_owned()),
        ("tests/t.rs", "#[test]\nfn it_works() {}\n".to_owned()),
        ("docs/spec.md", "# spec\n".to_owned()),
    ];
    if web {
        files.push((
            "src/api/svc.ts",
            "export function svc() { return 1; }\n".to_owned(),
        ));
        files.push((
            "src/ui/app.ts",
            "import { svc } from \"../api/svc\";\nexport function app() { return svc(); }\n"
                .to_owned(),
        ));
    }
    files
}

/// Write `text` at `rel` under `root`.
fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    std::fs::create_dir_all(p.parent().expect("a file has a parent")).expect("mkdir");
    std::fs::write(p, text).expect("write");
}

/// Bind the repository at `root`.
fn bind(root: &Path, modeled: &[String]) -> Binding {
    let walked = gob_walk::walk(root, &gob_walk::WalkConfig::default()).expect("walk");
    let mut model = ModelFiles::new();
    for f in &walked.files {
        if Path::new(&f.path).extension().is_some_and(|e| e == "grmb") {
            model = model.with_file(&f.path, std::fs::read(root.join(&f.path)).expect("read"));
        }
    }
    grimble_bind::bind(&BindInput {
        root,
        entries: &walked.files,
        model: &model,
        modeled,
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// The findings of `binding` for `rule`, as pipeline findings.
fn findings_of(binding: &Binding, rule: &gob_rules::RuleId) -> Vec<Finding> {
    let mut files = FileInterner::new();
    binding
        .findings
        .iter()
        .filter(|f| f.rule == rule.as_str())
        .cloned()
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

/// Ack the drift repository at `root` so the lock holds the current digests.
fn ack_flow(root: &Path) {
    let plan = plan_ack(
        &bind(root, &[]),
        root,
        &AckRequest {
            targets: vec!["flow/f".to_owned()],
            all: false,
            reason: Some("initial".to_owned()),
            renames: Vec::new(),
            actor: "Me <me@example.com>".to_owned(),
            at: "2026-10-02T00:00:00Z".to_owned(),
        },
    )
    .expect("ack plan");
    let lock: &LockFile = &plan.plan.lock;
    lock.save(&root.join("grimble.lock")).expect("save lock");
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-bind/src/rules/cap001.rs::Cap001
    // frob:tests crates/grimble-bind/src/rules/cap002.rs::Cap002
    // frob:tests crates/grimble-bind/src/rules/cap005.rs::Cap005
    // frob:tests crates/grimble-bind/src/rules/sys001.rs::Sys001
    // frob:tests crates/grimble-bind/src/rules/sys002.rs::Sys002
    // frob:tests crates/grimble-bind/src/rules/sys003.rs::Sys003
    // frob:tests crates/grimble-bind/src/rules/sys004.rs::Sys004
    // frob:tests crates/grimble-bind/src/rules/sys005.rs::Sys005
    // frob:tests crates/grimble-bind/src/rules/sys006.rs::Sys006
    // frob:tests crates/grimble-bind/src/rules/sys007.rs::Sys007
    // frob:tests crates/grimble-bind/src/rules/sys008.rs::Sys008
    // frob:tests crates/grimble-bind/src/rules/sys009.rs::Sys009
    // frob:tests crates/grimble-bind/src/rules/sys010.rs::Sys010
    // frob:tests crates/grimble-bind/src/rules/sys011.rs::Sys011
    // frob:tests crates/grimble-bind/src/rules/sys013.rs::Sys013
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let words = case.config.as_deref().unwrap_or("");
    let has = |w: &str| words.split_whitespace().any(|x| x == w);
    if case.language == "rust" {
        write(root, "design/m.grmb", DRIFT_MODEL);
        write(
            root,
            "p/lib.rs",
            &format!("pub fn emit(x: u32) -> u32 {BIG}\n"),
        );
        write(
            root,
            "c/lib.rs",
            &format!("pub fn take(x: u32) -> u32 {BIG}\n"),
        );
        ack_flow(root);
        write(root, &case.file_name, &case.text);
        return findings_of(&bind(root, &[]), &case.rule);
    }
    for (rel, text) in fixed_files(has("web")) {
        write(root, rel, &text);
    }
    if has("py") {
        write(root, "src/x.py", PY);
    }
    if has("grants") {
        write(
            root,
            "frob.toml",
            "[evidence]\nattesters = [\"me@example.com\"]\n",
        );
        write(root, "grimble.grants.toml", GRANT_LEDGER);
    }
    write(root, &case.file_name, &case.text);
    let modeled = if has("modeled") {
        vec!["\"src/**\" & lang(rust)".to_owned()]
    } else {
        Vec::new()
    };
    findings_of(&bind(root, &modeled), &case.rule)
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);
