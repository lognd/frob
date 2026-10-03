//! Lock-backed drift (binding.md 5, 6.6 to 6.8, 10): the `ack/*` and `identity/*` cases and the
//! SYS006 to SYS008 truth tables, run over two-crate fixtures that are bound, acked and edited
//! in a temporary repository (the lock holds real digests, so the cases are built, not stored).

// frob:ticket 01M3Z714820D1SK6X44T9R1B70

use std::path::Path;

use gob_lock::{LockFile, PlanError};
use gob_rules::Severity;
use grimble_bind::ack::{AckError, AckRequest, plan_ack};
use grimble_bind::{BindInput, Binding, reason_of_message};
use grimble_model::ModelFiles;

const MODEL: &str = r#"grimble = "2";
module m;

node p : trusted { owns "p/**"; }
node c : trusted { owns "c/**"; }
node d : trusted { owns "design/**"; }

flow f : p -> c {
  producer "p/lib.rs::emit";
  consumer "c/lib.rs::take";
}
"#;

const BIG: &str = "{ let mut total = x; for i in 0..x { total = total + i * 2; } if total > 10 { total - 1 } else { total + 1 } }";

fn emit(ty: &str) -> String {
    format!("pub fn emit(x: {ty}) -> {ty} {BIG}\n")
}

fn take() -> String {
    format!("pub fn take(x: u32) -> u32 {BIG}\n")
}

struct Repo {
    dir: tempfile::TempDir,
}

impl Repo {
    fn new() -> Self {
        let r = Self {
            dir: tempfile::tempdir().unwrap(),
        };
        r.write("design/m.grmb", MODEL);
        r.write("p/lib.rs", &emit("u32"));
        r.write("c/lib.rs", &take());
        r
    }

    fn root(&self) -> &Path {
        self.dir.path()
    }

    fn write(&self, rel: &str, text: &str) {
        let p = self.root().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }

    fn bind(&self) -> Binding {
        let walked = gob_walk::walk(self.root(), &gob_walk::WalkConfig::default()).unwrap();
        let mut model = ModelFiles::new();
        for f in &walked.files {
            if f.path.ends_with(".grmb") {
                model = model.with_file(&f.path, std::fs::read(self.root().join(&f.path)).unwrap());
            }
        }
        grimble_bind::bind(&BindInput {
            root: self.root(),
            entries: &walked.files,
            model: &model,
            modeled: &[],
            strict: false,
        })
    }

    fn ack(
        &self,
        targets: &[&str],
        all: bool,
        reason: Option<&str>,
    ) -> Result<Vec<String>, AckError> {
        self.ack_with(targets, all, reason, &[])
    }

    fn ack_with(
        &self,
        targets: &[&str],
        all: bool,
        reason: Option<&str>,
        renames: &[(&str, &str)],
    ) -> Result<Vec<String>, AckError> {
        let plan = plan_ack(
            &self.bind(),
            self.root(),
            &AckRequest {
                targets: targets.iter().map(|t| (*t).to_owned()).collect(),
                all,
                reason: reason.map(str::to_owned),
                renames: renames
                    .iter()
                    .map(|(a, b)| ((*a).to_owned(), (*b).to_owned()))
                    .collect(),
                actor: "Me <me@example.com>".to_owned(),
                at: "2026-10-02T00:00:00Z".to_owned(),
            },
        )?;
        plan.plan
            .lock
            .save(&self.root().join("grimble.lock"))
            .unwrap();
        Ok(plan.plan.acked)
    }

    fn lock(&self) -> LockFile {
        LockFile::load(&self.root().join("grimble.lock")).unwrap()
    }
}

/// `RULE severity[:reason]` of the drift findings, sorted.
fn drift(b: &Binding) -> Vec<String> {
    let mut v: Vec<String> = b
        .findings
        .iter()
        .filter(|f| matches!(f.rule, "SYS006" | "SYS007" | "SYS008"))
        .map(|f| match f.severity {
            Severity::Unresolved => format!(
                "{} unresolved:{}",
                f.rule,
                reason_of_message(&f.message).unwrap_or("?")
            ),
            s => format!("{} {}", f.rule, format!("{s:?}").to_lowercase()),
        })
        .collect();
    v.sort();
    v
}

fn message_of<'a>(b: &'a Binding, rule: &str) -> &'a str {
    &b.findings
        .iter()
        .find(|f| f.rule == rule)
        .expect("finding")
        .message
}

fn acked_repo() -> Repo {
    let r = Repo::new();
    let acked = r.ack(&["flow/f"], false, Some("initial")).unwrap();
    assert_eq!(acked.len(), 3, "the flow and its two ends: {acked:?}");
    r
}

// frob:tests crates/grimble-bind/src/ack.rs::plan_ack
// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn ack_flow_records_both_ends_and_a_second_ack_is_a_no_op_and_clean() {
    let r = acked_repo();
    let lock = r.lock();
    assert!(lock.flows.contains_key("flow/f"));
    assert!(lock.entries.contains_key("p/lib.rs::emit"));
    assert!(lock.entries.contains_key("c/lib.rs::take"));
    let b = r.bind();
    assert_eq!(drift(&b), Vec::<String>::new(), "{:#?}", b.findings);
    assert_eq!(b.subjects["SYS006"], 1);
    assert_eq!(b.subjects["SYS007"], 2);
    assert!(r.ack(&["flow/f"], false, None).unwrap().is_empty());
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_producer_contract_changed_names_flow_and_both_ends() {
    let r = acked_repo();
    r.write("p/lib.rs", &emit("u64"));
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS006 error", "SYS007 error"]);
    let m = message_of(&b, "SYS006");
    for needle in [
        "flow/f",
        "p/lib.rs::emit",
        "c/lib.rs::take",
        "consumer",
        "behind",
    ] {
        assert!(m.contains(needle), "`{needle}` missing from {m}");
    }
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_matrix_both_equal_one_behind_both_behind_and_ends_differ() {
    // Equal and acked: clean (covered above). Consumer behind after the producer moved:
    let r = acked_repo();
    r.write("c/lib.rs", &format!("pub fn take(x: u64) -> u64 {BIG}\n"));
    let b = r.bind();
    assert!(drift(&b).contains(&"SYS006 error".to_owned()));
    assert!(
        message_of(&b, "SYS006").contains("producer"),
        "{}",
        message_of(&b, "SYS006")
    );
    // Both moved together: each is ahead of its ack, the ends agree, still skew from the ack.
    r.write("p/lib.rs", &emit("u64"));
    let b = r.bind();
    let m = message_of(&b, "SYS006");
    assert!(
        m.contains("producer") && m.contains("consumer") && !m.contains("ends differ"),
        "{m}"
    );
    // Re-acked at the new pair: clean again.
    r.ack(&["flow/f"], false, Some("both moved")).unwrap();
    assert_eq!(drift(&r.bind()), Vec::<String>::new());
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys007_kinds_facet_gone_and_the_body_edit_is_not_a_contract_skew() {
    let r = acked_repo();
    r.write(
        "c/lib.rs",
        &format!("pub fn take(x: u32) -> u32 {}\n", BIG.replace("+ 1", "+ 3")),
    );
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS007 error"]);
    assert!(message_of(&b, "SYS007").contains("kind facet"));
    assert!(message_of(&b, "SYS007").contains("body"));
    // Gone with nothing to pair it with.
    r.write("c/lib.rs", "pub fn other() {}\n");
    let b = r.bind();
    assert!(
        message_of(&b, "SYS007").contains("kind gone"),
        "{}",
        message_of(&b, "SYS007")
    );
    assert!(!drift(&b).iter().any(|d| d.starts_with("SYS008")));
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
// frob:tests crates/grimble-bind/src/ack.rs::plan_ack
#[test]
fn identity_body_rename_is_sys008_then_ack_rename_carries_the_entry() {
    let r = acked_repo();
    r.write("c/lib.rs", &take().replace("take", "receive"));
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS008 advisory"], "{:#?}", b.findings);
    assert!(
        message_of(&b, "SYS008").contains("grimble ack --rename c/lib.rs::take c/lib.rs::receive")
    );
    let acked = r
        .ack_with(
            &[],
            false,
            Some("renamed"),
            &[("c/lib.rs::take", "c/lib.rs::receive")],
        )
        .unwrap();
    assert_eq!(acked, ["c/lib.rs::receive"]);
    let lock = r.lock();
    assert!(!lock.entries.contains_key("c/lib.rs::take"));
    assert_eq!(lock.renamed["c/lib.rs::take"], "c/lib.rs::receive");
    assert_eq!(lock.flows["flow/f"].consumer.identity, "c/lib.rs::receive");
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn identity_body_rename_several_candidates_are_all_listed_and_trivial_bodies_are_gone() {
    let r = acked_repo();
    r.write(
        "c/lib.rs",
        &(take().replace("take", "a") + &take().replace("take", "b")),
    );
    let b = r.bind();
    let m = message_of(&b, "SYS008");
    assert!(
        m.contains("c/lib.rs::a") && m.contains("c/lib.rs::b"),
        "{m}"
    );
    assert_eq!(drift(&b), ["SYS008 advisory"]);
    // A trivial body is never paired.
    let r = Repo::new();
    r.write("p/small.rs", "pub fn tiny() {}\n");
    r.ack(&["p/small.rs::tiny"], false, None).unwrap();
    r.write("p/small.rs", "pub fn small() {}\n");
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS007 error"], "{:#?}", b.findings);
    assert!(message_of(&b, "SYS007").contains("kind gone"));
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn identity_rename_and_edit_is_not_paired_and_ack_rename_refuses_a_different_body() {
    let r = acked_repo();
    r.write(
        "c/lib.rs",
        &format!(
            "pub fn receive(x: u32) -> u32 {}\n",
            BIG.replace("+ 1", "+ 9")
        ),
    );
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS007 error"]);
    assert!(message_of(&b, "SYS007").contains("kind gone"));
    let err = r
        .ack_with(&[], false, None, &[("c/lib.rs::take", "c/lib.rs::receive")])
        .unwrap_err();
    assert!(matches!(err, AckError::Rename { .. }), "{err}");
}

// frob:tests crates/grimble-bind/src/ack.rs::plan_ack
#[test]
fn ack_refuse_may_unbound_and_node_targets_with_the_rows() {
    let r = Repo::new();
    r.write(
        "p/extra.rs",
        &format!("pub fn extra(x: u32) -> u32 {BIG}\n"),
    );
    for target in ["p/extra.rs::nothing", "node/p"] {
        let err = r.ack(&[target], false, None).unwrap_err();
        assert!(
            matches!(err, AckError::Refused { .. } | AckError::Resolve { .. }),
            "{target}: {err}"
        );
    }
    let err = r.ack(&["p/lib.rs::emit"], false, None);
    assert!(err.is_ok(), "owned by a Must node: {err:?}");
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
// frob:tests crates/grimble-bind/src/ack.rs::plan_ack
#[test]
fn rules_sys007_scheme_change_is_one_finding_per_entry_and_forces_reattest() {
    let r = acked_repo();
    let text = std::fs::read_to_string(r.root().join("grimble.lock")).unwrap();
    r.write(
        "grimble.lock",
        &text.replace("digest_scheme = 2", "digest_scheme = 1"),
    );
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS007 error", "SYS007 error", "SYS007 error"]);
    assert!(message_of(&b, "SYS007").contains("kind scheme"));
    let err = r.ack(&["p/lib.rs::emit"], false, Some("why")).unwrap_err();
    assert!(
        matches!(
            err,
            AckError::Plan(PlanError::MigrationRequired { entries: 3, .. })
        ),
        "{err}"
    );
    assert!(err.to_string().starts_with("E-LOCK-REATTEST"));
    r.ack(&[], true, Some("scheme bump reviewed")).unwrap();
    assert_eq!(drift(&r.bind()), Vec::<String>::new());
}

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_unresolved_when_an_end_is_hidden_or_the_lock_is_unreadable() {
    let r = acked_repo();
    // The consumer end now points into a file no adapter folds: the row is a placeholder.
    r.write(
        "design/m.grmb",
        &MODEL.replace("c/lib.rs::take", "c/data.bin::take"),
    );
    r.write("c/data.bin", "\0\0\0");
    let b = r.bind();
    let d = drift(&b);
    assert!(
        d.contains(&"SYS006 unresolved:unseen-remainder".to_owned()),
        "{d:?}"
    );
    // An unreadable lock is Unresolved, not clean.
    r.write("grimble.lock", "version = ");
    let b = r.bind();
    assert!(drift(&b).contains(&"SYS007 unresolved:lock-unreadable".to_owned()));
}
