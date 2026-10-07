//! Lock-backed drift (binding.md 5, 6.6 to 6.8, 10): the `ack/*` and `identity/*` cases and the
//! SYS006 to SYS008 truth tables, run over two-crate fixtures that are bound, acked and edited
//! in a temporary repository (the lock holds real digests, so the cases are built, not stored).

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4

use std::path::Path;

use gob_lock::{LockFile, PlanError};
use gob_rules::Severity;
use grimble_bind::ack::{AckError, AckRequest, plan_ack};
use grimble_bind::{BindInput, Binding, Reason};
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
        Self::with_model(MODEL)
    }

    fn with_model(model: &str) -> Self {
        let r = Self {
            dir: tempfile::tempdir().unwrap(),
        };
        r.write("design/m.grmb", model);
        r.write("p/lib.rs", &emit("u32"));
        r.write("c/lib.rs", &take());
        r.write("s/lib.rs", "pub fn msg(id: u32) -> u32 { id }\n");
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
        self.bind_with(12)
    }

    fn bind_with(&self, rename_min_tokens: usize) -> Binding {
        let walked = gob_walk::walk(self.root(), &gob_walk::WalkConfig::default()).unwrap();
        let mut model = ModelFiles::new();
        for f in &walked.files {
            if Path::new(&f.path).extension().is_some_and(|e| e == "grmb") {
                model = model.with_file(&f.path, std::fs::read(self.root().join(&f.path)).unwrap());
            }
        }
        grimble_bind::bind(&BindInput {
            root: self.root(),
            entries: &walked.files,
            model: &model,
            modeled: &[],
            strict: false,
            rename_min_tokens,
            ledger_dir: "tickets",
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
                f.reason.map_or("?", Reason::code)
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
    assert!(r.ack(&["flow/f"], false, Some("why")).unwrap().is_empty());
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
    assert!(b.subjects["SYS008"] >= 1, "the lock entries are examined");
    assert!(!b.not_applicable.contains_key("SYS008"));
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
    r.ack(&["p/small.rs::tiny"], false, Some("why")).unwrap();
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
        .ack_with(
            &[],
            false,
            Some("moved"),
            &[("c/lib.rs::take", "c/lib.rs::receive")],
        )
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
        let err = r.ack(&[target], false, Some("why")).unwrap_err();
        assert!(
            matches!(err, AckError::Refused { .. } | AckError::Resolve { .. }),
            "{target}: {err}"
        );
    }
    let err = r.ack(&["p/lib.rs::emit"], false, Some("why"));
    assert!(err.is_ok(), "owned by a Must node: {err:?}");
}

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

// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_without_a_lock_have_no_subjects_so_must_measure_is_not_vacuous() {
    let r = Repo::new();
    let b = r.bind();
    assert!(!b.subjects.contains_key("SYS006"));
    assert!(!b.subjects.contains_key("SYS007"));
    assert_eq!(drift(&b), Vec::<String>::new());
}

fn contract_model(versioning: &str) -> String {
    format!(
        "grimble = \"2\";\nmodule m;\nnode p : trusted {{ owns \"p/**\"; }}\nnode c : trusted {{ owns \"c/**\"; }}\nnode s : trusted {{ owns \"s/**\"; }}\nnode d : trusted {{ owns \"design/**\"; }}\n\
         contract k {{ shape \"s/lib.rs::msg\"; {versioning} }}\n\
         flow f : p -> c {{ contract k; producer \"p/lib.rs::emit\"; consumer \"c/lib.rs::take\"; }}\n"
    )
}

/// An acked repo whose consumer ack records a stale shape digest (the consumer is behind).
fn consumer_behind_repo(versioning: &str) -> Repo {
    let r = Repo::with_model(&contract_model(versioning));
    r.ack(&["flow/f"], false, Some("initial")).unwrap();
    let mut lock = r.lock();
    let flow = lock.flows.get_mut("flow/f").unwrap();
    assert!(flow.producer.shape_contract.is_some(), "{flow:?}");
    assert_eq!(flow.producer.shape_contract, flow.consumer.shape_contract);
    flow.consumer.shape_contract = Some("0".repeat(64));
    lock.save(&r.root().join("grimble.lock")).unwrap();
    r
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_shape_contract_clean_when_all_three_agree() {
    let r = Repo::with_model(&contract_model("versioning compat=backward;"));
    r.ack(&["flow/f"], false, Some("initial")).unwrap();
    assert_eq!(drift(&r.bind()), Vec::<String>::new());
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_consumer_behind_is_warn_under_backward_and_error_otherwise() {
    let r = consumer_behind_repo("versioning compat=backward;");
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS006 warn"], "{:#?}", b.findings);
    assert!(message_of(&b, "SYS006").contains("consumer"));
    for versioning in ["", "versioning compat=none;", "versioning compat=forward;"] {
        let r = consumer_behind_repo(versioning);
        assert_eq!(drift(&r.bind()), ["SYS006 error"], "{versioning}");
    }
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rules_sys006_shape_changed_under_both_acks_is_error_even_under_backward() {
    let r = Repo::with_model(&contract_model("versioning compat=backward;"));
    r.ack(&["flow/f"], false, Some("initial")).unwrap();
    r.write(
        "s/lib.rs",
        "pub fn msg(id: u32, extra: u64) -> u32 { id + extra as u32 }\n",
    );
    let b = r.bind();
    assert_eq!(drift(&b), ["SYS006 error"], "{:#?}", b.findings);
    assert!(message_of(&b, "SYS006").contains("contract shape changed"));
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble-bind/src/ack.rs::plan_ack
#[test]
fn ack_without_a_reason_is_refused_and_a_rename_is_logged() {
    let r = Repo::new();
    for reason in [None, Some("  ")] {
        let err = r.ack(&["flow/f"], false, reason).unwrap_err();
        assert!(matches!(err, AckError::ReasonRequired), "{err}");
    }
    let r = acked_repo();
    r.write("c/lib.rs", &take().replace("take", "receive"));
    r.ack_with(
        &[],
        false,
        Some("renamed"),
        &[("c/lib.rs::take", "c/lib.rs::receive")],
    )
    .unwrap();
    let log = r.lock().ack_log;
    assert_eq!(log.len(), 1, "{log:?}");
    assert_eq!(log[0].kind, gob_lock::AckLogKind::Rename);
    assert_eq!(log[0].subject, "c/lib.rs::take");
    assert_eq!(log[0].target.as_deref(), Some("c/lib.rs::receive"));
    assert_eq!(log[0].actor, "Me <me@example.com>");
    assert_eq!(log[0].at, "2026-10-02T00:00:00Z");
    assert_eq!(log[0].reason, "renamed");
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/grimble-bind/src/drift.rs::evaluate
#[test]
fn rename_min_tokens_knob_decides_whether_a_body_can_be_paired() {
    let r = acked_repo();
    r.write("c/lib.rs", &take().replace("take", "receive"));
    assert_eq!(drift(&r.bind_with(12)), ["SYS008 advisory"]);
    assert_eq!(drift(&r.bind_with(10_000)), ["SYS007 error"]);
}

// frob:tests crates/grimble-bind/src/drift.rs::sys008_inapplicable
#[test]
fn sys008_with_a_lock_and_no_gone_anchor_is_a_measured_clean() {
    let r = acked_repo();
    let b = r.bind();
    assert!(!b.not_applicable.contains_key("SYS008"));
    assert!(b.subjects["SYS008"] >= 1, "lock entries are the subjects");
    assert!(!b.findings.iter().any(|f| f.rule == "SYS008"));
}

// frob:tests crates/grimble-bind/src/drift.rs::sys008_inapplicable
#[test]
fn sys008_without_a_lock_is_not_applicable_with_a_reason() {
    let r = Repo::new();
    let b = r.bind();
    assert!(b.not_applicable["SYS008"].contains("grimble.lock"));
    assert!(!b.subjects.contains_key("SYS008"), "no zero subject count");
}
