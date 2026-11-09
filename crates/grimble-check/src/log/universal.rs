//! The universal-model witness for LOG001: call targets resolved through gob-symbols, not tree-sitter.
//!
//! Per `docs/design/shared/universal-model.md` sections 3, 5 and 8 a rule is written once against
//! the universal model `U`. The per-language scanners in `lang_*` walk raw trees; this module
//! answers the same question through `gob_symbols::extract_file` (call sites with their qualifying
//! path, `use` bindings, file-local symbols). [`output_calls`] returns every call whose canonical
//! path a reportable catalogue atom accepts, so [`super::pass`] can cross-check the scanners:
//! a call `U` resolves to direct output that a scanner left clean is reported Unresolved, never clean.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use std::collections::{BTreeMap, BTreeSet};

use gob_symbols::{FileSymbols, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

use super::catalogue::{ArgInfo, Args, Group};
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
/// Argument conditions (`when`, `mode_arg`, `capture-kwarg`) are queried from the call's byte span,
/// following one hop of handle-flow through names bound once in the file.
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
    let out = resolve(gid, sep, text, &fs, group);
    tracing::debug!(
        file = path,
        calls = fs.calls.len(),
        resolved = out.len(),
        "U witness done"
    );
    out
}

/// Split the text between a call's outer parentheses on top-level commas, honouring nested
/// brackets and quoted strings; the call's arguments as written, trimmed, empty ones dropped.
fn split_args(span: &str) -> Vec<String> {
    let Some(open) = span.find('(') else {
        return Vec::new();
    };
    let (mut depth, mut quote, mut cur) = (0usize, None::<char>, String::new());
    let mut parts: Vec<String> = Vec::new();
    for ch in span[open + 1..].chars() {
        if let Some(q) = quote {
            quote = (ch != q).then_some(q);
        } else if matches!(ch, '"' | '\'') {
            quote = Some(ch);
        } else if matches!(ch, '(' | '[' | '{') {
            depth += 1;
        } else if matches!(ch, ')' | ']' | '}') {
            if depth == 0 {
                break;
            }
            depth -= 1;
        } else if ch == ',' && depth == 0 {
            parts.push(std::mem::take(&mut cur));
            continue;
        }
        cur.push(ch);
    }
    parts.push(cur);
    parts
        .into_iter()
        .map(|p| p.trim().to_owned())
        .filter(|p| !p.is_empty())
        .collect()
}

/// Split a Python-style `name=value` keyword argument; `None` for a positional expression.
fn split_kwarg(arg: &str) -> Option<(&str, &str)> {
    let (k, v) = arg.split_once('=')?;
    let ident = !k.is_empty() && k.chars().all(|c| c.is_alphanumeric() || c == '_');
    (ident && !v.starts_with('=')).then_some((k, v.trim()))
}

/// The facts one argument expression carries: integer, string literal, `True`, or a symbol path
/// whose head is resolved through the file's `use` bindings (a trailing `()` is a query on the path).
fn arg_info(expr: &str, sep: &str, fs: &FileSymbols) -> ArgInfo {
    let int = expr.parse::<i64>().ok();
    let unprefixed = expr.trim_start_matches(['r', 'b']);
    let text = ['"', '\'']
        .iter()
        .find_map(|q| unprefixed.strip_prefix(*q)?.strip_suffix(*q))
        .filter(|t| !t.contains(['"', '\'']))
        .map(str::to_owned);
    let bare = expr.strip_suffix("()").unwrap_or(expr);
    let dotted = bare
        .split(sep)
        .all(|s| !s.is_empty() && s.chars().all(|c| c.is_alphanumeric() || c == '_'));
    let path = (int.is_none() && text.is_none() && dotted).then(|| {
        let mut segs: Vec<String> = bare.split(sep).map(str::to_owned).collect();
        if let Some(u) = fs.uses.iter().rev().find(|u| u.local == segs[0]) {
            let mut head: Vec<String> = u.target.split(sep).map(str::to_owned).collect();
            head.extend(segs.drain(1..));
            segs = head;
        }
        segs
    });
    ArgInfo {
        int,
        text,
        path,
        truthy: expr == "True",
    }
}

/// Single-assignment bindings of a file (`h = sys.stdout`, `let fd = 1;`): name to right-hand side.
/// A name assigned more than once is dropped, so only a flow that is unambiguous is followed.
fn flow_bindings(text: &str) -> BTreeMap<String, String> {
    let mut seen: BTreeMap<String, Option<String>> = BTreeMap::new();
    for line in text.lines() {
        let mut stmt = line.trim();
        for kw in ["let mut ", "let ", "const ", "var "] {
            stmt = stmt.strip_prefix(kw).unwrap_or(stmt);
        }
        let Some((lhs, rhs)) = stmt.split_once('=') else {
            continue;
        };
        let (lhs, rhs) = (lhs.trim(), rhs.trim().trim_end_matches(';').trim());
        let ident = !lhs.is_empty() && lhs.chars().all(|c| c.is_alphanumeric() || c == '_');
        if !ident || rhs.starts_with('=') || rhs.is_empty() {
            continue;
        }
        let slot = seen.entry(lhs.to_owned()).or_insert(None);
        *slot = match slot {
            None => Some(rhs.to_owned()),
            Some(_) => Some(String::new()),
        };
    }
    let out: BTreeMap<String, String> = seen
        .into_iter()
        .filter_map(|(k, v)| v.filter(|r| !r.is_empty()).map(|r| (k, r)))
        .collect();
    tracing::debug!(bindings = out.len(), "handle-flow bindings collected");
    out
}

/// The facts of one argument, following one hop of handle-flow: a bare name bound once in the
/// file stands for its right-hand side, and a `name.member` path for the bound path plus member.
fn flow_info(expr: &str, sep: &str, fs: &FileSymbols, flow: &BTreeMap<String, String>) -> ArgInfo {
    let (head, rest) = expr.split_once(sep).unwrap_or((expr, ""));
    let Some(bound) = flow.get(head) else {
        return arg_info(expr, sep, fs);
    };
    let joined = if rest.is_empty() {
        bound.clone()
    } else {
        format!("{bound}{sep}{rest}")
    };
    tracing::debug!(name = head, bound = %bound, "argument followed through handle-flow");
    arg_info(&joined, sep, fs)
}

/// The arguments of the call occupying `start..end` of `text`, read from its source span (the
/// U query for `when`, `mode_arg` and `capture-kwarg` conditions); empty when the span is unknown.
fn call_args(text: &str, start: usize, end: usize, sep: &str, fs: &FileSymbols) -> Args {
    let mut args = Args::default();
    let Some(span) = text.get(start..end) else {
        return args;
    };
    let flow = flow_bindings(text);
    for raw in split_args(span) {
        match split_kwarg(&raw) {
            Some((k, v)) => args.kw.push((k.to_owned(), flow_info(v, sep, fs, &flow))),
            None => args.pos.push(flow_info(&raw, sep, fs, &flow)),
        }
    }
    args
}

/// A call site with its canonical path and arguments, before any atom is chosen.
struct Site {
    /// One-based line of the call.
    line: u32,
    /// Byte span of the call expression.
    span: (usize, usize),
    /// The canonical symbol path.
    path: SymPath,
    /// The call's arguments.
    args: Args,
}

/// Resolve the call sites of `fs` through its `use` bindings into canonical paths with arguments.
fn sites(gid: &str, sep: &str, text: &str, fs: &FileSymbols) -> Vec<Site> {
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
        out.push(Site {
            line: c.line,
            span: (c.start, c.end),
            args: call_args(text, c.start, c.end, sep, fs),
            path,
        });
    }
    out
}

/// Resolve the call sites of `fs` through its `use` bindings and match them against `group`.
fn resolve(gid: &str, sep: &str, text: &str, fs: &FileSymbols, group: &Group) -> Vec<UCall> {
    sites(gid, sep, text, fs)
        .into_iter()
        .filter_map(|s| {
            let atom = group.first_match(&s.path, &s.args)?;
            Some(UCall {
                line: s.line,
                start: s.span.0,
                end: s.span.1,
                path: s.path,
                atom,
            })
        })
        .collect()
}

/// Every call to a mode-aware atom whose mode argument `U` cannot decide (neither a literal nor a
/// once-bound name), so whether it opens for writing is unresolved rather than silently clean.
///
/// Same groups and callee rules as [`output_calls`]; `atom` indexes the mode-aware atom.
#[must_use]
pub fn mode_unresolved_calls(gid: &str, path: &str, text: &str, group: &Group) -> Vec<UCall> {
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
    let out: Vec<UCall> = sites(gid, sep, text, &fs)
        .into_iter()
        .filter(|s| group.mode_unresolved(&s.path, &s.args))
        .filter_map(|s| {
            let atom = group
                .atoms
                .iter()
                .position(|a| a.mode_arg.is_some() && a.matches_path(&s.path))?;
            Some(UCall {
                line: s.line,
                start: s.span.0,
                end: s.span.1,
                path: s.path,
                atom,
            })
        })
        .collect();
    tracing::debug!(
        file = path,
        unresolved = out.len(),
        "U mode-unresolved done"
    );
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
    fn fd_and_path_literal_conditions_are_queried() {
        let src = "import os\nos.write(1, b'x')\nos.write(7, b'x')\nopen('/dev/stdout', 'w')\n";
        let got = calls("python", "a.py", src);
        let ids: Vec<&str> = got.iter().map(|c| c.2.as_str()).collect();
        assert_eq!(ids, ["py.os-write", "py.path-std"], "{got:?}");
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn capture_kwarg_suppresses_subprocess() {
        let src = "import subprocess\nsubprocess.run(['a'])\nsubprocess.run(['a'], capture_output=True)\n";
        let got = calls("python", "a.py", src);
        assert_eq!(got.len(), 1, "{got:?}");
        assert_eq!(got[0].0, 2);
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn rust_fd_literal_is_queried() {
        let src =
            "use nix::unistd::write;\nfn f() {\n    write(1, b\"x\");\n    write(9, b\"x\");\n}\n";
        let got = calls("rust", "a.rs", src);
        assert_eq!(got.len(), 1, "{got:?}");
        assert_eq!(got[0].0, 3);
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

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn handle_flow_follows_a_once_bound_name() {
        let src = "import os\nfd = 1\nos.write(fd, b'x')\nother = 7\nos.write(other, b'x')\n";
        let got = calls("python", "a.py", src);
        assert_eq!(got.len(), 1, "{got:?}");
        assert_eq!(got[0].0, 3);
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::output_calls
    #[test]
    fn rebound_name_is_not_followed() {
        let src = "import os\nfd = 1\nfd = 7\nos.write(fd, b'x')\n";
        assert!(calls("python", "a.py", src).is_empty());
    }

    // frob:tests crates/grimble-check/src/log/universal.rs::mode_unresolved_calls
    #[test]
    fn non_literal_mode_is_unresolved_not_clean() {
        let cat = Catalogue::builtin().expect("catalogue");
        let g = &cat.groups["python"];
        let src = "m = 'w'\nopen('a', m)\nopen('a', pick())\nopen('a', 'r')\n";
        let got = mode_unresolved_calls("python", "a.py", src, g);
        assert_eq!(got.len(), 1, "{got:?}");
        assert_eq!(got[0].line, 3);
    }
}
