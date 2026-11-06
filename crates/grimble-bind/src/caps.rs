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
//! CAP002 reads its cells from the public [`grant_cells`] matrix API (one [`GrantCell`] per judgeable
//! grant), the source the matrix verb consumes instead of rebuilding cells from CAP findings.
//!
//! Method vocabulary (ticket 2T7C4A9): `Path.m` names method `m` on a receiver whose type is
//! `pathlib.Path`, resolved textually (a `Path(..)` chain, or a name assigned or annotated as one
//! in the same file); it is a Must use. A `.m` entry on a receiver that does not resolve is a May
//! use, reported Unresolved (`docs/design/grimble/binding.md` section 7: unknown never reads as clean).
//!
//! Import resolution (ticket D36SRKP): besides the call graph, `gob_symbols::path_uses` resolves
//! each call and each function-valued reference through `use ... as`, from-imports, `let` and
//! assignment aliases (including the bare builtin `open`, ticket 8B9HSHH), literal `getattr` / `import_module` (the same use as the direct form) and explicit
//! `std::` / `tokio::` roots (which a repository type named `Command` cannot hide). Rust names are
//! followed across the repository (ticket 01M64230DV9KGPE0JH2D37NDVN, `rust_modules`): type aliases,
//! `pub use` chains over inline modules and `mod x;` files, same-file `macro_rules!` bodies and
//! literal `include!` targets resolve to the origin path; globs, fragment-path macros, computed
//! includes and missing module files are Unresolved. A Python `from m import *` (ticket G68NRS1) resolves each
//! bare name no scope binds to the single known vocabulary module that supplies it (certain);
//! several wildcards, a relative or unknown module, or a repository module that may re-export the
//! name are reported Unresolved against every atom the name could reach, and a repository
//! module's literal `__all__` (or its own definition of the name) is honoured. A name-computed lookup (`getattr`, `__import__`,
//! `importlib.import_module`, `vars(m)[n]`, `m.__dict__[n]`, `sys.modules[n]`) resolves through
//! the shared gob-ir `name_lookup` rule (ticket 6CV37RW): a literal name denotes the origin symbol
//! exactly as the direct form, any other name is reported Unresolved against every atom its known
//! prefix could reach.
//!
//! Python `eval`, `exec` and `compile` (atom `code.eval`, ticket T78E2WZ) resolve through the same
//! alias and import machinery (`e = eval`, `builtins.eval`, `from builtins import exec as run`,
//! `getattr(builtins, 'eval')`, `__builtins__['eval']`). A constant source is parsed and its uses
//! are scanned in the scopes of the call; any other source, an unparsable or over-nested one, or a
//! function value is reported Unresolved against `code.eval`, naming the call. A spelled name alone
//! is never a certain use, so the finding is never an error.
//!
//! Python entry points (ticket 01M6422ZVVSTEKVMY0PR269X33): the os exec, spawn and fork family,
//! `pty`, asyncio subprocesses, `http.client`, urllib3, httpx, smtplib, ftplib, asyncio streams
//! (constructor and module-function entry points), `os.environ` / `os.environb` reads (also by
//! index or iteration), ctypes loaders, `pickle` / `marshal` / `shelve` / `dill` /
//! `cloudpickle` loaders (atom `code.eval`) and archive extraction are registered in
//! `gob_symbols::capvocab`. `tarfile` / `zipfile` `extract` / `extractall` are typed through the
//! constructing call (the pack's receiver families); an untyped receiver in a file that reaches the module
//! is Unresolved. Not covered: methods on `http.client` / `smtplib` / `ftplib` connections and
//! asyncio loop methods beyond the constructors, and the Python `ffi` detector.
//!
//! TypeScript family and C# (ticket PKW7X2J): `typescript` (TypeScript, JavaScript, Node, Deno,
//! Bun) and `csharp` files are judged by import resolution alone, never by spelled call text, so
//! a local object named `fs` or a repository class named `File` is not a capability. The
//! registry entries live in `gob_symbols::capvocab`; they are matched against paths resolved
//! through ES imports, `require`, `import x = require`, ambient globals, and C# `using`
//! (namespace, `static`, alias, `global::`). A computed `require(n)` or `obj[n]` stays Unresolved,
//! and `eval` / `Function` / `Assembly.Load` are never a certain use.
//!
//! No-detector languages (ticket 01M5XNNHET0VW6RFJAF0QH7RRS): a node owning shell, Dockerfile or
//! workflow code, for which no atom has a detector, reports one CAP001 Unresolved naming the
//! unknown atoms (`cap_no_detector`) instead of reading as clean. Data files do not count.
//!
//! Python cross-module and multi-binding names (ticket 7XKRQQ2): a path written through a project
//! module (`from helpers import r`, `helpers.r(..)`, relative imports) is followed through that
//! module's own imports to its origin symbol (`python_modules`); a name bound several ways (rebound,
//! try/except fallback, conditional shadow) is reported per origin, Unresolved.
//!
//! Typed receivers (tickets YCR4M6H and 01M64230GWHHTH9R7CZ55XRPGG): a Rust vocabulary entry
//! `<type path>.<method>` (`ureq::Agent.run`) names a method call whose receiver type resolves,
//! from the syntax tree, to that path: through `use` imports (also function-local) and aliases,
//! struct fields (`self.agent`), parameters, `let` bindings scoped lexically (an inner `let` hides
//! the outer name only inside its block), constructors, the declared return types of functions and
//! methods in the file (builder chains), `?` / `unwrap` / `if let Some` / `match` unwrapping,
//! `Arc` / `Box` / `Rc` / lock wrappers, `clone()` and typed `const` / `static` items. It is a
//! Must use. A receiver typed by a generic parameter, `impl Trait`, `dyn Trait` or an associated
//! type is Unresolved: a May use of every typed method of that name. A receiver of any other
//! unknown type is not reported.
//!
//! Calls into another node (ticket 01M642304NQ5XQP3WWD0T8Z2BM, audit case q07): a use belongs to the
//! node that owns the code it sits in, but a node that calls a function owned elsewhere also
//! reaches what that function does. Every call edge the graph resolved (imports, aliases,
//! re-exports, methods with a proven receiver; any language with a call graph, so Python,
//! TypeScript/JavaScript, C# and Rust) whose callee sits in code owned by a different node carries
//! the callee's uses, and those reached through its own calls in turn, to the caller's owner
//! (`propagate_cross_node`). The carried use is certain only when every hop is a proven (`Must`,
//! symbolic) edge and the original use was certain; a hop that is `May` or a method-name guess
//! makes it a May use, reported Unresolved. The traversal keeps a visited set, so recursion and
//! call cycles terminate and there is no depth bound to hit. A call that resolves to nothing in
//! the repository carries nothing (its vocabulary match is judged directly). A callee's nested
//! units count as part of it; module-level code of the callee's file is not reached by a call.
//!
//! Function values (ticket 01M5XNNJ994RN6Y24AT6ZD117V): a reference to a function used as a value
//! (`let f = write_any;`, `for_each(write_any)`) that is not itself a call is carried as a May
//! hop, so the capability reaches the caller as Unresolved; closures and trait-object dispatch
//! already arrive as May edges. A `provides C via S` boundary (grimble-capabilities-v3.md 5.3,
//! ticket 01M666NX8TN1R3X13Q4S9CTJ1V) stops the walk: when the traversal reaches a symbol the
//! owning node declared a provider, only the uses of the provided atom `C` found in S itself are
//! carried (the boundary's declared effect) and the calls S makes are not followed, so the
//! interior of S does not leak to its callers. A wrapper with no `provides` is never a boundary.
//! Not yet modeled: narrowing the carried use to the declared arguments of `C`, and the caller
//! side `may C via S`.
//!
//! Known limits: receiver typing is per file and textual (no cross-module constants, no
//! shadowing by unannotated parameters; typed receivers resolve only types written in the same
//! file, not values returned by calls); `open(..)` in a write mode is `fs.write` (ticket 01M4HYH9CDNJSYEZQGKRZA7WX2) but a mode other than a literal (or a `*args` / `**kw` call) is a May `fs.write` beside the read; a call is matched to its use by byte offset, so an aliased or shadowed `open` is judged symbolically (ticket 01M5XNNHY7KZDKBZKK2MM08TTF); a Rust `OpenOptions::new()` / `File::options()` builder is followed through chains and `let` bindings (`argdet.rs`): `read(true)` alone needs only `fs.read`, `write` / `append` / `create` / `truncate` need `fs.write`, a conditional or escaping builder is May; `shutil.copy*` / `fs::copy` scope `fs.read` to the source and `fs.write` to the destination; `os.open` flags, `shutil.move` / `os.rename` directions and other languages' open modes are not modeled; template excuses are resolved to files and CAP004 (packs-and-plugins.md 6.7) is emitted from `grimble_capabilities::excuse::cap004` (Error for a certain use, Unresolved for a May use; the use is then not also CAP001); the pack
//! severity is consulted for CAP001 (ticket K4EMP90): `[packs.severity]` for the atom, else the
//! atom row (`warn` there makes the denied use Unresolved, never an Error), else Error; the message
//! carries the row's rationale and safer alternative. CAP002 is a Warning.
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
// frob:ticket 01M5XNNJXHY369P16NZJMQ3SX6
// frob:ticket 01M64230AR8DHJZY9QQS3EC85S
// frob:ticket 01M4HEMAM737MTY3385G7VKXQ4
// frob:ticket 01M5XNNHY7KZDKBZKK2MM08TTF
// frob:ticket 01M59RWT16TFNSACMMTTXX200T
// frob:ticket 01M5XNNHBSPSM5XFG8FM64HENY
// frob:ticket 01M5XNNHJ0ES2PB6ZKAD36SRKP
// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE
// frob:ticket 01M5XNNHRFE1K2DHBD7S9HQ7A6
// frob:ticket 01M5XWCAYVZQX363SSWYCR4M6H
// frob:ticket 01M4HYH9CDNJSYEZQGKRZA7WX2
// frob:ticket 01M642307T98S89GQ4APKW7X2J
// frob:ticket 01M6422Z8JGE789ZHW4G68NRS1
// frob:ticket 01M642304NQ5XQP3WWD0T8Z2BM
// frob:ticket 01M5XNNJ994RN6Y24AT6ZD117V

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fmt::Write as _;

use gob_ir::Answer;
use gob_ir::registry::{DetectorKind, atoms, callee_vocab, detectors};
use gob_rules::Severity;
use gob_symbols::{EdgeKind, Target};
use gob_walk::{Owner, selects_unit_or_enclosing};
use grimble_capabilities::excuse::{self, Excuse, GrantScope, UseSite};
use grimble_capabilities::{Cell, NodeInput};
use grimble_model::args::{ArgKind, Judgement, arg_kind, judge};
use grimble_model::ast::EntityKind;
use grimble_model::{PackDetectorKind, PackPin, pack_arg_kind};

mod argdet;
mod python_modules;
mod rstype;
mod rust_modules;

use crate::code::CodeFile;
use crate::eval::{Cx, Output};
use crate::model::Grant;
use crate::types::Reason;
use python_modules::Modules;
use rust_modules::RustModules;

/// How many example call sites one finding names.
const EXAMPLES: usize = 3;

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
    /// The byte offset of the call when the source knows it: pins argument analysis to the exact call.
    offset: Option<usize>,
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
    /// Uses in code no node owns (`Owner::Foreign`): checked against an implicit node with no
    /// grants (default-deny, ticket S9HQ7A6).
    unowned: Vec<Use>,
    /// Uses in code whose owner cannot be named and has no candidate (a hidden remainder).
    unseen: Vec<Use>,
}

/// Why CAP001 and CAP002 have no subject: no node owns code, so no cell exists.
pub fn caps_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    let owns = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Node && !e.external && e.owns_code());
    (!owns).then_some("no node owns code, so no use can be observed")
}

/// Why SYS012 has no subject: no template excuse meets a node grant, so none can contradict.
pub fn sys012_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    let has = |kind, any: fn(&crate::model::Entity) -> bool| {
        model.entities.values().any(|e| e.kind == kind && any(e))
    };
    let both = has(EntityKind::Template, |e| !e.excuses.is_empty())
        && has(EntityKind::Node, |e| !e.grants.is_empty());
    (!both).then_some("no template excuse and node grant exist together to contradict")
}

/// Why CAP004 has no subject: CAP001/CAP002 are inapplicable, or no template declares an excuse.
pub fn cap004_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    if let Some(why) = caps_inapplicable(model) {
        return Some(why);
    }
    let excused = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Template && !e.excuses.is_empty());
    (!excused).then_some("no template declares an excuse, so none can mask a use")
}

/// Why CAP006 has no subject: the model declares no `ceiling`, so no grant can exceed one.
pub fn cap006_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    model
        .ceilings
        .is_empty()
        .then_some("no `ceiling` is declared, so no grant can exceed one")
}

fn callee_of(text: &str) -> &str {
    text.strip_suffix("(..)").unwrap_or(text)
}

/// True when the written `callee` names the vocabulary entry `name` (a Rust path entry also
/// matches behind extra leading segments: `std::fs::read` names `fs::read`, but a path rooted
/// in a non-process crate (pack data) names nothing).
fn names_callee(lang: &str, names: &BTreeSet<&str>, callee: &str) -> bool {
    if names.contains(callee) {
        return true;
    }
    // a trailing `*` names every item under its prefix (`libc::*`), from the exact root only
    if names
        .iter()
        .any(|n| wildcard_prefix(n).is_some_and(|p| callee.starts_with(p)))
    {
        return true;
    }
    // `process.env.HOME` and `os.environ.items` read through the object entry
    if matches!(lang, "typescript" | "python")
        && names.iter().any(|n| {
            n.rsplit_once('.')
                .is_some_and(|(_, last)| matches!(last, "env" | "environ" | "environb"))
                && callee.starts_with(&format!("{n}."))
        })
    {
        return true;
    }
    lang == "rust"
        && !callee
            .split_once("::")
            .is_some_and(|(root, _)| gob_ir::core_pack::non_process_crates().contains(&root))
        && names
            .iter()
            .any(|n| n.contains("::") && callee.ends_with(&format!("::{n}")))
}

/// The prefix a wildcard vocabulary name covers (`libc::*` -> `libc::`, `A.B.*` -> `A.B.`).
fn wildcard_prefix(name: &str) -> Option<&str> {
    name.strip_suffix('*')
        .filter(|p| p.ends_with("::") || p.ends_with('.'))
}

/// True when a computed (unknown-tail) use of `path` may reach vocabulary `name`: the name lives
/// under the path, is the path, or (Rust) is spelled relative to a module the path ends in, as
/// after `use std::arch::*` (names are matched by suffix, so `arch::asm` is `std::arch::asm`).
fn computed_reaches(lang: &str, name: &str, path: &str) -> bool {
    if name == path || name.starts_with(&format!("{path}.")) {
        return true;
    }
    if let Some(p) = wildcard_prefix(name)
        && path.starts_with(p.trim_end_matches([':', '.']))
    {
        return true;
    }
    if lang != "rust" {
        return false;
    }
    if name.starts_with(&format!("{path}::")) {
        return true;
    }
    // some proper segment-prefix of the name is a segment-suffix of the path
    let segs: Vec<&str> = name.split("::").collect();
    (1..segs.len()).any(|k| {
        let q = segs[..k].join("::");
        path == q || path.ends_with(&format!("::{q}"))
    })
}

/// True for languages whose uses are found only by import resolution: a spelled call-graph text
/// (`fs.readFile`) proves nothing there, since the receiver may be any local object named `fs`.
fn resolved_only(lang: &str) -> bool {
    matches!(
        lang,
        "typescript" | "csharp" | "go" | "java" | "c" | "cpp" | "shell"
    )
}

/// The atom of the code-evaluating builtins, whose use is only ever unresolved from a name.
const CODE_EVAL: &str = "code.eval";

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
    for a in atoms()
        .into_iter()
        .filter(|a| !gob_ir::core_pack::is_grouping(a.name))
    {
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

/// The atoms whose vocabulary in `lang` names the call `callee`, given the lazily computed type of
/// its receiver.
fn atoms_of(
    vocabs: &[(&str, BTreeSet<&str>)],
    lang: &str,
    callee: &str,
    receiver_is_path: &mut dyn FnMut(&str) -> bool,
) -> Vec<Hit> {
    let mut out = Vec::new();
    for (atom, names) in vocabs {
        let atom = *atom;
        if names_callee(lang, names, callee) {
            out.push(Hit {
                atom: atom.to_owned(),
                // a spelled `builtins.eval` names no source: whether the code is constant is
                // only known to the symbolic pass, so the name alone is never proof (T78E2WZ)
                certain: atom != CODE_EVAL,
            });
            continue;
        }
        let Some((recv, m)) = callee.rsplit_once('.') else {
            continue;
        };
        if !names.contains(format!(".{m}").as_str()) {
            continue;
        }
        if lang == "python"
            && gob_ir::core_pack::receiver_families(lang).any(|f| f.methods.contains(&(atom, m)))
        {
            // typed by its receiver's constructor, not by this call's text (`scan_python_receivers`)
            continue;
        }
        if names.contains(format!("Path.{m}").as_str()) && receiver_is_path(recv) {
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
        // A tie names its candidates: each may own the use.
        Owner::Unknown(ns) if !ns.is_empty() => {
            for n in ns {
                uses.hi
                    .entry(n.as_str().to_owned())
                    .or_default()
                    .push(u.clone());
            }
        }
        Owner::Unknown(_) => uses.unseen.push(u),
        Owner::Foreign => uses.unowned.push(u),
    }
}

/// The owner of the unit a use sits in. A file no selector reaches has no ownership units at all
/// (see `owner::build`), so its code is `Foreign` rather than skipped; frob-owned and unwalked
/// files and units the owner pass never saw have no owner to judge (`None`).
fn owner_of_use(cx: &Cx<'_>, unit: &str, path: &str) -> Option<Owner> {
    if let Some(uo) = cx.owners.units.get(unit) {
        return Some(uo.merged.owner.clone());
    }
    let unreached = cx.owners.files.get(path).is_some_and(|fo| !fo.expanded);
    if unreached && !crate::frob_owned::is_frob_owned(path, cx.ledger_dir) {
        tracing::debug!(path, unit, "use sits in code no node owns");
        return Some(Owner::Foreign);
    }
    None
}

/// The last path segment of a vocabulary name (`fs::read` -> `read`, `subprocess.run` -> `run`).
fn last_segment(name: &str) -> &str {
    let name = name
        .trim_start_matches('.')
        .trim_end_matches('*')
        .trim_end_matches(['.', ':']);
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

/// frob:ticket 01M642301PNSE0VTM2F313NY13
/// True when the call edge proves no target: unresolved, or a guess by method name alone. A
/// project class that merely shares a method's name must never hide a use whose receiver may be
/// a capability type, so such an edge is judged like an unresolved call.
fn is_open_call(e: &gob_symbols::StatusEdge) -> bool {
    e.kind == EdgeKind::Calls && (e.to.is_none() || (e.basis == gob_symbols::EdgeBasis::NameOnly))
}

/// (file, line, name) of every call the graph resolved inside the repository.
fn graph_resolved_calls(cx: &Cx<'_>) -> BTreeSet<(String, u32, String)> {
    let mut local = BTreeSet::new();
    for e in cx.graph.edges_with_status() {
        if e.kind == EdgeKind::Calls
            && e.to.is_some()
            && !is_open_call(e)
            && let (Some(l), Some(n)) = (e.line, e.name.as_ref())
        {
            local.insert((e.from.path().to_owned(), l, n.clone()));
        }
    }
    local
}

/// Dedup keys (unit, line, atom, certain) of every use already recorded.
fn seen_uses(uses: &Uses) -> BTreeSet<(String, Option<u32>, String, bool)> {
    let mut set = BTreeSet::new();
    for us in uses
        .lo
        .values()
        .chain(uses.hi.values())
        .chain([&uses.unowned, &uses.unseen])
    {
        for u in us {
            set.insert((u.unit.clone(), u.line, u.atom.clone(), u.certain));
        }
    }
    set
}

/// Files the import-resolution pass reads: every unit file plus unexpanded (unowned) files.
fn scan_files<'a>(cx: &'a Cx<'_>) -> BTreeSet<&'a str> {
    cx.owners
        .units
        .values()
        .map(|u| u.file.as_str())
        .chain(
            cx.owners
                .files
                .iter()
                .filter(|(_, fo)| !fo.expanded)
                .map(|(p, _)| p.as_str()),
        )
        .collect()
}

/// Cheap prefilter: whether `src` mentions a vocabulary name or a name-computed lookup at all.
/// Python is checked on its NFKC form, since identifiers may be spelled in any equivalent form
/// (ticket 01M6422ZYR690QV4JF17VYCFGM); other languages are never normalised.
fn file_is_relevant(language: &str, src: &str, vocab: &[(&str, BTreeSet<&str>)]) -> bool {
    // C and C++ have computed callees (function pointers, macros) that name no vocabulary entry,
    // so no spelling can rule a file out (ticket 01M64VBRHX20P2EJGQ2S1VG0FG); a shell command
    // word may be an expansion (`$c -rf x`), which names no vocabulary entry either
    // (ticket 01M6CN4WNECMHQ1T65JT6CSE34)
    if matches!(language, "c" | "cpp" | "shell") {
        return true;
    }
    let folded;
    let hay: &str = if language == "python" && !src.is_ascii() {
        folded = unicode_normalization::UnicodeNormalization::nfkc(src).collect::<String>();
        &folded
    } else {
        src
    };
    // (a name-computed lookup names no vocabulary entry, so a lookup primitive also passes)
    // (`__builtins__[n]` is a lookup into the builtins namespace, which names no primitive)
    gob_ir::name_lookup::mentions_lookup(language, hay)
        || (language == "python" && hay.contains("__builtins__"))
        || vocab
            .iter()
            .any(|(_, names)| names.iter().any(|n| hay.contains(last_segment(n))))
}

/// The atoms whose vocabulary the use `callee` names: a wildcard's hits, a computed use's reachable
/// atoms, or the atoms naming the callee exactly.
fn vocab_hits<'a>(
    language: &str,
    vocab: &[(&'a str, BTreeSet<&'a str>)],
    star: Option<&StarOutcome<'a>>,
    pu: &gob_symbols::PathUse,
    callee: &str,
) -> Vec<&'a str> {
    if let Some(star) = star {
        return star.hits.clone();
    }
    vocab
        .iter()
        .filter(|(_, names)| {
            if pu.computed {
                // unknown tail: any atom whose vocabulary lives under the known prefix
                // (or a vocabulary entry that is the path itself: a computed use of `eval`)
                callee.is_empty() || names.iter().any(|n| computed_reaches(language, n, callee))
            } else {
                names_callee(language, names, callee)
            }
        })
        .map(|(a, _)| *a)
        .collect()
}

/// The paths a use may denote once repository re-exports are followed, with whether each is unproven.
fn rewrite_path(
    cx: &Cx<'_>,
    path: &str,
    language: &str,
    pu: &gob_symbols::PathUse,
    modules: &mut Modules,
    rust_modules: &mut RustModules,
) -> Vec<(String, bool)> {
    let origins = match language {
        "python" => modules.origins(cx, path, &pu.path),
        "rust" if !pu.external_root => rust_modules.origins(cx, path, &pu.path),
        _ => return vec![(pu.path.clone(), false)],
    };
    origins.into_iter().map(|o| (o.path, o.unproven)).collect()
}

/// The path uses of every relevant file, read and parsed in parallel.
///
/// Reading, the relevance prefilter and `path_uses` (a tree-sitter parse) dominate the pass and
/// depend on the file alone, so they run on the rayon pool; the order-dependent resolution that
/// follows stays serial and takes each file's result from the map.
fn prepare_path_uses<'a>(
    cx: &Cx<'_>,
    files: &BTreeSet<&'a str>,
    reaching: &BTreeSet<String>,
) -> BTreeMap<&'a str, Vec<gob_symbols::PathUse>> {
    use rayon::prelude::*;
    let vocabs: BTreeMap<&str, Vec<(&str, BTreeSet<&str>)>> = SCANNED_LANGUAGES
        .iter()
        .map(|&lang| (lang, vocabularies(lang, cx.packs)))
        .collect();
    let paths: Vec<&'a str> = files.iter().copied().collect();
    let out: BTreeMap<&'a str, Vec<gob_symbols::PathUse>> = paths
        .par_iter()
        .filter_map(|&path| {
            let code = cx.code.file(path)?;
            let vocab = vocabs.get(code.language.as_str())?;
            let src = code.source()?;
            if !file_is_relevant(&code.language, &src, vocab) && !reaching.contains(path) {
                return None;
            }
            code.symbols()?;
            let mut found = gob_symbols::path_uses(&code.language, &src);
            if code.language == "rust" {
                found.extend(included_uses(cx, path, &src, 0));
            }
            Some((path, found))
        })
        .collect();
    tracing::debug!(files = out.len(), "path uses prepared in parallel");
    out
}

/// Languages the import-resolution pass reads.
const SCANNED_LANGUAGES: [&str; 9] = [
    "rust",
    "python",
    "typescript",
    "csharp",
    "go",
    "java",
    "c",
    "cpp",
    "shell",
];

/// Uses found by import resolution (ticket D36SRKP): calls and function values whose written
/// path names a vocabulary entry only through an alias, a from-import, a `let` binding, a literal
/// `getattr` / `import_module`, or an explicit `std::` / `tokio::` root that a same-named
/// repository item hides from the call graph. Added to `uses` unless the call-graph pass already
/// recorded the same atom on the same line of the same unit.
#[allow(clippy::too_many_lines)] // one pass per file: variants, hits and routing together
fn scan_resolved(cx: &Cx<'_>, uses: &mut Uses) {
    let local = graph_resolved_calls(cx);
    let mut seen = seen_uses(uses);
    let files = scan_files(cx);
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
    let reaching = module_reaching(cx, &files);
    let mut prepared = prepare_path_uses(cx, &files, &reaching);
    let mut modules = Modules::default();
    let mut rust_modules = RustModules::default();
    let mut added = 0usize;
    for path in files {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if !SCANNED_LANGUAGES.contains(&code.language.as_str()) {
            continue;
        }
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        let Some(found) = prepared.remove(path) else {
            continue;
        };
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for pu in found {
            if !pu.external_root
                && !pu.dynamic
                && !pu.maybe
                && local.contains(&(
                    path.to_owned(),
                    pu.line,
                    last_segment(&pu.spelled).to_owned(),
                ))
            {
                tracing::debug!(file = path, line = pu.line, spelled = %pu.spelled, "resolved path is a repository item");
                continue;
            }
            let star = (!pu.wildcards.is_empty())
                .then(|| resolve_star(cx, path, &code.language, vocab, &pu));
            // a path may be rewritten by a repository module's own re-exports (Python modules,
            // Rust modules, type aliases and `mod x;` files; ticket 01M64230DV9KGPE0JH2D37NDVN)
            let variants = if star.is_none() && !pu.computed {
                rewrite_path(
                    cx,
                    path,
                    &code.language,
                    &pu,
                    &mut modules,
                    &mut rust_modules,
                )
            } else {
                vec![(pu.path.clone(), false)]
            };
            for (callee, unproven) in variants {
                let hits = vocab_hits(&code.language, vocab, star.as_ref(), &pu, &callee);
                if hits.is_empty() {
                    continue;
                }
                let (unit, qual) = unit_at(cx, symbols, &file_unit, pu.offset);
                let Some(owner) = owner_of_use(cx, &unit, path) else {
                    tracing::debug!(file = path, unit = %unit, "resolved use has no ownership unit");
                    continue;
                };
                // a literal lookup name denotes the origin symbol exactly as the direct form; only
                // a computed name, several possible bindings or origins are unproven
                let certain = !pu.computed
                    && !pu.maybe
                    && !unproven
                    && star.as_ref().is_none_or(|st| st.certain);
                for atom in hits {
                    // a spelled `eval` / `Function` / `Assembly.Load` names no source: only unproven
                    let certain = certain && !(atom == CODE_EVAL && resolved_only(&code.language));
                    if !seen.insert((unit.clone(), Some(pu.line), atom.to_owned(), certain)) {
                        continue;
                    }
                    tracing::debug!(file = path, line = pu.line, atom, %callee, certain, "resolved capability use");
                    added += 1;
                    route(
                        uses,
                        &owner,
                        Use {
                            atom: atom.to_owned(),
                            file: path.to_owned(),
                            unit: unit.clone(),
                            qual: qual.clone(),
                            line: Some(pu.line),
                            offset: Some(pu.offset),
                            callee: callee.clone(),
                            certain,
                            arg: None,
                        },
                    );
                }
            }
        }
    }
    tracing::info!(added, "import-resolved capability uses added");
}

/// One structural detector row: the atom, its kind and its expanded grammar patterns.
type StructuralRow<'a> = (&'a str, PackDetectorKind, Vec<String>);

/// The structural detector rows of the enabled packs for `lang`: `(atom, kind, patterns)`, with
/// every `import` row's module names already expanded to the language's import patterns.
fn structural_rows<'a>(packs: &'a BTreeMap<String, PackPin>, lang: &str) -> Vec<StructuralRow<'a>> {
    packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .filter(|d| d.kind.is_structural() && d.lang == lang)
        .map(|d| {
            let patterns = if d.kind == PackDetectorKind::Import {
                d.patterns
                    .iter()
                    .flat_map(|m| gob_pattern::detector::import_patterns(lang, m))
                    .collect()
            } else {
                d.patterns.clone()
            };
            (d.atom.as_str(), d.kind, patterns)
        })
        .collect()
}

/// The 1-based line holding byte `offset` of `src`.
fn line_of(src: &str, offset: usize) -> u32 {
    let end = offset.min(src.len());
    let lines = src.as_bytes()[..end].split(|&b| b == b'\n').count();
    u32::try_from(lines).unwrap_or(u32::MAX)
}

/// Pack `import`, `attribute` and `pattern` detector rows (ticket 01M5XNNJHXH8FFQ9JHJP21FHB9): run
/// each row's grammar patterns over every scanned file of its language and route one certain use
/// per match to the owner of the enclosing unit. A pattern that does not compile, or a file that
/// does not parse, is logged and fires nothing (the cell is never reported clean by guessing).
fn scan_structural(cx: &Cx<'_>, uses: &mut Uses) {
    if !cx
        .packs
        .values()
        .flat_map(|p| p.detectors.iter())
        .any(|d| d.kind.is_structural())
    {
        return;
    }
    let mut seen = seen_uses(uses);
    let mut rows: BTreeMap<String, Vec<StructuralRow<'_>>> = BTreeMap::new();
    let mut added = 0usize;
    for path in scan_files(cx) {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        let rows = rows
            .entry(code.language.clone())
            .or_insert_with(|| structural_rows(cx.packs, &code.language));
        if rows.is_empty() {
            continue;
        }
        let (Some(src), Some(symbols)) = (code.source(), code.symbols()) else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for (atom, kind, patterns) in rows.iter() {
            let sites = match gob_pattern::detector::sites(&code.language, patterns, &src) {
                Ok(s) => s,
                Err(err) => {
                    tracing::warn!(file = path, atom, %err, "structural detector could not run");
                    continue;
                }
            };
            for offset in sites {
                let (unit, qual) = unit_at(cx, symbols, &file_unit, offset);
                let Some(owner) = owner_of_use(cx, &unit, path) else {
                    continue;
                };
                let line = line_of(&src, offset);
                if !seen.insert((unit.clone(), Some(line), (*atom).to_owned(), true)) {
                    continue;
                }
                tracing::debug!(file = path, line, atom, ?kind, "structural capability use");
                added += 1;
                route(
                    uses,
                    &owner,
                    Use {
                        atom: (*atom).to_owned(),
                        file: path.to_owned(),
                        unit,
                        qual,
                        line: Some(line),
                        offset: Some(offset),
                        callee: format!("{kind:?}").to_lowercase(),
                        certain: true,
                        arg: None,
                    },
                );
            }
        }
    }
    tracing::info!(added, "structural capability uses added");
}

/// The Python and Rust files that may reach a vocabulary callee through a repository re-export
/// (tickets 01M6422ZN7HKF98JDAP7XKRQQ2, 01M64230DV9KGPE0JH2D37NDVN): those that mention one, and
/// those that mention the module name of such a file. A Rust file that holds an `include!` also
/// counts. Other files are not parsed.
fn module_reaching(cx: &Cx<'_>, files: &BTreeSet<&str>) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for lang in ["python", "rust"] {
        let vocab = vocabularies(lang, cx.packs);
        let sources: Vec<(String, String)> = files
            .iter()
            .filter_map(|p| {
                let code = cx.code.file(p)?;
                (code.language == lang).then_some(())?;
                Some(((*p).to_owned(), code.source()?))
            })
            .collect();
        let found = if lang == "python" {
            python_modules::reaching(
                &sources,
                |src| file_is_relevant(lang, src, &vocab),
                python_modules::stem,
            )
        } else {
            python_modules::reaching(
                &sources,
                |src| file_is_relevant(lang, src, &vocab) || src.contains("include!"),
                rust_modules::stem,
            )
        };
        out.extend(found);
    }
    out
}

/// The uses of the files a Rust source pulls in with a literal `include!("file.rs")` (ticket
/// 01M64230DV9KGPE0JH2D37NDVN), re-attributed to the call site; a target that cannot be read
/// becomes one computed (Unresolved) use there.
fn included_uses(cx: &Cx<'_>, file: &str, src: &str, depth: usize) -> Vec<gob_symbols::PathUse> {
    const MAX_INCLUDE_DEPTH: usize = 4;
    let dir = file.rsplit_once('/').map_or("", |(d, _)| d);
    let mut out = Vec::new();
    for inc in gob_symbols::rust_includes(src) {
        let target = rust_modules::join_normalized(dir, &inc.target)
            .filter(|t| depth < MAX_INCLUDE_DEPTH && cx.code.file(t).is_some());
        let body = target
            .as_deref()
            .and_then(|t| Some((t, cx.code.file(t)?.source()?)));
        let Some((target, text)) = body else {
            tracing::debug!(file, line = inc.line, target = %inc.target, "include! target unreadable; unresolved");
            out.push(gob_symbols::PathUse {
                offset: inc.offset,
                line: inc.line,
                spelled: "include!".to_owned(),
                path: String::new(),
                call: true,
                dynamic: true,
                external_root: false,
                computed: true,
                wildcards: Vec::new(),
                maybe: false,
            });
            continue;
        };
        tracing::debug!(
            file,
            line = inc.line,
            target,
            "include! target folded into the call site"
        );
        let mut nested = gob_symbols::path_uses("rust", &text);
        nested.extend(included_uses(cx, target, &text, depth + 1));
        for mut pu in nested {
            pu.offset = inc.offset;
            pu.line = inc.line;
            out.push(pu);
        }
    }
    out
}

/// How a name bound by `from m import *` resolves (ticket G68NRS1).
struct StarOutcome<'a> {
    /// Atoms whose vocabulary the name may denote.
    hits: Vec<&'a str>,
    /// True only when exactly one wildcard module can supply the name and it is a known
    /// vocabulary module: the use then denotes that origin symbol exactly.
    certain: bool,
}

/// What a repository module offers a wildcard importer under one name.
enum StarExport {
    /// `__all__` (or the private-underscore rule) keeps the name out of the import.
    Excluded,
    /// The module defines the name itself: a repository item, not a capability.
    Defined,
    /// The module may still re-export the name through its own imports.
    Maybe,
}

/// The repository file a wildcard module names: relative to the importer (`.x`, `..x`), or an
/// absolute dotted path from the root or beside the importer. `None` when no file matches.
fn star_repo_file(cx: &Cx<'_>, importer: &str, module: &str) -> Option<String> {
    let dir = importer.rsplit_once('/').map_or("", |(d, _)| d);
    let dots = module.chars().take_while(|c| *c == '.').count();
    let rest = module[dots..].replace('.', "/");
    let mut bases: Vec<String> = Vec::new();
    if dots > 0 {
        let mut base = dir;
        for _ in 1..dots {
            base = base.rsplit_once('/').map_or("", |(d, _)| d);
        }
        bases.push(base.to_owned());
    } else {
        bases.push(String::new());
        bases.push(dir.to_owned());
        bases.push("src".to_owned());
    }
    for base in bases {
        let join = |tail: &str| {
            [base.as_str(), tail]
                .iter()
                .filter(|p| !p.is_empty())
                .copied()
                .collect::<Vec<_>>()
                .join("/")
        };
        let candidates = if rest.is_empty() {
            vec![join("__init__.py")]
        } else {
            vec![
                join(&format!("{rest}.py")),
                join(&format!("{rest}/__init__.py")),
            ]
        };
        if let Some(found) = candidates.into_iter().find(|c| cx.code.file(c).is_some()) {
            return Some(found);
        }
    }
    None
}

/// What the repository module at `file` exports under `name` to a wildcard importer.
fn star_export(cx: &Cx<'_>, file: &str, name: &str) -> StarExport {
    let Some(code) = cx.code.file(file) else {
        return StarExport::Maybe;
    };
    let listed = code
        .source()
        .and_then(|src| gob_symbols::python_all(&src))
        .map(|all| all.contains(name));
    let excluded = match listed {
        Some(listed) => !listed,
        None => name.starts_with('_'),
    };
    if excluded {
        return StarExport::Excluded;
    }
    let defined = code.symbols().is_some_and(|fs| {
        fs.symbols.iter().any(|s| {
            matches!(s.symref.target(), Target::Symbol(segs) if segs.len() == 1 && segs[0] == name)
        })
    });
    if defined {
        StarExport::Defined
    } else {
        StarExport::Maybe
    }
}

/// Resolves a Python use of a name bound by `from m import *` to the vocabulary atoms it may
/// denote. A single known vocabulary module gives the origin symbol (`os` + `getenv` ->
/// `os.getenv`, certain). Several wildcards, a relative or unknown module, or a repository module
/// that may re-export the name leave the origin unproven: every atom whose vocabulary ends in
/// the written path is reported, uncertain, never dropped silently.
fn resolve_star<'a>(
    cx: &Cx<'_>,
    importer: &str,
    lang: &str,
    vocab: &'a [(&'a str, BTreeSet<&'a str>)],
    pu: &gob_symbols::PathUse,
) -> StarOutcome<'a> {
    let head = pu.path.split('.').next().unwrap_or(&pu.path);
    let known_module = |m: &str| {
        vocab
            .iter()
            .any(|(_, ns)| ns.iter().any(|n| n.starts_with(&format!("{m}."))))
    };
    let mut live = 0usize;
    let mut open = false;
    let mut known: Vec<&str> = Vec::new();
    for m in &pu.wildcards {
        if let Some(file) = star_repo_file(cx, importer, m) {
            match star_export(cx, &file, head) {
                StarExport::Excluded => {
                    tracing::debug!(module = %m, name = head, "wildcard module does not export the name");
                }
                StarExport::Defined => live += 1,
                StarExport::Maybe => {
                    live += 1;
                    open = true;
                }
            }
        } else if !m.starts_with('.') && known_module(m) {
            live += 1;
            known.push(m);
        } else {
            tracing::debug!(module = %m, name = head, "wildcard module is unresolved");
            live += 1;
            open = true;
        }
    }
    let mut hits: Vec<&str> = vocab
        .iter()
        .filter(|(_, names)| {
            known
                .iter()
                .any(|m| names_callee(lang, names, &format!("{m}.{}", pu.path)))
        })
        .map(|(a, _)| *a)
        .collect();
    if open {
        let tail = format!(".{}", pu.path);
        for (atom, names) in vocab {
            if !hits.contains(atom) && names.iter().any(|n| *n == pu.path || n.ends_with(&tail)) {
                hits.push(atom);
            }
        }
    }
    let certain = live == 1 && !open && known.len() == 1;
    tracing::debug!(path = %pu.path, live, open, certain, hits = hits.len(), "wildcard use resolved");
    StarOutcome { hits, certain }
}

/// True for a `<type path>.<method>` vocabulary name (`ureq::Agent.run`).
fn is_typed_name(name: &str) -> bool {
    name.contains('.') && !name.starts_with('.') && name.contains("::")
}

/// The `(callee text, certain)` pairs a typed call may name: an unprovable receiver is an
/// uncertain use of any typed method, a repository path follows its re-exports to the external
/// type it names.
fn typed_callees(
    cx: &Cx<'_>,
    rust_modules: &mut RustModules,
    path: &str,
    call: &rstype::TypedCall,
    typed_methods: &BTreeSet<&str>,
) -> Vec<(String, bool)> {
    match &call.ty {
        None if typed_methods.contains(call.method.as_str()) => {
            vec![(format!("<unresolved receiver>.{}", call.method), false)]
        }
        None => Vec::new(),
        Some(ty)
            if ty.starts_with("crate::")
                || ty.starts_with("self::")
                || ty.starts_with("super::") =>
        {
            rust_modules
                .origins(cx, path, ty)
                .into_iter()
                .map(|o| (format!("{}.{}", o.path, call.method), !o.unproven))
                .collect()
        }
        Some(ty) => vec![(format!("{ty}.{}", call.method), true)],
    }
}

/// Uses found by typed-receiver resolution (ticket YCR4M6H): method calls whose receiver type
/// resolves (`rstype`) to a path a vocabulary names as `<type path>.<method>`, such as
/// `ureq::Agent.run`. A Must use, added unless an earlier pass recorded the same atom on the same
/// line of the same unit.
fn scan_typed_receivers(cx: &Cx<'_>, uses: &mut Uses) {
    let mut seen = seen_uses(uses);
    let vocab = vocabularies("rust", cx.packs);
    if !vocab
        .iter()
        .any(|(_, names)| names.iter().any(|n| is_typed_name(n)))
    {
        return;
    }
    let typed_methods: BTreeSet<&str> = vocab
        .iter()
        .flat_map(|(_, names)| names.iter())
        .filter(|n| is_typed_name(n))
        .filter_map(|n| n.rsplit_once('.').map(|(_, m)| m))
        .collect();
    let mut rust_modules = RustModules::default();
    let mut added = 0usize;
    for path in scan_files(cx) {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if code.language != "rust" {
            continue;
        }
        let Some(src) = code.source() else { continue };
        // cheap prefilter: some typed entry's type name must occur in the file at all
        if !vocab.iter().any(|(_, names)| {
            names.iter().filter(|n| is_typed_name(n)).any(|n| {
                n.rsplit_once('.')
                    .is_some_and(|(ty, _)| src.contains(last_segment(ty)))
            })
        }) {
            continue;
        }
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for call in rstype::typed_calls(&src) {
            let callees = typed_callees(cx, &mut rust_modules, path, &call, &typed_methods);
            for (callee, certain) in callees {
                let hits: Vec<&str> = if certain || call.ty.is_some() {
                    vocab
                        .iter()
                        .filter(|(_, names)| names.contains(callee.as_str()))
                        .map(|(a, _)| *a)
                        .collect()
                } else {
                    vocab
                        .iter()
                        .filter(|(_, names)| {
                            names.iter().any(|n| {
                                is_typed_name(n)
                                    && n.rsplit_once('.').is_some_and(|(_, m)| m == call.method)
                            })
                        })
                        .map(|(a, _)| *a)
                        .collect()
                };
                if hits.is_empty() {
                    continue;
                }
                let (unit, qual) = unit_at(cx, symbols, &file_unit, call.offset);
                let Some(owner) = owner_of_use(cx, &unit, path) else {
                    tracing::debug!(file = path, unit = %unit, "typed use has no ownership unit");
                    continue;
                };
                for atom in hits {
                    if !seen.insert((unit.clone(), Some(call.line), atom.to_owned(), certain)) {
                        continue;
                    }
                    tracing::debug!(file = path, line = call.line, atom, %callee, certain, "typed-receiver capability use");
                    added += 1;
                    route(
                        uses,
                        &owner,
                        Use {
                            atom: atom.to_owned(),
                            file: path.to_owned(),
                            unit: unit.clone(),
                            qual: qual.clone(),
                            line: Some(call.line),
                            offset: Some(call.offset),
                            callee: callee.clone(),
                            certain,
                            arg: None,
                        },
                    );
                }
            }
        }
    }
    tracing::info!(added, "typed-receiver capability uses added");
}

/// Uses found by Python receiver typing (ticket 01M6422ZRSX74XT6RD0BG4T2RC): a socket method
/// called on a receiver built by a socket constructor is a Must use, however the constructor was
/// imported or the receiver copied. A receiver of unproven origin in a file that reaches the
/// `socket` module is a May use (never passed silently); one built by another constructor, or in a
/// file that never reaches `socket`, is not a socket call. Archive `extract` and `extractall` are
/// typed the same way by `tarfile.open` / `zipfile.ZipFile` receivers (ticket
/// 01M6422ZVVSTEKVMY0PR269X33).
fn scan_python_receivers(cx: &Cx<'_>, uses: &mut Uses) {
    let mut seen = seen_uses(uses);
    let mut added = 0usize;
    for path in scan_files(cx) {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if code.language != "python" {
            continue;
        }
        let Some(src) = code.source() else { continue };
        let families: Vec<&gob_ir::core_pack::ReceiverFamily> =
            gob_ir::core_pack::receiver_families("python")
                .filter(|f| f.methods.iter().any(|(_, m)| src.contains(m)))
                .collect();
        if families.is_empty() {
            continue;
        }
        let Some(symbols) = code.symbols() else {
            continue;
        };
        let found = gob_symbols::python_receiver_calls(&src);
        let file_unit = gob_symbols::Symref::file(path).to_string();
        for family in families {
            let reaches = found.reaches(family.module);
            for call in &found.calls {
                let certain = match call.ty.as_deref() {
                    Some(t) if family.ctors.contains(&t) => true,
                    None if reaches => false,
                    Some(_) | None => continue,
                };
                let (unit, qual) = unit_at(cx, symbols, &file_unit, call.offset);
                let Some(owner) = owner_of_use(cx, &unit, path) else {
                    tracing::debug!(file = path, unit = %unit, "receiver use has no ownership unit");
                    continue;
                };
                for (atom, _) in family.methods.iter().filter(|(_, m)| *m == call.method) {
                    if !seen.insert((unit.clone(), Some(call.line), (*atom).to_owned(), certain)) {
                        continue;
                    }
                    tracing::debug!(file = path, line = call.line, atom, recv = %call.recv, certain, "python receiver capability use");
                    added += 1;
                    route(
                        uses,
                        &owner,
                        Use {
                            atom: (*atom).to_owned(),
                            file: path.to_owned(),
                            unit: unit.clone(),
                            qual: qual.clone(),
                            line: Some(call.line),
                            offset: Some(call.offset),
                            callee: format!("{}.{}", call.recv, call.method),
                            certain,
                            arg: None,
                        },
                    );
                }
            }
        }
    }
    tracing::info!(added, "python receiver capability uses added");
}

fn observe(cx: &Cx<'_>) -> Uses {
    let edges: Vec<_> = cx
        .graph
        .edges_with_status()
        .iter()
        .filter(|e| is_open_call(e))
        .collect();
    let mut sources: BTreeMap<String, Option<String>> = BTreeMap::new();
    let mut uses = Uses::default();
    let mut vocabs: BTreeMap<String, Vec<(&str, BTreeSet<&str>)>> = BTreeMap::new();
    // A name-only call carries one edge per same-named method: judge the site once.
    let mut judged: BTreeSet<(String, Option<u32>, String)> = BTreeSet::new();
    for e in &edges {
        let Some(text) = &e.text else { continue };
        let path = e.from.path();
        if e.to.is_some() && !judged.insert((e.from.to_string(), e.line, text.clone())) {
            continue;
        }
        // Code no selector reaches has no units: its calls sit in the file unit.
        let from = if cx.owners.units.contains_key(&e.from.to_string()) {
            e.from.to_string()
        } else {
            gob_symbols::Symref::file(path).to_string()
        };
        let Some(owner) = owner_of_use(cx, &from, path) else {
            continue;
        };
        let callee = callee_of(text);
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if resolved_only(&code.language) {
            continue;
        }
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
                    .entry(path.to_owned())
                    .or_insert_with(|| code.source())
                    .as_deref()
                    .is_some_and(|src| pytype::is_path_expr(src, recv, 0))
        };
        let vocab = vocabs
            .entry(code.language.clone())
            .or_insert_with(|| vocabularies(&code.language, cx.packs));
        for Hit { atom, certain } in atoms_of(vocab, &code.language, callee, &mut is_path) {
            let u = Use {
                atom,
                file: path.to_owned(),
                unit: from.clone(),
                qual: match e.from.target() {
                    Target::Symbol(segs) => segs.clone(),
                    _ => Vec::new(),
                },
                line: e.line,
                offset: None,
                callee: callee.to_owned(),
                certain,
                arg: None,
            };
            route(&mut uses, &owner, u);
        }
    }
    scan_resolved(cx, &mut uses);
    scan_typed_receivers(cx, &mut uses);
    scan_python_receivers(cx, &mut uses);
    scan_structural(cx, &mut uses);
    refine_open_modes(cx, &mut uses);
    attach_args(cx, &mut uses);
    propagate_cross_node(cx, &mut uses);
    tracing::info!(
        must_nodes = uses.lo.len(),
        may_nodes = uses.hi.len(),
        unowned = uses.unowned.len(),
        unseen = uses.unseen.len(),
        "capability uses observed"
    );
    uses
}

/// A resolved call edge, indexed by the file of its caller.
struct CallHop {
    /// Qualname segments of the calling symbol (empty for module-level code).
    from: Vec<String>,
    /// The unit symref text the call sits in (`observe` rules).
    unit: String,
    line: Option<u32>,
    text: String,
    /// The callee file and qualname segments.
    to: (String, Vec<String>),
    /// True when the edge is proven (`Must` and symbolic), not a May edge or a name guess.
    proven: bool,
}

/// The uses of every set, once each, with the owner each was routed to dropped.
fn direct_uses(uses: &Uses) -> Vec<Use> {
    let mut seen = BTreeSet::new();
    let mut all = Vec::new();
    let sets = uses.lo.values().chain(uses.hi.values());
    for u in sets.flatten().chain(&uses.unowned).chain(&uses.unseen) {
        let key = (
            u.file.clone(),
            u.unit.clone(),
            u.line,
            u.atom.clone(),
            u.callee.clone(),
            u.certain,
        );
        if seen.insert(key) {
            all.push(u.clone());
        }
    }
    all
}

/// The resolved call edges of the graph with a symbol callee, by calling file.
fn call_hops(cx: &Cx<'_>) -> BTreeMap<String, Vec<CallHop>> {
    let mut by_file: BTreeMap<String, Vec<CallHop>> = BTreeMap::new();
    // A reference to a function used as a value (`let f = write_any;`, `map(write_any)`) may be
    // invoked anywhere the value flows, so it is a May hop unless the same site is also a call.
    let called: BTreeSet<(String, Option<u32>, String)> = cx
        .graph
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls)
        .filter_map(|e| Some((e.from.to_string(), e.line, e.to.as_ref()?.to_string())))
        .collect();
    for e in cx.graph.edges_with_status() {
        let (Some(to), true) = (
            &e.to,
            matches!(e.kind, EdgeKind::Calls | EdgeKind::References),
        ) else {
            continue;
        };
        let by_value = e.kind == EdgeKind::References;
        if by_value && called.contains(&(e.from.to_string(), e.line, to.to_string())) {
            continue;
        }
        let Target::Symbol(to_segs) = to.target() else {
            continue;
        };
        let path = e.from.path();
        let unit = if cx.owners.units.contains_key(&e.from.to_string()) {
            e.from.to_string()
        } else {
            gob_symbols::Symref::file(path).to_string()
        };
        by_file.entry(path.to_owned()).or_default().push(CallHop {
            from: match e.from.target() {
                Target::Symbol(segs) => segs.clone(),
                _ => Vec::new(),
            },
            unit,
            line: e.line,
            text: e
                .text
                .clone()
                .or_else(|| e.name.clone())
                .unwrap_or_default(),
            to: (to.path().to_owned(), to_segs.clone()),
            proven: !by_value
                && e.status == gob_ir::Status::Must
                && e.basis == gob_symbols::EdgeBasis::Symbolic,
        });
    }
    by_file
}

/// Carry the capability uses of functions owned by another node to the nodes that call them.
///
/// For each resolved call edge whose callee unit has a different owner than the calling unit, a
/// traversal from the callee over every resolved call edge (visited set, so cycles end) collects
/// the uses of the callee and of what it reaches; those not already owned by the caller's owner
/// become uses of the caller's unit at the call line. Certainty is the conjunction of every hop.
fn propagate_cross_node(cx: &Cx<'_>, uses: &mut Uses) {
    let direct = direct_uses(uses);
    if direct.is_empty() {
        return;
    }
    let mut by_file: BTreeMap<&str, Vec<(usize, &Use)>> = BTreeMap::new();
    for (i, u) in direct.iter().enumerate() {
        by_file.entry(u.file.as_str()).or_default().push((i, u));
    }
    let hops = call_hops(cx);
    // Every per-use fact the carry loop compares is interned to an integer once, so the loop
    // over (edges x reached uses) does no string work for a use it drops or has already carried.
    let mut strings = Interner::default();
    let mut owners: Vec<Owner> = Vec::new();
    let unit_owners: Vec<Option<usize>> = direct
        .iter()
        .map(|u| owner_of_use(cx, &u.unit, &u.file).map(|o| owner_index(&mut owners, o)))
        .collect();
    let atom_ids: Vec<u32> = direct.iter().map(|u| strings.id(&u.atom)).collect();
    let site_ids: Vec<u32> = direct.iter().map(|u| strings.id(&u.site())).collect();
    let mut pairs = 0usize;
    let mut walk = Walk::default();
    let mut carried: Vec<(usize, Use)> = Vec::new();
    let mut seen_carried: HashSet<CarryKey> = HashSet::new();
    for (file, edges) in &hops {
        for edge in edges {
            let (callee_file, callee_segs) = &edge.to;
            let Some(caller) = owner_of_use(cx, &edge.unit, file) else {
                continue;
            };
            let callee_unit = callee_unit_text(cx, callee_file, callee_segs);
            let Some(callee_owner) = owner_of_use(cx, &callee_unit, callee_file) else {
                continue;
            };
            if callee_owner == caller {
                continue;
            }
            // The traversal from a callee depends only on (callee, proven), never on the caller,
            // so it is computed once and shared by every edge into that callee.
            let reached = walk.closure(&edge.to, edge.proven, &mut |target| {
                expand_target(cx, &by_file, &hops, target)
            });
            let caller_id = owner_index(&mut owners, caller);
            pairs += reached.len();
            let unit_id = strings.id(&edge.unit);
            let text_id = strings.id(&edge.text);
            for &(idx, certain) in reached.iter() {
                if unit_owners[idx] == Some(caller_id) {
                    continue;
                }
                let u = &direct[idx];
                let certain = u.certain && certain;
                let key = (
                    unit_id,
                    edge.line,
                    atom_ids[idx],
                    text_id,
                    site_ids[idx],
                    certain,
                );
                if !seen_carried.insert(key) {
                    continue;
                }
                let mut moved = u.clone();
                moved.callee = format!("{} -> {}", edge.text, u.site());
                moved.file.clone_from(file);
                moved.unit.clone_from(&edge.unit);
                moved.qual.clone_from(&edge.from);
                moved.line = edge.line;
                moved.certain = certain;
                carried.push((caller_id, moved));
            }
        }
    }
    tracing::debug!(
        pairs,
        closures = walk.closures_computed,
        expansions = walk.expansions_computed,
        "cross-node call traversals computed"
    );
    tracing::info!(
        carried = carried.len(),
        "capability uses carried across calls into other nodes"
    );
    for (owner, u) in carried {
        route(uses, &owners[owner], u);
    }
}

/// The dedupe key of a carried use: (caller unit, line, atom, edge text, site, certainty), interned.
type CarryKey = (u32, Option<u32>, u32, u32, u32, bool);

/// Maps each distinct string to a small integer id.
#[derive(Default)]
struct Interner(HashMap<String, u32>);

impl Interner {
    /// The id of `s`, assigning the next free one on first sight.
    fn id(&mut self, s: &str) -> u32 {
        if let Some(&i) = self.0.get(s) {
            return i;
        }
        let i = u32::try_from(self.0.len()).unwrap_or(u32::MAX);
        self.0.insert(s.to_owned(), i);
        i
    }
}

/// The index of `owner` in `owners`, appending it on first sight (owners are few).
fn owner_index(owners: &mut Vec<Owner>, owner: Owner) -> usize {
    owners.iter().position(|o| *o == owner).unwrap_or_else(|| {
        owners.push(owner);
        owners.len() - 1
    })
}

/// A call-graph target: the callee file and qualname segments.
type CallTarget = (String, Vec<String>);

/// What one target contributes to a traversal, independent of who called it.
#[derive(Default)]
struct Expansion {
    /// Indices (into the direct uses) of the uses sitting under the target and let through.
    uses: Vec<usize>,
    /// The call edges leaving the target (empty at a provider boundary) with their proven flag.
    nexts: Vec<(CallTarget, bool)>,
}

/// An [`Expansion`] with its edge targets interned to ids, so a traversal never compares strings.
struct Interned {
    uses: Vec<usize>,
    nexts: Vec<(u32, bool)>,
}

/// Reached (use index, certain) pairs of one closure, shared between callers.
type Closure = std::rc::Rc<Vec<(usize, bool)>>;

/// Memoized cross-node traversals: expansions per target and closures per `(target, proven)`.
#[derive(Default)]
struct Walk {
    /// Target -> id, in first-seen order.
    ids: HashMap<CallTarget, u32>,
    /// The expansion of each target id, once computed.
    expansions: Vec<Option<std::rc::Rc<Interned>>>,
    /// The target of each id (to expand it on first reach).
    targets: Vec<CallTarget>,
    closures: HashMap<(u32, bool), Closure>,
    /// How many traversals ran (the work the memo exists to bound).
    closures_computed: usize,
    /// How many targets were expanded.
    expansions_computed: usize,
}

impl Walk {
    /// The id of `target`, assigning the next free one on first sight.
    fn id(&mut self, target: &CallTarget) -> u32 {
        if let Some(&i) = self.ids.get(target) {
            return i;
        }
        let i = u32::try_from(self.targets.len()).unwrap_or(u32::MAX);
        self.ids.insert(target.clone(), i);
        self.targets.push(target.clone());
        self.expansions.push(None);
        i
    }

    /// The `(use index, certainty)` pairs reached from `start` over the call edges, in walk order.
    fn closure(
        &mut self,
        start: &CallTarget,
        proven: bool,
        expand: &mut dyn FnMut(&CallTarget) -> Expansion,
    ) -> std::rc::Rc<Vec<(usize, bool)>> {
        let start = self.id(start);
        let key = (start, proven);
        if let Some(hit) = self.closures.get(&key) {
            return hit.clone();
        }
        self.closures_computed += 1;
        // target -> best certainty seen; an upgrade re-queues, so the walk is monotone.
        let mut visited: HashMap<u32, bool> = HashMap::new();
        let mut queue = vec![(start, proven)];
        let mut reached = Vec::new();
        while let Some((target, certain)) = queue.pop() {
            match visited.get(&target) {
                Some(&prev) if prev || !certain => continue,
                _ => {
                    visited.insert(target, certain);
                }
            }
            let exp = if let Some(e) = &self.expansions[target as usize] {
                e.clone()
            } else {
                self.expansions_computed += 1;
                let raw = expand(&self.targets[target as usize]);
                let nexts = raw.nexts.iter().map(|(t, p)| (self.id(t), *p)).collect();
                let e = std::rc::Rc::new(Interned {
                    uses: raw.uses,
                    nexts,
                });
                self.expansions[target as usize] = Some(e.clone());
                e
            };
            reached.extend(exp.uses.iter().map(|&i| (i, certain)));
            for &(next, next_proven) in &exp.nexts {
                queue.push((next, certain && next_proven));
            }
        }
        let reached = std::rc::Rc::new(reached);
        self.closures.insert(key, reached.clone());
        reached
    }
}

/// Expand one target: the direct uses under it that its provider boundary lets through, and the
/// call edges leaving it.
fn expand_target(
    cx: &Cx<'_>,
    by_file: &BTreeMap<&str, Vec<(usize, &Use)>>,
    hops: &BTreeMap<String, Vec<CallHop>>,
    target: &CallTarget,
) -> Expansion {
    let (tfile, tsegs) = target;
    let boundary = boundary_atoms(cx, tfile, tsegs);
    if let Some(atoms) = &boundary {
        tracing::debug!(file = %tfile, symbol = %tsegs.join("."), ?atoms, "provider boundary stops the walk");
    }
    let uses = by_file
        .get(tfile.as_str())
        .into_iter()
        .flatten()
        .filter(|(_, u)| u.qual.starts_with(tsegs))
        .filter(|(_, u)| {
            boundary
                .as_ref()
                .is_none_or(|atoms| atoms.iter().any(|a| provided_covers(a, &u.atom)))
        })
        .map(|&(i, _)| i)
        .collect();
    let nexts = if boundary.is_some() {
        Vec::new()
    } else {
        by_file_hops(hops, tfile, tsegs)
            .map(|h| (h.to.clone(), h.proven))
            .collect()
    };
    Expansion { uses, nexts }
}

/// True when `atom` is the provided atom `provided` or one of its children (`fs` provides `fs.write`).
fn provided_covers(provided: &str, atom: &str) -> bool {
    let granted = gob_ir::registry::canonical(provided).unwrap_or(provided);
    granted == atom
        || atom
            .strip_prefix(granted)
            .is_some_and(|rest| rest.starts_with('.'))
}

/// The atoms the node that owns `segs` in `file` provides there (`provides C via S` with S
/// selecting the symbol), or `None` when the symbol is not a declared boundary.
fn boundary_atoms<'m>(cx: &'m Cx<'_>, file: &str, segs: &[String]) -> Option<Vec<&'m str>> {
    let unit = callee_unit_text(cx, file, segs);
    let Some(Owner::Must(node)) = owner_of_use(cx, &unit, file) else {
        return None;
    };
    node_atoms(cx, node.as_str(), file, segs)
}

/// The atoms `node` provides via a selector covering `segs` in `file`, `None` when there are none.
fn node_atoms<'m>(cx: &'m Cx<'_>, node: &str, file: &str, segs: &[String]) -> Option<Vec<&'m str>> {
    let atoms: Vec<&str> = cx
        .model
        .entities
        .values()
        .filter(|e| e.anchor == node)
        .flat_map(|e| &e.providers)
        .filter(|p| selects_unit_or_enclosing(&p.via, file, segs))
        .map(|p| p.atom.as_str())
        .collect();
    (!atoms.is_empty()).then_some(atoms)
}

/// The hops whose calling symbol is `segs` or nested inside it, in `file`.
fn by_file_hops<'a>(
    hops: &'a BTreeMap<String, Vec<CallHop>>,
    file: &str,
    segs: &[String],
) -> impl Iterator<Item = &'a CallHop> {
    let segs = segs.to_vec();
    hops.get(file)
        .into_iter()
        .flatten()
        .filter(move |h| h.from.starts_with(&segs))
}

/// The unit symref text of the symbol `segs` in `file`: the nearest enclosing unit, else the file.
fn callee_unit_text(cx: &Cx<'_>, file: &str, segs: &[String]) -> String {
    for n in (1..=segs.len()).rev() {
        let r = gob_symbols::Symref::symbol(file, segs[..n].to_vec()).to_string();
        if cx.owners.units.contains_key(&r) {
            return r;
        }
    }
    gob_symbols::Symref::file(file).to_string()
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
fn observed_arg(
    kind: ArgKind,
    call: &gob_symbols::CallArgs,
    dir: Option<CopyEnd>,
) -> Option<String> {
    use gob_symbols::ArgValue;
    let first = match dir {
        // `shutil.copy(src, dst)`: the read is of `src` and the write is of `dst`.
        Some(end) => {
            if call.splat {
                return None;
            }
            let (slot, kw) = match end {
                CopyEnd::Source => (0, "src"),
                CopyEnd::Dest => (1, "dst"),
            };
            call.kwargs
                .get(kw)
                .or_else(|| call.args.get(slot))?
                .as_ref()?
        }
        None => call.args.first()?.as_ref()?,
    };
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

/// Which end of a copy a use is about.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CopyEnd {
    /// The file read from (`src`, the first argument).
    Source,
    /// The file written to (`dst`, the second argument).
    Dest,
}

/// Copy calls whose first argument is the source and second the destination
/// (ticket 01M5XNNHY7KZDKBZKK2MM08TTF); `shutil.move` and `os.rename` also remove the source, so they stay undirected.
const COPY_CALLS: &[&str] = &[
    "shutil.copy",
    "shutil.copy2",
    "shutil.copyfile",
    "shutil.copytree",
    "fs::copy",
];

/// The end of a copy that the `atom` use of `callee` concerns, or `None` for any other call.
fn copy_end(atom: &str, callee: &str) -> Option<CopyEnd> {
    let tail = |n: &str| {
        callee == n || callee.ends_with(&format!(".{n}")) || callee.ends_with(&format!("::{n}"))
    };
    if !COPY_CALLS.iter().any(|n| tail(n)) {
        return None;
    }
    match atom {
        "fs.read" => Some(CopyEnd::Source),
        "fs.write" => Some(CopyEnd::Dest),
        _ => None,
    }
}

/// True when the vocabulary entry reaches the call through a receiver, so the first call argument
/// is not the path, name or program the atom is about (`Path.read_text`, `.read_text`).
fn receiver_entry(callee: &str) -> bool {
    callee.starts_with("Path.")
        || callee.starts_with('.')
        || callee.starts_with("?.")
        || is_typed_name(callee)
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
    if scoped {
        attach_scoped_args(cx, uses);
    }
}

/// Parse each used file once and attach the folded argument of the one call matching each use.
fn attach_scoped_args(cx: &Cx<'_>, uses: &mut Uses) {
    let mut parsed: BTreeMap<String, BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>>> =
        BTreeMap::new();
    let (mut known, mut unknown) = (0usize, 0usize);
    for u in uses.lo.values_mut().chain(uses.hi.values_mut()).flatten() {
        let Some(kind) = use_arg_kind(cx.packs, &u.atom) else {
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
        let dir = copy_end(&u.atom, &u.callee);
        let vals: BTreeSet<Option<String>> =
            cands.iter().map(|c| observed_arg(kind, c, dir)).collect();
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

/// What the mode argument of a Python `open` says.
#[derive(Debug, PartialEq, Eq)]
enum OpenMode {
    /// Read only (no mode, or a literal without `w`, `a`, `x` or `+`).
    Read,
    /// A literal mode that writes; `reads` when it also reads (`r+`, `w+`).
    Write { reads: bool },
    /// A mode that does not fold: it may write.
    Unknown,
}

/// Classify the mode of the `open` call `c`; a receiver form (`Path.open`) takes the mode first.
fn open_mode(c: &gob_symbols::CallArgs, receiver: bool) -> OpenMode {
    use gob_symbols::ArgValue;
    let slot = usize::from(!receiver);
    let given = match c.kwargs.get("mode") {
        Some(v) => Some(v),
        None => c.args.get(slot),
    };
    if c.splat {
        // `open(*a)` / `open(**kw)` can supply the mode from anywhere.
        return OpenMode::Unknown;
    }
    match given {
        None => OpenMode::Read,
        Some(Some(ArgValue::Str(m))) => {
            let plus = m.contains('+');
            if plus || m.contains(['w', 'a', 'x']) {
                OpenMode::Write {
                    reads: plus || m.contains('r'),
                }
            } else {
                OpenMode::Read
            }
        }
        Some(_) => OpenMode::Unknown,
    }
}

/// Refine one Rust use of an `OpenOptions` builder by its flags (ticket 01M5XNNHY7KZDKBZKK2MM08TTF); returns
/// whether to keep `u`. The builder constructors sit in both `fs.read` and `fs.write` vocabulary, so
/// each half is kept, dropped, or re-added as a May use per the proven flags.
fn refine_open_options(code: &CodeFile, u: &Use, added: &mut Vec<Use>) -> bool {
    use argdet::Tri;
    let is_builder = u.callee.ends_with("OpenOptions::new") || u.callee.ends_with("File::options");
    let (true, Some(src)) = (is_builder, code.source()) else {
        return true;
    };
    let site = match (u.offset, u.line) {
        (Some(offset), _) => argdet::Site::Offset(offset),
        (None, Some(line)) => argdet::Site::Line(line, &u.callee),
        (None, None) => return true,
    };
    let Some(v) = argdet::rust_open_options(&src, site) else {
        return true;
    };
    tracing::debug!(file = %u.file, ?site, atom = %u.atom, ?v, "open-options flags");
    match u.atom.as_str() {
        "fs.read" => v.reads != Tri::No,
        "fs.write" => match v.writes {
            Tri::Yes => true,
            Tri::No => false,
            Tri::Maybe => {
                added.push(Use {
                    certain: false,
                    ..u.clone()
                });
                false
            }
        },
        _ => true,
    }
}

/// Make a Python `open` mode-aware (ticket 01M4HYH9CDNJSYEZQGKRZA7WX2): `open(p, 'w')` is `fs.write` and no longer
/// `fs.read` (unless the mode also reads), and a mode that is not a literal adds a May `fs.write`
/// beside the read. A use whose call cannot be found on its line stays a plain read.
fn refine_open_modes(cx: &Cx<'_>, uses: &mut Uses) {
    let mut parsed: BTreeMap<String, BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>>> =
        BTreeMap::new();
    let (mut writes, mut mays) = (0usize, 0usize);
    let mut refine = |bucket: &mut Vec<Use>| -> Vec<Use> {
        let mut added = Vec::new();
        bucket.retain(|u| {
            let Some(code) = cx.code.file(&u.file) else {
                return true;
            };
            if code.language == "rust" {
                return refine_open_options(code, u, &mut added);
            }
            if u.atom != "fs.read" || last_segment(&u.callee) != "open" || code.language != "python"
            {
                return true;
            }
            let Some(line) = u.line else {
                return true;
            };
            let calls = parsed.entry(u.file.clone()).or_insert_with(|| {
                let mut m: BTreeMap<(u32, String), Vec<gob_symbols::CallArgs>> = BTreeMap::new();
                if let Some(src) = code.source() {
                    for c in gob_symbols::call_args(&code.language, &src) {
                        m.entry((c.line, String::new())).or_default().push(c);
                    }
                }
                m
            });
            // Pin to the exact call by byte offset (so `from io import open as o` is found); a use
            // without an offset falls back to the calls on its line whose callee ends in `open`.
            let cands: Vec<&gob_symbols::CallArgs> = calls
                .get(&(line, String::new()))
                .into_iter()
                .flatten()
                .filter(|c| match u.offset {
                    Some(o) => c.offset == o,
                    None => last_segment(&c.callee) == "open",
                })
                .collect();
            if cands.is_empty() {
                return true;
            }
            let receiver = !matches!(u.callee.as_str(), "open" | "io.open" | "codecs.open");
            let modes: Vec<OpenMode> = cands.iter().map(|c| open_mode(c, receiver)).collect();
            let mode = match modes.as_slice() {
                [only] => only,
                _ => &OpenMode::Unknown,
            };
            match mode {
                OpenMode::Read => true,
                OpenMode::Write { reads } => {
                    writes += 1;
                    tracing::debug!(file = %u.file, line, callee = %u.callee, reads, "open mode writes: fs.write");
                    added.push(Use { atom: "fs.write".to_owned(), ..u.clone() });
                    *reads
                }
                OpenMode::Unknown => {
                    mays += 1;
                    tracing::debug!(file = %u.file, line, callee = %u.callee, "open mode not a literal: May fs.write");
                    added.push(Use { atom: "fs.write".to_owned(), certain: false, ..u.clone() });
                    true
                }
            }
        });
        added
    };
    let mut to_hi: Vec<(String, Use)> = Vec::new();
    for (node, bucket) in &mut uses.lo {
        for u in refine(bucket) {
            if u.certain {
                bucket.push(u);
            } else {
                to_hi.push((node.clone(), u));
            }
        }
    }
    for bucket in uses.hi.values_mut() {
        let add = refine(bucket);
        bucket.extend(add);
    }
    let extra = refine(&mut uses.unowned);
    uses.unowned.extend(extra);
    for (node, u) in to_hi {
        uses.hi.entry(node).or_default().push(u);
    }
    tracing::info!(writes, mays, "open modes refined");
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

/// The argument kind of `atom`: the registry's, else the one an enabled pack declares for it
/// (ticket 01M61Y35AKW4QDRE70W6HFQAJ5).
fn use_arg_kind(packs: &BTreeMap<String, PackPin>, atom: &str) -> Option<ArgKind> {
    arg_kind(atom).or_else(|| pack_arg_kind(packs, atom))
}

/// The `Judgement` of the use against one argument-scoped grant: any grant argument that matches
/// is `Match`; otherwise `Unknown` if any could not be decided or the use has no folded argument.
fn judge_use(packs: &BTreeMap<String, PackPin>, grant: &Grant, atom: &str, u: &Use) -> Judgement {
    let (Some(kind), Some(obs)) = (use_arg_kind(packs, atom), u.arg.as_deref()) else {
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
fn coverage(packs: &BTreeMap<String, PackPin>, grants: &[Grant], atom: &str, u: &Use) -> Coverage {
    let mut granted: Vec<String> = Vec::new();
    let mut unknown = false;
    for g in grants.iter().filter(|g| live(g, u) && covers(g, atom, u)) {
        if g.args.is_empty() {
            return Coverage::Covered;
        }
        match judge_use(packs, g, atom, u) {
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

/// The profile a source file belongs to: `test` for test code, `prod` otherwise; the
/// `GRIMBLE_PROFILE` environment variable overrides it.
// frob:ticket 01M5XNNJTK08K3CB98MCT14W34
pub fn profile_of(file: &str) -> String {
    if let Ok(p) = std::env::var("GRIMBLE_PROFILE") {
        if !p.is_empty() {
            return p;
        }
    }
    let name = file.rsplit('/').next().unwrap_or(file);
    let stem = name.split('.').next().unwrap_or(name);
    let is_test = file.starts_with("tests/")
        || file.contains("/tests/")
        || stem.ends_with("_test")
        || stem.starts_with("test_");
    if is_test { "test" } else { "prod" }.to_owned()
}

/// Today as an ISO date, comparable with a grant's `until`.
fn today_iso() -> String {
    gob_time::Clock::today(&gob_time::SystemClock::pin()).to_string()
}

/// True when `grant` is in force for the use `u`: not expired, and scoped to its profile.
// frob:ticket 01M5XNNJTK08K3CB98MCT14W34
fn live(grant: &Grant, u: &Use) -> bool {
    if grant.until.is_some() && grant.expired(&today_iso()) {
        return false;
    }
    grant.in_profile(&profile_of(&u.file))
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
        write!(s, " (+{} more)", uses.len() - EXAMPLES).ok();
    }
    s
}

/// The narrowest `may` line that would allow `u`: its atom, the observed argument when it is
/// statically known and the atom takes one, scoped `at` the file and enclosing symbol of the call
/// (CAP diagnostics, ticket JMQ3SX6). Copy-pasteable into the node.
fn suggested_grant(packs: &BTreeMap<String, PackPin>, u: &Use) -> String {
    let arg = match (use_arg_kind(packs, &u.atom), u.arg.as_deref()) {
        (Some(_), Some(a)) => format!("({a:?})"),
        _ => String::new(),
    };
    let at = if u.qual.is_empty() {
        u.file.clone()
    } else {
        format!("{}::{}", u.file, u.qual.join("::"))
    };
    format!("may {}{arg} at {at:?};", u.atom)
}

/// Every call site of `uses` as `file:line callee`, then the distinct narrowest grants that would
/// allow them, so a finding never nudges toward a broad grant (ticket JMQ3SX6).
fn sites_and_fixes(packs: &BTreeMap<String, PackPin>, uses: &[&Use]) -> String {
    let sites = uses.iter().map(|u| u.site()).collect::<Vec<_>>().join("; ");
    let fixes: BTreeSet<String> = uses.iter().map(|u| suggested_grant(packs, u)).collect();
    tracing::debug!(
        sites = uses.len(),
        fixes = fixes.len(),
        "CAP001 narrowest grants"
    );
    format!(
        "{sites}; narrowest grant: {}",
        fixes.into_iter().collect::<Vec<_>>().join(" ")
    )
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
            if coverage(cx.packs, &e.grants, &u.atom, u) != Coverage::Uncovered {
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

/// How loudly CAP001 reports a denied use of one atom.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Level {
    /// An Error finding.
    Error,
    /// An Unresolved finding: the use is reported but does not fail the gate on its own.
    Warn,
}

/// The CAP001 level of `atom`: `[packs.severity]`, else the atom row, else Error (K4EMP90).
fn level_of(cx: &Cx<'_>, atom: &str) -> Level {
    let canon = gob_ir::registry::canonical(atom).unwrap_or(atom);
    let configured = cx
        .pack_severity
        .get(atom)
        .or_else(|| cx.pack_severity.get(canon))
        .and_then(|m| m.get("CAP001").cloned())
        .or_else(|| {
            gob_ir::registry::atom_row(canon).and_then(|r| r.severity.get("CAP001").cloned())
        });
    let level = match configured.as_deref() {
        None | Some("error") => Level::Error,
        Some("warn") => Level::Warn,
        Some(other) => {
            tracing::warn!(
                atom,
                level = other,
                "unknown CAP001 severity; treated as error"
            );
            Level::Error
        }
    };
    tracing::debug!(atom, ?level, "CAP001 level resolved");
    level
}

/// The atom row's rationale and safer alternative as a message suffix; empty when the row has none.
fn advice(atom: &str) -> String {
    let Some(row) = gob_ir::registry::atom_row(atom) else {
        return String::new();
    };
    let parts: Vec<String> = [
        row.rationale
            .filter(|r| !r.is_empty())
            .map(|r| format!("why: {r}")),
        row.safer_alternative
            .filter(|a| !a.is_empty())
            .map(|a| format!("safer: {a}")),
    ]
    .into_iter()
    .flatten()
    .collect();
    if parts.is_empty() {
        String::new()
    } else {
        format!(" [{}]", parts.join("; "))
    }
}

/// Reports a certain denied use at the atom's level: Error, or Unresolved when the row says warn.
fn deny(
    out: &mut Output,
    level: Level,
    message: String,
    anchor: &str,
    site: Option<(&str, (usize, usize))>,
) {
    match level {
        Level::Error => out.fire("CAP001", Severity::Error, message, anchor, site),
        Level::Warn => out.unresolved(
            "CAP001",
            Reason::MayOnlyOwner,
            &format!("{message} (warn-level atom)"),
            anchor,
            site,
        ),
    }
}

/// Argument findings keyed by (atom, observed argument or None when unfolded, granted arguments).
type ByArg<'a> = BTreeMap<(&'a str, Option<String>, Vec<String>), Vec<&'a Use>>;

#[allow(clippy::too_many_lines)] // one pass per node: exact, argument and may findings together
fn cap001(cx: &Cx<'_>, uses: &Uses, excuses: &[Excuse], today: gob_time::Day, out: &mut Output) {
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
                if crate::model::silenced(e, "CAP001", &u.atom, today) {
                    continue;
                }
                // One root cause, one finding: a use in excused code is CAP004, not CAP001.
                if is_excused(excuses, u) {
                    continue;
                }
                match coverage(cx.packs, &e.grants, &u.atom, u) {
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
                        deny(
                            out,
                            level_of(cx, atom),
                            format!(
                                "`{}` uses `{atom}` with argument {obs:?}, outside every granted argument ({allowed}) ({} use(s)): {}{}",
                                e.anchor,
                                us.len(),
                                sites_and_fixes(cx.packs, &us),
                                advice(atom)
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
                    deny(
                        out,
                        level_of(cx, atom),
                        format!(
                            "`{}` uses `{atom}` with no grant ({} use(s)): {}{}",
                            e.anchor,
                            us.len(),
                            sites_and_fixes(cx.packs, &us),
                            advice(atom)
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

/// CAP001 for code no node owns: an implicit node with no grants, so every observed use is denied.
///
/// A certain use in `Foreign` code is an Error; an unresolved receiver, or code whose owner is
/// hidden (an unseen remainder), is Unresolved, never silent. Frob-owned and `[check] exclude`d
/// files are not in the walk of uses (see `owner_of_use`).
fn cap001_unowned(cx: &Cx<'_>, uses: &Uses, out: &mut Output) {
    out.count("CAP001", 1);
    // (atom, receiver unresolved, owner hidden) -> uses
    let mut by_atom: BTreeMap<(&str, bool, bool), Vec<&Use>> = BTreeMap::new();
    for (set, hidden) in [(&uses.unowned, false), (&uses.unseen, true)] {
        for u in set {
            by_atom
                .entry((u.atom.as_str(), !u.certain, hidden))
                .or_default()
                .push(u);
        }
    }
    for ((atom, unresolved_receiver, hidden), us) in by_atom {
        if !unresolved_receiver && !hidden {
            let anchor = format!("cap/unowned/{atom}");
            deny(
                out,
                level_of(cx, atom),
                format!(
                    "unowned code uses `{atom}`; no node owns it, so nothing grants it ({} use(s)): {}{}",
                    us.len(),
                    list(&us),
                    advice(atom)
                ),
                &anchor,
                None,
            );
        } else if hidden {
            let anchor = format!("cap/unowned/{atom}/hidden");
            out.unresolved(
                "CAP001",
                Reason::UnseenRemainder,
                &format!(
                    "`{atom}` is used in code whose owner cannot be named (unseen remainder): {}",
                    list(&us)
                ),
                &anchor,
                None,
            );
        } else {
            let anchor = format!("cap/unowned/{atom}/receiver");
            out.unresolved(
                "CAP001",
                Reason::UnresolvedEdge,
                &format!(
                    "`{atom}` may be used by unowned code, which has no grant; the receiver type of the call could not be resolved: {}",
                    list(&us)
                ),
                &anchor,
                None,
            );
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

/// Count of `select_files` walks CAP002 has run in this process, a seam for the once-per-grant regression test.
pub static CAP002_SELECT_FILES_CALLS: std::sync::atomic::AtomicUsize =
    std::sync::atomic::AtomicUsize::new(0);

/// One grant's cell in the capability matrix: the public shape shared by CAP002 and the matrix verb.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GrantCell {
    /// Anchor of the node holding the grant.
    pub node: String,
    /// The canonical atom the grant names.
    pub atom: String,
    /// The grant as written, for messages.
    pub written: String,
    /// Source file of the grant.
    pub file: String,
    /// Byte range of the grant in `file`.
    pub span: (usize, usize),
    /// `Uses` (observed), `DeclaredUnused` (absence is Exact) or `Unknown` (absence not judgeable).
    pub cell: Cell,
}

/// The matrix cell of every judgeable grant, the single source CAP002 reads (counts subjects and
/// reports undetectable pack atoms into `out` as a side effect).
pub fn grant_cells(cx: &Cx<'_>, out: &mut Output) -> Vec<GrantCell> {
    grant_cells_with(cx, &observe(cx), out)
}

/// `grant_cells` over already-observed uses, so `evaluate` observes once for CAP001 and CAP002.
fn grant_cells_with(cx: &Cx<'_>, uses: &Uses, out: &mut Output) -> Vec<GrantCell> {
    let mut cells = Vec::new();
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
            // One walk-wide selection per grant, not one per owned file (that was quadratic).
            let selected: Option<BTreeSet<String>> = g.at.as_ref().map(|sel| {
                CAP002_SELECT_FILES_CALLS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                gob_walk::select_files(sel, &cx.code.walk)
                    .into_iter()
                    .map(|m| m.path)
                    .collect()
            });
            let in_scope = |f: &str| selected.as_ref().is_none_or(|set| set.contains(f));
            let use_in_scope = |u: &Use| g.at.as_ref().is_none_or(|sel| selects_use(sel, u));
            let scoped: Vec<&str> = files.iter().copied().filter(|f| in_scope(f)).collect();
            report_no_detector(cx, e, &atoms, &scoped, &mut reported, site, out);
            let observed = [&uses.lo, &uses.hi].iter().any(|by_node| {
                by_node.get(&e.anchor).is_some_and(|us| {
                    us.iter()
                        .any(|u| atoms.contains(&u.atom) && use_in_scope(u))
                })
            });
            let cell_of = |cell| GrantCell {
                node: e.anchor.clone(),
                atom: g.atom.clone(),
                written: g.written.clone(),
                file: g.file.clone(),
                span: (g.span.start, g.span.end),
                cell,
            };
            if observed {
                cells.push(cell_of(Cell::Uses));
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
                cells.push(cell_of(Cell::Unknown));
                continue;
            }
            cells.push(cell_of(Cell::DeclaredUnused));
        }
    }
    tracing::debug!(cells = cells.len(), "grant matrix cells");
    cells
}

/// The template excuses of the model with their `for` selectors resolved to the files they cover.
fn template_excuses(cx: &Cx<'_>) -> Vec<Excuse> {
    let mut out = Vec::new();
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Template)
    {
        for x in &e.excuses {
            let files: BTreeSet<String> = gob_walk::select_files(&x.selector, &cx.code.walk)
                .into_iter()
                .map(|m| m.path)
                .collect();
            tracing::debug!(template = %e.anchor, atom = %x.atom, files = files.len(), "template excuse resolved");
            out.push(Excuse {
                template: e.anchor.clone(),
                atom: gob_ir::registry::canonical(&x.atom)
                    .unwrap_or(&x.atom)
                    .to_owned(),
                files,
                because: x.because.clone(),
            });
        }
    }
    out
}

/// The matrix view of `u`: certain only when `certain` holds and the use itself is certain.
fn use_site(u: &Use, certain: bool) -> UseSite {
    UseSite {
        atom: u.atom.clone(),
        file: u.file.clone(),
        site: u.site(),
        certain: certain && u.certain,
    }
}

/// True when some template excuse covers the atom of `u` at its file (the use is CAP004's, not CAP001's).
fn is_excused(excuses: &[Excuse], u: &Use) -> bool {
    !excuses.is_empty() && !excuse::cap004("", &[use_site(u, true)], excuses).is_empty()
}

/// CAP004 (packs-and-plugins.md 6.7, binding.md 7.2 item 3): a template excuse never masks an
/// observed use. A certain Must-owned use in excused code is an Error; a May use (unresolved
/// receiver, or code owned only at May) is Unresolved, since an excuse is not evidence of absence.
fn cap004(cx: &Cx<'_>, uses: &Uses, excuses: &[Excuse], out: &mut Output) {
    out.count("CAP004", excuses.len());
    if excuses.is_empty() {
        return;
    }
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        for (set, must) in [(&uses.lo, true), (&uses.hi, false)] {
            let Some(found) = set.get(&e.anchor) else {
                continue;
            };
            let sites: Vec<UseSite> = found.iter().map(|u| use_site(u, must)).collect();
            for c in excuse::cap004(&e.anchor, &sites, excuses) {
                let list = c
                    .sites
                    .iter()
                    .take(EXAMPLES)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join("; ");
                let what = format!(
                    "`{}` uses `{}` in code a template excuse covers (because \"{}\"); an excuse never masks an observed use: {list}",
                    c.node, c.atom, c.because
                );
                if c.certain {
                    let anchor = format!("cap/{}/{}/excused", c.node, c.atom);
                    out.fire("CAP004", Severity::Error, what, &anchor, None);
                } else if must {
                    let anchor = format!("cap/{}/{}/excused/receiver", c.node, c.atom);
                    out.unresolved("CAP004", Reason::UnresolvedEdge, &what, &anchor, None);
                } else {
                    let anchor = format!("cap/{}/{}/excused/may", c.node, c.atom);
                    out.unresolved("CAP004", Reason::MayOnlyOwner, &what, &anchor, None);
                }
            }
        }
    }
}

/// The `may` grants of every code-owning node with their scope resolved to files: the grant's `at`
/// selection, or every file the node owns (Must or May).
fn grant_scopes(cx: &Cx<'_>) -> Vec<GrantScope> {
    let mut out = Vec::new();
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        if e.grants.is_empty() {
            continue;
        }
        let owned: BTreeSet<String> = cx
            .owners
            .units
            .values()
            .filter(|uo| match &uo.merged.owner {
                Owner::Must(n) => n.as_str() == e.anchor,
                Owner::May(ns) => ns.iter().any(|n| n.as_str() == e.anchor),
                _ => false,
            })
            .map(|uo| uo.file.clone())
            .collect();
        for g in &e.grants {
            let files = match &g.at {
                Some(sel) => gob_walk::select_files(sel, &cx.code.walk)
                    .into_iter()
                    .map(|m| m.path)
                    .collect(),
                None => owned.clone(),
            };
            out.push(GrantScope {
                node: e.anchor.clone(),
                atom: gob_ir::registry::canonical(&g.atom)
                    .unwrap_or(&g.atom)
                    .to_owned(),
                written: g.written.clone(),
                files,
            });
        }
    }
    out
}

/// SYS012 (binding.md 6.12): a template excuse whose atom and files overlap a node's `may` grant.
/// Model facts only, so it is always Exact and never Unresolved.
fn sys012(cx: &Cx<'_>, excuses: &[Excuse], out: &mut Output) {
    out.count("SYS012", excuses.len());
    if excuses.is_empty() {
        return;
    }
    for c in excuse::sys012(excuses, &grant_scopes(cx)) {
        let what = format!(
            "template `{}` excuses `{}` but `{}` grants `{}` over overlapping code; the excuse says the atom does not apply there and the grant says it may be used: remove one",
            c.template, c.excused, c.node, c.written
        );
        let anchor = format!("cap/{}/{}/{}/excuse-grant", c.template, c.excused, c.node);
        out.fire("SYS012", Severity::Error, what, &anchor, None);
    }
}

fn cap002(cx: &Cx<'_>, uses: &Uses, today: gob_time::Day, out: &mut Output) {
    for c in grant_cells_with(cx, uses, out) {
        if c.cell != Cell::DeclaredUnused {
            continue;
        }
        let Some(e) = cx.model.entities.values().find(|e| e.anchor == c.node) else {
            continue;
        };
        if crate::model::silenced(e, "CAP002", &c.atom, today) {
            continue;
        }
        out.fire(
            "CAP002",
            Severity::Error,
            format!(
                "`{}` grants `{}` but no use of it is observed in the code it owns",
                c.node, c.written
            ),
            &format!("cap/{}/{}", c.node, c.atom),
            Some((c.file.as_str(), c.span)),
        );
    }
}

/// Extensions of opaque (adapter-less) files that are executable code, so a node owning them is
/// not measured: shell, batch, scripting and compiled languages without a capability detector.
const UNMEASURED_EXTS: &[&str] = &[
    "zsh", "fish", "ksh", "ps1", "bat", "cmd", "rb", "go", "java", "kt", "php", "pl", "lua",
    "swift", "c", "cc", "cpp", "h", "hpp", "scala", "ex", "exs", "r", "dart",
];

/// Adapter languages whose files are executable but that carry no capability detector rows.
const UNMEASURED_ADAPTERS: &[&str] = &["dockerfile", "github-actions"];

/// The unmeasured-language tag of `f` (`shell`, `dockerfile`, ...), or `None` when the file is
/// data or its language has detectors.
fn unmeasured_tag(f: &crate::code::CodeFile) -> Option<String> {
    if gob_symbols::is_workflow_path(&f.path) {
        return Some("github-actions".to_owned());
    }
    if f.language == crate::code::OPAQUE {
        if gob_symbols::is_dockerfile_path(&f.path) {
            return Some("dockerfile".to_owned());
        }
        let gob_walk::LanguageHint::Other(ext) = &f.hint else {
            return None;
        };
        return UNMEASURED_EXTS.contains(&ext.as_str()).then(|| ext.clone());
    }
    UNMEASURED_ADAPTERS
        .contains(&f.language.as_str())
        .then(|| f.language.clone())
}

/// True when no registered atom or enabled pack detects anything in `lang` (every answer Unknown).
fn lang_has_no_detector(cx: &Cx<'_>, lang: &str) -> bool {
    let registered = gob_ir::registry::atoms()
        .iter()
        .all(|a| matches!(gob_ir::registry::detectors(a.name, lang), Answer::Unknown));
    registered
        && !cx
            .packs
            .values()
            .any(|p| p.detectors.iter().any(|d| d.lang == lang))
}

/// One Unresolved per node (ticket 01M5XNNHET0VW6RFJAF0QH7RRS) that owns executable code in a
/// language with no capability detector at all: its uses cannot be judged, so the node must not
/// read as clean. The message names the languages and every atom left unknown.
fn cap_no_detector(cx: &Cx<'_>, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node && !e.external && e.owns_code())
    {
        let mut langs: BTreeSet<String> = BTreeSet::new();
        for uo in cx.owners.units.values() {
            let Owner::Must(n) = &uo.merged.owner else {
                continue;
            };
            if n.as_str() != e.anchor {
                continue;
            }
            let Some(f) = cx.code.file(uo.file.as_str()) else {
                continue;
            };
            let tag = unmeasured_tag(f).filter(|_| lang_has_no_detector(cx, &f.language));
            if let Some(t) = tag {
                langs.insert(t);
            }
        }
        if langs.is_empty() {
            continue;
        }
        let mut atoms: BTreeSet<String> = gob_ir::registry::atoms()
            .iter()
            .filter(|a| !a.detectors.is_empty())
            .map(|a| a.name.to_owned())
            .collect();
        for p in cx.packs.values() {
            atoms.extend(
                p.atoms
                    .iter()
                    .filter(|a| !is_pack_parent(cx.packs, a))
                    .cloned(),
            );
        }
        let list = langs.iter().cloned().collect::<Vec<_>>().join(", ");
        let names = atoms.iter().cloned().collect::<Vec<_>>().join(", ");
        tracing::warn!(node = %e.anchor, langs = %list, "node owns code in a language with no capability detector");
        out.unresolved(
            "CAP001",
            Reason::Fidelity,
            &format!(
                "`{}` owns {list} code but no capability detector covers that language (no-detector); its use of {names} is unknown, not clean",
                e.anchor
            ),
            &format!("cap/{}/no-detector", e.anchor),
            Some((e.file.as_str(), (e.span.start, e.span.end))),
        );
    }
}

/// True when granting `grant` reaches `forbidden`: equal, narrower (`fs.write` under `fs`) or a
/// parent (`fs` covers `fs.write`), after alias canonicalisation.
// frob:ticket 01M5XNNJMSCGPFS84V3PZQKTNC
fn atom_reaches(grant: &str, forbidden: &str) -> bool {
    let g = gob_ir::registry::canonical(grant).unwrap_or(grant);
    let f = gob_ir::registry::canonical(forbidden).unwrap_or(forbidden);
    let within = |inner: &str, outer: &str| {
        inner == outer
            || inner
                .strip_prefix(outer)
                .is_some_and(|r| r.starts_with('.'))
    };
    within(g, f) || within(f, g)
}

/// True when the observed atom `used` is the forbidden atom or a child of it (`net` forbids `net.connect`).
// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D
fn atom_within(used: &str, forbidden: &str) -> bool {
    let u = gob_ir::registry::canonical(used).unwrap_or(used);
    let f = gob_ir::registry::canonical(forbidden).unwrap_or(forbidden);
    u == f || u.strip_prefix(f).is_some_and(|r| r.starts_with('.'))
}

/// CLAIM004: `claim never NODE uses ATOM` is refuted by an observed use, direct or carried through
/// callees (the carried use names the call path in its callee). A certain Must-owned use is an
/// Error; a May-owned or receiver-unresolved use is Unresolved, since absence is not shown.
// frob:ticket 01M5XNNJQN463MG3PT8NBEC70D
fn claim004(cx: &Cx<'_>, uses: &Uses, out: &mut Output) {
    let claims: Vec<&crate::model::Entity> = cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Claim && e.never.is_some())
        .collect();
    out.count("CLAIM004", claims.len());
    for e in claims {
        let Some(nv) = &e.never else { continue };
        for (set, must) in [(&uses.lo, true), (&uses.hi, false)] {
            let Some(found) = set.get(&nv.node) else {
                continue;
            };
            let hits: Vec<&Use> = found
                .iter()
                .filter(|u| atom_within(&u.atom, &nv.atom))
                .collect();
            if hits.is_empty() {
                continue;
            }
            let certain = must && hits.iter().any(|u| u.certain);
            let list = hits
                .iter()
                .take(EXAMPLES)
                .map(|u| u.site())
                .collect::<Vec<_>>()
                .join("; ");
            let what = format!(
                "`{}` is claimed to never use `{}`, but owned code does: {list}",
                nv.node, nv.written
            );
            tracing::info!(claim = %e.anchor, node = %nv.node, certain, hits = hits.len(), "never claim refuted");
            if certain {
                let anchor = format!("{}/never", e.anchor);
                out.fire("CLAIM004", Severity::Error, what, &anchor, None);
            } else if must {
                let anchor = format!("{}/never/receiver", e.anchor);
                out.unresolved("CLAIM004", Reason::UnresolvedEdge, &what, &anchor, None);
            } else {
                let anchor = format!("{}/never/may", e.anchor);
                out.unresolved("CLAIM004", Reason::MayOnlyOwner, &what, &anchor, None);
            }
        }
    }
}

/// CAP006: a `may` grant on a node whose trust is at or below a declared ceiling forbids it.
// frob:ticket 01M5XNNJMSCGPFS84V3PZQKTNC
fn cap006(cx: &Cx<'_>, out: &mut Output) {
    use grimble_model::fold::TRUST_LEVELS;
    let rank = |l: &str| TRUST_LEVELS.iter().position(|t| *t == l);
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        let Some(node_rank) = e.trust.as_deref().and_then(rank) else {
            continue;
        };
        out.count("CAP006", e.grants.len());
        for g in &e.grants {
            for c in &cx.model.ceilings {
                let Some(level) = rank(&c.level) else {
                    tracing::warn!(level = %c.level, "ceiling names an unknown trust level; ignored");
                    continue;
                };
                if node_rank > level {
                    continue;
                }
                let Some(hit) = c.atoms.iter().find(|a| atom_reaches(&g.atom, a)) else {
                    continue;
                };
                let trust = e.trust.as_deref().unwrap_or_default();
                tracing::info!(node = %e.anchor, atom = %g.written, ceiling = %c.level, "grant exceeds ceiling");
                out.fire(
                    "CAP006",
                    Severity::Error,
                    format!(
                        "`may {}` on {trust} node `{}` exceeds the `ceiling {} forbids {hit}` declared in {}",
                        g.written, e.anchor, c.level, c.file
                    ),
                    &format!("cap/{}/ceiling/{}", e.anchor, g.written),
                    Some((g.file.as_str(), (g.span.start, g.span.end))),
                );
            }
        }
    }
}

/// Why CAP007 has no subject: no `may` grant carries an `until=` date.
pub fn cap007_inapplicable(model: &crate::model::Model) -> Option<&'static str> {
    let any = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Node && e.grants.iter().any(|g| g.until.is_some()));
    (!any).then_some("no `may` grant carries an `until=` date, so none can expire")
}

/// CAP007: a `may` grant whose `until=` date has passed no longer covers anything.
// frob:ticket 01M5XNNJTK08K3CB98MCT14W34
fn cap007(cx: &Cx<'_>, today: &str, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        let dated: Vec<_> = e.grants.iter().filter(|g| g.until.is_some()).collect();
        out.count("CAP007", dated.len());
        for g in dated.into_iter().filter(|g| g.expired(today)) {
            let until = g.until.as_deref().unwrap_or_default();
            tracing::warn!(node = %e.anchor, atom = %g.written, until, "grant expired");
            out.fire(
                "CAP007",
                Severity::Error,
                format!(
                    "`may {}` on `{}` expired on {until}; renew the date or remove the grant",
                    g.written, e.anchor
                ),
                &format!("cap/{}/expired/{}", e.anchor, g.written),
                Some((g.file.as_str(), (g.span.start, g.span.end))),
            );
        }
    }
}

/// Evaluate CAP001 and CAP002 over the observed uses and the node grants.
pub fn evaluate(cx: &Cx<'_>, out: &mut Output) {
    let uses = observe(cx);
    let today = gob_time::Clock::today(&gob_time::SystemClock::pin());
    let excuses = template_excuses(cx);
    cap001(cx, &uses, &excuses, today, out);
    cap001_unowned(cx, &uses, out);
    cap_no_detector(cx, out);
    cap002(cx, &uses, today, out);
    cap004(cx, &uses, &excuses, out);
    sys012(cx, &excuses, out);
    cap006(cx, out);
    cap007(cx, &today.to_string(), out);
    claim004(cx, &uses, out);
    tracing::info!(
        cap001 = out.subjects.get("CAP001").copied().unwrap_or(0),
        cap004 = out.subjects.get("CAP004").copied().unwrap_or(0),
        cap002 = out.subjects.get("CAP002").copied().unwrap_or(0),
        "CAP rules evaluated"
    );
}

#[cfg(test)]
mod walk_tests {
    use super::*;

    fn target(i: usize) -> CallTarget {
        ("src/a.rs".to_owned(), vec![format!("f{i}")])
    }

    // frob:ticket 01M6A73SAGJNKRZ6JHGYNRQJ09
    /// Expand chain node `t` of `n`: it uses itself and leads to the next node; counts the call.
    fn chain_expansion(expanded: &mut usize, t: &CallTarget, n: usize) -> Expansion {
        *expanded += 1;
        let i: usize = t.1[0][1..].parse().unwrap();
        Expansion {
            uses: vec![i],
            nexts: if i + 1 < n {
                vec![(target(i + 1), true)]
            } else {
                Vec::new()
            },
        }
    }

    /// Walks the closure of every chain target `edges` times; returns the total reached.
    fn drive_chain(walk: &mut Walk, expanded: &mut usize, n: usize, edges: usize) -> usize {
        let mut reached = 0usize;
        for _ in 0..edges {
            for i in 0..n {
                reached += walk
                    .closure(&target(i), true, &mut |t| chain_expansion(expanded, t, n))
                    .len();
            }
        }
        reached
    }

    // frob:tests crates/grimble-bind/src/caps.rs::propagate_cross_node
    /// A chain of N functions with many call edges into each: expansions stay linear in N.
    #[test]
    fn cross_node_walk_expands_each_target_once() {
        const N: usize = 200;
        const EDGES_PER_CALLEE: usize = 20;
        let mut expanded = 0usize;
        let mut walk = Walk::default();
        let reached = drive_chain(&mut walk, &mut expanded, N, EDGES_PER_CALLEE);
        // Every start still sees the whole tail of the chain ...
        assert_eq!(reached, EDGES_PER_CALLEE * N * (N + 1) / 2);
        // ... but each target is expanded once and each closure computed once, not once per edge.
        assert_eq!(expanded, N);
        assert_eq!(walk.expansions_computed, N);
        assert_eq!(walk.closures_computed, N);
    }
}

#[cfg(test)]
mod cell_tests {
    use super::*;

    // frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
    // frob:tests crates/grimble-bind/src/caps.rs::grant_cells
    /// A granted atom nothing uses yields one cell for that node and counts its CAP002 subjects.
    #[test]
    fn an_unused_grant_yields_one_cell_for_its_node() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(dir.path().join("src/a.py"), "def go():\n    return 1\n").unwrap();
        let text = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  may net.connect;\n}\n";
        let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
        let files = grimble_model::ModelFiles::new()
            .with_file("design/model.grmb", text.as_bytes().to_vec());
        let model = crate::model::load(&files);
        let code = crate::code::Code::build(dir.path(), &walked.files);
        let directives = crate::directives::scan(&code);
        let rel = crate::relation::build(&model, &code, &directives);
        let expand = crate::expand_files(&rel, &[], &code);
        let owners = crate::owner::build(&model.owner_inputs(), &code, &rel, &expand);
        let graph = gob_symbols::SymbolGraph::default();
        let cx = Cx {
            model: &model,
            code: &code,
            rel: &rel,
            owners: &owners,
            modeled: &[],
            strict: false,
            graph: &graph,
            ledger_dir: "tickets",
            packs: &files.packs,
            pack_severity: &files.pack_severity,
            grant_ledger: None,
        };
        let mut out = Output::default();
        let cells = grant_cells(&cx, &mut out);
        assert_eq!(cells.len(), 1, "{cells:?}");
        assert_eq!(cells[0].atom, "net.connect");
        assert!(cells[0].node.ends_with('a'), "{}", cells[0].node);
        assert_eq!(out.subjects.get("CAP002"), Some(&1));
    }

    /// Runs CAP001 over one ungranted python file with the given `[packs.severity]` overrides.
    fn cap001_out(src: &str, sev: &[(&str, &str)]) -> Output {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(dir.path().join("src/a.py"), src).unwrap();
        let text = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n";
        let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
        let severity = sev
            .iter()
            .map(|(a, l)| {
                (
                    (*a).to_owned(),
                    BTreeMap::from([("CAP001".to_owned(), (*l).to_owned())]),
                )
            })
            .collect();
        let files = grimble_model::ModelFiles::new()
            .with_file("design/model.grmb", text.as_bytes().to_vec())
            .with_pack_severity(severity);
        let model = crate::model::load(&files);
        let code = crate::code::Code::build(dir.path(), &walked.files);
        let directives = crate::directives::scan(&code);
        let rel = crate::relation::build(&model, &code, &directives);
        let expand = crate::expand_files(&rel, &[], &code);
        let owners = crate::owner::build(&model.owner_inputs(), &code, &rel, &expand);
        let graph = gob_symbols::SymbolGraph::default();
        let cx = Cx {
            model: &model,
            code: &code,
            rel: &rel,
            owners: &owners,
            modeled: &[],
            strict: false,
            graph: &graph,
            ledger_dir: "tickets",
            packs: &files.packs,
            pack_severity: &files.pack_severity,
            grant_ledger: None,
        };
        let mut out = Output::default();
        evaluate(&cx, &mut out);
        out
    }

    const ENV_USE: &str = "import os\n\ndef go():\n    return os.environ[\"HOME\"]\n";

    // frob:ticket 01M5XNNJF27AX6510KBK4EMP90
    // frob:tests crates/grimble-bind/src/caps.rs::level_of
    /// A warn-level atom row makes an ungranted use Unresolved, not an Error.
    #[test]
    fn a_warn_level_atom_row_makes_cap001_unresolved() {
        let out = cap001_out(ENV_USE, &[]);
        let f: Vec<_> = out.findings.iter().filter(|f| f.rule == "CAP001").collect();
        assert!(!f.is_empty(), "{:?}", out.findings);
        assert!(f.iter().all(|f| f.severity != Severity::Error), "{f:?}");
        assert!(f.iter().all(|f| f.reason.is_some()), "{f:?}");
    }

    // frob:ticket 01M5XNNJF27AX6510KBK4EMP90
    // frob:tests crates/grimble-bind/src/caps.rs::level_of
    /// `[packs.severity]` overrides the row: a warn atom set to error fires as an Error.
    #[test]
    fn a_packs_severity_override_beats_the_atom_row() {
        let out = cap001_out(ENV_USE, &[("env.read", "error")]);
        assert!(
            out.findings
                .iter()
                .any(|f| f.rule == "CAP001" && f.severity == Severity::Error),
            "{:?}",
            out.findings
        );
    }

    // frob:ticket 01M5XNNJF27AX6510KBK4EMP90
    // frob:tests crates/grimble-bind/src/caps.rs::level_of
    /// An error-row atom set to warn by `[packs.severity]` is no longer an Error.
    #[test]
    fn a_packs_severity_warn_demotes_an_error_atom() {
        let src =
            "import urllib.request\n\ndef go():\n    return urllib.request.urlopen(\"http://x\")\n";
        let base = cap001_out(src, &[]);
        assert!(
            base.findings
                .iter()
                .any(|f| f.rule == "CAP001" && f.severity == Severity::Error),
            "{:?}",
            base.findings
        );
        let out = cap001_out(src, &[("net.connect", "warn")]);
        assert!(
            out.findings
                .iter()
                .all(|f| f.rule != "CAP001" || f.severity != Severity::Error),
            "{:?}",
            out.findings
        );
    }

    // frob:ticket 01M5XNNJF27AX6510KBK4EMP90
    // frob:tests crates/grimble-bind/src/caps.rs::advice
    /// The message suffix carries the row's rationale and safer alternative, and is empty without.
    #[test]
    fn advice_carries_rationale_and_safer_alternative() {
        gob_ir::registry::register_rows(vec![gob_ir::registry::AtomRow {
            atom: "k4emp90.demo".to_owned(),
            rationale: Some("shells out".to_owned()),
            safer_alternative: Some("use the library API".to_owned()),
            ..Default::default()
        }]);
        let a = advice("k4emp90.demo");
        assert!(a.contains("why: shells out"), "{a}");
        assert!(a.contains("safer: use the library API"), "{a}");
        assert_eq!(advice("k4emp90.absent"), "");
    }
}
