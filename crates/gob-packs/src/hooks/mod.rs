//! The typed hook registry: the whole plugin ABI (plugins.md section 5).
//!
//! The hook list is closed ([`Hook`]); a pack declares each implementation with the hook
//! name, the version it implements, its signature and an explicit priority. Implementations
//! are validated when registered: an unknown hook, an unsupported version, a signature that
//! differs from the specification or a missing capability is PACK005 stating the exact
//! reason. Ordering is priority ascending with a tie-break by pack name, so the order is the
//! same on every run. There is no wrapper hook in version 1.

// frob:ticket 01M3ZX7JN8RWAKDVYK0BNG3E2K

use crate::error::PackError;

/// One of the hooks of the version-1 ABI.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Hook {
    /// `atoms`: once per run, tier 1.
    Atoms,
    /// `detect(lang, unit) -> uses`: once per file.
    Detect,
    /// `templates`: once per run, tier 1.
    Templates,
    /// `check_file(file) -> findings`: once per file.
    CheckFile,
    /// `check_repo(graph) -> findings`: once per run, root packs only.
    CheckRepo,
    /// `fix(finding) -> edits`: on request.
    Fix,
    /// `adapter.fold(source) -> term`: once per file, tier 4.
    AdapterFold,
    /// `config_tables`: once at load.
    ConfigTables,
}

/// Every hook, in specification order.
pub const ALL_HOOKS: [Hook; 8] = [
    Hook::Atoms,
    Hook::Detect,
    Hook::Templates,
    Hook::CheckFile,
    Hook::CheckRepo,
    Hook::Fix,
    Hook::AdapterFold,
    Hook::ConfigTables,
];

impl Hook {
    /// The hook as a pack names it, for example `adapter.fold`.
    pub fn name(self) -> &'static str {
        match self {
            Self::Atoms => "atoms",
            Self::Detect => "detect",
            Self::Templates => "templates",
            Self::CheckFile => "check_file",
            Self::CheckRepo => "check_repo",
            Self::Fix => "fix",
            Self::AdapterFold => "adapter.fold",
            Self::ConfigTables => "config_tables",
        }
    }

    /// Resolves a hook name, or `None` when it is not part of the ABI.
    pub fn from_name(name: &str) -> Option<Self> {
        ALL_HOOKS.into_iter().find(|h| h.name() == name)
    }

    /// The signature the specification fixes for this hook (whitespace-insensitive).
    pub fn signature(self) -> &'static str {
        match self {
            Self::Atoms => "atoms",
            Self::Detect => "detect(lang,unit)->uses",
            Self::Templates => "templates",
            Self::CheckFile => "check_file(file)->findings",
            Self::CheckRepo => "check_repo(graph)->findings",
            Self::Fix => "fix(finding)->edits",
            Self::AdapterFold => "adapter.fold(source)->term",
            Self::ConfigTables => "config_tables",
        }
    }

    /// The hook versions this build implements; additive growth appends here.
    pub fn versions(self) -> &'static [u32] {
        &[1]
    }

    /// The capability a pack must declare to implement this hook, if any.
    pub fn required_capability(self) -> Option<&'static str> {
        match self {
            Self::CheckRepo => Some("graph"),
            Self::AdapterFold => Some("adapter"),
            _ => None,
        }
    }
}

/// One hook implementation as a pack declares it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Implementation {
    /// The hook name as written by the pack.
    pub hook: String,
    /// The hook version implemented.
    pub version: u32,
    /// The signature the pack claims, for example `check_file(file) -> findings`.
    pub signature: String,
    /// Explicit priority; lower runs first.
    pub priority: i32,
}

/// What a pack declares for the registry: its hooks, capabilities and config tables.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PackHooks {
    /// The manifest file, named in errors.
    pub file: String,
    /// The pack's name; the priority tie-break.
    pub name: String,
    /// Capabilities the pack declares.
    pub capabilities: Vec<String>,
    /// The hook implementations.
    pub implementations: Vec<Implementation>,
    /// Config tables the pack materializes (the `config_tables` hook's output).
    pub config_tables: Vec<String>,
}

/// A validated implementation bound to its pack.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    /// The implementing pack's name.
    pub pack: String,
    /// The hook version implemented.
    pub version: u32,
    /// Explicit priority; lower runs first.
    pub priority: i32,
}

/// The validated set of hook implementations across packs.
#[derive(Debug, Default)]
pub struct Registry {
    entries: Vec<(Hook, Entry)>,
    tables: Vec<(String, String)>,
}

fn strip_ws(s: &str) -> String {
    s.chars().filter(|c| !c.is_whitespace()).collect()
}

fn validate(p: &PackHooks, imp: &Implementation) -> Result<Hook, PackError> {
    let key = format!("hooks.{}", imp.hook);
    let Some(hook) = Hook::from_name(&imp.hook) else {
        let known: Vec<&str> = ALL_HOOKS.iter().map(|h| h.name()).collect();
        return Err(PackError::malformed(
            &p.file,
            &key,
            format!("unknown hook `{}` (known: {})", imp.hook, known.join(", ")),
        ));
    };
    if !hook.versions().contains(&imp.version) {
        return Err(PackError::malformed(
            &p.file,
            &key,
            format!(
                "hook `{}` has no version {} (implemented: {:?})",
                imp.hook,
                imp.version,
                hook.versions()
            ),
        ));
    }
    if strip_ws(&imp.signature) != hook.signature() {
        return Err(PackError::malformed(
            &p.file,
            &key,
            format!(
                "wrong signature for hook `{}`: expected `{}`, found `{}`",
                imp.hook,
                hook.signature(),
                imp.signature
            ),
        ));
    }
    if let Some(cap) = hook.required_capability()
        && !p.capabilities.iter().any(|c| c == cap)
    {
        return Err(PackError::malformed(
            &p.file,
            &key,
            format!(
                "hook `{}` requires capability `{cap}`, which the pack does not declare",
                imp.hook
            ),
        ));
    }
    Ok(hook)
}

impl Registry {
    /// An empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Validates every implementation of `pack` and adds them; nothing is added on error.
    ///
    /// # Errors
    /// PACK005 naming the first implementation with an unknown hook, unimplemented version,
    /// wrong signature or missing capability.
    pub fn register(&mut self, pack: &PackHooks) -> Result<(), PackError> {
        let mut staged = Vec::with_capacity(pack.implementations.len());
        for imp in &pack.implementations {
            let hook = validate(pack, imp).inspect_err(
                |e| tracing::warn!(pack = %pack.name, error = %e, "hook implementation refused"),
            )?;
            staged.push((
                hook,
                Entry {
                    pack: pack.name.clone(),
                    version: imp.version,
                    priority: imp.priority,
                },
            ));
        }
        tracing::debug!(pack = %pack.name, hooks = staged.len(), "hooks registered");
        self.entries.extend(staged);
        self.tables.extend(
            pack.config_tables
                .iter()
                .map(|t| (t.clone(), pack.name.clone())),
        );
        Ok(())
    }

    /// The implementations of `hook` in call order: priority ascending, then pack name.
    pub fn ordered(&self, hook: Hook) -> Vec<&Entry> {
        let mut v: Vec<&Entry> = self
            .entries
            .iter()
            .filter(|(h, _)| *h == hook)
            .map(|(_, e)| e)
            .collect();
        v.sort_by(|a, b| (a.priority, &a.pack).cmp(&(b.priority, &b.pack)));
        v
    }

    /// Every materialized config table as `(table, pack)`, sorted for determinism.
    pub fn config_tables(&self) -> Vec<(&str, &str)> {
        let mut v: Vec<(&str, &str)> = self
            .tables
            .iter()
            .map(|(t, p)| (t.as_str(), p.as_str()))
            .collect();
        v.sort_unstable();
        v
    }
}
