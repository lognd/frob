//! `grimble serve --mcp`: grimble's design queries as read-only MCP tools on [`gob_serve`].
//!
//! Three tools are offered, `check` (the `gob.sibling/1` document of a model check), `graph`
//! (the model entities as nodes and the binding relation as edges) and `explore` (one node with
//! its neighbours). All only read the
//! repository. Every request must present the per-launch token (D29); [`launch`] generates it
//! and hands it to the client once, on the announce stream (stderr for the binary), never to
//! the log. The transport lives in `gob-serve`; `grimble-check` stays free of it.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ
// frob:ticket 01M5M682VX5JMQ8076X42VGPKQ

use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};

use gob_serve::{ServeError, Server, Token, ToolSpec, Tools};
use grimble_check::sibling::entities_json;
use grimble_check::{CheckOptions, GrimbleRun, sibling_document};
use serde_json::{Map, Value, json};

/// The read-only tools of one repository.
#[derive(Debug, Clone)]
pub struct GrimbleTools {
    root: PathBuf,
}

impl GrimbleTools {
    /// Tools that read the repository at `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }

    /// Run the model check once; a config or walk failure is the tool's error text.
    fn run(&self) -> Result<GrimbleRun, String> {
        // Served tools are read-only: no telemetry or precision history in the repository.
        let options = CheckOptions {
            skip_telemetry: true,
            ..CheckOptions::default()
        };
        grimble_check::run(&self.root, &options).map_err(|e| e.to_string())
    }
}

/// The empty-arguments schema both tools share.
fn no_arguments() -> Value {
    json!({ "type": "object", "properties": {}, "additionalProperties": false })
}

/// The `explore` payload: the entity anchored at `id`, its binding rows and its neighbours.
///
/// Neighbours are the entities joined to `id` by a planning edge in either direction.
fn explore(run: &GrimbleRun, id: &str) -> Result<Value, String> {
    let entities = entities_json(run);
    let find = |anchor: &str| entities.iter().find(|e| e["anchor"] == anchor).cloned();
    let Some(node) = find(id) else {
        tracing::warn!(id, "explore: unknown node");
        return Err(format!("unknown node `{id}`"));
    };
    let edges: Vec<&Value> = run
        .plan
        .edges
        .iter()
        .filter(|e| e["from"] == id || e["to"] == id)
        .collect();
    let mut neighbours: Vec<Value> = Vec::new();
    for edge in &edges {
        let other = if edge["from"] == id {
            &edge["to"]
        } else {
            &edge["from"]
        };
        if let Some(n) = other.as_str().and_then(find)
            && !neighbours.contains(&n)
        {
            neighbours.push(n);
        }
    }
    let bindings: Vec<&Value> = run.bindings.iter().filter(|b| b["entity"] == id).collect();
    tracing::debug!(id, neighbours = neighbours.len(), "explore");
    Ok(json!({
        "node": node,
        "neighbours": neighbours,
        "edges": edges,
        "bindings": bindings,
    }))
}

impl Tools for GrimbleTools {
    fn list(&self) -> Vec<ToolSpec> {
        vec![
            ToolSpec {
                name: "check".to_owned(),
                description: "Check the design model and return the gob.sibling/1 document."
                    .to_owned(),
                input_schema: no_arguments(),
            },
            ToolSpec {
                name: "graph".to_owned(),
                description: "The design graph: model entities as nodes, bindings as edges."
                    .to_owned(),
                input_schema: no_arguments(),
            },
            ToolSpec {
                name: "explore".to_owned(),
                description: "One design node by id, with its neighbours, edges and bindings."
                    .to_owned(),
                input_schema: json!({
                    "type": "object",
                    "properties": { "id": { "type": "string", "description": "node anchor" } },
                    "required": ["id"],
                    "additionalProperties": false,
                }),
            },
        ]
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> Result<Value, String> {
        let allowed = if name == "explore" { "id" } else { "" };
        if let Some(key) = arguments.keys().find(|k| k.as_str() != allowed) {
            return Err(format!("unknown argument `{key}` for `{name}`"));
        }
        let run = self.run()?;
        match name {
            "check" => Ok(sibling_document(&run)),
            "graph" => Ok(json!({
                "nodes": run.view.entities_json(),
                "edges": run.bindings,
            })),
            "explore" => {
                let id = arguments
                    .get("id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| "`explore` needs a string `id`".to_owned())?;
                explore(&run, id)
            }
            other => Err(format!("unknown tool `{other}`")),
        }
    }
}

/// A server for the repository at `root` guarded by `token`.
pub fn server(root: &Path, token: Token) -> Server<GrimbleTools> {
    Server::new(
        "grimble",
        env!("CARGO_PKG_VERSION"),
        token,
        GrimbleTools::new(root),
    )
}

/// Start a launch: mint the token, tell the client once on `announce`, then serve until EOF.
///
/// # Errors
///
/// [`ServeError`] when the token cannot be minted or the transport fails.
pub fn launch<R: BufRead, W: Write, A: Write>(
    root: &Path,
    input: R,
    out: &mut W,
    announce: &mut A,
) -> Result<(), ServeError> {
    let token = Token::generate()?;
    writeln!(announce, "grimble serve: token {}", token.expose())?;
    announce.flush()?;
    tracing::info!(root = ?root, "grimble mcp launch");
    server(root, token).serve(input, out)
}
