//! SCENE002 to SCENE004: the structural facts of a scene the dialect restricts: every element has a
//! unique `data-id`, tags are HTML or components, and only supported at-rules appear.

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V

use std::collections::HashMap;

use crate::doc::{ElementKind, SceneDoc, SceneElement};

/// The at-rules a scene may use: `@media` only, since breakpoints are the one responsive tool.
pub const SUPPORTED_AT_RULES: &[&str] = &["media"];

/// Lowercase tags that are document scaffolding or non-rendered, so they carry no `data-id`.
const SCAFFOLD_TAGS: &[&str] = &["html", "head", "body", "style", "script"];

/// What is wrong with an element's `data-id`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DataIdProblem {
    /// No `data-id`, or an empty or blank one.
    Missing,
    /// The value was already used by an earlier element, which starts on `first_line`.
    Duplicate {
        /// The repeated value.
        id: String,
        /// Line of the first element using it.
        first_line: u32,
    },
}

/// One SCENE002 finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Scene002 {
    /// The tag as written.
    pub tag: String,
    /// The problem.
    pub problem: DataIdProblem,
    /// Byte offset of the element's start tag.
    pub offset: usize,
    /// 1-based line of the start tag.
    pub line: u32,
}

/// One SCENE003 finding: a lowercase tag outside the dialect.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Scene003 {
    /// The tag as written.
    pub tag: String,
    /// Byte offset of the start tag.
    pub offset: usize,
    /// 1-based line of the start tag.
    pub line: u32,
}

/// One SCENE004 finding: an at-rule outside [`SUPPORTED_AT_RULES`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Scene004 {
    /// The at-rule name without `@`.
    pub name: String,
    /// Byte offset of the at-rule.
    pub offset: usize,
    /// 1-based line of the at-rule.
    pub line: u32,
}

/// Whether `element` sits inside an `<svg>` (graphics content the dialect does not model).
fn inside_svg(doc: &SceneDoc, element: &SceneElement) -> bool {
    let mut at = element.parent;
    while let Some(i) = at {
        let parent = &doc.elements[i];
        if parent.tag.eq_ignore_ascii_case("svg") {
            return true;
        }
        at = parent.parent;
    }
    false
}

/// Whether an element must carry a `data-id`: HTML and component elements outside the scaffolding
/// tags and outside `<svg>` content. Unknown tags are SCENE003's.
fn needs_data_id(doc: &SceneDoc, element: &SceneElement) -> bool {
    element.kind != ElementKind::Unknown
        && !SCAFFOLD_TAGS.contains(&element.tag.to_ascii_lowercase().as_str())
        && !inside_svg(doc, element)
}

/// Elements missing a `data-id` (absent, empty or blank) or repeating one, in source order. A
/// repeat is reported on every element after the first; ids are scoped to one scene file.
pub fn data_id_problems(doc: &SceneDoc) -> Vec<Scene002> {
    let mut first: HashMap<&str, u32> = HashMap::new();
    let mut out = Vec::new();
    for el in &doc.elements {
        if !needs_data_id(doc, el) {
            continue;
        }
        let problem = match el.data_id.as_deref().map(str::trim) {
            None | Some("") => Some(DataIdProblem::Missing),
            Some(id) => {
                let seen = first.get(id).copied();
                if seen.is_none() {
                    first.insert(id, el.line);
                }
                seen.map(|first_line| DataIdProblem::Duplicate {
                    id: id.to_owned(),
                    first_line,
                })
            }
        };
        if let Some(problem) = problem {
            tracing::debug!(tag = %el.tag, line = el.line, ?problem, "SCENE002: data-id problem");
            out.push(Scene002 {
                tag: el.tag.clone(),
                problem,
                offset: el.offset,
                line: el.line,
            });
        }
    }
    out
}

/// Elements whose tag is neither a dialect HTML tag nor a component, in source order; `<svg>`
/// content is skipped.
pub fn unknown_tags(doc: &SceneDoc) -> Vec<Scene003> {
    doc.elements
        .iter()
        .filter(|e| e.kind == ElementKind::Unknown && !inside_svg(doc, e))
        .map(|e| {
            tracing::debug!(tag = %e.tag, line = e.line, "SCENE003: unknown tag");
            Scene003 {
                tag: e.tag.clone(),
                offset: e.offset,
                line: e.line,
            }
        })
        .collect()
}

/// Every at-rule outside [`SUPPORTED_AT_RULES`] (any case), nested ones included, in source order.
pub fn unsupported_at_rules(doc: &SceneDoc) -> Vec<Scene004> {
    doc.at_rule_sites
        .iter()
        .filter(|a| !SUPPORTED_AT_RULES.contains(&a.name.to_ascii_lowercase().as_str()))
        .map(|a| {
            tracing::debug!(name = %a.name, line = a.line, "SCENE004: unsupported at-rule");
            Scene004 {
                name: a.name.clone(),
                offset: a.offset,
                line: a.line,
            }
        })
        .collect()
}
