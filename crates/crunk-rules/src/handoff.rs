//! The handoff judge behind `crunk status ID ready`: collects every reason a screen is not ready.
//!
//! Pure over gathered facts; the verb does the I/O (lints, export drift, file existence) and
//! hands the results here so the refusal can name each reason at once.

// frob:ticket 01M5XCZ18GTA7MKKF4Z0MD95W3

use crunk_spec::handoff::Comment;

/// Facts about one screen gathered by the verb.
#[derive(Debug, Clone, Copy)]
pub struct Facts<'a> {
    /// Every review comment in the project; only this screen's are judged.
    pub comments: &'a [Comment],
    /// The screen id.
    pub screen: &'a str,
    /// The screen's state ids, for anchor checks.
    pub states: &'a [&'a str],
    /// Generated token files that are missing or drifted.
    pub stale_exports: &'a [String],
    /// Whether the screen maps to code (it lists sources and each exists).
    pub has_code_mapping: bool,
    /// Error-severity lint findings against the screen, as `RULE message`.
    pub red_lints: &'a [String],
}

/// One reason a screen cannot be handed off.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Reason {
    /// An open blocking comment.
    BlockingComment(String),
    /// A generated export is missing or drifted.
    StaleExport(String),
    /// The screen maps to no code.
    MissingCodeMapping,
    /// A lint at or below the tier is red.
    RedLint(String),
}

impl Reason {
    /// The one-line human description naming the reason.
    #[must_use]
    pub fn line(&self) -> String {
        match self {
            Self::BlockingComment(id) => format!("open blocking comment `{id}`"),
            Self::StaleExport(path) => format!("stale export `{path}`"),
            Self::MissingCodeMapping => {
                "missing code mapping (list existing paths under `sources`)".to_owned()
            }
            Self::RedLint(what) => format!("red lint {what}"),
        }
    }
}

/// The outcome of judging one screen.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Verdict {
    /// Every reason the screen is not ready; empty means green.
    pub reasons: Vec<Reason>,
    /// Ids of comments anchored to a deleted state; reported, never blocking.
    pub orphaned: Vec<String>,
}

/// Judge one screen: collect every blocker and the orphaned comments.
#[must_use]
pub fn judge(facts: &Facts<'_>) -> Verdict {
    let mut verdict = Verdict::default();
    for c in facts.comments.iter().filter(|c| c.screen == facts.screen) {
        if c.is_orphaned(facts.states) {
            tracing::debug!(comment = %c.id, "handoff: orphaned comment does not block");
            verdict.orphaned.push(c.id.clone());
        } else if c.is_open_blocking() {
            verdict.reasons.push(Reason::BlockingComment(c.id.clone()));
        }
    }
    verdict
        .reasons
        .extend(facts.stale_exports.iter().cloned().map(Reason::StaleExport));
    if !facts.has_code_mapping {
        verdict.reasons.push(Reason::MissingCodeMapping);
    }
    verdict
        .reasons
        .extend(facts.red_lints.iter().cloned().map(Reason::RedLint));
    verdict
}

/// Where a screen stands against its recorded handoff hash.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Standing {
    /// No handoff is recorded.
    Draft,
    /// The recorded hash matches the current content.
    Ready,
    /// The content moved since the handoff was recorded.
    Changed,
}

impl Standing {
    /// The status word (`draft`, `ready` or `changed`).
    #[must_use]
    pub fn word(self) -> &'static str {
        match self {
            Self::Draft => "draft",
            Self::Ready => "ready",
            Self::Changed => "changed",
        }
    }
}

/// Compare the recorded handoff hash (if any) with the current content hash.
#[must_use]
pub fn standing(recorded: Option<&str>, current: &str) -> Standing {
    match recorded {
        None => Standing::Draft,
        Some(h) if h == current => Standing::Ready,
        Some(_) => Standing::Changed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crunk_spec::handoff::{Comment, CommentStatus};

    fn comment(id: &str, anchor: Option<&str>, blocking: bool, status: CommentStatus) -> Comment {
        Comment {
            id: id.to_owned(),
            screen: "home".to_owned(),
            anchor: anchor.map(str::to_owned),
            body: String::new(),
            blocking,
            status,
        }
    }

    fn green<'a>(comments: &'a [Comment], states: &'a [&'a str]) -> Facts<'a> {
        Facts {
            comments,
            screen: "home",
            states,
            stale_exports: &[],
            has_code_mapping: true,
            red_lints: &[],
        }
    }

    // frob:tests judge
    #[test]
    fn all_green_facts_have_no_reasons() {
        assert!(judge(&green(&[], &["default"])).reasons.is_empty());
    }

    // frob:tests judge
    #[test]
    fn an_open_blocking_comment_is_a_reason() {
        let cs = [comment("c1", Some("default"), true, CommentStatus::Open)];
        let v = judge(&green(&cs, &["default"]));
        assert_eq!(v.reasons, vec![Reason::BlockingComment("c1".to_owned())]);
    }

    // frob:tests judge
    #[test]
    fn an_orphaned_comment_is_reported_but_does_not_block() {
        let cs = [comment("c1", Some("gone"), true, CommentStatus::Open)];
        let v = judge(&green(&cs, &["default"]));
        assert!(v.reasons.is_empty());
        assert_eq!(v.orphaned, vec!["c1".to_owned()]);
    }

    // frob:tests standing
    #[test]
    fn a_hash_that_moved_is_changed() {
        assert_eq!(standing(Some("a"), "b"), Standing::Changed);
    }
}
