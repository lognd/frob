//! `Finding`, `Fingerprint` and fix data.

use std::fmt;

use gob_text::{FileId, Span, TextRange};

use crate::id::RuleId;
use crate::meta::{FixKind, Severity};
use crate::required::RequiredReason;
use crate::unresolved::UnresolvedReason;

/// Stable identity of a finding: blake3 over rule, anchor and normalized message.
///
/// ```
/// use gob_rules::{Fingerprint, RuleId};
/// let r: RuleId = "COV006".parse().unwrap();
/// let a = Fingerprint::compute(&r, "src/a.rs::f", "line 12  missing   test");
/// let b = Fingerprint::compute(&r, "src/a.rs::f", "line 99 missing test");
/// assert_eq!(a, b);
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Fingerprint([u8; 32]);

impl Fingerprint {
    /// Hash `rule`, `anchor` (symref or file path) and the normalized `message`.
    pub fn compute(rule: &RuleId, anchor: &str, message: &str) -> Self {
        let mut h = blake3::Hasher::new();
        for part in [rule.as_str(), anchor, &normalize_message(message)] {
            h.update(&(part.len() as u64).to_le_bytes());
            h.update(part.as_bytes());
        }
        Self(*h.finalize().as_bytes())
    }

    /// Lowercase hex form.
    pub fn to_hex(&self) -> String {
        blake3::Hash::from_bytes(self.0).to_hex().to_string()
    }
}

impl fmt::Display for Fingerprint {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.to_hex())
    }
}

/// Collapse whitespace runs to one space and digit runs to `#`.
fn normalize_message(message: &str) -> String {
    let mut out = String::with_capacity(message.len());
    let mut prev_digit = false;
    for word_or_ws in message.split_whitespace().enumerate() {
        if word_or_ws.0 > 0 {
            out.push(' ');
            prev_digit = false;
        }
        for c in word_or_ws.1.chars() {
            if c.is_ascii_digit() {
                if !prev_digit {
                    out.push('#');
                }
                prev_digit = true;
            } else {
                out.push(c);
                prev_digit = false;
            }
        }
    }
    out
}

/// One replacement of a byte range in a file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TextEdit {
    /// File to edit.
    pub file: FileId,
    /// Byte range replaced.
    pub range: TextRange,
    /// Replacement text.
    pub replacement: String,
}

/// A proposed repair attached to a finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fix {
    /// How the fix is applied.
    pub kind: FixKind,
    /// Short human title.
    pub title: String,
    /// Edits making up the fix.
    pub edits: Vec<TextEdit>,
}

/// A rule violation (or unresolved evaluation) at an optional location.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// The rule that produced this finding.
    pub rule: RuleId,
    /// Severity of this finding.
    pub severity: Severity,
    /// Location, when the finding has one.
    pub span: Option<Span>,
    /// Human-readable message.
    pub message: String,
    /// Line-number-free stable identity.
    pub fingerprint: Fingerprint,
    /// Optional repair.
    pub fix: Option<Fix>,
    /// Why this Unresolved finding fails the gate (`cli.md` section 2); `None` when not required.
    pub required: Option<RequiredReason>,
    /// Why this Unresolved finding could not decide (`testing.md`, D106); `None` for a resolved finding.
    pub reason: Option<UnresolvedReason>,
}

impl Finding {
    /// Build a finding, computing its fingerprint from `anchor` (symref or file).
    pub fn new(
        rule: RuleId,
        severity: Severity,
        span: Option<Span>,
        message: impl Into<String>,
        anchor: &str,
    ) -> Self {
        let message = message.into();
        let fingerprint = Fingerprint::compute(&rule, anchor, &message);
        Self {
            rule,
            severity,
            span,
            message,
            fingerprint,
            fix: None,
            required: None,
            reason: None,
        }
    }

    /// Mark the finding required for `reason`, so the Unresolved gate fails on it.
    #[must_use]
    pub fn with_required(mut self, reason: RequiredReason) -> Self {
        self.required = Some(reason);
        self
    }

    /// Record the typed reason this Unresolved finding could not decide.
    #[must_use]
    pub fn with_reason(mut self, reason: UnresolvedReason) -> Self {
        self.reason = Some(reason);
        self
    }

    /// Attach a fix.
    #[must_use]
    pub fn with_fix(mut self, fix: Fix) -> Self {
        self.fix = Some(fix);
        self
    }
}
