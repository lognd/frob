//! Persistent history behind the precision ledger: fixed findings across runs and reasoned dismissals.
//!
//! One run cannot tell that a finding was fixed; two runs can. The history keeps the fingerprints
//! left standing by the last recorded run, and a finding that stood then and is gone now (while its
//! rule was evaluated again) counts as fixed. Dismissals are recorded by hand, each with a reason
//! that passes [`check_reason`]. Both feed [`PrecisionLedger::add_fixed`] and
//! [`PrecisionLedger::add_dismissed`] through [`PrecisionHistory::feed`].

// frob:ticket 01M4M8EJA0RAXE090V8X84157K

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::finding::Finding;
use crate::id::RuleId;
use crate::precision::PrecisionLedger;
use crate::reason::{ReasonPolicy, ReasonRejected, check_reason};

/// File name of the history inside the state directory.
pub const HISTORY_FILE: &str = "precision-history.json";

/// Why the history could not be read, written or extended.
#[derive(Debug, thiserror::Error)]
pub enum HistoryError {
    /// The history file could not be read or written.
    #[error("precision history {path}: {source}")]
    Io {
        /// The file.
        path: PathBuf,
        /// The cause.
        source: std::io::Error,
    },
    /// The history file is not valid history JSON.
    #[error("precision history {path} is malformed: {source}")]
    Malformed {
        /// The file.
        path: PathBuf,
        /// The cause.
        source: serde_json::Error,
    },
    /// A dismissal was given without an acceptable reason.
    #[error("a dismissal needs a reason: {0}")]
    Reason(#[from] ReasonRejected),
}

/// One finding dismissed as not useful, with the reason that justified it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Dismissal {
    /// The rule that reported it.
    pub rule: String,
    /// Hex fingerprint of the dismissed finding.
    pub fingerprint: String,
    /// Why it was not useful.
    pub reason: String,
}

/// What persists between runs: standing fingerprints, fixed counts and dismissals.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PrecisionHistory {
    /// Fingerprints left standing by the last recorded run, per rule.
    #[serde(default)]
    standing: BTreeMap<String, BTreeSet<String>>,
    /// Findings seen fixed so far, per rule.
    #[serde(default)]
    fixed: BTreeMap<String, u32>,
    /// Dismissals, one per fingerprint.
    #[serde(default)]
    dismissals: Vec<Dismissal>,
}

impl PrecisionHistory {
    /// The history file under `state_dir`.
    pub fn path(state_dir: &Path) -> PathBuf {
        state_dir.join(HISTORY_FILE)
    }

    #[expect(
        clippy::disallowed_methods,
        reason = "the history is the product's own state file, not walked content"
    )]
    /// Read the history under `state_dir`; an absent file is an empty history.
    ///
    /// # Errors
    ///
    /// [`HistoryError::Io`] on a read failure, [`HistoryError::Malformed`] on bad JSON.
    pub fn load(state_dir: &Path) -> Result<Self, HistoryError> {
        let path = Self::path(state_dir);
        let text = match std::fs::read_to_string(&path) {
            Ok(text) => text,
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!(path = %path.display(), "no precision history yet");
                return Ok(Self::default());
            }
            Err(source) => return Err(HistoryError::Io { path, source }),
        };
        serde_json::from_str(&text).map_err(|source| HistoryError::Malformed { path, source })
    }

    /// Write the history under `state_dir`, creating the directory.
    ///
    /// # Errors
    ///
    /// [`HistoryError::Io`] when the directory or file cannot be written.
    pub fn save(&self, state_dir: &Path) -> Result<(), HistoryError> {
        let path = Self::path(state_dir);
        let io = |source| HistoryError::Io {
            path: path.clone(),
            source,
        };
        std::fs::create_dir_all(state_dir).map_err(io)?;
        let text =
            serde_json::to_string_pretty(self).map_err(|source| HistoryError::Malformed {
                path: path.clone(),
                source,
            })?;
        gob_fs::write_atomic(&path, text.as_bytes()).map_err(io)?;
        tracing::debug!(path = %path.display(), "precision history saved");
        Ok(())
    }

    /// Record one run: standing findings that vanished while their rule was evaluated count as fixed.
    ///
    /// `evaluated` are the rules this run examined; a rule outside it (a filtered or failed run)
    /// keeps its previous standing set untouched. Dismissed findings are never counted as fixed.
    pub fn record_run(&mut self, open: &[Finding], evaluated: &BTreeSet<String>) {
        let mut now: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for f in open {
            now.entry(f.rule.to_string())
                .or_default()
                .insert(f.fingerprint.to_hex());
        }
        let dismissed: BTreeSet<&str> = self
            .dismissals
            .iter()
            .map(|d| d.fingerprint.as_str())
            .collect();
        let mut next = BTreeMap::new();
        for (rule, before) in std::mem::take(&mut self.standing) {
            if !evaluated.contains(&rule) {
                next.insert(rule, before);
                continue;
            }
            let still = now.get(&rule);
            let gone = before
                .iter()
                .filter(|fp| {
                    !still.is_some_and(|s| s.contains(*fp)) && !dismissed.contains(fp.as_str())
                })
                .count();
            if gone > 0 {
                let n = u32::try_from(gone).unwrap_or(u32::MAX);
                tracing::info!(%rule, fixed = n, "findings fixed since the last run");
                let total = self.fixed.entry(rule).or_default();
                *total = total.saturating_add(n);
            }
        }
        for (rule, fps) in now {
            next.insert(rule, fps);
        }
        self.standing = next;
    }

    /// Record `finding` of `rule` as dismissed for `reason`; a repeat of the same fingerprint is a no-op.
    ///
    /// # Errors
    ///
    /// [`HistoryError::Reason`] when `reason` fails the default [`ReasonPolicy`].
    pub fn dismiss(
        &mut self,
        rule: &RuleId,
        fingerprint: &str,
        reason: &str,
    ) -> Result<(), HistoryError> {
        check_reason(reason, &ReasonPolicy::default())?;
        if self.dismissals.iter().any(|d| d.fingerprint == fingerprint) {
            tracing::debug!(%rule, fingerprint, "already dismissed");
            return Ok(());
        }
        tracing::info!(%rule, fingerprint, "finding dismissed");
        self.dismissals.push(Dismissal {
            rule: rule.to_string(),
            fingerprint: fingerprint.to_owned(),
            reason: reason.trim().to_owned(),
        });
        Ok(())
    }

    /// The recorded dismissals.
    pub fn dismissals(&self) -> &[Dismissal] {
        &self.dismissals
    }

    /// Add the fixed and dismissed counts to `ledger`.
    pub fn feed(&self, ledger: &mut PrecisionLedger) {
        for (rule, n) in &self.fixed {
            if let Ok(id) = rule.parse::<RuleId>() {
                ledger.add_fixed(&id, *n);
            }
        }
        let mut dismissed: BTreeMap<&str, u32> = BTreeMap::new();
        for d in &self.dismissals {
            *dismissed.entry(d.rule.as_str()).or_default() += 1;
        }
        for (rule, n) in dismissed {
            if let Ok(id) = rule.parse::<RuleId>() {
                ledger.add_dismissed(&id, n);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::meta::Severity;

    fn id(s: &str) -> RuleId {
        s.parse().unwrap()
    }

    fn finding(rule: &str, anchor: &str) -> Finding {
        Finding::new(id(rule), Severity::Error, None, "m", anchor)
    }

    fn eval(rules: &[&str]) -> BTreeSet<String> {
        rules.iter().map(|r| (*r).to_owned()).collect()
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.record_run
    #[test]
    fn fixed_findings_accumulate_across_runs_and_feed_the_ledger() {
        let dir = tempfile::tempdir().unwrap();
        let mut h = PrecisionHistory::default();
        h.record_run(
            &[finding("COV001", "a"), finding("COV001", "b")],
            &eval(&["COV001"]),
        );
        h.save(dir.path()).unwrap();

        let mut h = PrecisionHistory::load(dir.path()).unwrap();
        h.record_run(&[finding("COV001", "b")], &eval(&["COV001"]));
        h.save(dir.path()).unwrap();

        let mut h = PrecisionHistory::load(dir.path()).unwrap();
        h.record_run(&[], &eval(&["COV001"]));
        h.save(dir.path()).unwrap();

        let h = PrecisionHistory::load(dir.path()).unwrap();
        let mut ledger = PrecisionLedger::new();
        h.feed(&mut ledger);
        assert_eq!(ledger.tally(&id("COV001")).fixed, 2);
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.record_run
    #[test]
    fn a_rule_that_was_not_evaluated_does_not_report_fixes() {
        let mut h = PrecisionHistory::default();
        h.record_run(&[finding("COV001", "a")], &eval(&["COV001"]));
        h.record_run(&[], &eval(&["DOC001"]));
        let mut ledger = PrecisionLedger::new();
        h.feed(&mut ledger);
        assert_eq!(ledger.tally(&id("COV001")).fixed, 0);
        h.record_run(&[], &eval(&["COV001"]));
        h.feed(&mut ledger);
        assert_eq!(ledger.tally(&id("COV001")).fixed, 1);
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.dismiss
    #[test]
    fn a_dismissal_needs_a_reason_and_persists_into_the_ledger() {
        let dir = tempfile::tempdir().unwrap();
        let f = finding("WEB001", "x");
        let fp = f.fingerprint.to_hex();
        let mut h = PrecisionHistory::default();
        assert!(matches!(
            h.dismiss(&id("WEB001"), &fp, "  "),
            Err(HistoryError::Reason(_))
        ));
        assert!(h.dismissals().is_empty());
        h.dismiss(
            &id("WEB001"),
            &fp,
            "the sink is sanitized upstream by the gateway",
        )
        .unwrap();
        h.dismiss(
            &id("WEB001"),
            &fp,
            "the sink is sanitized upstream by the gateway",
        )
        .unwrap();
        h.save(dir.path()).unwrap();

        let h = PrecisionHistory::load(dir.path()).unwrap();
        let mut ledger = PrecisionLedger::new();
        h.feed(&mut ledger);
        assert_eq!(ledger.tally(&id("WEB001")).dismissed, 1);
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.record_run
    #[test]
    fn a_dismissed_finding_that_disappears_is_not_also_counted_fixed() {
        let f = finding("WEB001", "x");
        let mut h = PrecisionHistory::default();
        h.record_run(std::slice::from_ref(&f), &eval(&["WEB001"]));
        h.dismiss(
            &id("WEB001"),
            &f.fingerprint.to_hex(),
            "the sink is sanitized upstream",
        )
        .unwrap();
        h.record_run(&[], &eval(&["WEB001"]));
        let mut ledger = PrecisionLedger::new();
        h.feed(&mut ledger);
        let t = ledger.tally(&id("WEB001"));
        assert_eq!((t.fixed, t.dismissed), (0, 1));
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.load
    #[test]
    fn a_malformed_history_is_an_error_and_an_absent_one_is_empty() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(
            PrecisionHistory::load(dir.path()).unwrap(),
            PrecisionHistory::default()
        );
        std::fs::write(PrecisionHistory::path(dir.path()), "{nope").unwrap();
        assert!(matches!(
            PrecisionHistory::load(dir.path()),
            Err(HistoryError::Malformed { .. })
        ));
    }

    // frob:tests crates/gob-rules/src/precision_history.rs::PrecisionHistory.save
    #[test]
    #[expect(
        clippy::disallowed_methods,
        reason = "the test lists the state directory itself, not walked content"
    )]
    fn save_replaces_the_file_whole_and_leaves_no_temp_sibling() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            PrecisionHistory::path(dir.path()),
            "x".repeat(64 * 1024).as_bytes(),
        )
        .unwrap();
        let mut h = PrecisionHistory::default();
        h.record_run(&[finding("COV001", "a")], &eval(&["COV001"]));
        h.save(dir.path()).unwrap();

        assert_eq!(PrecisionHistory::load(dir.path()).unwrap(), h);
        let names: Vec<_> = std::fs::read_dir(dir.path())
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        assert_eq!(names, [std::ffi::OsString::from(HISTORY_FILE)]);
    }
}
