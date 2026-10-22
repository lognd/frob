//! The focus graph of one scene: which elements a gamepad can focus, where each direction leads,
//! which one is selected first, and what is unreachable or inescapable.
//!
//! Authoring vocabulary (all plain attributes on scene elements):
//!
//! - an element is focusable when it is a native control (`button`, `a[href]`, `input`, `select`,
//!   `textarea`), a known interactive component (`Button`, `Toggle`, ...), has `tabindex >= 0` or
//!   carries `data-focusable`; `disabled`, `aria-disabled="true"`, `data-focusable="false"` or a
//!   negative `tabindex` takes it out of the graph;
//! - `data-focus-default` marks the element selected when the scene opens;
//! - `data-focus-group` (with optional `data-focus-axis="vertical|horizontal"` and
//!   `data-focus-wrap="wrap|clamp"`) makes an element a focus group; focusables nest into their
//!   nearest group, the scene itself being a vertical clamped group. Inside a group, document order
//!   gives the implicit neighbours along the axis and wrap joins the last to the first;
//! - `data-nav-up|down|left|right="<data-id>"` overrides one direction; `none` blocks it.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

use std::collections::{BTreeSet, HashMap, VecDeque};

use crunk_scene::{ElementKind, SceneDoc, SceneElement};

/// Component tags that are interactive without further markup.
const INTERACTIVE_COMPONENTS: &[&str] = &[
    "Button",
    "IconButton",
    "Link",
    "Toggle",
    "Checkbox",
    "Radio",
    "Slider",
    "Tab",
    "Input",
    "Select",
    "MenuItem",
];

/// A pad direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Direction {
    /// Towards the previous item of a vertical group.
    Up,
    /// Towards the next item of a vertical group.
    Down,
    /// Towards the previous item of a horizontal group.
    Left,
    /// Towards the next item of a horizontal group.
    Right,
}

impl Direction {
    /// All four directions.
    pub const ALL: [Direction; 4] = [
        Direction::Up,
        Direction::Down,
        Direction::Left,
        Direction::Right,
    ];

    /// The attribute name that overrides this direction.
    pub const fn attribute(self) -> &'static str {
        match self {
            Direction::Up => "data-nav-up",
            Direction::Down => "data-nav-down",
            Direction::Left => "data-nav-left",
            Direction::Right => "data-nav-right",
        }
    }
}

/// The axis a focus group lays its items along.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GroupAxis {
    /// Up and down move between items (the default).
    Vertical,
    /// Left and right move between items.
    Horizontal,
}

/// What happens at the end of a group.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WrapMode {
    /// The edge stops the move (the default).
    Clamp,
    /// The move continues at the other end.
    Wrap,
}

/// One focusable element.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FocusNode {
    /// Index into [`SceneDoc::elements`].
    pub element: usize,
    /// A name for findings: `data-id 'x'`, else `<tag>`.
    pub label: String,
    /// The `data-id`, when the element has one.
    pub data_id: Option<String>,
    /// Byte offset of the start tag.
    pub offset: usize,
    /// 1-based line of the start tag.
    pub line: u32,
}

/// A directed move between two nodes (indices into [`FocusGraph::nodes`]).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct FocusEdge {
    /// Where the move starts.
    pub from: usize,
    /// Where it lands.
    pub to: usize,
    /// The pad direction.
    pub direction: Direction,
}

/// Why an authored focus attribute is unusable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InvalidReason {
    /// A `data-nav-*` names a `data-id` that no element has.
    UnknownTarget(String),
    /// A `data-nav-*` names an element that is not focusable (or is disabled).
    UnfocusableTarget(String),
    /// A `data-focus-wrap` value other than `wrap` or `clamp`.
    BadWrap(String),
    /// A `data-focus-axis` value other than `vertical` or `horizontal`.
    BadAxis(String),
}

/// An authored focus attribute that cannot be honoured.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvalidEdge {
    /// Index into [`SceneDoc::elements`] of the element carrying the attribute.
    pub element: usize,
    /// A name for findings.
    pub label: String,
    /// The attribute name.
    pub attribute: String,
    /// What is wrong.
    pub reason: InvalidReason,
    /// Byte offset of the element.
    pub offset: usize,
    /// 1-based line of the element.
    pub line: u32,
}

/// The focus graph of a scene.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct FocusGraph {
    /// Enabled focusable elements in document order.
    pub nodes: Vec<FocusNode>,
    /// Every move, sorted.
    pub edges: Vec<FocusEdge>,
    /// Nodes marked `data-focus-default`, in document order.
    pub defaults: Vec<usize>,
    /// Elements marked `data-focus-default` that are not focusable or are disabled.
    pub dead_defaults: Vec<usize>,
    /// Authored attributes that cannot be honoured.
    pub invalid: Vec<InvalidEdge>,
}

/// An in-progress focus group.
struct Group {
    axis: GroupAxis,
    wrap: WrapMode,
    members: Vec<usize>,
}

impl FocusGraph {
    /// Derive the focus graph of `doc`.
    pub fn from_scene(doc: &SceneDoc) -> Self {
        let mut graph = Self::default();
        let mut node_of: HashMap<usize, usize> = HashMap::new();
        for (i, el) in doc.elements.iter().enumerate() {
            if is_focusable(el) {
                node_of.insert(i, graph.nodes.len());
                graph.nodes.push(FocusNode {
                    element: i,
                    label: label_of(el),
                    data_id: el.data_id.clone(),
                    offset: el.offset,
                    line: el.line,
                });
            }
        }
        graph.collect_defaults(doc, &node_of);
        let by_id: HashMap<&str, usize> = doc
            .elements
            .iter()
            .enumerate()
            .filter_map(|(i, e)| e.data_id.as_deref().map(|id| (id, i)))
            .collect();
        let mut edges: BTreeSet<FocusEdge> = BTreeSet::new();
        let mut explicit: BTreeSet<(usize, Direction)> = BTreeSet::new();
        for (&element, &node) in &node_of {
            let el = &doc.elements[element];
            for dir in Direction::ALL {
                let Some(value) = attr(el, dir.attribute()) else {
                    continue;
                };
                explicit.insert((node, dir));
                let target = value.trim();
                if target.is_empty() || target.eq_ignore_ascii_case("none") {
                    continue;
                }
                if let Some(&to) = by_id.get(target).and_then(|t| node_of.get(t)) {
                    edges.insert(FocusEdge {
                        from: node,
                        to,
                        direction: dir,
                    });
                } else {
                    let reason = if by_id.contains_key(target) {
                        InvalidReason::UnfocusableTarget(target.to_owned())
                    } else {
                        InvalidReason::UnknownTarget(target.to_owned())
                    };
                    graph
                        .invalid
                        .push(invalid(el, element, dir.attribute(), reason));
                }
            }
        }
        for (key, members) in group_members(doc, &node_of) {
            let group = graph.read_group(doc, key, members);
            implicit_edges(&group, &explicit, &mut edges);
        }
        graph.edges = edges.into_iter().collect();
        graph
            .invalid
            .sort_by_key(|v| (v.offset, v.attribute.clone()));
        tracing::debug!(
            nodes = graph.nodes.len(),
            edges = graph.edges.len(),
            defaults = graph.defaults.len(),
            invalid = graph.invalid.len(),
            "focus graph built"
        );
        graph
    }

    /// Record `data-focus-default` elements as defaults or dead defaults.
    fn collect_defaults(&mut self, doc: &SceneDoc, node_of: &HashMap<usize, usize>) {
        for (i, el) in doc.elements.iter().enumerate() {
            if !is_on(attr(el, "data-focus-default")) {
                continue;
            }
            match node_of.get(&i) {
                Some(&n) => self.defaults.push(n),
                None => self.dead_defaults.push(i),
            }
        }
    }

    /// Read a group's axis and wrap attributes (recording bad values) into a [`Group`].
    fn read_group(&mut self, doc: &SceneDoc, key: Option<usize>, members: Vec<usize>) -> Group {
        let mut group = Group {
            axis: GroupAxis::Vertical,
            wrap: WrapMode::Clamp,
            members,
        };
        let Some(i) = key else {
            return group;
        };
        let el = &doc.elements[i];
        match attr(el, "data-focus-axis").map(str::trim) {
            None | Some("vertical") => {}
            Some("horizontal") => group.axis = GroupAxis::Horizontal,
            Some(other) => self.invalid.push(invalid(
                el,
                i,
                "data-focus-axis",
                InvalidReason::BadAxis(other.to_owned()),
            )),
        }
        match attr(el, "data-focus-wrap").map(str::trim) {
            None | Some("clamp") => {}
            Some("wrap") => group.wrap = WrapMode::Wrap,
            Some(other) => self.invalid.push(invalid(
                el,
                i,
                "data-focus-wrap",
                InvalidReason::BadWrap(other.to_owned()),
            )),
        }
        group
    }

    /// The nodes selection starts from: the defaults, else the first node (the engine's fallback).
    pub fn entries(&self) -> Vec<usize> {
        if !self.defaults.is_empty() {
            self.defaults.clone()
        } else if self.nodes.is_empty() {
            Vec::new()
        } else {
            vec![0]
        }
    }

    /// Nodes no sequence of moves reaches from the entries, in document order.
    pub fn unreachable(&self) -> Vec<usize> {
        let seen = self.flood(&self.entries(), false);
        (0..self.nodes.len()).filter(|&n| !seen[n]).collect()
    }

    /// Reachable nodes from which no sequence of moves returns to any entry: focus gets stuck.
    pub fn traps(&self) -> Vec<usize> {
        let entries = self.entries();
        let forward = self.flood(&entries, false);
        let back = self.flood(&entries, true);
        (0..self.nodes.len())
            .filter(|&n| forward[n] && !back[n])
            .collect()
    }

    /// Breadth-first reach from `starts`, along edges or (`reverse`) against them.
    fn flood(&self, starts: &[usize], reverse: bool) -> Vec<bool> {
        let mut seen = vec![false; self.nodes.len()];
        let mut queue: VecDeque<usize> = VecDeque::new();
        for &s in starts {
            if !seen[s] {
                seen[s] = true;
                queue.push_back(s);
            }
        }
        while let Some(n) = queue.pop_front() {
            for e in &self.edges {
                let (from, to) = if reverse {
                    (e.to, e.from)
                } else {
                    (e.from, e.to)
                };
                if from == n && !seen[to] {
                    seen[to] = true;
                    queue.push_back(to);
                }
            }
        }
        seen
    }
}

/// Add the document-order moves of `group` along its axis, except where a direction is authored.
fn implicit_edges(
    group: &Group,
    explicit: &BTreeSet<(usize, Direction)>,
    edges: &mut BTreeSet<FocusEdge>,
) {
    let (prev, next) = match group.axis {
        GroupAxis::Vertical => (Direction::Up, Direction::Down),
        GroupAxis::Horizontal => (Direction::Left, Direction::Right),
    };
    let n = group.members.len();
    if n < 2 {
        return;
    }
    for (i, &from) in group.members.iter().enumerate() {
        let after = (i + 1 < n)
            .then(|| group.members[i + 1])
            .or_else(|| (group.wrap == WrapMode::Wrap).then(|| group.members[0]));
        let before = (i > 0)
            .then(|| group.members[i - 1])
            .or_else(|| (group.wrap == WrapMode::Wrap).then(|| group.members[n - 1]));
        for (dir, to) in [(next, after), (prev, before)] {
            if let Some(to) = to
                && !explicit.contains(&(from, dir))
            {
                edges.insert(FocusEdge {
                    from,
                    to,
                    direction: dir,
                });
            }
        }
    }
}

/// Group the focusable nodes by their nearest `data-focus-group` ancestor (`None` is the scene),
/// keeping document order. Groups come out in the order of their first member.
fn group_members(
    doc: &SceneDoc,
    node_of: &HashMap<usize, usize>,
) -> Vec<(Option<usize>, Vec<usize>)> {
    let mut groups: Vec<(Option<usize>, Vec<usize>)> = Vec::new();
    let mut elements: Vec<_> = node_of.iter().collect();
    elements.sort();
    for (&element, &node) in elements {
        let key = nearest_group(doc, element);
        match groups.iter_mut().find(|(k, _)| *k == key) {
            Some((_, members)) => members.push(node),
            None => groups.push((key, vec![node])),
        }
    }
    groups
}

/// The nearest proper ancestor of `element` marked as a focus group.
fn nearest_group(doc: &SceneDoc, element: usize) -> Option<usize> {
    let mut cur = doc.elements[element].parent;
    while let Some(p) = cur {
        if attr(&doc.elements[p], "data-focus-group").is_some() {
            return Some(p);
        }
        cur = doc.elements[p].parent;
    }
    None
}

/// Whether an element is in the focus graph.
fn is_focusable(el: &SceneElement) -> bool {
    if attr(el, "disabled").is_some_and(|v| v != "false")
        || attr(el, "aria-disabled") == Some("true")
        || attr(el, "data-focusable") == Some("false")
    {
        return false;
    }
    let tabindex = attr(el, "tabindex").and_then(|v| v.trim().parse::<i32>().ok());
    if tabindex.is_some_and(|t| t < 0) {
        return false;
    }
    if tabindex.is_some() || attr(el, "data-focusable").is_some() {
        return true;
    }
    match el.kind {
        ElementKind::Component => INTERACTIVE_COMPONENTS.contains(&el.tag.as_str()),
        ElementKind::Html => match el.tag.to_ascii_lowercase().as_str() {
            "button" | "input" | "select" | "textarea" => true,
            "a" => attr(el, "href").is_some(),
            _ => false,
        },
        ElementKind::Unknown => false,
    }
}

/// An attribute's value, when present.
fn attr<'a>(el: &'a SceneElement, name: &str) -> Option<&'a str> {
    el.attributes
        .iter()
        .find(|(n, _)| n == name)
        .map(|(_, v)| v.as_str())
}

/// Whether a boolean-ish attribute is set (present and not `false`).
fn is_on(value: Option<&str>) -> bool {
    value.is_some_and(|v| v != "false")
}

/// A name for findings.
fn label_of(el: &SceneElement) -> String {
    match &el.data_id {
        Some(id) => format!("data-id '{id}'"),
        None => format!("<{}>", el.tag),
    }
}

/// Build an [`InvalidEdge`] for `el`.
fn invalid(
    el: &SceneElement,
    element: usize,
    attribute: &str,
    reason: InvalidReason,
) -> InvalidEdge {
    InvalidEdge {
        element,
        label: label_of(el),
        attribute: attribute.to_owned(),
        reason,
        offset: el.offset,
        line: el.line,
    }
}
