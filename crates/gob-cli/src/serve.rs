//! The built-in `serve` verb: a read-only MCP server generated from verb metadata.
//!
//! Every live verb declared `#[command(read_only)]` becomes one MCP tool whose input schema is
//! derived from the verb's own clap arguments and whose result is the same JSON envelope the CLI
//! prints, so there is no second API to keep in sync (cli.md, "frob serve"). Mutating verbs are
//! never listed and the write flags of read-only verbs (`--fix`, `--dry-run`) are not exposed.
//! The transport is newline-delimited JSON-RPC 2.0 on stdin and stdout; EOF on stdin ends the
//! server, and between requests it blocks on stdin, so an idle server uses no CPU.

// frob:ticket 01M44AZ69FG7NFQFNAWMQ1NM4Q

use std::ffi::OsString;
use std::io::{BufRead, Write};
use std::path::Path;

use clap::{Arg, ArgAction, ArgMatches};
use serde_json::{Map, Value, json};

use crate::cli::Cli;
use crate::command::Command;
use crate::context::Context;
use crate::error::{CliError, Outcome};

/// MCP protocol revision announced when the client does not name one.
const DEFAULT_PROTOCOL: &str = "2025-06-18";

/// Argument ids that are never exposed to a tool call: global flags, clap built-ins and write flags.
const HIDDEN_ARGS: &[&str] = &[
    "format", "json", "text", "quiet", "verbose", "color", "cwd", "schema", "help", "version",
    "dry_run", "fix",
];

/// Serve the read-only verbs of this product as MCP tools over stdin and stdout.
#[derive(Debug, Clone, Copy, Default, crate::Command)]
#[command(verb = "serve", product = "any", exits(ok, usage, internal))]
pub struct ServeCmd;

impl ServeCmd {
    /// The verb path the root intercepts to start the MCP loop.
    pub(crate) const VERB: &'static str = "serve";
}

impl Command for ServeCmd {
    type Data = ();

    fn configure(cmd: clap::Command) -> clap::Command {
        cmd.arg(
            Arg::new("mcp")
                .long("mcp")
                .action(ArgAction::SetTrue)
                .help("Speak MCP over stdio (the default and only transport)"),
        )
    }

    fn from_matches(_matches: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, _ctx: &Context) -> Outcome<()> {
        Err(CliError::internal(
            "serve is started by the root, not run as a buffered verb",
        ))
    }
}

/// Why the MCP transport stopped.
#[derive(Debug, thiserror::Error)]
pub enum ServeError {
    /// Reading a request or writing a reply failed.
    #[error("mcp transport i/o failed: {0}")]
    Io(#[from] std::io::Error),
}

/// How one argument is passed on the command line.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Shape {
    Flag,
    Count,
    One,
    Many,
}

/// One tool input property and how to turn it back into argv.
#[derive(Debug, Clone)]
struct Param {
    key: String,
    long: Option<String>,
    short: Option<char>,
    index: Option<usize>,
    shape: Shape,
    required: bool,
    schema: Value,
}

/// One MCP tool: a read-only verb with its argv mapping.
#[derive(Debug, Clone)]
struct Tool {
    name: String,
    verb: &'static str,
    summary: &'static str,
    params: Vec<Param>,
}

impl Tool {
    /// The MCP `tools/list` entry; the input schema is the verb's argument schema.
    fn listing(&self) -> Value {
        let properties: Map<String, Value> = self
            .params
            .iter()
            .map(|p| (p.key.clone(), p.schema.clone()))
            .collect();
        let required: Vec<&str> = self
            .params
            .iter()
            .filter(|p| p.required)
            .map(|p| p.key.as_str())
            .collect();
        json!({
            "name": self.name,
            "description": self.summary,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": false,
            },
            "annotations": { "readOnlyHint": true, "idempotentHint": true },
        })
    }
}

/// The tool name of a verb: product and verb words joined by underscores.
fn tool_name(product: &str, verb: &str) -> String {
    format!("{product}_{}", verb.replace([' ', '-'], "_"))
}

/// The JSON Schema property for one clap argument, plus the way it is passed.
fn param_of(arg: &Arg) -> Param {
    let shape = match arg.get_action() {
        ArgAction::SetTrue | ArgAction::SetFalse => Shape::Flag,
        ArgAction::Count => Shape::Count,
        ArgAction::Append => Shape::Many,
        _ if arg.get_num_args().is_some_and(|r| r.max_values() > 1) => Shape::Many,
        _ => Shape::One,
    };
    let long = arg.get_long().map(str::to_owned);
    let short = arg.get_short();
    let positional = long.is_none() && short.is_none();
    let key = long.clone().unwrap_or_else(|| arg.get_id().to_string());
    let mut scalar = Map::new();
    scalar.insert("type".into(), json!("string"));
    let values: Vec<String> = arg
        .get_possible_values()
        .iter()
        .filter(|v| !v.is_hide_set())
        .map(|v| v.get_name().to_owned())
        .collect();
    if !values.is_empty() {
        scalar.insert("enum".into(), json!(values));
    }
    let mut schema = match shape {
        Shape::Flag => json!({ "type": "boolean" }),
        Shape::Count => json!({ "type": "integer", "minimum": 0 }),
        Shape::One => Value::Object(scalar),
        Shape::Many => json!({ "type": "array", "items": Value::Object(scalar) }),
    };
    if let (Some(help), Some(obj)) = (arg.get_help(), schema.as_object_mut()) {
        obj.insert("description".into(), json!(help.to_string()));
    }
    Param {
        key,
        long,
        short,
        index: positional.then(|| arg.get_index().unwrap_or(usize::MAX)),
        shape,
        required: arg.is_required_set(),
        schema,
    }
}

/// Find the clap command of `verb` (words separated by spaces) under `root`.
fn find_leaf<'a>(root: &'a clap::Command, verb: &str) -> Option<&'a clap::Command> {
    verb.split(' ').try_fold(root, |cmd, word| {
        cmd.get_subcommands().find(|c| c.get_name() == word)
    })
}

/// Render a scalar JSON value as one argv word.
fn word(key: &str, v: &Value) -> Result<String, String> {
    match v {
        Value::String(s) => Ok(s.clone()),
        Value::Number(n) => Ok(n.to_string()),
        Value::Bool(b) => Ok(b.to_string()),
        _ => Err(format!(
            "argument `{key}` must be a string, number or boolean"
        )),
    }
}

/// Turn tool arguments into the verb's argv (always `--json`); options first, positionals after `--`.
fn argv_of(tool: &Tool, given: &Map<String, Value>) -> Result<Vec<OsString>, String> {
    let mut argv: Vec<OsString> = tool.verb.split(' ').map(OsString::from).collect();
    argv.push("--json".into());
    let mut positionals: Vec<(usize, String)> = Vec::new();
    for (key, value) in given {
        let Some(p) = tool.params.iter().find(|p| &p.key == key) else {
            return Err(format!("unknown argument `{key}` for `{}`", tool.name));
        };
        let values: Vec<&Value> = match (p.shape, value) {
            (Shape::Many, Value::Array(items)) => items.iter().collect(),
            _ => vec![value],
        };
        if let Some(index) = p.index {
            for v in values {
                positionals.push((index, word(key, v)?));
            }
            continue;
        }
        let flag = match (&p.long, p.short) {
            (Some(l), _) => format!("--{l}"),
            (None, Some(s)) => format!("-{s}"),
            (None, None) => unreachable!("a non-positional has a flag name"),
        };
        match p.shape {
            Shape::Flag => {
                if value
                    .as_bool()
                    .ok_or_else(|| format!("`{key}` must be a boolean"))?
                {
                    argv.push(flag.into());
                }
            }
            Shape::Count => {
                let n = value
                    .as_u64()
                    .ok_or_else(|| format!("`{key}` must be a non-negative integer"))?;
                argv.extend((0..n).map(|_| OsString::from(&flag)));
            }
            Shape::One | Shape::Many => {
                for v in values {
                    let w = word(key, v)?;
                    if p.long.is_some() {
                        argv.push(format!("{flag}={w}").into());
                    } else {
                        argv.extend([OsString::from(&flag), w.into()]);
                    }
                }
            }
        }
    }
    if !positionals.is_empty() {
        positionals.sort_by_key(|(i, _)| *i);
        argv.push("--".into());
        argv.extend(positionals.into_iter().map(|(_, w)| OsString::from(w)));
    }
    Ok(argv)
}

/// A JSON-RPC error reply.
fn rpc_error(id: &Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}

impl Cli {
    /// The MCP tools: one per live read-only verb of this product, sorted by name.
    fn mcp_tools(&self) -> Vec<Tool> {
        let root = self.build(false);
        let mut tools: Vec<Tool> = self
            .verbs
            .iter()
            .filter(|v| {
                v.meta.read_only
                    && v.meta.deprecated.is_none()
                    && (v.meta.product == self.product || v.meta.product == "any")
            })
            .filter_map(|v| {
                let leaf = find_leaf(&root, v.meta.verb)?;
                let params = leaf
                    .get_arguments()
                    .filter(|a| !HIDDEN_ARGS.contains(&a.get_id().as_str()))
                    .map(param_of)
                    .collect();
                Some(Tool {
                    name: tool_name(self.product, v.meta.verb),
                    verb: v.meta.verb,
                    summary: v.meta.summary,
                    params,
                })
            })
            .collect();
        tools.sort_by(|a, b| a.name.cmp(&b.name));
        tracing::debug!(
            tools = tools.len(),
            "mcp tools generated from verb metadata"
        );
        tools
    }

    /// Serve MCP (newline-delimited JSON-RPC) from `input` to `out` until EOF, running tools in `cwd`.
    ///
    /// # Errors
    ///
    /// [`ServeError::Io`] when reading a request or writing a reply fails.
    pub fn serve_mcp<R: BufRead, W: Write>(
        &self,
        input: R,
        out: &mut W,
        cwd: &Path,
    ) -> Result<(), ServeError> {
        let tools = self.mcp_tools();
        tracing::info!(tools = tools.len(), "mcp server ready");
        for line in input.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(reply) = self.mcp_reply(&tools, &line, cwd) {
                writeln!(out, "{reply}")?;
                out.flush()?;
            }
        }
        tracing::info!("mcp server: stdin closed, exiting");
        Ok(())
    }

    /// The reply to one request line, or `None` for a notification.
    fn mcp_reply(&self, tools: &[Tool], line: &str, cwd: &Path) -> Option<Value> {
        let Ok(msg) = serde_json::from_str::<Value>(line) else {
            tracing::debug!("mcp: unparseable request");
            return Some(rpc_error(&Value::Null, -32700, "parse error"));
        };
        let Some(obj) = msg.as_object() else {
            return Some(rpc_error(&Value::Null, -32600, "request must be an object"));
        };
        let id = obj.get("id").cloned();
        let method = obj
            .get("method")
            .and_then(Value::as_str)
            .unwrap_or_default();
        tracing::debug!(method, "mcp request");
        let id = id?;
        let params = obj.get("params").cloned().unwrap_or(Value::Null);
        let result = match method {
            "initialize" => json!({
                "protocolVersion": params
                    .get("protocolVersion")
                    .and_then(Value::as_str)
                    .unwrap_or(DEFAULT_PROTOCOL),
                "capabilities": { "tools": { "listChanged": false } },
                "serverInfo": { "name": self.product, "version": self.version },
            }),
            "ping" => json!({}),
            "tools/list" => json!({ "tools": tools.iter().map(Tool::listing).collect::<Vec<_>>() }),
            "tools/call" => match self.mcp_call(tools, &params, cwd) {
                Ok(v) => v,
                Err(message) => return Some(rpc_error(&id, -32602, &message)),
            },
            _ => return Some(rpc_error(&id, -32601, "method not found")),
        };
        Some(json!({ "jsonrpc": "2.0", "id": id, "result": result }))
    }

    /// Run one `tools/call`: the result text is the CLI's JSON envelope for the verb.
    fn mcp_call(&self, tools: &[Tool], params: &Value, cwd: &Path) -> Result<Value, String> {
        let name = params
            .get("name")
            .and_then(Value::as_str)
            .ok_or("tools/call needs a tool name")?;
        let tool = tools
            .iter()
            .find(|t| t.name == name)
            .ok_or_else(|| format!("unknown tool `{name}`"))?;
        let empty = Map::new();
        let given = match params.get("arguments") {
            None | Some(Value::Null) => &empty,
            Some(Value::Object(m)) => m,
            Some(_) => return Err("arguments must be an object".to_owned()),
        };
        let argv = argv_of(tool, given)?;
        tracing::info!(tool = name, "mcp tool call");
        let exec = self.execute(argv, Some(cwd), false);
        let text = if exec.stdout.is_empty() {
            exec.stderr
        } else {
            exec.stdout
        };
        Ok(json!({
            "content": [{ "type": "text", "text": text.trim_end() }],
            "isError": exec.exit >= 2,
        }))
    }
}
