//! `doctor` for milestones and cycles: fold equals frontmatter, event order, dangling members.

use std::collections::BTreeMap;

use crate::error::Result;
use crate::fold::fold;
use crate::model::{ObjectId, ObjectKind};
use crate::store::PmStore;

/// Seconds an event's `at` may differ from its ULID time before it is flagged.
pub const CLOCK_SKEW_SECS: i64 = frob_ledger::doctor::CLOCK_SKEW_SECS;

/// One problem found in an object.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PmIssue {
    /// Stable code: `E-PM-UNREADABLE`, `E-PM-ID`, `E-PM-ORDER`, `E-PM-CONFLICT`,
    /// `E-PM-DRIFT`, `E-PM-MEMBER` or `E-PM-ALIAS`.
    pub code: &'static str,
    /// Milestone or cycle.
    pub kind: ObjectKind,
    /// The object directory name (a ULID unless that is the problem).
    pub subject: String,
    /// What is wrong.
    pub message: String,
}

/// The result of [`PmStore::doctor`].
#[derive(Debug, Clone, Default)]
pub struct PmReport {
    /// Objects examined.
    pub objects: usize,
    /// Events examined.
    pub events: usize,
    /// Problems.
    pub issues: Vec<PmIssue>,
    /// Objects whose frontmatter `--fix` rewrote.
    pub fixed: Vec<ObjectId>,
}

impl PmReport {
    /// True when nothing is wrong.
    pub fn is_clean(&self) -> bool {
        self.issues.is_empty()
    }
}

impl PmStore<'_> {
    /// Re-fold every milestone and cycle at the tip and compare with its frontmatter.
    ///
    /// With `fix`, frontmatter that differs from a successful fold is rewritten.
    /// Unreadable objects are reported as issues, never as errors.
    ///
    /// # Errors
    ///
    /// Ledger read or commit failures.
    pub fn doctor(self, fix: bool) -> Result<PmReport> {
        let mut report = PmReport::default();
        let Some(tip) = self.ledger.tip_hex()? else {
            return Ok(report);
        };
        for kind in ObjectKind::ALL {
            let mut aliases: BTreeMap<String, Vec<String>> = BTreeMap::new();
            for (dir, files) in self.files_by_dir(&tip, kind)? {
                report.objects += 1;
                let mut found = Vec::new();
                let checked = self.check_object(&tip, kind, &dir, &files, &mut found)?;
                report
                    .issues
                    .extend(found.into_iter().map(|(code, message)| PmIssue {
                        code,
                        kind,
                        subject: dir.clone(),
                        message,
                    }));
                let Some(c) = checked else { continue };
                report.events += c.events;
                aliases.entry(c.alias).or_default().push(dir.clone());
                if c.drift {
                    let id = c.id;
                    if fix && self.reconcile(kind, id, 3)?.is_some() {
                        report.fixed.push(id);
                    } else {
                        report.issues.push(PmIssue {
                            code: "E-PM-DRIFT",
                            kind,
                            subject: dir.clone(),
                            message: "frontmatter differs from the fold of its events".to_owned(),
                        });
                    }
                }
            }
            for (alias, dirs) in aliases.into_iter().filter(|(_, d)| d.len() > 1) {
                report.issues.push(PmIssue {
                    code: "E-PM-ALIAS",
                    kind,
                    subject: dirs.join(","),
                    message: format!("alias `{alias}` names {} {kind}s", dirs.len()),
                });
            }
        }
        tracing::info!(
            objects = report.objects,
            issues = report.issues.len(),
            fixed = report.fixed.len(),
            "pm doctor finished"
        );
        Ok(report)
    }

    /// Check one object directory, pushing `(code, message)` problems onto `found`; `None` when it cannot be folded.
    fn check_object(
        self,
        tip: &str,
        kind: ObjectKind,
        dir: &str,
        files: &[String],
        found: &mut Vec<(&'static str, String)>,
    ) -> Result<Option<Checked>> {
        let Ok(id) = dir.parse::<ObjectId>() else {
            found.push(("E-PM-ID", format!("`{dir}` is not a ULID directory name")));
            return Ok(None);
        };
        if !files.iter().any(|f| f == kind.file()) {
            found.push(("E-PM-UNREADABLE", format!("missing {}", kind.file())));
        }
        let events = match self.read_events_at(tip, kind, id) {
            Ok(e) => e,
            Err(e) => {
                found.push(("E-PM-UNREADABLE", e.to_string()));
                return Ok(None);
            }
        };
        for ev in &events {
            let ulid_secs = i64::try_from(ev.id.timestamp_ms() / 1000).unwrap_or(0);
            let skew = (ev.at.unix() - ulid_secs).abs();
            if skew > CLOCK_SKEW_SECS {
                found.push((
                    "E-PM-ORDER",
                    format!(
                        "event {} has at={} but its ULID says a time {skew}s away",
                        ev.id, ev.at
                    ),
                ));
            }
        }
        let folded = match fold(kind, id, &events) {
            Ok(f) => f,
            Err(e) => {
                found.push(("E-PM-UNREADABLE", e.to_string()));
                return Ok(None);
            }
        };
        for c in &folded.conflicts {
            found.push((
                "E-PM-CONFLICT",
                format!(
                    "event {} changed `{}` expecting {} but found {}",
                    c.event,
                    c.field,
                    c.expected.as_deref().unwrap_or("unset"),
                    c.found.as_deref().unwrap_or("unset")
                ),
            ));
        }
        for t in folded.object.members() {
            if !self.ledger.ticket_exists_at(tip, &t.to_string())? {
                found.push((
                    "E-PM-MEMBER",
                    format!("member {t} is not a ticket on this ledger"),
                ));
            }
        }
        let drift = match self.read_stored_at(tip, kind, id) {
            Ok(Some(stored)) => stored != folded.object,
            Ok(None) => {
                found.push(("E-PM-UNREADABLE", format!("{} is missing", kind.file())));
                false
            }
            Err(e) => {
                found.push(("E-PM-UNREADABLE", e.to_string()));
                false
            }
        };
        Ok(Some(Checked {
            id,
            events: events.len(),
            alias: folded.object.alias(),
            drift,
        }))
    }
}

/// What a successful per-object check learned.
struct Checked {
    id: ObjectId,
    events: usize,
    alias: String,
    drift: bool,
}
