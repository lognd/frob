//! Cross-module Python name resolution for the capability scan (ticket 01M6422ZN7HKF98JDAP7XKRQQ2).
//!
//! `from subprocess import run as r` in one repository module and `from helpers import r` in
//! another hide the vocabulary callee from a per-file scan. [`Modules::origins`] follows a
//! dotted use path through the repository's own Python modules (re-exports under an alias,
//! relative imports, chains of them) to every symbol it may denote. A name a module defines
//! itself is a repository item, not a capability; a name with several possible bindings (a
//! definition then an import, a `try`/`except ImportError` fallback) yields every origin, each
//! unproven.

// frob:ticket 01M6422ZN7HKF98JDAP7XKRQQ2

use std::collections::{BTreeMap, BTreeSet};

use gob_symbols::PythonModule;

use super::{Cx, star_repo_file};

/// Deepest chain of re-exports followed before the path is left as written (unproven).
const MAX_DEPTH: usize = 8;

/// One symbol a use path may denote after following repository re-exports.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct Origin {
    /// The qualified path (the use path itself when no repository module rewrites it).
    pub path: String,
    /// True when another binding or origin could equally supply the name.
    pub unproven: bool,
}

/// Parsed module-level bindings of repository Python files, cached per file.
#[derive(Default)]
pub(super) struct Modules {
    cache: BTreeMap<String, Option<PythonModule>>,
}

impl Modules {
    /// The module-level bindings of the repository file `file` (`None` when unreadable).
    fn module(&mut self, cx: &Cx<'_>, file: &str) -> Option<&PythonModule> {
        self.cache
            .entry(file.to_owned())
            .or_insert_with(|| {
                let src = cx.code.file(file)?.source()?;
                let m = gob_symbols::python_module(&src);
                if m.is_none() {
                    tracing::debug!(file, "python module does not parse; re-exports unresolved");
                }
                m
            })
            .as_ref()
    }

    /// Every symbol `path`, written in `importer`, may denote once repository re-exports are
    /// followed. Empty when the name is defined by a repository module (a repository item).
    pub(super) fn origins(&mut self, cx: &Cx<'_>, importer: &str, path: &str) -> Vec<Origin> {
        self.walk(cx, importer, path, 0, &mut BTreeSet::new())
    }

    fn walk(
        &mut self,
        cx: &Cx<'_>,
        importer: &str,
        path: &str,
        depth: usize,
        active: &mut BTreeSet<(String, String)>,
    ) -> Vec<Origin> {
        let as_written = |unproven: bool| {
            vec![Origin {
                path: path.to_owned(),
                unproven,
            }]
        };
        let key = (importer.to_owned(), path.to_owned());
        if depth >= MAX_DEPTH || active.contains(&key) {
            tracing::debug!(importer, path, depth, "re-export chain too deep or cyclic");
            return as_written(true);
        }
        let dots = path.chars().take_while(|c| *c == '.').count();
        let segs: Vec<&str> = path[dots..].split('.').collect();
        // the longest module prefix that is a repository file wins; `name` is the next segment
        let first = usize::from(dots == 0);
        let Some((file, k)) = (first..segs.len()).rev().find_map(|k| {
            let module = format!("{}{}", ".".repeat(dots), segs[..k].join("."));
            star_repo_file(cx, importer, &module).map(|f| (f, k))
        }) else {
            return as_written(false);
        };
        let name = segs[k];
        let tail = segs[k + 1..].join(".");
        let Some(module) = self.module(cx, &file) else {
            return as_written(true);
        };
        let Some(binding) = module.names.get(name).cloned() else {
            let open = !module.stars.is_empty();
            tracing::debug!(file, name, open, "name is not bound at module level");
            return as_written(open);
        };
        if binding.origins.is_empty() {
            tracing::debug!(file, name, "name is defined by a repository module");
            return Vec::new();
        }
        let several = binding.origins.len() > 1 || binding.local;
        active.insert(key.clone());
        let mut out = Vec::new();
        for origin in &binding.origins {
            let next = if tail.is_empty() {
                origin.clone()
            } else {
                format!("{origin}.{tail}")
            };
            for mut o in self.walk(cx, &file, &next, depth + 1, active) {
                o.unproven |= several;
                out.push(o);
            }
        }
        active.remove(&key);
        out
    }
}

/// The module name a Python file answers to for its importers: its stem, or its directory for an
/// `__init__.py`.
pub(super) fn stem(path: &str) -> Option<&str> {
    let (dir, file) = path.rsplit_once('/').unwrap_or(("", path));
    let name = file.strip_suffix(".py")?;
    if name == "__init__" {
        return dir.rsplit('/').next().filter(|d| !d.is_empty());
    }
    Some(name)
}

/// The Python files that may supply a vocabulary callee: those whose source passes `direct`, and
/// (repeatedly) those that mention the module name of one already in the set. A file outside it
/// cannot reach the vocabulary through a repository re-export, so it need not be parsed.
pub(super) fn reaching(
    sources: &[(String, String)],
    direct: impl Fn(&str) -> bool,
    stem: impl Fn(&str) -> Option<&str>,
) -> BTreeSet<String> {
    let mut set: BTreeSet<String> = sources
        .iter()
        .filter(|(_, src)| direct(src))
        .map(|(p, _)| p.clone())
        .collect();
    for _ in 0..MAX_DEPTH {
        let stems: BTreeSet<&str> = set.iter().filter_map(|p| stem(p)).collect();
        let more: Vec<String> = sources
            .iter()
            .filter(|(p, src)| !set.contains(p) && stems.iter().any(|s| src.contains(s)))
            .map(|(p, _)| p.clone())
            .collect();
        if more.is_empty() {
            break;
        }
        set.extend(more);
    }
    set
}
