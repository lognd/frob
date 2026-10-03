//! frob as a [`gob_check::Product`]: its inputs, rule groups, ticket scope and exceptions.

use std::sync::Arc;

use frob_ack::{Affect001, Drift001, Drift002, Drift003};
use frob_lease::LeaseConfig;
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::rules::{Tick001, Tick003};
use frob_obligations::{
    Cov001, Inv001, Inv002, Todo002, apply_exceptions, cov001_subjects, evaluate_repo,
};
use frob_pm::rules::membership::Pm034;
use frob_pm::rules::replenish::Pm033;
use frob_pm::rules::wip::Pm013;
use frob_release::rel001::Rel001;
use frob_release::rel002::Rel002;
use frob_release::rel003::Rel003;
use gob_check::{
    CheckError, CheckTable, CollectCx, Collected, External, FileCheck, Product, RepoGroup,
    ScopedFindings, Snapshot, Timing,
};
use gob_languages::Language;
use gob_rules::{Finding, Resolved, Rule, RuleMeta};
use gob_text::FileInterner;

use crate::filecheck::builtin_checks;
use crate::options::CheckOptions;
use crate::scope::{self, TicketScope};
use crate::sibling::Siblings;
use crate::snapshot::{self, FrobInputs, FrobShared};

/// Rules that read the ticket ledger: without one they examine nothing.
const LEDGER_RULES: [&str; 3] = ["REF001", "TODO002", "TICK002"];

/// Why `PM034` is not applicable when it is not (logged, never a finding).
const PM034_NA: &str = "no milestone objects in this repository";

/// frob driving the shared check pipeline, with the options of one `frob check` run.
pub struct Frob {
    opts: CheckOptions,
    siblings: Siblings,
}

impl Frob {
    /// The product for a run with `opts`.
    pub fn new(opts: CheckOptions) -> Self {
        Self {
            opts,
            siblings: Siblings::default(),
        }
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

/// `PM034` findings for the `repo:pm` group; empty without a ledger, milestones or on a read failure.
// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
fn pm_findings(inputs: &FrobInputs) -> Vec<Finding> {
    let Some(state) = &inputs.ledger else {
        return Vec::new();
    };
    frob_pm::rules::membership::evaluate(&state.ledger).map_or_else(
        |err| {
            tracing::warn!(%err, "PM034 not evaluated");
            Vec::new()
        },
        |e| e.findings,
    )
}

/// `PM013` findings for the `repo:wip` group; the limit is `[pm.wip] in_progress`, and the ledger index is the only input.
// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
fn wip_findings(inputs: &FrobInputs) -> Vec<Finding> {
    let Some(state) = &inputs.ledger else {
        return Vec::new();
    };
    let limit = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.wip.in_progress,
        Err(err) => {
            tracing::warn!(%err, "pm config unreadable; PM013 not evaluated");
            return Vec::new();
        }
    };
    frob_pm::rules::wip::evaluate(&state.ledger, limit).map_or_else(
        |err| {
            tracing::warn!(%err, "PM013 not evaluated");
            Vec::new()
        },
        |e| e.findings,
    )
}

/// `PM033` findings for the `repo:replenish` group; ready is `Ledger::doable` under the live lease check, as `ticket doable` computes it.
// frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS
fn replenish_findings(inputs: &FrobInputs, lease_cfg: Option<&LeaseConfig>) -> Vec<Finding> {
    let Some(state) = &inputs.ledger else {
        return Vec::new();
    };
    let ready_min = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.pm.ready_min,
        Err(err) => {
            tracing::warn!(%err, "pm config unreadable; PM033 not evaluated");
            return Vec::new();
        }
    };
    let cfg = match lease_cfg {
        Some(c) => Ok(c.clone()),
        None => LeaseConfig::load(&inputs.root),
    };
    let guard = cfg
        .map_err(|e| e.to_string())
        .and_then(|c| frob_lease::open_store(&inputs.root, c).map_err(|e| e.to_string()))
        .and_then(|(store, _)| frob_lease::LeaseGuard::new(store).map_err(|e| e.to_string()));
    let leases: Box<dyn LeaseCheck> = match guard {
        Ok(g) => Box::new(g),
        Err(msg) => {
            tracing::warn!(error = %msg, "lease check unavailable; PM033 counts every doable ticket");
            Box::new(NoLeases)
        }
    };
    frob_pm::rules::replenish::evaluate(&state.ledger, &*leases, ready_min).map_or_else(
        |err| {
            tracing::warn!(%err, "PM033 not evaluated");
            Vec::new()
        },
        |e| e.findings,
    )
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
            RepoGroup::new("repo:pm", vec![Pm034.meta()], |s: &Snapshot<Self>, _| {
                pm_findings(&s.inputs)
            }),
            // frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
            RepoGroup::new("repo:wip", vec![Pm013.meta()], |s: &Snapshot<Self>, _| {
                wip_findings(&s.inputs)
            }),
            // frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS
            RepoGroup::new("repo:replenish", vec![Pm033.meta()], {
                let lease = self.opts.lease.clone();
                move |s: &Snapshot<Self>, _| replenish_findings(&s.inputs, lease.as_ref())
            }),
            // frob:ticket 01M4069WNGJ8YR9DTTM9K9K8V5
            RepoGroup::new(
                "repo:release",
                vec![Rel002.meta()],
                |s: &Snapshot<Self>, _| frob_release::rel002::evaluate(&s.core.root).findings,
            ),
            // frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
            RepoGroup::new(
                "repo:release-tags",
                vec![Rel001.meta()],
                |s: &Snapshot<Self>, _| rel001_findings(s),
            ),
            // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
            RepoGroup::new(
                "repo:fragments",
                vec![Rel003.meta()],
                |s: &Snapshot<Self>, _| rel003_findings(s),
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
        let mut findings = scope::ticket_rules(snap, scope, &base);
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

    fn scans_text(&self, path: &str) -> bool {
        Language::detect(path).is_some()
    }

    fn applicable(&self, snap: &Snapshot<Self>, meta: &RuleMeta) -> bool {
        // frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
        if meta.id == "PM034" {
            let ok = snap
                .inputs
                .ledger
                .as_ref()
                .is_some_and(|l| l.milestones > 0);
            if !ok {
                tracing::info!(rule = meta.id, why = PM034_NA, "not applicable");
            }
            ok
        } else if meta.id == "REL001" {
            // frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
            rel001_inputs(snap).is_some_and(|(repo, cuts)| {
                let why = frob_release::rel001::not_applicable(&repo, &cuts);
                if let Some(why) = &why {
                    tracing::info!(rule = meta.id, %why, "not applicable");
                }
                why.is_none()
            })
        } else if meta.id == "REL003" {
            // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
            let why = frob_release::rel003::not_applicable(
                &snap.core.root,
                fragment_required(&snap.core.root),
            );
            if let Some(why) = &why {
                tracing::info!(rule = meta.id, %why, "not applicable");
            }
            why.is_none()
        } else if meta.id == "REF001" || meta.id == "TODO002" {
            let ok = ledger_rule_applicable(
                meta.id,
                &snap.inputs.directives,
                snap.shared.has_ledger,
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
/// Whether `[pm] done_requires` lists `changelog_fragment`; an unreadable `[pm]` table counts as required (the default), logged.
fn fragment_required(root: &std::path::Path) -> bool {
    match frob_pm::PmConfig::load(root) {
        Ok(pm) => pm
            .pm
            .done_requires
            .contains(&frob_pm::DoneRequirement::ChangelogFragment),
        Err(err) => {
            tracing::warn!(%err, "REL003: [pm] unreadable; assuming changelog_fragment is required");
            true
        }
    }
}

// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
/// `REL003` for every fragment in the repository that does not validate against the ledger.
fn rel003_findings(snap: &Snapshot<Frob>) -> Vec<Finding> {
    let Some(state) = &snap.inputs.ledger else {
        tracing::info!("REL003: no ledger; fragment ULIDs cannot be resolved");
        return Vec::new();
    };
    let resolver = |ulid: &str| -> Option<String> {
        let id: frob_ledger::TicketId = ulid.parse().ok()?;
        state.ledger.show(id).ok().map(|v| v.summary.handle)
    };
    frob_release::rel003::evaluate(&snap.core.root, &resolver).findings
}

// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
/// `REL003` for the checked ticket when it is still open, fragments are required and it has none.
fn rel003_missing(snap: &Snapshot<Frob>, scope: &TicketScope) -> Option<Finding> {
    let state = snap.inputs.ledger.as_ref()?;
    if !fragment_required(&snap.core.root) {
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

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// The repository and every recorded release cut, the two inputs of `REL001`; `None` outside a git work tree.
fn rel001_inputs(snap: &Snapshot<Frob>) -> Option<(gob_git::Repo, Vec<frob_pm::event::CutData>)> {
    let repo = match gob_git::Repo::discover(&snap.core.root) {
        Ok(r) if r.work_dir().is_some() => r,
        Ok(_) | Err(_) => {
            tracing::info!("REL001: no git work tree");
            return None;
        }
    };
    let cuts = snap
        .inputs
        .ledger
        .as_ref()
        .map(|l| recorded_cuts(&l.ledger))
        .unwrap_or_default();
    Some((repo, cuts))
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// Every `cut` event on every milestone at the ledger tip; an unreadable ledger yields none (logged).
fn recorded_cuts(ledger: &frob_ledger::Ledger) -> Vec<frob_pm::event::CutData> {
    use frob_pm::event::PmBody;
    use frob_pm::{ObjectKind, PmStore};
    let read = || -> Result<Vec<frob_pm::event::CutData>, String> {
        let Some(tip) = ledger.tip_hex().map_err(|e| e.to_string())? else {
            return Ok(Vec::new());
        };
        let store = PmStore::new(ledger);
        let mut cuts = Vec::new();
        for m in frob_pm::rules::membership::milestones(ledger).map_err(|e| e.to_string())? {
            for e in store
                .read_events_at(&tip, ObjectKind::Milestone, m.id)
                .map_err(|e| e.to_string())?
            {
                if let PmBody::Cut(d) = e.body {
                    cuts.push(d);
                }
            }
        }
        Ok(cuts)
    };
    read().unwrap_or_else(|err| {
        tracing::warn!(%err, "REL001: recorded cuts unreadable");
        Vec::new()
    })
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// `REL001` findings for the snapshot's repository.
fn rel001_findings(snap: &Snapshot<Frob>) -> Vec<Finding> {
    rel001_inputs(snap)
        .map(|(repo, cuts)| frob_release::rel001::evaluate(&repo, &cuts).findings)
        .unwrap_or_default()
}
