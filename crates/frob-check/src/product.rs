//! frob as a [`gob_check::Product`]: its inputs, rule groups, ticket scope and exceptions.

use std::sync::Arc;

use frob_lease::LeaseConfig;
use frob_obligations::{Cov001, Todo002, apply_exceptions, cov001_subjects, evaluate_legacy_repo};
use gob_check::{
    CheckError, CheckTable, CollectCx, Collected, External, FileCheck, Product, RepoGroup, RuleSet,
    ScopedFindings, Snapshot, Timing,
};
use gob_languages::Language;
use gob_rules::{Finding, Resolved, Rule, RuleDef, RuleMeta};
use gob_text::FileInterner;

use crate::filecheck::builtin_checks;
use crate::host::FrobHost;
use crate::options::CheckOptions;
use crate::product_rules;
use crate::scope::{self, TicketScope};
use crate::sibling::Siblings;
use crate::snapshot::{self, FrobInputs, FrobShared};

/// The host the declared rules judge: the snapshot's inputs.
fn host<'a>(_: &'a Frob, snap: &'a Snapshot<Frob>) -> &'a (dyn FrobHost + 'static) {
    &snap.inputs
}

/// Rules that read the ticket ledger and stay on the legacy path: without one they examine nothing.
const LEDGER_RULES: [&str; 2] = ["REF001", "TODO002"];

/// frob driving the shared check pipeline, with the options of one `frob check` run.
pub struct Frob {
    opts: CheckOptions,
    siblings: Siblings,
    /// Paths of the `--ticket` branch diff, recorded by the scoped rules for the text view.
    diff: std::sync::Mutex<Option<std::collections::BTreeSet<String>>>,
}

impl Frob {
    /// The product for a run with `opts`.
    pub fn new(opts: CheckOptions) -> Self {
        Self {
            opts,
            siblings: Siblings::default(),
            diff: std::sync::Mutex::new(None),
        }
    }

    // frob:ticket 01M413V8CDKKBSBV8JDV92VDGB
    /// The paths of the `--ticket` branch diff of the last run; `None` outside `--ticket` or when the diff failed.
    pub fn diff_paths(&self) -> Option<std::collections::BTreeSet<String>> {
        self.diff
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
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

    fn rule_set(&self) -> RuleSet<Self> {
        // frob:ticket 01M55ZW4P41ES0N6HBZ9TQ01YC
        // The gob_check and gob_directives rules are computed by the pipeline's own stages, so they
        // are declared (staged) rather than run: a bound empty body would double their findings.
        let staged: Vec<&'static RuleDef> = gob_check::rules::METAS
            .iter()
            .chain(gob_directives::rules::METAS)
            .copied()
            .collect();
        let bound: Vec<_> = product_rules::rules()
            .into_iter()
            .filter(|r| staged.iter().all(|d| d.id != r.def.id))
            .collect();
        staged
            .into_iter()
            .fold(RuleSet::new().bind(bound, host), RuleSet::stage)
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        let mut checks = builtin_checks();
        checks.extend(self.opts.extra_checks.iter().cloned());
        checks
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        vec![
            // COV001 and TODO002 stay on the legacy derive: `Out` cannot carry their span ranges.
            // frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3
            RepoGroup::new(
                "repo:obligations",
                vec![Cov001.meta(), Todo002.meta()],
                |s: &Snapshot<Self>, f| evaluate_legacy_repo(&s.inputs.obligations(), f),
            )
            .counting(|s| {
                vec![
                    ("COV001", cov001_subjects(&s.inputs.ack.graph)),
                    ("TODO002", s.inputs.ledger.as_ref().map_or(0, |l| l.tickets)),
                ]
            }),
        ]
    }

    fn repo_digest(&self, snap: &Snapshot<Self>) -> Vec<u8> {
        let mut out = b"ledger\0".to_vec();
        out.extend_from_slice(snap.shared.ledger_tip.as_bytes());
        // Local private rules decide TICK005; a changed rule set must not replay a cached result.
        if let Some(rules) = snap
            .inputs
            .ledger
            .as_ref()
            .and_then(|l| l.ledger.redaction().ok())
        {
            out.extend_from_slice(rules.fingerprint().as_bytes());
        }
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
        let mut diff = None;
        let mut findings = scope::ticket_rules(snap, scope, &base, &mut diff);
        *self
            .diff
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = diff;
        findings.extend(rel003_missing(snap, scope));
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

    fn start_external(
        &self,
        snap: &Snapshot<Self>,
        table: &CheckTable,
        scope_files: Option<&std::collections::BTreeSet<String>>,
    ) {
        let base = self.opts.base.clone().unwrap_or_else(|| table.base.clone());
        self.siblings
            .start(&snap.core.root, table, &base, scope_files, &self.opts);
    }

    fn join_external(
        &self,
        snap: &Snapshot<Self>,
        files: &mut FileInterner,
        timing: &mut Timing,
    ) -> External {
        let ledger = snap.inputs.ledger.as_ref().map(|l| &l.ledger);
        self.siblings.join(&snap.core.root, ledger, files, timing)
    }

    fn file_info(&self, shared: &FrobShared, path: &str) -> Option<gob_symbols::FileInfo> {
        shared.file_info.get(path).cloned()
    }

    // frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
    fn unreadable(&self, shared: &FrobShared) -> Vec<gob_symbols::SkippedFile> {
        shared.unreadable.clone()
    }

    fn scans_text(&self, path: &str) -> bool {
        Language::detect(path).is_some()
    }

    fn applicable(&self, snap: &Snapshot<Self>, meta: &RuleMeta) -> bool {
        if snap.inputs.ledger_missing.is_some() && LEDGER_RULES.contains(&meta.id) {
            // frob:ticket 01M44VQ57WQW4G5JTZDDYEVJPW
            // The absent ledger is reported once by the ledger group, not as zero-subject verdicts.
            tracing::info!(rule = meta.id, "not applicable: ledger ref is absent");
            false
        } else if meta.id == "REF001" || meta.id == "TODO002" {
            let ok = ledger_rule_applicable(
                meta.id,
                &snap.inputs.directives,
                snap.shared.has_ledger || snap.inputs.ledger_error.is_some(),
                snap.inputs.tickets_configured,
            );
            if !ok {
                tracing::info!(
                    rule = meta.id,
                    "not applicable: nothing to resolve against a ledger"
                );
            }
            ok
        } else if LEDGER_RULES.contains(&meta.id) {
            snap.shared.has_ledger
                || snap.inputs.ledger_error.is_some()
                || snap.inputs.tickets_configured
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

/// Whether `REF001` or `TODO002` has anything to decide, from facts known before evaluation.
///
/// `REF001` judges `frob:ticket` references and `TODO002` judges `frob:todo` directives against the ledger, so each applies when the repository holds at least one such directive; `REF001` also applies when a ledger with tickets is open (every file is then a subject). With no such directive and no ledger there is nothing to resolve, so the rule is not applicable instead of a required silent zero; a configured-but-missing ledger with directives present stays a required Unresolved.
// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5
pub(crate) fn ledger_rule_applicable(
    rule: &str,
    directives: &[gob_directives::DirectiveRecord],
    has_ledger: bool,
    tickets_configured: bool,
) -> bool {
    let verb = if rule == "REF001" { "ticket" } else { "todo" };
    let referenced = directives
        .iter()
        .any(|d| d.namespace == "frob" && d.verb == verb);
    (tickets_configured || has_ledger) && (referenced || (rule == "REF001" && has_ledger))
}

// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
/// `REL003` for the checked ticket when it is still open, fragments are required and it has none.
fn rel003_missing(snap: &Snapshot<Frob>, scope: &TicketScope) -> Option<Finding> {
    let state = snap.inputs.ledger.as_ref()?;
    if !frob_release::rel003::fragment_required(&snap.core.root) {
        tracing::debug!("REL003: changelog_fragment not required; no per-ticket check");
        return None;
    }
    let id = state.ledger.resolve(&scope.handle).ok()?;
    let view = state.ledger.show(id).ok()?;
    if view.summary.category == frob_ledger::model::Category::Done {
        tracing::debug!(handle = %scope.handle, "REL003: ticket already done");
        return None;
    }
    if snap.inputs.changelog_exempt {
        tracing::info!(handle = %scope.handle, "REL003: exempt by the caller (--no-changelog)");
        return None;
    }
    let exempt = state
        .ledger
        .events(id)
        .ok()
        .and_then(|e| frob_ledger::event::changelog_exemption(&e));
    if let Some(x) = exempt {
        tracing::info!(handle = %scope.handle, actor = %x.actor, reason = %x.reason, "REL003: ticket is changelog-exempt");
        return None;
    }
    frob_release::rel003::missing(&snap.core.root, &id.to_string(), &scope.handle)
}
