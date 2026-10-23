//! The authored content files (`design/content/*.toml`) as the CONTENT rules read them, and the
//! copy a scene document carries: literal text that should be a key, and the keys it references.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
// frob:ticket 01M5HM3W7MK7255AGEN27SXEXP

use std::collections::BTreeMap;

use crunk_spec::{ContentFile, DesignSpec, parse_content_file};

use crate::scene_docs::{SCENE_DOC_SUFFIX, SceneDocFile};
use crate::sheets::site_path;

/// The project directory holding the authored content files, relative to the root.
pub const CONTENT_DIR: &str = "design/content";

/// The voice and tone file's name inside [`CONTENT_DIR`]; it is not a copy file.
pub const VOICE_FILE: &str = "voice.toml";

/// The attribute that makes an element's text a reference to a copy key.
pub const COPY_ATTR: &str = "data-copy";

/// The attributes whose value is read by people (so is copy); each is keyed with
/// `data-copy-<attribute>`.
pub const COPY_ATTRIBUTES: &[&str] = &["alt", "aria-label", "placeholder", "title"];

/// The longest literal quoted in a finding, in characters.
const QUOTE_MAX: usize = 40;

/// One content file that parsed.
#[derive(Debug, Clone)]
pub struct ContentDocFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed content.
    pub content: ContentFile,
}

impl ContentDocFile {
    /// Byte offset of the `"<id>"` string that names key `id`, 0 when it cannot be found.
    #[must_use]
    pub fn offset_of_key(&self, id: &str) -> usize {
        self.text.find(&format!("\"{id}\"")).unwrap_or(0)
    }
}

/// What `design/content/voice.toml` is on disk (CRAFT013).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum VoiceFile {
    /// No such regular file.
    #[default]
    Missing,
    /// A file with no content but whitespace and `#` comments: a placeholder, not a voice.
    Blank,
    /// A file with content; whether it is well formed is not this fact's concern.
    Present,
}

impl VoiceFile {
    /// Classify a voice file's text: no line besides blanks and `#` comments is `Blank`.
    #[must_use]
    pub fn of_text(text: &str) -> Self {
        let live = text
            .lines()
            .map(str::trim)
            .any(|l| !l.is_empty() && !l.starts_with('#'));
        if live { Self::Present } else { Self::Blank }
    }

    /// Read the voice file under `spec`'s root; an unreadable file counts as present.
    #[must_use]
    pub fn load(spec: &DesignSpec) -> Self {
        let path = spec.root.join(CONTENT_DIR).join(VOICE_FILE);
        if !path.is_file() {
            return Self::Missing;
        }
        match std::fs::read_to_string(&path) {
            Ok(text) => Self::of_text(&text),
            Err(err) => {
                tracing::warn!(%err, "voice file unreadable; counted as present");
                Self::Present
            }
        }
    }
}

/// Every content file of a project that parsed, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct ContentFacts {
    /// The files, in path order (the voice file is not one).
    pub files: Vec<ContentDocFile>,
    /// The state of `design/content/voice.toml`.
    pub voice: VoiceFile,
}

impl ContentFacts {
    /// Read and parse `<root>/design/content/*.toml`; a missing directory gives no files, and an
    /// unreadable or invalid file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(CONTENT_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| p.extension().is_some_and(|x| x == "toml"))
                .filter(|p| p.file_name().is_none_or(|n| n != VOICE_FILE))
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<ContentDocFile> = paths
            .into_iter()
            .filter_map(|path| {
                let rel = site_path(spec, &path);
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %rel, %err, "content file unreadable; skipped");
                    })
                    .ok()?;
                let content = parse_content_file(&text)
                    .inspect_err(
                        |err| tracing::warn!(path = %rel, %err, "content file invalid; skipped"),
                    )
                    .ok()?;
                tracing::debug!(path = %rel, keys = content.keys.len(), "content file loaded");
                Some(ContentDocFile {
                    path: rel,
                    text,
                    content,
                })
            })
            .collect();
        let voice = VoiceFile::load(spec);
        tracing::debug!(?voice, "voice file state");
        Self { files, voice }
    }

    /// How many keys the files define in all.
    #[must_use]
    pub fn key_count(&self) -> usize {
        self.files.iter().map(|f| f.content.keys.len()).sum()
    }

    /// Whether any file defines key `id`.
    #[must_use]
    pub fn defines(&self, id: &str) -> bool {
        self.files
            .iter()
            .any(|f| f.content.keys.iter().any(|k| k.id == id))
    }

    /// A stable digest of the files' paths and texts, for the repo digest.
    #[must_use]
    pub fn fingerprint(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        for file in &self.files {
            hasher.update(file.path.as_bytes());
            hasher.update(b"\0");
            hasher.update(file.text.as_bytes());
            hasher.update(b"\0");
        }
        hasher.update(format!("voice:{:?}", self.voice).as_bytes());
        hasher.finalize().to_hex().to_string()
    }
}

/// Literal copy found in a scene: text or an attribute that should be a content key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LiteralCopy {
    /// Byte offset of the owning element's start tag.
    pub offset: usize,
    /// 1-based line of that start tag.
    pub line: u32,
    /// The literal, trimmed.
    pub literal: String,
    /// The attribute that holds it, `None` for the element's text.
    pub attribute: Option<String>,
    /// The key to define, for example `home.hero_title`.
    pub suggested_key: String,
    /// The attribute that should reference the key (`data-copy` or `data-copy-<attribute>`).
    pub reference_attr: String,
}

/// A reference from a scene to a copy key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CopyRef {
    /// Byte offset of the owning element's start tag.
    pub offset: usize,
    /// 1-based line of that start tag.
    pub line: u32,
    /// The key as written, trimmed.
    pub key: String,
}

/// Whether `value` reads as human copy: it holds at least one letter, so empty, whitespace-only,
/// numeric and punctuation-only values (`"42"`, `"-"`, `"$1,000"`) are not copy.
#[must_use]
pub fn is_copy(value: &str) -> bool {
    value.chars().any(char::is_alphabetic)
}

/// The key a literal on element `data_id`/`tag` of scene `path` might be given: the scene's stem
/// then the element, lowercased with every non-alphanumeric run as `_`, plus the attribute.
#[must_use]
pub fn suggest_key(path: &str, label: &str, attribute: Option<&str>) -> String {
    let file = path.rsplit('/').next().unwrap_or(path);
    let stem = file.strip_suffix(SCENE_DOC_SUFFIX).unwrap_or(file);
    let mut parts = vec![slug(stem), slug(label)];
    if let Some(a) = attribute {
        parts.push(slug(a));
    }
    parts.retain(|p| !p.is_empty());
    parts.join(".")
}

fn slug(text: &str) -> String {
    let mut out = String::new();
    for c in text.chars() {
        if c.is_alphanumeric() {
            out.extend(c.to_lowercase());
        } else if !out.ends_with('_') && !out.is_empty() {
            out.push('_');
        }
    }
    out.trim_end_matches('_').to_owned()
}

/// `literal` cut to `QUOTE_MAX` characters with an ellipsis, for a finding.
#[must_use]
pub fn quote(literal: &str) -> String {
    if literal.chars().count() <= QUOTE_MAX {
        return literal.to_owned();
    }
    let cut: String = literal.chars().take(QUOTE_MAX).collect();
    format!("{cut}...")
}

/// The literal copy `file` carries, in source order. An element with `data-copy` has its text
/// taken as the key's stand-in render and is not flagged for it; an attribute is flagged unless
/// its `data-copy-<attribute>` twin is present.
#[must_use]
pub fn literal_copy(file: &SceneDocFile) -> Vec<LiteralCopy> {
    let mut out = Vec::new();
    for el in &file.doc.elements {
        let label = el.data_id.as_deref().unwrap_or(&el.tag);
        let has = |name: &str| el.attributes.iter().any(|(n, _)| n == name);
        if !has(COPY_ATTR) {
            for text in el.text.iter().filter(|t| is_copy(t)) {
                out.push(LiteralCopy {
                    offset: el.offset,
                    line: el.line,
                    literal: text.clone(),
                    attribute: None,
                    suggested_key: suggest_key(&file.path, label, None),
                    reference_attr: COPY_ATTR.to_owned(),
                });
            }
        }
        for (name, value) in &el.attributes {
            if COPY_ATTRIBUTES.contains(&name.as_str())
                && is_copy(value)
                && !has(&format!("{COPY_ATTR}-{name}"))
            {
                out.push(LiteralCopy {
                    offset: el.offset,
                    line: el.line,
                    literal: value.trim().to_owned(),
                    attribute: Some(name.clone()),
                    suggested_key: suggest_key(&file.path, label, Some(name)),
                    reference_attr: format!("{COPY_ATTR}-{name}"),
                });
            }
        }
    }
    out
}

/// The copy-key references `file` makes (`data-copy` and `data-copy-<attribute>`), in source order.
#[must_use]
pub fn copy_refs(file: &SceneDocFile) -> Vec<CopyRef> {
    let mut out = Vec::new();
    for el in &file.doc.elements {
        for (name, value) in &el.attributes {
            if name == COPY_ATTR || name.starts_with(&format!("{COPY_ATTR}-")) {
                out.push(CopyRef {
                    offset: el.offset,
                    line: el.line,
                    key: value.trim().to_owned(),
                });
            }
        }
    }
    out
}

/// Every key defined more than once across files, with the paths that define it (sorted).
#[must_use]
pub fn duplicate_keys(facts: &ContentFacts) -> BTreeMap<String, Vec<String>> {
    let mut by_key: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for f in &facts.files {
        for k in &f.content.keys {
            by_key.entry(k.id.clone()).or_default().push(f.path.clone());
        }
    }
    by_key.retain(|_, paths| paths.len() > 1);
    by_key
}
