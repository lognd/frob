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
//! Known limits: the template excuses and CAP004 (packs.md 6.7) are not implemented; the pack
//! severity table is not consulted (CAP001 is an Error, CAP002 a Warning); a grant's `at`
//! selector is compared at file granularity; `may` arguments are ignored.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

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

/// The atoms whose vocabulary in `lang` names `callee`, given the calls `file_calls` of its file.
fn atoms_of(lang: &str, callee: &str, file_calls: &BTreeSet<String>) -> Vec<&'static str> {
    let mut out = Vec::new();
    for a in atoms() {
        let Answer::Exact(names) = callee_vocab(lang, a.name) else {
            continue;
        };
        let direct = names.contains(callee);
        let by_method = callee.rsplit_once('.').is_some_and(|(_, m)| {
            names.contains(format!(".{m}").as_str())
                && METHOD_GATES.iter().any(|(atom, l, method, gate)| {
                    *atom == a.name && *l == lang && *method == m && file_calls.contains(*gate)
                })
        });
        if direct || by_method {
            out.push(a.name);
        }
    }
    out
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
        for atom in atoms_of(&code.language, callee, file_calls) {
            let u = Use {
                atom,
                file: uo.file.clone(),
                line: e.line,
                callee: callee.to_owned(),
            };
            match &uo.merged.owner {
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
            let mut by_atom: BTreeMap<&str, Vec<&Use>> = BTreeMap::new();
            for u in found {
                if !e.grants.iter().any(|g| covers(cx, g, u.atom, &u.file)) {
                    by_atom.entry(u.atom).or_default().push(u);
                }
            }
            for (atom, us) in by_atom {
                let anchor = format!("cap/{}/{atom}", e.anchor);
                if must {
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
                } else {
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
