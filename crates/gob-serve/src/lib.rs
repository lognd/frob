//! Shared MCP transport plumbing: the per-launch token (D29), JSON-RPC 2.0 dispatch and a
//! newline-delimited line transport.
//!
//! A product supplies a [`Tools`] implementation (a fixed list of read-only tools) and a
//! [`Token`]; [`Server`] does everything else. Every request that carries an `id` must present
//! the token in `params._meta.token`; a request without it, with an empty one or with a wrong
//! one is refused with [`CODE_UNAUTHORIZED`] before the method is even looked at, so an
//! unauthenticated peer learns nothing (not the tool list, not whether a tool exists).
//! Notifications get no reply, authenticated or not. The token is compared in constant time and
//! is never written to a log: [`Token`] has no `Display` and a redacted `Debug`.
//!
//! The server is read-only by construction: it dispatches only names that [`Tools::list`]
//! returned, every listing is annotated `readOnlyHint`, and [`Tools::call`] takes `&self`.
//! The core stays synchronous; the transport blocks on its input, so an idle server uses no CPU.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use std::fmt::{self, Write as _};
use std::io::{BufRead, Write};

use serde_json::{Map, Value, json};
use subtle::ConstantTimeEq;

/// JSON-RPC code for a request whose token is missing, empty or wrong.
pub const CODE_UNAUTHORIZED: i64 = -32001;
/// JSON-RPC code for malformed JSON.
pub const CODE_PARSE: i64 = -32700;
/// JSON-RPC code for a request that is not a single JSON-RPC request object.
pub const CODE_INVALID_REQUEST: i64 = -32600;
/// JSON-RPC code for a method the server does not implement.
pub const CODE_METHOD_NOT_FOUND: i64 = -32601;
/// JSON-RPC code for bad parameters, including an unknown tool name.
pub const CODE_INVALID_PARAMS: i64 = -32602;

/// MCP protocol revision announced when the client does not name one.
const DEFAULT_PROTOCOL: &str = "2025-06-18";
/// Random bytes in a generated token (rendered as twice as many hex digits).
const TOKEN_BYTES: usize = 32;

/// Why the plumbing failed.
#[derive(Debug, thiserror::Error)]
pub enum ServeError {
    /// The operating system gave no randomness for the token.
    #[error("no randomness available for the launch token: {0}")]
    Entropy(String),
    /// Reading a request or writing a reply failed.
    #[error("mcp transport i/o failed: {0}")]
    Io(#[from] std::io::Error),
}

/// The per-launch secret every request must present.
#[derive(Clone, PartialEq, Eq)]
pub struct Token(String);

impl Token {
    /// A fresh random token (64 hex digits) for this launch.
    ///
    /// # Errors
    ///
    /// [`ServeError::Entropy`] when the OS random source fails.
    pub fn generate() -> Result<Self, ServeError> {
        let mut bytes = [0u8; TOKEN_BYTES];
        getrandom::fill(&mut bytes).map_err(|e| ServeError::Entropy(e.to_string()))?;
        let hex = bytes
            .iter()
            .fold(String::with_capacity(TOKEN_BYTES * 2), |mut acc, b| {
                let _ = write!(acc, "{b:02x}");
                acc
            });
        tracing::debug!("launch token generated");
        Ok(Self(hex))
    }

    /// A token from a known value (tests, or a launcher that supplies one); `None` when empty,
    /// because an empty token would let an empty presentation through.
    pub fn from_value(value: &str) -> Option<Self> {
        (!value.is_empty()).then(|| Self(value.to_owned()))
    }

    /// The secret text, for handing to the one legitimate client; never log it.
    pub fn expose(&self) -> &str {
        &self.0
    }

    /// True when `presented` equals this token, compared in constant time; empty never matches.
    pub fn verify(&self, presented: &str) -> bool {
        !presented.is_empty() && bool::from(self.0.as_bytes().ct_eq(presented.as_bytes()))
    }
}

impl fmt::Debug for Token {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("Token(<redacted>)")
    }
}

/// One tool as listed to the client.
#[derive(Debug, Clone)]
pub struct ToolSpec {
    /// Tool name, the key of `tools/call`.
    pub name: String,
    /// One-line description.
    pub description: String,
    /// JSON Schema of the arguments object.
    pub input_schema: Value,
}

impl ToolSpec {
    /// The MCP `tools/list` entry, always annotated read-only and idempotent.
    fn listing(&self) -> Value {
        json!({
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": { "readOnlyHint": true, "idempotentHint": true },
        })
    }
}

/// The product's read-only tools.
pub trait Tools {
    /// Every tool on offer; only these names are ever dispatched.
    fn list(&self) -> Vec<ToolSpec>;

    /// Run the named tool, returning its JSON result, or a message when the call itself failed.
    ///
    /// # Errors
    ///
    /// The failure text, reported to the client as a tool error.
    fn call(&self, name: &str, arguments: &Map<String, Value>) -> Result<Value, String>;
}

/// An MCP server over a [`Tools`] set, guarded by a [`Token`].
pub struct Server<T: Tools> {
    name: String,
    version: String,
    token: Token,
    tools: T,
}

impl<T: Tools> Server<T> {
    /// A server announcing `name` and `version`, serving `tools` to whoever holds `token`.
    pub fn new(name: &str, version: &str, token: Token, tools: T) -> Self {
        Self {
            name: name.to_owned(),
            version: version.to_owned(),
            token,
            tools,
        }
    }

    /// Serve newline-delimited JSON-RPC from `input` to `out` until EOF.
    ///
    /// # Errors
    ///
    /// [`ServeError::Io`] when reading a request or writing a reply fails.
    pub fn serve<R: BufRead, W: Write>(&self, input: R, out: &mut W) -> Result<(), ServeError> {
        tracing::info!(server = %self.name, "mcp server ready");
        for line in input.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Some(reply) = self.handle_line(&line) {
                writeln!(out, "{reply}")?;
                out.flush()?;
            }
        }
        tracing::info!("mcp server: input closed, exiting");
        Ok(())
    }

    /// The reply to one request line, or `None` for a notification.
    pub fn handle_line(&self, line: &str) -> Option<Value> {
        let Ok(msg) = serde_json::from_str::<Value>(line) else {
            tracing::debug!("mcp: unparseable request");
            return Some(rpc_error(&Value::Null, CODE_PARSE, "parse error"));
        };
        let Some(obj) = msg.as_object() else {
            tracing::debug!("mcp: request is not an object");
            return Some(rpc_error(
                &Value::Null,
                CODE_INVALID_REQUEST,
                "request must be a single object",
            ));
        };
        let id = obj.get("id").cloned();
        let params = obj.get("params").cloned().unwrap_or(Value::Null);
        let presented = params
            .pointer("/_meta/token")
            .and_then(Value::as_str)
            .unwrap_or_default();
        if !self.token.verify(presented) {
            tracing::warn!(
                has_token = !presented.is_empty(),
                "mcp: request refused, token missing or wrong"
            );
            return id
                .map(|id| rpc_error(&id, CODE_UNAUTHORIZED, "unauthorized: bad or missing token"));
        }
        let method = obj
            .get("method")
            .and_then(Value::as_str)
            .unwrap_or_default();
        tracing::debug!(method, "mcp request");
        let id = id?;
        match self.dispatch(method, &params) {
            Ok(result) => Some(json!({ "jsonrpc": "2.0", "id": id, "result": result })),
            Err((code, message)) => Some(rpc_error(&id, code, &message)),
        }
    }

    /// Route an authenticated request to its result or a `(code, message)` error.
    fn dispatch(&self, method: &str, params: &Value) -> Result<Value, (i64, String)> {
        match method {
            "initialize" => Ok(json!({
                "protocolVersion": params
                    .get("protocolVersion")
                    .and_then(Value::as_str)
                    .unwrap_or(DEFAULT_PROTOCOL),
                "capabilities": { "tools": { "listChanged": false } },
                "serverInfo": { "name": self.name, "version": self.version },
            })),
            "ping" => Ok(json!({})),
            "tools/list" => {
                let mut listed = Vec::new();
                for spec in self.tools.list() {
                    listed.push(spec.listing());
                }
                Ok(json!({ "tools": listed }))
            }
            "tools/call" => self.call(params).map_err(|m| (CODE_INVALID_PARAMS, m)),
            _ => Err((CODE_METHOD_NOT_FOUND, "method not found".to_owned())),
        }
    }

    /// Run one `tools/call`; an unlisted name or non-object arguments are invalid params.
    fn call(&self, params: &Value) -> Result<Value, String> {
        let name = params
            .get("name")
            .and_then(Value::as_str)
            .ok_or("tools/call needs a tool name")?;
        if !self.tools.list().iter().any(|t| t.name == name) {
            tracing::warn!(tool = name, "mcp: unknown tool requested");
            return Err(format!("unknown tool `{name}`"));
        }
        let empty = Map::new();
        let arguments = match params.get("arguments") {
            None | Some(Value::Null) => &empty,
            Some(Value::Object(m)) => m,
            Some(_) => return Err("arguments must be an object".to_owned()),
        };
        tracing::info!(tool = name, "mcp tool call");
        let (text, is_error) = match self.tools.call(name, arguments) {
            Ok(v) => (v.to_string(), false),
            Err(message) => (message, true),
        };
        Ok(json!({ "content": [{ "type": "text", "text": text }], "isError": is_error }))
    }
}

/// A JSON-RPC error reply.
fn rpc_error(id: &Value, code: i64, message: &str) -> Value {
    json!({ "jsonrpc": "2.0", "id": id, "error": { "code": code, "message": message } })
}
