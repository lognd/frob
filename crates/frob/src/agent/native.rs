//! Registration of frob's own `frob agent hook <event>` handlers in an agent's `settings.json`.
//!
//! Pure planning over the parsed settings: each native hook is either added, already present, updated
//! (our marked entry drifted) or a conflict (an unmarked entry already calls the same handler, which is
//! reported and never overwritten). Only entries carrying the frob owner marker are ever replaced.

// frob:ticket 01M4P2N1GFSA69RHJR4D41NVHV

use schemars::JsonSchema;
use serde::Serialize;
use serde_json::{Value, json};

use super::OWNER_PREFIX;

/// One native handler: the settings event, tool matcher and the `frob agent hook` argument.
#[derive(Debug, Clone, Copy)]
pub struct Native {
    /// The agent settings event name.
    pub event: &'static str,
    /// The tool matcher (empty for non-tool events).
    pub matcher: &'static str,
    /// The `frob agent hook` event argument.
    pub arg: &'static str,
}

/// Every handler `frob agent hook` answers.
pub const NATIVE: [Native; 6] = [
    Native {
        event: "PreToolUse",
        matcher: "Bash",
        arg: "pre-bash",
    },
    Native {
        event: "PreToolUse",
        matcher: "Read",
        arg: "pre-read",
    },
    Native {
        event: "SessionStart",
        matcher: "",
        arg: "session-start",
    },
    Native {
        event: "PreCompact",
        matcher: "",
        arg: "pre-compact",
    },
    Native {
        event: "UserPromptSubmit",
        matcher: "",
        arg: "user-prompt",
    },
    Native {
        event: "Stop",
        matcher: "",
        arg: "stop",
    },
];

/// What installing one native hook would do.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    /// No frob entry yet; one will be appended.
    Add,
    /// Already registered exactly as it would be written.
    Present,
    /// A frob-marked entry differs and will be replaced.
    Update,
    /// An unowned entry already calls this handler; left alone.
    Conflict,
}

/// One row of the install plan.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Row {
    /// The settings event.
    pub event: String,
    /// The tool matcher.
    pub matcher: String,
    /// The command that is (or would be) registered.
    pub command: String,
    /// What install does with it.
    pub action: Action,
}

/// The marker naming native hook `n` as frob-owned.
fn marker(n: &Native) -> String {
    format!("{OWNER_PREFIX}native-{}", n.arg)
}

/// The shell command registered for `n`: the bare-JSON text form, then the owner marker.
#[must_use]
pub fn command(n: &Native) -> String {
    format!("frob agent hook {} --text {}", n.arg, marker(n))
}

fn command_of(e: &Value) -> &str {
    e.get("command").and_then(Value::as_str).unwrap_or("")
}

/// Every command entry of `event`, as `(matcher, entry)`.
fn entries<'a>(settings: &'a Value, event: &str) -> Vec<(&'a str, &'a Value)> {
    let groups = settings
        .get("hooks")
        .and_then(|h| h.get(event))
        .and_then(Value::as_array);
    let mut out = Vec::new();
    for g in groups.into_iter().flatten() {
        let m = g.get("matcher").and_then(Value::as_str).unwrap_or("");
        for e in g
            .get("hooks")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            out.push((m, e));
        }
    }
    out
}

/// True when the unowned command `c` already invokes handler `n`.
fn calls(c: &str, n: &Native) -> bool {
    !c.contains(OWNER_PREFIX) && c.contains(&format!("agent hook {}", n.arg))
}

/// Decide, for every native hook, what install would do to `settings`.
#[must_use]
pub fn plan(settings: &Value) -> Vec<Row> {
    NATIVE
        .iter()
        .map(|n| {
            let want = command(n);
            let es = entries(settings, n.event);
            let own: Vec<_> = es
                .iter()
                .filter(|(_, e)| command_of(e).ends_with(&marker(n)))
                .collect();
            let action = match own.as_slice() {
                [] if es.iter().any(|(_, e)| calls(command_of(e), n)) => Action::Conflict,
                [] => Action::Add,
                [(m, e)] if command_of(e) == want && *m == n.matcher => Action::Present,
                _ => Action::Update,
            };
            Row {
                event: n.event.to_owned(),
                matcher: n.matcher.to_owned(),
                command: want,
                action,
            }
        })
        .collect()
}

/// Remove `n`'s marked entries from `groups`, dropping groups this empties.
fn strip(groups: &mut Vec<Value>, n: &Native) {
    let mark = marker(n);
    groups.retain_mut(|g| {
        let Some(hooks) = g.get_mut("hooks").and_then(Value::as_array_mut) else {
            return true;
        };
        let before = hooks.len();
        hooks.retain(|e| !command_of(e).ends_with(&mark));
        !(before > hooks.len() && hooks.is_empty())
    });
}

/// Apply `rows` to `settings`: add or replace only frob-marked entries, skipping present and conflicts.
///
/// # Panics
/// Never for a settings root that is a JSON object, which `plan` and the loader guarantee.
pub fn apply(settings: &mut Value, rows: &[Row]) {
    for (n, row) in NATIVE.iter().zip(rows) {
        if matches!(row.action, Action::Present | Action::Conflict) {
            continue;
        }
        let root = settings.as_object_mut().expect("settings is an object");
        let hooks = root.entry("hooks").or_insert_with(|| json!({}));
        if !hooks.is_object() {
            *hooks = json!({});
        }
        let groups = hooks
            .as_object_mut()
            .expect("hooks is an object")
            .entry(n.event)
            .or_insert_with(|| json!([]));
        if !groups.is_array() {
            *groups = json!([]);
        }
        let groups = groups.as_array_mut().expect("event is an array");
        strip(groups, n);
        groups.push(json!({
            "matcher": n.matcher,
            "hooks": [{"type": "command", "command": command(n)}],
        }));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn actions(s: &Value) -> Vec<Action> {
        plan(s).iter().map(|r| r.action).collect()
    }

    #[test]
    fn empty_settings_plan_adds_every_handler() {
        assert!(actions(&json!({})).iter().all(|a| *a == Action::Add));
    }

    #[test]
    fn applying_the_plan_twice_is_a_fixed_point() {
        let mut s = json!({"model": "x"});
        let rows = plan(&s);
        apply(&mut s, &rows);
        assert!(actions(&s).iter().all(|a| *a == Action::Present));
    }

    #[test]
    fn apply_preserves_unrelated_keys_and_user_entries() {
        let user = json!({"matcher": "Bash", "hooks": [{"type": "command", "command": "mine.sh"}]});
        let mut s = json!({"model": "x", "hooks": {"PreToolUse": [user.clone()]}});
        let rows = plan(&s);
        apply(&mut s, &rows);
        assert_eq!(s["model"], "x");
        assert_eq!(s["hooks"]["PreToolUse"][0], user);
    }

    #[test]
    fn unowned_entry_calling_the_handler_is_a_conflict_and_untouched() {
        let theirs = json!({"matcher": "Bash", "hooks": [{"type": "command", "command": "frob agent hook stop"}]});
        let mut s = json!({"hooks": {"Stop": [theirs.clone()]}});
        let rows = plan(&s);
        assert_eq!(rows[5].action, Action::Conflict);
        apply(&mut s, &rows);
        assert_eq!(s["hooks"]["Stop"], json!([theirs]));
    }

    #[test]
    fn drifted_marked_entry_is_updated_in_place_of_duplicating() {
        let old = json!({"matcher": "", "hooks": [{"type": "command", "command": "old # frob-owned:native-stop"}]});
        let mut s = json!({"hooks": {"Stop": [old]}});
        let rows = plan(&s);
        assert_eq!(rows[5].action, Action::Update);
        apply(&mut s, &rows);
        assert_eq!(s["hooks"]["Stop"].as_array().map(Vec::len), Some(1));
    }
}
