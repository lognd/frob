//! Path-scoped pack activation from the one root configuration
//! (plugins.md section 2: no directory-scoped packs).
//!
//! `[[packs.enable]]` entries say which packs apply to which paths; the
//! legacy `[packs] enabled = [...]` list activates packs everywhere. Only
//! the root configuration text is consulted: resolving a path never looks at
//! the filesystem, so a nested `pack.toml` or `grimble.toml` cannot change
//! what applies below it. Every answer names the config line it came from.

use globset::{Glob, GlobSet, GlobSetBuilder};
use serde::Deserialize;
use toml::Spanned;

use crate::error::PackError;

/// Most `[[packs.enable]]` entries accepted.
const MAX_ENABLES: usize = 1024;
/// Most path globs per entry.
const MAX_PATHS: usize = 256;

#[derive(Deserialize)]
struct Root {
    #[serde(default)]
    packs: Option<PacksRaw>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PacksRaw {
    #[serde(default)]
    enabled: Option<Spanned<Vec<String>>>,
    #[serde(default)]
    enable: Vec<Spanned<EnableRaw>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct EnableRaw {
    name: String,
    #[serde(default)]
    paths: Vec<String>,
    #[serde(default)]
    required: bool,
}

/// One activation entry: a pack, the paths it applies to, and its source line.
#[derive(Debug, Clone)]
pub struct Enable {
    /// The pack name.
    pub name: String,
    /// The path globs it applies to; empty means everywhere.
    pub paths: Vec<String>,
    /// Whether the pack must be resolvable (an unfinished plugin is then Unresolved).
    pub required: bool,
    /// One-based line of the entry in the root configuration.
    pub line: usize,
    set: Option<GlobSet>,
}

/// A pack found active for a path, with the config location that activated it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Active {
    /// The pack name.
    pub name: String,
    /// The root configuration file.
    pub file: String,
    /// One-based line of the activating entry.
    pub line: usize,
    /// Whether the entry marked the pack required.
    pub required: bool,
}

/// The parsed activation entries of one root configuration.
#[derive(Debug, Clone)]
pub struct Activation {
    file: String,
    entries: Vec<Enable>,
}

fn line_of(text: &str, offset: usize) -> usize {
    text[..offset.min(text.len())]
        .bytes()
        .filter(|&b| b == b'\n')
        .count()
        + 1
}

fn bad(file: &str, key: &str, line: usize, reason: impl Into<String>) -> PackError {
    PackError::Malformed {
        file: file.into(),
        key: key.into(),
        line: Some(line),
        reason: reason.into(),
    }
}

impl Activation {
    /// Parses the `[packs]` table of the root config.
    ///
    /// # Errors
    /// PACK005 [`PackError::Malformed`] naming file, key and line.
    pub fn parse(file: &str, text: &str) -> Result<Self, PackError> {
        let root: Root = toml::from_str(text).map_err(|e| {
            let line = e.span().map_or(1, |s| line_of(text, s.start));
            bad(file, "packs", line, e.message().to_string())
        })?;
        let mut entries = Vec::new();
        if let Some(p) = root.packs {
            if let Some(list) = p.enabled {
                let line = line_of(text, list.span().start);
                for name in list.into_inner() {
                    entries.push(Enable {
                        name,
                        paths: vec![],
                        required: false,
                        line,
                        set: None,
                    });
                }
            }
            if p.enable.len() > MAX_ENABLES {
                return Err(bad(
                    file,
                    "packs.enable",
                    1,
                    format!("more than {MAX_ENABLES} entries"),
                ));
            }
            for sp in p.enable {
                let line = line_of(text, sp.span().start);
                let raw = sp.into_inner();
                if raw.paths.len() > MAX_PATHS {
                    return Err(bad(
                        file,
                        "packs.enable.paths",
                        line,
                        format!("more than {MAX_PATHS} paths"),
                    ));
                }
                let set = if raw.paths.is_empty() {
                    None
                } else {
                    let mut b = GlobSetBuilder::new();
                    for g in &raw.paths {
                        let glob = Glob::new(g)
                            .map_err(|e| bad(file, "packs.enable.paths", line, e.to_string()))?;
                        b.add(glob);
                    }
                    Some(
                        b.build()
                            .map_err(|e| bad(file, "packs.enable.paths", line, e.to_string()))?,
                    )
                };
                entries.push(Enable {
                    name: raw.name,
                    paths: raw.paths,
                    required: raw.required,
                    line,
                    set,
                });
            }
        }
        tracing::debug!(file, entries = entries.len(), "activation parsed");
        Ok(Self {
            file: file.into(),
            entries,
        })
    }

    /// The parsed entries in file order.
    pub fn entries(&self) -> &[Enable] {
        &self.entries
    }

    /// The packs active for a root-relative path, each with the config line that activated it.
    pub fn resolve(&self, path: &str) -> Vec<Active> {
        let out: Vec<Active> = self
            .entries
            .iter()
            .filter(|e| e.set.as_ref().is_none_or(|s| s.is_match(path)))
            .map(|e| Active {
                name: e.name.clone(),
                file: self.file.clone(),
                line: e.line,
                required: e.required,
            })
            .collect();
        tracing::debug!(path, active = out.len(), "activation resolved");
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const CFG: &str = "[project]\nx = 1\n\n[[packs.enable]]\nname = \"react\"\npaths = [\"frontend/**\"]\n\n[[packs.enable]]\nname = \"core\"\nrequired = true\n";

    // frob:ticket 01M3ZX7JWHQZQHD66HV2SB0498
    #[test]
    fn activation_scopes_react_to_frontend_and_names_line() {
        let a = Activation::parse("grimble.toml", CFG).unwrap();
        let f = a.resolve("frontend/a.tsx");
        assert!(
            f.iter()
                .any(|x| x.name == "react" && x.line == 4 && x.file == "grimble.toml")
        );
        let b = a.resolve("backend/b.ts");
        assert!(b.iter().all(|x| x.name != "react"));
        assert!(
            b.iter()
                .any(|x| x.name == "core" && x.required && x.line == 8)
        );
    }

    // frob:ticket 01M3ZX7JWHQZQHD66HV2SB0498
    #[test]
    fn activation_ignores_nested_pack_toml() {
        let d = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(d.path().join("sub")).unwrap();
        std::fs::write(d.path().join("sub/pack.toml"), "[pack]\nname=\"zzz\"\n").unwrap();
        let a = Activation::parse("grimble.toml", CFG).unwrap();
        let before = a.resolve("sub/x.ts");
        assert_eq!(before, a.resolve("sub/x.ts"));
        assert!(before.iter().all(|x| x.name != "zzz"));
    }

    // frob:ticket 01M3ZX7JWHQZQHD66HV2SB0498
    #[test]
    fn activation_rejects_bad_glob_with_line() {
        let e = Activation::parse("g.toml", "[[packs.enable]]\nname=\"a\"\npaths=[\"[\"]\n")
            .unwrap_err();
        assert!(e.to_string().contains("PACK005 g.toml:1"));
    }
}
