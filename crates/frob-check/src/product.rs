//! frob as a [`gob_check::Product`]: its inputs, rule groups, ticket scope and exceptions.

use std::collections::BTreeSet;
use std::sync::Arc;

use frob_ack::{Affect001, Drift001, Drift002, Drift003};
use frob_lease::{LeaseConfig, LeaseStore};
use frob_ledger::TicketId;
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::rules::{Tick001, Tick003, Tick004, Tick005, Tick007, Tick008, Tick009};
use frob_obligations::{
    Cov001, Inv001, Inv002, Todo002, apply_exceptions, cov001_subjects, evaluate_repo,
};
use frob_pm::rules::aging::{Pm008, Pm009};
use frob_pm::rules::cycle::Pm036;
use frob_pm::rules::cycle_plan::{Pm010, Pm011, Pm012};
use frob_pm::rules::good_first::Pm031;
use frob_pm::rules::membership::Pm034;
use frob_pm::rules::milestone::{Pm001, Pm002};
use frob_pm::rules::pm032::Pm032;
use frob_pm::rules::replenish::Pm033;
use frob_pm::rules::story::{Pm003, Pm004, Pm005, Pm006, Pm007};
use frob_pm::rules::wip::Pm013;
use frob_release::rel001::Rel001;
use frob_release::rel002::Rel002;
use frob_release::rel003::Rel003;
use gob_check::{
    CheckError, CheckTable, CollectCx, Collected, External, FileCheck, Product, RepoGroup,
    ScopedFindings, Snapshot, Timing,
};
use gob_languages::Language;
use gob_rules::{Finding, RequiredReason, Resolved, Rule, RuleMeta, Severity};
use gob_text::FileInterner;

use crate::filecheck::builtin_checks;
use crate::options::CheckOptions;
use crate::scope::{self, TicketScope};
use crate::sibling::Siblings;
use crate::snapshot::{self, FrobInputs, FrobShared};

/// Rules that read the ticket ledger: without one they examine nothing.
const LEDGER_RULES: [&str; 3] = ["REF001", "TODO002", "TICK002"];

/// Why `PM034`, `PM001` and `PM002` are not applicable when it is not (logged, never a finding).
const PM034_NA: &str = "no milestone objects in this repository";

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
        Tick001.meta(),
        Tick003.meta(),
        Tick004.meta(),
        Tick005.meta(),
        Tick007.meta(),
        Tick008.meta(),
        Tick009.meta(),
        frob_obligations::Tick006.meta(),
    ]
}

/// `TICK001` and `TICK003` from the ledger doctor and `TICK004` from the home-path scan (read-only); empty without a ledger.
// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
fn ledger_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &[
        "TICK001", "TICK003", "TICK004", "TICK005", "TICK007", "TICK008",
    ];
    // frob:ticket 01M44VQ57WQW4G5JTZDDYEVJPW
    if let Some(why) = &inputs.ledger_missing {
        // One finding for the whole absent ledger, carried by the ledger doctor's first rule.
        return settle([Err(failed(&ALL[..1], why))]);
    }
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([
        state
            .ledger
            .doctor(false)
            .map(|r| r.findings)
            .map_err(|e| failed(&["TICK001", "TICK003"], e)),
        state
            .ledger
            .home_path_findings()
            .map_err(|e| failed(&["TICK004"], e)),
        private_term_findings(inputs, state),
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
        // frob:ticket 01M4P8M16T2T3Y311ER1Z77KSE
        tick006_ledger_findings(&state.ledger),
    ])
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

// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
/// `TICK005` for ledger files and changelog fragments holding a local private term; local-only, so none without local rules.
fn private_term_findings(inputs: &FrobInputs, state: &snapshot::LedgerState) -> Evaluated {
    let mut out = state
        .ledger
        .private_term_findings()
        .map_err(|e| failed(&["TICK005"], e))?;
    if let Ok(rules) = state.ledger.redaction() {
        out.extend(frob_ledger::redact::fragment_findings(
            &inputs.root,
            "changelog.d",
            rules,
        ));
    }
    Ok(out)
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
    frob_pm::rules::apply_strict(strict, findings)
}

/// `PM034`, `PM001` and `PM002` findings for the `repo:pm` group; empty without a ledger or milestones.
// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
fn pm_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM034", "PM001", "PM002"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([
        frob_pm::rules::membership::evaluate(&state.ledger)
            .map(|e| e.findings)
            .map_err(|e| failed(&["PM034"], e)),
        frob_pm::rules::milestone::evaluate(&state.ledger)
            .map(|e| e.findings)
            .map_err(|e| failed(&["PM001", "PM002"], e)),
    ])
}

/// `PM036` findings for the `repo:cycle` group; empty without a ledger or cycles.
// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
fn cycle_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM036"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([frob_pm::rules::cycle::evaluate(&state.ledger)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
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
        frob_pm::rules::aging::evaluate(&state.ledger, &limits, state.ledger.clock().now())
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
    settle([frob_pm::rules::cycle_plan::evaluate(&state.ledger, &pm)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
}

/// Ticket ids holding a live lease, the liveness input of `PM013`; `None` (every in-progress ticket counts) when the lease store cannot be read.
// frob:ticket 01M416Z11V5GR012FR47HWFTBP
fn live_leases(
    state: &snapshot::LedgerState,
    root: &std::path::Path,
) -> Option<BTreeSet<TicketId>> {
    let cfg = LeaseConfig::load(root).unwrap_or_else(|err| {
        tracing::warn!(%err, "lease config unreadable; default used for PM013 liveness");
        LeaseConfig::default()
    });
    match LeaseStore::open(state.ledger.repo(), cfg, state.ledger.clock().clone())
        .and_then(|s| s.live_snapshot())
    {
        Ok(live) => Some(
            live.into_iter()
                .filter(|l| !l.queued)
                .map(|l| l.ticket)
                .collect(),
        ),
        Err(err) => {
            tracing::warn!(%err, "leases unreadable; PM013 counts every in-progress ticket");
            None
        }
    }
}

/// `PM013` findings for the `repo:wip` group; limits are `[pm.wip] in_progress` and `[pm.classes] expedite_max`, counted with the same lease-aware rule as the `work` gate.
// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
// frob:ticket 01M416Z11V5GR012FR47HWFTBP
fn wip_findings(inputs: &FrobInputs) -> Vec<Finding> {
    const ALL: &[&str] = &["PM013"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([wip_evaluated(inputs, state)])
}

/// `PM013` for `state`, or the failure when `[pm]` or the ledger cannot be read.
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn wip_evaluated(inputs: &FrobInputs, state: &snapshot::LedgerState) -> Evaluated {
    let cfg = frob_pm::PmConfig::load(&inputs.root)
        .map_err(|e| failed(&["PM013"], format_args!("pm config unreadable: {e}")))?;
    let limits = frob_pm::rules::wip::WipLimits {
        in_progress: cfg.wip.in_progress,
        expedite_max: cfg.classes.expedite_max,
    };
    let live = live_leases(state, &inputs.root);
    frob_pm::rules::wip::evaluate_with(&state.ledger, limits, live.as_ref())
        .map(|e| e.findings)
        .map_err(|e| failed(&["PM013"], e))
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
    let max = frob_pm::rules::good_first::max_points(&inputs.root);
    settle([frob_pm::rules::good_first::evaluate(&state.ledger, max)
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
    settle([frob_pm::rules::story::evaluate(&state.ledger, max)
        .map(|e| e.findings)
        .map_err(|e| failed(ALL, e))])
}

/// `PM033` findings for the `repo:replenish` group; ready is `Ledger::doable` under the live lease check, as `ticket doable` computes it.
// frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS
fn replenish_findings(inputs: &FrobInputs, lease_cfg: Option<&LeaseConfig>) -> Vec<Finding> {
    const ALL: &[&str] = &["PM033"];
    let state = match ledger_of(inputs, ALL) {
        Ok(Some(state)) => state,
        Ok(None) => return Vec::new(),
        Err(e) => return settle([Err(e)]),
    };
    settle([replenish_evaluated(inputs, state, lease_cfg)])
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
    let min = frob_pm::rules::pm032::min_ready(&inputs.root);
    let leases = lease_check(inputs, state, lease_cfg, "PM032");
    settle([
        frob_pm::rules::pm032::evaluate(&state.ledger, &*leases, min)
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

/// `PM033` for `state`, or the failure when `[pm]` or the ledger cannot be read.
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn replenish_evaluated(
    inputs: &FrobInputs,
    state: &snapshot::LedgerState,
    lease_cfg: Option<&LeaseConfig>,
) -> Evaluated {
    let ready_min = frob_pm::PmConfig::load(&inputs.root)
        .map_err(|e| failed(&["PM033"], format_args!("pm config unreadable: {e}")))?
        .pm
        .ready_min;
    let leases = lease_check(inputs, state, lease_cfg, "PM033");
    frob_pm::rules::replenish::evaluate(&state.ledger, &*leases, ready_min)
        .map(|e| e.findings)
        .map_err(|e| failed(&["PM033"], e))
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

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        let mut checks = builtin_checks();
        checks.extend(self.opts.extra_checks.iter().cloned());
        checks
    }

    #[allow(clippy::too_many_lines)] // one declarative table of repo groups
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
                    let read = |p: &str| s.core.text(p).ok();
                    frob_tests::test001_with_sources(
                        &s.inputs.directives,
                        &s.inputs.ack.graph,
                        &read,
                    )
                },
            ),
            // frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
            // frob:ticket 01M4HAJZA6JTNSSGJYV040TA9M
            RepoGroup::new(
                "repo:pm",
                vec![Pm034.meta(), Pm001.meta(), Pm002.meta()],
                |s: &Snapshot<Self>, _| strict_pm(&s.inputs, pm_findings(&s.inputs)),
            )
            .full_only(),
            // frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
            RepoGroup::new("repo:wip", vec![Pm013.meta()], |s: &Snapshot<Self>, _| {
                strict_pm(&s.inputs, wip_findings(&s.inputs))
            })
            .full_only(),
            // frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
            RepoGroup::new("repo:cycle", vec![Pm036.meta()], |s: &Snapshot<Self>, _| {
                strict_pm(&s.inputs, cycle_findings(&s.inputs))
            })
            .full_only(),
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
            // frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS
            RepoGroup::new("repo:replenish", vec![Pm033.meta()], {
                let lease = self.opts.lease.clone();
                move |s: &Snapshot<Self>, _| {
                    strict_pm(&s.inputs, replenish_findings(&s.inputs, lease.as_ref()))
                }
            })
            .full_only(),
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

    fn scans_text(&self, path: &str) -> bool {
        Language::detect(path).is_some()
    }

    fn applicable(&self, snap: &Snapshot<Self>, meta: &RuleMeta) -> bool {
        // frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
        if matches!(meta.id, "PM034" | "PM001" | "PM002") {
            // An unreadable ledger is applicable: its failure must surface, not hide as "not applicable".
            let ok = snap.inputs.ledger_error.is_some()
                || snap
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
            rel001_repo(snap).is_some_and(|repo| {
                let cuts = match ledger_of(&snap.inputs, &["REL001"]) {
                    Ok(None) => Ok(Vec::new()),
                    Ok(Some(state)) => recorded_cuts(&state.ledger),
                    Err(e) => Err(e.error),
                };
                // A failed cut read is applicable so REL001 reports it.
                let Ok(cuts) = cuts else { return true };
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
        } else if snap.inputs.ledger_missing.is_some() && LEDGER_RULES.contains(&meta.id) {
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
/// The git repository of the snapshot, the input of `REL001`; `None` outside a git work tree.
fn rel001_repo(snap: &Snapshot<Frob>) -> Option<gob_git::Repo> {
    let repo = match gob_git::Repo::discover(&snap.core.root) {
        Ok(r) if r.work_dir().is_some() => r,
        Ok(_) | Err(_) => {
            tracing::info!("REL001: no git work tree");
            return None;
        }
    };
    Some(repo)
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
/// Every `cut` event on every milestone at the ledger tip; an unreadable ledger is an error, never "no cuts".
// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn recorded_cuts(ledger: &frob_ledger::Ledger) -> Result<Vec<frob_pm::event::CutData>, String> {
    use frob_pm::event::PmBody;
    use frob_pm::{ObjectKind, PmStore};
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
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
/// `REL001` findings for the snapshot's repository.
fn rel001_findings(snap: &Snapshot<Frob>) -> Vec<Finding> {
    const ALL: &[&str] = &["REL001"];
    let Some(repo) = rel001_repo(snap) else {
        return Vec::new();
    };
    let cuts = match ledger_of(&snap.inputs, ALL) {
        Err(e) => return settle([Err(e)]),
        Ok(None) => Ok(Vec::new()),
        Ok(Some(state)) => recorded_cuts(&state.ledger).map_err(|e| failed(ALL, e)),
    };
    settle([cuts.map(|c| frob_release::rel001::evaluate(&repo, &c).findings)])
}
