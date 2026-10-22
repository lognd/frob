//! Agent-neutral syncing of tracked instructions, hooks, agent definitions and skills.
//!
//! The repository holds one canonical, agent-neutral source set declared in `frob.toml` `[agent]`
//! ([`Manifest`]). Each coding agent is an [`Emitter`]: it says where an item lands, how to render it,
//! and how to register or unregister hooks. The shared [`engine`] owns everything else: banners, atomic
//! writes, backups, idempotence, drift detection and reversibility (only frob-owned files and entries
//! are touched). Adding an agent means adding one emitter module and listing it in [`emitters`].

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ

pub mod claude;
pub mod engine;
pub mod project;

use std::path::{Component, Path, PathBuf};

use schemars::JsonSchema;
use serde::Serialize;

/// Prefix of the shell comment that marks a registered hook command as frob-owned; the hook name follows.
pub const OWNER_PREFIX: &str = "# frob-owned:";

/// Why an agent operation could not complete.
#[derive(Debug, thiserror::Error)]
pub enum AgentError {
    /// A file or directory operation failed.
    #[error("{path}: {source}")]
    Io {
        /// The path being read or written.
        path: PathBuf,
        /// The underlying error.
        source: std::io::Error,
    },
    /// A JSON file is not valid JSON.
    #[error("{path}: not valid JSON: {source}")]
    Json {
        /// The file that failed to parse.
        path: PathBuf,
        /// The parse error.
        source: serde_json::Error,
    },
    /// A registration file parsed but has an unexpected shape.
    #[error("{path}: unexpected shape: {detail}")]
    Shape {
        /// The file.
        path: PathBuf,
        /// What was wrong.
        detail: String,
    },
    /// A `[agent]` manifest entry is malformed or unsafe.
    #[error("[agent] manifest: {0}")]
    Manifest(String),
    /// `--agent` named an emitter that does not exist.
    #[error("unknown agent `{0}`")]
    UnknownAgent(String),
}

/// What a canonical item is, which decides where each agent puts it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    /// Standing instructions for the agent.
    Instruction,
    /// A script an agent runs on an event; registered through the emitter.
    Hook,
    /// A sub-agent definition.
    Agent,
    /// A skill.
    Skill,
    /// A file other items need (a library a hook imports).
    Support,
}

impl Kind {
    fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "instruction" => Self::Instruction,
            "hook" => Self::Hook,
            "agent" => Self::Agent,
            "skill" => Self::Skill,
            "support" => Self::Support,
            _ => return None,
        })
    }
}

/// One canonical, agent-neutral source file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Item {
    /// What it is.
    pub kind: Kind,
    /// Its name, unique per kind (also the ownership id of a hook).
    pub name: String,
    /// Source path relative to the repository root.
    pub src: String,
}

/// A request to register a hook item for an event.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HookReg {
    /// Name of a `hook` item.
    pub name: String,
    /// Event name, e.g. `PreToolUse`.
    pub event: String,
    /// Tool matcher, e.g. `Bash|Edit`.
    pub matcher: String,
}

/// A hook registration resolved against one agent's home directory.
#[derive(Debug, Clone)]
pub struct Reg {
    /// The request.
    pub hook: HookReg,
    /// Where the hook script is installed for this agent.
    pub script: PathBuf,
}

/// How one hook registration stands.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum RegState {
    /// Registered exactly once as expected.
    Registered,
    /// No frob entry for this hook.
    Missing,
    /// Present but duplicated, legacy-unmarked, or different from what sync would write.
    Changed,
}

/// The parsed `[agent]` manifest.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Manifest {
    /// Canonical source files.
    pub items: Vec<Item>,
    /// Hook registrations.
    pub hooks: Vec<HookReg>,
}

/// Reject absolute paths and `..` so a manifest cannot reach outside the repository.
fn safe_rel(p: &str) -> Result<(), AgentError> {
    let ok = !p.is_empty()
        && Path::new(p)
            .components()
            .all(|c| matches!(c, Component::Normal(_)));
    if ok {
        Ok(())
    } else {
        Err(AgentError::Manifest(format!(
            "path `{p}` must be relative with no `..`"
        )))
    }
}

impl Manifest {
    /// Parse `items` (`"KIND:NAME = SRC"`) and `hooks` (`"NAME:EVENT:MATCHER"`) as written in `frob.toml`.
    ///
    /// # Errors
    /// [`AgentError::Manifest`] for a malformed entry, unsafe path, duplicate item, or a hook naming no `hook` item.
    pub fn parse(items: &[String], hooks: &[String]) -> Result<Self, AgentError> {
        let mut out = Self::default();
        for entry in items {
            let bad = || AgentError::Manifest(format!("item `{entry}` is not `KIND:NAME = SRC`"));
            let (head, src) = entry.split_once('=').ok_or_else(bad)?;
            let (kind, name) = head.trim().split_once(':').ok_or_else(bad)?;
            let kind = Kind::parse(kind.trim()).ok_or_else(|| {
                AgentError::Manifest(format!(
                    "item `{entry}`: kind must be instruction, hook, agent, skill or support"
                ))
            })?;
            let (name, src) = (name.trim(), src.trim());
            safe_rel(src)?;
            if name.is_empty() || name.contains(['/', ' ', ':']) {
                return Err(AgentError::Manifest(format!(
                    "item `{entry}`: name must be a plain word"
                )));
            }
            if out.items.iter().any(|i| i.kind == kind && i.name == name) {
                return Err(AgentError::Manifest(format!("duplicate item `{entry}`")));
            }
            out.items.push(Item {
                kind,
                name: name.to_owned(),
                src: src.to_owned(),
            });
        }
        for h in hooks {
            let mut parts = h.splitn(3, ':');
            let (Some(name), Some(event), Some(matcher)) =
                (parts.next(), parts.next(), parts.next())
            else {
                return Err(AgentError::Manifest(format!(
                    "hook `{h}` is not `NAME:EVENT:MATCHER`"
                )));
            };
            if event.is_empty()
                || !out
                    .items
                    .iter()
                    .any(|i| i.kind == Kind::Hook && i.name == name)
            {
                return Err(AgentError::Manifest(format!(
                    "hook `{h}` needs an event and a `hook:{name}` item"
                )));
            }
            out.hooks.push(HookReg {
                name: name.to_owned(),
                event: event.to_owned(),
                matcher: matcher.to_owned(),
            });
        }
        Ok(out)
    }

    // frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
    // frob:tests crates/frob/tests/it/agent.rs::sync_into_empty_home_is_idempotent_and_byte_identical
    /// True when nothing is declared (the feature is off for this repository).
    pub fn is_empty(&self) -> bool {
        self.items.is_empty() && self.hooks.is_empty()
    }
}

/// One coding agent: where items go, how they render, and how hooks are registered.
///
/// Everything else (banners, atomic writes, backups, drift, reversibility) is the [`engine`]'s job.
pub trait Emitter {
    /// Selector name for `--agent`.
    fn id(&self) -> &'static str;

    // frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
    // frob:tests crates/frob/tests/it/agent.rs::sync_into_empty_home_is_idempotent_and_byte_identical
    /// The agent's usual home directory, or `None` when it cannot be determined.
    fn default_home(&self) -> Option<PathBuf>;

    /// Where `item` lands relative to the home directory, or `None` when this agent has no place for it.
    fn target(&self, item: &Item) -> Option<PathBuf>;

    /// The bytes written for `item` at `dest`; the default is the source behind the do-not-edit banner.
    fn render(&self, item: &Item, dest: &Path, src: &[u8]) -> Vec<u8> {
        engine::with_banner(&item.src, dest, src)
    }

    /// Where each registration stands, in `regs` order; the default has nothing to register.
    ///
    /// # Errors
    /// [`AgentError`] when the registration file cannot be read.
    fn registration_state(&self, _home: &Path, regs: &[Reg]) -> Result<Vec<RegState>, AgentError> {
        Ok(vec![RegState::Registered; regs.len()])
    }

    /// Make `regs` registered exactly once, touching only frob-owned entries; true when anything changed.
    ///
    /// # Errors
    /// [`AgentError`] when the registration file cannot be read or written.
    fn register(&self, _home: &Path, _regs: &[Reg], _dry_run: bool) -> Result<bool, AgentError> {
        Ok(false)
    }

    /// Remove every frob-owned registration (including those of `regs`); the number removed.
    ///
    /// # Errors
    /// [`AgentError`] when the registration file cannot be read or written.
    fn unregister(&self, _home: &Path, _regs: &[Reg], _dry_run: bool) -> Result<usize, AgentError> {
        Ok(0)
    }
}

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
// frob:tests crates/frob/tests/it/agent.rs::sync_into_empty_home_is_idempotent_and_byte_identical
// frob:tests crates/frob/tests/it/agent.rs::unknown_agent_is_a_usage_error
/// Every implemented emitter; a new agent is one line here plus its module.
pub fn emitters() -> Vec<Box<dyn Emitter>> {
    vec![Box::new(claude::Claude)]
}

/// The emitters named by `--agent` (`all` or one id).
///
/// # Errors
/// [`AgentError::UnknownAgent`] for an id no emitter has.
pub fn select(agent: &str) -> Result<Vec<Box<dyn Emitter>>, AgentError> {
    let all = emitters();
    if agent == "all" {
        return Ok(all);
    }
    let picked: Vec<_> = all.into_iter().filter(|e| e.id() == agent).collect();
    if picked.is_empty() {
        Err(AgentError::UnknownAgent(agent.to_owned()))
    } else {
        Ok(picked)
    }
}
