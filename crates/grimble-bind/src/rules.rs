//! Evaluation of SYS001 to SYS005 and SYS009 to SYS011 over the relation and the owners.
//!
//! Every rule follows binding.md section 6: fire only from `lo` (P+) or from an empty `hi`
//! (P-), certify clean only from the opposite bound, and report Unresolved with a reason code
//! otherwise. Nothing here passes silently on an Unknown answer.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC
// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4
// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use gob_ir::select;
use gob_rules::Severity;
use gob_symbols::{Fidelity, SymbolGraph, SymbolKind, Visibility};
use gob_walk::{Owner, Selector, select_files};
use grimble_model::ast::EntityKind;

use crate::code::Code;
use crate::model::{Clause, Entity, Model};
use crate::owner::Owners;
use crate::relation::{ClauseResult, Relation, hidden_reason};
use crate::types::{BindFinding, Reason, Role, Source, Status};

/// Everything the rules read.
pub struct Cx<'a> {
    /// The model's entities.
    pub model: &'a Model,
    /// The folded code.
    pub code: &'a Code,
    /// The relation B before the owner merge.
    pub rel: &'a Relation,
    /// Ownership per identity.
    pub owners: &'a Owners,
    /// The parsed `[grimble] modeled` selectors.
    pub modeled: &'a [Selector],
    /// `[grimble] strict`: Warn rules become Error.
    pub strict: bool,
    /// The symbol graph of the snapshot: the import and call edges SYS013 walks.
    pub graph: &'a SymbolGraph,
    /// The ledger directory; with `changelog.d/`, `frob.lock` and `.frob/` it is frob-owned.
    pub ledger_dir: &'a str,
}

/// The findings and subject counts of one evaluation.
#[derive(Debug, Default)]
pub struct Output {
    /// Findings in rule order.
    pub findings: Vec<BindFinding>,
    /// Subjects examined per rule.
    pub subjects: BTreeMap<&'static str, usize>,
}

impl Output {
    pub(crate) fn count(&mut self, rule: &'static str, n: usize) {
        *self.subjects.entry(rule).or_default() += n;
    }

    pub(crate) fn fire(
        &mut self,
        rule: &'static str,
        severity: Severity,
        message: String,
        anchor: &str,
        site: Option<(&str, (usize, usize))>,
    ) {
        tracing::debug!(rule, anchor, %message, "rule fires");
        self.findings.push(BindFinding {
            rule,
            severity,
            file: site.map(|(f, _)| f.to_owned()),
            range: site.map(|(_, r)| r),
            message,
            reason: None,
            anchor: anchor.to_owned(),
        });
    }

    pub(crate) fn unresolved(
        &mut self,
        rule: &'static str,
        reason: Reason,
        message: &str,
        anchor: &str,
        site: Option<(&str, (usize, usize))>,
    ) {
        tracing::debug!(rule, anchor, reason = reason.code(), %message, "rule unresolved");
        self.findings
            .push(BindFinding::unresolved(rule, reason, message, anchor, site));
    }
}

fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or(".", |(d, _)| d)
}

/// The path part of a symref text.
pub fn path_of(symref: &str) -> &str {
    let p = symref.split('#').next().unwrap_or(symref);
    p.split("::").next().unwrap_or(p)
}

fn qual_of(symref: &str) -> &str {
    symref.split_once("::").map_or("", |(_, q)| q)
}

/// True when a unit looks like a test item: under `tests/`, a `*_test`/`test_*` file or a
/// `test`/`tests` qualifier. A stand-in for the adapter query `test_items` (Q35).
pub fn is_test_unit(symref: &str) -> bool {
    let path = path_of(symref);
    let stem = path.rsplit('/').next().unwrap_or(path);
    let stem = stem.split('.').next().unwrap_or(stem);
    path.starts_with("tests/")
        || path.contains("/tests/")
        || stem.ends_with("_test")
        || stem.starts_with("test_")
        || qual_of(symref)
            .split('.')
            .any(|s| s == "tests" || s == "test")
}

fn warn_sev(strict: bool) -> Severity {
    if strict {
        Severity::Error
    } else {
        Severity::Warn
    }
}

fn list(items: &[String], max: usize) -> String {
    let mut s = items
        .iter()
        .take(max)
        .cloned()
        .collect::<Vec<_>>()
        .join(", ");
    if items.len() > max {
        let _ = write!(s, " (+{} more)", items.len() - max);
    }
    s
}

fn first_reason(rs: &[Reason]) -> Reason {
    rs.first().copied().unwrap_or(Reason::UnseenRemainder)
}

fn modeled_paths(cx: &Cx<'_>) -> BTreeSet<String> {
    cx.modeled
        .iter()
        .flat_map(|s| select_files(s, &cx.code.walk))
        .map(|m| m.path)
        .collect()
}

/// Why SYS001 has no subject, or `None` when the model declares a node that could own a file.
///
/// With no node at all, "no node owns this file" is vacuous (every file would read as unowned);
/// with a node, each unowned file is a real finding.
pub fn sys001_inapplicable(model: &Model) -> Option<&'static str> {
    let has = model.entities.values().any(|e| e.kind == EntityKind::Node);
    (!has).then_some("the model declares no node, so no file can be unowned")
}

/// Why SYS002 has no subject, or `None` when an `owns` row or a directive owner exists.
///
/// Subjects: an identity with an owner candidate, so an `owns` clause that matched an identity
/// or a directive owner.
pub fn sys002_inapplicable(rel: &Relation) -> Option<&'static str> {
    let has = !rel.dir_owns.is_empty() || rel.rows.iter().any(|r| r.role == Role::Owns);
    (!has).then_some("no `owns` clause matches an identity and no directive names an owner, so no ownership can tie")
}

/// Why SYS004 has no subject, or `None` when a clause or flow it checks for code exists.
///
/// Subjects: a node `owns` clause, a contract `shape` clause, a claim `evidence` selector that
/// is not itself a checked claim, or a flow.
pub fn sys004_inapplicable(model: &Model) -> Option<&'static str> {
    let has = model
        .entities
        .values()
        .any(|e| e.kind == EntityKind::Flow || e.clauses.iter().any(|c| sys004_clause(e, c)));
    (!has).then_some("the model has no node owns, contract shape, claim evidence selector or flow to check for code")
}

/// Whether SYS004 checks this clause of `e` for code.
fn sys004_clause(e: &Entity, c: &Clause) -> bool {
    match (e.kind, c.role) {
        (EntityKind::Node, Role::Owns) | (EntityKind::Contract, Role::Shape) => true,
        (EntityKind::Claim, Role::Evidence) => !is_checked_claim(e) && c.selector.is_some(),
        _ => false,
    }
}

fn sys001(cx: &Cx<'_>, out: &mut Output) {
    let skip = modeled_paths(cx);
    let mut unowned: BTreeMap<&str, Vec<String>> = BTreeMap::new();
    let mut soft: BTreeMap<(&str, &'static str), (Reason, Vec<String>)> = BTreeMap::new();
    for f in &cx.code.files {
        if crate::frob_owned::is_frob_owned(&f.path, cx.ledger_dir) {
            continue;
        }
        out.count("SYS001", 1);
        let Some(fo) = cx.owners.files.get(&f.path) else {
            continue;
        };
        let (mut owned, mut may, mut hidden) = (false, false, false);
        if fo.expanded {
            for u in &fo.units {
                let Some(uo) = cx.owners.units.get(u) else {
                    continue;
                };
                match &uo.merged.owner {
                    Owner::Must(_) => owned = true,
                    Owner::Unknown(set) if !set.is_empty() => owned = true,
                    Owner::May(_) => may = true,
                    Owner::Unknown(_) => hidden = true,
                    Owner::Foreign => {}
                }
            }
        }
        if owned || skip.contains(&f.path) {
            continue;
        }
        let dir = dir_of(&f.path);
        if may {
            let e = soft
                .entry((dir, Reason::MayOnlyOwner.code()))
                .or_insert((Reason::MayOnlyOwner, Vec::new()));
            e.1.push(f.path.clone());
        } else if hidden {
            let r = hidden_reason(f).unwrap_or(Reason::UnseenRemainder);
            let e = soft.entry((dir, r.code())).or_insert((r, Vec::new()));
            e.1.push(f.path.clone());
        } else {
            unowned.entry(dir).or_default().push(f.path.clone());
        }
    }
    for (dir, files) in unowned {
        out.fire(
            "SYS001",
            warn_sev(cx.strict),
            format!(
                "{} unowned file(s) in `{dir}`: {}",
                files.len(),
                list(&files, 5)
            ),
            dir,
            None,
        );
    }
    for ((dir, _), (reason, files)) in soft {
        out.unresolved(
            "SYS001",
            reason,
            &format!(
                "{} file(s) in `{dir}` may be unowned: {}",
                files.len(),
                list(&files, 5)
            ),
            dir,
            None,
        );
    }
}

fn owns_anchors(cx: &Cx<'_>) -> BTreeMap<(String, String), Vec<String>> {
    let mut m: BTreeMap<(String, String), Vec<String>> = BTreeMap::new();
    for r in &cx.rel.rows {
        if let (Role::Owns, Some(id), Some(a)) = (r.role, &r.identity, &r.anchor) {
            m.entry((id.clone(), r.entity.clone()))
                .or_default()
                .push(a.clone());
        }
    }
    m
}

fn sys002(cx: &Cx<'_>, out: &mut Output) {
    let anchors = owns_anchors(cx);
    // (file, tied node names, fires) -> identities
    let mut groups: BTreeMap<(String, Vec<String>, bool), Vec<String>> = BTreeMap::new();
    for (sym, uo) in &cx.owners.units {
        if !uo.merged.candidates.is_empty() {
            out.count("SYS002", 1);
        }
        let Some(t) = &uo.merged.tie else { continue };
        let mut names: Vec<String> = t.nodes.iter().map(|(n, _)| n.to_string()).collect();
        names.sort();
        names.dedup();
        groups
            .entry((uo.file.clone(), names, t.fires))
            .or_default()
            .push(sym.clone());
    }
    for ((file, names, fires), ids) in groups {
        let first = &ids[0];
        let spec = cx
            .owners
            .units
            .get(first)
            .and_then(|u| u.merged.tie.as_ref())
            .and_then(|t| t.nodes.first().map(|(_, s)| s.components()));
        let clauses: Vec<String> = names
            .iter()
            .flat_map(|n| {
                anchors
                    .get(&(first.clone(), n.clone()))
                    .cloned()
                    .unwrap_or_default()
            })
            .collect();
        let msg = format!(
            "{} identity(ies) in `{file}` are owned equally by {} (specificity {spec:?}; clauses {}); first: {first}",
            ids.len(),
            names.join(" and "),
            clauses.join(", "),
        );
        if fires {
            out.fire(
                "SYS002",
                Severity::Error,
                msg,
                &format!("{file}|{}", names.join("|")),
                None,
            );
        } else {
            out.unresolved(
                "SYS002",
                Reason::MayOnlyOwner,
                &format!("{msg}; a May row is in the tie, so it may not be one"),
                &format!("{file}|{}", names.join("|")),
                None,
            );
        }
    }
}

fn singleton_rows(cx: &Cx<'_>, e: &Entity, role: Role) -> BTreeSet<String> {
    cx.rel
        .rows
        .iter()
        .filter(|r| {
            r.entity == e.anchor
                && r.role == role
                && r.status == Status::Must
                && r.source != Source::Residual
        })
        .filter_map(|r| r.identity.clone())
        .collect()
}

fn sys003(cx: &Cx<'_>, out: &mut Output) {
    out.count("SYS003", cx.rel.operands);
    out.findings.extend(cx.rel.findings.iter().cloned());
    for (sym, uo) in &cx.owners.units {
        let m = &uo.merged;
        if let Some(nodes) = &m.directive_directive {
            let names: Vec<String> = nodes.iter().map(ToString::to_string).collect();
            out.fire(
                "SYS003",
                Severity::Error,
                format!("directive-directive: directives give `{sym}` several owners: {}; its owner is Unknown", names.join(", ")),
                sym,
                cx.rel.dir_owns.get(sym).and_then(|d| d.first()).map(|d| (d.file.as_str(), d.range)),
            );
        }
        if let Some((x, top)) = &m.directive_selector {
            let sel: Vec<String> = top
                .iter()
                .map(|(n, s)| format!("{n} {:?}", s.components()))
                .collect();
            out.fire(
                "SYS003",
                Severity::Error,
                format!("directive-selector: a directive makes `{x}` own `{sym}` but the most specific selectors name {}; the owner stays `{x}`", sel.join(", ")),
                sym,
                cx.rel.dir_owns.get(sym).and_then(|d| d.first()).map(|d| (d.file.as_str(), d.range)),
            );
        }
    }
    for e in cx.model.entities.values() {
        for role in [Role::Shape, Role::Runnable, Role::Ref] {
            if e.clauses_of(role).next().is_none() {
                continue;
            }
            out.count("SYS003", 1);
            let ids = singleton_rows(cx, e, role);
            if ids.len() >= 2 {
                let site = e
                    .clauses_of(role)
                    .next()
                    .map(|c| (c.file.as_str(), (c.span.start, c.span.end)));
                let names: Vec<String> = ids.into_iter().collect();
                out.fire(
                    "SYS003",
                    Severity::Error,
                    format!(
                        "ambiguous-singleton: {} `{}` must name exactly one identity but names {}",
                        e.anchor,
                        role.as_str(),
                        names.join(", ")
                    ),
                    &format!("{}/{}", e.anchor, role.as_str()),
                    site,
                );
            }
        }
        end_owner(cx, e, out);
    }
}

fn end_owner(cx: &Cx<'_>, flow: &Entity, out: &mut Output) {
    let Some((from, to)) = &flow.ends else { return };
    for (role, end) in [(Role::Producer, from), (Role::Consumer, to)] {
        let Some(end) = end else { continue };
        if cx.model.entities.get(end).is_some_and(|n| n.external) {
            continue;
        }
        if flow.clauses_of(role).next().is_some() {
            out.count("SYS003", 1);
        }
        for sym in singleton_rows(cx, flow, role) {
            let Some(uo) = cx.owners.units.get(&sym) else {
                continue;
            };
            let site = flow
                .clauses_of(role)
                .next()
                .map(|c| (c.file.as_str(), (c.span.start, c.span.end)));
            let anchor = format!("{}/{}|{sym}", flow.anchor, role.as_str());
            match &uo.merged.owner {
                Owner::Must(n) if n.as_str() != end => out.fire(
                    "SYS003",
                    Severity::Error,
                    format!("end-owner: the {} of {} is `{sym}`, owned by `{n}`, not by `{end}`", role.as_str(), flow.anchor),
                    &anchor,
                    site,
                ),
                Owner::May(set) | Owner::Unknown(set) if set.iter().any(|n| n.as_str() != end) && !set.is_empty() => out.unresolved(
                    "SYS003",
                    Reason::MayOnlyOwner,
                    &format!("end-owner: the owner of `{sym}` (the {} of {}) is not known to be `{end}`", role.as_str(), flow.anchor),
                    &anchor,
                    site,
                ),
                _ => {}
            }
        }
    }
}

fn clause_result<'a>(cx: &'a Cx<'_>, anchor: &str) -> Option<&'a ClauseResult> {
    cx.rel.clauses.iter().find(|c| c.clause.anchor == anchor)
}

fn sys004(cx: &Cx<'_>, out: &mut Output) {
    for e in cx.model.entities.values() {
        for c in &e.clauses {
            if !sys004_clause(e, c) {
                continue;
            }
            let Some(r) = clause_result(cx, &c.anchor) else {
                continue;
            };
            out.count("SYS004", 1);
            let site = Some((c.file.as_str(), (c.span.start, c.span.end)));
            if r.files_matched == 0 && r.hidden.is_empty() {
                tracing::debug!(clause = %c.anchor, "selector path matches no file; MDL005 owns this");
            } else if r.hi_empty() {
                if e.infer_requested {
                    out.unresolved(
                        "SYS004",
                        Reason::InferenceUnavailable,
                        &format!(
                            "{} matches no code and asked for pack inference, which cannot run yet",
                            c.anchor
                        ),
                        &c.anchor,
                        site,
                    );
                } else {
                    out.fire(
                        "SYS004",
                        Severity::Warn,
                        format!("{} matches no unit and hides none", c.anchor),
                        &c.anchor,
                        site,
                    );
                }
            } else if r.lo() == 0 {
                let reason = if r.hidden.is_empty() {
                    Reason::MayOnlyOwner
                } else {
                    first_reason(&r.hidden)
                };
                out.unresolved(
                    "SYS004",
                    reason,
                    &format!("{} matches only May rows or hidden units", c.anchor),
                    &c.anchor,
                    site,
                );
            }
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum End {
    Bound,
    Maybe(Reason),
    Empty,
    Future,
}

fn end_state(cx: &Cx<'_>, flow: &Entity, role: Role) -> End {
    let rows: Vec<_> = cx
        .rel
        .rows
        .iter()
        .filter(|r| r.entity == flow.anchor && r.role == role)
        .collect();
    if rows
        .iter()
        .any(|r| r.status == Status::Must && r.source != Source::Residual)
    {
        return End::Bound;
    }
    if let Some(r) = rows.first() {
        let reason = if rows.iter().any(|r| r.source == Source::Residual) {
            first_reason(
                &cx.rel
                    .clauses
                    .iter()
                    .filter(|c| c.entity == flow.anchor && c.clause.role == role)
                    .flat_map(|c| c.hidden.clone())
                    .collect::<Vec<_>>(),
            )
        } else {
            let _ = r;
            Reason::MayOnlyOwner
        };
        return End::Maybe(reason);
    }
    let clauses: Vec<_> = cx
        .rel
        .clauses
        .iter()
        .filter(|c| c.entity == flow.anchor && c.clause.role == role)
        .collect();
    if !clauses.is_empty() && clauses.iter().all(|c| c.files_matched == 0) {
        End::Future
    } else {
        End::Empty
    }
}

fn expected(model: &Model, flow: &Entity, role: Role) -> bool {
    let Some((from, to)) = &flow.ends else {
        return false;
    };
    let end = if role == Role::Producer { from } else { to };
    end.as_ref()
        .and_then(|a| model.entities.get(a))
        .is_some_and(|n| n.owns_code() && !n.external)
}

/// Why SYS003 has no subject, or `None` when the model or the code gives it one.
///
/// Subjects: an operand (`grimble:binds`), a `shape`, `ref` or `runnable` clause, a directive
/// owner, or a flow `producer`/`consumer` clause.
pub fn sys003_inapplicable(model: &Model, rel: &Relation) -> Option<&'static str> {
    let has = rel.operands > 0
        || !rel.dir_owns.is_empty()
        || model.entities.values().any(|e| {
            e.clauses.iter().any(|c| {
                matches!(
                    c.role,
                    Role::Shape | Role::Runnable | Role::Ref | Role::Producer | Role::Consumer
                )
            })
        });
    (!has).then_some(
        "the model has no operand, directive owner, shape, ref, runnable, producer or consumer clause to examine",
    )
}

/// Why SYS009 has no subject, or `None` when a flow end's node owns code.
pub fn sys009_inapplicable(model: &Model) -> Option<&'static str> {
    let has = model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Flow)
        .any(|f| expected(model, f, Role::Producer) || expected(model, f, Role::Consumer));
    (!has).then_some("the model declares no flow whose endpoint node owns code")
}

/// Why SYS010 has no subject, or `None` when a claim above L1 that is not assumed exists.
pub fn sys010_inapplicable(model: &Model) -> Option<&'static str> {
    let has = model.entities.values().any(is_checked_claim);
    (!has).then_some("the model declares no claim above proof level L1 that is not assumed")
}

/// Why SYS011 has no subject, or `None` when a vmodel `ref` or `runnable` clause exists.
pub fn sys011_inapplicable(model: &Model) -> Option<&'static str> {
    let has = model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Vmodel)
        .any(|e| {
            e.clauses
                .iter()
                .any(|c| matches!(c.role, Role::Ref | Role::Runnable))
        });
    (!has).then_some("the model declares no vmodel ref or runnable clause")
}

fn is_checked_claim(e: &Entity) -> bool {
    e.kind == EntityKind::Claim && e.proof.is_some_and(|p| p >= 2) && !e.assumed
}

fn flows(cx: &Cx<'_>, out: &mut Output) {
    for f in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Flow)
    {
        let (p, c) = (
            end_state(cx, f, Role::Producer),
            end_state(cx, f, Role::Consumer),
        );
        let (pe, ce) = (
            expected(cx.model, f, Role::Producer),
            expected(cx.model, f, Role::Consumer),
        );
        out.count("SYS009", usize::from(pe) + usize::from(ce));
        let site = Some((f.file.as_str(), (f.span.start, f.span.end)));
        let empty = |s: End| matches!(s, End::Empty | End::Future);
        out.count("SYS004", 1);
        if empty(p) && empty(c) {
            if p == End::Future && c == End::Future {
                continue;
            }
            if (p == End::Empty && pe) || (c == End::Empty && ce) {
                if f.infer_requested {
                    out.unresolved("SYS004", Reason::InferenceUnavailable, &format!("{} has no code at either end and asked for pack inference, which cannot run yet", f.anchor), &f.anchor, site);
                } else {
                    out.fire(
                        "SYS004",
                        Severity::Warn,
                        format!(
                            "{} is a flow without code: neither end binds anything",
                            f.anchor
                        ),
                        &f.anchor,
                        site,
                    );
                }
            }
            continue;
        }
        for (role, state, exp) in [(Role::Producer, p, pe), (Role::Consumer, c, ce)] {
            if !exp {
                continue;
            }
            let anchor = format!("{}/{}", f.anchor, role.as_str());
            match state {
                End::Empty if f.infer_requested => out.unresolved("SYS009", Reason::InferenceUnavailable, &format!("the {} end of {} is unbound and asked for pack inference, which cannot run yet", role.as_str(), f.anchor), &anchor, site),
                End::Empty => out.fire("SYS009", Severity::Warn, format!("the {} end of {} binds no code while the other end does", role.as_str(), f.anchor), &anchor, site),
                End::Maybe(reason) => out.unresolved("SYS009", reason, &format!("the {} end of {} binds only May rows or hidden units", role.as_str(), f.anchor), &anchor, site),
                End::Bound | End::Future => {}
            }
        }
    }
}

/// Facts gathered while walking the modeled selectors.
#[derive(Default)]
struct Modeled {
    unknown_vis: BTreeMap<String, usize>,
    may_sel: BTreeMap<String, usize>,
    seen: BTreeSet<String>,
}

const CODE_KINDS: [SymbolKind; 10] = [
    SymbolKind::Module,
    SymbolKind::Function,
    SymbolKind::Method,
    SymbolKind::Struct,
    SymbolKind::Enum,
    SymbolKind::Trait,
    SymbolKind::Const,
    SymbolKind::Static,
    SymbolKind::TypeAlias,
    SymbolKind::Macro,
];

fn modeled_unit(
    cx: &Cx<'_>,
    f: &crate::code::CodeFile,
    text: &str,
    acc: &mut Modeled,
    out: &mut Output,
) {
    let Some(folded) = &f.folded else { return };
    if f.fidelity < Fidelity::F2 {
        *acc.unknown_vis.entry(f.path.clone()).or_default() += 1;
        return;
    }
    let Some(rec) = folded
        .file
        .symbols
        .iter()
        .find(|s| s.symref.to_string() == text)
    else {
        return;
    };
    if !CODE_KINDS.contains(&rec.kind) {
        return;
    }
    out.count("SYS005", 1);
    if rec.visibility != Visibility::Public {
        return;
    }
    let Some(uo) = cx.owners.units.get(text) else {
        return;
    };
    let range = (
        u32::from(rec.span.start()) as usize,
        u32::from(rec.span.end()) as usize,
    );
    let site = Some((f.path.as_str(), range));
    match &uo.merged.owner {
        Owner::Foreign => out.fire(
            "SYS005",
            warn_sev(cx.strict),
            format!("public unit `{text}` is in a modeled selector and no node owns it"),
            text,
            site,
        ),
        Owner::May(_) => out.unresolved(
            "SYS005",
            Reason::MayOnlyOwner,
            &format!("public unit `{text}` may be unowned"),
            text,
            site,
        ),
        Owner::Unknown(set) if set.is_empty() => out.unresolved(
            "SYS005",
            Reason::UnseenRemainder,
            &format!("public unit `{text}` may be claimed by a hidden unit"),
            text,
            site,
        ),
        Owner::Must(_) | Owner::Unknown(_) => {}
    }
}

fn sys005(cx: &Cx<'_>, out: &mut Output) {
    if cx.modeled.is_empty() {
        return;
    }
    out.subjects.entry("SYS005").or_default();
    let mut acc = Modeled::default();
    for sel in cx.modeled {
        for m in select_files(sel, &cx.code.walk) {
            let Some(f) = cx.code.file(&m.path) else {
                continue;
            };
            let Some(folded) = &f.folded else {
                *acc.unknown_vis.entry(f.path.clone()).or_default() += 1;
                continue;
            };
            for u in select(sel, &folded.term, &folded.scopes, &cx.code.walk).matches {
                let text = u.symref.to_string();
                if u.status != gob_ir::Status::Must {
                    *acc.may_sel.entry(f.path.clone()).or_default() += 1;
                } else if acc.seen.insert(text.clone()) {
                    modeled_unit(cx, f, &text, &mut acc, out);
                }
            }
        }
    }
    for (path, n) in acc.unknown_vis {
        out.unresolved(
            "SYS005",
            Reason::Fidelity,
            &format!("{n} unit(s) of `{path}` have no known visibility at this fidelity"),
            &path,
            None,
        );
    }
    for (path, n) in acc.may_sel {
        out.unresolved(
            "SYS005",
            Reason::MayOnlyOwner,
            &format!("{n} unit(s) of `{path}` are in the modeled selector only at May"),
            &path,
            None,
        );
    }
}

fn sys010(cx: &Cx<'_>, out: &mut Output) {
    for e in cx.model.entities.values() {
        if !is_checked_claim(e) {
            continue;
        }
        out.count("SYS010", 1);
        let site = e
            .clauses_of(Role::Evidence)
            .next()
            .map_or((e.file.as_str(), (e.span.start, e.span.end)), |c| {
                (c.file.as_str(), (c.span.start, c.span.end))
            });
        let rows: Vec<_> = cx
            .rel
            .rows
            .iter()
            .filter(|r| r.entity == e.anchor && r.role == Role::Evidence)
            .collect();
        let from_ref = |r: &crate::types::Row| {
            e.clauses
                .iter()
                .any(|c| Some(&c.anchor) == r.anchor.as_ref() && c.symref.is_some())
        };
        let clean = rows.iter().any(|r| {
            r.status == Status::Must
                && r.source != Source::Residual
                && (from_ref(r) || r.identity.as_deref().is_some_and(is_test_unit))
        });
        if clean {
            continue;
        }
        if rows
            .iter()
            .any(|r| r.status == Status::May && r.identity.as_deref().is_some_and(is_test_unit))
        {
            out.unresolved(
                "SYS010",
                Reason::MayOnlyOwner,
                &format!("{} has test evidence only at May", e.anchor),
                &e.anchor,
                Some(site),
            );
        } else if rows.iter().any(|r| r.source == Source::Residual) {
            let reason = first_reason(
                &cx.rel
                    .clauses
                    .iter()
                    .filter(|c| c.entity == e.anchor)
                    .flat_map(|c| c.hidden.clone())
                    .collect::<Vec<_>>(),
            );
            out.unresolved(
                "SYS010",
                reason,
                &format!("{} has evidence in files that hide units", e.anchor),
                &e.anchor,
                Some(site),
            );
        } else {
            out.fire(
                "SYS010",
                Severity::Warn,
                format!(
                    "{} is a claim at proof level L{} with no test evidence",
                    e.anchor,
                    e.proof.unwrap_or(0)
                ),
                &e.anchor,
                Some(site),
            );
        }
    }
}

fn sys011(cx: &Cx<'_>, out: &mut Output) {
    for e in cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Vmodel)
    {
        for c in e
            .clauses
            .iter()
            .filter(|c| matches!(c.role, Role::Ref | Role::Runnable))
        {
            let Some(r) = clause_result(cx, &c.anchor) else {
                continue;
            };
            out.count("SYS011", 1);
            let site = Some((c.file.as_str(), (c.span.start, c.span.end)));
            let tests = r
                .matches
                .iter()
                .filter(|(h, _)| h.status == Status::Must && is_test_unit(&h.symref))
                .count();
            let good = if c.role == Role::Runnable {
                tests >= 1
            } else {
                r.lo() >= 1
            };
            if good {
                continue;
            }
            if !r.hidden.is_empty() {
                out.unresolved(
                    "SYS011",
                    first_reason(&r.hidden),
                    &format!("{} may point into units its file hides", c.anchor),
                    &c.anchor,
                    site,
                );
            } else if r.may() > 0 {
                out.unresolved(
                    "SYS011",
                    Reason::MayOnlyOwner,
                    &format!("{} resolves only at May", c.anchor),
                    &c.anchor,
                    site,
                );
            } else if r.files_matched == 0 {
                tracing::debug!(clause = %c.anchor, "link target file is not in the walk; no finding");
            } else if c.role == Role::Runnable && r.lo() > 0 {
                out.fire(
                    "SYS011",
                    Severity::Error,
                    format!("{} selects no test unit", c.anchor),
                    &c.anchor,
                    site,
                );
            } else {
                out.fire(
                    "SYS011",
                    Severity::Error,
                    format!(
                        "{} resolves to nothing although its file is in the walk",
                        c.anchor
                    ),
                    &c.anchor,
                    site,
                );
            }
        }
    }
}

/// Evaluate every binding rule.
pub fn evaluate(cx: &Cx<'_>) -> Output {
    let mut out = Output::default();
    for rule in [
        "SYS001", "SYS002", "SYS003", "SYS004", "SYS009", "SYS010", "SYS011", "SYS013", "CAP001",
        "CAP002",
    ] {
        out.subjects.entry(rule).or_default();
    }
    sys001(cx, &mut out);
    sys002(cx, &mut out);
    sys003(cx, &mut out);
    sys004(cx, &mut out);
    flows(cx, &mut out);
    sys005(cx, &mut out);
    sys010(cx, &mut out);
    sys011(cx, &mut out);
    crate::edges::sys013(cx, &mut out);
    crate::caps::evaluate(cx, &mut out);
    tracing::info!(findings = out.findings.len(), "binding rules evaluated");
    out
}
