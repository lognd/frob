//! The COH pass: judge every function of the walked files with COH001 and COH002 and return the verdicts.
//!
//! COH003 runs in the same pass: its callee layers need the definitions of every walked file, so
//! all files are folded first and the layers (`layers::coh003_options`) are built once per run.
//!
//! Findings share the PATH finding and report shapes, so the product converts them the same way.

// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
// frob:ticket 01M5M1TVT09K4YPK17S62Y1A18
// frob:ticket 01M5M34XTDZEZ08TAA78872RRP
// frob:ticket 01M6ABTQWDG7TKJDYTZDEYY4PR
// frob:ticket 01M4TVEKR73CP9A5RGGPPK3AWW
// frob:ticket 01M5K18043Y5V9TF7QD2KNYR34

use gob_ir::{NodeId, Operator, Universal};
use gob_languages::Language;
use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{Folded, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use grimble_lints::lang::{is_code, script_family, tag};
use grimble_lints::pass::{PathFile, PathFinding, PathReport};
use rayon::prelude::*;

use crate::coh001::{Coh001, CohOptions, coh001};
use crate::coh002::{Coh002, Coh002Options, Coh002Unresolved, UnitRole, coh002};
use crate::coh003::{Coh003, Coh003Options, Coh003Unresolved, DEFAULT_MAX_LEVEL_SPREAD, coh003};
use crate::coh004::{Coh004, Coh004Options, coh004};
use crate::layers::{ModelLayers, coh003_options, definitions};
use crate::unit_role::{declared_roles, resolve_role};

/// Rule id of the independent-jobs rule.
pub const COH001: &str = "COH001";

/// Rule id of the decision-with-effects rule.
pub const COH002: &str = "COH002";

/// Rule id of the mixed-abstraction-levels rule.
pub const COH003: &str = "COH003";

/// Rule id of the mixed-vocabularies rule.
pub const COH004: &str = "COH004";

/// True when COH002 can judge `language`.
fn judged(language: Language) -> bool {
    matches!(language, Language::Rust | Language::Python) || script_family(language)
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
    /// COH001 knobs (`min_slice_statements` and the trivial vocabulary from the `[coh]` table).
    pub coh001: CohOptions,
    /// COH002 vocabularies (the `[coh]` overrides on top of the effects capability).
    pub coh002: Coh002Options,
    /// COH004 knobs (the cluster floor and stop words from the `[coh]` table).
    pub coh004: Coh004Options,
    /// The largest layer distance COH003 still accepts as one level of abstraction.
    pub max_level_spread: u32,
    /// The layered nodes of the grimble model (empty when there is no model or it declares none).
    pub model: ModelLayers,
}

impl Default for CohPassOptions {
    fn default() -> Self {
        Self {
            coh001: CohOptions::default(),
            coh002: Coh002Options::default(),
            coh004: Coh004Options::default(),
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

/// Fold one judged file; an unparsable file is skipped.
fn fold_one<'a>(f: &'a PathFile<'a>) -> Option<Parsed<'a>> {
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
}

/// Push one Unresolved finding per COH rule and unjudged code language, at the first such file.
///
/// A language COH cannot judge is reported rather than dropped, so a repository in Go or Java
/// never passes COH as if it had been examined.
fn report_unjudged(files: &[PathFile<'_>], report: &mut PathReport) {
    let mut seen: std::collections::BTreeSet<&'static str> = std::collections::BTreeSet::new();
    for f in files
        .iter()
        .filter(|f| !judged(f.language) && is_code(f.language))
    {
        if !seen.insert(f.language.name()) {
            continue;
        }
        tracing::debug!(
            file = f.path,
            language = f.language.name(),
            "coh: language unjudged"
        );
        for rule in [COH001, COH002, COH003, COH004] {
            report
                .findings
                .push(grimble_lints::pass::unsupported_language(
                    rule, f.path, f.language,
                ));
        }
    }
}

/// Fold every file COH can judge across the rayon pool, keeping the walk order.
///
/// Folding is the bulk of the pass (a parse and a scope graph per file) and files are independent,
/// so a serial loop left every other core idle. `fold` is a parameter so a test can observe how
/// many folds run at once.
fn fold_judged_with<'a, F>(files: &'a [PathFile<'a>], fold: F) -> Vec<Parsed<'a>>
where
    F: Fn(&'a PathFile<'a>) -> Option<Parsed<'a>> + Sync,
{
    let judged_files: Vec<&'a PathFile<'a>> = files.iter().filter(|f| judged(f.language)).collect();
    tracing::debug!(files = judged_files.len(), "coh pass folding in parallel");
    judged_files.into_par_iter().filter_map(&fold).collect()
}

/// Fold every file COH can judge; an unparsable file is skipped.
fn fold_judged<'a>(files: &'a [PathFile<'a>]) -> Vec<Parsed<'a>> {
    fold_judged_with(files, fold_one)
}

/// Judge every function of one file with COH001 and push the findings.
fn judge_coh001(f: &PathFile<'_>, folded: &Folded, opts: &CohOptions, report: &mut PathReport) {
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        // A language without def-use support yields no verdict: the unit is simply not judged.
        let Some(verdict) = coh001(folded, tag(f.language), unit, opts) else {
            continue;
        };
        match verdict {
            Coh001::Fire { lo, fixes, .. } => {
                tracing::debug!(file = f.path, unit = name, jobs = lo, "COH001 fires");
                let first = fixes
                    .iter()
                    .find_map(|x| x.statements.first().copied())
                    .unwrap_or(unit);
                report.findings.push(PathFinding {
                    rule: COH001,
                    severity: Severity::Error,
                    file: f.path.to_owned(),
                    range: range_of(folded, first),
                    message: format!(
                        "`{name}` does {lo} independent jobs; extract each job into its own unit"
                    ),
                    reason: None,
                    anchor: format!("{}:{name}", f.path),
                });
            }
            Coh001::Unresolved { lo, hi, witnesses } => {
                let vars: Vec<&str> = witnesses.iter().map(|w| w.var.as_str()).collect();
                tracing::debug!(file = f.path, unit = name, lo, hi, "COH001 unresolved");
                report.findings.push(PathFinding {
                    rule: COH001,
                    severity: Severity::Unresolved,
                    file: f.path.to_owned(),
                    range: witnesses
                        .first()
                        .map_or((0, 0), |w| range_of(folded, w.def)),
                    message: format!(
                        "`{name}` looks like {hi} independent jobs unless a may-alias edge ({}) joins them",
                        vars.join(", ")
                    ),
                    reason: Some(UnresolvedReason::EdgeMay),
                    anchor: format!("{}:{name}:{COH001}", f.path),
                });
            }
            Coh001::Clean => {}
        }
    }
}

/// Judge every function of one file with COH002 and push the findings.
fn judge_coh002(f: &PathFile<'_>, folded: &Folded, opts: &Coh002Options, report: &mut PathReport) {
    let mut unknown: Vec<String> = Vec::new();
    let roles = declared_roles(folded, f.language, f.text);
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        let role = resolve_role(roles.get(&unit).copied(), UnitRole::None);
        let Some(verdict) = coh002(folded, tag(f.language), unit, role, opts) else {
            continue;
        };
        match verdict {
            Coh002::Fire { decisions, .. } => {
                for d in decisions {
                    let callees: Vec<&str> = d.effects.iter().map(|e| e.callee.as_str()).collect();
                    report.findings.push(PathFinding {
                        rule: COH002,
                        severity: Severity::Error,
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

/// Judge every function of one file with COH004 and push the findings.
///
/// The verdict is a heuristic, so it is reported Unresolved (never an Error): the severity model has
/// no Advisory (rules.md 6.1.1), and Unresolved never fails a run by itself.
fn judge_coh004(f: &PathFile<'_>, folded: &Folded, opts: &Coh004Options, report: &mut PathReport) {
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        if let Coh004::Advisory { clusters } = coh004(&folded.term, unit, opts) {
            tracing::debug!(
                file = f.path,
                unit = name,
                clusters = clusters.len(),
                "COH004 fires"
            );
            let shown: Vec<String> = clusters
                .iter()
                .map(|c| format!("[{}]", c.join(", ")))
                .collect();
            report.findings.push(PathFinding {
                rule: COH004,
                severity: Severity::Unresolved,
                file: f.path.to_owned(),
                range: range_of(folded, unit),
                message: format!(
                    "`{name}` mixes {} unrelated vocabularies: {}; consider splitting it",
                    clusters.len(),
                    shown.join(" and ")
                ),
                reason: Some(UnresolvedReason::Opaque(
                    "heuristic:vocabularies".to_owned(),
                )),
                anchor: format!("{}:{name}:{COH004}", f.path),
            });
        }
    }
}

/// Judge every function of one file with COH003 under `opts` and push the findings.
///
/// Returns the sorted, deduplicated callee names on no layer; the caller decides how to report them.
fn judge_coh003(
    f: &PathFile<'_>,
    folded: &Folded,
    opts: &Coh003Options,
    report: &mut PathReport,
) -> Vec<String> {
    let mut unknown: Vec<String> = Vec::new();
    if grimble_lints::path::is_test_path(f.path) {
        // A test calls the code under test across every layer by design; that is not a smell.
        tracing::debug!(file = %f.path, "coh003 skips a test file");
        return unknown;
    }
    for unit in function_units(folded) {
        let name = folded.term.node(unit).name().unwrap_or("<anonymous>");
        match coh003(&folded.term, tag(f.language), unit, opts) {
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
                    severity: Severity::Error,
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
    unknown.sort();
    unknown.dedup();
    unknown
}

/// Note the unplaced callees in the log; they are not findings.
///
/// A callee on no layer (a library call sharing a repo name, a function in a file no layer source
/// places) cannot prove a spread, so it never fails or warns: P+ means only a proven spread fires.
/// The names stay visible at debug level for anyone calibrating a model.
fn report_unplaced(unplaced: &[(String, Vec<String>)], layered: bool) {
    for (file, names) in unplaced {
        tracing::debug!(%file, layered, message = %unplaced_message(names, layered), "coh003 callees on no layer");
    }
}

/// Run COH001 to COH004 over `files` with `opts`.
pub fn analyze(files: &[PathFile<'_>], opts: &CohPassOptions) -> PathReport {
    let mut report = PathReport::default();
    let parsed = fold_judged(files);
    let examined = parsed.len();
    report_unjudged(files, &mut report);
    let defs: Vec<_> = parsed
        .iter()
        .map(|p| definitions(p.file.path, &p.folded))
        .collect();
    let mut coh003_opts = coh003_options(&opts.model, &defs);
    coh003_opts.max_level_spread = opts.max_level_spread;
    let coh004_opts = &opts.coh004;
    let judged_each: Vec<(PathReport, Vec<String>)> = parsed
        .par_iter()
        .map(|p| {
            let mut each = PathReport::default();
            judge_coh001(p.file, &p.folded, &opts.coh001, &mut each);
            judge_coh002(p.file, &p.folded, &opts.coh002, &mut each);
            judge_coh004(p.file, &p.folded, coh004_opts, &mut each);
            let names = judge_coh003(p.file, &p.folded, &coh003_opts, &mut each);
            (each, names)
        })
        .collect();
    let mut unplaced: Vec<(String, Vec<String>)> = Vec::new();
    for (p, (each, names)) in parsed.iter().zip(judged_each) {
        report.findings.extend(each.findings);
        if !names.is_empty() {
            unplaced.push((p.file.path.to_owned(), names));
        }
    }
    // Freeing thousands of terms one by one on this thread costs a measurable share of the pass.
    parsed.into_par_iter().for_each(drop);
    report_unplaced(&unplaced, !coh003_opts.layers.is_empty());
    if examined == 0 {
        for id in [COH001, COH002, COH003, COH004] {
            report.not_applicable.insert(
                id,
                "no Rust, Python, TypeScript or JavaScript files in the walk".to_owned(),
            );
        }
    } else {
        report.subjects.insert(COH001, examined);
        report.subjects.insert(COH002, examined);
        report.subjects.insert(COH003, examined);
        report.subjects.insert(COH004, examined);
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

#[cfg(test)]
mod tests {
    //! Count-based guard for the parallel fold (ticket DEYY4PR): concurrency is counted, never timed.

    use std::sync::atomic::{AtomicUsize, Ordering};

    use super::*;

    /// A tiny Rust source whose one function is judged.
    const SRC: &str = "fn helper() -> u32 { 1 }\nfn run() -> u32 { helper() }\n";

    /// Files fold concurrently (at least two in flight at once), once each, in walk order.
    // frob:tests crates/grimble-check/src/coh_pass.rs::fold_judged_with
    #[test]
    fn fold_runs_files_concurrently_exactly_once_in_order() {
        let paths: Vec<String> = (0..32).map(|i| format!("src/f{i}.rs")).collect();
        let files: Vec<PathFile<'_>> = paths
            .iter()
            .map(|p| PathFile {
                path: p,
                language: Language::Rust,
                text: SRC,
            })
            .collect();
        let in_flight = AtomicUsize::new(0);
        let peak = AtomicUsize::new(0);
        let calls = AtomicUsize::new(0);
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .expect("test pool builds");
        let parsed = pool.install(|| {
            fold_judged_with(&files, |f| {
                calls.fetch_add(1, Ordering::SeqCst);
                let now = in_flight.fetch_add(1, Ordering::SeqCst) + 1;
                peak.fetch_max(now, Ordering::SeqCst);
                // Hold the slot until a second fold is in flight; a serial fold never gets there,
                // so the bound only caps a failing run, it does not decide a passing one.
                let mut spins = 0_u32;
                while peak.load(Ordering::SeqCst) < 2 && spins < 50_000_000 {
                    std::hint::spin_loop();
                    spins += 1;
                }
                in_flight.fetch_sub(1, Ordering::SeqCst);
                fold_one(f)
            })
        });
        assert!(
            peak.load(Ordering::SeqCst) >= 2,
            "folds never overlapped: the pass is serial again"
        );
        assert_eq!(calls.load(Ordering::SeqCst), files.len());
        let got: Vec<&str> = parsed.iter().map(|p| p.file.path).collect();
        let want: Vec<&str> = paths.iter().map(String::as_str).collect();
        assert_eq!(got, want);
    }

    /// Unjudged languages are never folded.
    // frob:tests crates/grimble-check/src/coh_pass.rs::fold_judged_with
    #[test]
    fn fold_skips_unjudged_languages() {
        let files = [PathFile {
            path: "a.md",
            language: Language::Markdown,
            text: "# x",
        }];
        assert!(fold_judged_with(&files, |_| panic!("must not fold")).is_empty());
    }

    /// A Go file is reported Unresolved for every COH rule, once per language, never silent.
    // frob:tests crates/grimble-check/src/coh_pass.rs::report_unjudged
    #[test]
    fn unjudged_code_language_is_unresolved_once() {
        let files = [
            PathFile {
                path: "a.go",
                language: Language::Go,
                text: "package a\n",
            },
            PathFile {
                path: "b.go",
                language: Language::Go,
                text: "package b\n",
            },
            PathFile {
                path: "c.md",
                language: Language::Markdown,
                text: "# x",
            },
        ];
        let report = analyze(&files, &CohPassOptions::default());
        let unresolved: Vec<_> = report
            .findings
            .iter()
            .filter(|f| f.severity == Severity::Unresolved)
            .collect();
        assert_eq!(unresolved.len(), 4, "{unresolved:?}");
        assert!(unresolved.iter().all(|f| f.file == "a.go"));
    }

    /// TSX, JS and JSX files are judged like TypeScript, so COH sees them as subjects.
    // frob:tests crates/grimble-check/src/coh_pass.rs::judged
    #[test]
    fn script_family_is_judged() {
        for l in [
            Language::Tsx,
            Language::JavaScript,
            Language::Jsx,
            Language::TypeScript,
        ] {
            assert!(judged(l), "{l:?}");
        }
        assert!(!judged(Language::Go));
    }
}
