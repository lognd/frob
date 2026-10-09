//! Name-based call reach, a supplement to `SymbolGraph::affects`.
//!
//! `gob-symbols` records calls per crate and does not see inside macro
//! invocations, so `assert_eq!(double(2), 4)` and a call from one workspace
//! crate into another leave no edge. This module scans function bodies for
//! `name(` and links the caller to every function of that name, but only when
//! exactly one function in the repository has the name: a unique name is an
//! unambiguous callee, while `new` or `run` would drag in the world. Ambiguous
//! names fall back to the graph's own (per-crate) edges alone.

use std::collections::{BTreeSet, HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};

use gob_symbols::{SymbolGraph, SymbolKind, Symref};

/// Lazily read file text, shared by the attribute scan and the body scan.
#[derive(Debug)]
pub struct Sources {
    root: PathBuf,
    cache: HashMap<String, Option<String>>,
}

impl Sources {
    /// Sources under the work tree `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            cache: HashMap::new(),
        }
    }

    // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
    /// The text of repo-relative `path`, read once, as git would store it when the work tree file has CRLF ends.
    ///
    /// Symbol spans are measured on the git-normalized text (a CRLF checkout of an LF blob parses as LF),
    /// so a raw CRLF read would drift one byte per line and every attribute scan after the first method
    /// would read the wrong place. Only a file holding a `\r` pays for the git read.
    pub fn get(&mut self, path: &str) -> Option<&str> {
        let root = &self.root;
        self.cache
            .entry(path.to_owned())
            .or_insert_with(|| {
                let raw = std::fs::read_to_string(root.join(path)).ok()?;
                if !raw.contains('\r') {
                    return Some(raw);
                }
                gob_walk::ContentSource::locate(root)
                    .with_reader(|r| r.read_text(path))
                    .ok()
                    .or(Some(raw))
            })
            .as_deref()
    }
}

/// Identifiers directly followed by `(` in `body` (calls and method calls, not macros or `fn`/`def` names).
pub fn called_names(body: &str) -> BTreeSet<String> {
    let bytes = body.as_bytes();
    let mut out = BTreeSet::new();
    let mut i = 0;
    while i < bytes.len() {
        let b = bytes[i];
        if b == b'_' || b.is_ascii_alphabetic() {
            let start = i;
            while i < bytes.len() && (bytes[i] == b'_' || bytes[i].is_ascii_alphanumeric()) {
                i += 1;
            }
            let name = &body[start..i];
            let mut j = i;
            while j < bytes.len() && bytes[j] == b' ' {
                j += 1;
            }
            let before = body[..start].trim_end();
            // frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
            let after_fn = ["fn", "def"].iter().any(|kw| {
                before.strip_suffix(kw).is_some_and(|head| {
                    !head.ends_with(|c: char| c == '_' || c.is_ascii_alphanumeric())
                })
            });
            if bytes.get(j) == Some(&b'(') && !after_fn {
                out.insert(name.to_owned());
            }
        } else {
            i += 1;
        }
    }
    out
}

/// Every function that transitively calls (by unique name) one of `seeds`.
pub fn name_callers(
    graph: &SymbolGraph,
    sources: &mut Sources,
    seeds: &BTreeSet<Symref>,
) -> BTreeSet<Symref> {
    let funcs: Vec<_> = graph
        .records()
        .filter(|r| matches!(r.kind, SymbolKind::Function | SymbolKind::Method))
        .collect();
    let mut count: HashMap<&str, usize> = HashMap::new();
    for r in &funcs {
        if let Some(n) = r.symref.name() {
            *count.entry(n).or_default() += 1;
        }
    }
    let mut callers: HashMap<String, Vec<Symref>> = HashMap::new();
    for r in &funcs {
        let Some(text) = sources.get(r.symref.path()) else {
            continue;
        };
        let range = usize::try_from(u32::from(r.span.start())).unwrap_or(usize::MAX)
            ..usize::try_from(u32::from(r.span.end())).unwrap_or(usize::MAX);
        let Some(body) = text.get(range) else {
            continue;
        };
        for name in called_names(body) {
            if r.symref.name() != Some(name.as_str()) {
                callers.entry(name).or_default().push(r.symref.clone());
            }
        }
    }
    let mut found: BTreeSet<Symref> = BTreeSet::new();
    let mut seen: HashSet<Symref> = HashSet::new();
    let mut queue: VecDeque<Symref> = seeds.iter().cloned().collect();
    while let Some(s) = queue.pop_front() {
        if !seen.insert(s.clone()) {
            continue;
        }
        let Some(name) = s.name() else { continue };
        if count.get(name).copied() != Some(1) {
            continue;
        }
        for c in callers.get(name).into_iter().flatten() {
            found.insert(c.clone());
            queue.push_back(c.clone());
        }
    }
    tracing::debug!(
        seeds = seeds.len(),
        found = found.len(),
        "name-based reach computed"
    );
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_calls_in_macros_and_methods_but_not_definitions_or_macros() {
        let names =
            called_names("fn go() { assert_eq!(double(2), 4); x.triple(); println!(\"hi\"); }");
        assert!(names.contains("double") && names.contains("triple"));
        assert!(!names.contains("assert_eq") && !names.contains("println"));
        assert!(!names.contains("go"), "{names:?}");
    }
}
