//! Review comments (`design/review/*.toml`): anchored notes a reviewer leaves on a screen.
//!
//! Each file holds `[[comment]]` rows. A comment names a screen and, optionally, one of its
//! states (the anchor). An open blocking comment stops `crunk status ID ready`; a comment whose
//! anchor no longer names a state is orphaned and never blocks (crunk.md 5, 8).

// frob:ticket 01M5XCZ18GTA7MKKF4Z0MD95W3

use std::path::Path;

use serde::Deserialize;

/// Directory under the project root holding review comment files.
pub const REVIEW_DIR: &str = "design/review";

/// Whether a comment still needs an answer.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CommentStatus {
    /// Not yet answered.
    #[default]
    Open,
    /// Answered; it no longer blocks.
    Resolved,
}

/// One anchored review comment (`[[comment]]`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Comment {
    /// Stable comment id, unique within the project.
    pub id: String,
    /// The screen the comment is on.
    pub screen: String,
    /// The state id the comment is anchored to; the whole screen when absent.
    #[serde(default)]
    pub anchor: Option<String>,
    /// What the reviewer said.
    #[serde(default)]
    pub body: String,
    /// True when the comment must be resolved before handoff.
    #[serde(default)]
    pub blocking: bool,
    /// Open or resolved.
    #[serde(default)]
    pub status: CommentStatus,
}

impl Comment {
    /// Whether this comment, still open, would stop a handoff were its anchor live.
    #[must_use]
    pub fn is_open_blocking(&self) -> bool {
        self.blocking && self.status == CommentStatus::Open
    }

    /// Whether the anchor names no state of the screen whose state ids are `states`.
    #[must_use]
    pub fn is_orphaned(&self, states: &[&str]) -> bool {
        self.anchor.as_deref().is_some_and(|a| !states.contains(&a))
    }
}

/// The on-disk shape of one review file.
#[derive(Debug, Default, Deserialize)]
struct ReviewFile {
    #[serde(default)]
    comment: Vec<Comment>,
}

/// Parse one review file's text into its comments.
///
/// # Errors
/// The text is not TOML or not the review schema.
pub fn parse_review_file(text: &str) -> Result<Vec<Comment>, String> {
    let file: ReviewFile = toml_edit::de::from_str(text).map_err(|e| e.to_string())?;
    Ok(file.comment)
}

/// Read every `<root>/design/review/*.toml`, sorted by path; a missing directory yields none.
///
/// An unreadable or invalid file is skipped with a warning.
pub fn load_comments(root: &Path) -> Vec<Comment> {
    let dir = root.join(REVIEW_DIR);
    let Ok(entries) = std::fs::read_dir(&dir) else {
        tracing::debug!(dir = %dir.display(), "no review directory");
        return Vec::new();
    };
    let mut paths: Vec<_> = entries
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|x| x == "toml"))
        .collect();
    paths.sort();
    let comments: Vec<Comment> = paths
        .into_iter()
        .filter_map(|path| {
            let text = std::fs::read_to_string(&path)
                .inspect_err(|err| {
                    tracing::warn!(path = %path.display(), %err, "review file unreadable; skipped");
                })
                .ok()?;
            parse_review_file(&text)
                .inspect_err(|err| {
                    tracing::warn!(path = %path.display(), %err, "review file invalid; skipped");
                })
                .ok()
        })
        .flatten()
        .collect();
    tracing::debug!(count = comments.len(), "loaded review comments");
    comments
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEXT: &str =
        "[[comment]]\nid = \"c1\"\nscreen = \"home\"\nanchor = \"default\"\nblocking = true\n";

    // frob:tests Comment.is_open_blocking
    #[test]
    fn a_parsed_blocking_comment_defaults_to_open() {
        let c = parse_review_file(TEXT).unwrap().remove(0);
        assert!(c.is_open_blocking());
    }

    // frob:tests Comment.is_orphaned
    #[test]
    fn an_anchor_outside_the_states_is_orphaned() {
        let c = parse_review_file(TEXT).unwrap().remove(0);
        assert!(c.is_orphaned(&["other"]));
    }
}
