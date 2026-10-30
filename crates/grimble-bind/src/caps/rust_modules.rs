//! Cross-module Rust name resolution for the capability scan (ticket 01M64230DV9KGPE0JH2D37NDVN).
//!
//! `pub use std::process::Command as Cmd;` in one repository module and `use crate::w::Cmd;` in
//! another hide the vocabulary callee from a per-file scan, as do type aliases that a module
//! re-exports. [`RustModules::origins`] follows a `::` path through the repository's own Rust
//! modules (inline `mod x { .. }`, `mod x;` files with `#[path]`, `crate::` / `self::` / `super::`
//! heads, `use .. as ..` chains, glob imports) to every symbol it may denote. A name a module
//! defines itself is a repository item, not a capability; a name with several possible bindings,
//! a glob that may supply it, a missing module file or a chain too deep or cyclic yields the path
//! unproven (Unresolved), never silently dropped. A head that no repository module binds is an
//! external crate and stays as written.

// frob:ticket 01M64230DV9KGPE0JH2D37NDVN

use std::collections::{BTreeMap, BTreeSet};

use gob_symbols::RustModule;

use super::Cx;
pub(super) use super::python_modules::Origin;

/// Deepest chain of re-exports followed before the path is left as written (unproven).
const MAX_DEPTH: usize = 8;

/// A module of the repository: a file, then the inline modules nested in it.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Loc {
    file: String,
    chain: Vec<String>,
}

impl Loc {
    /// The module body of the file itself.
    fn root(file: &str) -> Self {
        Self {
            file: file.to_owned(),
            chain: Vec::new(),
        }
    }
}

/// Parsed module trees of repository Rust files, cached per file.
#[derive(Default)]
pub(super) struct RustModules {
    cache: BTreeMap<String, Option<RustModule>>,
}

impl RustModules {
    /// The module body at `loc` (`None` when the file is unreadable, unparsable or lacks it).
    fn module(&mut self, cx: &Cx<'_>, loc: &Loc) -> Option<RustModule> {
        let tree = self
            .cache
            .entry(loc.file.clone())
            .or_insert_with(|| {
                let src = cx.code.file(&loc.file)?.source()?;
                let m = gob_symbols::rust_module(&src);
                if m.is_none() {
                    tracing::debug!(file = %loc.file, "rust module does not parse; re-exports unresolved");
                }
                m
            })
            .as_ref()?;
        let mut m = tree;
        for name in &loc.chain {
            m = m.mods.get(name)?;
        }
        Some(m.clone())
    }

    /// Every symbol `path`, written in the file module of `importer`, may denote once repository
    /// re-exports are followed. Empty when the name is defined by a repository module.
    pub(super) fn origins(&mut self, cx: &Cx<'_>, importer: &str, path: &str) -> Vec<Origin> {
        self.walk(
            cx,
            &Loc::root(importer),
            path,
            0,
            false,
            &mut BTreeSet::new(),
        )
    }

    fn walk(
        &mut self,
        cx: &Cx<'_>,
        loc: &Loc,
        path: &str,
        depth: usize,
        globbed: bool,
        active: &mut BTreeSet<(Loc, String)>,
    ) -> Vec<Origin> {
        let as_written = |unproven: bool| {
            vec![Origin {
                path: path.to_owned(),
                unproven,
            }]
        };
        let key = (loc.clone(), path.to_owned());
        if depth >= MAX_DEPTH || active.contains(&key) {
            tracing::debug!(file = %loc.file, path, depth, "re-export chain too deep or cyclic");
            return as_written(true);
        }
        let segs: Vec<&str> = path.split("::").collect();
        let Some((mut cur, mut i)) = head_of(cx, loc, &segs) else {
            return as_written(true);
        };
        loop {
            if i >= segs.len() {
                // the path names a module itself
                return as_written(false);
            }
            let name = segs[i];
            let rest = segs[i + 1..].join("::");
            let Some(module) = self.module(cx, &cur) else {
                return as_written(true);
            };
            if module.mods.contains_key(name) {
                cur.chain.push(name.to_owned());
                i += 1;
                continue;
            }
            if let Some(attr) = module.decls.get(name) {
                let Some(child) = child_file(cx, &cur, name, attr.as_deref()) else {
                    tracing::debug!(file = %cur.file, name, "module file not found; path unresolved");
                    return as_written(true);
                };
                cur = Loc::root(&child);
                i += 1;
                continue;
            }
            if let Some(binding) = module.names.get(name) {
                if binding.origins.is_empty() {
                    tracing::debug!(file = %cur.file, name, "name is defined by a repository module");
                    return Vec::new();
                }
                let several = binding.origins.len() > 1 || binding.local;
                active.insert(key.clone());
                let mut out = Vec::new();
                for origin in &binding.origins {
                    let next = if rest.is_empty() {
                        origin.clone()
                    } else {
                        format!("{origin}::{rest}")
                    };
                    for mut o in self.walk(cx, &cur, &next, depth + 1, false, active) {
                        o.unproven |= several;
                        out.push(o);
                    }
                }
                active.remove(&key);
                return out;
            }
            // (a path a glob import supplied starts at a crate or module, never at another glob)
            if module.globs.is_empty() || (globbed && i == 0) {
                tracing::debug!(file = %cur.file, name, "name is not bound in the module");
                return as_written(false);
            }
            // a glob import may supply the name: every glob is a candidate, none is proven
            active.insert(key.clone());
            let mut out = Vec::new();
            for glob in &module.globs {
                let next = format!("{glob}::{}", segs[i..].join("::"));
                for mut o in self.walk(cx, &cur, &next, depth + 1, true, active) {
                    o.unproven = true;
                    out.push(o);
                }
            }
            active.remove(&key);
            return out;
        }
    }
}

/// Where the walk of `segs` starts: the module and the index of the first segment still to follow.
/// `None` when a `crate::` / `super::` head leaves the known files (the path is then unproven).
fn head_of(cx: &Cx<'_>, loc: &Loc, segs: &[&str]) -> Option<(Loc, usize)> {
    match segs[0] {
        "crate" => {
            if let Some(root) = crate_root(cx, &loc.file) {
                return Some((Loc::root(&root), 1));
            }
            // no lib.rs / main.rs among the files: the first segment is a module file beside
            // the nearest `src` directory
            let file = segs.get(1).and_then(|n| rootless_child(cx, &loc.file, n));
            if file.is_none() {
                tracing::debug!(file = %loc.file, "no crate root found for crate:: path");
            }
            file.map(|f| (Loc::root(&f), 2))
        }
        "self" => Some((Loc::root(&loc.file), 1)),
        "super" => {
            let mut cur = Loc::root(&loc.file);
            let mut i = 0;
            while segs.get(i) == Some(&"super") {
                let Some(parent) = parent_file(cx, &cur.file) else {
                    tracing::debug!(file = %cur.file, "super:: leaves the known modules");
                    return None;
                };
                cur = Loc::root(&parent);
                i += 1;
            }
            Some((cur, i))
        }
        _ => Some((loc.clone(), 0)),
    }
}

/// The directory of a repository path (empty at the root).
fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// `dir/rel` with `.` and `..` segments folded away; `None` when `rel` climbs above the root.
pub(super) fn join_normalized(dir: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = dir.split('/').filter(|p| !p.is_empty()).collect();
    for seg in rel.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// The file name of `path` (after the last `/`).
fn base_of(path: &str) -> &str {
    path.rsplit_once('/').map_or(path, |(_, f)| f)
}

/// The directory in which the child modules of the module file `file` live.
fn children_dir(file: &str) -> String {
    let dir = dir_of(file);
    match base_of(file) {
        "lib.rs" | "main.rs" | "mod.rs" => dir.to_owned(),
        other => {
            let stem = other.strip_suffix(".rs").unwrap_or(other);
            join_normalized(dir, stem).unwrap_or_default()
        }
    }
}

/// The crate root file above `file`: the nearest `lib.rs` / `main.rs` up the directory tree.
fn crate_root(cx: &Cx<'_>, file: &str) -> Option<String> {
    let mut dir = dir_of(file).to_owned();
    loop {
        for root in ["lib.rs", "main.rs"] {
            let cand = join_normalized(&dir, root)?;
            if cx.code.file(&cand).is_some() {
                return Some(cand);
            }
        }
        if dir.is_empty() {
            return None;
        }
        dir = dir_of(&dir).to_owned();
    }
}

/// The file of top-level module `name` when the crate has no root file: beside the nearest `src`.
fn rootless_child(cx: &Cx<'_>, file: &str, name: &str) -> Option<String> {
    let mut dir = dir_of(file).to_owned();
    while !dir.is_empty() && base_of(&dir) != "src" {
        dir = dir_of(&dir).to_owned();
    }
    if dir.is_empty() {
        dir_of(file).clone_into(&mut dir);
    }
    [format!("{name}.rs"), format!("{name}/mod.rs")]
        .iter()
        .filter_map(|c| join_normalized(&dir, c))
        .find(|c| cx.code.file(c).is_some())
}

/// The file of the module that declares the module file `file`, when it can be found.
fn parent_file(cx: &Cx<'_>, file: &str) -> Option<String> {
    let dir = dir_of(file);
    let base = base_of(file);
    if matches!(base, "lib.rs" | "main.rs") {
        return None;
    }
    // the parent's children live in `pdir`: beside `x.rs`, one level up from a `mod.rs`
    let pdir = if base == "mod.rs" { dir_of(dir) } else { dir };
    let mut cands: Vec<String> = ["mod.rs", "lib.rs", "main.rs"]
        .iter()
        .filter_map(|f| join_normalized(pdir, f))
        .collect();
    if !pdir.is_empty() {
        let name = base_of(pdir);
        cands.extend(join_normalized(dir_of(pdir), &format!("{name}.rs")));
    }
    cands
        .into_iter()
        .find(|c| c != file && cx.code.file(c).is_some())
}

/// The file a `mod name;` declaration in `parent` loads (its `#[path]` when it has one).
fn child_file(cx: &Cx<'_>, parent: &Loc, name: &str, attr: Option<&str>) -> Option<String> {
    let cands: Vec<String> = if let Some(rel) = attr {
        join_normalized(dir_of(&parent.file), rel)
            .into_iter()
            .collect()
    } else {
        let mut base = children_dir(&parent.file);
        for seg in &parent.chain {
            base = join_normalized(&base, seg)?;
        }
        [format!("{name}.rs"), format!("{name}/mod.rs")]
            .iter()
            .filter_map(|c| join_normalized(&base, c))
            .collect()
    };
    cands.into_iter().find(|c| cx.code.file(c).is_some())
}

/// The module name a Rust file answers to for its importers: its stem, or its directory for a
/// `mod.rs` / `lib.rs` / `main.rs`.
pub(super) fn stem(path: &str) -> Option<&str> {
    let (dir, file) = path.rsplit_once('/').unwrap_or(("", path));
    let name = file.strip_suffix(".rs")?;
    if matches!(name, "mod" | "lib" | "main") {
        return dir.rsplit('/').next().filter(|d| !d.is_empty());
    }
    Some(name)
}
