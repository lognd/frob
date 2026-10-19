//! Registry-driven rule coverage: every registered rule needs an mdtest pair or a fixture.
//!
//! Modelled on ruff's per-rule fixtures (`docs/design/build-test-ci.md` 6, D98).
//! A rule is covered when, anywhere under `crates/`,
//!
//! - an mdtest suite (`tests/mdtest/**.md`) holds at least one `expect=fire`
//!   and one `expect=clean` block for it, or
//! - a fixture `resources/test/fixtures/<FAMILY>/<RULE>.<ext>` exists with a
//!   diagnostics snapshot `<RULE>.snap` beside it.
//!
//! Beyond fire and clean, the case kinds of `docs/design/testing.md` section 3
//! are derived from the rule's [`RuleMeta`]: an `unresolved` case for every
//! polarity, and a `vacuous` case (`expect=unresolved reason=vacuous`) for a
//! `must_measure` rule. A rule's fire and clean blocks must live in one suite
//! file. The Universal-tier language matrix is checked by [`crate::matrix`].
//!
//! Known gaps live in one allowlist file ([`ALLOWLIST_PATH`]), keyed by
//! (product, rule, case kind) with a ticket handle per entry. The allowlist may
//! only shrink: an entry whose case is now present, whose rule is no longer
//! registered or does not require that kind, or whose ticket handle is
//! malformed fails the test, as does any missing case that is not listed.

// frob:ticket 01M47QTTKVRY3C52CXZBGB8V55

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_rules::{Polarity, Registry, RuleMeta};
use serde::Deserialize;
use walkdir::WalkDir;

use crate::parse::{Expect, parse_suite};

/// Alias rules and the rule that owns their findings, `(alias, target)`.
///
/// An alias is declared so references resolve but is never emitted, so it can
/// have no corpus of its own; it is exempt, its target's coverage standing for it. Mirrors
/// `frob_obligations::COV003_ALIAS_OF`.
pub const RULE_ALIASES: &[(&str, &str)] = &[("COV003", "TEST001")];

/// Allowlist location relative to the workspace root.
pub const ALLOWLIST_PATH: &str = "crates/gob-mdtest/coverage-allowlist.toml";

/// Why the coverage inputs could not be read.
#[derive(Debug, thiserror::Error)]
pub enum CoverageError {
    /// The allowlist file could not be read.
    #[error("cannot read allowlist {path}: {source}")]
    Read {
        /// The allowlist path.
        path: PathBuf,
        /// The underlying error.
        source: std::io::Error,
    },
    /// The allowlist file is not valid TOML of the expected shape.
    #[error("cannot parse allowlist {path}: {message}")]
    Parse {
        /// The allowlist path.
        path: PathBuf,
        /// The parser message.
        message: String,
    },
}

/// The identity of one registered rule as coverage sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoverageRule {
    /// Rule id, e.g. `COV001`.
    pub id: String,
    /// Family prefix, naming the fixture directory.
    pub family: String,
    /// Polarity, selecting the required `unresolved` case.
    pub polarity: Polarity,
    /// True when zero subjects must be a required Unresolved (`vacuous` case).
    pub must_measure: bool,
}

impl CoverageRule {
    /// A rule with the default polarity and no `must_measure`, the family taken from the id.
    #[must_use]
    pub fn new(id: &str) -> Self {
        Self {
            id: id.to_owned(),
            family: id.trim_end_matches(char::is_numeric).to_owned(),
            polarity: Polarity::Pplus,
            must_measure: false,
        }
    }

    /// The case kinds this rule requires, in report order.
    #[must_use]
    pub fn required_kinds(&self) -> Vec<CaseKind> {
        let mut kinds = vec![CaseKind::Fire, CaseKind::Clean, CaseKind::Unresolved];
        if self.must_measure {
            kinds.push(CaseKind::Vacuous);
        }
        kinds
    }
}

impl From<&RuleMeta> for CoverageRule {
    fn from(m: &RuleMeta) -> Self {
        Self {
            id: m.id.to_owned(),
            family: m.family.to_owned(),
            polarity: m.polarity,
            must_measure: m.must_measure,
        }
    }
}

/// One kind of test case a rule must have (`docs/design/testing.md` section 3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CaseKind {
    /// An `expect=fire` case.
    Fire,
    /// An `expect=clean` case, in the same suite file as the fire case.
    Clean,
    /// An `expect=unresolved` case shaped by the rule's polarity.
    Unresolved,
    /// An `expect=unresolved reason=vacuous` case, required of `must_measure` rules.
    Vacuous,
}

impl std::fmt::Display for CaseKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Fire => "fire",
            Self::Clean => "clean",
            Self::Unresolved => "unresolved",
            Self::Vacuous => "vacuous",
        })
    }
}

/// What the `unresolved` case of a rule of this polarity must exercise.
fn unresolved_shape(p: Polarity) -> &'static str {
    match p {
        Polarity::Pplus => {
            "the offender is reachable only through a May edge or sits in an opaque region"
        }
        Polarity::Pminus => {
            "the good thing is present only on a May edge, or the needed answer is Unknown"
        }
        Polarity::P0 => "one side is not Exact",
        Polarity::Pn => "the count is only bounded (lo <= N < hi)",
        Polarity::Pc => "the path runs only through May edges; the poisoned frontier is named",
    }
}

/// The registered rules of one product, in id order.
#[must_use]
pub fn rules_of(registry: &Registry, product: &str) -> Vec<CoverageRule> {
    registry
        .iter()
        .filter(|m| m.product == product)
        .map(CoverageRule::from)
        .collect()
}

/// One allowlisted gap: a rule's missing case kind, owned by a ticket.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gap {
    /// Product namespace of the rule.
    pub product: String,
    /// Rule id.
    pub rule: String,
    /// The missing case kind this entry allows.
    pub kind: CaseKind,
    /// Ticket handle (`~XXXXXXX`) that will close the gap.
    pub ticket: String,
}

/// The parsed allowlist file.
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Allowlist {
    /// Every allowlisted gap.
    #[serde(default)]
    pub gap: Vec<Gap>,
    /// Every allowlisted language-matrix gap (see [`crate::matrix`]).
    #[serde(default)]
    pub matrix_gap: Vec<crate::matrix::MatrixGap>,
}

impl Allowlist {
    /// Read and parse the allowlist at `path`.
    ///
    /// # Errors
    ///
    /// Returns [`CoverageError`] when the file is unreadable or malformed.
    pub fn load(path: &Path) -> Result<Self, CoverageError> {
        let text = std::fs::read_to_string(path).map_err(|source| CoverageError::Read {
            path: path.to_owned(),
            source,
        })?;
        let list: Self = toml::from_str(&text).map_err(|e| CoverageError::Parse {
            path: path.to_owned(),
            message: e.to_string(),
        })?;
        tracing::debug!(path = %path.display(), gaps = list.gap.len(), "coverage allowlist loaded");
        Ok(list)
    }
}

/// What the corpora under `crates/` prove, by rule.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Corpus {
    /// Per rule, the suite files holding an `expect=fire` block.
    pub fire: BTreeMap<String, BTreeSet<PathBuf>>,
    /// Per rule, the suite files holding an `expect=clean` block.
    pub clean: BTreeMap<String, BTreeSet<PathBuf>>,
    /// Rules with an `expect=unresolved` block.
    pub unresolved: BTreeSet<String>,
    /// Rules with an `expect=unresolved reason=vacuous` block.
    pub vacuous: BTreeSet<String>,
    /// `(family, rule)` pairs with a fixture and a snapshot.
    pub fixtures: BTreeSet<(String, String)>,
}

/// True when `path` lies in a `tests/mdtest` directory.
fn in_mdtest_dir(path: &Path) -> bool {
    let parts: Vec<_> = path
        .components()
        .map(std::path::Component::as_os_str)
        .collect();
    parts
        .windows(2)
        .any(|w| w[0] == "tests" && w[1] == "mdtest")
}

/// The `(family, rule)` of a fixture file `.../resources/test/fixtures/FAMILY/RULE.ext` with a snapshot.
fn fixture_key(path: &Path) -> Option<(String, String)> {
    let ext = path.extension()?.to_str()?;
    if ext == "snap" {
        return None;
    }
    let parts: Vec<_> = path
        .components()
        .map(std::path::Component::as_os_str)
        .collect();
    let n = parts.len();
    if n < 5 || parts[n - 5] != "resources" || parts[n - 4] != "test" || parts[n - 3] != "fixtures"
    {
        return None;
    }
    if !path.with_extension("snap").is_file() {
        return None;
    }
    let family = parts[n - 2].to_str()?.to_owned();
    let rule = path.file_stem()?.to_str()?.to_owned();
    Some((family, rule))
}

/// Every mdtest block under `<root>/crates`, in walk order; unreadable or unparsable suites are skipped with a warning.
#[must_use]
pub fn scan_blocks(root: &Path) -> Vec<crate::parse::Block> {
    let walker = WalkDir::new(root.join("crates"))
        .into_iter()
        .filter_entry(|e| e.file_name() != "target");
    let mut out = Vec::new();
    for entry in walker
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_file())
    {
        let path = entry.path();
        if !(path.extension().is_some_and(|x| x == "md") && in_mdtest_dir(path)) {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(path) else {
            tracing::warn!(path = %path.display(), "unreadable mdtest suite skipped");
            continue;
        };
        match parse_suite(&text) {
            Ok(blocks) => out.extend(blocks),
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "unparsable mdtest suite skipped");
            }
        }
    }
    out
}

/// Scan every mdtest suite and fixture under `<root>/crates`.
#[must_use]
pub fn scan_corpus(root: &Path) -> Corpus {
    let mut corpus = Corpus::default();
    let walker = WalkDir::new(root.join("crates"))
        .into_iter()
        .filter_entry(|e| e.file_name() != "target");
    for entry in walker
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_file())
    {
        let path = entry.path();
        if path.extension().is_some_and(|x| x == "md") && in_mdtest_dir(path) {
            let Ok(text) = std::fs::read_to_string(path) else {
                tracing::warn!(path = %path.display(), "unreadable mdtest suite skipped");
                continue;
            };
            match parse_suite(&text) {
                Ok(blocks) => {
                    for b in blocks {
                        let id = b.rule.as_str().to_owned();
                        match b.expect {
                            Expect::Fire => {
                                corpus.fire.entry(id).or_default().insert(path.to_owned());
                            }
                            Expect::Clean => {
                                corpus.clean.entry(id).or_default().insert(path.to_owned());
                            }
                            Expect::Unresolved => {
                                if b.reason
                                    .as_deref()
                                    .is_some_and(|r| r.eq_ignore_ascii_case("vacuous"))
                                {
                                    corpus.vacuous.insert(id.clone());
                                }
                                corpus.unresolved.insert(id);
                            }
                            Expect::NotApplicable => {}
                        }
                    }
                }
                Err(e) => {
                    tracing::warn!(path = %path.display(), error = %e, "unparsable mdtest suite skipped");
                }
            }
        } else if let Some(key) = fixture_key(path) {
            corpus.fixtures.insert(key);
        }
    }
    tracing::debug!(
        fire = corpus.fire.len(),
        clean = corpus.clean.len(),
        unresolved = corpus.unresolved.len(),
        fixtures = corpus.fixtures.len(),
        "coverage corpus scanned"
    );
    corpus
}

/// True when `s` looks like a ticket handle: `~` and seven Crockford characters.
pub(crate) fn is_handle(s: &str) -> bool {
    s.strip_prefix('~').is_some_and(|h| {
        h.len() == 7
            && h.chars()
                .all(|c| c.is_ascii_digit() || c.is_ascii_uppercase())
    })
}

/// A required case a rule lacks and the allowlist does not cover.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Missing {
    /// Rule id.
    pub rule: String,
    /// The missing case kind.
    pub kind: CaseKind,
    /// What is missing, naming the polarity for an `unresolved` case.
    pub detail: String,
}

/// The outcome of one product's coverage check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoverageReport {
    /// The product checked.
    pub product: String,
    /// Registered rules examined.
    pub checked: usize,
    /// Required cases that are absent and not allowlisted.
    pub uncovered: Vec<Missing>,
    /// Allowlist entries (`RULE [kind]`) whose case is now present (delete them).
    pub stale: Vec<String>,
    /// Allowlist entries naming a rule not registered for the product, or a kind it does not require.
    pub unknown: Vec<String>,
    /// Allowlist entries without a valid ticket handle.
    pub bad_ticket: Vec<String>,
}

impl CoverageReport {
    /// True when nothing is wrong.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.uncovered.is_empty()
            && self.stale.is_empty()
            && self.unknown.is_empty()
            && self.bad_ticket.is_empty()
    }

    /// A multi-line failure text naming every offending rule and case kind.
    #[must_use]
    pub fn render(&self) -> String {
        let mut out = format!("{}: rule coverage ({} rules)\n", self.product, self.checked);
        for m in &self.uncovered {
            let _ = writeln!(
                out,
                "  {} {}: missing `{}` case; add it to the rule's suite or allowlist it as a [[gap]] with a ticket",
                m.rule, m.detail, m.kind
            );
        }
        for entry in &self.stale {
            let _ = writeln!(
                out,
                "  {entry}: allowlisted but now present; delete the allowlist entry"
            );
        }
        for entry in &self.unknown {
            let _ = writeln!(
                out,
                "  {entry}: allowlisted but not a case a registered {} rule requires; delete the entry",
                self.product
            );
        }
        for entry in &self.bad_ticket {
            let _ = writeln!(
                out,
                "  {entry}: allowlist entry needs a ticket handle like ~ABCDEFG"
            );
        }
        out
    }
}

/// The required kinds of `rule` that `corpus` does not provide, with a detail line each.
fn missing_kinds(rule: &CoverageRule, corpus: &Corpus) -> Vec<(CaseKind, String)> {
    if RULE_ALIASES.iter().any(|(alias, _)| *alias == rule.id) {
        tracing::debug!(alias = %rule.id, "alias rule is never emitted; exempt from corpus");
        return Vec::new();
    }
    let fixture = corpus
        .fixtures
        .contains(&(rule.family.clone(), rule.id.clone()));
    let fire_files = corpus.fire.get(&rule.id);
    let clean_files = corpus.clean.get(&rule.id);
    let paired = fire_files
        .zip(clean_files)
        .is_some_and(|(f, c)| f.intersection(c).next().is_some());
    let sym = rule.polarity.symbol();
    let mut out = Vec::new();
    for kind in rule.required_kinds() {
        let detail = match kind {
            CaseKind::Fire if !fixture && fire_files.is_none() => Some(if clean_files.is_some() {
                "has clean, lacks fire".to_owned()
            } else {
                "no mdtest block and no fixture".to_owned()
            }),
            CaseKind::Clean if !fixture && !paired => Some(if clean_files.is_some() {
                "fire and clean are in different suite files".to_owned()
            } else if fire_files.is_some() {
                "has fire, lacks clean".to_owned()
            } else {
                "no mdtest block and no fixture".to_owned()
            }),
            CaseKind::Unresolved if !corpus.unresolved.contains(&rule.id) => Some(format!(
                "{sym} unresolved ({})",
                unresolved_shape(rule.polarity)
            )),
            CaseKind::Vacuous if !corpus.vacuous.contains(&rule.id) => Some(
                "must_measure vacuous (zero subjects is Unresolved reason=vacuous, never clean)"
                    .to_owned(),
            ),
            _ => None,
        };
        if let Some(d) = detail {
            out.push((kind, d));
        }
    }
    out
}

/// Compare `rules` (one product) against `corpus` and `allowlist`.
///
/// A rule listed in [`RULE_ALIASES`] is exempt: its target's coverage (or
/// allowlist entry) stands for it.
#[must_use]
pub fn analyze(
    product: &str,
    rules: &[CoverageRule],
    corpus: &Corpus,
    allowlist: &Allowlist,
) -> CoverageReport {
    let allowed: Vec<&Gap> = allowlist
        .gap
        .iter()
        .filter(|g| g.product == product)
        .collect();
    let mut report = CoverageReport {
        product: product.to_owned(),
        checked: rules.len(),
        uncovered: Vec::new(),
        stale: Vec::new(),
        unknown: Vec::new(),
        bad_ticket: Vec::new(),
    };
    let mut seen: BTreeSet<(&str, CaseKind)> = BTreeSet::new();
    for rule in rules {
        let missing = missing_kinds(rule, corpus);
        for kind in rule.required_kinds() {
            let is_missing = missing.iter().find(|(k, _)| *k == kind);
            let listed = allowed.iter().any(|g| g.rule == rule.id && g.kind == kind);
            match (is_missing, listed) {
                (None, true) => report.stale.push(format!("{} [{kind}]", rule.id)),
                (Some((_, detail)), false) => report.uncovered.push(Missing {
                    rule: rule.id.clone(),
                    kind,
                    detail: detail.clone(),
                }),
                _ => {}
            }
            seen.insert((rule.id.as_str(), kind));
        }
    }
    for gap in &allowed {
        let key = format!("{} [{}]", gap.rule, gap.kind);
        if !seen.contains(&(gap.rule.as_str(), gap.kind)) {
            report.unknown.push(key.clone());
        }
        if !is_handle(&gap.ticket) {
            report.bad_ticket.push(key);
        }
    }
    tracing::info!(
        product,
        checked = report.checked,
        uncovered = report.uncovered.len(),
        passed = report.passed(),
        "rule coverage analysed"
    );
    report
}

/// Check the global registry's rules of `product` against the workspace at `root`.
///
/// # Errors
///
/// Returns [`CoverageError`] when the allowlist cannot be read.
pub fn check_product(root: &Path, product: &str) -> Result<CoverageReport, CoverageError> {
    let allowlist = Allowlist::load(&root.join(ALLOWLIST_PATH))?;
    let rules = rules_of(Registry::global(), product);
    Ok(analyze(product, &rules, &scan_corpus(root), &allowlist))
}

/// Test entry point: panic naming every uncovered rule of `product`.
///
/// `compile_time_manifest` is the caller's `env!("CARGO_MANIFEST_DIR")`; the
/// workspace root is two levels above it (`crates/<crate>`).
///
/// # Panics
///
/// Panics when coverage fails or the allowlist is unreadable.
pub fn assert_product_coverage(compile_time_manifest: &str, product: &str) {
    let root = crate::manifest_dir(compile_time_manifest)
        .ancestors()
        .nth(2)
        .expect("crate lives two levels below the workspace root")
        .to_owned();
    let report = check_product(&root, product).unwrap_or_else(|e| panic!("{e}"));
    assert!(report.passed(), "{}", report.render());
}
