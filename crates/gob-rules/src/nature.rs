//! Rule nature and the waivable-error message contract (rules.md section 6.1.4).
//!
//! A [`Nature::Heuristic`] rule is a smell check: its finding is an Error a human may waive. The
//! message always names what it is and why it fired; only the human form carries the exact
//! `frob:waive` line, the agent form tells the agent to fix the code and not to waive.

use serde::{Deserialize, Serialize};
use tracing::debug;

use crate::finding::{Finding, Fingerprint};
use crate::id::RuleId;
use crate::meta::Severity;
use gob_text::Span;

/// Part 1 of every heuristic message: what the finding is.
pub const HEURISTIC_PREFIX: &str = "HEURISTIC: this is a smell check, not a proven defect.";

/// Part 3 of the agent form: the instruction replacing the waive line.
pub const AGENT_INSTRUCTION: &str =
    "Fix the code. Do NOT waive this: waiving a heuristic is a human decision.";

/// Whether a rule proves a defect or makes a judgment call.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Nature {
    /// Proves a defect; baselined, fixed or off, never waived by default.
    #[default]
    Exact,
    /// A smell check; an Error a human may waive.
    Heuristic,
}

impl Nature {
    /// Lowercase label used as the envelope `nature` value.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Exact => "exact",
            Self::Heuristic => "heuristic",
        }
    }

    /// Who may waive a finding of this nature: `Some("human")` for a heuristic, `None` for an exact rule.
    #[must_use]
    pub const fn waivable_by(self) -> Option<&'static str> {
        match self {
            Self::Exact => None,
            Self::Heuristic => Some("human"),
        }
    }
}

/// Who reads the output; chosen by the existing agent detection, never guessed from a tty.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Audience {
    /// An agent: told to fix the code, never shown the waive line.
    Agent,
    /// A human: shown the exact waive line.
    Human,
}

/// The evidence behind one heuristic finding, renderable for either audience.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeuristicNote {
    rule: RuleId,
    evidence: String,
}

impl HeuristicNote {
    /// Note that `rule` fired because of `evidence` (what was measured against what threshold).
    pub fn new(rule: RuleId, evidence: impl Into<String>) -> Self {
        Self {
            rule,
            evidence: evidence.into(),
        }
    }

    /// The copy-pasteable suppression for a human, `frob:waive RULE reason="..."`.
    #[must_use]
    pub fn waive_line(&self) -> String {
        format!(
            "frob:waive {} reason=\"<why this is fine>\"",
            self.rule.as_str()
        )
    }

    /// The three-part message for `audience` (what it is, why it fired, waive line or instruction).
    #[must_use]
    pub fn message(&self, audience: Audience) -> String {
        let third = match audience {
            Audience::Agent => AGENT_INSTRUCTION.to_owned(),
            Audience::Human => format!("To waive at this site: {}", self.waive_line()),
        };
        format!("{HEURISTIC_PREFIX} {} {third}", self.evidence)
    }
}

impl Finding {
    /// Build an Error finding for a heuristic rule, rendering `note` for `audience`.
    ///
    /// The fingerprint is computed from the evidence alone, so it is the same for both audiences.
    pub fn heuristic(
        note: &HeuristicNote,
        audience: Audience,
        span: Option<Span>,
        anchor: &str,
    ) -> Self {
        debug!(rule = %note.rule, ?audience, "rendering heuristic finding");
        let mut f = Self::new(
            note.rule.clone(),
            Severity::Error,
            span,
            note.message(audience),
            anchor,
        );
        f.fingerprint = Fingerprint::compute(&note.rule, anchor, &note.evidence);
        f
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn note() -> HeuristicNote {
        HeuristicNote::new(
            "COH003".parse().unwrap(),
            "cohesion 0.2 is below the 0.4 threshold.",
        )
    }

    // frob:tests crates/gob-rules/src/nature.rs::HeuristicNote::message
    #[test]
    fn human_message_has_three_parts_and_waive_line() {
        let m = note().message(Audience::Human);
        assert!(m.starts_with(HEURISTIC_PREFIX));
        assert!(m.contains("cohesion 0.2 is below"));
        assert!(m.contains("frob:waive COH003 reason=\"<why this is fine>\""));
    }

    // frob:tests crates/gob-rules/src/nature.rs::HeuristicNote::message
    #[test]
    fn agent_message_says_do_not_waive_and_omits_waive_line() {
        let m = note().message(Audience::Agent);
        assert!(m.starts_with(HEURISTIC_PREFIX));
        assert!(m.contains("Do NOT waive this"));
        assert!(!m.contains("frob:waive"));
    }

    // frob:tests crates/gob-rules/src/nature.rs::Finding::heuristic
    #[test]
    fn heuristic_finding_is_error_with_audience_independent_fingerprint() {
        let a = Finding::heuristic(&note(), Audience::Agent, None, "src/a.rs");
        let h = Finding::heuristic(&note(), Audience::Human, None, "src/a.rs");
        assert_eq!(a.severity, Severity::Error);
        assert_eq!(a.fingerprint, h.fingerprint);
        assert_ne!(a.message, h.message);
    }

    // frob:tests crates/gob-rules/src/nature.rs::Nature::waivable_by
    #[test]
    fn nature_labels_and_waivable_by() {
        assert_eq!(Nature::default(), Nature::Exact);
        assert_eq!(Nature::Heuristic.label(), "heuristic");
        assert_eq!(Nature::Heuristic.waivable_by(), Some("human"));
        assert_eq!(Nature::Exact.waivable_by(), None);
    }

    // frob:tests crates/gob-rules/src/reason.rs::check_reason
    #[test]
    fn reasonless_placeholder_stays_rejected() {
        assert!(crate::check_reason("", &crate::ReasonPolicy::default()).is_err());
    }
}
