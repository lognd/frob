//! The COH pass: judge every function of the walked files with COH002 and return the verdicts.
//!
//! COH003 runs in the same pass: its callee layers need the definitions of every walked file, so
//! all files are folded first and the layers (`layers::coh003_options`) are built once per run.
//!
//! Findings share the PATH finding and report shapes, so the product converts them the same way.

// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
// frob:ticket 01M5M1TVT09K4YPK17S62Y1A18

use gob_ir::{NodeId, Operator, Universal};
use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{Folded, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_lints::pass::{PathFile, PathFinding, PathReport};

use crate::coh002::{Coh002, Coh002Options, Coh002Unresolved, UnitRole, coh002};
use crate::coh003::{Coh003, Coh003Options, DEFAULT_MAX_LEVEL_SPREAD, Coh003Unresolved, coh003};
use crate::layers::{ModelLayers, coh003_options, definitions};
use crate::unit_role::{declared_roles, resolve_role};

/// Rule id of the decision-with-effects rule.
pub const COH002: &str = "COH002";

/// Rule id of the mixed-abstraction-levels rule.
pub const COH003: &str = "COH003";

/// True when COH002 can judge `language`.
fn judged(language: Language) -> bool {
    matches!(
        language,
        Language::Rust | Language::Python | Language::TypeScript
    )
}

/// The file-level Unresolved finding for a unit whose language has no effects capability.
fn no_capability(path: &str, unit: &str, lang: &str) -> PathFinding {
    PathFinding {
        rule: COH002,
        severity: Severity::Unresolved,
        file: path.to_owned(),
        range: (0, 0),
        message: format!(
            "the {lang} adapter declares no effects capability; `{unit}` cannot be judged"
        ),
        reason: Some(UnresolvedReason::Fidelity),
        anchor: format!("{path}:{unit}:no-effects-capability"),
    }
}

/// The byte range of a node, or an empty range when it has no span.
fn range_of(folded: &Folded, node: NodeId) -> (usize, usize) {
    folded
        .term
        .node(node)
        .location()
        .span()
        .map_or((0, 0), |sp| {
            (
                u32::from(sp.range.start()) as usize,
                u32::from(sp.range.end()) as usize,
            )
        })
}

/// The ids of the function units of a folded file, in source order.
pub(crate) fn function_units(folded: &Folded) -> Vec<NodeId> {
    folded
        .term
        .ids()
        .filter(|&i| {
            matches!(folded.term.node(i).op(),
                Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
        })
        .collect()
}

/// What the COH pass is told: the COH002 vocabularies, the COH003 spread and the model's layers.
#[derive(Debug, Clone)]
pub struct CohPassOptions {
    /// COH002 vocabularies (the `[coh]` overrides on top of the effects capability).
    pub coh002: Coh002Options,
    /// The largest layer distance COH003 still accepts as one level of abstraction.
    pub max_level_spread: u32,
    /// The layered nodes of the grimble model (empty when there is no model or it declares none).
    pub model: ModelLayers,
}

impl Default for CohPassOptions {
    fn default() -> Self {
        Self {
            coh002: Coh002Options::default(),
            max_level_spread: DEFAULT_MAX_LEVEL_SPREAD,
            model: ModelLayers::default(),
        }
    }
}

/// A walked file that parsed, ready to be judged.
struct Parsed<'a> {
    /// The walked file.
    file: &'a PathFile<'a>,
    /// Its folded universal term.
    folded: Folded,
}

/// Fold every file COH can judge; an unparsable file is skipped.
fn fold_judged<'a>(files: &'a [PathFile<'a>]) -> Vec<Parsed<'a>> {
    files
        .iter()
        .filter(|f| judged(f.language))
        .filter_map(|f| {
            let entry = FileEntry {
                path: f.path.to_owned(),
                size: f.text.len() as u64,
                digest: Digest::of(f.text.as_bytes()),
                language: LanguageHint::from_path(f.path),
            };
            match fold_file(&entry, f.text) {
                Ok(folded) => Some(Parsed { file: f, folded }),
                Err(err) => {
                    tracing::debug!(file = f.path, %err, "coh pass skipped an unparsable file");
                    None
                }
            }
        })
        .collect()
}

/// Judge every function of one file with COH002 and push the findings.
fn judge_coh002(f: &PathFile<'_>, folded: &Folded, opts: &Coh002Options, report: &mut PathReport) {
    let mut unknown: Vec<String> = Vec::new();
    let roles = declared_roles(folded, f.language, f.text);
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        let role = resolve_role(roles.get(&unit).copied(), UnitRole::None);
        let Some(verdict) = coh002(folded, f.language.name(), unit, role, opts) else {
            continue;
        };
        match verdict {
            Coh002::Fire { decisions, .. } => {
                for d in decisions {
                    let callees: Vec<&str> =
                        d.effects.iter().map(|e| e.callee.as_str()).collect();
                    report.findings.push(PathFinding {
                        rule: COH002,
                        severity: Severity::Advisory,
                        file: f.path.to_owned(),
                        range: range_of(folded, d.decision),
                        message: format!(
                            "`{name}` decides on computed data and performs effects in the branch ({}); return the decision and act in the caller",
                            callees.join(", ")
                        ),
                        reason: None,
                        anchor: format!("{}:{name}", f.path),
                    });
                }
            }
            Coh002::Unresolved(Coh002Unresolved::UnknownCallees { callees }) => {
                unknown.extend(callees);
            }
            Coh002::Unresolved(Coh002Unresolved::UnverifiedShell { decisions }) => {
                report.findings.push(PathFinding {
                    rule: COH002,
                    severity: Severity::Unresolved,
                    file: f.path.to_owned(),
                    range: decisions
                        .first()
                        .map_or((0, 0), |d| range_of(folded, d.decision)),
                    message: format!(
                        "`{name}` claims `grimble:shell` but the claim is not verified; its decisions with effects stay unjudged"
                    ),
                    reason: Some(UnresolvedReason::AnnotationEffects),
                    anchor: format!("{}:{name}:shell", f.path),
                });
            }
            Coh002::Unresolved(Coh002Unresolved::NoEffectsCapability { lang }) => {
                report.findings.push(no_capability(f.path, name, &lang));
            }
            Coh002::Clean => {}
        }
    }
    if !unknown.is_empty() {
        unknown.sort();
        unknown.dedup();
        // One Unresolved verdict per file keeps an unclassified vocabulary from flooding.
        report.findings.push(PathFinding {
            rule: COH002,
            severity: Severity::Unresolved,
            file: f.path.to_owned(),
            range: (0, 0),
            message: format!(
                "branches call callees with an unknown effect ({}); the language adapter cannot place them; add them to [coh] effect_calls or trivial",
                unknown.join(", ")
            ),
            reason: Some(UnresolvedReason::EdgeUnknown),
            anchor: format!("{}:unresolved:{COH002}", f.path),
        });
    }
}

/// The Unresolved message of a file whose branches call callees on no layer.
fn unplaced_message(unknown: &[String], layers_known: bool) -> String {
    let names = unknown.join(", ");
    if layers_known {
        format!(
            "calls to callees on no layer ({names}) leave the abstraction levels unjudged; define them in a walked file the model or the module depth places"
        )
    } else {
        format!(
            "no layer source places any callee ({names}); declare `attr layer` on model nodes that own the code, or spread the code over module depths"
        )
    }
}

/// Judge every function of one file with COH003 under `opts` and push the findings.
fn judge_coh003(f: &PathFile<'_>, folded: &Folded, opts: &Coh003Options, report: &mut PathReport) {
    let mut unknown: Vec<String> = Vec::new();
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        match coh003(&folded.term, f.language.name(), unit, opts) {
            Coh003::Fire { spread, high, low } => {
                let names = |calls: &[crate::coh003::LayeredCall]| -> String {
                    let mut v: Vec<String> = calls
                        .iter()
                        .map(|c| format!("{} (layer {})", c.callee, c.layer))
                        .collect();
                    v.dedup();
                    v.join(", ")
                };
                report.findings.push(PathFinding {
                    rule: COH003,
                    severity: Severity::Advisory,
                    file: f.path.to_owned(),
                    range: high.first().map_or((0, 0), |c| range_of(folded, c.node)),
                    message: format!(
                        "`{name}` mixes abstraction levels ({spread} layers apart, more than {}): {} next to {}; extract the low-level steps into a helper",
                        opts.max_level_spread,
                        names(&high),
                        names(&low)
                    ),
                    reason: None,
                    anchor: format!("{}:{name}:{COH003}", f.path),
                });
            }
            Coh003::Unresolved(Coh003Unresolved::UnknownCallees { callees }) => {
                unknown.extend(callees);
            }
            Coh003::Clean => {}
        }
    }
    if !unknown.is_empty() {
        unknown.sort();
        unknown.dedup();
        // One Unresolved verdict per file keeps an unplaced vocabulary from flooding.
        report.findings.push(PathFinding {
            rule: COH003,
            severity: Severity::Unresolved,
            file: f.path.to_owned(),
            range: (0, 0),
            message: unplaced_message(&unknown, !opts.layers.is_empty()),
            reason: Some(UnresolvedReason::EdgeUnknown),
            anchor: format!("{}:unresolved:{COH003}", f.path),
        });
    }
}

/// Run COH002 and COH003 over `files` with `opts`.
pub fn analyze(files: &[PathFile<'_>], opts: &CohPassOptions) -> PathReport {
    let mut report = PathReport::default();
    let parsed = fold_judged(files);
    let examined = parsed.len();
    let defs: Vec<_> = parsed
        .iter()
        .map(|p| definitions(p.file.path, &p.folded))
        .collect();
    let mut coh003_opts = coh003_options(&opts.model, &defs);
    coh003_opts.max_level_spread = opts.max_level_spread;
    for p in &parsed {
        judge_coh002(p.file, &p.folded, &opts.coh002, &mut report);
        judge_coh003(p.file, &p.folded, &coh003_opts, &mut report);
    }
    if examined == 0 {
        for id in [COH002, COH003] {
            report.not_applicable.insert(
                id,
                "no Rust, Python or TypeScript files in the walk".to_owned(),
            );
        }
    } else {
        report.subjects.insert(COH002, examined);
        report.subjects.insert(COH003, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(
        findings = report.findings.len(),
        examined,
        layered = coh003_opts.layers.len(),
        "coh pass done"
    );
    report
}
