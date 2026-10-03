//! frob as a [`gob_check::Product`]: its inputs, rule groups, ticket scope and exceptions.

use std::sync::Arc;

use frob_ack::{Affect001, Drift001, Drift002, Drift003};
use frob_lease::LeaseConfig;
use frob_ledger::rules::{Tick001, Tick003};
use frob_obligations::{
    Cov001, Inv001, Inv002, Todo002, apply_exceptions, cov001_subjects, evaluate_repo,
};
use gob_check::{
    CheckError, CheckTable, CollectCx, Collected, FileCheck, Product, RepoGroup, ScopedFindings,
    Snapshot,
};
use gob_languages::Language;
use gob_rules::{Finding, Resolved, Rule, RuleMeta};
use gob_text::FileInterner;

use crate::filecheck::builtin_checks;
use crate::options::CheckOptions;
use crate::scope::{self, TicketScope};
use crate::snapshot::{self, FrobInputs, FrobShared};

/// Rules that read the ticket ledger: without one they examine nothing.
const LEDGER_RULES: [&str; 3] = ["REF001", "TODO002", "TICK002"];

/// frob driving the shared check pipeline, with the options of one `frob check` run.
pub struct Frob {
    opts: CheckOptions,
}

impl Frob {
    /// The product for a run with `opts`.
    pub fn new(opts: CheckOptions) -> Self {
        Self { opts }
    }
}

/// `TICK001` and `TICK003` from the ledger doctor (read-only); empty without a ledger.
fn ledger_findings(inputs: &FrobInputs) -> Vec<Finding> {
    let Some(state) = &inputs.ledger else {
        return Vec::new();
    };
    match state.ledger.doctor(false) {
        Ok(report) => report.findings,
        Err(err) => {
            tracing::warn!(%err, "ledger doctor failed; TICK001 and TICK003 not evaluated");
            Vec::new()
        }
    }
}

impl Product for Frob {
    type Shared = FrobShared;
    type Inputs = FrobInputs;
    type Scope = TicketScope;

    fn name(&self) -> &'static str {
        "frob"
    }

    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        snapshot::collect(cx, &self.opts)
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        let mut checks = builtin_checks();
        checks.extend(self.opts.extra_checks.iter().cloned());
        checks
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        vec![
            RepoGroup::new(
                "repo:obligations",
                vec![Cov001.meta(), Todo002.meta(), Inv001.meta(), Inv002.meta()],
                |s: &Snapshot<Self>, f| evaluate_repo(&s.inputs.obligations(), f),
            )
            .counting(|s| {
                vec![
                    ("COV001", cov001_subjects(&s.inputs.ack.graph)),
                    ("TODO002", s.inputs.ledger.as_ref().map_or(0, |l| l.tickets)),
                ]
            }),
            RepoGroup::new(
                "repo:ack",
                vec![
                    Drift001.meta(),
                    Drift002.meta(),
                    Drift003.meta(),
                    Affect001.meta(),
                ],
                |s: &Snapshot<Self>, _| frob_ack::check(&s.inputs.ack),
            ),
            RepoGroup::new(
                "repo:tests",
                vec![frob_tests::Test001.meta()],
                |s: &Snapshot<Self>, _| {
                    let read = |p: &str| std::fs::read_to_string(s.core.root.join(p)).ok();
                    frob_tests::test001_with_sources(
                        &s.inputs.directives,
                        &s.inputs.ack.graph,
                        &read,
                    )
                },
            ),
            RepoGroup::new(
                "repo:ledger",
                vec![Tick001.meta(), Tick003.meta()],
                |s: &Snapshot<Self>, _| ledger_findings(&s.inputs),
            ),
        ]
    }

    fn repo_digest(&self, snap: &Snapshot<Self>) -> Vec<u8> {
        let mut out = b"ledger\0".to_vec();
        out.extend_from_slice(snap.shared.ledger_tip.as_bytes());
        out.extend_from_slice(format!("{:?}", snap.inputs.invariants.forbid_imports).as_bytes());
        out
    }

    fn resolve_scope(
        &self,
        snap: &Snapshot<Self>,
        table: &CheckTable,
        reference: &str,
    ) -> Result<TicketScope, CheckError> {
        let lease_cfg = match &self.opts.lease {
            Some(c) => c.clone(),
            None => LeaseConfig::load(&snap.core.root)?,
        };
        scope::resolve(snap, reference, table.ticket_hops, lease_cfg)
    }

    fn scoped_rules(
        &self,
        snap: &Snapshot<Self>,
        scope: &TicketScope,
        table: &CheckTable,
    ) -> ScopedFindings {
        let base = self.opts.base.clone().unwrap_or_else(|| table.base.clone());
        let findings = scope::ticket_rules(snap, scope, &base);
        let subjects = snap
            .inputs
            .ledger
            .as_ref()
            .map(|l| ("TICK002", l.tickets))
            .into_iter()
            .collect();
        ScopedFindings { findings, subjects }
    }

    fn resolve_exceptions(
        &self,
        snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        apply_exceptions(&snap.inputs.obligations(), files, raw)
    }

    fn file_info(&self, shared: &FrobShared, path: &str) -> Option<gob_symbols::FileInfo> {
        shared.file_info.get(path).cloned()
    }

    fn scans_text(&self, path: &str) -> bool {
        Language::detect(path).is_some()
    }

    fn applicable(&self, snap: &Snapshot<Self>, meta: &RuleMeta) -> bool {
        if LEDGER_RULES.contains(&meta.id) {
            snap.shared.has_ledger || snap.inputs.tickets_configured
        } else if meta.id == "COV001" {
            // COV001 needs a language with a test capability; only Rust has one today.
            snap.core
                .entries
                .iter()
                .any(|e| Language::detect(&e.path) == Some(Language::Rust))
        } else {
            true
        }
    }
}
