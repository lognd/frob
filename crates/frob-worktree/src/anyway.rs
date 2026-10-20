//! The escape valve of a claimed ticket: `work --anyway` (`distributed-tickets.md` section 3.3, scenario 69).
//!
//! When another clone holds the claim (its create-only push won), `work`
//! normally refuses with `E-CLAIM-LOST`. `--anyway --reason TEXT` proceeds
//! without taking the claim: nothing is pushed, no claim transfers, and a note
//! on the ticket records the reason, the scope worked in and an expiry. `land`
//! shows the note as `worked over <branch>'s claim: <reason>`, flagging an
//! expired one.

// frob:ticket 01M5CW05JQZKCQKV68ZEQ5WASD

use frob_ledger::event::EventBody;
use frob_ledger::model::CommentSubtype;
use frob_ledger::{Ledger, TicketId};

/// Default days an escape stays valid.
pub const DEFAULT_EXPIRY_DAYS: u32 = 7;

/// Marker that starts every escape note.
const MARKER: &str = "worked over claim";

const SEP: &str = " | ";

/// A reasoned, scoped, expiring way past someone else's claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Anyway {
    /// Why the work proceeds despite the claim.
    pub reason: String,
    /// Globs the work is limited to; empty keeps the ticket's own scope.
    pub scope: Vec<String>,
    /// Days until the escape expires.
    pub expiry_days: u32,
}

/// A parsed escape note.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Note {
    /// The claimed branch that was worked over.
    pub branch: String,
    /// Unix seconds the escape expires at.
    pub expires: i64,
    /// Scope globs worked in.
    pub scope: Vec<String>,
    /// The stated reason.
    pub reason: String,
}

impl Note {
    /// The comment body that records an escape over `branch` taken at `now` (unix seconds).
    #[must_use]
    pub fn render(anyway: &Anyway, branch: &str, tip: &str, now: i64) -> String {
        let expires = now + i64::from(anyway.expiry_days) * 86_400;
        format!(
            "{MARKER}{SEP}{branch} at {tip}{SEP}{expires}{SEP}{}{SEP}{}",
            anyway.scope.join(","),
            anyway.reason
        )
    }

    /// Parse a comment body written by [`Note::render`]; `None` for any other comment.
    #[must_use]
    pub fn parse(body: &str) -> Option<Self> {
        let mut parts = body.splitn(5, SEP);
        if parts.next()? != MARKER {
            return None;
        }
        let branch = parts.next()?.split(" at ").next()?.to_owned();
        let expires = parts.next()?.parse().ok()?;
        let scope = parts
            .next()?
            .split(',')
            .filter(|g| !g.is_empty())
            .map(str::to_owned)
            .collect();
        let reason = parts.next()?.to_owned();
        Some(Self {
            branch,
            expires,
            scope,
            reason,
        })
    }

    /// The line `land` shows for this note at `now`.
    #[must_use]
    pub fn notice(&self, now: i64) -> String {
        let scope = if self.scope.is_empty() {
            String::new()
        } else {
            format!(" (scope {})", self.scope.join(", "))
        };
        let state = if now > self.expires {
            "; the escape has expired"
        } else {
            ""
        };
        format!(
            "worked over the claim on {}: {}{scope}{state}",
            self.branch, self.reason
        )
    }
}

/// Record on `id` that its claim on `branch` (at `tip`) was worked over.
///
/// # Errors
/// Ledger failures from the comment.
pub fn record(
    ledger: &Ledger,
    id: TicketId,
    anyway: &Anyway,
    branch: &str,
    tip: &str,
) -> Result<(), frob_ledger::LedgerError> {
    let now = ledger.clock().now().unix();
    ledger.comment(
        id,
        CommentSubtype::Note,
        &Note::render(anyway, branch, tip, now),
    )?;
    tracing::warn!(ticket = %id, branch, tip, reason = %anyway.reason, "worked over a claim");
    Ok(())
}

/// The notices `land` shows for `id`: one per escape note on the ticket.
#[must_use]
pub fn land_notices(ledger: &Ledger, id: TicketId) -> Vec<String> {
    let now = ledger.clock().now().unix();
    let events = match ledger.events(id) {
        Ok(e) => e,
        Err(e) => {
            tracing::warn!(ticket = %id, error = %e, "reading escape notes failed");
            return Vec::new();
        }
    };
    events
        .iter()
        .filter_map(|e| match &e.body {
            EventBody::Comment(c) => Note::parse(&c.body),
            _ => None,
        })
        .map(|n| n.notice(now))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Anyway {
        Anyway {
            reason: "owner away | urgent".to_owned(),
            scope: vec!["crates/x/**".to_owned()],
            expiry_days: 2,
        }
    }

    // frob:tests Note.render
    // frob:tests Note.parse
    #[test]
    fn a_rendered_note_parses_back() {
        let body = Note::render(&sample(), "ticket/abc", "deadbeef", 1000);
        let note = Note::parse(&body).expect("parses");
        assert_eq!(note.branch, "ticket/abc");
        assert_eq!(note.expires, 1000 + 2 * 86_400);
        assert_eq!(note.scope, vec!["crates/x/**".to_owned()]);
        assert_eq!(note.reason, "owner away | urgent");
    }

    // frob:tests Note.parse
    #[test]
    fn other_comments_are_not_notes() {
        assert!(Note::parse("lease stolen from a").is_none());
    }

    // frob:tests Note.notice
    #[test]
    fn an_expired_note_says_so() {
        let note = Note::parse(&Note::render(&sample(), "ticket/abc", "d", 0)).expect("parses");
        assert!(!note.notice(10).contains("expired"));
        assert!(note.notice(10 * 86_400).contains("expired"));
        assert!(
            note.notice(10)
                .contains("worked over the claim on ticket/abc")
        );
    }
}
