//! First NEAT neatness rules: `NEAT010` effect ceiling and `NEAT031` dispatch-site-owns-logic.
//!
//! [`scan`] reads the Rust functions of one file as units, takes their `frob:` claims from the
//! comments above them (`unit`), answers the `effects(unit)` capability as a
//! [`gob_ir::Answer`] ([`effects`]) and reports a claim whose lower bound exceeds its ceiling
//! (`NEAT010`, Warn) and a dispatcher whose branch condition is more than a guard
//! (`NEAT031`, Advisory) (`dispatcher`, docs/design/grimble/rule-families.md section 1.2). A claim the
//! analysis cannot decide is reported unresolved, never clean.
//!
//! Unit discovery runs through the universal model (`gob_symbols::model_of_source_at`): a tree
//! function is a unit only when the model has a function or method unit over it. Claims, the
//! effect vocabulary and the dispatcher weighing stay on tree-sitter (see
//! docs/design/grimble/lint-classification.md).

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP
// frob:ticket 01M59QKE60PDB1GDWTDEBAQ4JG
// frob:ticket 01M6VRR46TR8D8C4TG0GYNK2NK

mod config;
mod dispatcher;
pub mod effects;
mod model;
mod shape;
mod unit;

pub use config::ConfigError;

use gob_languages::{Language, ParseLimits, ParseResult, ParsedTree, parse};
use gob_text::TextRange;

pub use effects::{Atom, EffectSet};
pub use unit::Claim;

/// Which NEAT rule a finding belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Rule {
    /// `NEAT001`: a function spans more lines than `max_fn_lines`.
    FunctionTooLong,
    /// `NEAT002`: a function takes more than `max_params` parameters.
    TooManyParams,
    /// `NEAT003`: a function takes a positional boolean flag.
    BooleanFlagParam,
    /// `NEAT004`: branches nest deeper than `max_depth`.
    NestingTooDeep,
    /// `NEAT005`: cognitive complexity exceeds `max_cognitive`.
    CognitiveComplexity,
    /// `NEAT006`: a loop body exceeds `raw_loop_statements`.
    RawLoop,
    /// `NEAT007`: comments label phases inside one body.
    SectionComment,
    /// `NEAT008`: the same parameters repeat across units.
    ParamObjectCandidate,
    /// `NEAT009`: a bare numeric literal in a body.
    MagicValue,
    /// `NEAT010`: a unit's effects exceed its declared ceiling.
    EffectCeilingExceeded,
    /// `NEAT011`: a public unit declares no effects claim.
    EffectsUndeclared,
    /// `NEAT012`: a unit touches a mutable global.
    HiddenStateRead,
    /// `NEAT013`: an unclaimed unit calls an ambient source.
    AmbientSourceCall,
    /// `NEAT030`: a hook holds more than `hook_statements` statements.
    ThinHook,
    /// `NEAT031`: a dispatcher owns condition logic that belongs to its callee.
    DispatchSiteOwnsLogic,
}

impl Rule {
    /// The rule id.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::FunctionTooLong => "NEAT001",
            Self::TooManyParams => "NEAT002",
            Self::BooleanFlagParam => "NEAT003",
            Self::NestingTooDeep => "NEAT004",
            Self::CognitiveComplexity => "NEAT005",
            Self::RawLoop => "NEAT006",
            Self::SectionComment => "NEAT007",
            Self::ParamObjectCandidate => "NEAT008",
            Self::MagicValue => "NEAT009",
            Self::EffectCeilingExceeded => "NEAT010",
            Self::EffectsUndeclared => "NEAT011",
            Self::HiddenStateRead => "NEAT012",
            Self::AmbientSourceCall => "NEAT013",
            Self::ThinHook => "NEAT030",
            Self::DispatchSiteOwnsLogic => "NEAT031",
        }
    }

    /// The severity the rule ships with.
    pub fn default_severity(self) -> Severity {
        match self {
            Self::FunctionTooLong
            | Self::CognitiveComplexity
            | Self::RawLoop
            | Self::ParamObjectCandidate
            | Self::MagicValue
            | Self::ThinHook
            | Self::DispatchSiteOwnsLogic => Severity::Advisory,
            Self::TooManyParams
            | Self::BooleanFlagParam
            | Self::NestingTooDeep
            | Self::SectionComment
            | Self::EffectCeilingExceeded
            | Self::EffectsUndeclared
            | Self::HiddenStateRead
            | Self::AmbientSourceCall => Severity::Warn,
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

/// Knobs of [`scan`] (`[neat]`); see [`Options::from_config`] for the key spelling.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Options {
    /// Callee vocabulary: `(path, atom)`; a call matches a path or its trailing segments
    /// (`[neat.effects]`).
    pub vocabulary: Vec<(String, Atom)>,
    /// The heaviest branch condition `NEAT031` accepts as a guard (`guard_weight`).
    pub guard_weight: usize,
    /// Path fragments whose files are core: units there without a claim count as `frob:core`
    /// (`core_paths`).
    pub core_paths: Vec<String>,
    /// `NEAT002` parameter limit (`max_params`).
    pub max_params: usize,
    /// `NEAT004` nesting limit (`max_depth`).
    pub max_depth: usize,
    /// `NEAT001` line limit; 0 is off (`max_fn_lines`).
    pub max_fn_lines: usize,
    /// `NEAT005` cognitive complexity limit; 0 is off (`max_cognitive`).
    pub max_cognitive: usize,
    /// `NEAT006` statements a loop body may hold; 0 is off (`raw_loop_statements`).
    pub raw_loop_statements: usize,
    /// `NEAT030` statements a hook may hold (`hook_statements`).
    pub hook_statements: usize,
    /// Name prefixes that make a function a hook (`hook_prefixes`).
    pub hook_prefixes: Vec<String>,
    /// `NEAT008` repeated parameters that make a candidate; 0 is off (`param_object_params`).
    pub param_object_params: usize,
    /// `NEAT009` is on (`magic_values`).
    pub magic_values: bool,
    /// `NEAT011` is on (`require_effects`).
    pub require_effects: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            vocabulary: effects::registry_vocabulary(),
            guard_weight: 2,
            core_paths: Vec::new(),
            max_params: 5,
            max_depth: 3,
            max_fn_lines: 0,
            max_cognitive: 0,
            raw_loop_statements: 0,
            hook_statements: 5,
            hook_prefixes: vec!["on_".to_owned()],
            param_object_params: 3,
            magic_values: false,
            require_effects: false,
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
    /// The universal model of the file could not be built.
    #[error("E-NEAT-MODEL: {0}")]
    Model(String),
}

/// The NEAT findings of `text` parsed as `language`; only Rust has detectors yet.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan(language: Language, text: &str, options: &Options) -> Result<Report, ScanError> {
    scan_at(language, "", text, options)
}

/// [`scan`] for the file at `path`, which `Options::core_paths` may declare core.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan_at(
    language: Language,
    path: &str,
    text: &str,
    options: &Options,
) -> Result<Report, ScanError> {
    if language != Language::Rust {
        tracing::debug!(language = language.name(), "neat: no detectors, skipped");
        return Ok(Report::default());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let core = !path.is_empty() && options.core_paths.iter().any(|c| path.contains(c.as_str()));
    tracing::debug!(path, core, "neat scanning");
    let spans = model::function_spans(text)?;
    Ok(scan_tree(&tree, text, options, core, &spans))
}

/// The NEAT report of a parsed Rust file: claims checked, offenders found, findings in source order.
fn scan_tree(
    tree: &ParsedTree,
    text: &str,
    options: &Options,
    core: bool,
    spans: &[(usize, usize)],
) -> Report {
    let mut units = unit::units(tree.root(), text);
    units.retain(|u| model::gates(spans, u));
    if core {
        for u in units.iter_mut().filter(|u| u.claims.is_empty()) {
            u.claims.push(unit::Claim::Honest("core".to_owned()));
        }
    }
    let globals = shape::mutable_globals(tree.root(), text);
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
        for raw in shape::unit_findings(u, text, options, &globals) {
            report.findings.push(finding(tree, u, raw));
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
    if options.param_object_params > 0 {
        for raw in shape::param_object_candidates(&units, text, options.param_object_params) {
            let owner = units
                .iter()
                .find(|u| u.node == raw.node)
                .expect("raw points at a unit");
            report.findings.push(finding(tree, owner, raw));
        }
    }
    report.findings.sort_by_key(|f| (f.range.start(), f.rule));
    tracing::debug!(
        findings = report.findings.len(),
        claims = report.claims.len(),
        "neat scanned"
    );
    report
}

/// A finding for a shape result in `unit`.
fn finding(tree: &ParsedTree, unit: &unit::Unit<'_>, raw: shape::Raw<'_>) -> Finding {
    Finding {
        rule: raw.rule,
        unit: unit.name.clone(),
        range: tree.node_range(&raw.node),
        line: raw.node.start_position().row + 1,
        message: raw.message,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/neat/mod.rs::Rule.rule_id
    #[test]
    fn rule_ids_follow_rules() {
        assert_eq!(Rule::FunctionTooLong.rule_id(), "NEAT001");
        assert_eq!(Rule::ThinHook.rule_id(), "NEAT030");
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

    // frob:tests crates/grimble-lints/src/neat/effects.rs::Atom.within
    #[test]
    fn a_claim_on_a_parent_atom_covers_its_children() {
        let fs = Atom::from_word("fs").unwrap();
        let net = Atom::from_word("net").unwrap();
        let ceiling: effects::Ceiling = [fs].into_iter().collect();
        assert!(fs.within(&ceiling));
        assert!(!net.within(&ceiling));
        if let Some(read) = Atom::from_word("fs.read") {
            assert!(read.within(&ceiling));
        }
    }

    // frob:tests crates/grimble-lints/src/neat/effects.rs::registry_vocabulary
    #[test]
    fn default_vocabulary_comes_from_the_registry() {
        let vocab = effects::registry_vocabulary();
        assert!(
            vocab
                .iter()
                .any(|(n, a)| n.ends_with("Instant::now") && a.word() == "clock")
        );
        assert!(
            vocab
                .iter()
                .all(|(n, _)| !n.starts_with('.') && !n.ends_with('*'))
        );
    }

    // frob:tests crates/grimble-lints/src/neat/mod.rs::scan
    #[test]
    fn every_adapter_language_scans_without_error() {
        for language in Language::ALL {
            scan(language, "x = 1\n", &Options::default())
                .unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }

    // frob:tests crates/grimble-lints/src/neat/mod.rs::scan
    #[test]
    fn claimed_rust_unit_is_found_through_the_model() {
        let src = "// frob:pure\nfn f() { let _ = std::time::Instant::now(); }\n";
        let r = scan(Language::Rust, src, &Options::default()).expect("parses");
        assert_eq!(r.claims.len(), 1);
        assert_eq!(r.findings[0].rule, Rule::EffectCeilingExceeded);
    }

    // frob:tests crates/grimble-lints/src/neat/mod.rs::scan
    #[test]
    fn marked_dispatcher_is_found_through_the_model() {
        let src = "// frob:dispatcher\nfn d(a: i32) { if f(g(a)) && h(a) { x(); } }\n";
        let r = scan(Language::Rust, src, &Options::default()).expect("parses");
        assert!(
            r.findings
                .iter()
                .any(|f| f.rule == Rule::DispatchSiteOwnsLogic)
        );
    }
}
