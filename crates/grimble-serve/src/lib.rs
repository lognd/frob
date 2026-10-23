//! `grimble serve --mcp`: grimble's design queries as read-only MCP tools on [`gob_serve`].
//!
//! Two tools are offered, `check` (the `gob.sibling/1` document of a model check) and `graph`
//! (the model entities as nodes and the binding relation as edges). Both only read the
//! repository. Every request must present the per-launch token (D29); [`launch`] generates it
//! and hands it to the client once, on the announce stream (stderr for the binary), never to
//! the log. The transport lives in `gob-serve`; `grimble-check` stays free of it.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};

use gob_serve::{ServeError, Server, Token, ToolSpec, Tools};
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
        grimble_check::run(&self.root, &CheckOptions::default()).map_err(|e| e.to_string())
    }
}

/// The empty-arguments schema both tools share.
fn no_arguments() -> Value {
    json!({ "type": "object", "properties": {}, "additionalProperties": false })
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
        ]
    }

    fn call(&self, name: &str, arguments: &Map<String, Value>) -> Result<Value, String> {
        if let Some(key) = arguments.keys().next() {
            return Err(format!("unknown argument `{key}` for `{name}`"));
        }
        let run = self.run()?;
        match name {
            "check" => Ok(sibling_document(&run)),
            "graph" => Ok(json!({
                "nodes": run.view.entities_json(),
                "edges": run.bindings,
            })),
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
