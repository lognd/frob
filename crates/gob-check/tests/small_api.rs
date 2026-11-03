//! Small public helpers of the shared pipeline: shared-context lookups, scope views, repo-group
//! flags, stage timing, the fidelity reason and the sibling schema.

use std::collections::BTreeSet;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

use gob_check::sibling::fidelity_reason;
use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, FileIndex, Product, RepoGroup, ScopeView,
    SharedCtx, Snapshot, Timing,
};
use gob_rules::{Finding, Severity};

/// A scope over a fixed set of files with a fixed label.
struct Fixed(BTreeSet<String>);

impl ScopeView for Fixed {
    fn label(&self) -> &'static str {
        "fixed"
    }

    fn files(&self) -> &BTreeSet<String> {
        &self.0
    }
}

/// A product with nothing to check; it exists to type a shared context and a repo group.
struct Bare;

impl Product for Bare {
    type Shared = ();
    type Inputs = ();
    type Scope = Fixed;

    fn name(&self) -> &'static str {
        "bare"
    }

    fn collect(&self, _cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        Ok(Collected {
            shared: (),
            inputs: (),
            findings: Vec::new(),
        })
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        Vec::new()
    }

    fn repo_digest(&self, _snap: &Snapshot<Self>) -> Vec<u8> {
        Vec::new()
    }

    fn resolve_scope(
        &self,
        _snap: &Snapshot<Self>,
        _table: &gob_check::CheckTable,
        _reference: &str,
    ) -> Result<Fixed, CheckError> {
        Ok(Fixed(BTreeSet::new()))
    }
}

// frob:tests crates/gob-check/src/filecheck.rs::SharedCtx.digest_of
// frob:tests crates/gob-check/src/filecheck.rs::SharedCtx.has_dir
#[test]
fn the_shared_context_answers_digest_and_directory_lookups() {
    let mut index = FileIndex::default();
    index
        .digests
        .insert("src/a.txt".to_owned(), "abc123".to_owned());
    index.dirs.insert("src".to_owned());
    let ctx: SharedCtx<'_, Bare> = SharedCtx {
        root: Path::new("."),
        index: &index,
        product: &(),
    };
    assert_eq!(ctx.digest_of("src/a.txt"), Some("abc123"));
    assert_eq!(ctx.digest_of("src/missing.txt"), None);
    assert!(ctx.has_dir("src"));
    assert!(!ctx.has_dir("lib"));
}

// frob:tests crates/gob-check/src/product.rs::ScopeView.label
// frob:tests crates/gob-check/src/product.rs::ScopeView.files
// frob:tests crates/gob-check/src/product.rs::ScopeView.changes
#[test]
fn a_scope_exposes_its_label_files_and_no_changes_by_default() {
    let scope = Fixed(["a.txt".to_owned()].into());
    let view: &dyn ScopeView = &scope;
    assert_eq!(view.label(), "fixed");
    assert!(view.files().contains("a.txt"));
    assert!(view.changes().is_none());
}

// frob:tests crates/gob-check/src/product.rs::RepoGroup.full_only
// frob:tests crates/gob-check/src/product.rs::RepoGroup.counting
#[test]
fn a_repo_group_can_be_marked_full_only_and_given_a_subject_counter() {
    let group: RepoGroup<Bare> =
        RepoGroup::new("repo:bare", Vec::new(), |_: &Snapshot<Bare>, _| Vec::new())
            .counting(|_| vec![("BARE001", 3)])
            .full_only();
    assert_eq!(group.name, "repo:bare");
    assert!(group.full_only);
}

// frob:tests crates/gob-check/src/report.rs::Timing.push
#[test]
fn timing_records_stages_and_sums_only_the_budgeted_ones() {
    let mut timing = Timing::default();
    timing.push("walk", Duration::from_millis(7), true);
    timing.push("tools", Duration::from_millis(100), false);
    assert_eq!(timing.stages.len(), 2);
    assert_eq!(timing.stages[0].name, "walk");
    assert_eq!(timing.stages[1].ms, 100);
    assert_eq!(timing.budget_ms(), 7);
}

// frob:tests crates/gob-check/src/sibling.rs::fidelity_reason
#[test]
fn an_unresolved_finding_carries_the_fidelity_reason() {
    let rule = "COV001".parse().expect("valid id");
    let unresolved = Finding::new(rule, Severity::Unresolved, None, "m", "x");
    assert_eq!(fidelity_reason(&unresolved).as_deref(), Some("fidelity"));
}

// frob:tests crates/gob-check/src/sibling.rs::fidelity_reason
#[test]
fn an_error_finding_carries_no_fidelity_reason() {
    let rule = "COV001".parse().expect("valid id");
    let error = Finding::new(rule, Severity::Error, None, "m", "x");
    assert_eq!(fidelity_reason(&error), None);
}

// frob:tests crates/gob-check/src/sibling_doc.rs::schema
#[test]
fn the_sibling_schema_is_an_object_schema_with_definitions() {
    let schema = gob_check::sibling_doc::schema();
    assert_eq!(schema["title"], "SiblingOutput");
    assert_eq!(schema["type"], "object");
    assert!(schema["$defs"].is_object() || schema["definitions"].is_object());
}
