//! The serve patch tool: `edit --patch` exposed as a write MCP tool (opt-in).
//!
//! The tool wraps [`crate::edit::apply_patch_text`], the same engine as the `edit` verb, so there
//! is no second patch engine: an RFC 6902 patch addressed by stable id is applied to a design
//! file, re-validated by the file kind's schema, written atomically, and the reply carries the
//! unified diff and the findings of the touched nodes only.
//!
//! Write tools are opt-in. [`PatchTool::new`] takes `allow_write`; without it [`PatchTool::listing`]
//! is empty and a call is refused as an unknown tool, exactly as if the tool did not exist.
//!
//! # Edge cases
//!
//! - A patch that fails to apply or whose result fails schema validation writes nothing and
//!   returns an error result with the stable code, the file, and the located message
//!   (the operation index and pointer for a patch error, the parser's line for a schema error).
//! - `dry_run: true` plans and reports the diff without writing.
//! - A file outside the project root is refused (`E-EDIT-PATH`).

// frob:ticket 01M5XCW9ZZ5GX5VGERB6H96M2G

use std::path::{Path, PathBuf};

use serde_json::{Value, json};

use crate::edit::{EditError, apply_patch_text};

/// The MCP tool name.
pub const TOOL_NAME: &str = "crunk_edit_patch";

/// The write patch tool, bound to a project root and a write permission.
#[derive(Debug, Clone)]
pub struct PatchTool {
    root: PathBuf,
    allow_write: bool,
}

impl PatchTool {
    /// A patch tool over `root`; the tool is absent unless `allow_write` is true.
    #[must_use]
    pub fn new(root: &Path, allow_write: bool) -> Self {
        tracing::info!(root = %root.display(), allow_write, "serve patch tool configured");
        Self {
            root: root.to_path_buf(),
            allow_write,
        }
    }

    /// The MCP `tools/list` entries this tool contributes: empty in a read-only session.
    #[must_use]
    pub fn listing(&self) -> Vec<Value> {
        if !self.allow_write {
            return Vec::new();
        }
        vec![json!({
            "name": TOOL_NAME,
            "description": "Apply an RFC 6902 patch, addressed by stable id, to a screen, component or content file; returns the diff and the findings of the touched nodes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file": { "type": "string", "description": "Design file, relative to the project root" },
                    "patch": { "type": "array", "items": { "type": "object" }, "description": "RFC 6902 operations; array elements are addressed by id or name" },
                    "dry_run": { "type": "boolean", "description": "Plan and diff without writing" },
                },
                "required": ["file", "patch"],
                "additionalProperties": false,
            },
            "annotations": { "readOnlyHint": false, "idempotentHint": false, "destructiveHint": true },
        })]
    }

    /// Run a `tools/call` for `name` with `arguments`: the MCP result, or a message for an
    /// unknown tool or malformed arguments (a JSON-RPC invalid-params error).
    ///
    /// # Errors
    ///
    /// A message when `name` is not this tool (or writes are not allowed) or the arguments are
    /// not `{file, patch, dry_run?}`.
    pub fn call(&self, name: &str, arguments: &Value) -> Result<Value, String> {
        if name != TOOL_NAME || !self.allow_write {
            tracing::debug!(name, "serve patch tool: not offered");
            return Err(format!("unknown tool `{name}`"));
        }
        let (file, patch, dry_run) = parse_arguments(arguments)?;
        let path = crunk_spec::normalize_join(&self.root, &file);
        tracing::info!(file, dry_run, "serve patch tool call");
        let result = apply_patch_text(&self.root, &path, &patch.to_string(), dry_run);
        Ok(match result {
            Ok(data) => reply(false, &json!(data)),
            Err(e) => reply(true, &failure(&e, &file)),
        })
    }
}

/// The `{file, patch, dry_run}` arguments of a call.
fn parse_arguments(arguments: &Value) -> Result<(String, Value, bool), String> {
    let obj = arguments
        .as_object()
        .ok_or("arguments must be an object with `file` and `patch`")?;
    if let Some(extra) = obj
        .keys()
        .find(|k| !matches!(k.as_str(), "file" | "patch" | "dry_run"))
    {
        return Err(format!("unknown argument `{extra}` for `{TOOL_NAME}`"));
    }
    let file = obj
        .get("file")
        .and_then(Value::as_str)
        .ok_or("`file` must be a string")?;
    let patch = obj
        .get("patch")
        .filter(|p| p.is_array())
        .ok_or("`patch` must be an array of RFC 6902 operations")?;
    let dry_run = match obj.get("dry_run") {
        None | Some(Value::Null) => false,
        Some(v) => v.as_bool().ok_or("`dry_run` must be a boolean")?,
    };
    Ok((file.to_owned(), patch.clone(), dry_run))
}

/// A located, coded error body: nothing was written.
fn failure(err: &EditError, file: &str) -> Value {
    tracing::info!(code = err.code(), file, "serve patch tool: refused");
    json!({
        "code": err.code(),
        "file": file,
        "message": err.to_string(),
        "written": false,
    })
}

/// An MCP tool result carrying `body` as JSON text.
fn reply(is_error: bool, body: &Value) -> Value {
    json!({
        "content": [{ "type": "text", "text": body.to_string() }],
        "isError": is_error,
    })
}
