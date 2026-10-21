//! Fix harness (ruff-style): apply fixes to a fixpoint, snapshot the diff, reject regressions.
//!
//! The harness is engine-agnostic: the caller supplies `observe`, which parses and checks the
//! current fixture files and reports an [`Observation`]. Each round plans the observed fixes,
//! applies them in memory and re-observes; a round that degrades parse status, opaque or hole
//! counts, or turns a firing finding into an unresolved one is a [`Violation`].

// frob:ticket 01M47QTVCF0WDJWM22AG4WAFJT

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use crate::apply::splice;
use crate::plan::{Edit, Fix, Tier, plan};

/// Most rounds before a fixture is declared non-convergent (ruff uses the same bound).
pub const MAX_ROUNDS: usize = 10;

/// How well one file parsed; later variants are worse, so a round must never increase it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ParseStatus {
    /// No syntax errors.
    Clean,
    /// Parsed with error recovery.
    Recovered,
    /// No usable tree.
    Failed,
}

/// Outcome class of one finding; only the fire to unresolved move is policed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FindingClass {
    /// The rule decided and fired.
    Fire,
    /// The rule could not decide.
    Unresolved,
}

/// One finding as the harness sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObservedFinding {
    /// Rule id.
    pub rule: String,
    /// Line-number-free identity (the fingerprint), stable across fix rounds.
    pub key: String,
    /// Fire or unresolved.
    pub class: FindingClass,
    /// Whether a fix admitted at the run's tier is attached.
    pub fixable: bool,
}

/// Everything the harness needs from one check of the current files.
#[derive(Debug, Clone, Default)]
pub struct Observation {
    /// Parse status per path (a path absent here counts as clean).
    pub parse: BTreeMap<String, ParseStatus>,
    /// Opaque regions across all files.
    pub opaque: usize,
    /// Holes across all files.
    pub holes: usize,
    /// Findings of the rules under test.
    pub findings: Vec<ObservedFinding>,
    /// Fixes proposed by those findings.
    pub fixes: Vec<Fix>,
}

/// One fixture: a rule and the (possibly multi-file) sources it is run over.
#[derive(Debug, Clone)]
pub struct Fixture {
    /// Fixture name, used in the snapshot name and messages.
    pub name: String,
    /// Rule the fixture belongs to.
    pub rule: String,
    /// Path to source text.
    pub files: BTreeMap<String, String>,
}

/// Why a fixture failed the harness.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Violation {
    /// A planned edit is out of range, off a char boundary or names an unknown file.
    InvalidEdit {
        /// Round (1-based).
        round: usize,
        /// Offending path.
        path: String,
    },
    /// A file's parse status got worse after a round.
    ParseDegraded {
        /// Round (1-based).
        round: usize,
        /// Offending path.
        path: String,
        /// Status before the round.
        before: ParseStatus,
        /// Status after the round.
        after: ParseStatus,
    },
    /// The opaque-region count grew after a round.
    OpaqueIncreased {
        /// Round (1-based).
        round: usize,
        /// Count before.
        before: usize,
        /// Count after.
        after: usize,
    },
    /// The hole count grew after a round.
    HolesIncreased {
        /// Round (1-based).
        round: usize,
        /// Count before.
        before: usize,
        /// Count after.
        after: usize,
    },
    /// A finding that fired before the round is unresolved after it.
    ClassChanged {
        /// Round (1-based).
        round: usize,
        /// Rule id.
        rule: String,
        /// Finding key.
        key: String,
    },
    /// Fixes were still being applied after [`MAX_ROUNDS`] rounds (oscillation or runaway).
    NoFixpoint,
    /// A fixable finding survives the fixpoint.
    FixableRemains {
        /// Rule id.
        rule: String,
        /// Finding key.
        key: String,
    },
    /// A fixable rule has no fixture at all.
    NoFixture {
        /// Rule id.
        rule: String,
    },
}

/// Result of running one fixture to a fixpoint (or failure).
#[derive(Debug, Clone)]
pub struct Outcome {
    /// Rounds in which at least one edit was applied.
    pub rounds: usize,
    /// Files after the last applied round.
    pub files: BTreeMap<String, String>,
    /// Everything that went wrong; empty means pass.
    pub violations: Vec<Violation>,
    diff: String,
}

impl Outcome {
    /// Whether the fixture passed every check.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.violations.is_empty()
    }

    /// Deterministic snapshot text: round count then the unified diff original to final.
    #[must_use]
    pub fn snapshot_text(&self) -> String {
        format!("rounds: {}\n{}", self.rounds, self.diff)
    }
}

/// Fixable rules in `fixable` that no fixture covers, as [`Violation::NoFixture`] (empty `fixable` passes).
#[must_use]
pub fn missing_fixtures(fixable: &[&str], fixtures: &[Fixture]) -> Vec<Violation> {
    let covered: BTreeSet<&str> = fixtures.iter().map(|f| f.rule.as_str()).collect();
    fixable
        .iter()
        .filter(|r| !covered.contains(*r))
        .map(|r| {
            tracing::warn!(rule = *r, "fixable rule has no fix fixture");
            Violation::NoFixture {
                rule: (*r).to_owned(),
            }
        })
        .collect()
}

/// Apply the accepted fixes of `fixes` to `files`; `Err(path)` names the first bad edit's file.
fn apply_in_memory(
    accepted: &[Fix],
    files: &BTreeMap<String, String>,
) -> Result<BTreeMap<String, String>, String> {
    let mut by_file: BTreeMap<&str, Vec<&Edit>> = BTreeMap::new();
    for e in accepted.iter().flat_map(|f| &f.edits) {
        let text = files.get(&e.path).ok_or_else(|| e.path.clone())?;
        if e.end > text.len() || !text.is_char_boundary(e.start) || !text.is_char_boundary(e.end) {
            return Err(e.path.clone());
        }
        by_file.entry(e.path.as_str()).or_default().push(e);
    }
    let mut out = files.clone();
    for (path, mut edits) in by_file {
        edits.sort_by_key(|e| (e.start, e.end));
        let bytes = splice(files[path].as_bytes(), &edits);
        // Offsets were checked on char boundaries and replacements are str, so this holds.
        out.insert(
            path.to_owned(),
            String::from_utf8_lossy(&bytes).into_owned(),
        );
    }
    Ok(out)
}

/// Violations of one round between the observations before and after it.
fn round_violations(round: usize, before: &Observation, after: &Observation) -> Vec<Violation> {
    let mut v = Vec::new();
    for (path, b) in &before.parse {
        let a = after.parse.get(path).copied().unwrap_or(ParseStatus::Clean);
        if a > *b {
            v.push(Violation::ParseDegraded {
                round,
                path: path.clone(),
                before: *b,
                after: a,
            });
        }
    }
    for (path, a) in &after.parse {
        let b = before
            .parse
            .get(path)
            .copied()
            .unwrap_or(ParseStatus::Clean);
        if !before.parse.contains_key(path) && *a > b {
            v.push(Violation::ParseDegraded {
                round,
                path: path.clone(),
                before: b,
                after: *a,
            });
        }
    }
    if after.opaque > before.opaque {
        v.push(Violation::OpaqueIncreased {
            round,
            before: before.opaque,
            after: after.opaque,
        });
    }
    if after.holes > before.holes {
        v.push(Violation::HolesIncreased {
            round,
            before: before.holes,
            after: after.holes,
        });
    }
    for b in before
        .findings
        .iter()
        .filter(|f| f.class == FindingClass::Fire)
    {
        let flipped = after
            .findings
            .iter()
            .any(|a| a.rule == b.rule && a.key == b.key && a.class == FindingClass::Unresolved);
        if flipped {
            v.push(Violation::ClassChanged {
                round,
                rule: b.rule.clone(),
                key: b.key.clone(),
            });
        }
    }
    v
}

/// Run `fixture` to a fixpoint at `tier`, checking every round; `observe` checks the current files.
pub fn run_fixture(
    fixture: &Fixture,
    tier: Tier,
    observe: &dyn Fn(&BTreeMap<String, String>) -> Observation,
) -> Outcome {
    let mut files = fixture.files.clone();
    let mut obs = observe(&files);
    let mut rounds = 0;
    let mut violations = Vec::new();
    let mut converged = false;
    while rounds < MAX_ROUNDS {
        let p = plan(obs.fixes.clone(), tier);
        if p.accepted.is_empty() {
            converged = true;
            break;
        }
        let round = rounds + 1;
        let next = match apply_in_memory(&p.accepted, &files) {
            Ok(n) => n,
            Err(path) => {
                tracing::warn!(fixture = %fixture.name, round, %path, "invalid edit");
                violations.push(Violation::InvalidEdit { round, path });
                break;
            }
        };
        if next == files {
            tracing::warn!(fixture = %fixture.name, round, "fixes changed nothing");
            converged = true;
            break;
        }
        files = next;
        rounds = round;
        let after = observe(&files);
        let found = round_violations(round, &obs, &after);
        tracing::debug!(fixture = %fixture.name, round, violations = found.len(), "round done");
        let stop = !found.is_empty();
        violations.extend(found);
        obs = after;
        if stop {
            break;
        }
    }
    if violations.is_empty() {
        if !converged {
            // The last allowed round may itself have reached the fixpoint.
            converged = plan(obs.fixes.clone(), tier).accepted.is_empty();
        }
        if converged {
            violations.extend(obs.findings.iter().filter(|f| f.fixable).map(|f| {
                Violation::FixableRemains {
                    rule: f.rule.clone(),
                    key: f.key.clone(),
                }
            }));
        } else {
            violations.push(Violation::NoFixpoint);
        }
    }
    let diff = fixture
        .files
        .iter()
        .filter(|(p, old)| files.get(*p) != Some(old))
        .map(|(p, old)| unified_diff(p, old, &files[p]))
        .collect();
    Outcome {
        rounds,
        files,
        violations,
        diff,
    }
}

const CONTEXT: usize = 3;

/// Longest-common-subsequence line edit script as `(' '|'-'|'+', line)`.
fn line_script<'a>(a: &[&'a str], b: &[&'a str]) -> Vec<(char, &'a str)> {
    let mut lcs = vec![vec![0usize; b.len() + 1]; a.len() + 1];
    for i in (0..a.len()).rev() {
        for j in (0..b.len()).rev() {
            lcs[i][j] = if a[i] == b[j] {
                lcs[i + 1][j + 1] + 1
            } else {
                lcs[i + 1][j].max(lcs[i][j + 1])
            };
        }
    }
    let (mut i, mut j) = (0, 0);
    let mut out = Vec::new();
    while i < a.len() || j < b.len() {
        if i < a.len() && j < b.len() && a[i] == b[j] {
            out.push((' ', a[i]));
            i += 1;
            j += 1;
        } else if i < a.len() && (j == b.len() || lcs[i + 1][j] >= lcs[i][j + 1]) {
            out.push(('-', a[i]));
            i += 1;
        } else {
            out.push(('+', b[j]));
            j += 1;
        }
    }
    out
}

/// Unified diff (ASCII, three lines of context) of one file, `--- a/` and `+++ b/` headers.
fn unified_diff(path: &str, old: &str, new: &str) -> String {
    let a: Vec<&str> = old.split('\n').collect();
    let b: Vec<&str> = new.split('\n').collect();
    let script = line_script(&a, &b);
    let changed: Vec<usize> = script
        .iter()
        .enumerate()
        .filter(|(_, (c, _))| *c != ' ')
        .map(|(i, _)| i)
        .collect();
    let mut out = format!("--- a/{path}\n+++ b/{path}\n");
    let mut k = 0;
    while k < changed.len() {
        let mut end = changed[k];
        let start = changed[k].saturating_sub(CONTEXT);
        while k + 1 < changed.len() && changed[k + 1] <= end + 2 * CONTEXT + 1 {
            k += 1;
            end = changed[k];
        }
        k += 1;
        let stop = (end + CONTEXT + 1).min(script.len());
        let hunk = &script[start..stop];
        let old_start = script[..start].iter().filter(|(c, _)| *c != '+').count() + 1;
        let new_start = script[..start].iter().filter(|(c, _)| *c != '-').count() + 1;
        let old_n = hunk.iter().filter(|(c, _)| *c != '+').count();
        let new_n = hunk.iter().filter(|(c, _)| *c != '-').count();
        let _ = writeln!(out, "@@ -{old_start},{old_n} +{new_start},{new_n} @@");
        for (c, line) in hunk {
            out.push(*c);
            out.push_str(&line.escape_default().to_string());
            out.push('\n');
        }
    }
    out
}
