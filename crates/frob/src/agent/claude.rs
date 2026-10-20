//! The Claude Code emitter: files under `~/.claude`, hooks registered in `settings.json`.
//!
//! Registration semantics mirror `scripts/claude-hooks/frob_hook_settings.py`: every command carries a
//! `# frob-owned:<name>` marker, legacy unmarked entries naming the script count as frob's, and only
//! frob's entries are ever added, collapsed or removed.

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ

use gob_path::Shown;
use std::path::{Path, PathBuf};

use serde_json::{Map, Value, json};

use super::engine::{backup, read_opt, write_atomic};
use super::{AgentError, Emitter, Item, Kind, OWNER_PREFIX, Reg, RegState};

/// The Claude Code agent.
pub struct Claude;

const SETTINGS: &str = "settings.json";

impl Emitter for Claude {
    fn id(&self) -> &'static str {
        "claude"
    }

    fn default_home(&self) -> Option<PathBuf> {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".claude"))
    }

    fn target(&self, item: &Item) -> Option<PathBuf> {
        Some(match item.kind {
            Kind::Hook | Kind::Support => {
                PathBuf::from("hooks").join(Path::new(&item.src).file_name()?)
            }
            Kind::Agent => PathBuf::from(format!("agents/{}.md", item.name)),
            Kind::Skill => PathBuf::from(format!("skills/{}/SKILL.md", item.name)),
            Kind::Instruction => PathBuf::from(format!("{}.md", item.name)),
        })
    }

    fn registration_state(&self, home: &Path, regs: &[Reg]) -> Result<Vec<RegState>, AgentError> {
        let settings = load_settings(&home.join(SETTINGS))?;
        Ok(regs.iter().map(|r| hook_state(&settings, r)).collect())
    }

    fn register(&self, home: &Path, regs: &[Reg], dry_run: bool) -> Result<bool, AgentError> {
        if regs.is_empty() {
            return Ok(false);
        }
        let path = home.join(SETTINGS);
        let mut settings = load_settings(&path)?;
        for r in regs {
            install_hook(&mut settings, r, regs);
        }
        write_settings(&path, &settings, dry_run)
    }

    fn unregister(&self, home: &Path, regs: &[Reg], dry_run: bool) -> Result<usize, AgentError> {
        let path = home.join(SETTINGS);
        if read_opt(&path)?.is_none() {
            return Ok(0);
        }
        let mut settings = load_settings(&path)?;
        let removed = uninstall_hooks(&mut settings, regs);
        if removed > 0 {
            write_settings(&path, &settings, dry_run)?;
        }
        Ok(removed)
    }
}

/// The shell command registered for a hook: a runner by extension, the script, then the owner marker.
fn hook_command(r: &Reg) -> String {
    let script = crate::pathtext::text(&r.script);
    let runner = match crate::pathtext::ext_text(&r.script).as_deref() {
        Some("py") => "python3 ",
        Some("sh") => "bash ",
        _ => "",
    };
    format!("{runner}{script} {OWNER_PREFIX}{}", r.hook.name)
}

fn script_name(r: &Reg) -> String {
    r.script
        .file_name()
        .map(crate::pathtext::name_text)
        .unwrap_or_default()
}

fn command_of(entry: &Value) -> &str {
    entry.get("command").and_then(Value::as_str).unwrap_or("")
}

/// True for an entry frob owns: marked, or an unmarked legacy command naming one of frob's scripts.
fn is_frob(entry: &Value, regs: &[Reg]) -> bool {
    let c = command_of(entry);
    c.contains(OWNER_PREFIX) || regs.iter().any(|r| c.contains(&script_name(r)))
}

fn is_marked_for(entry: &Value, name: &str) -> bool {
    command_of(entry).contains(&format!("{OWNER_PREFIX}{name}"))
}

/// Parse `settings.json`; absent or empty is `{}`.
fn load_settings(path: &Path) -> Result<Value, AgentError> {
    let Some(bytes) = read_opt(path)? else {
        return Ok(json!({}));
    };
    if bytes.iter().all(u8::is_ascii_whitespace) {
        return Ok(json!({}));
    }
    let v: Value = serde_json::from_slice(&bytes).map_err(|source| AgentError::Json {
        path: path.to_path_buf(),
        source,
    })?;
    if v.is_object() {
        Ok(v)
    } else {
        Err(AgentError::Shape {
            path: path.to_path_buf(),
            detail: "top level is not an object".to_owned(),
        })
    }
}

/// Write settings (pretty, trailing newline) atomically with a backup; false when bytes are unchanged.
fn write_settings(path: &Path, settings: &Value, dry_run: bool) -> Result<bool, AgentError> {
    let mut text = serde_json::to_string_pretty(settings).map_err(|source| AgentError::Json {
        path: path.to_path_buf(),
        source,
    })?;
    text.push('\n');
    if read_opt(path)?.as_deref() == Some(text.as_bytes()) {
        return Ok(false);
    }
    if !dry_run {
        backup(path)?;
        write_atomic(path, text.as_bytes(), false)?;
    }
    tracing::info!(path = %Shown::of(path), dry_run, "settings updated");
    Ok(true)
}

fn groups_mut<'a>(settings: &'a mut Value, event: &str) -> Option<&'a mut Vec<Value>> {
    settings.get_mut("hooks")?.get_mut(event)?.as_array_mut()
}

/// True when `e` is hook `r`'s own entry: marked for it, or an unmarked legacy command naming its script.
fn is_hooks_own(e: &Value, r: &Reg) -> bool {
    is_marked_for(e, &r.hook.name)
        || (!command_of(e).contains(OWNER_PREFIX) && command_of(e).contains(&script_name(r)))
}

fn hook_state(settings: &Value, r: &Reg) -> RegState {
    let groups = settings
        .get("hooks")
        .and_then(|h| h.get(&r.hook.event))
        .and_then(Value::as_array);
    let mut own = Vec::new();
    for g in groups.into_iter().flatten() {
        let matcher = g.get("matcher").and_then(Value::as_str).unwrap_or("");
        for e in g
            .get("hooks")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            if is_hooks_own(e, r) {
                own.push((command_of(e), matcher));
            }
        }
    }
    match own.as_slice() {
        [] => RegState::Missing,
        [(c, m)] if *c == hook_command(r) && *m == r.hook.matcher => RegState::Registered,
        _ => RegState::Changed,
    }
}

/// Drop frob entries (all, or only hook `only`'s) from `groups`; a group emptied by this is removed.
fn strip_frob(groups: &mut Vec<Value>, regs: &[Reg], only: Option<&Reg>) -> usize {
    let mut removed = 0;
    groups.retain_mut(|g| {
        let Some(hooks) = g.get_mut("hooks").and_then(Value::as_array_mut) else {
            return true;
        };
        let before = hooks.len();
        hooks.retain(|e| !match only {
            Some(r) => is_hooks_own(e, r),
            None => is_frob(e, regs),
        });
        let dropped = before - hooks.len();
        removed += dropped;
        !(dropped > 0 && hooks.is_empty())
    });
    removed
}

/// Make hook `r` registered exactly once; a no-op when it already is.
fn install_hook(settings: &mut Value, r: &Reg, regs: &[Reg]) {
    if hook_state(settings, r) == RegState::Registered {
        return;
    }
    let root = settings.as_object_mut().expect("settings is an object");
    let hooks = root
        .entry("hooks")
        .or_insert_with(|| Value::Object(Map::new()));
    if !hooks.is_object() {
        *hooks = Value::Object(Map::new());
    }
    let groups = hooks
        .as_object_mut()
        .expect("hooks is an object")
        .entry(r.hook.event.clone())
        .or_insert_with(|| Value::Array(Vec::new()));
    if !groups.is_array() {
        *groups = Value::Array(Vec::new());
    }
    let groups = groups.as_array_mut().expect("event is an array");
    strip_frob(groups, regs, Some(r));
    groups.push(json!({
        "matcher": r.hook.matcher,
        "hooks": [{"type": "command", "command": hook_command(r)}],
    }));
}

/// Remove every frob entry; prune emptied events and an emptied `hooks` key. Returns entries removed.
fn uninstall_hooks(settings: &mut Value, regs: &[Reg]) -> usize {
    let mut removed = 0;
    let mut events: Vec<String> = regs.iter().map(|r| r.hook.event.clone()).collect();
    if let Some(h) = settings.get("hooks").and_then(Value::as_object) {
        events.extend(h.keys().cloned());
    }
    events.sort();
    events.dedup();
    for ev in events {
        if let Some(groups) = groups_mut(settings, &ev) {
            removed += strip_frob(groups, regs, None);
            if groups.is_empty() {
                settings
                    .get_mut("hooks")
                    .and_then(Value::as_object_mut)
                    .map(|h| h.remove(&ev));
            }
        }
    }
    if settings
        .get("hooks")
        .and_then(Value::as_object)
        .is_some_and(Map::is_empty)
    {
        settings.as_object_mut().map(|o| o.remove("hooks"));
    }
    removed
}
