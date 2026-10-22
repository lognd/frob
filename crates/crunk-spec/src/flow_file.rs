//! A standalone flow file (`design/flows/<name>.flow.toml`): a directed graph of `screen:state`
//! nodes joined by trigger edges, validated without any project context.
//!
//! Cycles are legal (back navigation, retry loops, a menu that returns to itself), so no cycle
//! check runs; reachability and dead ends are project-level findings, not file-schema errors.

// frob:ticket 01M5JHRGCES4BCHCNBCB7WWZ9F

use std::collections::HashSet;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// One flow file: its name, its nodes and the edges between them.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct FlowFile {
    /// Flow name, the file stem.
    pub name: String,
    /// Nodes as `screen:state`, unique within the flow.
    pub nodes: Vec<String>,
    /// Transitions between declared nodes.
    pub edges: Vec<FlowEdge>,
}

/// One transition: `from` reaches `to` when `trigger` fires.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct FlowEdge {
    /// Source node, declared in `nodes`.
    pub from: String,
    /// Target node, declared in `nodes`.
    pub to: String,
    /// What fires the edge: click, a key, `gamepad:south`, timeout.
    pub trigger: String,
    /// What the transition does, if anything beyond moving.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub action: Option<String>,
    /// Motion token the transition plays.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub motion: Option<String>,
}

/// Why a flow file was rejected; every variant has a stable code and names its location.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum FlowFileError {
    /// The file has no content at all.
    #[error("flow file is empty; it needs `name`, `nodes` and `edges`")]
    Empty,
    /// Not valid TOML, a missing or unknown key, or a wrongly typed value (the text carries the
    /// line and column).
    #[error("invalid flow file: {0}")]
    Parse(String),
    /// `name` is blank.
    #[error("`name` is blank")]
    BlankName,
    /// A node is not `screen:state`.
    #[error("`nodes[{index}]` is `{node}`, expected `screen:state`")]
    BadNode {
        /// Position in `nodes`.
        index: usize,
        /// The offending text.
        node: String,
    },
    /// A node id repeats an earlier one.
    #[error("`nodes[{index}]` repeats node `{node}`")]
    DuplicateNode {
        /// Position of the repeat.
        index: usize,
        /// The repeated node.
        node: String,
    },
    /// An edge endpoint names no declared node.
    #[error("`edges[{index}].{field}` references undeclared node `{node}`")]
    DanglingEdge {
        /// Position in `edges`.
        index: usize,
        /// `from` or `to`.
        field: &'static str,
        /// The missing node.
        node: String,
    },
    /// An edge has a blank trigger.
    #[error("`edges[{index}].trigger` is blank")]
    BlankTrigger {
        /// Position in `edges`.
        index: usize,
    },
}

impl FlowFileError {
    /// The stable error code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Empty => "E-FLOW-EMPTY",
            Self::Parse(_) => "E-FLOW-PARSE",
            Self::BlankName => "E-FLOW-NAME",
            Self::BadNode { .. } => "E-FLOW-NODE",
            Self::DuplicateNode { .. } => "E-FLOW-DUP-NODE",
            Self::DanglingEdge { .. } => "E-FLOW-DANGLING",
            Self::BlankTrigger { .. } => "E-FLOW-TRIGGER",
        }
    }

    /// Where the problem is, as a key path (`edges[2].to`); a parse error carries its own
    /// line and column in the message, so its location is the whole file.
    #[must_use]
    pub fn location(&self) -> String {
        match self {
            Self::Empty | Self::Parse(_) => "file".to_owned(),
            Self::BlankName => "name".to_owned(),
            Self::BadNode { index, .. } | Self::DuplicateNode { index, .. } => {
                format!("nodes[{index}]")
            }
            Self::DanglingEdge { index, field, .. } => format!("edges[{index}].{field}"),
            Self::BlankTrigger { index } => format!("edges[{index}].trigger"),
        }
    }
}

/// True when `node` is `screen:state` with both halves non-blank and no further colon.
fn is_node_id(node: &str) -> bool {
    node.split_once(':').is_some_and(|(screen, state)| {
        !screen.trim().is_empty() && !state.trim().is_empty() && !state.contains(':')
    })
}

/// Parse and validate one flow file's text, checking every rule that needs no project context.
///
/// # Errors
/// [`FlowFileError`] on empty text, bad TOML, a missing or unknown key, a blank name or trigger,
/// a malformed or duplicate node, or an edge naming an undeclared node.
pub fn parse_flow_file(text: &str) -> Result<FlowFile, FlowFileError> {
    if text.trim().is_empty() {
        return Err(FlowFileError::Empty);
    }
    let flow: FlowFile =
        toml_edit::de::from_str(text).map_err(|e| FlowFileError::Parse(e.to_string()))?;
    if flow.name.trim().is_empty() {
        return Err(FlowFileError::BlankName);
    }
    let mut seen: HashSet<&str> = HashSet::new();
    for (index, node) in flow.nodes.iter().enumerate() {
        if !is_node_id(node) {
            return Err(FlowFileError::BadNode {
                index,
                node: node.clone(),
            });
        }
        if !seen.insert(node.as_str()) {
            return Err(FlowFileError::DuplicateNode {
                index,
                node: node.clone(),
            });
        }
    }
    for (index, edge) in flow.edges.iter().enumerate() {
        for (field, node) in [("from", &edge.from), ("to", &edge.to)] {
            if !seen.contains(node.as_str()) {
                return Err(FlowFileError::DanglingEdge {
                    index,
                    field,
                    node: node.clone(),
                });
            }
        }
        if edge.trigger.trim().is_empty() {
            return Err(FlowFileError::BlankTrigger { index });
        }
    }
    tracing::debug!(flow = %flow.name, nodes = flow.nodes.len(), edges = flow.edges.len(), "parsed flow file");
    Ok(flow)
}

#[cfg(test)]
mod tests {
    use super::*;

    const GOOD: &str = r#"
name = "signup"
nodes = ["home:default", "form:default", "form:error"]

[[edges]]
from = "home:default"
to = "form:default"
trigger = "click"
motion = "motion.slide"

[[edges]]
from = "form:default"
to = "form:error"
trigger = "timeout"

[[edges]]
from = "form:error"
to = "form:default"
trigger = "gamepad:south"
action = "retry"
"#;

    fn err(text: &str) -> FlowFileError {
        parse_flow_file(text).expect_err("rejected")
    }

    // frob:tests crates/crunk-spec/src/flow_file.rs::parse_flow_file
    #[test]
    fn valid_flow_passes_including_cycles_and_the_skeleton() {
        let f = parse_flow_file(GOOD).expect("parses");
        assert_eq!(f.nodes.len(), 3);
        assert_eq!(f.edges[2].action.as_deref(), Some("retry"));
        parse_flow_file("name = \"a\"\nnodes = []\nedges = []\n").expect("skeleton");
    }

    // frob:tests crates/crunk-spec/src/flow_file.rs::parse_flow_file
    // frob:tests crates/crunk-spec/src/flow_file.rs::FlowFileError.code
    // frob:tests crates/crunk-spec/src/flow_file.rs::FlowFileError.location
    #[test]
    fn bad_flows_get_a_code_and_a_location() {
        let head = "name = \"a\"\nnodes = [\"s:x\"]\n";
        let cases: [(String, &str, String); 9] = [
            (String::new(), "E-FLOW-EMPTY", "file".into()),
            ("  \n".into(), "E-FLOW-EMPTY", "file".into()),
            (
                "name = \"a\"\nnodes = []\n".into(),
                "E-FLOW-PARSE",
                "file".into(),
            ),
            (
                "name = \"a\"\nnodes = []\nedges = []\nextra = 1\n".into(),
                "E-FLOW-PARSE",
                "file".into(),
            ),
            (
                "name = \" \"\nnodes = []\nedges = []\n".into(),
                "E-FLOW-NAME",
                "name".into(),
            ),
            (
                "name = \"a\"\nnodes = [\"s:x\", \"s\"]\nedges = []\n".into(),
                "E-FLOW-NODE",
                "nodes[1]".into(),
            ),
            (
                "name = \"a\"\nnodes = [\"s:x\", \"s:x\"]\nedges = []\n".into(),
                "E-FLOW-DUP-NODE",
                "nodes[1]".into(),
            ),
            (
                format!("{head}[[edges]]\nfrom = \"s:x\"\nto = \"s:y\"\ntrigger = \"click\"\n"),
                "E-FLOW-DANGLING",
                "edges[0].to".into(),
            ),
            (
                format!("{head}[[edges]]\nfrom = \"s:x\"\nto = \"s:x\"\ntrigger = \"\"\n"),
                "E-FLOW-TRIGGER",
                "edges[0].trigger".into(),
            ),
        ];
        for (text, code, loc) in cases {
            let e = err(&text);
            assert_eq!((e.code(), e.location()), (code, loc), "{text:?}: {e}");
        }
        let dangling_from =
            format!("{head}[[edges]]\nfrom = \"q:x\"\nto = \"s:x\"\ntrigger = \"k\"\n");
        assert_eq!(err(&dangling_from).location(), "edges[0].from");
        assert!(
            err("name = \"a\"\nnodes = []\nedges = []\nextra = 1\n")
                .to_string()
                .contains("extra")
        );
    }
}
