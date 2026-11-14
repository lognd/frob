//! The voice and tone file (`design/content/voice.toml`): the glossary of preferred terms and the
//! banned words that the CONTENT glossary and tone rules hold content-key text to. Any other key
//! (a free-form `voice = "plain and warm"` note, say) is ignored, so a prose-only file still counts
//! as a voice for CRAFT013 and simply carries no machine rules.

// frob:ticket 01M5H5P5E98XTANP62H5TVTSC4

use serde::{Deserialize, Serialize};

/// One glossary entry: the term the product uses and the variants copy must not use instead.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GlossaryTerm {
    /// The term copy should use, for example `sign in`.
    pub preferred: String,
    /// Variants that name the same thing and are to be replaced, for example `log in`.
    #[serde(default)]
    pub avoid: Vec<String>,
}

/// The machine-readable part of a voice file.
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct VoiceRules {
    /// Words and phrases the tone forbids anywhere in copy.
    #[serde(default)]
    pub banned: Vec<String>,
    /// Preferred terms with the variants to avoid, in file order.
    #[serde(default, rename = "term")]
    pub glossary: Vec<GlossaryTerm>,
}

impl VoiceRules {
    /// Whether the file carries no rules, so the glossary and tone rules have nothing to check.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.banned.is_empty() && self.glossary.is_empty()
    }
}

/// Parse the rules out of a voice file's text; text that is not valid TOML or does not fit the
/// rule shapes gives `Err` with the reason (the caller decides whether that is fatal).
///
/// # Errors
///
/// Returns the parse reason when `text` is not valid TOML or does not fit the rule shapes.
pub fn parse_voice_rules(text: &str) -> Result<VoiceRules, String> {
    let rules: VoiceRules = toml_edit::de::from_str(text).map_err(|e| e.to_string())?;
    tracing::debug!(
        banned = rules.banned.len(),
        terms = rules.glossary.len(),
        "voice rules parsed"
    );
    Ok(rules)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/voice_file.rs::parse_voice_rules
    #[test]
    fn parses_banned_words_and_glossary_terms_and_ignores_prose() {
        let r = parse_voice_rules(
            "voice = \"plain\"\nbanned = [\"seamless\"]\n[[term]]\npreferred = \"sign in\"\navoid = [\"log in\", \"login\"]\n",
        )
        .expect("parses");
        assert_eq!(r.banned, ["seamless"]);
        assert_eq!(r.glossary[0].preferred, "sign in");
        assert_eq!(r.glossary[0].avoid, ["log in", "login"]);
        assert!(!r.is_empty());
        assert!(
            parse_voice_rules("voice = \"plain\"\n")
                .expect("parses")
                .is_empty()
        );
        assert!(parse_voice_rules("banned = 3\n").is_err());
    }
}
