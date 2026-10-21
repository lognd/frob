//! The authored screen spec files (`design/screens/*.screen.toml`) as the STATE rules read them:
//! each parsed into a [`ScreenConfig`] with its text kept so findings can anchor.

// frob:ticket 01M4CXR89ERNB60CEDG60E2DXH

use crunk_spec::table::{ScreenConfig, ScreenKind};
use crunk_spec::{DesignSpec, parse_screen_file};

use crate::sheets::site_path;

/// The project directory holding the authored screen files, relative to the root.
pub const SCREENS_DIR: &str = "design/screens";

/// The file suffix that marks a screen file.
pub const SCREEN_SUFFIX: &str = ".screen.toml";

/// One screen file that parsed.
#[derive(Debug, Clone)]
pub struct ScreenFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed screen.
    pub screen: ScreenConfig,
}

impl ScreenFile {
    /// Byte offset of the first line starting with `key` (a top-level key), 0 when absent.
    #[must_use]
    pub fn offset_of(&self, key: &str) -> usize {
        let mut at = 0;
        for line in self.text.split_inclusive('\n') {
            if line.starts_with(key) {
                return at;
            }
            at += line.len();
        }
        0
    }

    /// The state ids this screen declares.
    pub fn state_ids(&self) -> impl Iterator<Item = &str> {
        self.screen.states.iter().map(|s| s.id.as_str())
    }

    /// The states `kind` requires that this screen does not declare, in requirement order.
    #[must_use]
    pub fn missing_states(&self, kind: ScreenKind) -> Vec<&'static str> {
        required_states(kind)
            .iter()
            .copied()
            .filter(|need| !self.state_ids().any(|id| id == *need))
            .collect()
    }
}

/// The state ids a screen of `kind` must declare (STATE001, 002, 003 and 006).
#[must_use]
pub const fn required_states(kind: ScreenKind) -> &'static [&'static str] {
    match kind {
        ScreenKind::Interactive => &["default", "hover", "focus-visible", "active", "disabled"],
        ScreenKind::DataBound => &["loading", "empty", "error", "partial"],
        ScreenKind::Form => &["error", "success", "validation"],
        ScreenKind::Game => &["menu-default", "pause", "disconnect", "low-hull", "death"],
    }
}

/// The content hash of a screen: blake3 over its canonical JSON with `status` and `content_hash`
/// cleared, so recording the hash does not change it.
///
/// # Panics
/// Never in practice: a `ScreenConfig` always serializes to JSON.
#[must_use]
pub fn content_hash(screen: &ScreenConfig) -> String {
    let mut body = screen.clone();
    body.status = None;
    body.content_hash = None;
    let json = serde_json::to_string(&body).expect("a screen serializes to JSON");
    blake3::hash(json.as_bytes()).to_hex().to_string()
}

/// Every authored screen file of a project that parsed, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct ScreenFacts {
    /// The files, in path order.
    pub files: Vec<ScreenFile>,
}

impl ScreenFacts {
    /// Read and parse `<root>/design/screens/*.screen.toml`; a missing directory gives no files,
    /// and an unreadable or invalid file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(SCREENS_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    p.file_name()
                        .is_some_and(|n| n.to_string_lossy().ends_with(SCREEN_SUFFIX))
                })
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<ScreenFile> = paths
            .into_iter()
            .filter_map(|path| {
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %path.display(), %err, "screen file unreadable; skipped");
                    })
                    .ok()?;
                let rel = site_path(spec, &path);
                let screen = parse_screen_file(&text)
                    .inspect_err(|err| tracing::warn!(path = %rel, %err, "screen file invalid; skipped"))
                    .ok()?;
                tracing::debug!(path = %rel, states = screen.states.len(), "screen file loaded");
                Some(ScreenFile {
                    path: rel,
                    text,
                    screen,
                })
            })
            .collect();
        Self { files }
    }

    /// A stable digest of the files' paths and texts, for the repo digest.
    pub fn fingerprint(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        for file in &self.files {
            hasher.update(file.path.as_bytes());
            hasher.update(b"\0");
            hasher.update(file.text.as_bytes());
            hasher.update(b"\0");
        }
        hasher.finalize().to_hex().to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn file(text: &str) -> ScreenFile {
        ScreenFile {
            path: "design/screens/a.screen.toml".into(),
            text: text.into(),
            screen: parse_screen_file(text).expect("parses"),
        }
    }

    const TEXT: &str =
        "id = \"a\"\nentry = \"/\"\nkinds = [\"form\"]\n[[states]]\nid = \"error\"\n";

    // frob:tests crates/crunk-rules/src/screen_files.rs::ScreenFile.missing_states
    #[test]
    fn missing_states_lists_what_the_kind_still_needs() {
        let f = file(TEXT);
        assert_eq!(
            f.missing_states(ScreenKind::Form),
            ["success", "validation"]
        );
        assert!(f.missing_states(ScreenKind::DataBound).contains(&"loading"));
    }

    // frob:tests crates/crunk-rules/src/screen_files.rs::ScreenFile.offset_of
    #[test]
    fn offset_of_finds_a_top_level_key_line() {
        let f = file(TEXT);
        assert_eq!(f.offset_of("kinds"), TEXT.find("kinds").expect("kinds"));
        assert_eq!(f.offset_of("nope"), 0);
    }

    // frob:tests crates/crunk-rules/src/screen_files.rs::content_hash
    #[test]
    fn content_hash_ignores_status_and_the_hash_itself() {
        let mut s = file(TEXT).screen;
        let h = content_hash(&s);
        s.status = Some(crunk_spec::table::ScreenStatus::Ready);
        s.content_hash = Some("x".into());
        assert_eq!(content_hash(&s), h);
        s.headings.push("Hi".into());
        assert_ne!(content_hash(&s), h);
    }

    // frob:tests crates/crunk-rules/src/screen_files.rs::ScreenFacts.fingerprint
    #[test]
    fn fingerprint_changes_with_the_text() {
        let a = ScreenFacts {
            files: vec![file(TEXT)],
        };
        let b = ScreenFacts {
            files: vec![file(&format!("{TEXT}# x\n"))],
        };
        assert_ne!(a.fingerprint(), b.fingerprint());
    }
}
