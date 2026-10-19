//! First NEAT neatness rules: `NEAT010` effect ceiling and `NEAT031` dispatch-site-owns-logic.
//!
//! [`scan`] reads the Rust functions of one file as units, takes their `frob:` claims from the
//! comments above them ([`unit`]), answers the `effects(unit)` capability as a
//! [`gob_ir::Answer`] ([`effects`]) and reports a claim whose lower bound exceeds its ceiling
//! (`NEAT010`, Warn) and a dispatcher whose branch condition is more than a guard
//! (`NEAT031`, Advisory) ([`dispatcher`], docs/design/neatness.md section 4). A claim the
//! analysis cannot decide is reported unresolved, never clean.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

mod dispatcher;
pub mod effects;
mod unit;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;

pub use effects::{Atom, EffectSet};
pub use unit::Claim;

/// Which NEAT rule a finding belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Rule {
    /// `NEAT010`: a unit's effects exceed its declared ceiling.
    EffectCeilingExceeded,
    /// `NEAT031`: a dispatcher owns condition logic that belongs to its callee.
    DispatchSiteOwnsLogic,
}

impl Rule {
    /// The rule id.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::EffectCeilingExceeded => "NEAT010",
            Self::DispatchSiteOwnsLogic => "NEAT031",
        }
    }

    /// The severity the rule ships with.
    pub fn default_severity(self) -> Severity {
        match self {
            Self::EffectCeilingExceeded => Severity::Warn,
            Self::DispatchSiteOwnsLogic => Severity::Advisory,
        }
    }
}

/// The severity a finding carries.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    /// Reported, never gating.
    Advisory,
    /// Reported, gating only when configured so.
    Warn,
}

/// How an effect claim fared against the unit's calls.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    /// The upper bound is inside the claim.
    Verified,
    /// The lower bound exceeds the claim.
    Contradicted,
    /// The analysis could not decide (an unresolved callee).
    Unverified,
}

/// One finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// The rule that fired.
    pub rule: Rule,
    /// The unit (function) name.
    pub unit: String,
    /// The offending span in the scanned text.
    pub range: TextRange,
    /// 1-based line where the span starts.
    pub line: usize,
    /// What to do about it.
    pub message: String,
}

/// One effect claim and its verdict, for every claimed unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimResult {
    /// The unit (function) name.
    pub unit: String,
    /// 1-based line of the unit.
    pub line: usize,
    /// The verdict.
    pub verdict: Verdict,
}

/// Knobs of [`scan`] (`[neat]`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Options {
    /// Callee vocabulary: `(path, atom)`; a call matches a path or its trailing segments
    /// (`[neat.effects]`).
    pub vocabulary: Vec<(String, Atom)>,
    /// The heaviest branch condition `NEAT031` accepts as a guard (`dispatcher_guard_weight`).
    pub guard_weight: usize,
}

impl Default for Options {
    fn default() -> Self {
        let v = |p: &str, a| (p.to_owned(), a);
        Self {
            vocabulary: vec![
                v("std::time::Instant::now", Atom::Clock),
                v("std::time::SystemTime::now", Atom::Clock),
                v("std::env::var", Atom::Env),
                v("std::env::args", Atom::Env),
                v("std::fs::read_to_string", Atom::Fs),
                v("std::fs::read", Atom::Fs),
                v("std::fs::write", Atom::Fs),
                v("std::process::exit", Atom::Exit),
                v("std::net::TcpStream::connect", Atom::Net),
                v("rand::random", Atom::Rng),
                v("rand::thread_rng", Atom::Rng),
                v("std::io::stdin", Atom::Stdio),
            ],
            guard_weight: 2,
        }
    }
}

/// The result of one scan.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Report {
    /// Findings in source order.
    pub findings: Vec<Finding>,
    /// Every claimed unit's verdict; an `Unverified` one is reported Unresolved.
    pub claims: Vec<ClaimResult>,
}

/// Why a file could not be scanned.
#[derive(Debug, thiserror::Error)]
pub enum ScanError {
    /// The file did not parse within the limits, or its grammar is not built in.
    #[error("E-NEAT-PARSE: {0}")]
    Parse(String),
}

/// The NEAT findings of `text` parsed as `language`; only Rust has detectors yet.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan(language: Language, text: &str, options: &Options) -> Result<Report, ScanError> {
    if language != Language::Rust {
        tracing::debug!(language = language.name(), "neat: no detectors, skipped");
        return Ok(Report::default());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let units = unit::units(tree.root(), text);
    let mut report = Report::default();
    for u in &units {
        if let Some(ceiling) = u.ceiling() {
            let answer = effects::effects(u, &units, text, options);
            let verdict = effects::verdict(&answer, &ceiling);
            tracing::debug!(unit = %u.name, ?verdict, "neat010 claim checked");
            report.claims.push(ClaimResult {
                unit: u.name.clone(),
                line: u.line(),
                verdict,
            });
            if verdict == Verdict::Contradicted {
                report.findings.push(Finding {
                    rule: Rule::EffectCeilingExceeded,
                    unit: u.name.clone(),
                    range: tree.node_range(&u.node),
                    line: u.line(),
                    message: format!(
                        "`{}` claims {} but its calls perform {}",
                        u.name,
                        u.claim_text(),
                        effects::describe(&answer)
                    ),
                });
            }
        }
        if u.is_shell() {
            continue;
        }
        for site in dispatcher::offenders(u, text, options.guard_weight) {
            tracing::debug!(unit = %u.name, line = site.row + 1, "neat031 offender");
            report.findings.push(Finding {
                rule: Rule::DispatchSiteOwnsLogic,
                unit: u.name.clone(),
                range: tree.node_range(&site.node),
                line: site.row + 1,
                message: format!(
                    "dispatcher `{}` decides more than a guard (weight {} > {}); move the condition into the callee or a named predicate",
                    u.name, site.weight, options.guard_weight
                ),
            });
        }
    }
    report.findings.sort_by_key(|f| (f.range.start(), f.rule));
    tracing::debug!(
        findings = report.findings.len(),
        claims = report.claims.len(),
        "neat scanned"
    );
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/neat/mod.rs::Rule.rule_id
    #[test]
    fn rule_ids_follow_rules() {
        assert_eq!(Rule::EffectCeilingExceeded.rule_id(), "NEAT010");
        assert_eq!(Rule::DispatchSiteOwnsLogic.rule_id(), "NEAT031");
    }

    // frob:tests crates/grimble-lints/src/neat/mod.rs::Rule.default_severity
    #[test]
    fn contradicted_claims_warn_and_dispatch_is_advisory() {
        assert_eq!(
            Rule::EffectCeilingExceeded.default_severity(),
            Severity::Warn
        );
        assert_eq!(
            Rule::DispatchSiteOwnsLogic.default_severity(),
            Severity::Advisory
        );
    }

    // frob:tests crates/grimble-lints/src/neat/effects.rs::Atom.word
    #[test]
    fn atom_words_round_trip() {
        for w in ["clock", "rng", "env", "fs", "net", "stdio", "exit"] {
            assert_eq!(Atom::from_word(w).map(Atom::word), Some(w));
        }
        assert_eq!(Atom::from_word("teleport"), None);
    }
}
