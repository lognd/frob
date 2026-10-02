//! Exceptions: `frob:accept` and `frob:defer` suppress findings; EXC001, EXC003, EXC005 and EXC007 police them.

use std::ops::Range;

use gob_directives::frob::{Accept, Defer};
use gob_directives::{Binding, Directive, DirectiveRecord};
use gob_lock::LockFile;
use gob_rules::{Exception, ExceptionKind, Finding, ReasonPolicy, RuleId, check_reason};
use gob_symbols::{SymbolGraph, Symref};
use gob_text::{FileInterner, Span};

use crate::rules::{Exc001, Exc003, Exc005, Exc007};
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// One parsed `frob:accept` or `frob:defer` with where it applies.
struct Bound {
    exception: Exception,
    /// Where the directive text sits.
    at: Span,
    /// Repo-relative path the exception applies to.
    path: String,
    /// Byte range inside `path`; `None` means the whole file.
    range: Option<Range<usize>>,
    /// The symref lock entries are keyed by (the file symref for file-bound).
    symref: Symref,
}

impl Bound {
    /// True when `f` is of this exception's rule and lies inside its binding.
    fn covers(&self, f: &Finding, files: &FileInterner) -> bool {
        if f.rule != self.exception.rule {
            return false;
        }
        let Some(span) = f.span else {
            return false;
        };
        if files.path(span.file) != Some(self.path.as_str()) {
            return false;
        }
        self.range.as_ref().is_none_or(|r| {
            r.start <= to_usize(u32::from(span.range.start()))
                && to_usize(u32::from(span.range.end())) <= r.end
        })
    }

    /// Size of the bound region, for choosing the tightest cover.
    fn width(&self) -> usize {
        self.range.as_ref().map_or(usize::MAX, |r| r.end - r.start)
    }
}

fn to_usize(n: u32) -> usize {
    usize::try_from(n).unwrap_or(usize::MAX)
}

/// The exceptions written in `directives`, malformed ones skipped (PARSE001 reports them).
fn collect(
    graph: &SymbolGraph,
    directives: &[DirectiveRecord],
    files: &FileInterner,
) -> Vec<Bound> {
    let mut out = Vec::new();
    for d in directives.iter().filter(|d| d.namespace == "frob") {
        let (rule, kind, because, ticket, until): (RuleId, _, _, _, _) = match d.verb.as_str() {
            "accept" => match Accept::parse_args(&d.args) {
                Ok(a) => (a.rule, ExceptionKind::Accept, a.because, None, a.until),
                Err(_) => continue,
            },
            "defer" => match Defer::parse_args(&d.args) {
                Ok(a) => (
                    a.rule,
                    ExceptionKind::Defer,
                    a.because,
                    Some(a.ticket),
                    a.until,
                ),
                Err(_) => continue,
            },
            _ => continue,
        };
        let Some(own) = files.path(d.span.file) else {
            continue;
        };
        let (path, range, symref) = match &d.bound {
            Binding::Symbol(s) => match graph.get(s) {
                Some(rec) => (
                    s.path().to_owned(),
                    Some(
                        to_usize(u32::from(rec.span.start()))..to_usize(u32::from(rec.span.end())),
                    ),
                    s.clone(),
                ),
                None => (s.path().to_owned(), None, s.clone()),
            },
            Binding::File => (own.to_owned(), None, Symref::file(own)),
        };
        out.push(Bound {
            exception: Exception {
                kind,
                rule,
                reason: because,
                ticket,
                until,
            },
            at: d.span,
            path,
            range,
            symref,
        });
    }
    out
}

/// What applying exceptions decided.
pub struct Resolved {
    /// Findings left standing, plus the EXC findings.
    pub findings: Vec<Finding>,
    /// Suppressed findings with the exception that suppressed each.
    pub suppressed: Vec<(Finding, Exception)>,
}

/// The EXC findings of one exception.
fn police(
    b: &Bound,
    graph: &SymbolGraph,
    lock: &LockFile,
    tickets: &Tickets<'_>,
    policy: &ReasonPolicy,
) -> Vec<Finding> {
    let ex = &b.exception;
    let verb = if ex.kind == ExceptionKind::Accept {
        "accept"
    } else {
        "defer"
    };
    let anchor = format!("{}:{}", b.symref, ex.rule);
    let mut out = Vec::new();
    if let Err(why) = check_reason(&ex.reason, policy) {
        out.push(finding(
            &Exc001,
            Some(b.at),
            format!("`frob:{verb} {}` reason rejected: {why}", ex.rule),
            &anchor,
        ));
    }
    match (ex.kind, ex.ticket.as_deref()) {
        (ExceptionKind::Defer, Some(ticket)) => match tickets.standing(ticket) {
            Standing::Missing => out.push(finding(
                &Exc007,
                Some(b.at),
                format!(
                    "`frob:defer {}` names ticket {ticket}, which does not exist; fix the id or file the ticket",
                    ex.rule
                ),
                &anchor,
            )),
            Standing::Terminal(outcome) => out.push(finding(
                &Exc003,
                Some(b.at),
                format!(
                    "`frob:defer {}` names ticket {ticket}, which is already done ({outcome}); pay the debt or re-point the defer",
                    ex.rule
                ),
                &anchor,
            )),
            Standing::Open | Standing::Unknown => {}
        },
        (ExceptionKind::Accept, _) => {
            let key = b.symref.to_string();
            match lock.entries.get(&key) {
                None => out.push(finding(
                    &Exc005,
                    Some(b.at),
                    format!(
                        "`frob:accept {}` is unattested: `{key}` has no entry in frob.lock; run `frob ack {key}`",
                        ex.rule
                    ),
                    &anchor,
                )),
                Some(entry) => {
                    let live = graph.get(&b.symref).map(|r| r.digests.body.to_string());
                    if live.as_ref().is_some_and(|d| *d != entry.body) {
                        out.push(finding(
                            &Exc005,
                            Some(b.at),
                            format!(
                                "`frob:accept {}`: `{key}` changed since it was attested; re-read it and run `frob ack {key}`",
                                ex.rule
                            ),
                            &anchor,
                        ));
                    }
                }
            }
        }
        _ => {}
    }
    out
}

/// Apply the exceptions of `directives` to `raw`, appending EXC findings.
///
/// `until` dates are not evaluated at milestone 1; a rejected reason, an
/// expired or missing ticket or a stale attestation each raise an EXC finding
/// but the exception still suppresses, so one problem fails the gate once.
pub(crate) fn resolve(
    graph: &SymbolGraph,
    lock: &LockFile,
    directives: &[DirectiveRecord],
    files: &FileInterner,
    tickets: &Tickets<'_>,
    raw: Vec<Finding>,
) -> Resolved {
    let bound = collect(graph, directives, files);
    let policy = ReasonPolicy::default();
    let mut findings = Vec::new();
    let mut suppressed = Vec::new();
    for f in raw {
        let best = bound
            .iter()
            .filter(|b| b.covers(&f, files))
            .min_by_key(|b| b.width());
        match best {
            Some(b) => {
                tracing::debug!(rule = %f.rule, path = %b.path, "finding suppressed by exception");
                suppressed.push((f, b.exception.clone()));
            }
            None => findings.push(f),
        }
    }
    for b in &bound {
        findings.extend(police(b, graph, lock, tickets, &policy));
    }
    Resolved {
        findings,
        suppressed,
    }
}
