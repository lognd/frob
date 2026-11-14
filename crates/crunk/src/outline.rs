//! `outline [--node ID]`: a sparse tree of tokens, components, screens and flows, then one node.
//!
//! The token-economy entry to the design system for agents (design crunk.md section 5, interop
//! row): the bare verb returns ids and one-line summaries only, and `--node ID` drills into the
//! single node it names. Search over the design system is [`crate::query`] (`find`) and the
//! code map is [`crate::map`]; this module does not repeat either. The verb is `read_only`, so
//! `crunk serve` lists it as an MCP tool.
//!
//! # Edge cases
//!
//! - A bare id that names nodes of more than one kind is a usage error listing the `kind:id`
//!   forms; `token:`, `component:`, `screen:` and `flow:` prefixes pick one.
//! - A token id may be written with or without its leading `--`.
//! - An unreadable or invalid flow file is skipped with a warning, as the check pipeline does.

// frob:ticket 01M5XCW9WCHSZBR5F29VKYBM25

use std::path::Path;

use crunk_rules::component_files::ComponentFacts;
use crunk_spec::{DesignSpec, FlowFile, parse_flow_file};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::query::load;

/// Directory under the project root holding flow files.
pub const FLOWS_DIR: &str = "design/flows";

/// File-name suffix of a flow file.
pub const FLOW_SUFFIX: &str = ".flow.toml";

/// The longest summary, in characters, before it is cut with an ellipsis.
const SUMMARY_MAX: usize = 72;

/// The node kinds, in outline order.
pub const KINDS: [&str; 4] = ["token", "component", "screen", "flow"];

/// Return a sparse outline of the design system, or with `--node ID` only that node in full.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "outline",
    product = "crunk",
    idempotent = true,
    read_only,
    exits(ok, refused, usage, internal)
)]
pub struct Outline {
    node: Option<String>,
}

/// One outline entry: what it is, its id and a one-line summary.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct OutlineEntry {
    /// `token`, `component`, `screen` or `flow`.
    pub kind: String,
    /// The id to pass to `outline --node` (a token's custom property name, else its name or id).
    pub id: String,
    /// One line describing the node.
    pub summary: String,
}

/// Output of `outline`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct OutlineData {
    /// The drilled node's id; absent for the whole outline.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node: Option<String>,
    /// The entries: every node for the whole outline, the one node when drilled.
    pub entries: Vec<OutlineEntry>,
    /// The drilled node in full; absent for the whole outline.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<Value>,
}

/// `Outline` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct OutlineArgs {
    #[arg(
        long,
        value_name = "ID",
        help = "Drill into one node by id (a token name, component name, screen id or flow name; `kind:id` when ambiguous)"
    )]
    node: Option<String>,
}

/// A node with its outline entry and its full JSON.
struct Node {
    entry: OutlineEntry,
    detail: Value,
}

/// Cut `text` to one short line.
fn one_line(text: &str) -> String {
    let flat = text.split_whitespace().collect::<Vec<_>>().join(" ");
    if flat.chars().count() <= SUMMARY_MAX {
        return flat;
    }
    let cut: String = flat.chars().take(SUMMARY_MAX - 3).collect();
    format!("{cut}...")
}

/// The authored `design/flows/*.flow.toml` files that parse, sorted by path.
fn load_flows(root: &Path) -> Vec<FlowFile> {
    let dir = root.join(FLOWS_DIR);
    let Ok(read) = std::fs::read_dir(&dir) else {
        tracing::debug!(dir = %dir.display(), "no flows directory");
        return Vec::new();
    };
    let mut paths: Vec<_> = read
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .is_some_and(|n| n.to_string_lossy().ends_with(FLOW_SUFFIX))
        })
        .collect();
    paths.sort();
    paths
        .into_iter()
        .filter_map(|path| {
            let text = std::fs::read_to_string(&path)
                .inspect_err(|err| {
                    tracing::warn!(path = %path.display(), %err, "flow file unreadable; skipped");
                })
                .ok()?;
            parse_flow_file(&text)
                .inspect_err(|err| {
                    tracing::warn!(path = %path.display(), %err, "flow file invalid; skipped");
                })
                .ok()
        })
        .collect()
}

/// Serialize a node body; a type that cannot serialize is a programmer bug.
fn detail_of<T: Serialize>(value: &T) -> Value {
    serde_json::to_value(value).expect("a design node serializes to JSON")
}

/// Every node of the project in outline order: tokens, components, screens, flows.
fn nodes(spec: &DesignSpec, tokens: &crunk_tokens::TokenSet) -> Vec<Node> {
    let mut out = Vec::new();
    for token in tokens.iter() {
        let value = tokens
            .resolve(&token.name, None)
            .and_then(|v| serde_json::to_string(v).ok())
            .unwrap_or_default();
        let summary = match &token.description {
            Some(desc) => format!("{desc} ({value})"),
            None => format!("{:?} {value}", token.kind).to_lowercase(),
        };
        out.push(Node {
            entry: entry("token", &token.name, &summary),
            detail: detail_of(token),
        });
    }
    for file in ComponentFacts::load(spec).files {
        let c = &file.component;
        let summary = format!(
            "{} prop(s), {} variant(s), {} state(s), {} binding(s)",
            c.props.len(),
            c.variants.len(),
            c.states.len(),
            c.bindings.len()
        );
        out.push(Node {
            entry: entry("component", &c.name, &summary),
            detail: detail_of(c),
        });
    }
    for screen in spec.screens.values() {
        let summary = format!("{}, {} state(s)", screen.entry, screen.states.len());
        out.push(Node {
            entry: entry("screen", &screen.id, &summary),
            detail: detail_of(screen),
        });
    }
    for flow in load_flows(&spec.root) {
        let summary = format!("{} node(s), {} edge(s)", flow.nodes.len(), flow.edges.len());
        out.push(Node {
            entry: entry("flow", &flow.name, &summary),
            detail: detail_of(&flow),
        });
    }
    out
}

/// An outline entry with a one-line summary.
fn entry(kind: &str, id: &str, summary: &str) -> OutlineEntry {
    OutlineEntry {
        kind: kind.to_owned(),
        id: id.to_owned(),
        summary: one_line(summary),
    }
}

/// Whether `node` is the one `wanted` names: bare, or `kind:id`.
fn matches_id(node: &Node, wanted: &str) -> bool {
    let (kind, id) = wanted
        .split_once(':')
        .filter(|(k, _)| KINDS.contains(k))
        .map_or((None, wanted), |(k, i)| (Some(k), i));
    if kind.is_some_and(|k| k != node.entry.kind) {
        return false;
    }
    let own = node.entry.id.as_str();
    own == id
        || (node.entry.kind == "token"
            && own.trim_start_matches("--") == id.trim_start_matches("--"))
}

/// The one node named `wanted`.
///
/// # Errors
///
/// A usage error when no node or more than one node matches.
fn pick(all: Vec<Node>, wanted: &str) -> Result<Node, CliError> {
    let mut hits: Vec<Node> = all.into_iter().filter(|n| matches_id(n, wanted)).collect();
    match hits.len() {
        0 => Err(CliError::Usage(format!(
            "outline --node: no token, component, screen or flow with id '{wanted}'"
        ))),
        1 => Ok(hits.remove(0)),
        _ => {
            let forms: Vec<String> = hits
                .iter()
                .map(|n| format!("{}:{}", n.entry.kind, n.entry.id))
                .collect();
            Err(CliError::Usage(format!(
                "outline --node: '{wanted}' is ambiguous; use one of {}",
                forms.join(", ")
            )))
        }
    }
}

impl Command for Outline {
    type Data = OutlineData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<OutlineArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<OutlineArgs>(m)?;
        Ok(Self { node: a.node })
    }

    fn run(&self, ctx: &Context) -> Outcome<OutlineData> {
        let loaded = load("outline", ctx)?;
        let all = nodes(&loaded.spec, &loaded.tokens);
        let data = match &self.node {
            None => {
                tracing::info!(nodes = all.len(), "outline built");
                OutlineData {
                    node: None,
                    entries: all.into_iter().map(|n| n.entry).collect(),
                    detail: None,
                }
            }
            Some(wanted) => {
                let node = pick(all, wanted)?;
                tracing::info!(kind = %node.entry.kind, id = %node.entry.id, "outline node drilled");
                OutlineData {
                    node: Some(node.entry.id.clone()),
                    entries: vec![node.entry],
                    detail: Some(node.detail),
                }
            }
        };
        let lines: Vec<String> = data
            .entries
            .iter()
            .map(|e| format!("{:<9} {}  {}", e.kind, e.id, e.summary))
            .collect();
        Ok(Payload::new(data).with_rendered(lines))
    }
}
