//! frob as a [`gob_check::Product`]: its inputs, rule groups, ticket scope and exceptions.

use std::sync::Arc;

use frob_lease::LeaseConfig;
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::legacy::{Tick007, Tick008, Tick009, Tick010};
use frob_obligations::{Cov001, Todo002, apply_exceptions, cov001_subjects, evaluate_legacy_repo};
use frob_pm::legacy::aging::{Pm008, Pm009};
use frob_pm::legacy::cycle_plan::{Pm010, Pm011, Pm012};
use frob_pm::legacy::good_first::Pm031;
use frob_pm::legacy::pm032::Pm032;
use frob_pm::legacy::story::{Pm003, Pm004, Pm005, Pm006, Pm007};
use gob_check::{
    CheckError, CheckTable, CollectCx, Collected, External, FileCheck, Product, RepoGroup, RuleSet,
    ScopedFindings, Snapshot, Timing,
};
use gob_languages::Language;
use gob_rules::{Finding, RequiredReason, Resolved, Rule, RuleMeta, Severity};
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
    /// The `--ticket` cone (scope files plus dependents), recorded by the scoped rules.
    cone: std::sync::Mutex<Option<std::collections::BTreeSet<String>>>,
}

impl Frob {
    /// The product for a run with `opts`.
    pub fn new(opts: CheckOptions) -> Self {
        Self {
            opts,
            siblings: Siblings::default(),
            diff: std::sync::Mutex::new(None),
            cone: std::sync::Mutex::new(None),
        }
    }

    // frob:ticket 01M4GRV9YMN2VEPCTMMD5ZJPVH
    /// The affected cone of the last `--ticket` run: the ticket's files plus their dependents, unresolved calls included; `None` outside `--ticket`.
    pub fn cone_paths(&self) -> Option<std::collections::BTreeSet<String>> {
        self.cone
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
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

/// A rule producer that could not evaluate: the rules it covers and why.
///
/// The only way an evaluation error leaves a producer; [`settle`] is the only
/// consumer and renders it as required Unresolved findings, so an error can
/// never be rendered as zero findings (unknown is never a pass).
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
struct EvalFailure {
    /// Ids of the rules that were not evaluated.
    rules: &'static [&'static str],
    /// The underlying error, as text.
    error: String,
}

/// The outcome of one rule producer: its findings, or the typed failure to produce them.
type Evaluated = Result<Vec<Finding>, EvalFailure>;

/// Record that `rules` were not evaluated because of `err` (logged at warn).
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn failed(rules: &'static [&'static str], err: impl std::fmt::Display) -> EvalFailure {
    let error = err.to_string();
    tracing::warn!(rules = ?rules, %error, "rules not evaluated; reporting required Unresolved");
    EvalFailure { rules, error }
}

/// The single place a producer outcome becomes findings: each failure is one required Unresolved per affected rule.
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn settle(parts: impl IntoIterator<Item = Evaluated>) -> Vec<Finding> {
    let mut out = Vec::new();
    for part in parts {
        match part {
            Ok(found) => out.extend(found),
            Err(EvalFailure { rules, error }) => {
                for rule in rules {
                    let id = rule
                        .parse()
                        .unwrap_or_else(|e| unreachable!("rule id literal {rule}: {e}"));
                    out.push(
                        Finding::new(
                            id,
                            Severity::Unresolved,
                            None,
                            format!("evaluation-failed: {rule} was not evaluated: {error}"),
                            "repository",
                        )
                        .with_required(RequiredReason::EvaluationFailed {
                            rule: (*rule).to_owned(),
                            error: error.clone(),
                        }),
                    );
                }
            }
        }
    }
    out
}

/// The ledger of `inputs`, or the failure when it exists but could not be read (`rules` are then not evaluated); `Ok(None)` when there is none.
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn ledger_of<'a>(
    inputs: &'a FrobInputs,
    rules: &'static [&'static str],
) -> Result<Option<&'a snapshot::LedgerState>, EvalFailure> {
    match &inputs.ledger_error {
        Some(err) => Err(failed(rules, format_args!("ledger unreadable: {err}"))),
        None => Ok(inputs.ledger.as_ref()),
    }
}

/// The metas of the `TICK` rules that `ledger_findings` evaluates.
// frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD
fn ledger_rule_metas() -> Vec<&'static gob_rules::RuleMeta> {
    vec![
        Tick007.meta(),
        Tick008.meta(),
        Tick009.meta(),
        Tick010.meta(),
        frob_obligations::Tick006.meta(),
    ]
}

/// `TICK006` to `TICK010` from the ledger's replay, move, misfile and hand-written scans (read-only); empty without a ledger.
// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
fn ledger_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["TICK006", "TICK007", "TICK008", "TICK009", "TICK010"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([
        // frob:ticket 01M3ZX86R5V67MT726K3X7KVWM
        state
            .ledger
            .reindex_replay_findings()
            .map_err(|e| failed(&["TICK007"], e)),
        // frob:ticket 01M3ZX86W1P62F80ZNR17Q0SQ9
        state
            .ledger
            .move_outside_reindex_findings()
            .map_err(|e| failed(&["TICK008"], e)),
        // frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD
        state
            .ledger
            .misfiled_ticket_findings()
            .map_err(|e| failed(&["TICK009"], e)),
        // frob:ticket 01M4052VK08NTRJS6HZZ9B82RZ
        tick010_findings(&inputs.root, &state.ledger),
        // frob:ticket 01M4P8M16T2T3Y311ER1Z77KSE
        tick006_ledger_findings(&state.ledger),
    ])
}

/// `TICK010` over the ticket branch tip; the expected nudge is for the configured branch and the numeric `[mirror] bot_ids`.
// frob:ticket 01M5B0BWX6BERAV0RJGKV4Z6KW
fn tick010_findings(root: &std::path::Path, ledger: &frob_ledger::Ledger) -> Evaluated {
    let configured = gob_config::ConfigDocument::read(root, snapshot::PRODUCT)
        .and_then(|doc| doc.table::<gob_config::MirrorTable>())
        .map_err(|e| {
            failed(
                &["TICK010"],
                format_args!("[mirror] config unreadable: {e}"),
            )
        })?
        .value
        .bot_ids;
    let spec = frob_ledger::nudge::NudgeSpec {
        ticket_branch: ledger.config().branch.clone(),
        bot_ids: numeric_bot_ids(&configured),
    };
    ledger
        .github_tree_findings(&spec)
        .map_err(|e| failed(&["TICK010"], e))
}

/// The entries of `[mirror] bot_ids` that are GitHub user ids; logins cannot be matched against `github.actor_id` and are skipped, logged.
// frob:ticket 01M5B0BWX6BERAV0RJGKV4Z6KW
fn numeric_bot_ids(configured: &[String]) -> Vec<u64> {
    configured
        .iter()
        .filter_map(|entry| {
            let id = entry.trim().parse::<u64>().ok();
            if id.is_none() {
                tracing::warn!(entry = %entry, "[mirror] bot_ids entry is not a numeric user id; left out of the nudge workflow");
            }
            id
        })
        .collect()
}

/// `TICK006` over the hand-written files of a ticket-branch ledger (bodies, `EPIC.md`).
// frob:ticket 01M4P8M16T2T3Y311ER1Z77KSE
fn tick006_ledger_findings(ledger: &frob_ledger::Ledger) -> Evaluated {
    let texts = ledger
        .hand_written_texts()
        .map_err(|e| failed(&["TICK006"], e))?;
    Ok(texts
        .iter()
        .flat_map(|(path, text)| frob_obligations::tick006_ledger_file(path, text, ledger))
        .collect())
}

/// Apply `[pm] strict` to a PM group's `findings`; an unreadable `[pm]` table means not strict, logged.
// frob:ticket 01M41B2PD4NAV8VACA13750GWB
fn strict_pm(inputs: &FrobInputs, findings: Vec<Finding>) -> Vec<Finding> {
    if findings.is_empty() {
        return findings;
    }
    let strict = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.pm.strict,
        Err(err) => {
            tracing::warn!(%err, "pm config unreadable; [pm] strict not applied");
            false
        }
    };
    frob_pm::eval::apply_strict(strict, findings)
}

/// `PM008` and `PM009` findings for the `repo:aging` group; limits from `[pm.max_age_days]`, age measured at the ledger clock's now.
// frob:ticket 01M4CT0AF76FJTWFG10SKXJZAZ
fn aging_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM008", "PM009"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    let limits = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.max_age_days,
        Err(e) => {
            return settle([Err(failed(ALL, format_args!("pm config unreadable: {e}")))]);
        }
    };
    settle([
        frob_pm::legacy::aging::evaluate(&state.ledger, &limits, state.ledger.clock().now())
            .map(|e| e.findings)
            .map_err(|e| failed(ALL, e)),
    ])
}

/// `PM010`-`PM012` findings for the `repo:cycle-plan` group; empty without a ledger or cycles, `[pm]` knobs from `frob.toml`.
// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ
fn cycle_plan_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM010", "PM011", "PM012"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    let pm = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.pm,
        Err(e) => {
            return settle([Err(failed(ALL, format_args!("pm config unreadable: {e}")))]);
        }
    };
    settle([frob_pm::legacy::cycle_plan::evaluate(&state.ledger, &pm)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
}

/// `PM031` findings for the `repo:good-first` group; empty without a ledger, limit from `[tickets] good_first_max_points`.
// frob:ticket 01M3ZX87KRP6G49GHANMAK5JA8
fn good_first_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM031"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    let max = frob_pm::legacy::good_first::max_points(&inputs.root);
    settle([frob_pm::legacy::good_first::evaluate(&state.ledger, max)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
}

/// `PM003`-`PM007` findings for the `repo:story` group; empty without a ledger, the size limit from `[pm] max_story_points`.
// frob:ticket 01M4CT054RN6SY75KRYSY14778
fn story_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM003", "PM004", "PM005", "PM006", "PM007"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    let max = match frob_pm::PmConfig::load(&inputs.root) {
        Ok(cfg) => cfg.pm.max_story_points,
        Err(e) => {
            return settle([Err(failed(ALL, format_args!("pm config unreadable: {e}")))]);
        }
    };
    settle([frob_pm::legacy::story::evaluate(&state.ledger, max)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
}

/// `PM032` findings for the `repo:good-first-pool` group; the ready pool is `Ledger::doable` under the live lease check, the minimum `[tickets] good_first_min`.
// frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ
fn good_first_pool_findings(inputs: &FrobInputs, lease_cfg: Option<&LeaseConfig>) -> Vec<Finding> {
    const ALL: &[&str] = &["PM032"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    let min = frob_pm::legacy::pm032::min_ready(&inputs.root);
    let leases = lease_check(inputs, state, lease_cfg, "PM032");
    settle([
        frob_pm::legacy::pm032::evaluate(&state.ledger, &*leases, min)
            .map(|e| e.findings)
            .map_err(|e| failed(ALL, e)),
    ])
}

/// The live lease check for `state`, or one that frees everything (logged) when the lease store cannot be opened.
// frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ
fn lease_check(
    inputs: &FrobInputs,
    state: &snapshot::LedgerState,
    lease_cfg: Option<&LeaseConfig>,
    rule: &str,
) -> Box<dyn LeaseCheck> {
    let cfg = match lease_cfg {
        Some(c) => Ok(c.clone()),
        None => LeaseConfig::load(&inputs.root),
    };
    let guard = cfg
        .map_err(|e| e.to_string())
        .and_then(|c| {
            frob_lease::open_store(&inputs.root, c, state.ledger.clock().clone())
                .map_err(|e| e.to_string())
        })
        .and_then(|(store, _)| frob_lease::LeaseGuard::new(store).map_err(|e| e.to_string()));
    match guard {
        Ok(g) => Box::new(g),
        Err(msg) => {
            tracing::warn!(error = %msg, "lease check unavailable; {rule} counts every doable ticket");
            Box::new(NoLeases)
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

    // frob:ticket 01M4FH7QN0DHJD45C4HC8N7M9Q
    fn defers_unknown_only(&self) -> bool {
        true
    }

    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        snapshot::collect(cx, &self.opts)
    }

    fn rule_set(&self) -> RuleSet<Self> {
        RuleSet::new().bind(product_rules::rules(), host)
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        let mut checks = builtin_checks();
        checks.extend(self.opts.extra_checks.iter().cloned());
        checks
    }

    #[allow(clippy::too_many_lines)] // one declarative table of repo groups
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
            // frob:ticket 01M4CT0AF76FJTWFG10SKXJZAZ
            RepoGroup::new(
                "repo:aging",
                vec![Pm008.meta(), Pm009.meta()],
                |s: &Snapshot<Self>, _| strict_pm(&s.inputs, aging_findings(&s.inputs)),
            )
            .full_only(),
            // frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ
            RepoGroup::new(
                "repo:cycle-plan",
                vec![Pm010.meta(), Pm011.meta(), Pm012.meta()],
                |s: &Snapshot<Self>, _| strict_pm(&s.inputs, cycle_plan_findings(&s.inputs)),
            )
            .full_only(),
            // frob:ticket 01M4CT054RN6SY75KRYSY14778
            RepoGroup::new(
                "repo:story",
                vec![
                    Pm003.meta(),
                    Pm004.meta(),
                    Pm005.meta(),
                    Pm006.meta(),
                    Pm007.meta(),
                ],
                |s: &Snapshot<Self>, _| strict_pm(&s.inputs, story_findings(&s.inputs)),
            )
            .full_only(),
            // frob:ticket 01M3ZX87KRP6G49GHANMAK5JA8
            RepoGroup::new(
                "repo:good-first",
                vec![Pm031.meta()],
                |s: &Snapshot<Self>, _| good_first_findings(&s.inputs),
            )
            .full_only(),
            // frob:ticket 01M3ZX87ZJR4YVZZ4AS7VSR4BQ
            RepoGroup::new("repo:good-first-pool", vec![Pm032.meta()], {
                let lease = self.opts.lease.clone();
                move |s: &Snapshot<Self>, _| good_first_pool_findings(&s.inputs, lease.as_ref())
            })
            .full_only(),
            // frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY
            RepoGroup::new(
                "repo:grl",
                vec![crate::grl::Grl016.meta()],
                |s: &Snapshot<Self>, files| crate::grl::findings(s, files),
            )
            .counting(|s| vec![("GRL016", crate::grl::example_count(s))]),
            RepoGroup::new(
                "repo:ledger",
                ledger_rule_metas(),
                |s: &Snapshot<Self>, _| ledger_findings(&s.inputs),
            ),
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
        if reference == scope::DIFF_SCOPE_REF {
            let base = self.opts.diff_base.as_deref().unwrap_or(&table.base);
            let cfg = snap
                .inputs
                .ledger
                .as_ref()
                .map(|l| l.ledger.config().clone())
                .or_else(|| self.opts.ledger.clone())
                .unwrap_or_default();
            return scope::resolve_diff(snap, table.ticket_hops, base, &cfg);
        }
        scope::resolve(snap, reference, table.ticket_hops, &table.base, lease_cfg)
    }

    fn scoped_rules(
        &self,
        snap: &Snapshot<Self>,
        scope: &TicketScope,
        table: &CheckTable,
    ) -> ScopedFindings {
        let base = self.opts.base.clone().unwrap_or_else(|| table.base.clone());
        let mut diff = None;
        *self
            .cone
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = Some(scope.files.clone());
        if scope.lease.is_none() {
            tracing::debug!(label = %scope.handle, "diff-base scope: ticket rules skipped");
            *self
                .diff
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) =
                scope.changes.as_ref().map(|c| c.files.clone());
            return ScopedFindings::default();
        }
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
        self.siblings.start(
            &snap.core.root,
            table,
            &base,
            scope_files,
            &snap.core.index.digests,
            &self.opts,
        );
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

    // frob:ticket 01M5GCNBD6AT6HNQKF3MQTXQC5
    fn malformed_projects(&self, shared: &FrobShared) -> Vec<gob_symbols::MalformedProject> {
        shared.malformed_projects.clone()
    }

    fn scans_text(&self, path: &str) -> bool {
        Language::detect(path).is_some()
    }

    fn owns_file(&self, path: &str) -> bool {
        is_frob_owned(path)
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

/// True for the files `frob init` and the ledger write: config, git attributes and ignore, tickets, fragments.
fn is_frob_owned(path: &str) -> bool {
    matches!(path, "frob.toml" | ".gitattributes" | ".gitignore")
        || path.starts_with("tickets/")
        || path.starts_with("changelog.d/")
}

#[cfg(test)]
mod mirror_bot_id_tests {
    use super::numeric_bot_ids;

    // frob:tests crates/frob-check/src/product.rs::numeric_bot_ids
    #[test]
    fn numeric_bot_ids_keeps_user_ids_and_skips_logins() {
        let configured = ["42".to_owned(), "some-bot".to_owned(), " 7 ".to_owned()];
        assert_eq!(numeric_bot_ids(&configured), [42, 7]);
        assert!(numeric_bot_ids(&[]).is_empty());
    }
}

#[cfg(test)]
mod malformed_projects_tests {
    use super::*;

    // frob:tests crates/frob-check/src/product.rs::malformed_projects
    #[test]
    fn frob_product_returns_shared_malformed_projects() {
        let shared = FrobShared {
            ledger_tip: String::new(),
            ref_unsettled: std::collections::BTreeMap::default(),
            obligation_paths: std::collections::BTreeSet::default(),
            has_ledger: false,
            file_info: std::collections::BTreeMap::default(),
            unreadable: Vec::new(),
            malformed_projects: vec![gob_symbols::MalformedProject {
                path: "a/b.csproj".to_owned(),
                reason: "bad xml".to_owned(),
            }],
            roles: gob_walk::Roles::new("tickets"),
        };
        let frob = Frob::new(CheckOptions::default());
        let got = frob.malformed_projects(&shared);
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].path, "a/b.csproj");
    }
}
