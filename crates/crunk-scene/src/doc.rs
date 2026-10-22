//! A parsed scene: its elements (tags, `data-id`, nesting) and every CSS declaration, read from the
//! gob HTML adapter's term.

// frob:ticket 01M4CXRDTCFVJ4VPZKAJ22BXS0

use std::collections::{BTreeMap, HashMap};

use gob_ir::{Location, Model, NodeId, const_value::Value, markup, style};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};

use crate::dialect::KNOWN_TAGS;

/// The attribute that gives an element its stable identity.
const DATA_ID: &str = "data-id";

/// Why a scene could not be read at all (never bad markup: that parses partially).
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum SceneError {
    /// The bytes are not UTF-8.
    #[error("scene is not valid UTF-8 (first bad byte at offset {offset})")]
    NotUtf8 {
        /// Offset of the first invalid byte.
        offset: usize,
    },
    /// The HTML adapter built an ill-formed term (an adapter bug).
    #[error("cannot fold the scene: {0}")]
    Fold(String),
}

/// What kind of tag an element is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ElementKind {
    /// A lowercase tag of [`KNOWN_TAGS`].
    Html,
    /// A capitalised tag: a component instance such as `<Button variant="primary">`.
    Component,
    /// A lowercase tag outside the dialect (`<blink>`, `<my-widget>`).
    Unknown,
}

/// One element of the scene.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SceneElement {
    /// The tag as written (a component keeps its capitals).
    pub tag: String,
    /// Whether the tag is HTML, a component or unknown.
    pub kind: ElementKind,
    /// The `data-id` value, when the element has a plain one.
    pub data_id: Option<String>,
    /// Attributes other than `data-id`, names lowercase, in source order; a bare attribute is `true`.
    pub attributes: Vec<(String, String)>,
    /// Index into [`SceneDoc::elements`] of the parent element; `None` for a top-level element.
    pub parent: Option<usize>,
    /// Byte offset of the start tag.
    pub offset: usize,
    /// 1-based line of the start tag.
    pub line: u32,
}

/// One CSS declaration of a `<style>` body or an inline `style` attribute.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SceneDecl {
    /// The property as written, trimmed (case kept so a finding quotes the source).
    pub property: String,
    /// The value text.
    pub value: String,
    /// The enclosing at-rule's name (`media`, `keyframes`), when there is one.
    pub at_rule: Option<String>,
    /// Byte offset of the declaration.
    pub offset: usize,
    /// 1-based line of the declaration.
    pub line: u32,
}

/// A parsed scene.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SceneDoc {
    /// Every element in source order.
    pub elements: Vec<SceneElement>,
    /// Every non-custom-property declaration in source order.
    pub declarations: Vec<SceneDecl>,
    /// The names of the at-rules the stylesheets use, in source order (`media`, `font-face`).
    pub at_rules: Vec<String>,
}

impl SceneDoc {
    /// The `data-id` values used by more than one element, sorted, each once.
    pub fn duplicate_data_ids(&self) -> Vec<&str> {
        let mut seen: BTreeMap<&str, usize> = BTreeMap::new();
        for id in self.elements.iter().filter_map(|e| e.data_id.as_deref()) {
            *seen.entry(id).or_default() += 1;
        }
        seen.into_iter()
            .filter_map(|(id, n)| (n > 1).then_some(id))
            .collect()
    }

    /// The elements that are components, in source order.
    pub fn components(&self) -> impl Iterator<Item = &SceneElement> {
        self.elements
            .iter()
            .filter(|e| e.kind == ElementKind::Component)
    }
}

/// Parse a scene from raw bytes; the bytes must be UTF-8.
///
/// # Errors
///
/// [`SceneError::NotUtf8`] for invalid UTF-8, [`SceneError::Fold`] for an adapter bug.
pub fn parse_scene_bytes(bytes: &[u8]) -> Result<SceneDoc, SceneError> {
    match std::str::from_utf8(bytes) {
        Ok(text) => parse_scene_html(text),
        Err(err) => {
            tracing::warn!(offset = err.valid_up_to(), "scene is not UTF-8");
            Err(SceneError::NotUtf8 {
                offset: err.valid_up_to(),
            })
        }
    }
}

/// Parse a scene's text. Malformed markup or CSS never fails: the adapter keeps the partial parse.
///
/// # Errors
///
/// [`SceneError::Fold`] when the HTML adapter builds an ill-formed term (an adapter bug).
pub fn parse_scene_html(text: &str) -> Result<SceneDoc, SceneError> {
    if text.trim().is_empty() {
        tracing::debug!("scene is empty");
        return Ok(SceneDoc::default());
    }
    let entry = FileEntry {
        path: "scene.html".to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path("scene.html"),
    };
    let folded = fold_file(&entry, text).map_err(|e| SceneError::Fold(e.to_string()))?;
    let model = Model::new(folded.term, folded.scopes);
    let lines = LineIndex::of(text);

    let raw_elements = markup::elements(&model);
    let mut parents: HashMap<NodeId, usize> = HashMap::new();
    for (i, el) in raw_elements.iter().enumerate() {
        for child in &el.children {
            if let markup::Child::Element(c) = child {
                parents.insert(*c, i);
            }
        }
    }
    let mut elements: Vec<SceneElement> = raw_elements
        .iter()
        .map(|el| {
            let offset = start_of(&model, el.node).unwrap_or(0);
            let tag = written_tag(text, offset)
                .or_else(|| el.tag.clone())
                .unwrap_or_default();
            let kind = classify(&tag);
            let mut data_id = None;
            let mut attributes = Vec::new();
            for attr in &el.attributes {
                let Some(name) = attr.name.as_deref() else {
                    continue;
                };
                let value = match markup::attribute_value(&model, attr).known() {
                    Some(Value::Str(s)) => s.clone(),
                    Some(Value::Bool(true)) | None => "true".to_owned(),
                    Some(other) => format!("{other:?}"),
                };
                if name == DATA_ID {
                    data_id = Some(value);
                } else {
                    attributes.push((name.to_owned(), value));
                }
            }
            SceneElement {
                tag,
                kind,
                data_id,
                attributes,
                parent: parents.get(&el.node).copied(),
                offset,
                line: lines.line_of(offset),
            }
        })
        .collect();
    sort_source_order(&mut elements);

    let at_rule_names: HashMap<NodeId, String> = style::at_rules(&model)
        .into_iter()
        .map(|a| (a.node, a.name))
        .collect();
    let declarations = style::declarations(&model)
        .into_iter()
        .filter(|d| !d.property.starts_with("--"))
        .map(|d| {
            let offset = start_of(&model, d.node).unwrap_or(0);
            SceneDecl {
                property: d.property.trim().to_owned(),
                value: d.raw.trim().to_owned(),
                at_rule: d.owner.and_then(|o| at_rule_names.get(&o).cloned()),
                offset,
                line: lines.line_of(offset),
            }
        })
        .collect();
    let at_rules = style::at_rules(&model)
        .into_iter()
        .map(|a| a.name)
        .collect();
    let doc = SceneDoc {
        elements,
        declarations,
        at_rules,
    };
    tracing::debug!(
        elements = doc.elements.len(),
        declarations = doc.declarations.len(),
        "scene parsed"
    );
    Ok(doc)
}

/// Byte offset where `node` starts, when it has a text location.
fn start_of(model: &Model, node: NodeId) -> Option<usize> {
    match model.term().node(node).location() {
        Location::Text { range, .. } => Some(u32::from(range.start()) as usize),
        _ => None,
    }
}

/// The tag name written at `offset` (`<Button ...` gives `Button`); the adapter lowercases tags, so
/// the source is the only place a component's capitals survive.
fn written_tag(text: &str, offset: usize) -> Option<String> {
    let rest = text.get(offset..)?.strip_prefix('<')?;
    let name: String = rest
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | ':'))
        .collect();
    (!name.is_empty()).then_some(name)
}

/// Classify a written tag.
fn classify(tag: &str) -> ElementKind {
    if tag.chars().next().is_some_and(|c| c.is_ascii_uppercase()) {
        ElementKind::Component
    } else if KNOWN_TAGS.contains(&tag.to_ascii_lowercase().as_str()) {
        ElementKind::Html
    } else {
        ElementKind::Unknown
    }
}

/// Byte offsets of line starts (`\n` terminated, so CRLF and LF agree).
struct LineIndex(Vec<usize>);

impl LineIndex {
    fn of(text: &str) -> Self {
        let mut starts = vec![0];
        starts.extend(text.match_indices('\n').map(|(i, _)| i + 1));
        Self(starts)
    }

    /// 1-based line holding `offset`.
    fn line_of(&self, offset: usize) -> u32 {
        let n = self.0.partition_point(|&s| s <= offset);
        u32::try_from(n).unwrap_or(u32::MAX)
    }
}

/// Reorder `elements` by start offset and remap each `parent` index (the adapter lists children
/// before parents).
fn sort_source_order(elements: &mut Vec<SceneElement>) {
    let mut order: Vec<usize> = (0..elements.len()).collect();
    order.sort_by_key(|&i| elements[i].offset);
    let mut new_index = vec![0; elements.len()];
    for (new, &old) in order.iter().enumerate() {
        new_index[old] = new;
    }
    let mut sorted: Vec<SceneElement> = order.iter().map(|&i| elements[i].clone()).collect();
    for el in &mut sorted {
        el.parent = el.parent.map(|p| new_index[p]);
    }
    *elements = sorted;
}
