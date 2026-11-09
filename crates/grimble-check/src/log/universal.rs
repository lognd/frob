//! The universal-model witness for LOG001: call targets resolved through gob-symbols, not tree-sitter.
//!
//! Per `docs/design/shared/universal-model.md` sections 3, 5 and 8 a rule is written once against
//! the universal model `U`. The per-language scanners in `lang_*` walk raw trees; this module
//! answers the same question through `gob_symbols::extract_file` (call sites with their qualifying
//! path, `use` bindings, file-local symbols). [`output_calls`] returns every call whose canonical
//! path a reportable catalogue atom accepts, so [`super::pass`] can cross-check the scanners:
//! a call `U` resolves to direct output that a scanner left clean is reported Unresolved, never clean.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use std::collections::BTreeSet;

use gob_symbols::{FileSymbols, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

use super::catalogue::{Args, Atom, Group};
use super::engine::SymPath;

/// One call the universal model resolves to a catalogue atom.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UCall {
    /// One-based source line of the call.
    pub line: u32,
    /// Byte offset of the call expression's first byte.
    pub start: usize,
    /// Byte offset one past the call expression's last byte.
    pub end: usize,
    /// The canonical symbol path the call resolves to.
    pub path: SymPath,
    /// Index into [`Group::atoms`].
    pub atom: usize,
}

/// The path separator of a group's `use` targets (`::` for Rust, `.` elsewhere), or `None` when
/// the group is not resolved through `U` yet.
fn separator(gid: &str) -> Option<&'static str> {
    match gid {
        "rust" => Some("::"),
        "python" | "javascript" => Some("."),
        _ => None,
    }
}

/// Every call in `text` that `U` resolves to a reportable atom of `group`, in source order.
///
/// Groups other than Rust, Python and JavaScript/TypeScript yield nothing (their adapters are
/// not yet precise enough to be a witness). A callee headed by a local binding, a file-local
/// symbol or a method receiver is not resolved: it is never reported from here.
#[must_use]
pub fn output_calls(gid: &str, path: &str, text: &str, group: &Group) -> Vec<UCall> {
    let Some(sep) = separator(gid) else {
        return Vec::new();
    };
    let entry = FileEntry {
        language: LanguageHint::from_path(path),
        digest: Digest::of(text.as_bytes()),
        size: text.len() as u64,
        path: path.to_owned(),
    };
    let fs = extract_file(&entry, text);
    let out = resolve(gid, sep, &fs, group);
    tracing::debug!(
        file = path,
        calls = fs.calls.len(),
        resolved = out.len(),
        "U witness done"
    );
    out
}

/// True when the atom fires on the callee path alone: no argument condition, no mode argument,
/// and no resolution class (`capture-kwarg`, `handle-flow`) that needs the call's arguments or uses.
fn is_plain(atom: &Atom) -> bool {
    atom.when.is_none()
        && atom.mode_arg.is_none()
        && !atom.via.iter().any(|v| {
            matches!(
                v.as_str(),
                "capture-kwarg" | "handle-flow" | "fd-literal" | "path-literal"
            )
        })
}

/// Resolve the call sites of `fs` through its `use` bindings and match them against `group`.
fn resolve(gid: &str, sep: &str, fs: &FileSymbols, group: &Group) -> Vec<UCall> {
    let local_names: BTreeSet<&str> = fs
        .symbols
        .iter()
        .filter_map(|s| s.symref.segments().last().map(String::as_str))
        .collect();
    let mut out = Vec::new();
    for c in &fs.calls {
        if c.method
            || c.in_macro
            || c.opaque_qualifier
            || c.local != gob_symbols::LocalBinding::None
        {
            continue;
        }
        let mut segs: Vec<String> = c.qual_path.clone();
        segs.push(c.callee.clone());
        let head = segs[0].clone();
        if local_names.contains(head.as_str()) {
            continue;
        }
        let mut path: SymPath = match fs.uses.iter().rev().find(|u| u.local == head) {
            Some(u) => u
                .target
                .split(sep)
                .filter(|s| !s.is_empty())
                .map(str::to_owned)
                .collect(),
            None if gid == "python" && segs.len() == 1 => vec!["builtins".to_owned(), head],
            None => vec![head],
        };
        path.extend(segs.into_iter().skip(1));
        if let Some(atom) = group
            .first_match(&path, &Args::default())
            .filter(|&i| is_plain(&group.atoms[i]))
        {
            out.push(UCall {
                line: c.line,
                start: c.start,
                end: c.end,
                path,
                atom,
            });
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::log::catalogue::Catalogue;

    fn spans(gid: &str, file: &str, text: &str) -> Vec<(usize, usize)> {
        let cat = Catalogue::builtin().expect("catalogue");
        output_calls(gid, file, text, &cat.groups[gid])
            .into_iter()
            .map(|c| (c.start, c.end))
            .collect()
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn two_calls_on_one_line_carry_distinct_byte_spans() {
        let text = "def f():\n    print(1); print(2)\n";
        let got = spans("python", "a.py", text);
        assert_eq!(got.len(), 2, "{got:?}");
        assert_eq!(&text[got[0].0..got[0].1], "print(1)");
        assert_eq!(&text[got[1].0..got[1].1], "print(2)");
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn rust_call_span_covers_the_call_expression() {
        let text = "use std::io::stdout;\nfn f() {\n    let _ = std::process::exit(0);\n}\n";
        for (a, b) in spans("rust", "a.rs", text) {
            assert!(a < b && b <= text.len());
        }
    }

    fn calls(gid: &str, file: &str, text: &str) -> Vec<(u32, String, String)> {
        let cat = Catalogue::builtin().expect("catalogue");
        let g = &cat.groups[gid];
        output_calls(gid, file, text, g)
            .into_iter()
            .map(|c| (c.line, c.path.join("."), g.atoms[c.atom].id.clone()))
            .collect()
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn python_alias_and_builtin_resolve_through_uses() {
        let got = calls(
            "python",
            "a.py",
            "import pprint as pp\ndef f():\n    print('x')\n    pp.pprint(1)\n",
        );
        let atoms: Vec<&str> = got.iter().map(|c| c.2.as_str()).collect();
        assert!(atoms.contains(&"py.print"), "{got:?}");
        assert!(got.iter().any(|c| c.1 == "pprint.pprint"), "{got:?}");
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn local_shadowing_is_not_resolved() {
        let got = calls(
            "python",
            "a.py",
            "def print(x):\n    pass\n\ndef f():\n    print(1)\n",
        );
        assert!(got.is_empty(), "{got:?}");
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn unsupported_groups_yield_nothing() {
        assert!(
            calls(
                "java",
                "A.java",
                "class A { void f(){ System.out.println(1);} }"
            )
            .is_empty()
        );
    }
}
