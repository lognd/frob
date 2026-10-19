//! `config diff --base REF`: the policy delta GATE001 would read, and the CODEOWNERS recommendation `init` prints.
//!
//! Both sides are flattened by `gob_trust::policy::PolicySnapshot`; the weakenings are classified by
//! `gob_check::gate001::weakenings`, so this verb and the gate can never disagree (security.md 2.7).

// frob:ticket 01M3ZX7XMRBR2H68DNBNGV12ZZ

use std::path::Path;

use gob_check::gate001::weakenings;
use gob_trust::policy::{PolicyError, PolicySnapshot};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// One policy setting that differs between base and head.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct PolicyRow {
    /// Dotted key of the setting.
    pub key: String,
    /// Canonical value at base, absent when the setting did not exist.
    pub old: Option<String>,
    /// Canonical value at head, absent when the setting was removed.
    pub new: Option<String>,
}

/// Output of `config diff`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ConfigDiffData {
    /// The base ref.
    pub base: String,
    /// The head ref, or `worktree` for the working copy.
    pub head: String,
    /// Every changed policy setting, in key order.
    pub changes: Vec<PolicyRow>,
    /// The subset GATE001 reports as weakened.
    pub weakenings: Vec<PolicyRow>,
}

/// Output of the `config` verb: a file explanation or a policy diff.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(untagged)]
pub enum ConfigData {
    /// `config --for FILE`.
    For(crate::config_for::ConfigForData),
    /// `config diff --base REF`.
    Diff(ConfigDiffData),
}

/// Policy delta from the config text at base to the config text at head (empty text is an empty config).
///
/// # Errors
/// [`PolicyError::Toml`] when either text is not valid TOML.
pub fn config_diff(
    base_ref: &str,
    base_text: &str,
    head_ref: &str,
    head_text: &str,
) -> Result<ConfigDiffData, PolicyError> {
    let delta = PolicySnapshot::from_toml(base_text)?.diff(&PolicySnapshot::from_toml(head_text)?);
    let row = |key: &str, old: &Option<String>, new: &Option<String>| PolicyRow {
        key: key.to_owned(),
        old: old.clone(),
        new: new.clone(),
    };
    let weak = weakenings(&delta);
    tracing::info!(
        changes = delta.changes.len(),
        weakenings = weak.len(),
        "config diff computed"
    );
    Ok(ConfigDiffData {
        base: base_ref.to_owned(),
        head: head_ref.to_owned(),
        changes: delta
            .changes
            .iter()
            .map(|c| row(&c.key, &c.old, &c.new))
            .collect(),
        weakenings: weak.iter().map(|w| row(&w.key, &w.old, &w.new)).collect(),
    })
}

/// The control plane paths a CODEOWNERS file should cover (security.md 2.6).
pub const CONTROL_PLANE: &[&str] = &[
    "grimble.toml",
    "frob.toml",
    "grimble.lock",
    "packs/",
    ".github/workflows/",
    "CODEOWNERS",
];

/// Where git hosts look for a CODEOWNERS file, relative to the root.
const CODEOWNERS_FILES: &[&str] = &["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"];

/// Whether CODEOWNERS pattern `pat` covers the control plane path `path` (a lexical subset of the gitignore syntax).
fn pattern_covers(pat: &str, path: &str) -> bool {
    let pat = pat.trim_start_matches('/');
    if pat == "*" || pat == "**" {
        return true;
    }
    let dir = pat.trim_end_matches("**").trim_end_matches('/');
    pat == path
        || (pat.ends_with('/') || pat.ends_with("/**")) && path.starts_with(&format!("{dir}/"))
        || path.trim_end_matches('/') == dir
}

/// The control plane paths no pattern of the CODEOWNERS text covers; empty when all are covered.
fn uncovered(codeowners: &str) -> Vec<&'static str> {
    let patterns: Vec<&str> = codeowners
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .filter_map(|l| l.split_whitespace().next())
        .collect();
    CONTROL_PLANE
        .iter()
        .copied()
        .filter(|p| !patterns.iter().any(|pat| pattern_covers(pat, p)))
        .collect()
}

/// A recommendation line when the repository's CODEOWNERS does not cover the control plane, else `None`.
#[must_use]
pub fn codeowners_recommendation(root: &Path) -> Option<String> {
    let text = CODEOWNERS_FILES
        .iter()
        .find_map(|f| std::fs::read_to_string(root.join(f)).ok());
    let missing = match &text {
        Some(t) => uncovered(t),
        None => CONTROL_PLANE.to_vec(),
    };
    if missing.is_empty() {
        tracing::debug!("CODEOWNERS covers the control plane");
        return None;
    }
    let advice = format!(
        "CODEOWNERS {} the control plane; add an owner for: {}",
        if text.is_some() {
            "does not cover all of"
        } else {
            "is missing, so nothing protects"
        },
        missing.join(", ")
    );
    tracing::warn!(%advice, product = PRODUCT, "CODEOWNERS recommendation");
    Some(advice)
}

#[cfg(test)]
mod tests {
    use super::*;

    const BASE: &str = "[rules.SEC001]\nseverity = \"error\"\n";
    const HEAD: &str = "[rules.SEC001]\nseverity = \"warn\"\n";

    // frob:tests crates/grimble/src/config_diff.rs::config_diff
    #[test]
    fn a_weakened_severity_is_listed() {
        let d = config_diff("main", BASE, "worktree", HEAD).unwrap();
        assert_eq!(d.changes.len(), 1);
        assert_eq!(d.weakenings.len(), 1);
        assert_eq!(d.weakenings[0].key, "rules.SEC001.severity");
    }

    // frob:tests crates/grimble/src/config_diff.rs::config_diff
    #[test]
    fn a_strengthened_severity_is_a_change_but_not_a_weakening() {
        let d = config_diff("main", HEAD, "worktree", BASE).unwrap();
        assert_eq!(d.changes.len(), 1);
        assert!(d.weakenings.is_empty());
    }

    // frob:tests crates/grimble/src/config_diff.rs::config_diff
    #[test]
    fn invalid_toml_is_an_error() {
        assert!(config_diff("a", "= nope", "b", "").is_err());
    }

    // frob:tests crates/grimble/src/config_diff.rs::codeowners_recommendation
    #[test]
    fn a_missing_codeowners_is_recommended_and_a_covering_one_is_not() {
        let dir = tempfile::tempdir().unwrap();
        assert!(
            codeowners_recommendation(dir.path())
                .unwrap()
                .contains("grimble.toml")
        );
        std::fs::write(dir.path().join("CODEOWNERS"), "* @owner\n").unwrap();
        assert_eq!(codeowners_recommendation(dir.path()), None);
    }

    // frob:tests crates/grimble/src/config_diff.rs::codeowners_recommendation
    #[test]
    fn a_partial_codeowners_names_what_is_uncovered() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("CODEOWNERS"),
            "/grimble.toml @o\n/packs/ @o\n",
        )
        .unwrap();
        let r = codeowners_recommendation(dir.path()).unwrap();
        assert!(r.contains("frob.toml") && !r.contains("packs/") && !r.contains(" grimble.toml"));
    }
}
