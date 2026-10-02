//! Rule programs: polarity, subject accounting and findings (universal-model.md 4.2).

#![allow(
    clippy::many_single_char_names,
    reason = "short bindings in the polarity table"
)]

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use gob_rules::{Finding, RuleId, Severity};
use gob_text::FileId;
use tracing::{debug, info, warn};

use super::ctx::{Ctx, Poison};
use super::relation::Relation;
use crate::answer::{Answer, Truth};
use crate::operator::{Operator, Universal};
use crate::query::Model;
use crate::term::NodeId;

/// Rule polarity: which bound a rule may fire on and certify clean on.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Polarity {
    /// P+, presence: fires on `lo`, clean when `hi` is empty.
    Pplus,
    /// P-, absence: fires when `hi` holds no good thing, clean when `lo` does.
    Pminus,
    /// P0, equality: both sides must be `Exact`.
    P0,
    /// Pn, threshold: see [`ThresholdKind`].
    Pn,
    /// Pc, closure: fires on a path inside `lo` edges, clean without one inside `hi`.
    Pc,
}

/// Whether a threshold is an upper bound (`lines > N`) or a lower bound (fewer than N tests).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThresholdKind {
    /// Fires when the measured value exceeds `n`.
    Max,
    /// Fires when the measured value is below `n`.
    Min,
}

/// What a rule's check observed about one subject; the shape must match the polarity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Observation {
    /// P+ offenders or P- good things.
    Set(Answer<BTreeSet<NodeId>>),
    /// P0: the two sides, rendered canonically.
    Pair(Answer<String>, Answer<String>),
    /// Pn: the measured value.
    Count(Answer<u64>),
    /// Pc: a path exists inside `lo` edges / inside `hi` edges; `frontier` names the poisoned nodes.
    Reach {
        /// A path exists using only certain edges.
        lo: bool,
        /// A path exists using any possible edge.
        hi: bool,
        /// Nodes where certainty was lost.
        frontier: Vec<NodeId>,
    },
}

impl Observation {
    /// A closure observation from the Kleene truth of "A reaches B".
    pub fn reach(t: Truth, frontier: Vec<NodeId>) -> Self {
        Self::Reach {
            lo: t == Truth::Yes,
            hi: t != Truth::No,
            frontier,
        }
    }

    fn kind(&self) -> &'static str {
        match self {
            Self::Set(_) => "set",
            Self::Pair(..) => "pair",
            Self::Count(_) => "count",
            Self::Reach { .. } => "reach",
        }
    }
}

/// One verdict about a subject.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    /// Certified clean.
    Clean,
    /// The rule fires at these sites.
    Violation {
        /// Offending nodes (the subject itself for P-, P0, Pn, Pc).
        sites: Vec<NodeId>,
    },
    /// Could not be decided.
    Unresolved {
        /// Reason code (`opaque:...`, `hole`, `edge:may`, `unknown`, `vacuous`).
        reason: String,
        /// The maybe-set: possible offenders or poisoned frontier.
        maybe: Vec<NodeId>,
    },
    /// Excluded from the subject set.
    NotApplicable,
}

/// The verdicts for one subject.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubjectResult {
    /// The subject node.
    pub subject: NodeId,
    /// Whether the subject was examined (answer known at least as bounds).
    pub examined: bool,
    /// One or more verdicts (a P+ rule can fire and also report a maybe-set).
    pub verdicts: Vec<Verdict>,
}

/// A finding with the marks gob-rules' `Finding` does not carry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleFinding {
    /// The finding for the check pipeline.
    pub finding: Finding,
    /// A required Unresolved: fails the gate under `fail_on_unresolved = "required"` (D62).
    pub required: bool,
    /// Reason code of an Unresolved finding.
    pub reason: Option<String>,
}

/// The outcome of evaluating one rule over one model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleOutcome {
    /// The rule.
    pub rule: RuleId,
    /// Its polarity.
    pub polarity: Polarity,
    /// Subjects in the subject set (`NotApplicable` subjects excluded).
    pub subjects_total: usize,
    /// Subjects whose answer was known at least as bounds.
    pub subjects_examined: usize,
    /// The whole scope was `NotApplicable`: no findings, listed once in the fidelity report.
    pub not_applicable: bool,
    /// Per-subject results.
    pub results: Vec<SubjectResult>,
    /// Findings, violations then rolled-up Unresolved.
    pub findings: Vec<RuleFinding>,
}

impl RuleOutcome {
    /// Kleene truth of "the rule holds": `No` if it fires, `Unknown` if anything is
    /// Unresolved, else `Yes`. A not-applicable rule is `Unknown` by convention.
    pub fn truth(&self) -> Truth {
        if self
            .findings
            .iter()
            .any(|f| f.finding.severity > Severity::Unresolved)
        {
            Truth::No
        } else if self
            .findings
            .iter()
            .any(|f| f.finding.severity == Severity::Unresolved)
            || self.not_applicable
        {
            Truth::Unknown
        } else {
            Truth::Yes
        }
    }
}

/// Evaluator settings from `[compute]`.
#[derive(Debug, Clone, Default)]
pub struct EvalConfig {
    /// Opaque reason codes whose Unresolved is required (the `[compute]` key is `"required"`).
    pub required_reasons: BTreeSet<String>,
}

/// A rule program was malformed; always a programmer bug.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum EvalError {
    /// No subject selector was set.
    #[error("rule program has no subject selector")]
    NoSubjects,
    /// No check was set.
    #[error("rule program has no check")]
    NoCheck,
    /// A Pn rule without a threshold.
    #[error("Pn rule has no threshold")]
    NoThreshold,
    /// The observation shape does not match the polarity.
    #[error("polarity {polarity:?} cannot interpret a `{got}` observation")]
    Mismatch {
        /// The rule's polarity.
        polarity: Polarity,
        /// The observation kind received.
        got: &'static str,
    },
}

type StratumFn = Box<dyn Fn(&Ctx<'_>) -> Relation>;
type SubjectsFn = Box<dyn Fn(&Ctx<'_>) -> Answer<Vec<NodeId>>>;
type CheckFn = Box<dyn Fn(&Ctx<'_>, NodeId) -> Observation>;

/// A rule as a program over the term relations.
///
/// The ticket allows Rust closures instead of a Datalog parser; strata are ordered
/// closures that each read earlier strata through [`Ctx::derived`], which makes
/// negation stratified by construction. Build with the chained setters, then
/// [`RuleProgram::evaluate`].
pub struct RuleProgram {
    rule: RuleId,
    polarity: Polarity,
    severity: Severity,
    message: String,
    must_measure: bool,
    threshold: Option<(u64, ThresholdKind)>,
    strata: Vec<(String, StratumFn)>,
    subjects: Option<SubjectsFn>,
    check: Option<CheckFn>,
}

impl fmt::Debug for RuleProgram {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RuleProgram")
            .field("rule", &self.rule)
            .field("polarity", &self.polarity)
            .field("strata", &self.strata.len())
            .finish_non_exhaustive()
    }
}

fn sorted(set: &BTreeSet<NodeId>) -> Vec<NodeId> {
    set.iter().copied().collect()
}

impl RuleProgram {
    /// A program for `rule` with `polarity`; default severity `Error`.
    pub fn new(rule: RuleId, polarity: Polarity) -> Self {
        Self {
            rule,
            polarity,
            severity: Severity::Error,
            message: String::new(),
            must_measure: false,
            threshold: None,
            strata: Vec::new(),
            subjects: None,
            check: None,
        }
    }

    /// Severity of violations.
    #[must_use]
    pub fn severity(mut self, s: Severity) -> Self {
        self.severity = s;
        self
    }

    /// Message of findings.
    #[must_use]
    pub fn message(mut self, m: &str) -> Self {
        m.clone_into(&mut self.message);
        self
    }

    /// Mark the rule `must_measure`: examining zero subjects is a required Unresolved.
    #[must_use]
    pub fn must_measure(mut self) -> Self {
        self.must_measure = true;
        self
    }

    /// The threshold of a Pn rule.
    #[must_use]
    pub fn threshold(mut self, n: u64, kind: ThresholdKind) -> Self {
        self.threshold = Some((n, kind));
        self
    }

    /// Add a stratum deriving relation `name`; it may read earlier strata only.
    #[must_use]
    pub fn stratum(mut self, name: &str, f: impl Fn(&Ctx<'_>) -> Relation + 'static) -> Self {
        self.strata.push((name.to_owned(), Box::new(f)));
        self
    }

    /// The subject selector; `NotApplicable` excludes the whole scope.
    #[must_use]
    pub fn subjects(mut self, f: impl Fn(&Ctx<'_>) -> Answer<Vec<NodeId>> + 'static) -> Self {
        self.subjects = Some(Box::new(f));
        self
    }

    /// The per-subject check.
    #[must_use]
    pub fn check(mut self, f: impl Fn(&Ctx<'_>, NodeId) -> Observation + 'static) -> Self {
        self.check = Some(Box::new(f));
        self
    }

    /// Evaluate over `model` with Kleene semantics and subject accounting.
    ///
    /// # Errors
    ///
    /// Returns [`EvalError`] when the program is incomplete or an observation does not
    /// match the polarity.
    pub fn evaluate(&self, model: &Model, cfg: &EvalConfig) -> Result<RuleOutcome, EvalError> {
        let subjects_fn = self.subjects.as_ref().ok_or(EvalError::NoSubjects)?;
        let check = self.check.as_ref().ok_or(EvalError::NoCheck)?;
        if self.polarity == Polarity::Pn && self.threshold.is_none() {
            return Err(EvalError::NoThreshold);
        }
        let ctx = Ctx::new(model);
        for (name, f) in &self.strata {
            let rel = f(&ctx);
            debug!(rule = %self.rule, stratum = %name, pairs = rel.len(), "stratum derived");
            ctx.set_derived(name, rel);
        }
        ctx.clear_poison();

        let mut results = Vec::new();
        let (subjects, extra_unknown, scope_unknown) = match subjects_fn(&ctx) {
            Answer::NotApplicable => {
                info!(rule = %self.rule, "scope not applicable");
                return Ok(self.finish(model, cfg, Vec::new(), true, 0, 0));
            }
            Answer::Unknown => (Vec::new(), Vec::new(), true),
            Answer::Exact(v) => (v, Vec::new(), false),
            Answer::Bounds { lo, hi } => {
                let lo_set: BTreeSet<NodeId> = lo.iter().copied().collect();
                let extra = hi.into_iter().filter(|n| !lo_set.contains(n)).collect();
                (lo, extra, false)
            }
        };
        ctx.clear_poison();
        let mut total = 0usize;
        let mut examined = 0usize;
        let mut all_na = !subjects.is_empty() && extra_unknown.is_empty();
        for s in subjects {
            let r = self.evaluate_subject(&ctx, check.as_ref(), s)?;
            if r.verdicts == [Verdict::NotApplicable] {
                results.push(r);
                continue;
            }
            all_na = false;
            total += 1;
            examined += usize::from(r.examined);
            results.push(r);
        }
        for s in extra_unknown {
            total += 1;
            all_na = false;
            results.push(SubjectResult {
                subject: s,
                examined: false,
                verdicts: vec![Verdict::Unresolved {
                    reason: "unknown".to_owned(),
                    maybe: Vec::new(),
                }],
            });
        }
        if scope_unknown {
            results.push(SubjectResult {
                subject: model.term().root(),
                examined: false,
                verdicts: vec![Verdict::Unresolved {
                    reason: "unknown".to_owned(),
                    maybe: Vec::new(),
                }],
            });
        }
        Ok(self.finish(model, cfg, results, all_na, total, examined))
    }

    fn evaluate_subject(
        &self,
        ctx: &Ctx<'_>,
        check: &dyn Fn(&Ctx<'_>, NodeId) -> Observation,
        s: NodeId,
    ) -> Result<SubjectResult, EvalError> {
        let node = ctx.term().node(s);
        let unexamined = |reason: String| SubjectResult {
            subject: s,
            examined: false,
            verdicts: vec![Verdict::Unresolved {
                reason,
                maybe: Vec::new(),
            }],
        };
        match &node.op {
            Operator::Universal(Universal::Opaque { reason, .. }) => {
                return Ok(unexamined(reason.clone()));
            }
            Operator::Universal(Universal::Hole { .. }) => {
                return Ok(unexamined("hole".to_owned()));
            }
            _ => {}
        }
        ctx.clear_poison();
        let obs = check(ctx, s);
        let poison = ctx.poison();
        let reason = poison
            .first()
            .map_or_else(|| "unknown".to_owned(), |p: &Poison| p.reason.code());
        let obs = if poison.is_empty() { obs } else { taint(obs) };
        self.interpret(s, &obs, &reason)
    }

    fn interpret(
        &self,
        s: NodeId,
        obs: &Observation,
        reason: &str,
    ) -> Result<SubjectResult, EvalError> {
        let unresolved = |maybe: Vec<NodeId>| Verdict::Unresolved {
            reason: reason.to_owned(),
            maybe,
        };
        let mismatch = |o: &Observation| EvalError::Mismatch {
            polarity: self.polarity,
            got: o.kind(),
        };
        let violation = |sites: Vec<NodeId>| Verdict::Violation { sites };
        let (examined, verdicts) = match (self.polarity, obs) {
            (Polarity::Pplus, Observation::Set(a)) => match a {
                Answer::Exact(set) if set.is_empty() => (true, vec![Verdict::Clean]),
                Answer::Exact(set) => (true, vec![violation(sorted(set))]),
                Answer::Bounds { lo, hi } => {
                    let maybe: Vec<NodeId> = hi.difference(lo).copied().collect();
                    let mut v = Vec::new();
                    if !lo.is_empty() {
                        v.push(violation(sorted(lo)));
                    }
                    if !maybe.is_empty() {
                        v.push(unresolved(maybe));
                    } else if lo.is_empty() {
                        v.push(Verdict::Clean);
                    }
                    (true, v)
                }
                Answer::Unknown => (false, vec![unresolved(Vec::new())]),
                Answer::NotApplicable => (false, vec![Verdict::NotApplicable]),
            },
            (Polarity::Pminus, Observation::Set(a)) => match a {
                Answer::Exact(set) if set.is_empty() => (true, vec![violation(vec![s])]),
                Answer::Exact(_) => (true, vec![Verdict::Clean]),
                Answer::Bounds { lo, hi } => {
                    if hi.is_empty() {
                        (true, vec![violation(vec![s])])
                    } else if !lo.is_empty() {
                        (true, vec![Verdict::Clean])
                    } else {
                        (true, vec![unresolved(sorted(hi))])
                    }
                }
                Answer::Unknown => (false, vec![unresolved(Vec::new())]),
                Answer::NotApplicable => (false, vec![Verdict::NotApplicable]),
            },
            (Polarity::P0, Observation::Pair(l, r)) => match (l, r) {
                (Answer::NotApplicable, _) | (_, Answer::NotApplicable) => {
                    (false, vec![Verdict::NotApplicable])
                }
                (Answer::Exact(a), Answer::Exact(b)) if a == b => (true, vec![Verdict::Clean]),
                (Answer::Exact(_), Answer::Exact(_)) => (true, vec![violation(vec![s])]),
                (Answer::Unknown, _) | (_, Answer::Unknown) => {
                    (false, vec![unresolved(Vec::new())])
                }
                _ => (true, vec![unresolved(Vec::new())]),
            },
            (Polarity::Pn, Observation::Count(a)) => {
                let (n, kind) = self.threshold.ok_or(EvalError::NoThreshold)?;
                match (a, kind) {
                    (Answer::Exact(v), ThresholdKind::Max) if *v > n => {
                        (true, vec![violation(vec![s])])
                    }
                    (Answer::Exact(v), ThresholdKind::Min) if *v < n => {
                        (true, vec![violation(vec![s])])
                    }
                    (Answer::Exact(_), _) => (true, vec![Verdict::Clean]),
                    (Answer::Bounds { lo, .. }, ThresholdKind::Max) if *lo > n => {
                        (true, vec![violation(vec![s])])
                    }
                    (Answer::Bounds { hi, .. }, ThresholdKind::Max) if *hi <= n => {
                        (true, vec![Verdict::Clean])
                    }
                    (Answer::Bounds { hi, .. }, ThresholdKind::Min) if *hi < n => {
                        (true, vec![violation(vec![s])])
                    }
                    (Answer::Bounds { lo, .. }, ThresholdKind::Min) if *lo >= n => {
                        (true, vec![Verdict::Clean])
                    }
                    (Answer::Bounds { .. }, _) => (true, vec![unresolved(Vec::new())]),
                    (Answer::Unknown, _) => (false, vec![unresolved(Vec::new())]),
                    (Answer::NotApplicable, _) => (false, vec![Verdict::NotApplicable]),
                }
            }
            (Polarity::Pc, Observation::Reach { lo, hi, frontier }) => {
                if *lo {
                    (true, vec![violation(vec![s])])
                } else if !*hi {
                    (true, vec![Verdict::Clean])
                } else {
                    (true, vec![unresolved(frontier.clone())])
                }
            }
            _ => return Err(mismatch(obs)),
        };
        Ok(SubjectResult {
            subject: s,
            examined,
            verdicts,
        })
    }

    fn finish(
        &self,
        model: &Model,
        cfg: &EvalConfig,
        results: Vec<SubjectResult>,
        not_applicable: bool,
        total: usize,
        examined: usize,
    ) -> RuleOutcome {
        let term = model.term();
        let mut findings = Vec::new();
        if !not_applicable {
            let anchor_of = |n: NodeId| enclosing_symref(model, n);
            let mut rolled: BTreeMap<(FileId, String), Vec<NodeId>> = BTreeMap::new();
            for r in &results {
                for v in &r.verdicts {
                    match v {
                        Verdict::Violation { sites } => {
                            for &site in sites {
                                let n = term.node(site);
                                let msg = format!("{} [{}]", self.message, anchor_of(site));
                                findings.push(RuleFinding {
                                    finding: Finding::new(
                                        self.rule.clone(),
                                        self.severity,
                                        n.location.span(),
                                        msg,
                                        &anchor_of(site),
                                    ),
                                    required: false,
                                    reason: None,
                                });
                            }
                        }
                        Verdict::Unresolved { reason, .. } => {
                            let key = (term.node(r.subject).location.artifact(), reason.clone());
                            rolled.entry(key).or_default().push(r.subject);
                        }
                        Verdict::Clean | Verdict::NotApplicable => {}
                    }
                }
            }
            let measure_failed = self.must_measure && examined == 0;
            for ((_, reason), sites) in &rolled {
                findings.push(self.unresolved_finding(model, cfg, reason, sites, measure_failed));
            }
            if examined == 0 && rolled.is_empty() {
                warn!(rule = %self.rule, "rule examined zero subjects");
                findings.push(self.unresolved_finding(
                    model,
                    cfg,
                    "vacuous",
                    &[term.root()],
                    measure_failed,
                ));
            }
        }
        info!(
            rule = %self.rule,
            total,
            examined,
            findings = findings.len(),
            not_applicable,
            "rule evaluated"
        );
        RuleOutcome {
            rule: self.rule.clone(),
            polarity: self.polarity,
            subjects_total: total,
            subjects_examined: examined,
            not_applicable,
            results,
            findings,
        }
    }

    fn unresolved_finding(
        &self,
        model: &Model,
        cfg: &EvalConfig,
        reason: &str,
        sites: &[NodeId],
        measure_failed: bool,
    ) -> RuleFinding {
        let term = model.term();
        let first = sites[0];
        let names: Vec<String> = sites
            .iter()
            .take(3)
            .map(|&n| enclosing_symref(model, n))
            .collect();
        let message = format!(
            "{}: unresolved ({reason}) at {} site(s): {}",
            self.message,
            sites.len(),
            names.join(", ")
        );
        let anchor = format!("{}#{reason}", term.locator());
        RuleFinding {
            finding: Finding::new(
                self.rule.clone(),
                Severity::Unresolved,
                term.node(first).location.span(),
                message,
                &anchor,
            ),
            required: measure_failed || cfg.required_reasons.contains(reason),
            reason: Some(reason.to_owned()),
        }
    }
}

/// An `Exact` answer computed through poisoned atoms is not exact: downgrade to `Unknown`.
/// Explicit `Bounds` and `Reach` are the check's own statement and are trusted.
fn taint(obs: Observation) -> Observation {
    fn down<T>(a: Answer<T>) -> Answer<T> {
        if a.is_exact() { Answer::Unknown } else { a }
    }
    match obs {
        Observation::Set(a) => Observation::Set(down(a)),
        Observation::Pair(l, r) => Observation::Pair(down(l), down(r)),
        Observation::Count(a) => Observation::Count(down(a)),
        reach @ Observation::Reach { .. } => reach,
    }
}

/// The symref of the nearest unit at or above `n`, else the artifact locator.
fn enclosing_symref(model: &Model, n: NodeId) -> String {
    let term = model.term();
    std::iter::once(n)
        .chain(term.ancestors(n))
        .find_map(|a| term.symref_of(a))
        .map_or_else(|| term.locator().to_owned(), ToString::to_string)
}
