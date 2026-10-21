//! A standalone screen spec file (`design/screens/<id>.screen.toml`): one screen's fields at the
//! top level with `[[states]]`, the same model as a `[[screen]]` table.

// frob:ticket 01M4CXR89ERNB60CEDG60E2DXH

use std::collections::HashSet;

use crate::table::ScreenConfig;

/// Why a screen spec file could not be read as a [`ScreenConfig`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ScreenFileError {
    /// Not valid TOML, or not the screen schema.
    #[error("invalid screen file: {0}")]
    Parse(String),
    /// The file has no states.
    #[error("screen `{0}` needs at least one state")]
    NoStates(String),
    /// Two states share an id.
    #[error("screen `{screen}` repeats state id `{state}`")]
    DuplicateState {
        /// The screen id.
        screen: String,
        /// The repeated state id.
        state: String,
    },
    /// A `diff_against` names no sibling state.
    #[error("screen `{screen}` state `{state}` diffs against unknown state `{target}`")]
    DanglingDiff {
        /// The screen id.
        screen: String,
        /// The state with the bad reference.
        state: String,
        /// The missing sibling id.
        target: String,
    },
}

/// Parse one screen spec file's text, checking the rules that need no project context.
///
/// # Errors
/// [`ScreenFileError`] on bad TOML, no states, a duplicate state id or a dangling `diff_from`.
pub fn parse_screen_file(text: &str) -> Result<ScreenConfig, ScreenFileError> {
    let screen: ScreenConfig =
        toml_edit::de::from_str(text).map_err(|e| ScreenFileError::Parse(e.to_string()))?;
    if screen.states.is_empty() {
        return Err(ScreenFileError::NoStates(screen.id));
    }
    let mut ids: HashSet<&str> = HashSet::new();
    for s in &screen.states {
        if !ids.insert(s.id.as_str()) {
            return Err(ScreenFileError::DuplicateState {
                screen: screen.id.clone(),
                state: s.id.clone(),
            });
        }
    }
    for s in &screen.states {
        if let Some(t) = &s.diff_against
            && !ids.contains(t.as_str())
        {
            return Err(ScreenFileError::DanglingDiff {
                screen: screen.id.clone(),
                state: s.id.clone(),
                target: t.clone(),
            });
        }
    }
    tracing::debug!(screen = %screen.id, states = screen.states.len(), "parsed screen file");
    Ok(screen)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::table::{ScreenKind, ScreenStatus};

    const FILE: &str = r#"
id = "home"
entry = "/"
kinds = ["interactive", "form"]
landmarks = ["main", "nav"]
headings = ["Welcome"]
copy_keys = ["home.title"]
status = "ready"
content_hash = "abc"

[[states]]
id = "default"

[[states]]
id = "hover"
diff_against = "default"
"#;

    // frob:tests crates/crunk-spec/src/screen_file.rs::parse_screen_file
    #[test]
    fn screen_file_parses_extended_fields() {
        let s = parse_screen_file(FILE).expect("parses");
        assert_eq!(s.kinds, [ScreenKind::Interactive, ScreenKind::Form]);
        assert_eq!(s.status, Some(ScreenStatus::Ready));
        assert_eq!(s.landmarks, ["main", "nav"]);
        assert_eq!(s.copy_keys, ["home.title"]);
        assert_eq!(s.content_hash.as_deref(), Some("abc"));
    }

    // frob:tests crates/crunk-spec/src/screen_file.rs::parse_screen_file
    #[test]
    fn screen_file_rejects_bad_states() {
        let none = "id = \"a\"\nentry = \"/\"\nstates = []\n";
        assert!(matches!(
            parse_screen_file(none),
            Err(ScreenFileError::NoStates(_))
        ));
        let dup = "id = \"a\"\nentry = \"/\"\n[[states]]\nid = \"x\"\n[[states]]\nid = \"x\"\n";
        assert!(matches!(
            parse_screen_file(dup),
            Err(ScreenFileError::DuplicateState { .. })
        ));
        let dang = "id = \"a\"\nentry = \"/\"\n[[states]]\nid = \"x\"\ndiff_against = \"y\"\n";
        assert!(matches!(
            parse_screen_file(dang),
            Err(ScreenFileError::DanglingDiff { .. })
        ));
        assert!(matches!(
            parse_screen_file("id = 3"),
            Err(ScreenFileError::Parse(_))
        ));
    }

    // frob:tests crates/crunk-spec/src/table.rs::ScreenConfig
    #[test]
    fn old_screen_tables_serialize_without_new_fields() {
        let s = parse_screen_file("id = \"a\"\nentry = \"/\"\n[[states]]\nid = \"x\"\n")
            .expect("parses");
        let json = serde_json::to_string(&s).expect("json");
        for k in [
            "kinds",
            "landmarks",
            "headings",
            "copy_keys",
            "status",
            "content_hash",
        ] {
            assert!(!json.contains(k), "{k} leaked into {json}");
        }
    }
}
