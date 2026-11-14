//! The T1 layout tells of the SLOP family (SLOP020, 021, 026, 027, 028, 029): analyses over a
//! parsed scene document and, where a tell is about measured geometry, its layout solve.
//!
//! A [`SceneView`] indexes one scene file (children, inline styles, solved nodes); each tell is a
//! function from a view to [`Tell`]s the rule anchors with `fire_in`. Styles are the elements'
//! inline `style` attributes, the only styling the T1 solver reads. When the scene does not solve
//! (a missing `data-id`, a `var()` the token map cannot resolve) the geometry-backed checks
//! fall back to what the text alone shows; they never invent geometry.

// frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP

use std::collections::{BTreeMap, BTreeSet, HashMap};

use crunk_layout::output::{SolvedNode, SolvedText};
use crunk_scene::SceneElement;

use crate::scene_docs::SceneDocFile;

/// A card trio: this many identical sibling cards is the tell.
const TRIO: usize = 3;
/// Card nesting depth at which SLOP021 fires.
const NESTING_LIMIT: usize = 3;
/// More lines than this make centred text a tell (SLOP026).
const CENTRED_LINE_LIMIT: usize = 3;
/// More characters than this make centred text a tell when no solve is available (SLOP026).
const CENTRED_CHAR_LIMIT: usize = 160;
/// Consecutive sections with one layout (SLOP027) or one band weight (SLOP029) that are a tell.
const SECTION_RUN: usize = 4;
/// Largest-to-smallest band weight below which the page has no density rhythm (SLOP029).
const DENSITY_FLOOR: f32 = 1.75;
/// Share of spacing declarations on one value above which spacing has no rhythm (SLOP028).
const SPACING_DOMINANCE: f64 = 0.8;
/// Spacing declarations needed before dominance means anything.
const SPACING_MIN_DECLS: usize = 5;
/// Pixel tolerance when comparing solved sizes of siblings.
const SIZE_EPS: f32 = 2.0;

/// One finding of a tell: where (byte offset in the scene file) and what.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Tell {
    /// Byte offset of the start tag the finding anchors to.
    pub offset: usize,
    /// The finding's message.
    pub message: String,
}

/// One scene file indexed for the layout tells.
#[derive(Debug)]
pub struct SceneView<'a> {
    file: &'a SceneDocFile,
    styles: Vec<BTreeMap<String, String>>,
    children: Vec<Vec<usize>>,
    roots: Vec<usize>,
    nodes: HashMap<&'a str, &'a SolvedNode>,
}

/// An inline `style` attribute as lowercase property to trimmed value.
fn parse_style(text: &str) -> BTreeMap<String, String> {
    text.split(';')
        .filter_map(|d| d.split_once(':'))
        .map(|(k, v)| (k.trim().to_ascii_lowercase(), v.trim().to_owned()))
        .filter(|(k, v)| !k.is_empty() && !v.is_empty())
        .collect()
}

/// Whether a CSS value is zero or `none`.
fn is_zero(value: &str) -> bool {
    let v = value.trim();
    v == "none"
        || v.strip_suffix("px")
            .or_else(|| v.strip_suffix("rem"))
            .unwrap_or(v)
            .parse::<f64>()
            .is_ok_and(|n| n == 0.0)
}

impl<'a> SceneView<'a> {
    /// Index `file`, solving it (cached on the file) for the geometry-backed tells.
    pub fn new(file: &'a SceneDocFile) -> Self {
        let elements = &file.doc.elements;
        let styles = elements
            .iter()
            .map(|e| {
                e.attributes
                    .iter()
                    .find(|(k, _)| k == "style")
                    .map(|(_, v)| parse_style(v))
                    .unwrap_or_default()
            })
            .collect();
        let mut children = vec![Vec::new(); elements.len()];
        let mut roots = Vec::new();
        for (i, e) in elements.iter().enumerate() {
            match e.parent {
                Some(p) => children[p].push(i),
                None => roots.push(i),
            }
        }
        let nodes = file
            .solve()
            .ok()
            .map(|s| s.nodes.iter().map(|n| (n.id.as_str(), n)).collect())
            .unwrap_or_default();
        Self {
            file,
            styles,
            children,
            roots,
            nodes,
        }
    }

    fn el(&self, i: usize) -> &SceneElement {
        &self.file.doc.elements[i]
    }

    fn style(&self, i: usize, prop: &str) -> Option<&str> {
        self.styles[i].get(prop).map(String::as_str)
    }

    fn node(&self, i: usize) -> Option<&SolvedNode> {
        self.nodes.get(self.el(i).data_id.as_deref()?).copied()
    }

    /// The solved text of element `i`: its own text node, or the synthetic `<id>::text` child.
    fn solved_text(&self, i: usize) -> Option<&SolvedText> {
        let id = self.el(i).data_id.as_deref()?;
        self.node(i).and_then(|n| n.text.as_ref()).or_else(|| {
            self.nodes
                .get(format!("{id}::text").as_str())?
                .text
                .as_ref()
        })
    }

    fn siblings(&self, parent: Option<usize>) -> &[usize] {
        parent.map_or(self.roots.as_slice(), |p| self.children[p].as_slice())
    }

    /// Whether `i` reads as a card: a background, a border or shadow, and a rounded corner.
    fn is_card(&self, i: usize) -> bool {
        let has = |p: &str| self.style(i, p).is_some_and(|v| !is_zero(v));
        let ground = has("background") || has("background-color");
        let edge = has("box-shadow")
            || self.styles[i].iter().any(|(k, v)| {
                k.starts_with("border") && !k.starts_with("border-radius") && !is_zero(v)
            });
        ground && edge && has("border-radius")
    }

    fn card_ancestors(&self, i: usize) -> usize {
        let mut n = 0;
        let mut cur = self.el(i).parent;
        while let Some(p) = cur {
            n += usize::from(self.is_card(p));
            cur = self.el(p).parent;
        }
        n
    }

    /// The effective `text-align` of `i` (it inherits).
    fn text_align(&self, i: usize) -> Option<&str> {
        let mut cur = Some(i);
        while let Some(c) = cur {
            if let Some(v) = self.style(c, "text-align") {
                return Some(v);
            }
            cur = self.el(c).parent;
        }
        None
    }

    /// A one-letter class of a child for the icon-heading-paragraph shape.
    fn role(&self, i: usize) -> char {
        let e = self.el(i);
        let class = e
            .attributes
            .iter()
            .find(|(k, _)| k == "class")
            .map_or("", |(_, v)| v.as_str());
        match e.tag.to_ascii_lowercase().as_str() {
            "svg" | "img" | "i" => 'i',
            "h1" | "h2" | "h3" | "h4" | "h5" | "h6" => 'h',
            "p" => 'p',
            _ if class.contains("icon") => 'i',
            _ => 'x',
        }
    }

    /// The structure of the subtree at `i` as nested tags.
    fn signature(&self, i: usize) -> String {
        let inner: Vec<String> = self.children[i]
            .iter()
            .map(|&c| self.signature(c))
            .collect();
        format!(
            "{}({})",
            self.el(i).tag.to_ascii_lowercase(),
            inner.join(",")
        )
    }

    fn label(&self, i: usize) -> String {
        self.file.element_label(self.el(i).offset)
    }

    fn same_size(&self, group: &[usize]) -> bool {
        let sizes: Vec<(f32, f32)> = group
            .iter()
            .filter_map(|&i| self.node(i).map(|n| (n.width, n.height)))
            .collect();
        sizes.len() < group.len()
            || sizes
                .windows(2)
                .all(|w| (w[0].0 - w[1].0).abs() <= SIZE_EPS && (w[0].1 - w[1].1).abs() <= SIZE_EPS)
    }

    /// The maximal runs of consecutive `section` siblings, per parent, each of at least `min`.
    fn section_runs(&self, min: usize) -> Vec<Vec<usize>> {
        let parents = std::iter::once(None).chain((0..self.children.len()).map(Some));
        let mut runs = Vec::new();
        for parent in parents {
            let mut run: Vec<usize> = Vec::new();
            for &i in self.siblings(parent) {
                if self.el(i).tag.eq_ignore_ascii_case("section") {
                    run.push(i);
                } else {
                    if run.len() >= min {
                        runs.push(std::mem::take(&mut run));
                    }
                    run.clear();
                }
            }
            if run.len() >= min {
                runs.push(run);
            }
        }
        runs
    }

    /// The layout fingerprint of a section: alignment and flow styles, child count and the number
    /// of distinct solved columns its children occupy.
    fn fingerprint(&self, i: usize) -> String {
        const KEYS: [&str; 9] = [
            "display",
            "grid-template-columns",
            "flex-direction",
            "flex-wrap",
            "text-align",
            "align-items",
            "justify-content",
            "padding",
            "gap",
        ];
        let styled: Vec<String> = KEYS
            .iter()
            .map(|k| format!("{k}={}", self.style(i, k).unwrap_or("")))
            .collect();
        let columns: BTreeSet<i64> = self.children[i]
            .iter()
            .filter_map(|&c| self.node(c))
            // WHY: sub-pixel columns bucketed to 1/64 px; far inside i64.
            .map(|n| {
                #[allow(clippy::cast_possible_truncation)]
                let col = (n.x * 64.0).round() as i64;
                col
            })
            .collect();
        format!(
            "{};children={};columns={}",
            styled.join(";"),
            self.children[i].len(),
            columns.len()
        )
    }

    /// The (top, bottom) padding of `i` when it declares any.
    fn vertical_padding(&self, i: usize) -> Option<(String, String)> {
        if let Some(p) = self.style(i, "padding") {
            let parts: Vec<&str> = p.split_whitespace().collect();
            return match parts.as_slice() {
                [a] | [a, _] => Some(((*a).to_owned(), (*a).to_owned())),
                [a, _, c] | [a, _, c, _] => Some(((*a).to_owned(), (*c).to_owned())),
                _ => None,
            };
        }
        let top = self.style(i, "padding-top");
        let bottom = self.style(i, "padding-bottom");
        (top.is_some() || bottom.is_some()).then(|| {
            (
                top.unwrap_or("0").to_owned(),
                bottom.unwrap_or("0").to_owned(),
            )
        })
    }
}

/// SLOP020: three or more sibling cards that each run icon, heading, paragraph, with one
/// structure (and, solved, one size).
pub fn identical_cards(view: &SceneView<'_>) -> Vec<Tell> {
    let parents = std::iter::once(None).chain((0..view.children.len()).map(Some));
    let mut tells = Vec::new();
    for parent in parents {
        let group: Vec<usize> = view
            .siblings(parent)
            .iter()
            .copied()
            .filter(|&c| {
                let roles: String = view.children[c].iter().map(|&k| view.role(k)).collect();
                roles.starts_with("ihp")
            })
            .collect();
        if group.len() < TRIO {
            continue;
        }
        let first = view.signature(group[0]);
        if group.iter().all(|&c| view.signature(c) == first) && view.same_size(&group) {
            tracing::debug!(count = group.len(), "SLOP020: identical icon cards");
            tells.push(Tell {
                offset: view.el(group[0]).offset,
                message: format!(
                    "{} identical icon, heading, paragraph cards starting at {}; vary the trio or make one the lead",
                    group.len(),
                    view.label(group[0])
                ),
            });
        }
    }
    tells
}

/// SLOP021: a card nested three deep in cards, or a section whose children are mostly cards.
pub fn card_nesting(view: &SceneView<'_>) -> Vec<Tell> {
    let mut tells = Vec::new();
    for i in 0..view.children.len() {
        if view.is_card(i) && view.card_ancestors(i) + 1 >= NESTING_LIMIT {
            tracing::debug!(element = i, "SLOP021: card nesting");
            tells.push(Tell {
                offset: view.el(i).offset,
                message: format!(
                    "{} is a card nested {} deep in cards; flatten the surfaces",
                    view.label(i),
                    view.card_ancestors(i) + 1
                ),
            });
        }
        let kids = &view.children[i];
        let cards = kids.iter().filter(|&&c| view.is_card(c)).count();
        if view.el(i).tag.eq_ignore_ascii_case("section")
            && kids.len() >= 4
            && cards * 10 > kids.len() * 7
        {
            tracing::debug!(element = i, cards, total = kids.len(), "SLOP021: all cards");
            tells.push(Tell {
                offset: view.el(i).offset,
                message: format!(
                    "{}: {cards} of {} children are cards; let some content sit on the page",
                    view.label(i),
                    kids.len()
                ),
            });
        }
    }
    tells
}

/// SLOP026: centred text longer than three lines (solved), or over 160 characters (unsolved).
pub fn centred_long_text(view: &SceneView<'_>) -> Vec<Tell> {
    let mut tells = Vec::new();
    for i in 0..view.children.len() {
        let e = view.el(i);
        if e.text.is_empty() || view.text_align(i) != Some("center") {
            continue;
        }
        let chars: usize = e.text.iter().map(|t| t.chars().count()).sum();
        let long = match view.solved_text(i) {
            Some(t) => t.lines > CENTRED_LINE_LIMIT,
            None => chars > CENTRED_CHAR_LIMIT,
        };
        if long {
            tracing::debug!(element = i, chars, "SLOP026: centred long text");
            tells.push(Tell {
                offset: e.offset,
                message: format!(
                    "{} centres {chars} characters of running text; left-align anything over three lines",
                    view.label(i)
                ),
            });
        }
    }
    tells
}

/// SLOP027: four or more consecutive sections with one layout fingerprint.
pub fn one_layout(view: &SceneView<'_>) -> Vec<Tell> {
    let mut tells = Vec::new();
    for run in view.section_runs(SECTION_RUN) {
        let prints: Vec<String> = run.iter().map(|&i| view.fingerprint(i)).collect();
        let mut start = 0;
        while start < run.len() {
            let len = prints[start..]
                .iter()
                .take_while(|p| **p == prints[start])
                .count();
            if len >= SECTION_RUN {
                tracing::debug!(len, "SLOP027: one layout for all sections");
                tells.push(Tell {
                    offset: view.el(run[start]).offset,
                    message: format!(
                        "{len} consecutive sections share one layout from {}; change the structure of at least one",
                        view.label(run[start])
                    ),
                });
            }
            start += len;
        }
    }
    tells
}

/// SLOP028: identical vertical padding on every section of a run, or one spacing value for
/// over 80 percent of the spacing declarations.
pub fn flat_rhythm(view: &SceneView<'_>) -> Vec<Tell> {
    let mut tells = Vec::new();
    for run in view.section_runs(SECTION_RUN) {
        let pads: Vec<Option<(String, String)>> =
            run.iter().map(|&i| view.vertical_padding(i)).collect();
        if let Some(Some(first)) = pads.first()
            && pads.iter().all(|p| p.as_ref() == Some(first))
        {
            tracing::debug!(sections = run.len(), "SLOP028: identical section padding");
            tells.push(Tell {
                offset: view.el(run[0]).offset,
                message: format!(
                    "{} sections from {} all pad {} above and {} below; vary the vertical rhythm",
                    run.len(),
                    view.label(run[0]),
                    first.0,
                    first.1
                ),
            });
        }
    }
    let mut counts: BTreeMap<&str, usize> = BTreeMap::new();
    let mut first_at: Option<usize> = None;
    for (i, style) in view.styles.iter().enumerate() {
        for (prop, value) in style {
            let spacing = ["padding", "margin", "gap", "row-gap", "column-gap"]
                .iter()
                .any(|p| prop == p || prop.starts_with(&format!("{p}-")));
            if !spacing {
                continue;
            }
            for token in value
                .split_whitespace()
                .filter(|t| !is_zero(t) && *t != "auto")
            {
                *counts.entry(token).or_default() += 1;
                first_at.get_or_insert(i);
            }
        }
    }
    let total: usize = counts.values().sum();
    if let (Some((value, top)), Some(at)) = (counts.iter().max_by_key(|(_, n)| **n), first_at)
        && total >= SPACING_MIN_DECLS
    {
        #[allow(clippy::cast_precision_loss, reason = "a handful of declarations")]
        let share = *top as f64 / total as f64;
        if share > SPACING_DOMINANCE {
            tracing::debug!(%value, share, "SLOP028: one spacing value");
            tells.push(Tell {
                offset: view.el(at).offset,
                message: format!(
                    "{top} of {total} spacing values are {value}; use more than one step so groups read apart"
                ),
            });
        }
    }
    tells
}

/// SLOP029: four or more consecutive sections whose solved heights differ by less than 1.75x.
pub fn uniform_density(view: &SceneView<'_>) -> Vec<Tell> {
    let mut tells = Vec::new();
    for run in view.section_runs(SECTION_RUN) {
        let heights: Vec<f32> = run
            .iter()
            .filter_map(|&i| view.node(i))
            .map(|n| n.height)
            .collect();
        if heights.len() < run.len() {
            continue;
        }
        let max = heights.iter().copied().fold(f32::MIN, f32::max);
        let min = heights.iter().copied().fold(f32::MAX, f32::min);
        if min > 0.0 && max / min < DENSITY_FLOOR {
            tracing::debug!(max, min, "SLOP029: uniform density");
            tells.push(Tell {
                offset: view.el(run[0]).offset,
                message: format!(
                    "{} sections from {} are {min}px to {max}px tall (under 1.75x); give one an oversized moment",
                    run.len(),
                    view.label(run[0])
                ),
            });
        }
    }
    tells
}
