//! Tailwind theme ingest (the Python `ingest.tailwind`): the project's `theme` /
//! `theme.extend` (v3) or `@theme` blocks (v4), namespaced, with default collisions.
//!
//! The source is always read statically ([`v3`], [`v4`]); unless static mode is requested the
//! project's own Tailwind install is then asked through [`crunk_tailwind`] and its resolved
//! values are merged over the static read. A project with no `[tailwind]` section runs nothing:
//! no runtime is constructed and no process is spawned.
//!
//! # Known divergences from the Python crunk
//!
//! - The static JS reader understands object literals only; computed keys, function-valued
//!   namespaces and `require()` are left to the runtime and noted in
//!   [`TailwindTheme::diagnostics`]. Python executed the config through node every time.
//! - Collision rules are reported as data ([`Collision`]); the rules crate decides severity.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

mod model;
mod text;
mod v3;
mod v4;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use crunk_spec::table::TailwindVersion as SpecVersion;
use crunk_tailwind::defaults::{
    V3_BORDER_RADIUS_KEYS, V3_COLOR_NAMES, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS, V3_Z_INDEX_KEYS,
    V4_BORDER_RADIUS_KEYS, V4_COLOR_NAMES, V4_FONT_SIZE_KEYS, V4_Z_INDEX_KEYS, has_key,
    is_v4_spacing_key,
};
use crunk_tailwind::runtime::{Evaluation, Options, Runtime, Sources, TailwindVersion};
use gob_cache::Cache;

pub use model::{Collision, TailwindTheme, ThemeEntry, ThemeSource};

/// Which Tailwind shape `src` (at `path`) is: the spec's pin wins, else v4 signals, else v3.
pub fn detect_version(spec: &DesignSpec, path: &Path, src: &str) -> TailwindVersion {
    match spec.tailwind.version {
        SpecVersion::V3 => TailwindVersion::V3,
        SpecVersion::V4 => TailwindVersion::V4,
        SpecVersion::Auto => {
            let css = path.extension().is_some_and(|e| e == "css");
            if (css && v4::looks_like_v4(src)) || v4::looks_like_v4(src) {
                TailwindVersion::V4
            } else {
                TailwindVersion::V3
            }
        }
    }
}

/// Ingest the Tailwind theme of `spec`.
///
/// Returns `None` when `[tailwind]` names neither a config nor a CSS entry: nothing runs and
/// no process is spawned. A configured but missing or unreadable file is a diagnostic on the
/// returned theme, never an error. `options.static_mode` keeps the runtime from running.
pub fn ingest_tailwind(spec: &DesignSpec, options: Options, cache: Cache) -> Option<TailwindTheme> {
    let config = spec.tailwind_config_path();
    let entry =
        (!spec.tailwind.css_entry.is_empty()).then(|| spec.root.join(&spec.tailwind.css_entry));
    let Some(path) = config.clone().or_else(|| entry.clone()) else {
        tracing::debug!("tailwind: no [tailwind] section; nothing to ingest");
        return None;
    };
    let src = match std::fs::read_to_string(&path) {
        Ok(src) => src,
        Err(err) => {
            tracing::warn!(path = %path.display(), %err, "tailwind: config unreadable");
            return Some(TailwindTheme {
                version: match spec.tailwind.version {
                    SpecVersion::V3 => TailwindVersion::V3,
                    _ => TailwindVersion::V4,
                },
                path: path.clone(),
                entries: Vec::new(),
                collisions: Vec::new(),
                diagnostics: vec![format!("cannot read {}: {err}", path.display())],
                source: ThemeSource::Static {
                    reason: "config unreadable".to_owned(),
                },
            });
        }
    };
    let version = detect_version(spec, &path, &src);
    tracing::info!(path = %path.display(), ?version, "tailwind: ingesting theme");
    let mut diagnostics = Vec::new();
    let mut entries = match version {
        TailwindVersion::V3 => read_v3(spec, &src, &mut diagnostics),
        TailwindVersion::V4 => read_v4(spec, &src),
    };
    let waivers = text::waivers(&src);
    let collisions = collisions(version, &entries, &waivers);

    let sources = match version {
        TailwindVersion::V3 => Sources {
            config_path: Some(path.clone()),
            css_entry: entry,
        },
        TailwindVersion::V4 => Sources {
            config_path: config.filter(|p| p.extension().is_some_and(|e| e != "css")),
            css_entry: Some(path.clone()),
        },
    };
    let source = merge_runtime(
        spec,
        options,
        cache,
        &sources,
        &mut entries,
        &mut diagnostics,
    );
    Some(TailwindTheme {
        version,
        path,
        entries,
        collisions,
        diagnostics,
        source,
    })
}

fn merge_runtime(
    spec: &DesignSpec,
    options: Options,
    cache: Cache,
    sources: &Sources,
    entries: &mut Vec<ThemeEntry>,
    diagnostics: &mut Vec<String>,
) -> ThemeSource {
    let runtime = Runtime::new(&spec.root, options, cache);
    match runtime.resolve_theme(sources) {
        Ok(Evaluation::Resolved(theme)) => {
            tracing::info!(keys = theme.theme.len(), "tailwind: runtime theme merged");
            for (k, v) in theme.theme {
                let hit = entries.iter_mut().find(|e| {
                    if theme.version == TailwindVersion::V4 {
                        e.namespace.is_empty() && e.key == k
                            || v4_name(e).as_deref() == Some(k.as_str())
                    } else {
                        e.key.rsplit('-').next() == Some(k.as_str()) || e.key == k
                    }
                });
                match hit {
                    Some(e) => e.resolved = Some(v),
                    None => entries.push(ThemeEntry {
                        namespace: String::new(),
                        step: k.clone(),
                        key: k,
                        value: v,
                        resolved: None,
                        unresolved_vars: Vec::new(),
                        line: 0,
                        extend: true,
                        alpha_companion: false,
                    }),
                }
            }
            ThemeSource::Runtime
        }
        Ok(Evaluation::Unresolved(u)) => {
            tracing::info!(reason = %u, "tailwind: runtime not used");
            ThemeSource::Static {
                reason: u.to_string(),
            }
        }
        Err(err) => {
            tracing::warn!(%err, "tailwind: runtime failed; keeping the static read");
            diagnostics.push(format!("tailwind runtime failed: {err}"));
            ThemeSource::Static {
                reason: err.to_string(),
            }
        }
    }
}

/// The `--name` a namespaced v4 entry came from.
fn v4_name(e: &ThemeEntry) -> Option<String> {
    let prefix = match e.namespace.as_str() {
        "colors" => "--color-",
        "spacing" => "--spacing-",
        "borderRadius" => "--radius-",
        "screens" => "--breakpoint-",
        "fontFamily" => "--font-",
        "fontSize" => "--text-",
        "zIndex" => "--z-",
        _ => return None,
    };
    Some(format!("{prefix}{}", e.key))
}

/// The `[tokens.prefixes]` prefix that names `namespace`'s tokens.
fn prefix_of<'a>(spec: &'a DesignSpec, namespace: &str) -> &'a str {
    let p = &spec.tokens;
    match namespace {
        "colors" => &p.color,
        "spacing" => &p.space,
        "fontSize" => &p.font_size,
        "borderRadius" => &p.radius,
        "zIndex" => &p.layer,
        "fontFamily" => &p.font_family,
        _ => "",
    }
}

fn step_of(spec: &DesignSpec, namespace: &str, key: &str) -> String {
    let prefix = prefix_of(spec, namespace);
    if spec.tailwind.namespace_keys && !prefix.is_empty() {
        key.strip_prefix(&format!("{prefix}-"))
            .unwrap_or(key)
            .to_owned()
    } else {
        key.to_owned()
    }
}

fn read_v3(spec: &DesignSpec, src: &str, diagnostics: &mut Vec<String>) -> Vec<ThemeEntry> {
    let Some(theme) = v3::theme_object(src) else {
        diagnostics.push("no literal `theme` object found; left to the runtime".to_owned());
        return Vec::new();
    };
    let mut out = Vec::new();
    for section in &theme {
        if section.key == "extend" {
            if let v3::Node::Obj(ext) = &section.node {
                for ns in ext {
                    push_namespace(spec, ns, true, &mut out, diagnostics);
                }
            }
        } else {
            push_namespace(spec, section, false, &mut out, diagnostics);
        }
    }
    out
}

fn push_namespace(
    spec: &DesignSpec,
    ns: &v3::Member,
    extend: bool,
    out: &mut Vec<ThemeEntry>,
    diagnostics: &mut Vec<String>,
) {
    if matches!(ns.node, v3::Node::Leaf(_)) {
        diagnostics.push(format!(
            "theme namespace `{}` (line {}) is not an object literal; left to the runtime",
            ns.key, ns.line
        ));
        return;
    }
    let mut leaves = Vec::new();
    v3::flatten("", ns.line, &ns.node, &mut leaves);
    for (key, line, value) in leaves {
        let key = if key.is_empty() {
            "DEFAULT".to_owned()
        } else {
            key
        };
        out.push(ThemeEntry {
            namespace: ns.key.clone(),
            step: step_of(spec, &ns.key, &key),
            alpha_companion: value.contains("<alpha-value>"),
            key,
            value,
            resolved: None,
            unresolved_vars: Vec::new(),
            line,
            extend,
        });
    }
}

fn read_v4(spec: &DesignSpec, src: &str) -> Vec<ThemeEntry> {
    let vars = v4::theme_vars(src);
    let defined: BTreeMap<&str, &str> = vars
        .iter()
        .map(|v| (v.name.as_str(), v.value.as_str()))
        .collect();
    vars.iter()
        .map(|v| {
            let (ns, key) = v4::split_name(&v.name);
            let (resolved, unresolved_vars) = resolve_vars(&v.value, &defined, 0);
            ThemeEntry {
                namespace: ns.to_owned(),
                step: step_of(spec, ns, &key),
                key,
                alpha_companion: v.value.contains("<alpha-value>"),
                resolved: (resolved != v.value && unresolved_vars.is_empty()).then_some(resolved),
                value: v.value.clone(),
                unresolved_vars,
                line: v.line,
                extend: true,
            }
        })
        .collect()
}

/// Substitute `var(--x)` references from `defined`; returns the text and the names no
/// `@theme` entry defines (a fallback `var(--x, d)` counts as resolved to `d`).
fn resolve_vars(value: &str, defined: &BTreeMap<&str, &str>, depth: u8) -> (String, Vec<String>) {
    let mut out = String::new();
    let mut missing = Vec::new();
    let mut rest = value;
    while let Some(at) = rest.find("var(") {
        out.push_str(&rest[..at]);
        let body_start = at + 4;
        let mut depth_p = 1usize;
        let mut end = rest.len();
        for (i, c) in rest[body_start..].char_indices() {
            match c {
                '(' => depth_p += 1,
                ')' => {
                    depth_p -= 1;
                    if depth_p == 0 {
                        end = body_start + i;
                        break;
                    }
                }
                _ => {}
            }
        }
        let body = &rest[body_start..end];
        let (name, fallback) = match body.split_once(',') {
            Some((n, f)) => (n.trim(), Some(f.trim())),
            None => (body.trim(), None),
        };
        match (defined.get(name), fallback) {
            (Some(v), _) if depth < 8 => {
                let (inner, inner_missing) = resolve_vars(v, defined, depth + 1);
                out.push_str(&inner);
                missing.extend(inner_missing);
            }
            (_, Some(f)) => out.push_str(f),
            _ => {
                missing.push(name.to_owned());
                out.push_str(&rest[at..(end + 1).min(rest.len())]);
            }
        }
        rest = &rest[(end + 1).min(rest.len())..];
    }
    out.push_str(rest);
    (out, missing)
}

/// The default-collision rule an entry triggers, if any.
fn default_rule(version: TailwindVersion, namespace: &str, key: &str) -> Option<&'static str> {
    let v3 = version == TailwindVersion::V3;
    let hit = match namespace {
        "colors" => {
            return has_key(if v3 { V3_COLOR_NAMES } else { V4_COLOR_NAMES }, key)
                .then_some("TW004");
        }
        "spacing" => {
            if v3 {
                has_key(V3_SPACING_KEYS, key)
            } else {
                is_v4_spacing_key(key)
            }
        }
        "borderRadius" => has_key(
            if v3 {
                V3_BORDER_RADIUS_KEYS
            } else {
                V4_BORDER_RADIUS_KEYS
            },
            key,
        ),
        "fontSize" => has_key(
            if v3 {
                V3_FONT_SIZE_KEYS
            } else {
                V4_FONT_SIZE_KEYS
            },
            key,
        ),
        "zIndex" => has_key(if v3 { V3_Z_INDEX_KEYS } else { V4_Z_INDEX_KEYS }, key),
        _ => false,
    };
    hit.then_some("TW005")
}

fn collisions(
    version: TailwindVersion,
    entries: &[ThemeEntry],
    waivers: &[text::LineWaiver],
) -> Vec<Collision> {
    entries
        .iter()
        .filter(|e| e.extend)
        .filter_map(|e| {
            let rule = default_rule(version, &e.namespace, &e.key)?;
            let waiver = text::waiver_for(waivers, rule, e.line);
            tracing::debug!(rule, ns = %e.namespace, key = %e.key, waived = waiver.is_some(), "tailwind: default collision");
            Some(Collision {
                rule: rule.to_owned(),
                namespace: e.namespace.clone(),
                key: e.key.clone(),
                line: e.line,
                waived: waiver.is_some(),
                reason: waiver.and_then(|w| w.reason.clone()),
            })
        })
        .collect()
}

/// The path a `[tailwind]` section would read, for callers that only need to know it.
pub fn tailwind_source_path(spec: &DesignSpec) -> Option<PathBuf> {
    spec.tailwind_config_path().or_else(|| {
        (!spec.tailwind.css_entry.is_empty()).then(|| spec.root.join(&spec.tailwind.css_entry))
    })
}
