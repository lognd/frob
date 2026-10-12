//! CAP001 and CAP002: the capability cell of a node, from observed uses and its `may` grants.
//!
//! Binding.md 7.2 item 3: a use of an ungranted atom in code a node owns is `undeclared` and
//! CAP001 (Error, P+, deny by default). Item 6: a grant whose whole scope is Must-owned,
//! detector-covered and complete, and in which no use is possible, is `declared-unused` and
//! CAP002 (Warn, P-). A use is a call that resolves to nothing in the repository and whose
//! callee text is in the callee vocabulary of an atom for the file's language
//! (`gob_ir::registry::callee_vocab`, class = the atom name). A May-owned use never fires CAP001
//! (it is Unresolved) and does prevent CAP002.
//!
//! Method vocabulary (ticket 2T7C4A9): `Path.m` names method `m` on a receiver whose type is
//! `pathlib.Path`, resolved textually (a `Path(..)` chain, or a name assigned or annotated as one
//! in the same file); it is a Must use. A `.m` entry on a receiver that does not resolve is a May
//! use, reported Unresolved (grimble-model.md 9.6: unknown never reads as clean).
//!
//! Known limits: receiver typing is per file and textual (no cross-module constants, no
//! shadowing by unannotated parameters); `open(..)` is `fs.read` whatever its mode; the template excuses and CAP004 (packs.md 6.7) are not implemented; the pack
//! severity table is not consulted (CAP001 is an Error, CAP002 a Warning); a grant's `at`
//! selector is compared at file granularity; `may` arguments are ignored.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use gob_ir::Answer;
use gob_ir::registry::{DetectorKind, atoms, callee_vocab, detectors};
use gob_rules::Severity;
use gob_symbols::EdgeKind;
use gob_walk::{Owner, select_files};
use grimble_model::ast::EntityKind;

use crate::code::CodeFile;
use crate::model::Grant;
use crate::rules::{Cx, Output};
use crate::types::Reason;

/// How many example call sites one finding names.
const EXAMPLES: usize = 3;

/// A method-name vocabulary entry (`.listen`) counts only in a file that also calls the gate
/// callee: `(atom, language, method, companion callee)`.
const METHOD_GATES: [(&str, &str, &str, &str); 1] =
    [("net.listen", "python", "listen", "socket.socket")];

/// One observed use of an atom.
#[derive(Clone, Debug)]
struct Use {
    atom: &'static str,
    file: String,
    line: Option<u32>,
    callee: String,
    /// False when the receiver type did not resolve: a May use whoever owns the code.
    certain: bool,
}

impl Use {
    fn site(&self) -> String {
        match self.line {
            Some(l) => format!("{}:{l} {}", self.file, self.callee),
            None => format!("{} {}", self.file, self.callee),
        }
    }
}

/// Uses by node anchor: `lo` from Must-owned code, `hi` only from May-owned code.
#[derive(Default)]
struct Uses {
    lo: BTreeMap<String, Vec<Use>>,
    hi: BTreeMap<String, Vec<Use>>,
}

/// Why CAP001 and CAP002 have no subject: no node owns code, so no cell exists.
pub fn caps_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    let owns = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Node && !e.external && e.owns_code());
    (!owns).then_some("no node owns code, so no use can be observed")
}

fn callee_of(text: &str) -> &str {
    text.strip_suffix("(..)").unwrap_or(text)
}

/// Crates whose `Command` is a builder type, not a process: `clap::Command::new` names a CLI
/// command and must not match the `Command::new` spawn entry behind its extra leading segments.
const NON_PROCESS_CRATES: &[&str] = &["clap"];

/// True when the written `callee` names the vocabulary entry `name` (a Rust path entry also
/// matches behind extra leading segments: `std::fs::read` names `fs::read`, but a path rooted
/// in a `NON_PROCESS_CRATES` crate names nothing).
fn names_callee(lang: &str, names: &BTreeSet<&str>, callee: &str) -> bool {
    if names.contains(callee) {
        return true;
    }
    lang == "rust"
        && !callee
            .split_once("::")
            .is_some_and(|(root, _)| NON_PROCESS_CRATES.contains(&root))
        && names
            .iter()
            .any(|n| n.contains("::") && callee.ends_with(&format!("::{n}")))
}

/// One atom a call may use and whether the call certainly does.
struct Hit {
    atom: &'static str,
    certain: bool,
}

/// The atoms whose vocabulary in `lang` names the call `callee`, given the calls `file_calls` of
/// its file and the lazily computed type of its receiver.
fn atoms_of(
    lang: &str,
    callee: &str,
    file_calls: &BTreeSet<String>,
    receiver_is_path: &mut dyn FnMut(&str) -> bool,
) -> Vec<Hit> {
    let mut out = Vec::new();
    for a in atoms() {
        let Answer::Exact(names) = callee_vocab(lang, a.name) else {
            continue;
        };
        if names_callee(lang, &names, callee) {
            out.push(Hit {
                atom: a.name,
                certain: true,
            });
            continue;
        }
        let Some((recv, m)) = callee.rsplit_once('.') else {
            continue;
        };
        if !names.contains(format!(".{m}").as_str()) {
            continue;
        }
        let gated = METHOD_GATES
            .iter()
            .any(|(atom, l, method, _)| *atom == a.name && *l == lang && *method == m);
        if gated {
            let open = METHOD_GATES.iter().any(|(atom, l, method, gate)| {
                *atom == a.name && *l == lang && *method == m && file_calls.contains(*gate)
            });
            if open {
                out.push(Hit {
                    atom: a.name,
                    certain: true,
                });
            }
        } else if names.contains(format!("Path.{m}").as_str()) && receiver_is_path(recv) {
            out.push(Hit {
                atom: a.name,
                certain: true,
            });
        } else {
            tracing::debug!(
                callee,
                atom = a.name,
                "vocabulary method on an unresolved receiver: May"
            );
            out.push(Hit {
                atom: a.name,
                certain: false,
            });
        }
    }
    out
}

/// Python receiver typing: is the expression `recv` a `pathlib.Path`? Textual and per file.
mod pytype {
    /// Methods and attributes that keep a `Path` a `Path`.
    const KEEPS: [&str; 14] = [
        "resolve",
        "absolute",
        "parent",
        "parents",
        "joinpath",
        "with_name",
        "with_suffix",
        "with_stem",
        "expanduser",
        "relative_to",
        "readlink",
        "home",
        "cwd",
        "samefile",
    ];

    fn is_ident(c: char) -> bool {
        c.is_alphanumeric() || c == '_'
    }

    /// The index just past the bracket group opening at byte `at` of `s`, honouring quotes.
    fn skip_group(s: &str, at: usize) -> Option<usize> {
        let mut depth = 0usize;
        let mut quote: Option<char> = None;
        for (i, c) in s[at..].char_indices() {
            match quote {
                Some(q) => {
                    if c == q {
                        quote = None;
                    }
                }
                None => match c {
                    '"' | '\'' => quote = Some(c),
                    '(' | '[' | '{' => depth += 1,
                    ')' | ']' | '}' => {
                        depth = depth.checked_sub(1)?;
                        if depth == 0 {
                            return Some(at + i + c.len_utf8());
                        }
                    }
                    _ => {}
                },
            }
        }
        None
    }

    /// Split `s` on top-level `/` (true division, not `//`).
    fn split_div(s: &str) -> Vec<&str> {
        let mut parts = Vec::new();
        let (mut last, mut i) = (0, 0);
        let b = s.as_bytes();
        while i < b.len() {
            match b[i] {
                b'(' | b'[' | b'{' => match skip_group(s, i) {
                    Some(end) => {
                        i = end;
                        continue;
                    }
                    None => return vec![s],
                },
                b'"' | b'\'' => {
                    let q = b[i];
                    i += 1;
                    while i < b.len() && b[i] != q {
                        i += 1;
                    }
                }
                b'/' if b.get(i + 1) != Some(&b'/') && i > 0 && b[i - 1] != b'/' => {
                    parts.push(&s[last..i]);
                    last = i + 1;
                }
                _ => {}
            }
            i += 1;
        }
        parts.push(&s[last..]);
        parts
    }

    /// True when `e` is a `Path(..)` / `Path.home()` head followed only by Path-keeping steps.
    fn path_chain(e: &str) -> bool {
        let rest = ["pathlib.Path", "Path"]
            .iter()
            .find_map(|h| e.strip_prefix(h))
            .filter(|r| !r.starts_with(is_ident));
        let Some(mut rest) = rest else { return false };
        loop {
            rest = rest.trim_start();
            if rest.is_empty() {
                return true;
            }
            if rest.starts_with('(') {
                let Some(end) = skip_group(rest, 0) else {
                    return false;
                };
                rest = &rest[end..];
                continue;
            }
            let Some(after) = rest.strip_prefix('.') else {
                return false;
            };
            let n = after.find(|c: char| !is_ident(c)).unwrap_or(after.len());
            if !KEEPS.contains(&&after[..n]) {
                return false;
            }
            rest = &after[n..];
        }
    }

    /// The right-hand sides and annotations evidencing `name` in `src`: `(is_path, is_evidence)`.
    fn evidence(src: &str, name: &str, depth: usize) -> Vec<bool> {
        let mut out = Vec::new();
        let mut lines = src.lines().peekable();
        while let Some(line) = lines.next() {
            let t = line.trim_start();
            let Some(after) = t.strip_prefix(name).filter(|r| !r.starts_with(is_ident)) else {
                continue;
            };
            let after = after.trim_start();
            let (ann, rest) = match after.strip_prefix(':') {
                Some(a) => match a.split_once('=') {
                    Some((ann, rhs)) if !rhs.starts_with('=') => (Some(ann.trim()), Some(rhs)),
                    _ => (Some(a.trim().trim_end_matches(',')), None),
                },
                None => (
                    None,
                    after.strip_prefix('=').filter(|r| !r.starts_with('=')),
                ),
            };
            if ann.is_none() && rest.is_none() {
                continue;
            }
            if let Some(ann) = ann {
                if ann == "Path" || ann == "pathlib.Path" {
                    out.push(true);
                    continue;
                }
                if rest.is_none() {
                    // `name: Other` in a signature or bare annotation
                    out.push(false);
                    continue;
                }
            }
            let mut rhs = rest.unwrap_or("").to_owned();
            while skip_group_balanced(&rhs).is_none() {
                match lines.next() {
                    Some(l) => {
                        rhs.push(' ');
                        rhs.push_str(l.trim());
                    }
                    None => break,
                }
            }
            out.push(is_path_expr(src, &rhs, depth + 1));
        }
        // `name: Path` inside a single-line signature
        for pat in [format!("{name}: Path"), format!("{name}: pathlib.Path")] {
            for (i, _) in src.match_indices(&pat) {
                let before_ok = !src[..i].ends_with(is_ident);
                let after_ok = !src[i + pat.len()..].starts_with(is_ident);
                let line_start = src[..i].rsplit('\n').next().unwrap_or("").trim().is_empty();
                if before_ok && after_ok && !line_start {
                    out.push(true);
                }
            }
        }
        out
    }

    fn skip_group_balanced(s: &str) -> Option<()> {
        let mut depth = 0i32;
        let mut quote: Option<char> = None;
        for c in s.chars() {
            match quote {
                Some(q) if c == q => quote = None,
                Some(_) => {}
                None => match c {
                    '"' | '\'' => quote = Some(c),
                    '(' | '[' | '{' => depth += 1,
                    ')' | ']' | '}' => depth -= 1,
                    _ => {}
                },
            }
        }
        (depth <= 0).then_some(())
    }

    /// True when the expression `expr` evaluates to a `pathlib.Path` as far as `src` shows.
    pub(super) fn is_path_expr(src: &str, expr: &str, depth: usize) -> bool {
        if depth > 4 || !src.contains("pathlib") {
            return false;
        }
        let e = expr.trim();
        let e = e.split('#').next().unwrap_or(e).trim();
        if let Some(inner) = e
            .strip_prefix('(')
            .filter(|_| skip_group(e, 0) == Some(e.len()))
        {
            return is_path_expr(src, inner.strip_suffix(')').unwrap_or(inner), depth + 1);
        }
        let parts = split_div(e);
        if parts.len() > 1 {
            return parts.iter().any(|p| is_path_expr(src, p, depth + 1));
        }
        if path_chain(e) {
            return true;
        }
        if !e.is_empty() && e.chars().all(is_ident) {
            let ev = evidence(src, e, depth);
            return !ev.is_empty() && ev.iter().all(|p| *p);
        }
        false
    }
}

fn observe(cx: &Cx<'_>) -> Uses {
    let edges: Vec<_> = cx
        .graph
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.to.is_none())
        .collect();
    let mut calls_in: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for e in &edges {
        if let Some(t) = &e.text {
            calls_in
                .entry(e.from.path().to_owned())
                .or_default()
                .insert(callee_of(t).to_owned());
        }
    }
    let empty = BTreeSet::new();
    let mut sources: BTreeMap<String, Option<String>> = BTreeMap::new();
    let mut uses = Uses::default();
    for e in &edges {
        let Some(text) = &e.text else { continue };
        let from = e.from.to_string();
        let Some(uo) = cx.owners.units.get(&from) else {
            continue;
        };
        let callee = callee_of(text);
        let Some(code) = cx.code.file(&uo.file) else {
            continue;
        };
        let file_calls = calls_in.get(&uo.file).unwrap_or(&empty);
        // A cut-off callee text cannot be split; fall back to the spelled method name.
        let spelled;
        let callee = if callee.ends_with("...") {
            spelled = format!("?.{}", e.name.as_deref().unwrap_or(""));
            spelled.as_str()
        } else {
            callee
        };
        let mut is_path = |recv: &str| {
            code.language == "python"
                && sources
                    .entry(uo.file.clone())
                    .or_insert_with(|| code.source())
                    .as_deref()
                    .is_some_and(|src| pytype::is_path_expr(src, recv, 0))
        };
        for Hit { atom, certain } in atoms_of(&code.language, callee, file_calls, &mut is_path) {
            let u = Use {
                atom,
                file: uo.file.clone(),
                line: e.line,
                callee: callee.to_owned(),
                certain,
            };
            match &uo.merged.owner {
                Owner::Must(n) if !certain => {
                    uses.hi.entry(n.as_str().to_owned()).or_default().push(u);
                }
                Owner::Must(n) => uses.lo.entry(n.as_str().to_owned()).or_default().push(u),
                Owner::May(ns) => {
                    for n in ns {
                        uses.hi
                            .entry(n.as_str().to_owned())
                            .or_default()
                            .push(u.clone());
                    }
                }
                Owner::Unknown(_) | Owner::Foreign => {}
            }
        }
    }
    tracing::info!(
        must_nodes = uses.lo.len(),
        may_nodes = uses.hi.len(),
        "capability uses observed"
    );
    uses
}

/// True when `grant` covers `atom` (the atom itself or its parent) at `file`.
fn covers(cx: &Cx<'_>, grant: &Grant, atom: &str, file: &str) -> bool {
    let granted = gob_ir::registry::canonical(&grant.atom).unwrap_or(&grant.atom);
    let named = granted == atom
        || atom
            .strip_prefix(granted)
            .is_some_and(|rest| rest.starts_with('.'));
    named
        && grant.at.as_ref().is_none_or(|sel| {
            select_files(sel, &cx.code.walk)
                .iter()
                .any(|m| m.path == file)
        })
}

fn list(uses: &[&Use]) -> String {
    let mut s = uses
        .iter()
        .take(EXAMPLES)
        .map(|u| u.site())
        .collect::<Vec<_>>()
        .join("; ");
    if uses.len() > EXAMPLES {
        let _ = write!(s, " (+{} more)", uses.len() - EXAMPLES);
    }
    s
}

fn cap001(cx: &Cx<'_>, uses: &Uses, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        let site = Some((e.file.as_str(), (e.span.start, e.span.end)));
        out.count("CAP001", 1);
        for (set, must) in [(&uses.lo, true), (&uses.hi, false)] {
            let Some(found) = set.get(&e.anchor) else {
                continue;
            };
            // (atom, receiver unresolved) -> uses; an unresolved receiver is a May use.
            let mut by_atom: BTreeMap<(&str, bool), Vec<&Use>> = BTreeMap::new();
            for u in found {
                if !e.grants.iter().any(|g| covers(cx, g, u.atom, &u.file)) {
                    by_atom.entry((u.atom, !u.certain)).or_default().push(u);
                }
            }
            for ((atom, unresolved_receiver), us) in by_atom {
                if must && !unresolved_receiver {
                    let anchor = format!("cap/{}/{atom}", e.anchor);
                    out.fire(
                        "CAP001",
                        Severity::Error,
                        format!(
                            "`{}` uses `{atom}` with no grant ({} use(s)): {}",
                            e.anchor,
                            us.len(),
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                } else if unresolved_receiver {
                    let anchor = format!("cap/{}/{atom}/receiver", e.anchor);
                    out.unresolved(
                        "CAP001",
                        Reason::UnresolvedEdge,
                        &format!(
                            "`{atom}` may be used by `{}` with no grant; the receiver type of the call could not be resolved: {}",
                            e.anchor,
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                } else {
                    let anchor = format!("cap/{}/{atom}", e.anchor);
                    out.unresolved(
                        "CAP001",
                        Reason::MayOnlyOwner,
                        &format!(
                            "`{atom}` may be used by `{}` with no grant; the code is owned only at May: {}",
                            e.anchor,
                            list(&us)
                        ),
                        &anchor,
                        site,
                    );
                }
            }
        }
    }
}

/// The registered atoms a grant of `granted` covers: itself and its children.
fn expansion(granted: &str) -> Vec<&'static str> {
    atoms()
        .into_iter()
        .map(|a| a.name)
        .filter(|n| *n == granted || n.strip_prefix(granted).is_some_and(|r| r.starts_with('.')))
        .collect()
}

fn cap002(cx: &Cx<'_>, uses: &Uses, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        // A node without grants is still a subject: its cells are all `denied`, nothing to judge.
        out.count("CAP002", usize::from(e.grants.is_empty()));
        // The files of every unit the node owns, and whether any unit is only possibly its.
        let mut files: BTreeSet<&str> = BTreeSet::new();
        let mut may_owned = false;
        for uo in cx.owners.units.values() {
            match &uo.merged.owner {
                Owner::Must(n) if n.as_str() == e.anchor => {
                    files.insert(uo.file.as_str());
                }
                Owner::May(ns) if ns.iter().any(|n| n.as_str() == e.anchor) => may_owned = true,
                _ => {}
            }
        }
        let langs: BTreeSet<&str> = files
            .iter()
            .filter_map(|f| cx.code.file(f))
            .map(|f| f.language.as_str())
            .collect();
        let unseen = files
            .iter()
            .filter_map(|f| cx.code.file(f))
            .any(CodeFile::has_unseen);
        for g in &e.grants {
            out.count("CAP002", 1);
            let site = Some((g.file.as_str(), (g.span.start, g.span.end)));
            let atoms = expansion(gob_ir::registry::canonical(&g.atom).unwrap_or(&g.atom));
            if atoms.is_empty() || files.is_empty() {
                tracing::debug!(node = %e.anchor, atom = %g.atom, "grant has no detectable atom or no owned code; not judged");
                continue;
            }
            let in_scope = |f: &str| {
                g.at.as_ref()
                    .is_none_or(|sel| select_files(sel, &cx.code.walk).iter().any(|m| m.path == f))
            };
            let observed = [&uses.lo, &uses.hi].iter().any(|by_node| {
                by_node.get(&e.anchor).is_some_and(|us| {
                    us.iter()
                        .any(|u| atoms.contains(&u.atom) && in_scope(&u.file))
                })
            });
            if observed {
                continue;
            }
            let covered = atoms.iter().all(|a| {
                langs.iter().all(|l| match detectors(a, l) {
                    Answer::Exact(kinds) => !kinds.contains(&DetectorKind::Lexical),
                    Answer::NotApplicable => true,
                    _ => false,
                })
            });
            if may_owned || unseen || !covered {
                tracing::debug!(node = %e.anchor, atom = %g.atom, may_owned, unseen, covered, "grant not judged: absence is not Exact");
                continue;
            }
            out.fire(
                "CAP002",
                Severity::Warn,
                format!(
                    "`{}` grants `{}` but no use of it is observed in the code it owns",
                    e.anchor, g.written
                ),
                &format!("cap/{}/{}", e.anchor, g.atom),
                site,
            );
        }
    }
}

/// Evaluate CAP001 and CAP002 over the observed uses and the node grants.
pub fn evaluate(cx: &Cx<'_>, out: &mut Output) {
    let uses = observe(cx);
    cap001(cx, &uses, out);
    cap002(cx, &uses, out);
    tracing::info!(
        cap001 = out.subjects.get("CAP001").copied().unwrap_or(0),
        cap002 = out.subjects.get("CAP002").copied().unwrap_or(0),
        "CAP rules evaluated"
    );
}
