//! Reason-quality checker (exceptions design, section 5), a pure function.

/// A named banned phrase, matched case-insensitively on word boundaries.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BannedPattern {
    /// Name reported in the rejection.
    pub name: String,
    /// Space-separated lowercase words that must not appear in sequence.
    pub phrase: String,
}

impl BannedPattern {
    fn new(name: &str, phrase: &str) -> Self {
        Self {
            name: name.to_owned(),
            phrase: phrase.to_owned(),
        }
    }
}

/// Tunable knobs for [`check_reason`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReasonPolicy {
    /// Minimum reason length in characters (after trimming).
    pub min_len: usize,
    /// Banned phrases.
    pub banned: Vec<BannedPattern>,
    /// Reject a word repeated back to back.
    pub reject_repeated_words: bool,
}

impl Default for ReasonPolicy {
    fn default() -> Self {
        Self {
            min_len: 15,
            banned: vec![
                BannedPattern::new("temporary", "temporary"),
                BannedPattern::new("temporarily", "temporarily"),
                BannedPattern::new("for-now", "for now"),
                BannedPattern::new("fix-later", "fix later"),
                BannedPattern::new("wip", "wip"),
                BannedPattern::new("todo", "todo"),
                BannedPattern::new("tbd", "tbd"),
                BannedPattern::new("n/a", "n a"),
            ],
            reject_repeated_words: true,
        }
    }
}

/// Why a reason was refused; each variant names what tripped.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ReasonRejected {
    /// Shorter than the configured minimum.
    #[error("reason too short ({actual} < {min} characters)")]
    TooShort {
        /// Configured minimum.
        min: usize,
        /// Actual trimmed length.
        actual: usize,
    },
    /// Contains a banned phrase.
    #[error("reason matches banned pattern `{pattern}`")]
    Banned {
        /// Name of the matched pattern.
        pattern: String,
    },
    /// Merely restates a rule id (e.g. "COV006 does not apply").
    #[error("reason only restates the rule id `{rule}`")]
    RestatesRule {
        /// The rule id restated.
        rule: String,
    },
    /// A word is repeated back to back.
    #[error("reason repeats the word `{word}`")]
    RepeatedWord {
        /// The repeated word.
        word: String,
    },
}

/// Words that add no information next to a rule id.
const FILLER: &[&str] = &[
    "does", "do", "not", "no", "apply", "applies", "to", "this", "here", "is", "ok", "okay",
    "fine", "the", "a", "rule", "ignore", "ignored", "skip", "skipped", "disabled",
];

/// True for tokens shaped like a rule id (letters then 3 digits), any case.
fn is_rule_id_token(t: &str) -> bool {
    t.len() >= 5
        && t.len() <= 9
        && t[t.len() - 3..].bytes().all(|b| b.is_ascii_digit())
        && t[..t.len() - 3].bytes().all(|b| b.is_ascii_alphabetic())
}

/// Vet a reason against `policy`.
///
/// ```
/// use gob_rules::{ReasonPolicy, check_reason};
/// let p = ReasonPolicy::default();
/// assert!(check_reason("generated parser output, see ADR-0007", &p).is_ok());
/// assert!(check_reason("temporary workaround", &p).is_err());
/// ```
///
/// # Errors
///
/// Returns the first [`ReasonRejected`] cause found.
pub fn check_reason(reason: &str, policy: &ReasonPolicy) -> Result<(), ReasonRejected> {
    let trimmed = reason.trim();
    let actual = trimmed.chars().count();
    if actual < policy.min_len {
        return Err(ReasonRejected::TooShort {
            min: policy.min_len,
            actual,
        });
    }
    let words: Vec<String> = trimmed
        .split(|c: char| !c.is_alphanumeric())
        .filter(|w| !w.is_empty())
        .map(str::to_lowercase)
        .collect();
    for pat in &policy.banned {
        let needle: Vec<&str> = pat.phrase.split_whitespace().collect();
        if !needle.is_empty()
            && words
                .windows(needle.len())
                .any(|w| w.iter().zip(&needle).all(|(a, b)| a == b))
        {
            return Err(ReasonRejected::Banned {
                pattern: pat.name.clone(),
            });
        }
    }
    if let Some(rule) = words.iter().find(|w| is_rule_id_token(w))
        && words
            .iter()
            .all(|w| is_rule_id_token(w) || FILLER.contains(&w.as_str()))
    {
        return Err(ReasonRejected::RestatesRule {
            rule: rule.to_uppercase(),
        });
    }
    if policy.reject_repeated_words
        && let Some(pair) = words.windows(2).find(|w| w[0] == w[1])
    {
        return Err(ReasonRejected::RepeatedWord {
            word: pair[0].clone(),
        });
    }
    Ok(())
}
