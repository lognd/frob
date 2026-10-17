//! Typed results of the Tailwind theme ingest.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use std::collections::BTreeMap;
use std::path::PathBuf;

use crunk_tailwind::runtime::TailwindVersion;
use serde::{Deserialize, Serialize};

/// One theme value the project contributes (`theme.extend.spacing.18`, `--spacing-18`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ThemeEntry {
    /// The v3-style namespace: `colors`, `spacing`, `borderRadius`, `fontSize`, ... Empty for
    /// a runtime-only key or a v4 variable outside a known namespace.
    pub namespace: String,
    /// The flattened key inside the namespace (`primary-500`); the full `--name` when the
    /// namespace is empty.
    pub key: String,
    /// The key with its `[tokens.prefixes]` prefix removed when `[tailwind] namespace_keys`.
    pub step: String,
    /// The value as written.
    pub value: String,
    /// The value with `var()` references substituted, when it had any and all resolved.
    pub resolved: Option<String>,
    /// `var()` references that no `@theme` entry defines.
    pub unresolved_vars: Vec<String>,
    /// 1-based line of the key in its source; 0 for a runtime-only entry.
    pub line: u32,
    /// Whether the entry sits in `theme.extend` (v3) or `@theme` (v4), so it merges with the
    /// defaults rather than replacing a namespace.
    pub extend: bool,
    /// The value uses `<alpha-value>`: a `-rgb` channel companion makes opacity modifiers work.
    pub alpha_companion: bool,
}

/// A theme key that shadows a Tailwind default.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Collision {
    /// `TW004` (default color name) or `TW005` (default scale key).
    pub rule: String,
    /// The namespace of the colliding entry.
    pub namespace: String,
    /// The colliding key.
    pub key: String,
    /// 1-based line of the key.
    pub line: u32,
    /// A `crunk:waive` comment covers it.
    pub waived: bool,
    /// The waiver's reason, when given.
    pub reason: Option<String>,
}

/// Where the theme values came from.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThemeSource {
    /// The project's own Tailwind install resolved the theme (merged over the static read).
    Runtime,
    /// Only the static read of the source; `reason` says why Tailwind did not run.
    Static {
        /// Why the runtime was not used.
        reason: String,
    },
}

/// The ingested Tailwind theme of a project.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TailwindTheme {
    /// The shape of the source.
    pub version: TailwindVersion,
    /// The config or CSS entry that was read.
    pub path: PathBuf,
    /// Every theme entry, in source order, then runtime-only ones sorted by key.
    pub entries: Vec<ThemeEntry>,
    /// Keys shadowing a Tailwind default.
    pub collisions: Vec<Collision>,
    /// Problems and limits met while reading (non-literal namespaces, unreadable files).
    pub diagnostics: Vec<String>,
    /// Where the values came from.
    pub source: ThemeSource,
}

impl TailwindTheme {
    /// The flat `namespace.key -> value` map (resolved value when there is one); the shape the
    /// golden fixtures pin.
    pub fn theme_map(&self) -> BTreeMap<String, String> {
        self.entries
            .iter()
            .map(|e| {
                let name = if e.namespace.is_empty() {
                    e.key.clone()
                } else {
                    format!("{}.{}", e.namespace, e.key)
                };
                (name, e.resolved.clone().unwrap_or_else(|| e.value.clone()))
            })
            .collect()
    }

    /// Collisions no `crunk:waive` covers.
    pub fn unwaived_collisions(&self) -> impl Iterator<Item = &Collision> {
        self.collisions.iter().filter(|c| !c.waived)
    }
}
