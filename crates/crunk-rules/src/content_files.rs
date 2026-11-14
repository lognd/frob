//! The authored content files (`design/content/*.toml`) as the CONTENT rules read them, and the
//! copy a scene document carries: literal text that should be a key, and the keys it references.

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
// frob:ticket 01M5HM3W7MK7255AGEN27SXEXP
// frob:ticket 01M5H5P5E98XTANP62H5TVTSC4

use std::collections::{BTreeMap, BTreeSet};

use crunk_scene::ElementKind;
use crunk_spec::voice_file::{VoiceRules, parse_voice_rules};
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

/// The props of a component instance (`<Button label="Save">`) whose value is read by people, so
/// is copy; each is keyed with `data-copy-<prop>` like a copy attribute. Other props
/// (`variant="primary"`) are options, not copy.
pub const COMPONENT_TEXT_PROPS: &[&str] = &[
    "label",
    "text",
    "caption",
    "heading",
    "headline",
    "subtitle",
    "description",
    "message",
    "content",
    "tooltip",
];

/// Tags that never have a closing tag, so do not open a nesting level.
const VOID_TAGS: &[&str] = &[
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track",
    "wbr",
];

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

    /// Read the voice file under `spec`'s root, with the glossary and tone rules it carries; an
    /// unreadable file counts as present with no rules, and so does one whose rules do not parse.
    #[must_use]
    pub fn load(spec: &DesignSpec) -> (Self, VoiceRules) {
        let path = spec.root.join(CONTENT_DIR).join(VOICE_FILE);
        if !path.is_file() {
            return (Self::Missing, VoiceRules::default());
        }
        match std::fs::read_to_string(&path) {
            Ok(text) => {
                let rules = parse_voice_rules(&text).unwrap_or_else(|err| {
                    tracing::warn!(%err, "voice rules invalid; glossary and tone rules skipped");
                    VoiceRules::default()
                });
                (Self::of_text(&text), rules)
            }
            Err(err) => {
                tracing::warn!(%err, "voice file unreadable; counted as present");
                (Self::Present, VoiceRules::default())
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
    /// The glossary and banned words `design/content/voice.toml` declares.
    pub rules: VoiceRules,
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
        let (voice, rules) = VoiceFile::load(spec);
        tracing::debug!(
            ?voice,
            banned = rules.banned.len(),
            terms = rules.glossary.len(),
            "voice file state"
        );
        Self {
            files,
            voice,
            rules,
        }
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
        hasher.update(format!("{:?}", self.rules).as_bytes());
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
    /// The attribute (or component prop) that holds it, `None` for text.
    pub attribute: Option<String>,
    /// Whether the text sits outside every element (a top-level text node of the scene).
    pub top_level: bool,
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
                    top_level: false,
                    suggested_key: suggest_key(&file.path, label, None),
                    reference_attr: COPY_ATTR.to_owned(),
                });
            }
        }
        for (name, value) in &el.attributes {
            let is_text_prop =
                el.kind == ElementKind::Component && COMPONENT_TEXT_PROPS.contains(&name.as_str());
            if (COPY_ATTRIBUTES.contains(&name.as_str()) || is_text_prop)
                && is_copy(value)
                && !has(&format!("{COPY_ATTR}-{name}"))
            {
                out.push(LiteralCopy {
                    offset: el.offset,
                    line: el.line,
                    literal: value.trim().to_owned(),
                    attribute: Some(name.clone()),
                    top_level: false,
                    suggested_key: suggest_key(&file.path, label, Some(name)),
                    reference_attr: format!("{COPY_ATTR}-{name}"),
                });
            }
        }
    }
    for (n, (offset, text)) in top_level_text(&file.text).into_iter().enumerate() {
        // The adapter hangs text after a void tag on that tag; the element hit already has it.
        let owned_by_void = file.doc.elements.iter().any(|el| {
            VOID_TAGS.contains(&el.tag.to_ascii_lowercase().as_str())
                && el.offset < offset
                && el.text.contains(&text)
        });
        if !is_copy(&text) || owned_by_void {
            continue;
        }
        let label = if n == 0 {
            "text".to_owned()
        } else {
            format!("text {}", n + 1)
        };
        tracing::debug!(path = %file.path, offset, "top-level text node is literal copy");
        out.push(LiteralCopy {
            offset,
            line: line_at(&file.text, offset),
            literal: text,
            attribute: None,
            top_level: true,
            suggested_key: suggest_key(&file.path, &label, None),
            reference_attr: COPY_ATTR.to_owned(),
        });
    }
    out
}

/// 1-based line of byte `offset` in `text`.
fn line_at(text: &str, offset: usize) -> u32 {
    let newlines = text[..offset.min(text.len())].matches('\n').count();
    u32::try_from(newlines + 1).unwrap_or(u32::MAX)
}

/// The trimmed, non-empty text runs of `src` that sit outside every element, each with the byte
/// offset of its first character. A light tag scan: comments, doctypes, void and self-closing
/// tags, quoted attribute values and `<style>`/`<script>` bodies are skipped over.
fn top_level_text(src: &str) -> Vec<(usize, String)> {
    let bytes = src.as_bytes();
    let mut out = Vec::new();
    let (mut depth, mut i, mut run) = (0usize, 0usize, 0usize);
    let mut flush = |from: usize, to: usize, depth: usize| {
        if depth == 0 && from < to {
            let raw = &src[from..to];
            let lead = raw.len() - raw.trim_start().len();
            let text = raw.trim();
            if !text.is_empty() {
                out.push((from + lead, text.to_owned()));
            }
        }
    };
    while i < bytes.len() {
        if bytes[i] != b'<' {
            i += 1;
            continue;
        }
        flush(run, i, depth);
        let rest = &src[i..];
        if rest.starts_with("<!--") {
            i += rest.find("-->").map_or(rest.len(), |e| e + 3);
        } else if rest.starts_with("<!") || rest.starts_with("<?") {
            i += rest.find('>').map_or(rest.len(), |e| e + 1);
        } else if rest.starts_with("</") {
            depth = depth.saturating_sub(1);
            i += rest.find('>').map_or(rest.len(), |e| e + 1);
        } else if rest[1..].starts_with(|c: char| c.is_ascii_alphabetic()) {
            let name: String = rest[1..]
                .chars()
                .take_while(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | ':'))
                .collect::<String>()
                .to_ascii_lowercase();
            let mut j = 1;
            let mut quote_ch = None;
            let rb = rest.as_bytes();
            while j < rb.len() {
                match (quote_ch, rb[j]) {
                    (Some(q), c) if c == q => quote_ch = None,
                    (None, b'"' | b'\'') => quote_ch = Some(rb[j]),
                    (None, b'>') => break,
                    _ => {}
                }
                j += 1;
            }
            let self_closing = j > 0 && j <= rb.len() && rb.get(j - 1) == Some(&b'/');
            i += (j + 1).min(rest.len());
            if self_closing || VOID_TAGS.contains(&name.as_str()) {
                // no nesting level
            } else if name == "style" || name == "script" {
                let tail = &src[i..];
                let close = format!("</{name}");
                let at = tail.to_ascii_lowercase().find(&close).unwrap_or(tail.len());
                i += at;
                i += src[i..].find('>').map_or(src.len() - i, |e| e + 1);
            } else {
                depth += 1;
            }
        } else {
            i += 1;
            continue;
        }
        run = i;
    }
    flush(run, bytes.len().min(src.len()), depth);
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

/// One key a locale lacks that another locale defines.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocaleGap {
    /// The locale that lacks the key (`default` for files that declare no locale).
    pub locale: String,
    /// The first file of that locale, where the finding anchors.
    pub path: String,
    /// The missing key.
    pub key: String,
    /// A locale that does define the key.
    pub defined_in: String,
}

/// Every key some locale defines that another locale lacks; empty with fewer than two locales.
#[must_use]
pub fn locale_gaps(facts: &ContentFacts) -> Vec<LocaleGap> {
    let mut by_locale: BTreeMap<String, (String, BTreeSet<&str>)> = BTreeMap::new();
    for f in &facts.files {
        let name = f
            .content
            .locale
            .clone()
            .unwrap_or_else(|| "default".to_owned());
        let entry = by_locale
            .entry(name)
            .or_insert_with(|| (f.path.clone(), BTreeSet::new()));
        entry.1.extend(f.content.keys.iter().map(|k| k.id.as_str()));
    }
    let mut owner: BTreeMap<&str, &str> = BTreeMap::new();
    for (locale, (_, keys)) in &by_locale {
        for key in keys {
            owner.entry(key).or_insert(locale);
        }
    }
    let mut gaps = Vec::new();
    if by_locale.len() < 2 {
        return gaps;
    }
    for (locale, (path, keys)) in &by_locale {
        for (key, defined_in) in &owner {
            if !keys.contains(key) {
                gaps.push(LocaleGap {
                    locale: locale.clone(),
                    path: path.clone(),
                    key: (*key).to_owned(),
                    defined_in: (*defined_in).to_owned(),
                });
            }
        }
    }
    gaps
}

/// Whether `text` uses `term` as a whole word or phrase, ignoring case: the characters on either
/// side of a match are not letters or digits, so `log in` is in `Log in now` but not in `catalog in`.
#[must_use]
pub fn uses_term(text: &str, term: &str) -> bool {
    let needle = term.trim().to_lowercase();
    if needle.is_empty() {
        return false;
    }
    let hay = text.to_lowercase();
    hay.match_indices(&needle).any(|(at, m)| {
        let before = hay[..at].chars().next_back();
        let after = hay[at + m.len()..].chars().next();
        !before.is_some_and(char::is_alphanumeric) && !after.is_some_and(char::is_alphanumeric)
    })
}

/// One content key's text that breaks a voice rule, for CONTENT005 and CONTENT006.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VoiceHit {
    /// The file defining the key, relative to the project root.
    pub path: String,
    /// Byte offset of the key's id in that file.
    pub offset: usize,
    /// The key's id.
    pub key: String,
    /// The term found in the text (the avoided variant or the banned word, as the voice file spells it).
    pub found: String,
    /// The glossary's preferred term for `found`, `None` for a banned word.
    pub preferred: Option<String>,
}

/// Every key text in `facts` that uses an avoided glossary variant, in file then key order.
#[must_use]
pub fn glossary_hits(facts: &ContentFacts) -> Vec<VoiceHit> {
    let mut out = Vec::new();
    for file in &facts.files {
        for key in &file.content.keys {
            for term in &facts.rules.glossary {
                for variant in term.avoid.iter().filter(|v| uses_term(&key.text, v)) {
                    out.push(VoiceHit {
                        path: file.path.clone(),
                        offset: file.offset_of_key(&key.id),
                        key: key.id.clone(),
                        found: variant.clone(),
                        preferred: Some(term.preferred.clone()),
                    });
                }
            }
        }
    }
    out
}

/// Every key text in `facts` that uses a banned word or phrase, in file then key order.
#[must_use]
pub fn banned_hits(facts: &ContentFacts) -> Vec<VoiceHit> {
    let mut out = Vec::new();
    for file in &facts.files {
        for key in &file.content.keys {
            for word in facts
                .rules
                .banned
                .iter()
                .filter(|w| uses_term(&key.text, w))
            {
                out.push(VoiceHit {
                    path: file.path.clone(),
                    offset: file.offset_of_key(&key.id),
                    key: key.id.clone(),
                    found: word.clone(),
                    preferred: None,
                });
            }
        }
    }
    out
}
