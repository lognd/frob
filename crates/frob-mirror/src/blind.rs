//! Status classification and the token blindness check (mirror.md 3.3, "Status codes").
//!
//! A 404 is never read as "deleted" because a token that cannot see an issue also gets 404;
//! a 410 marks the ticket unmirrored and never triggers a create; a 301 moves the cached
//! location only after the marker verifies there. Before any of that, the blindness check
//! confirms the token sees the repository and its own recent issues, else MIR001 `token-blind`.
//! (The GitHub HTTPS client lives behind `TrackerAdapter`; this module is transport-free.)

// frob:ticket 01M4052QSA5YKG6MY52BCW6PWV

use tracing::{debug, info, warn};

use crate::adapter::{AdapterError, IssueRef, TrackerAdapter};

/// What a status-bearing adapter error means for one ticket's issue.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Disposition {
    /// 301: the issue moved; the location is a claim until the marker verifies there.
    Moved(String),
    /// 404: the token cannot see the issue; it may still exist, so it is never deleted.
    NotVisible,
    /// 410: the issue is deleted; the ticket is marked unmirrored and reported.
    Unmirrored,
}

impl Disposition {
    /// Whether the mirror may create a replacement issue; never, recreate is a human act.
    pub fn may_create(&self) -> bool {
        false
    }

    /// Whether the ticket is marked unmirrored and reported (410 only).
    pub fn marks_unmirrored(&self) -> bool {
        matches!(self, Self::Unmirrored)
    }

    /// Whether the mirror may treat the issue as deleted (410 only; 404 never).
    pub fn is_deleted(&self) -> bool {
        matches!(self, Self::Unmirrored)
    }
}

/// Classify an adapter error by status; `None` for errors that carry no status meaning.
pub fn classify(err: &AdapterError) -> Option<Disposition> {
    let d = match err {
        AdapterError::Moved(loc) => Disposition::Moved(loc.clone()),
        AdapterError::NotFound => Disposition::NotVisible,
        AdapterError::Gone => Disposition::Unmirrored,
        AdapterError::RateLimited | AdapterError::Other(_) => return None,
    };
    debug!(?d, "status classified");
    if d.marks_unmirrored() {
        warn!("issue gone (410): ticket marked unmirrored, no create");
    }
    Some(d)
}

/// Apply a 301: replace `cached` with `new_location` only if `marker_verifies` holds there.
///
/// Returns whether the cached location changed.
pub fn handle_moved(
    cached: &mut IssueRef,
    new_location: &str,
    marker_verifies: impl FnOnce(&str) -> bool,
) -> bool {
    if marker_verifies(new_location) {
        info!(from = %cached.0, to = new_location, "issue moved: cached location updated");
        *cached = IssueRef(new_location.to_string());
        true
    } else {
        warn!(
            cached = %cached.0,
            claimed = new_location,
            "301 target does not carry the marker: cached location kept"
        );
        false
    }
}

/// Why the blindness check stopped the run.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum BlindError {
    /// The token cannot see the repository or its own recent issues (MIR001 token-blind).
    #[error("MIR001 token-blind: {0}")]
    TokenBlind(String),
}

/// Check the token sees the repository and its own recent issues; reads only, never writes.
///
/// # Errors
/// Returns [`BlindError::TokenBlind`] when the repository or the bot's newest issue is not
/// visible, or when the repository cannot be read at all.
pub fn check_blind(adapter: &dyn TrackerAdapter, bot_id: u64) -> Result<(), BlindError> {
    adapter.inventory().map_err(|e| {
        warn!(error = %e, "blindness check: repository not readable");
        BlindError::TokenBlind(format!("repository not visible ({e})"))
    })?;
    let recent = adapter.list_by_creator(bot_id).map_err(|e| {
        warn!(error = %e, "blindness check: own issues not listable");
        BlindError::TokenBlind(format!("own recent issues not listable ({e})"))
    })?;
    if let Some(newest) = recent.first() {
        adapter.read(&newest.issue).map_err(|e| {
            warn!(issue = %newest.issue.0, error = %e, "blindness check: own issue unreadable");
            BlindError::TokenBlind(format!("own issue {} not visible ({e})", newest.issue.0))
        })?;
    }
    debug!(bot_id, listed = recent.len(), "blindness check passed");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::{
        AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry, HistoryRetention,
        Inventory, IssueState, IssueSummary, MarkdownDialect, StateReasons,
    };
    use crate::projection::{IssueProjection, Outcome, RelationKind};
    use std::cell::Cell;

    /// Read-only fake with switchable visibility; counts every write attempt.
    struct Fake {
        repo_visible: bool,
        issues_visible: bool,
        listed: Vec<IssueSummary>,
        writes: Cell<u32>,
    }

    impl Fake {
        fn new(repo_visible: bool, issues_visible: bool) -> Self {
            let listed = vec![IssueSummary {
                issue: IssueRef("7".into()),
                title: "t".into(),
                creator_id: 9,
                created_at: "2026-01-01T00:00:00Z".into(),
            }];
            Self {
                repo_visible,
                issues_visible,
                listed,
                writes: Cell::new(0),
            }
        }
        #[allow(clippy::unnecessary_wraps)]
        fn w(&mut self) -> AdapterResult<()> {
            self.writes.set(self.writes.get() + 1);
            Ok(())
        }
    }

    impl TrackerAdapter for Fake {
        fn capabilities(&self) -> Capabilities {
            Capabilities {
                native_sub_issues: false,
                native_links: false,
                custom_fields: false,
                state_reasons: StateReasons::Unsupported,
                history_retention: HistoryRetention::None,
                markdown: MarkdownDialect::Github,
            }
        }
        fn create(&mut self, _: &IssueProjection, _: &str) -> CreateOutcome {
            self.writes.set(self.writes.get() + 1);
            CreateOutcome::Unknown
        }
        fn update(&mut self, _: &IssueRef, _: &IssueProjection) -> AdapterResult<()> {
            self.w()
        }
        fn close(&mut self, _: &IssueRef, _: Outcome) -> AdapterResult<()> {
            self.w()
        }
        fn list_by_creator(&self, _: u64) -> AdapterResult<Vec<IssueSummary>> {
            Ok(self.listed.clone())
        }
        fn read(&self, i: &IssueRef) -> AdapterResult<IssueState> {
            if !self.issues_visible {
                return Err(AdapterError::NotFound);
            }
            Ok(IssueState {
                issue: i.clone(),
                title: String::new(),
                body: String::new(),
                labels: vec![],
                assignees: vec![],
                closed: false,
            })
        }
        fn history_after(
            &self,
            _: &IssueRef,
            _: Option<&EventId>,
        ) -> AdapterResult<Vec<HistoryEntry>> {
            Ok(vec![])
        }
        fn add_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            self.w()
        }
        fn remove_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            self.w()
        }
        fn add_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            self.w()
        }
        fn remove_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            self.w()
        }
        fn link(&mut self, _: &IssueRef, _: RelationKind, _: &IssueRef) -> AdapterResult<()> {
            self.w()
        }
        fn inventory(&self) -> AdapterResult<Inventory> {
            if self.repo_visible {
                Ok(Inventory::default())
            } else {
                Err(AdapterError::NotFound)
            }
        }
    }

    // frob:tests classify
    #[test]
    fn not_found_is_not_visible_never_deleted() {
        let d = classify(&AdapterError::NotFound).unwrap();
        assert_eq!(d, Disposition::NotVisible);
        assert!(!d.is_deleted());
        assert!(!d.marks_unmirrored());
    }

    // frob:tests classify
    #[test]
    fn gone_marks_unmirrored_and_never_creates() {
        let d = classify(&AdapterError::Gone).unwrap();
        assert!(d.marks_unmirrored());
        assert!(!d.may_create());
        assert!(!Disposition::NotVisible.may_create());
        assert!(classify(&AdapterError::RateLimited).is_none());
    }

    // frob:tests handle_moved
    #[test]
    fn moved_updates_cache_only_after_marker_verifies() {
        let mut cached = IssueRef("old".into());
        assert!(!handle_moved(&mut cached, "new", |_| false));
        assert_eq!(cached.0, "old");
        assert!(handle_moved(&mut cached, "new", |loc| loc == "new"));
        assert_eq!(cached.0, "new");
    }

    // frob:tests check_blind
    #[test]
    fn blind_token_stops_with_mir001_and_writes_nothing() {
        for fake in [Fake::new(false, true), Fake::new(true, false)] {
            let e = check_blind(&fake, 9).unwrap_err();
            assert!(e.to_string().contains("MIR001 token-blind"));
            assert_eq!(fake.writes.get(), 0);
        }
        assert!(check_blind(&Fake::new(true, true), 9).is_ok());
    }
}
