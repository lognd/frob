//! The COH pass: judge every function of the walked files with COH002 and return the verdicts.
//!
//! Findings share the PATH finding and report shapes, so the product converts them the same way.

// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C

use gob_ir::{NodeId, Operator, Universal};
use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{Folded, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_lints::pass::{PathFile, PathFinding, PathReport};

use crate::coh002::{Coh002, Coh002Options, Coh002Unresolved, UnitRole, coh002};
use crate::unit_role::{declared_roles, resolve_role};

/// Rule id of the decision-with-effects rule.
pub const COH002: &str = "COH002";

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

/// Run COH002 over `files` with `opts`.
pub fn analyze(files: &[PathFile<'_>], opts: &Coh002Options) -> PathReport {
    let mut report = PathReport::default();
    let mut examined = 0usize;
    for f in files.iter().filter(|f| judged(f.language)) {
        let entry = FileEntry {
            path: f.path.to_owned(),
            size: f.text.len() as u64,
            digest: Digest::of(f.text.as_bytes()),
            language: LanguageHint::from_path(f.path),
        };
        let folded = match fold_file(&entry, f.text) {
            Ok(folded) => folded,
            Err(err) => {
                tracing::debug!(file = f.path, %err, "coh pass skipped an unparsable file");
                continue;
            }
        };
        examined += 1;
        let mut unknown: Vec<String> = Vec::new();
        let roles = declared_roles(&folded, f.language, f.text);
        for unit in function_units(&folded) {
            let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
            let role = resolve_role(roles.get(&unit).copied(), UnitRole::None);
            let Some(verdict) = coh002(&folded, f.language.name(), unit, role, opts) else {
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
                            range: range_of(&folded, d.decision),
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
                            .map_or((0, 0), |d| range_of(&folded, d.decision)),
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
    if examined == 0 {
        report.not_applicable.insert(
            COH002,
            "no Rust, Python or TypeScript files in the walk".to_owned(),
        );
    } else {
        report.subjects.insert(COH002, examined);
    }
    report
        .findings
        .sort_by(|a, b| (&a.file, a.rule, &a.anchor).cmp(&(&b.file, b.rule, &b.anchor)));
    tracing::info!(findings = report.findings.len(), examined, "coh pass done");
    report
}
