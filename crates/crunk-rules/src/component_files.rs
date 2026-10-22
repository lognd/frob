//! The authored component spec files (`design/components/*.component.toml`) as the COMP and STATE
//! rules read them: each parsed into a [`ComponentConfig`] with its text kept so findings anchor.

// frob:ticket 01M4CXR7CHD30VMWHMRD6TTN3F

use crunk_spec::DesignSpec;
use crunk_spec::component_file::{ComponentConfig, parse_component_file};
use crunk_spec::table::{ScreenKind, ScreenStatus};
use crunk_tokens::model::TokenSet;

use crate::screen_files::required_states;
use crate::sheets::site_path;
use crate::token_files::TokenFacts;

/// The project directory holding the authored component files, relative to the root.
pub const COMPONENTS_DIR: &str = "design/components";

/// The file suffix that marks a component file.
pub const COMPONENT_SUFFIX: &str = ".component.toml";

/// The smallest pointer target, in CSS pixels, an interactive component may declare (WCAG 2.2 AA).
pub const MIN_TARGET_PX: u32 = 24;

/// One component file that parsed.
#[derive(Debug, Clone)]
pub struct ComponentFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed component.
    pub component: ComponentConfig,
}

impl ComponentFile {
    /// Byte offset of the first line containing `needle`, 0 when no line does.
    #[must_use]
    pub fn offset_of(&self, needle: &str) -> usize {
        let mut at = 0;
        for line in self.text.split_inclusive('\n') {
            if line.contains(needle) {
                return at;
            }
            at += line.len();
        }
        0
    }

    /// The state ids this component declares.
    pub fn state_ids(&self) -> impl Iterator<Item = &str> {
        self.component.states.iter().map(|s| s.id.as_str())
    }

    /// The states `kind` requires that this component does not declare, in requirement order.
    #[must_use]
    pub fn missing_states(&self, kind: ScreenKind) -> Vec<&'static str> {
        required_states(kind)
            .iter()
            .copied()
            .filter(|need| !self.state_ids().any(|id| id == *need))
            .collect()
    }

    /// Whether the component is `ready` or `completed`.
    #[must_use]
    pub fn is_locked(&self) -> bool {
        matches!(
            self.component.status,
            Some(ScreenStatus::Ready | ScreenStatus::Completed)
        )
    }
}

/// The token sets a component's bindings resolve against: the spec's own tokens and every
/// compiled `design/tokens` file.
#[derive(Debug, Clone, Default)]
pub struct TokenLookup {
    sets: Vec<TokenSet>,
}

impl TokenLookup {
    /// Gather the sets of `spec` and `tokens`; an uncompilable spec or file contributes nothing.
    #[must_use]
    pub fn new(spec: Option<&DesignSpec>, tokens: Option<&TokenFacts>) -> Self {
        let mut sets = Vec::new();
        if let Some(Ok(set)) = spec.map(TokenSet::from_spec) {
            sets.push(set);
        }
        if let Some(facts) = tokens {
            sets.extend(facts.ok_sets().map(|(_, set)| set.clone()));
        }
        Self { sets }
    }

    /// Whether no set was gathered, so no token can be judged unknown.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.sets.is_empty()
    }

    /// Whether any set defines `name`.
    #[must_use]
    pub fn knows(&self, name: &str) -> bool {
        self.sets.iter().any(|set| set.get(name).is_some())
    }

    /// The JSON of the resolved default-mode value of `name`, from the first set that has it.
    #[must_use]
    pub fn resolved_json(&self, name: &str) -> Option<String> {
        self.sets
            .iter()
            .find_map(|set| set.resolve(name, None))
            .and_then(|v| serde_json::to_string(v).ok())
    }
}

/// The content hash of a component: blake3 over its canonical JSON with `status` and
/// `content_hash` cleared, followed by the resolved value of every distinct bound token (in name
/// order), so changing a token a component binds invalidates the hash. A token that does not
/// resolve contributes its name only.
///
/// # Panics
/// Never in practice: a `ComponentConfig` always serializes to JSON.
#[must_use]
pub fn component_hash(component: &ComponentConfig, tokens: &TokenLookup) -> String {
    let mut body = component.clone();
    body.status = None;
    body.content_hash = None;
    let json = serde_json::to_string(&body).expect("a component serializes to JSON");
    let mut hasher = blake3::Hasher::new();
    hasher.update(json.as_bytes());
    let mut names: Vec<&str> = component
        .bindings
        .iter()
        .filter_map(|b| b.token.as_deref())
        .collect();
    names.sort_unstable();
    names.dedup();
    for name in names {
        hasher.update(b"\0");
        hasher.update(name.as_bytes());
        if let Some(v) = tokens.resolved_json(name) {
            hasher.update(b"=");
            hasher.update(v.as_bytes());
        }
    }
    hasher.finalize().to_hex().to_string()
}

/// Every authored component file of a project that parsed, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct ComponentFacts {
    /// The files, in path order.
    pub files: Vec<ComponentFile>,
}

impl ComponentFacts {
    /// Read and parse `<root>/design/components/*.component.toml`; a missing directory gives no
    /// files, and an unreadable or invalid file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(COMPONENTS_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    p.file_name()
                        .is_some_and(|n| n.to_string_lossy().ends_with(COMPONENT_SUFFIX))
                })
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<ComponentFile> = paths
            .into_iter()
            .filter_map(|path| {
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %path.display(), %err, "component file unreadable; skipped");
                    })
                    .ok()?;
                let rel = site_path(spec, &path);
                let component = parse_component_file(&text)
                    .inspect_err(|err| tracing::warn!(path = %rel, %err, "component file invalid; skipped"))
                    .ok()?;
                tracing::debug!(path = %rel, name = %component.name, "component file loaded");
                Some(ComponentFile {
                    path: rel,
                    text,
                    component,
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

    fn file(text: &str) -> ComponentFile {
        ComponentFile {
            path: "design/components/a.component.toml".into(),
            text: text.into(),
            component: parse_component_file(text).expect("parses"),
        }
    }

    const TEXT: &str = "name = \"a\"\nkinds = [\"form\"]\n[[states]]\nid = \"error\"\n";

    // frob:tests crates/crunk-rules/src/component_files.rs::ComponentFile.missing_states
    #[test]
    fn missing_states_lists_what_the_kind_still_needs() {
        let f = file(TEXT);
        assert_eq!(
            f.missing_states(ScreenKind::Form),
            ["success", "validation"]
        );
        assert_eq!(f.missing_states(ScreenKind::DataBound).len(), 3);
    }

    // frob:tests crates/crunk-rules/src/component_files.rs::ComponentFile.offset_of
    #[test]
    fn offset_of_finds_a_line_and_defaults_to_zero() {
        let f = file(TEXT);
        assert_eq!(f.offset_of("kinds"), TEXT.find("kinds").expect("kinds"));
        assert_eq!(f.offset_of("nope"), 0);
    }

    // frob:tests crates/crunk-rules/src/component_files.rs::ComponentFile.is_locked
    #[test]
    fn is_locked_for_ready_and_completed_only() {
        assert!(!file(TEXT).is_locked());
        assert!(file("name = \"a\"\nstatus = \"ready\"\n").is_locked());
        assert!(file("name = \"a\"\nstatus = \"completed\"\n").is_locked());
        assert!(!file("name = \"a\"\nstatus = \"draft\"\n").is_locked());
    }

    // frob:tests crates/crunk-rules/src/component_files.rs::component_hash
    #[test]
    fn component_hash_ignores_status_and_the_hash_itself() {
        let mut c = file(TEXT).component;
        let h = component_hash(&c, &TokenLookup::default());
        c.status = Some(ScreenStatus::Ready);
        c.content_hash = Some("x".into());
        assert_eq!(component_hash(&c, &TokenLookup::default()), h);
        c.props.clear();
        c.states.clear();
        assert_ne!(component_hash(&c, &TokenLookup::default()), h);
    }

    // frob:tests crates/crunk-rules/src/component_files.rs::TokenLookup.knows
    #[test]
    fn an_empty_lookup_is_empty_and_knows_nothing() {
        let t = TokenLookup::new(None, None);
        assert!(t.is_empty());
        assert!(!t.knows("anything"));
        assert_eq!(t.resolved_json("anything"), None);
    }

    // frob:tests crates/crunk-rules/src/component_files.rs::ComponentFacts.fingerprint
    #[test]
    fn fingerprint_changes_with_the_text() {
        let a = ComponentFacts {
            files: vec![file(TEXT)],
        };
        let b = ComponentFacts {
            files: vec![file(&format!("{TEXT}# x\n"))],
        };
        assert_ne!(a.fingerprint(), b.fingerprint());
        assert_eq!(
            ComponentFacts::default().fingerprint(),
            ComponentFacts::default().fingerprint()
        );
    }
}
