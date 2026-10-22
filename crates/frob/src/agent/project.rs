//! Project-scope Claude Code settings: `<repo>/.claude/settings.json` gains the frob MCP server and a
//! permission allowlist for frob's read-only verbs.
//!
//! Merge-only by construction: unrelated keys are preserved, an existing `mcpServers.frob` entry is the
//! user's and is kept, allowlist entries are appended only when absent, and a file that is not valid JSON
//! (or has the wrong shape) is an error that leaves it untouched.

// frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A

use std::path::Path;

use serde_json::{Value, json};

use super::AgentError;
use super::claude::{load_settings, write_settings};

/// Repository-relative path of the project settings file.
pub const PROJECT_SETTINGS: &str = ".claude/settings.json";

/// Name of the MCP server entry frob registers.
const SERVER: &str = "frob";

/// The `Bash(...)` permission rules for frob's read-only verbs.
pub const READ_ALLOWLIST: &[&str] = &[
    "Bash(frob ticket show:*)",
    "Bash(frob ticket list:*)",
    "Bash(frob ticket doable:*)",
    "Bash(frob lease list:*)",
    "Bash(frob board:*)",
    "Bash(frob check:*)",
    "Bash(frob stats:*)",
    "Bash(frob doctor:*)",
    "Bash(frob explain:*)",
    "Bash(frob config show:*)",
    "Bash(frob agent status:*)",
];

fn shape(path: &Path, detail: &str) -> AgentError {
    AgentError::Shape {
        path: path.to_path_buf(),
        detail: detail.to_owned(),
    }
}

/// The object at `parent[key]`, created empty when absent; a non-object is a shape error.
fn object_at<'a>(
    path: &Path,
    parent: &'a mut Value,
    key: &str,
) -> Result<&'a mut serde_json::Map<String, Value>, AgentError> {
    let slot = parent
        .as_object_mut()
        .ok_or_else(|| shape(path, "top level is not an object"))?
        .entry(key)
        .or_insert_with(|| json!({}));
    slot.as_object_mut()
        .ok_or_else(|| shape(path, &format!("`{key}` is not an object")))
}

/// Merge the frob MCP server and read allowlist into `settings`; true when anything was added.
fn merge(path: &Path, settings: &mut Value) -> Result<bool, AgentError> {
    let mut changed = false;
    let servers = object_at(path, settings, "mcpServers")?;
    if !servers.contains_key(SERVER) {
        servers.insert(
            SERVER.to_owned(),
            json!({"command": "frob", "args": ["serve", "--mcp"]}),
        );
        changed = true;
        tracing::info!("frob MCP server added to project settings");
    }
    let perms = object_at(path, settings, "permissions")?;
    let allow = perms
        .entry("allow")
        .or_insert_with(|| json!([]))
        .as_array_mut()
        .ok_or_else(|| shape(path, "`permissions.allow` is not an array"))?;
    for rule in READ_ALLOWLIST {
        if !allow.iter().any(|e| e.as_str() == Some(rule)) {
            allow.push(json!(rule));
            changed = true;
            tracing::info!(rule, "allowlist entry added");
        }
    }
    Ok(changed)
}

// frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
/// Write the frob MCP server and read-verb allowlist into `<root>/.claude/settings.json`; true when the file changed (or would).
///
/// # Errors
/// [`AgentError::Json`] for a file that is not valid JSON and [`AgentError::Shape`] for one whose
/// `mcpServers`, `permissions` or `permissions.allow` has the wrong type; the file is left untouched.
pub fn configure(root: &Path, dry_run: bool) -> Result<bool, AgentError> {
    let path = root.join(PROJECT_SETTINGS);
    let mut settings = load_settings(&path)?;
    if !merge(&path, &mut settings)? {
        tracing::debug!(path = %gob_path::Shown::of(&path), "project settings already configured");
        return Ok(false);
    }
    write_settings(&path, &settings, dry_run)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn read(root: &Path) -> Value {
        serde_json::from_slice(&std::fs::read(root.join(PROJECT_SETTINGS)).unwrap()).unwrap()
    }

    fn write(root: &Path, text: &str) {
        std::fs::create_dir_all(root.join(".claude")).unwrap();
        std::fs::write(root.join(PROJECT_SETTINGS), text).unwrap();
    }

    fn allow(v: &Value) -> Vec<&str> {
        v["permissions"]["allow"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(Value::as_str)
            .collect()
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn a_missing_claude_dir_is_created_with_the_server_and_allowlist() {
        let dir = tempfile::tempdir().unwrap();
        assert!(configure(dir.path(), false).unwrap());
        let v = read(dir.path());
        assert_eq!(v["mcpServers"]["frob"]["args"], json!(["serve", "--mcp"]));
        assert_eq!(allow(&v), READ_ALLOWLIST);
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn running_twice_changes_nothing_and_duplicates_nothing() {
        let dir = tempfile::tempdir().unwrap();
        configure(dir.path(), false).unwrap();
        let first = std::fs::read(dir.path().join(PROJECT_SETTINGS)).unwrap();
        assert!(!configure(dir.path(), false).unwrap());
        assert_eq!(
            std::fs::read(dir.path().join(PROJECT_SETTINGS)).unwrap(),
            first
        );
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn an_existing_file_keeps_unrelated_keys_other_servers_and_allow_entries() {
        let dir = tempfile::tempdir().unwrap();
        write(
            dir.path(),
            r#"{"model":"x","mcpServers":{"other":{"command":"o"}},
                "permissions":{"deny":["Bash(rm:*)"],"allow":["Bash(ls:*)","Bash(frob board:*)"]}}"#,
        );
        assert!(configure(dir.path(), false).unwrap());
        let v = read(dir.path());
        assert_eq!(v["model"], "x");
        assert_eq!(v["mcpServers"]["other"]["command"], "o");
        assert_eq!(v["permissions"]["deny"], json!(["Bash(rm:*)"]));
        let a = allow(&v);
        assert_eq!(a[0], "Bash(ls:*)");
        assert_eq!(a.iter().filter(|e| **e == "Bash(frob board:*)").count(), 1);
        assert_eq!(a.len(), READ_ALLOWLIST.len() + 1);
        assert!(dir.path().join(".claude/settings.json.frob-bak").exists());
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn a_users_own_frob_server_entry_is_never_overwritten() {
        let dir = tempfile::tempdir().unwrap();
        write(
            dir.path(),
            r#"{"mcpServers":{"frob":{"command":"/opt/frob"}}}"#,
        );
        configure(dir.path(), false).unwrap();
        assert_eq!(
            read(dir.path())["mcpServers"]["frob"]["command"],
            "/opt/frob"
        );
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn malformed_json_is_an_error_and_the_file_is_untouched() {
        let dir = tempfile::tempdir().unwrap();
        write(dir.path(), "{ not json");
        let e = configure(dir.path(), false).unwrap_err();
        assert!(matches!(e, AgentError::Json { .. }), "{e}");
        assert_eq!(
            std::fs::read_to_string(dir.path().join(PROJECT_SETTINGS)).unwrap(),
            "{ not json"
        );
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn a_wrongly_shaped_file_is_a_shape_error_and_untouched() {
        for bad in [
            "[]",
            r#"{"mcpServers":[]}"#,
            r#"{"permissions":"x"}"#,
            r#"{"permissions":{"allow":{}}}"#,
        ] {
            let dir = tempfile::tempdir().unwrap();
            write(dir.path(), bad);
            let e = configure(dir.path(), false).unwrap_err();
            assert!(matches!(e, AgentError::Shape { .. }), "{bad}: {e}");
            assert_eq!(
                std::fs::read_to_string(dir.path().join(PROJECT_SETTINGS)).unwrap(),
                bad
            );
        }
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn a_dry_run_reports_the_change_without_writing() {
        let dir = tempfile::tempdir().unwrap();
        assert!(configure(dir.path(), true).unwrap());
        assert!(!dir.path().join(PROJECT_SETTINGS).exists());
    }

    // frob:ticket 01M4CTV1F6JTX89DKB1QKDYH7A
    // frob:tests crates/frob/src/agent/project.rs::configure
    #[test]
    fn an_empty_file_counts_as_an_empty_object() {
        let dir = tempfile::tempdir().unwrap();
        write(dir.path(), "  \n");
        assert!(configure(dir.path(), false).unwrap());
        assert_eq!(allow(&read(dir.path())), READ_ALLOWLIST);
    }
}
