//! Pure decisions behind `frob agent hook`: parse a Claude Code hook payload and build the reply JSON.
//!
//! Every function here is side-effect free (the file size is passed in) so the policy is unit-testable;
//! the verb in `agent_hook_cmd` does the I/O. The guiding rule is fail open: a payload that cannot be
//! understood yields the empty reply `{}`, which lets the agent proceed.

// frob:ticket 01M4P2N1D8ZJN8A3EDD9T7ZT21

use std::path::{Path, PathBuf};

use serde::Deserialize;
use serde_json::{Value, json};

/// The hook events `frob agent hook` handles.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Event {
    /// `PreToolUse` on the Bash tool.
    PreBash,
    /// `PreToolUse` on the Read tool.
    PreRead,
    /// `SessionStart`.
    SessionStart,
    /// `PreCompact`.
    PreCompact,
    /// `UserPromptSubmit`.
    UserPrompt,
    /// `Stop`.
    Stop,
}

/// The fields of Claude Code's hook payload the handlers use; unknown fields are ignored.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct HookInput {
    /// The tool's input object (`command`, `file_path`, `offset`, `limit`).
    #[serde(default)]
    pub tool_input: Value,
    /// The agent's working directory, used to resolve relative read paths.
    #[serde(default)]
    pub cwd: Option<String>,
    /// True when a Stop hook already blocked once this turn.
    #[serde(default)]
    pub stop_hook_active: bool,
}

/// Why a payload could not be used.
#[derive(Debug, thiserror::Error)]
#[error("hook payload is not valid JSON: {0}")]
pub struct PayloadError(#[from] serde_json::Error);

/// Parse the stdin text of a hook call; an empty payload is an empty input.
///
/// # Errors
///
/// [`PayloadError`] when the text is non-empty and not a JSON object of the expected shape.
pub fn parse(text: &str) -> Result<HookInput, PayloadError> {
    if text.trim().is_empty() {
        return Ok(HookInput::default());
    }
    Ok(serde_json::from_str(text)?)
}

/// The thresholds the pre-tool handlers apply, taken from `[agent]`.
#[derive(Debug, Clone)]
pub struct Policy {
    /// Largest file readable whole, in bytes.
    pub read_max_bytes: u64,
    /// Lines to cap unbounded output at.
    pub bash_max_lines: u64,
    /// Command prefixes that must go through `frob agent heavy`.
    pub heavy: Vec<String>,
}

/// Commands whose output is unbounded unless piped or redirected.
const NOISY: [&str; 6] = ["cat", "find", "git log", "git diff", "grep -r", "ls -R"];

/// The reply that lets the agent proceed unchanged.
#[must_use]
pub fn allow() -> Value {
    json!({})
}

/// A `PreToolUse` reply carrying `decision` and its `reason`, plus optional rewritten tool input.
fn pre_tool(decision: &str, reason: &str, updated: Option<Value>) -> Value {
    let mut out = json!({
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    });
    if let Some(u) = updated {
        out["updatedInput"] = u;
    }
    json!({ "hookSpecificOutput": out })
}

/// True when `reply` is a `PreToolUse` deny.
#[must_use]
pub fn is_deny(reply: &Value) -> bool {
    reply["hookSpecificOutput"]["permissionDecision"] == "deny"
}

/// Which `pre-bash` guard produced `reply`: `pre-bash-heavy` (deny), `pre-bash-cap` (rewrite) or none.
#[must_use]
pub fn bash_guard(reply: &Value) -> Option<&'static str> {
    if is_deny(reply) {
        Some("pre-bash-heavy")
    } else if reply["hookSpecificOutput"].get("updatedInput").is_some() {
        Some("pre-bash-cap")
    } else {
        None
    }
}

/// Deny a whole-file read of a file over the size limit, pointing at offset/limit; otherwise allow.
#[must_use]
pub fn pre_read(
    input: &HookInput,
    policy: &Policy,
    size_of: impl Fn(&Path) -> Option<u64>,
) -> Value {
    let ti = &input.tool_input;
    let Some(file) = ti.get("file_path").and_then(Value::as_str) else {
        return allow();
    };
    if ti.get("offset").is_some() || ti.get("limit").is_some() {
        return allow();
    }
    let mut path = PathBuf::from(file);
    if path.is_relative()
        && let Some(cwd) = &input.cwd
    {
        path = Path::new(cwd).join(path);
    }
    match size_of(&path) {
        Some(n) if n > policy.read_max_bytes => {
            tracing::info!(file, bytes = n, "pre-read: denied whole-file read");
            pre_tool(
                "deny",
                &format!(
                    "{file} is {n} bytes (limit {}); read a slice with offset and limit, or search it first",
                    policy.read_max_bytes
                ),
                None,
            )
        }
        _ => allow(),
    }
}

/// True when `segment` starts with `prefix` on a word boundary.
fn starts_with_words(segment: &str, prefix: &str) -> bool {
    segment
        .strip_prefix(prefix)
        .is_some_and(|rest| rest.is_empty() || rest.starts_with(' '))
}

/// Route heavy commands through `frob agent heavy` and cap unbounded output; otherwise allow.
#[must_use]
pub fn pre_bash(input: &HookInput, policy: &Policy) -> Value {
    let Some(command) = input.tool_input.get("command").and_then(Value::as_str) else {
        return allow();
    };
    let command = command.trim();
    if command.starts_with("frob ") {
        return allow();
    }
    let segments: Vec<&str> = command
        .split(['|', ';', '&', '>'])
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect();
    if let Some(hit) = segments
        .iter()
        .find(|s| policy.heavy.iter().any(|h| starts_with_words(s, h)))
    {
        tracing::info!(command = hit, "pre-bash: heavy command redirected");
        return pre_tool(
            "deny",
            &format!("`{hit}` is heavy; run it as `frob agent heavy -- {command}`"),
            None,
        );
    }
    let bounded = command.contains(['|', '>']);
    if !bounded && NOISY.iter().any(|n| starts_with_words(command, n)) {
        tracing::info!(
            command,
            cap = policy.bash_max_lines,
            "pre-bash: output bounded"
        );
        let mut updated = input.tool_input.clone();
        updated["command"] = json!(format!("{command} | head -n {}", policy.bash_max_lines));
        return pre_tool(
            "allow",
            &format!("output capped at {} lines", policy.bash_max_lines),
            Some(updated),
        );
    }
    allow()
}

/// A reply that adds `text` to the agent's context for `event` (`SessionStart`, `UserPromptSubmit`).
#[must_use]
pub fn context(event: &str, text: &str) -> Value {
    json!({ "hookSpecificOutput": { "hookEventName": event, "additionalContext": text } })
}

/// A reply that shows `text` to the user without changing the agent's behaviour.
#[must_use]
pub fn message(text: &str) -> Value {
    json!({ "systemMessage": text })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn policy() -> Policy {
        Policy {
            read_max_bytes: 100,
            bash_max_lines: 50,
            heavy: vec!["cargo test".to_owned()],
        }
    }

    fn input(tool_input: Value) -> HookInput {
        HookInput {
            tool_input,
            ..HookInput::default()
        }
    }

    fn decision(v: &Value) -> &str {
        v["hookSpecificOutput"]["permissionDecision"]
            .as_str()
            .unwrap_or("")
    }

    #[test]
    fn empty_payload_parses_to_default() {
        assert!(parse("  ").is_ok());
    }

    #[test]
    fn malformed_payload_is_an_error() {
        assert!(parse("{not json").is_err());
    }

    #[test]
    fn big_whole_file_read_is_denied() {
        let i = input(json!({"file_path": "/a/b.rs"}));
        assert_eq!(decision(&pre_read(&i, &policy(), |_| Some(101))), "deny");
    }

    #[test]
    fn deny_reason_names_offset_and_limit() {
        let i = input(json!({"file_path": "/a/b.rs"}));
        let v = pre_read(&i, &policy(), |_| Some(101));
        let reason = v["hookSpecificOutput"]["permissionDecisionReason"].as_str();
        assert!(reason.is_some_and(|r| r.contains("offset and limit")));
    }

    #[test]
    fn sliced_read_is_allowed() {
        let i = input(json!({"file_path": "/a/b.rs", "limit": 10}));
        assert_eq!(pre_read(&i, &policy(), |_| Some(10_000)), allow());
    }

    #[test]
    fn small_read_is_allowed() {
        let i = input(json!({"file_path": "/a/b.rs"}));
        assert_eq!(pre_read(&i, &policy(), |_| Some(5)), allow());
    }

    #[test]
    fn unreadable_size_fails_open() {
        let i = input(json!({"file_path": "/a/b.rs"}));
        assert_eq!(pre_read(&i, &policy(), |_| None), allow());
    }

    #[test]
    fn heavy_command_is_denied_with_route() {
        let v = pre_bash(
            &input(json!({"command": "cd x && cargo test -p a"})),
            &policy(),
        );
        assert_eq!(decision(&v), "deny");
    }

    #[test]
    fn heavy_reason_names_frob_agent_heavy() {
        let v = pre_bash(&input(json!({"command": "cargo test"})), &policy());
        let reason = v["hookSpecificOutput"]["permissionDecisionReason"].as_str();
        assert!(reason.is_some_and(|r| r.contains("frob agent heavy -- cargo test")));
    }

    #[test]
    fn unbounded_output_gets_a_head_cap() {
        let v = pre_bash(&input(json!({"command": "git log"})), &policy());
        assert_eq!(
            v["hookSpecificOutput"]["updatedInput"]["command"],
            "git log | head -n 50"
        );
    }

    #[test]
    fn piped_output_is_left_alone() {
        let v = pre_bash(&input(json!({"command": "cat f | wc -l"})), &policy());
        assert_eq!(v, allow());
    }

    // frob:tests crates/frob/src/agent/hook.rs::bash_guard
    #[test]
    fn bash_guard_names_each_pre_bash_guard() {
        let heavy = pre_bash(&input(json!({"command": "cargo test"})), &policy());
        let cap = pre_bash(&input(json!({"command": "git log"})), &policy());
        assert_eq!(bash_guard(&heavy), Some("pre-bash-heavy"));
        assert_eq!(bash_guard(&cap), Some("pre-bash-cap"));
        assert_eq!(bash_guard(&allow()), None);
    }

    #[test]
    fn missing_command_fails_open() {
        assert_eq!(pre_bash(&input(json!({})), &policy()), allow());
    }

    // frob:tests crates/frob/src/agent/hook.rs::context
    #[test]
    fn context_reply_carries_additional_context() {
        let v = context("SessionStart", "hi");
        assert_eq!(v["hookSpecificOutput"]["additionalContext"], "hi");
    }

    // frob:tests crates/frob/src/agent/hook.rs::message
    #[test]
    fn message_reply_sets_system_message() {
        assert_eq!(message("hi")["systemMessage"], "hi");
    }
}
