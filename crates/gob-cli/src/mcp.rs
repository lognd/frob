//! `serve`: a read-only MCP (Model Context Protocol) surface generated from verb metadata.
//!
//! Every registered verb whose metadata says `read_only` becomes one tool; nothing is
//! hand-listed, so a new read-only verb appears here the moment it declares itself. A tool
//! call runs the verb in-process with `--json` and returns the very envelope the CLI prints,
//! so there is no second API to keep in sync. The transport is newline-delimited JSON-RPC 2.0
//! on stdin/stdout; logs go to stderr only.

use std::io::{BufRead, Write};
use std::path::Path;

use clap::ArgMatches;
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::{Value, json};

use crate::cli::Cli;
use crate::command::Registered;
use crate::{CliError, Command, Context, Outcome};

/// MCP protocol revision advertised when the client does not name one.
const PROTOCOL_VERSION: &str = "2025-06-18";

/// JSON-RPC error codes used by the server.
mod code {
    pub(super) const PARSE: i64 = -32700;
    pub(super) const INVALID_REQUEST: i64 = -32600;
    pub(super) const METHOD_NOT_FOUND: i64 = -32601;
    pub(super) const INVALID_PARAMS: i64 = -32602;
}

/// Serve the read-only verbs as MCP tools over stdin and stdout until the client closes the stream.
#[derive(Debug, Clone, Copy, Default, crate::Command)]
#[command(
    verb = "serve",
    product = "any",
    idempotent = true,
    exits(ok, internal)
)]
pub struct ServeCmd;

/// Output of `serve` (never produced: the root takes over stdio and returns no envelope).
#[derive(Debug, Serialize, JsonSchema)]
pub struct ServeData {}

impl Command for ServeCmd {
    type Data = ServeData;

    fn from_matches(_matches: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, _ctx: &Context) -> Outcome<ServeData> {
        Err(CliError::internal(
            "serve is dispatched by the Cli root, not run as a verb",
        ))
    }
}

/// The tool name of a verb path: words joined by underscores (`ticket show` -> `ticket_show`).
pub fn tool_name(verb: &str) -> String {
    verb.replace(' ', "_")
}

/// The MCP tool descriptor of one read-only verb.
///
/// The input schema takes the verb's own arguments as `args`; the verb's data schema (the
/// same value `<verb> --schema` prints) rides along under `x-verb-schema`.
fn tool(v: &Registered) -> Value {
    json!({
        "name": tool_name(v.meta.verb),
        "description": v.meta.summary,
        "inputSchema": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": format!("Arguments of `{}`, exactly as on the command line", v.meta.verb),
                },
            },
            "additionalProperties": false,
            "x-verb-schema": (v.schema)(),
        },
        "annotations": { "readOnlyHint": true, "idempotentHint": true },
    })
}

impl Cli {
    /// The read-only verbs, by tool name; `serve` itself and every mutating verb are absent.
    fn read_only_verbs(&self) -> impl Iterator<Item = &Registered> {
        self.verbs
            .iter()
            .filter(|v| v.meta.read_only && v.meta.deprecated.is_none())
    }

    /// The tool list `tools/list` returns.
    pub fn mcp_tools(&self) -> Vec<Value> {
        self.read_only_verbs().map(tool).collect()
    }

    /// Run one tool call; the text is the CLI's own JSON envelope.
    ///
    /// Returns `Err(message)` for an unknown tool or malformed arguments.
    fn mcp_call(&self, name: &str, args: &Value, cwd: &Path) -> Result<(String, bool), String> {
        let Some(v) = self
            .read_only_verbs()
            .find(|v| tool_name(v.meta.verb) == name)
        else {
            tracing::debug!(tool = name, "mcp call refused: not a read-only tool");
            return Err(format!("unknown tool `{name}`"));
        };
        let mut words: Vec<String> = v.meta.verb.split(' ').map(str::to_owned).collect();
        match args.get("args") {
            None | Some(Value::Null) => {}
            Some(Value::Array(items)) => {
                for item in items {
                    let Some(s) = item.as_str() else {
                        return Err("`args` must be an array of strings".to_owned());
                    };
                    words.push(s.to_owned());
                }
            }
            Some(_) => return Err("`args` must be an array of strings".to_owned()),
        }
        words.push("--json".to_owned());
        tracing::info!(tool = name, "mcp tool call");
        let exec = self.execute(words, Some(cwd), false);
        // Exit 1 is a negative answer (a failed gate), still a result; 2 and above are errors.
        Ok((exec.stdout, exec.exit > 1))
    }

    /// Handle one JSON-RPC message; `None` for a notification, which gets no reply.
    fn mcp_handle(&self, msg: &Value, cwd: &Path) -> Option<Value> {
        let id = msg.get("id").cloned();
        let method = msg.get("method").and_then(Value::as_str);
        let (Some(method), Some(id)) = (method, id) else {
            if method.is_none() && msg.get("id").is_some() {
                return Some(rpc_error(&Value::Null, code::INVALID_REQUEST, "no method"));
            }
            return None;
        };
        let params = msg.get("params").cloned().unwrap_or(Value::Null);
        tracing::debug!(method, "mcp request");
        let result = match method {
            "initialize" => json!({
                "protocolVersion": params
                    .get("protocolVersion")
                    .and_then(Value::as_str)
                    .unwrap_or(PROTOCOL_VERSION),
                "capabilities": { "tools": { "listChanged": false } },
                "serverInfo": { "name": self.product, "version": self.version },
            }),
            "ping" => json!({}),
            "tools/list" => json!({ "tools": self.mcp_tools() }),
            "tools/call" => {
                let name = params.get("name").and_then(Value::as_str).unwrap_or("");
                let args = params.get("arguments").cloned().unwrap_or(Value::Null);
                match self.mcp_call(name, &args, cwd) {
                    Ok((text, is_error)) => json!({
                        "content": [{ "type": "text", "text": text.trim_end() }],
                        "isError": is_error,
                    }),
                    Err(m) => return Some(rpc_error(&id, code::INVALID_PARAMS, &m)),
                }
            }
            other => {
                return Some(rpc_error(
                    &id,
                    code::METHOD_NOT_FOUND,
                    &format!("method `{other}` not found"),
                ));
            }
        };
        Some(json!({ "jsonrpc": "2.0", "id": id, "result": result }))
    }

    /// Serve MCP over `input` and `output` until `input` ends; each line is one JSON-RPC message.
    ///
    /// # Errors
    ///
    /// Any I/O error on the streams.
    pub fn serve_mcp<R: BufRead, W: Write>(
        &self,
        input: R,
        mut output: W,
        cwd: &Path,
    ) -> std::io::Result<()> {
        tracing::info!(tools = self.mcp_tools().len(), "mcp server started");
        for line in input.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let reply = match serde_json::from_str::<Value>(&line) {
                Ok(msg) => self.mcp_handle(&msg, cwd),
                Err(e) => Some(rpc_error(&Value::Null, code::PARSE, &e.to_string())),
            };
            if let Some(reply) = reply {
                writeln!(output, "{reply}")?;
                output.flush()?;
            }
        }
        tracing::info!("mcp server stopped: input closed");
        Ok(())
    }
}

/// A JSON-RPC error response.
fn rpc_error(id: &Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}
