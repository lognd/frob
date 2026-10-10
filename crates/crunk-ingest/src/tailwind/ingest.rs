//! The Tailwind ingest entry points: [`ingest_tailwind`] for a project, [`parse_tailwind_config`]
//! for one config text.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use crunk_tailwind::runtime::{
    Evaluation, Runtime, Sources, TailwindVersion as RuntimeVersion, Unresolved,
};
use indexmap::IndexMap;
use serde::{Deserialize, Serialize};

use super::collisions::{ThemeCollision, is_v3_default, is_v4_default, waiver_for};
use super::v3::read_v3;
use super::v4::{read_v4, split_namespace};

/// Where V4 CSS entries are looked for, relative to the project root.
const V4_CSS_CANDIDATES: [&str; 6] = [
    "styles/tailwind.css",
    "styles/main.css",
    "styles/index.css",
    "src/index.css",
    "src/main.css",
    "src/styles.css",
];

/// The Tailwind generation a config belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Version {
    /// A JS or TS config with `theme` and `theme.extend`.
    V3,
    /// A CSS-first config with `@theme`.
    V4,
}

/// Where the theme came from.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum Source {
    /// The project's own Tailwind, run through node.
    Node,
    /// The static readers. `reason` is why Tailwind was not run, when it was wanted.
    Static {
        /// The runtime's verdict (`unresolved-by-tailwind: ...`), or why it failed; `None` for
        /// static mode and for projects that never asked for the runtime.
        reason: Option<String>,
    },
}

/// How [`ingest_tailwind`] may resolve the theme.
#[derive(Debug, Clone, Copy)]
pub enum Engine<'a> {
    /// Never run Tailwind (`--static`, `[tailwind] engine = "static"`): no process is spawned.
    Static,
    /// Try the project's own Tailwind through this runtime first.
    Node(&'a Runtime),
}

/// The ingested theme and everything known about it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TailwindTheme {
    /// The generation of the config, when one was read.
    pub version: Option<Version>,
    /// Where the entries came from.
    pub source: Source,
    /// The `{name: value}` theme, namespace-stripped for v4.
    pub entries: IndexMap<String, String>,
    /// Keys left out because their value is not statically known (static readers only).
    pub unresolved: Vec<String>,
    /// Keys that redefine a Tailwind default, each with its waiver if there is one.
    pub collisions: Vec<ThemeCollision>,
    /// Config problems worth showing (a missing file, an unreadable one).
    pub diagnostics: Vec<String>,
}

impl TailwindTheme {
    fn empty() -> Self {
        Self {
            version: None,
            source: Source::Static { reason: None },
            entries: IndexMap::new(),
            unresolved: Vec::new(),
            collisions: Vec::new(),
            diagnostics: Vec::new(),
        }
    }
}

/// Sniff the generation of config `text`: `@import "tailwindcss"` or an `@theme` rule is v4,
/// everything else is v3.
pub fn detect_version(text: &str) -> Version {
    match read_v4(text) {
        Ok(read) if read.is_v4 => Version::V4,
        _ => Version::V3,
    }
}

/// The theme of config `text` through the static readers (no process is ever spawned).
///
/// `config_path` is the config's real path: it resolves relative `.json` imports and the v4
/// `@config` bridge (relative to its directory). `version` of `None` sniffs it.
pub fn parse_tailwind_config(
    text: &str,
    config_path: Option<&Path>,
    version: Option<Version>,
) -> TailwindTheme {
    let version = version.unwrap_or_else(|| detect_version(text));
    let mut out = TailwindTheme::empty();
    out.version = Some(version);
    match version {
        Version::V3 => static_v3(text, config_path, &mut out),
        Version::V4 => static_v4(text, config_path, &mut out),
    }
    out
}

fn static_v3(text: &str, config_path: Option<&Path>, out: &mut TailwindTheme) {
    let read = read_v3(text, config_path);
    out.entries = read.theme();
    out.unresolved.clone_from(&read.unresolved);
    for e in &read.entries {
        if is_v3_default(&e.section, &e.key) {
            out.collisions.push(ThemeCollision {
                section: e.section.clone(),
                key: e.key.clone(),
                line: e.line,
                waived: waiver_for(text, e.line),
            });
        }
    }
    if let Some(note) = read.note {
        tracing::debug!(%note, "tailwind config: static v3 read produced no theme");
    }
}

fn static_v4(text: &str, config_path: Option<&Path>, out: &mut TailwindTheme) {
    let read = match read_v4(text) {
        Ok(read) => read,
        Err(e) => {
            out.diagnostics.push(e.to_string());
            return;
        }
    };
    out.unresolved = read.opaque.iter().map(|n| split_namespace(n)).collect();
    for name in read.raw.keys() {
        if let Some((section, key)) = is_v4_default(name) {
            let line = text
                .lines()
                .position(|l| l.contains(name.as_str()))
                .map_or(1, |i| u32::try_from(i + 1).unwrap_or(u32::MAX));
            out.collisions.push(ThemeCollision {
                section: section.to_owned(),
                key,
                line,
                waived: waiver_for(text, line),
            });
        }
    }
    let mut merged = IndexMap::new();
    if let (Some(reference), Some(dir)) = (&read.config_ref, config_path.and_then(Path::parent)) {
        let bridged_path = dir.join(reference);
        match std::fs::read_to_string(&bridged_path) {
            Ok(body) => {
                let mut bridged = TailwindTheme::empty();
                static_v3(&body, Some(&bridged_path), &mut bridged);
                merged.extend(bridged.entries);
                out.unresolved.extend(bridged.unresolved);
                out.collisions.extend(bridged.collisions);
            }
            Err(e) => tracing::info!(
                path = %bridged_path.display(),
                error = %e,
                "tailwind config parse: @config target unreadable; bridge skipped"
            ),
        }
    } else if read.config_ref.is_some() {
        tracing::info!(
            "tailwind config parse: @config seen with no directory to resolve it against; bridge skipped"
        );
    }
    merged.extend(read.theme);
    out.entries = merged;
}

/// The first existing root-relative v4 CSS entry candidate holding `@import "tailwindcss"`.
fn detect_css_entry(root: &Path) -> Option<PathBuf> {
    V4_CSS_CANDIDATES.iter().map(|c| root.join(c)).find(|p| {
        std::fs::read_to_string(p)
            .ok()
            .and_then(|text| read_v4(&text).ok())
            .is_some_and(|r| r.is_v4)
    })
}

/// The Tailwind config file and the v4 CSS entry `spec` names, root-joined: `[tailwind] config`, and
/// `css_entry` or else a detected entry or a `.css` config.
fn locate_sources(spec: &DesignSpec) -> (Option<PathBuf>, Option<PathBuf>) {
    let cfg = &spec.tailwind;
    let root = &spec.root;
    let config_path = (!cfg.config.is_empty()).then(|| root.join(&cfg.config));
    let mut css_entry = (!cfg.css_entry.is_empty())
        .then(|| root.join(&cfg.css_entry))
        .or_else(|| detect_css_entry(root));
    if css_entry.is_none()
        && let Some(p) = &config_path
        && p.extension().is_some_and(|e| e.eq_ignore_ascii_case("css"))
    {
        css_entry = Some(p.clone());
    }
    (config_path, css_entry)
}

/// The project files the Tailwind runtime reads for `spec`: the v3 config and the v4 CSS entry,
/// each only when it exists (the same choice [`ingest_tailwind`] makes for the theme).
pub fn runtime_sources(spec: &DesignSpec) -> Sources {
    let (config_path, css_entry) = locate_sources(spec);
    Sources {
        config_path: config_path.filter(|p| p.is_file() && css_entry.as_ref() != Some(p)),
        css_entry: css_entry.filter(|p| p.is_file()),
    }
}

/// Ingest the Tailwind theme of the project `spec` describes.
///
/// With neither `[tailwind] config` nor `css_entry` set nothing is read and nothing runs. With
/// [`Engine::Node`] the project's own Tailwind is tried first; its verdict when it cannot answer
/// (`Unresolved`, a helper error) is recorded in [`Source::Static`] and the static readers answer
/// instead. A missing config file is a diagnostic, not an error.
pub fn ingest_tailwind(spec: &DesignSpec, engine: Engine<'_>) -> TailwindTheme {
    let cfg = &spec.tailwind;
    if cfg.config.is_empty() && cfg.css_entry.is_empty() {
        tracing::debug!("tailwind ingest: no [tailwind] config or css_entry; nothing to read");
        return TailwindTheme::empty();
    }
    let (config_path, _) = locate_sources(spec);
    let mut diagnostics = Vec::new();
    let mut text = String::new();
    if let Some(p) = &config_path {
        match std::fs::read_to_string(p) {
            Ok(body) => text = body,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => diagnostics.push(format!(
                "tailwind config {} does not exist; Tailwind theme judgments use the self-derived theme only",
                p.display()
            )),
            Err(e) => diagnostics.push(format!("tailwind config {} is unreadable: {e}", p.display())),
        }
    }

    let mut static_reason = None;
    if let Engine::Node(runtime) = engine {
        let sources = runtime_sources(spec);
        match runtime.resolve_theme(&sources) {
            Ok(Evaluation::Resolved(theme)) => {
                let version = match theme.version {
                    RuntimeVersion::V3 => Version::V3,
                    RuntimeVersion::V4 => Version::V4,
                };
                let mut entries = IndexMap::new();
                for (k, v) in theme.theme {
                    let key = if version == Version::V4 {
                        split_namespace(&k)
                    } else {
                        k
                    };
                    entries.insert(key, v);
                }
                let mut out = parse_tailwind_config(&text, config_path.as_deref(), Some(version));
                out.entries = entries;
                out.unresolved.clear();
                out.source = Source::Node;
                out.diagnostics.extend(diagnostics);
                tracing::info!(
                    entries = out.entries.len(),
                    "tailwind ingest: node-resolved theme"
                );
                return out;
            }
            Ok(Evaluation::Unresolved(why)) => {
                tracing::info!(reason = %why, "tailwind ingest: runtime unresolved; using the static readers");
                static_reason = Some(format!("{}: {why}", why.code()));
            }
            Err(e) => {
                tracing::warn!(error = %e, "tailwind ingest: runtime failed; using the static readers");
                static_reason = Some(format!("{}: {e}", Unresolved::StaticMode.code()));
            }
        }
    }

    let version = match spec.tailwind.version {
        crunk_spec::table::TailwindVersion::V3 => Some(Version::V3),
        crunk_spec::table::TailwindVersion::V4 => Some(Version::V4),
        crunk_spec::table::TailwindVersion::Auto => None,
    };
    let mut out = parse_tailwind_config(&text, config_path.as_deref(), version);
    out.source = Source::Static {
        reason: static_reason,
    };
    out.diagnostics.extend(diagnostics);
    tracing::info!(entries = out.entries.len(), "tailwind ingest: static theme");
    out
}
