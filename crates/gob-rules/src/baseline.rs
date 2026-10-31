//! The baseline store `frob-baseline.toml` (rules.md section 6.1.2, ~7FDF275).
//!
//! One sorted table per rule; a key is a [`Fingerprint`] in lowercase hex. The file only shrinks:
//! [`Baseline::adopt`] is the single writer that adds keys (and it creates a whole table),
//! [`Baseline::prune`] removes keys whose finding is gone, and [`growth`] (BASE001) and
//! [`dead_tables`] (BASE002) judge a head file against the base tip and the ticket ledger.

// frob:ticket 01M5XMJH35MV9Z2PFF27FDF275

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use serde::{Deserialize, Serialize};

use crate::exception::{Exception, ExceptionKind};
use crate::finding::{Finding, Fingerprint};
use crate::id::RuleId;
use crate::meta::Severity;

/// File name of the baseline store at the repository root.
pub const BASELINE_FILE: &str = "frob-baseline.toml";

/// File name of the superseded ratchet lock that [`migrate_ratchet_lock`] converts.
pub const RATCHET_LOCK_FILE: &str = "frob-ratchet.lock.json";

/// The only format version this code reads and writes.
pub const BASELINE_VERSION: u32 = 1;

/// Why a baseline file could not be read, written or changed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum BaselineError {
    /// The text carries merge-conflict markers; never treated as empty.
    #[error(
        "{BASELINE_FILE} has merge-conflict markers at line {line}; resolve them and rerun `frob baseline prune`"
    )]
    Conflict {
        /// One-based line of the first marker.
        line: usize,
    },
    /// The text is not valid baseline TOML.
    #[error("{BASELINE_FILE} is not valid: {0}")]
    Parse(String),
    /// The file exists but could not be read.
    #[error("{BASELINE_FILE} is not readable: {0}")]
    Io(String),
    /// The file declares a version this code does not know.
    #[error("{BASELINE_FILE} version {0} is not supported (expected {BASELINE_VERSION})")]
    Version(u32),
    /// A table key is not a rule id.
    #[error("{BASELINE_FILE} table `{0}` is not a rule id")]
    BadRule(String),
    /// A table lacks a required `reason` or `ticket`.
    #[error("{BASELINE_FILE} table `{rule}` needs a non-empty `{field}`")]
    Missing {
        /// The table's rule.
        rule: String,
        /// The empty field.
        field: &'static str,
    },
    /// A key is not a 64-digit lowercase hex fingerprint.
    #[error("{BASELINE_FILE} table `{rule}` has a malformed key `{key}`")]
    BadKey {
        /// The table's rule.
        rule: String,
        /// The offending key.
        key: String,
    },
    /// `adopt` found a table already present.
    #[error("rule {0} already has a baseline table; adopt creates a table only once")]
    AlreadyAdopted(String),
    /// `adopt` had no finding to record.
    #[error("rule {0} has no findings to adopt; an empty table is not created")]
    NothingToAdopt(String),
    /// Migration found a baseline already in place.
    #[error("{BASELINE_FILE} already exists; the ratchet lock migrates once")]
    AlreadyMigrated,
    /// The ratchet lock is not the JSON shape migration reads.
    #[error("{RATCHET_LOCK_FILE} is not readable: {0}")]
    BadLock(String),
}

/// One rule's pool of tolerated findings.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuleTable {
    /// Why the rule was adopted.
    pub reason: String,
    /// The burn-down ticket (BASE002 needs it live).
    pub ticket: String,
    /// Finding fingerprints (lowercase hex), kept sorted and unique.
    pub findings: Vec<String>,
}

/// The parsed `frob-baseline.toml`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Baseline {
    /// Format version, always [`BASELINE_VERSION`].
    pub version: u32,
    /// One table per rule id, sorted by id.
    #[serde(default)]
    pub rules: BTreeMap<String, RuleTable>,
}

impl Default for Baseline {
    fn default() -> Self {
        Self {
            version: BASELINE_VERSION,
            rules: BTreeMap::new(),
        }
    }
}

/// What a prune removed.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PruneReport {
    /// `(rule, key)` pairs removed because the finding no longer occurs.
    pub removed: Vec<(String, String)>,
    /// Rules whose table became empty and was deleted.
    pub tables_deleted: Vec<String>,
}

/// The evidence a prune needs from one full, unscoped run.
#[derive(Debug, Clone, Default)]
pub struct PruneInput {
    /// Fingerprints (hex) of every finding of the run, Unresolved ones included.
    pub live: BTreeSet<String>,
    /// Rule ids that evaluated (not skipped, not a version bump).
    pub evaluated: BTreeSet<String>,
    /// True only for a full, unscoped run; anything else prunes nothing.
    pub full_run: bool,
}

/// One BASE001 violation: a table that gained keys or changed ticket against the base tip.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Growth {
    /// The rule whose table grew.
    pub rule: String,
    /// Keys present at head and absent from the base table.
    pub added: Vec<String>,
    /// `(base, head)` when the ticket changed.
    pub ticket_changed: Option<(String, String)>,
}

/// Whether a burn-down ticket can still carry its debt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TicketLife {
    /// Open, or closed/dropped with a live successor.
    Live,
    /// Closed or dropped with no successor.
    Dead,
    /// The ledger could not say; BASE002 reports Unresolved, never clean.
    Unknown,
}

fn conflict_line(text: &str) -> Option<usize> {
    text.lines()
        .position(|l| l.starts_with("<<<<<<<") || l.starts_with(">>>>>>>") || l == "=======")
        .map(|i| i + 1)
}

fn is_key(k: &str) -> bool {
    k.len() == 64 && k.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

fn quote(s: &str) -> String {
    toml::Value::String(s.to_owned()).to_string()
}

impl Baseline {
    /// Parse and validate `text`; a conflicted or malformed file is an error, never empty.
    ///
    /// # Errors
    /// Conflict markers, invalid TOML, an unknown version, a bad rule id, key or empty field.
    pub fn parse(text: &str) -> Result<Self, BaselineError> {
        if let Some(line) = conflict_line(text) {
            tracing::error!(line, "baseline has merge-conflict markers");
            return Err(BaselineError::Conflict { line });
        }
        let mut b: Self =
            toml::from_str(text).map_err(|e| BaselineError::Parse(e.message().to_owned()))?;
        if b.version != BASELINE_VERSION {
            return Err(BaselineError::Version(b.version));
        }
        for (rule, table) in &mut b.rules {
            if rule.parse::<RuleId>().is_err() {
                return Err(BaselineError::BadRule(rule.clone()));
            }
            for (field, value) in [("reason", &table.reason), ("ticket", &table.ticket)] {
                if value.trim().is_empty() {
                    return Err(BaselineError::Missing {
                        rule: rule.clone(),
                        field,
                    });
                }
            }
            if let Some(key) = table.findings.iter().find(|k| !is_key(k)) {
                return Err(BaselineError::BadKey {
                    rule: rule.clone(),
                    key: key.clone(),
                });
            }
            table.findings.sort();
            table.findings.dedup();
        }
        tracing::debug!(tables = b.rules.len(), "baseline parsed");
        Ok(b)
    }

    /// The canonical text: sorted tables, one key per line, so diffs and merges are line-local.
    pub fn render(&self) -> String {
        let mut out = format!("version = {}\n", self.version);
        for (rule, t) in &self.rules {
            let mut keys: Vec<&String> = t.findings.iter().collect();
            keys.sort();
            keys.dedup();
            let _ = write!(
                out,
                "\n[rules.{rule}]\nreason = {}\nticket = {}\nfindings = [\n",
                quote(&t.reason),
                quote(&t.ticket)
            );
            for k in keys {
                let _ = writeln!(out, "  {},", quote(k));
            }
            out.push_str("]\n");
        }
        out
    }

    /// Total number of baselined keys.
    pub fn key_count(&self) -> usize {
        self.rules.values().map(|t| t.findings.len()).sum()
    }

    /// Create the table for `rule` from `findings` (the only writer that adds keys).
    ///
    /// Refuses when the rule already has a table or no Error finding of the rule is given.
    ///
    /// # Errors
    /// `AlreadyAdopted`, `NothingToAdopt`, or `Missing` for a blank reason or ticket.
    pub fn adopt(
        &mut self,
        rule: &RuleId,
        reason: &str,
        ticket: &str,
        findings: &[Finding],
    ) -> Result<usize, BaselineError> {
        let id = rule.as_str().to_owned();
        if self.rules.contains_key(&id) {
            return Err(BaselineError::AlreadyAdopted(id));
        }
        for (field, value) in [("reason", reason), ("ticket", ticket)] {
            if value.trim().is_empty() {
                return Err(BaselineError::Missing { rule: id, field });
            }
        }
        let keys: BTreeSet<String> = findings
            .iter()
            .filter(|f| f.rule == *rule && f.severity == Severity::Error)
            .map(|f| f.fingerprint.to_hex())
            .collect();
        if keys.is_empty() {
            return Err(BaselineError::NothingToAdopt(id));
        }
        let n = keys.len();
        tracing::info!(rule = %id, keys = n, ticket, "baseline adopted");
        self.rules.insert(
            id,
            RuleTable {
                reason: reason.to_owned(),
                ticket: ticket.to_owned(),
                findings: keys.into_iter().collect(),
            },
        );
        Ok(n)
    }

    /// True when `f` is an Error whose fingerprint is in its rule's list (Unresolved never is).
    pub fn covers(&self, f: &Finding) -> bool {
        f.severity == Severity::Error
            && self
                .rules
                .get(f.rule.as_str())
                .is_some_and(|t| t.findings.binary_search(&f.fingerprint.to_hex()).is_ok())
    }

    /// Split `findings` into `(live, baselined)`; baselined ones are muted but never dropped.
    pub fn partition(&self, findings: Vec<Finding>) -> (Vec<Finding>, Vec<Finding>) {
        let (base, live): (Vec<_>, Vec<_>) = findings.into_iter().partition(|f| self.covers(f));
        tracing::debug!(
            live = live.len(),
            baselined = base.len(),
            "baseline applied"
        );
        (live, base)
    }

    #[allow(
        clippy::disallowed_methods,
        reason = "frob-baseline.toml is the product's own store, not walked content"
    )]
    /// Read `<root>/frob-baseline.toml`; a missing file is an empty baseline, anything else unreadable is an error.
    ///
    /// # Errors
    /// [`BaselineError::Io`] for an unreadable file, else as [`Baseline::parse`].
    pub fn load(root: &std::path::Path) -> Result<Self, BaselineError> {
        match std::fs::read_to_string(root.join(BASELINE_FILE)) {
            Ok(text) => Self::parse(&text),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!("no baseline file; nothing is baselined");
                Ok(Self::default())
            }
            Err(e) => Err(BaselineError::Io(e.to_string())),
        }
    }

    /// Split `findings` into `(live, muted)`, each muted finding paired with the `Baseline` exception of its rule table.
    ///
    /// A key is the REPORTED fingerprint (rule, file path, message), which the pipeline assigns after exceptions
    /// resolve; `anchor_of` names the file path so the key is recomputed the same way here.
    pub fn mute(
        &self,
        findings: Vec<Finding>,
        anchor_of: impl Fn(&Finding) -> String,
    ) -> (Vec<Finding>, Vec<(Finding, Exception)>) {
        let mut live = Vec::new();
        let mut muted = Vec::new();
        for f in findings {
            let mut probe = f.clone();
            probe.fingerprint = Fingerprint::compute(&f.rule, &anchor_of(&f), &f.message);
            match self
                .rules
                .get(f.rule.as_str())
                .filter(|_| self.covers(&probe))
            {
                Some(table) => {
                    let exception = Exception {
                        kind: ExceptionKind::Baseline,
                        rule: f.rule.clone(),
                        reason: table.reason.clone(),
                        ticket: Some(table.ticket.clone()),
                        until: None,
                    };
                    muted.push((f, exception));
                }
                None => live.push(f),
            }
        }
        tracing::debug!(
            live = live.len(),
            baselined = muted.len(),
            "baseline applied"
        );
        (live, muted)
    }

    /// Remaining baselined keys per rule, for the per-rule total in the report.
    pub fn remaining(&self) -> BTreeMap<&str, usize> {
        self.rules
            .iter()
            .map(|(r, t)| (r.as_str(), t.findings.len()))
            .collect()
    }

    /// Remove keys whose finding is gone; never adds. Only a full run on an evaluated rule prunes.
    pub fn prune(&mut self, input: &PruneInput) -> PruneReport {
        let mut report = PruneReport::default();
        if !input.full_run {
            tracing::debug!("prune skipped: not a full unscoped run");
            return report;
        }
        for (rule, table) in &mut self.rules {
            if !input.evaluated.contains(rule) {
                continue;
            }
            table.findings.retain(|k| {
                let keep = input.live.contains(k);
                if !keep {
                    report.removed.push((rule.clone(), k.clone()));
                }
                keep
            });
        }
        self.rules.retain(|rule, t| {
            let keep = !t.findings.is_empty();
            if !keep {
                report.tables_deleted.push(rule.clone());
            }
            keep
        });
        tracing::info!(
            removed = report.removed.len(),
            tables = report.tables_deleted.len(),
            "baseline pruned"
        );
        report
    }

    /// Drop from `self` the keys the `base` tip no longer lists (shrinking is monotone), so a
    /// branch that still lists a key the base already pruned loses it silently.
    pub fn intersect_base(&mut self, base: &Self) {
        for (rule, t) in &mut self.rules {
            if let Some(b) = base.rules.get(rule) {
                t.findings.retain(|k| b.findings.contains(k));
            }
        }
    }
}

/// BASE001: tables of `head` that gained a key or changed `ticket` against the `base` tip.
///
/// A table absent from `base` is the `adopt` creation event and is not growth.
pub fn growth(base: &Baseline, head: &Baseline) -> Vec<Growth> {
    let mut out = Vec::new();
    for (rule, h) in &head.rules {
        let Some(b) = base.rules.get(rule) else {
            continue;
        };
        let known: BTreeSet<&String> = b.findings.iter().collect();
        let added: Vec<String> = h
            .findings
            .iter()
            .filter(|k| !known.contains(k))
            .cloned()
            .collect();
        let ticket_changed = (b.ticket != h.ticket).then(|| (b.ticket.clone(), h.ticket.clone()));
        if !added.is_empty() || ticket_changed.is_some() {
            out.push(Growth {
                rule: rule.clone(),
                added,
                ticket_changed,
            });
        }
    }
    out
}

/// BASE002: `(rule, ticket, life)` for every table whose ticket is not [`TicketLife::Live`].
pub fn dead_tables(
    head: &Baseline,
    life: impl Fn(&str) -> TicketLife,
) -> Vec<(String, String, TicketLife)> {
    head.rules
        .iter()
        .filter_map(|(rule, t)| match life(&t.ticket) {
            TicketLife::Live => None,
            other => Some((rule.clone(), t.ticket.clone(), other)),
        })
        .collect()
}

/// Convert the old ratchet lock once, keeping its keys.
///
/// Reads `{"<RULE>": ["<key>", ..]}` at the top level or under `"pools"`/`"rules"`. Refuses when
/// a baseline `existing` is already in place; the caller deletes the lock after writing.
///
/// # Errors
/// `AlreadyMigrated` when a baseline exists, `BadLock` when the lock is not recognisable.
pub fn migrate_ratchet_lock(
    lock_json: &str,
    existing: Option<&Baseline>,
    reason: &str,
    ticket: &str,
) -> Result<Baseline, BaselineError> {
    if existing.is_some() {
        return Err(BaselineError::AlreadyMigrated);
    }
    let v: serde_json::Value =
        serde_json::from_str(lock_json).map_err(|e| BaselineError::BadLock(e.to_string()))?;
    let root = ["pools", "rules"]
        .iter()
        .find_map(|k| v.get(*k))
        .unwrap_or(&v);
    let obj = root
        .as_object()
        .ok_or_else(|| BaselineError::BadLock("expected a JSON object".into()))?;
    let mut b = Baseline::default();
    for (rule, keys) in obj {
        let Some(arr) = keys.as_array() else {
            continue;
        };
        let mut set = BTreeSet::new();
        for k in arr {
            let s = k
                .as_str()
                .ok_or_else(|| BaselineError::BadLock(format!("non-string key in {rule}")))?;
            set.insert(s.to_owned());
        }
        if set.is_empty() {
            continue;
        }
        b.rules.insert(
            rule.clone(),
            RuleTable {
                reason: reason.to_owned(),
                ticket: ticket.to_owned(),
                findings: set.into_iter().collect(),
            },
        );
    }
    // Round-trip through the validator so a malformed lock fails here, not at the next check.
    let b = Baseline::parse(&b.render())?;
    tracing::info!(
        tables = b.rules.len(),
        keys = b.key_count(),
        "ratchet lock migrated"
    );
    Ok(b)
}

/// What BASE001 and BASE002 read from the product host: both baselines and ticket liveness.
pub trait BaselineHost {
    /// The baseline in the working tree, `None` when the file is absent.
    fn baseline_head(&self) -> Option<&Baseline>;
    /// The baseline at the base tip, `None` when the base has no file.
    fn baseline_base(&self) -> Option<&Baseline>;
    /// Whether `ticket` names a live (open) ticket.
    fn ticket_life(&self, ticket: &str) -> TicketLife;
}
