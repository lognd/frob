//! CAP001 (through `grimble_capabilities::build`) and CAP002: the capability cell of a node, from observed uses and its `may` grants.
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
//! Import resolution (ticket D36SRKP): besides the call graph, `gob_symbols::path_uses` resolves
//! each call and each function-valued reference through `use ... as`, from-imports, `let` and
//! assignment aliases, literal `getattr` / `import_module` (a May use, never CAP001) and explicit
//! `std::` / `tokio::` roots (which a repository type named `Command` cannot hide). Not resolved:
//! glob imports, macro bodies, computed attribute names.
//!
//! Known limits: receiver typing is per file and textual (no cross-module constants, no
//! shadowing by unannotated parameters); `open(..)` is `fs.read` whatever its mode; the template excuses and CAP004 (packs.md 6.7) are computed by `grimble_capabilities::excuse` but not yet emitted here; the pack
//! severity table is not consulted (CAP001 is an Error, CAP002 a Warning).
//!
//! `may` arguments (ticket 5X9CAQE): a grant `may fs.read("config/**")` covers a use only when the
//! use's argument is statically known and `grimble_model::args::judge` matches it against a grant
//! argument. The argument is folded by `gob_symbols::call_args` (literals, concatenations,
//! single-assignment constants, tuples, path wrappers). A known argument outside every covering
//! grant argument is CAP001 (Error) naming both. An argument that cannot be folded, a use through
//! a receiver (`Path(..).read_text()`), or an atom a pack declares is Unresolved with reason
//! `unresolved-edge`, never clean. Paths are compared lexically (symlinks are not followed).
//!
//! Grant scope (ticket M64HENY): a grant's `at` selector is judged against the unit of the use
//! (the call edge's from-symbol) and its enclosing symbols, not its file. `at "f.rs::allowed"`
//! covers a use in `allowed` and in anything nested in it, and a use in a sibling function of
//! the same file is CAP001. CAP002 asks whether any use falls inside the selected units.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9
// frob:ticket 01M4HEMAM737MTY3385G7VKXQ4
// frob:ticket 01M59RWT16TFNSACMMTTXX200T
// frob:ticket 01M5XNNHBSPSM5XFG8FM64HENY
// frob:ticket 01M5XNNHJ0ES2PB6ZKAD36SRKP
// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use gob_ir::Answer;
use gob_ir::registry::{DetectorKind, atoms, callee_vocab, detectors};
use gob_rules::Severity;
use gob_symbols::{EdgeKind, Target};
use gob_walk::{Owner, selects_unit_or_enclosing};
use grimble_capabilities::{Cell, NodeInput};
use grimble_model::args::{ArgKind, Judgement, arg_kind, judge};
use grimble_model::ast::EntityKind;
use grimble_model::{PackDetectorKind, PackPin};

use crate::code::CodeFile;
use crate::eval::{Cx, Output};
use crate::model::Grant;
use crate::types::Reason;

/// How many example call sites one finding names.
const EXAMPLES: usize = 3;

/// A method-name vocabulary entry (`.listen`) counts only in a file that also calls the gate
/// callee: `(atom, language, method, companion callee)`.
const METHOD_GATES: [(&str, &str, &str, &str); 2] = [
    ("net.listen", "python", "listen", "socket.socket"),
    ("net.connect", "python", "connect", "socket.socket"),
];

/// One observed use of an atom.
#[derive(Clone, Debug)]
struct Use {
    atom: String,
    file: String,
    /// The from-symbol of the call edge as text: the unit the use sits in.
    unit: String,
    /// The qualname segments of that unit (empty for module-level code).
    qual: Vec<String>,
    line: Option<u32>,
    callee: String,
    /// False when the receiver type did not resolve: a May use whoever owns the code.
    certain: bool,
    /// The statically known argument the call passes (see `attach_args`); `None` when it does not
    /// fold, which an argument-scoped grant can never clear.
    arg: Option<String>,
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
    atom: String,
    certain: bool,
}

/// Every atom with a callee vocabulary in `lang` and that vocabulary: the shared registry's atoms
/// and the atoms of the enabled repository packs whose detector row is a `callee` row.
fn vocabularies<'a>(
    lang: &str,
    packs: &'a BTreeMap<String, PackPin>,
) -> Vec<(&'a str, BTreeSet<&'a str>)> {
    let mut out: Vec<(&'a str, BTreeSet<&'a str>)> = Vec::new();
    for a in atoms() {
        if let Answer::Exact(names) = callee_vocab(lang, a.name) {
            out.push((a.name, names));
        }
    }
    for d in packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .filter(|d| d.kind == PackDetectorKind::Callee && d.lang == lang)
    {
        let names = d.names.iter().map(String::as_str);
        match out.iter_mut().find(|(a, _)| *a == d.atom) {
            Some((_, have)) => have.extend(names),
            None => out.push((d.atom.as_str(), names.collect())),
        }
    }
    out
}

/// The atoms whose vocabulary in `lang` names the call `callee`, given the calls `file_calls` of
/// its file and the lazily computed type of its receiver.
fn atoms_of(
    vocabs: &[(&str, BTreeSet<&str>)],
    lang: &str,
    callee: &str,
    file_calls: &BTreeSet<String>,
    receiver_is_path: &mut dyn FnMut(&str) -> bool,
) -> Vec<Hit> {
    let mut out = Vec::new();
    for (atom, names) in vocabs {
        let atom = *atom;
        if names_callee(lang, names, callee) {
            out.push(Hit {
                atom: atom.to_owned(),
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
            .any(|(m_atom, l, method, _)| *m_atom == atom && *l == lang && *method == m);
        if gated {
            let open = METHOD_GATES.iter().any(|(m_atom, l, method, gate)| {
                *m_atom == atom && *l == lang && *method == m && file_calls.contains(*gate)
            });
            if open {
                out.push(Hit {
                    atom: atom.to_owned(),
                    certain: true,
                });
            }
        } else if names.contains(format!("Path.{m}").as_str()) && receiver_is_path(recv) {
            out.push(Hit {
                atom: atom.to_owned(),
                certain: true,
            });
        } else {
            tracing::debug!(
                callee,
                atom,
                "vocabulary method on an unresolved receiver: May"
            );
            out.push(Hit {
                atom: atom.to_owned(),
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

/// Files an owner `Must` claims go to `lo` when certain, else `hi`; `May` owners get `hi`.
fn route(uses: &mut Uses, owner: &Owner, u: Use) {
    match owner {
        Owner::Must(n) if !u.certain => {
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

/// The last path segment of a vocabulary name (`fs::read` -> `read`, `subprocess.run` -> `run`).
fn last_segment(name: &str) -> &str {
    let name = name.trim_start_matches('.');
    name.rsplit(['.', ':']).next().unwrap_or(name)
}

/// The ownership unit holding byte `offset` of a file: its innermost symbol that is a unit, else
/// the file unit. Returns the unit's symref text and qualname segments.
fn unit_at(
    cx: &Cx<'_>,
    symbols: &gob_symbols::FileSymbols,
    file_unit: &str,
    offset: usize,
) -> (String, Vec<String>) {
    let width = |s: &gob_symbols::SymbolRecord| u32::from(s.span.end()) - u32::from(s.span.start());
    let holder = symbols
        .symbols
        .iter()
        .filter(|s| {
            usize::try_from(u32::from(s.span.start())).is_ok_and(|a| a <= offset)
                && usize::try_from(u32::from(s.span.end())).is_ok_and(|b| offset < b)
        })
        .filter(|s| cx.owners.units.contains_key(&s.symref.to_string()))
        .min_by_key(|s| width(s));
    match holder {
        Some(s) => (
            s.symref.to_string(),
            match s.symref.target() {
                Target::Symbol(segs) => segs.clone(),
                _ => Vec::new(),
            },
        ),
        None => (file_unit.to_owned(), Vec::new()),
    }
}

/// Uses found by import resolution (ticket D36SRKP): calls and function values whose written
/// path names a vocabulary entry only through an alias, a from-import, a `let` binding, a literal
/// `getattr` / `import_module`, or an explicit `std::` / `tokio::` root that a same-named
/// repository item hides from the call graph. Added to `uses` unless the call-graph pass already
/// recorded the same atom on the same line of the same unit.
fn scan_resolved(cx: &Cx<'_>, uses: &mut Uses) {
    // (file, line, name) of every call the graph resolved inside the repository
    let mut local: BTreeSet<(String, u32, String)> = BTreeSet::new();
    for e in cx.graph.edges_with_status() {
        if e.kind == EdgeKind::Calls
            && e.to.is_some()
            && let (Some(l), Some(n)) = (e.line, e.name.as_ref())
        {
            local.insert((e.from.path().to_owned(), l, n.clone()));
        }
    }
    let seen: BTreeSet<(String, Option<u32>, String, bool)> = {
        let mut set = BTreeSet::new();
        for (_, us) in uses.lo.iter().chain(uses.hi.iter()) {
            for u in us {
                set.insert((u.unit.clone(), u.line, u.atom.clone(), u.certain));
            }
        }
        set
    };
    let mut seen = seen;
    let files: BTreeSet<&str> = cx.owners.units.values().map(|u| u.file.as_str()).collect();
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
    let mut added = 0usize;
    for path in files {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if !matches!(code.language.as_str(), "rust" | "python") {
            continue;
        }
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        let Some(src) = code.source() else { continue };
        // cheap prefilter: some vocabulary name's last segment must occur in the file at all
        if !vocab
            .iter()
            .any(|(_, names)| names.iter().any(|n| src.contains(last_segment(n))))
        {
            continue;
        }
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for pu in gob_symbols::path_uses(&code.language, &src) {
            if !pu.external_root
                && !pu.dynamic
                && local.contains(&(
                    path.to_owned(),
                    pu.line,
                    last_segment(&pu.spelled).to_owned(),
                ))
            {
                tracing::debug!(file = path, line = pu.line, spelled = %pu.spelled, "resolved path is a repository item");
                continue;
            }
            let hits: Vec<&str> = vocab
                .iter()
                .filter(|(_, names)| names_callee(&code.language, names, &pu.path))
                .map(|(a, _)| *a)
                .collect();
            if hits.is_empty() {
                continue;
            }
            let (unit, qual) = unit_at(cx, symbols, &file_unit, pu.offset);
            let Some(uo) = cx.owners.units.get(&unit) else {
                tracing::debug!(file = path, unit = %unit, "resolved use has no ownership unit");
                continue;
            };
            let certain = !pu.dynamic;
            for atom in hits {
                if !seen.insert((unit.clone(), Some(pu.line), atom.to_owned(), certain)) {
                    continue;
                }
                tracing::debug!(file = path, line = pu.line, atom, callee = %pu.path, certain, "resolved capability use");
                added += 1;
                route(
                    uses,
                    &uo.merged.owner,
                    Use {
                        atom: atom.to_owned(),
                        file: path.to_owned(),
                        unit: unit.clone(),
                        qual: qual.clone(),
                        line: Some(pu.line),
                        callee: pu.path.clone(),
                        certain,
                        arg: None,
                    },
                );
            }
        }
    }
    tracing::info!(added, "import-resolved capability uses added");
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
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
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
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        for Hit { atom, certain } in
            atoms_of(vocab, &code.language, callee, file_calls, &mut is_path)
        {
            let u = Use {
                atom,
                file: uo.file.clone(),
                unit: from.clone(),
                qual: match e.from.target() {
                    Target::Symbol(segs) => segs.clone(),
                    _ => Vec::new(),
                },
                line: e.line,
                callee: callee.to_owned(),
                certain,
                arg: None,
            };
            route(&mut uses, &uo.merged.owner, u);
        }
    }
    scan_resolved(cx, &mut uses);
    attach_args(cx, &mut uses);
    tracing::info!(
        must_nodes = uses.lo.len(),
        may_nodes = uses.hi.len(),
        "capability uses observed"
    );
    uses
}

/// True when `sel` covers the unit a use sits in, or an enclosing symbol of it.
fn selects_use(sel: &gob_walk::Selector, u: &Use) -> bool {
    selects_unit_or_enclosing(sel, &u.file, &u.qual)
}

/// The first token of a shell string, or `None` when it holds a shell metacharacter and so may run
/// something else.
fn shell_program(cmd: &str) -> Option<String> {
    if cmd.contains([';', '|', '&', '$', '`', '<', '>', '(', ')', '\n']) {
        return None;
    }
    cmd.split_whitespace().next().map(str::to_owned)
}

/// The host pattern text of an observed `(host, port)` pair, bracketing an IPv6 host.
fn host_port(host: &str, port: Option<&str>) -> String {
    let host = if host.contains(':') && !host.starts_with('[') {
        format!("[{host}]")
    } else {
        host.to_owned()
    };
    match port {
        Some(p) => format!("{host}:{p}"),
        None => host,
    }
}

/// The argument a call passes, as the string `judge` compares, for an atom of `kind`.
fn observed_arg(kind: ArgKind, call: &gob_symbols::CallArgs) -> Option<String> {
    use gob_symbols::ArgValue;
    let first = call.args.first()?.as_ref()?;
    match (kind, first) {
        (ArgKind::Path | ArgKind::EnvName | ArgKind::Host, ArgValue::Str(s)) => Some(s.clone()),
        (ArgKind::Binary, ArgValue::Str(s)) => shell_program(s),
        (ArgKind::Binary, ArgValue::Seq(v)) => v.first().cloned().flatten(),
        (ArgKind::Host, ArgValue::Seq(v)) if v.len() == 2 => {
            let host = v[0].as_deref()?;
            Some(host_port(host, v[1].as_deref()))
        }
        _ => None,
    }
}

/// True when the vocabulary entry reaches the call through a receiver, so the first call argument
/// is not the path, name or program the atom is about (`Path.read_text`, `.read_text`).
fn receiver_entry(callee: &str) -> bool {
    callee.starts_with("Path.") || callee.starts_with('.') || callee.starts_with("?.")
}

/// Fill `Use::arg` for the uses an argument-scoped grant could judge: parse each file once and
/// match a use to the one call on its line with the same last callee segment. An ambiguous line
/// (two such calls with different arguments), a missing call or an unfoldable argument leaves
/// `None`. Does nothing when no grant carries arguments.
fn attach_args(cx: &Cx<'_>, uses: &mut Uses) {
    let scoped = cx
        .model
        .entities
        .values()
        .any(|e| e.grants.iter().any(|g| !g.args.is_empty()));
    if !scoped {
        return;
    }
    let mut parsed: BTreeMap<String, BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>>> =
        BTreeMap::new();
    let (mut known, mut unknown) = (0usize, 0usize);
    for u in uses.lo.values_mut().chain(uses.hi.values_mut()).flatten() {
        let Some(kind) = arg_kind(&u.atom) else {
            continue;
        };
        let Some(line) = u.line else { continue };
        if kind != ArgKind::Host && receiver_entry(&u.callee) {
            unknown += 1;
            continue;
        }
        let Some(code) = cx.code.file(&u.file) else {
            continue;
        };
        let calls = parsed.entry(u.file.clone()).or_insert_with(|| {
            let mut m: BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>> = BTreeMap::new();
            if let Some(src) = code.source() {
                for c in gob_symbols::call_args(&code.language, &src) {
                    m.entry((c.line, last_segment(&c.callee).to_owned()))
                        .or_default()
                        .push(c);
                }
            }
            m
        });
        let Some(cands) = calls.get(&(line, last_segment(&u.callee).to_owned())) else {
            unknown += 1;
            continue;
        };
        let vals: BTreeSet<Option<String>> = cands.iter().map(|c| observed_arg(kind, c)).collect();
        if vals.len() == 1 {
            u.arg = vals.into_iter().next().flatten();
        }
        if u.arg.is_some() {
            known += 1;
        } else {
            unknown += 1;
        }
    }
    tracing::info!(known, unknown, "call arguments attached to uses");
}

/// How the grants of a node judge one use.
#[derive(Clone, Debug, PartialEq, Eq)]
enum Coverage {
    /// No grant names the atom in the use's unit.
    Uncovered,
    /// A grant with no arguments, or an argument the use satisfies.
    Covered,
    /// Argument-scoped grants cover the atom and unit, but the observed argument matches none.
    Mismatch {
        observed: String,
        granted: Vec<String>,
    },
    /// Argument-scoped grants cover the atom and unit and the argument is not statically known.
    Unknown { granted: Vec<String> },
}

/// The `Judgement` of the use against one argument-scoped grant: any grant argument that matches
/// is `Match`; otherwise `Unknown` if any could not be decided or the use has no folded argument.
fn judge_use(grant: &Grant, atom: &str, u: &Use) -> Judgement {
    let (Some(kind), Some(obs)) = (arg_kind(atom), u.arg.as_deref()) else {
        return Judgement::Unknown;
    };
    let mut out = Judgement::NoMatch;
    for a in &grant.args {
        match judge(kind, a, obs) {
            Judgement::Match => return Judgement::Match,
            Judgement::Unknown => out = Judgement::Unknown,
            Judgement::NoMatch => {}
        }
    }
    out
}

/// Fold the grants of a node into one `Coverage` of the use `u` of `atom`.
fn coverage(grants: &[Grant], atom: &str, u: &Use) -> Coverage {
    let mut granted: Vec<String> = Vec::new();
    let mut unknown = false;
    for g in grants.iter().filter(|g| covers(g, atom, u)) {
        if g.args.is_empty() {
            return Coverage::Covered;
        }
        match judge_use(g, atom, u) {
            Judgement::Match => return Coverage::Covered,
            Judgement::Unknown => unknown = true,
            Judgement::NoMatch => {}
        }
        granted.extend(g.args.iter().cloned());
    }
    if granted.is_empty() {
        return Coverage::Uncovered;
    }
    match (&u.arg, unknown) {
        (Some(observed), false) => Coverage::Mismatch {
            observed: observed.clone(),
            granted,
        },
        _ => Coverage::Unknown { granted },
    }
}

/// True when `grant` covers the use `u` of `atom` (the atom itself or its parent) in its unit,
/// whatever its arguments say.
fn covers(grant: &Grant, atom: &str, u: &Use) -> bool {
    let granted = gob_ir::registry::canonical(&grant.atom).unwrap_or(&grant.atom);
    let named = granted == atom
        || atom
            .strip_prefix(granted)
            .is_some_and(|rest| rest.starts_with('.'));
    named && grant.at.as_ref().is_none_or(|sel| selects_use(sel, u))
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

/// The `(node anchor, atom, file)` triples the capability matrix marks `undeclared` (or `unknown`:
/// the callee vocabulary matched but no registry detector row exists, e.g. a pack atom) from the
/// certain uses in Must-owned code. Coverage is decided per use site (binding.md 7.2 item 3): a
/// grant that covers the atom in one unit never masks the same atom used in another unit. The
/// third element is the use's unit (its from-symbol), not its file.
fn matrix_undeclared(cx: &Cx<'_>, uses: &Uses) -> BTreeSet<(String, String, String)> {
    let mut out = BTreeSet::new();
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        let Some(found) = uses.lo.get(&e.anchor) else {
            continue;
        };
        // One matrix input per (file, language) of the node's used code, so each use is judged
        // against the grants that cover it at its own file.
        let mut inputs: BTreeMap<(&str, &str), NodeInput> = BTreeMap::new();
        for u in found.iter().filter(|u| u.certain) {
            let Some(lang) = cx.code.file(&u.file).map(|c| c.language.as_str()) else {
                continue;
            };
            let input = inputs
                .entry((u.unit.as_str(), lang))
                .or_insert_with(|| NodeInput {
                    node: e.anchor.clone(),
                    lang: lang.to_owned(),
                    ..NodeInput::default()
                });
            input.uses.insert(u.atom.clone());
            // An argument-scoped grant that names the atom keeps the cell declared; CAP001
            // judges its argument separately.
            if coverage(&e.grants, &u.atom, u) != Coverage::Uncovered {
                input.grants.insert(u.atom.clone());
            }
        }
        for ((unit, _), input) in inputs {
            let atoms: Vec<String> = input.uses.iter().cloned().collect();
            let atoms: Vec<&str> = atoms.iter().map(String::as_str).collect();
            let matrix = grimble_capabilities::build(&[input], &atoms);
            for (atom, cell) in matrix.cells.values().flatten() {
                if matches!(cell, Cell::Undeclared | Cell::Unknown) {
                    out.insert((e.anchor.clone(), atom.clone(), unit.to_owned()));
                }
            }
        }
    }
    tracing::debug!(cells = out.len(), "matrix undeclared cells");
    out
}

/// Argument findings keyed by (atom, observed argument or None when unfolded, granted arguments).
type ByArg<'a> = BTreeMap<(&'a str, Option<String>, Vec<String>), Vec<&'a Use>>;

#[allow(clippy::too_many_lines)] // one pass per node: exact, argument and may findings together
fn cap001(cx: &Cx<'_>, uses: &Uses, out: &mut Output) {
    let undeclared = matrix_undeclared(cx, uses);
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
            // argument findings: (atom, observed, granted) -> uses; observed None is unfolded
            let mut by_arg: ByArg<'_> = BTreeMap::new();
            for u in found {
                match coverage(&e.grants, &u.atom, u) {
                    Coverage::Covered => {}
                    Coverage::Mismatch { observed, granted } => by_arg
                        .entry((u.atom.as_str(), Some(observed), granted))
                        .or_default()
                        .push(u),
                    Coverage::Unknown { granted } => by_arg
                        .entry((u.atom.as_str(), None, granted))
                        .or_default()
                        .push(u),
                    Coverage::Uncovered => {
                        let flagged = !(must && u.certain)
                            || undeclared.contains(&(
                                e.anchor.clone(),
                                u.atom.clone(),
                                u.unit.clone(),
                            ));
                        if flagged {
                            by_atom
                                .entry((u.atom.as_str(), !u.certain))
                                .or_default()
                                .push(u);
                        }
                    }
                }
            }
            for ((atom, observed, granted), us) in by_arg {
                let allowed = granted
                    .iter()
                    .map(|a| format!("{a:?}"))
                    .collect::<Vec<_>>()
                    .join(", ");
                match observed {
                    Some(obs) if must && us.iter().all(|u| u.certain) => {
                        let anchor = format!("cap/{}/{atom}", e.anchor);
                        out.fire(
                            "CAP001",
                            Severity::Error,
                            format!(
                                "`{}` uses `{atom}` with argument {obs:?}, outside every granted argument ({allowed}) ({} use(s)): {}",
                                e.anchor,
                                us.len(),
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
                    Some(obs) => {
                        let anchor = format!("cap/{}/{atom}/arg", e.anchor);
                        out.unresolved(
                            "CAP001",
                            Reason::MayOnlyOwner,
                            &format!(
                                "`{atom}` may be used by `{}` with argument {obs:?}, outside every granted argument ({allowed}); the use is not certain Must-owned code: {}",
                                e.anchor,
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
                    None => {
                        let anchor = format!("cap/{}/{atom}/arg", e.anchor);
                        out.unresolved(
                            "CAP001",
                            Reason::UnresolvedEdge,
                            &format!(
                                "`{atom}` is used by `{}` with an argument that cannot be resolved statically, so the granted arguments ({allowed}) cannot be checked: {}",
                                e.anchor,
                                list(&us)
                            ),
                            &anchor,
                            site,
                        );
                    }
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

/// The atoms a grant of `granted` covers: itself and its children, registered or declared by a pack.
fn expansion(granted: &str, packs: &BTreeMap<String, PackPin>) -> Vec<String> {
    atoms()
        .into_iter()
        .map(|a| a.name)
        .chain(
            packs
                .values()
                .flat_map(|p| p.atoms.iter().map(String::as_str)),
        )
        .filter(|n| *n == granted || n.strip_prefix(granted).is_some_and(|r| r.starts_with('.')))
        .map(str::to_owned)
        .collect()
}

/// How the enabled packs answer `(atom, lang)`: `Some(kind)` for a real row, `None` for no row.
///
/// A `callee` row wins over `impossible` (PACK004 reports the clash); `none` rows are no row.
fn pack_answer(
    packs: &BTreeMap<String, PackPin>,
    atom: &str,
    lang: &str,
) -> Option<PackDetectorKind> {
    let kinds: BTreeSet<PackDetectorKind> = packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .filter(|d| d.atom == atom && d.lang == lang && d.kind != PackDetectorKind::None)
        .map(|d| d.kind)
        .collect();
    if kinds.contains(&PackDetectorKind::Callee) {
        Some(PackDetectorKind::Callee)
    } else {
        kinds.into_iter().next()
    }
}

/// True when another pack atom is a child of `atom` (`db` over `db.query`): it has no row of its own.
fn is_pack_parent(packs: &BTreeMap<String, PackPin>, atom: &str) -> bool {
    packs
        .values()
        .flat_map(|p| p.atoms.iter())
        .any(|n| n.strip_prefix(atom).is_some_and(|r| r.starts_with('.')))
}

/// True when `atom` is declared by an enabled pack rather than the shared registry.
fn is_pack_atom(packs: &BTreeMap<String, PackPin>, atom: &str) -> bool {
    !atom_registered(atom) && packs.values().any(|p| p.atoms.contains(atom))
}

fn atom_registered(atom: &str) -> bool {
    gob_ir::registry::atom(atom).is_some()
}

/// One Unresolved per node, pack atom and language for a granted pack atom that no enabled pack
/// has a detector for, in the languages of the node's files within the grant's scope.
fn report_no_detector(
    cx: &Cx<'_>,
    e: &crate::model::Entity,
    atoms: &[String],
    files: &[&str],
    reported: &mut BTreeSet<(String, String)>,
    site: Option<(&str, (usize, usize))>,
    out: &mut Output,
) {
    for a in atoms
        .iter()
        .filter(|a| is_pack_atom(cx.packs, a) && !is_pack_parent(cx.packs, a))
    {
        let mut no_detector: BTreeSet<&str> = BTreeSet::new();
        for f in files {
            let Some(lang) = cx.code.file(f).map(|c| c.language.as_str()) else {
                continue;
            };
            if lang != crate::code::OPAQUE && pack_answer(cx.packs, a, lang).is_none() {
                no_detector.insert(lang);
            }
        }
        for lang in no_detector {
            if !reported.insert((a.clone(), lang.to_owned())) {
                continue;
            }
            tracing::warn!(node = %e.anchor, atom = %a, lang, "pack atom has no detector for the language; not enforced");
            out.unresolved(
                "CAP002",
                Reason::Fidelity,
                &format!(
                    "`{a}` is granted to `{}` but no pack detector covers it in {lang} (no-detector); its use in {lang} code is not enforced",
                    e.anchor
                ),
                &format!("cap/{}/{a}/{lang}/no-detector", e.anchor),
                site,
            );
        }
    }
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
        let mut reported: BTreeSet<(String, String)> = BTreeSet::new();
        for g in &e.grants {
            out.count("CAP002", 1);
            let site = Some((g.file.as_str(), (g.span.start, g.span.end)));
            let atoms = expansion(
                gob_ir::registry::canonical(&g.atom).unwrap_or(&g.atom),
                cx.packs,
            );
            if atoms.is_empty() || files.is_empty() {
                tracing::debug!(node = %e.anchor, atom = %g.atom, "grant has no detectable atom or no owned code; not judged");
                continue;
            }
            // Scope in units: a file is in scope when the selector may reach it; a use is in
            // scope when its own unit (or an enclosing one) is selected.
            let in_scope = |f: &str| {
                g.at.as_ref().is_none_or(|sel| {
                    gob_walk::select_files(sel, &cx.code.walk)
                        .iter()
                        .any(|m| m.path == f)
                })
            };
            let use_in_scope = |u: &Use| g.at.as_ref().is_none_or(|sel| selects_use(sel, u));
            let scoped: Vec<&str> = files.iter().copied().filter(|f| in_scope(f)).collect();
            report_no_detector(cx, e, &atoms, &scoped, &mut reported, site, out);
            let observed = [&uses.lo, &uses.hi].iter().any(|by_node| {
                by_node.get(&e.anchor).is_some_and(|us| {
                    us.iter()
                        .any(|u| atoms.contains(&u.atom) && use_in_scope(u))
                })
            });
            if observed {
                continue;
            }
            let covered = atoms.iter().all(|a| {
                langs.iter().all(|l| {
                    if is_pack_atom(cx.packs, a) {
                        return is_pack_parent(cx.packs, a)
                            || pack_answer(cx.packs, a, l).is_some();
                    }
                    match detectors(a, l) {
                        Answer::Exact(kinds) => !kinds.contains(&DetectorKind::Lexical),
                        Answer::NotApplicable => true,
                        _ => false,
                    }
                })
            });
            if may_owned || unseen || !covered {
                tracing::debug!(node = %e.anchor, atom = %g.atom, may_owned, unseen, covered, "grant not judged: absence is not Exact");
                continue;
            }
            out.fire(
                "CAP002",
                Severity::Error,
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
