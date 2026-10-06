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
//! Known gaps live in one allowlist file ([`ALLOWLIST_PATH`]) with a ticket
//! handle per entry. The allowlist may only shrink: an entry whose rule is
//! now covered, whose rule is no longer registered, or whose ticket handle is
//! malformed fails the test, as does any uncovered rule that is not listed.

// frob:ticket 01M47QTTKVRY3C52CXZBGB8V55

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_rules::{Registry, RuleMeta};
use serde::Deserialize;
use walkdir::WalkDir;

use crate::parse::{Expect, parse_suite};

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
}

impl From<&RuleMeta> for CoverageRule {
    fn from(m: &RuleMeta) -> Self {
        Self {
            id: m.id.to_owned(),
            family: m.family.to_owned(),
        }
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

/// One allowlisted gap: a rule with no corpus yet, owned by a ticket.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gap {
    /// Product namespace of the rule.
    pub product: String,
    /// Rule id.
    pub rule: String,
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
    /// Rules with an `expect=fire` mdtest block.
    pub fire: BTreeSet<String>,
    /// Rules with an `expect=clean` mdtest block.
    pub clean: BTreeSet<String>,
    /// `(family, rule)` pairs with a fixture and a snapshot.
    pub fixtures: BTreeSet<(String, String)>,
}

/// True when `path` lies in a `tests/mdtest` directory.
fn in_mdtest_dir(path: &Path) -> bool {
    let parts: Vec<_> = path.components().map(|c| c.as_os_str()).collect();
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
    let parts: Vec<_> = path.components().map(|c| c.as_os_str()).collect();
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
                            Expect::Fire => corpus.fire.insert(id),
                            Expect::Clean => corpus.clean.insert(id),
                        };
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
        fixtures = corpus.fixtures.len(),
        "coverage corpus scanned"
    );
    corpus
}

/// True when `s` looks like a ticket handle: `~` and seven Crockford characters.
fn is_handle(s: &str) -> bool {
    s.strip_prefix('~').is_some_and(|h| {
        h.len() == 7
            && h.chars()
                .all(|c| c.is_ascii_digit() || c.is_ascii_uppercase())
    })
}

/// The outcome of one product's coverage check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoverageReport {
    /// The product checked.
    pub product: String,
    /// Registered rules examined.
    pub checked: usize,
    /// Uncovered rules that are not allowlisted, with what is missing.
    pub uncovered: Vec<(String, String)>,
    /// Allowlist entries whose rule is now covered (delete them).
    pub stale: Vec<String>,
    /// Allowlist entries naming a rule that is not registered for the product.
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

    /// A multi-line failure text naming every offending rule.
    #[must_use]
    pub fn render(&self) -> String {
        let mut out = format!("{}: rule coverage ({} rules)\n", self.product, self.checked);
        for (rule, missing) in &self.uncovered {
            let _ = writeln!(
                out,
                "  {rule}: no corpus ({missing}); add an mdtest fire/clean pair or a fixture, or allowlist it with a ticket"
            );
        }
        for rule in &self.stale {
            let _ = writeln!(
                out,
                "  {rule}: allowlisted but now covered; delete the allowlist entry"
            );
        }
        for rule in &self.unknown {
            let _ = writeln!(
                out,
                "  {rule}: allowlisted but not a registered {} rule; delete the entry",
                self.product
            );
        }
        for rule in &self.bad_ticket {
            let _ = writeln!(
                out,
                "  {rule}: allowlist entry needs a ticket handle like ~ABCDEFG"
            );
        }
        out
    }
}

/// Compare `rules` (one product) against `corpus` and `allowlist`.
#[must_use]
pub fn analyze(
    product: &str,
    rules: &[CoverageRule],
    corpus: &Corpus,
    allowlist: &Allowlist,
) -> CoverageReport {
    let allowed: BTreeMap<&str, &Gap> = allowlist
        .gap
        .iter()
        .filter(|g| g.product == product)
        .map(|g| (g.rule.as_str(), g))
        .collect();
    let mut report = CoverageReport {
        product: product.to_owned(),
        checked: rules.len(),
        uncovered: Vec::new(),
        stale: Vec::new(),
        unknown: Vec::new(),
        bad_ticket: Vec::new(),
    };
    for rule in rules {
        let fixture = corpus
            .fixtures
            .contains(&(rule.family.clone(), rule.id.clone()));
        let (fire, clean) = (
            corpus.fire.contains(&rule.id),
            corpus.clean.contains(&rule.id),
        );
        let covered = fixture || (fire && clean);
        match (covered, allowed.contains_key(rule.id.as_str())) {
            (true, true) => report.stale.push(rule.id.clone()),
            (false, false) => {
                let missing = match (fire, clean) {
                    (true, false) => "has fire, lacks clean",
                    (false, true) => "has clean, lacks fire",
                    _ => "no mdtest block and no fixture",
                };
                report.uncovered.push((rule.id.clone(), missing.to_owned()));
            }
            _ => {}
        }
    }
    let known: BTreeSet<&str> = rules.iter().map(|r| r.id.as_str()).collect();
    for (id, gap) in &allowed {
        if !known.contains(id) {
            report.unknown.push((*id).to_owned());
        }
        if !is_handle(&gap.ticket) {
            report.bad_ticket.push((*id).to_owned());
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
