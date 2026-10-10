//! Exceptions: `frob:accept` and `frob:defer` suppress findings; the EXC rules police them.

use gob_directives::frob::{Accept, Defer};
use gob_directives::{Binding, Directive, DirectiveRecord};
use gob_lock::LockFile;
use gob_rules::{
    BoundException, Exception, ExceptionCtx, ExceptionKind, Finding, ReasonPolicy, Resolved,
    RuleId, Severity, apply_exceptions, check_reason,
};
use gob_symbols::{SymbolGraph, Symref};
use gob_text::{FileInterner, Span};
use gob_time::Day;

use crate::rules::{Exc001, Exc003, Exc005, Exc007, Exc014, Exc016};
use crate::tickets::{Standing, Tickets};
use crate::util::finding;

/// One parsed `frob:accept` or `frob:defer` with where it applies.
pub(crate) struct Bound {
    /// The exception and its binding, in the shape gob-rules matches.
    pub(crate) inner: BoundException,
    /// Where the directive text sits.
    at: Span,
    /// The symref lock entries are keyed by (the file symref for file-bound).
    symref: Symref,
}

fn to_usize(n: u32) -> usize {
    usize::try_from(n).unwrap_or(usize::MAX)
}

/// The exceptions written in `directives`, malformed ones skipped (PARSE001 reports them).
pub(crate) fn collect(
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
            inner: BoundException {
                exception: Exception {
                    kind,
                    rule,
                    reason: because,
                    ticket,
                    until,
                },
                path,
                range,
            },
            at: d.span,
            symref,
        });
    }
    out
}

/// The EXC findings of one exception.
fn police(
    b: &Bound,
    graph: &SymbolGraph,
    lock: &LockFile,
    tickets: &Tickets<'_>,
    policy: &ReasonPolicy,
) -> Vec<Finding> {
    let ex = &b.inner.exception;
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

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// What an `until=` value says about a defer on a given day.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Lapse {
    /// No `until`, a metric target decided elsewhere, or a day not yet past.
    Live,
    /// The last day (inclusive) was before today.
    Expired(Day),
    /// Neither a `YYYY-MM-DD` day nor a metric target.
    Malformed,
}

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// Evaluate the `until` of `ex` against `today`; only defers expire (an accept never lapses).
pub(crate) fn lapse(ex: &Exception, today: Day) -> Lapse {
    let Some(until) = ex
        .until
        .as_deref()
        .filter(|_| ex.kind == ExceptionKind::Defer)
    else {
        return Lapse::Live;
    };
    if until.contains(':') {
        return Lapse::Live;
    }
    match until.parse::<Day>() {
        Ok(day) if day.days_since(today) < 0 => Lapse::Expired(day),
        Ok(_) => Lapse::Live,
        Err(_) => Lapse::Malformed,
    }
}

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// The exceptions of `bound` still in force on `today` (expired defers no longer cover).
pub(crate) fn in_force(bound: &[Bound], today: Day) -> Vec<BoundException> {
    bound
        .iter()
        .filter(|b| !matches!(lapse(&b.inner.exception, today), Lapse::Expired(_)))
        .map(|b| b.inner.clone())
        .collect()
}

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// EXC014 for a defer whose `until` has passed or is not a date.
fn expiry(b: &Bound, today: Day) -> Option<Finding> {
    let ex = &b.inner.exception;
    let anchor = format!("{}:{}", b.symref, ex.rule);
    match lapse(ex, today) {
        Lapse::Live => None,
        Lapse::Expired(day) => Some(finding(
            &Exc014,
            Some(b.at),
            format!(
                "`frob:defer {}` expired on {day} (today is {today}); the deferred finding stands again. Pay the debt or re-defer with a new date",
                ex.rule
            ),
            &anchor,
        )),
        Lapse::Malformed => Some(finding(
            &Exc014,
            Some(b.at),
            format!(
                "`frob:defer {}` has `until={}`, which is neither a YYYY-MM-DD day nor a `kind:target` metric",
                ex.rule,
                ex.until.as_deref().unwrap_or_default()
            ),
            &anchor,
        )),
    }
}

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// Apply `exceptions` to `raw`; an Unresolved finding yields only to a defer, and each accept that names one gets EXC016.
fn apply_in_force(
    raw: Vec<Finding>,
    exceptions: &[BoundException],
    files: &FileInterner,
    bound: &[Bound],
) -> Resolved {
    let ctx = ExceptionCtx { files };
    let (unresolved, resolvable): (Vec<Finding>, Vec<Finding>) = raw
        .into_iter()
        .partition(|f| f.severity == Severity::Unresolved);
    let mut resolved = apply_exceptions(resolvable, exceptions, &ctx);
    let deferrable: Vec<BoundException> = exceptions
        .iter()
        .filter(|b| b.exception.kind != ExceptionKind::Accept)
        .cloned()
        .collect();
    for b in bound
        .iter()
        .filter(|b| b.inner.exception.kind == ExceptionKind::Accept)
    {
        let hit = unresolved
            .iter()
            .filter(|f| b.inner.covers(f, &ctx))
            .count();
        if hit > 0 {
            let ex = &b.inner.exception;
            resolved.findings.push(finding(
                &Exc016,
                Some(b.at),
                format!(
                    "`frob:accept {}` covers {hit} Unresolved finding(s), which an accept cannot park; they stand. Park with `frob:defer {}` and a ticket, or baseline them",
                    ex.rule, ex.rule
                ),
                &format!("{}:{}", b.symref, ex.rule),
            ));
        }
    }
    let rest = apply_exceptions(unresolved, &deferrable, &ctx);
    resolved.findings.extend(rest.findings);
    resolved.suppressed.extend(rest.suppressed);
    resolved
}

/// Apply the exceptions of `directives` to `raw`, appending EXC findings.
///
/// A defer whose `until` day has passed no longer suppresses (EXC014). An
/// Unresolved finding is parked only by a defer; an accept naming one raises
/// EXC016 and the finding stands. A rejected reason, a missing or finished
/// ticket or a stale attestation each raise an EXC finding while the
/// exception still suppresses, so one problem fails the gate once.
pub(crate) fn resolve(
    graph: &SymbolGraph,
    lock: &LockFile,
    directives: &[DirectiveRecord],
    files: &FileInterner,
    tickets: &Tickets<'_>,
    today: Day,
    raw: Vec<Finding>,
) -> Resolved {
    let bound = collect(graph, directives, files);
    let policy = ReasonPolicy::default();
    let mut resolved = apply_in_force(raw, &in_force(&bound, today), files, &bound);
    for b in &bound {
        resolved
            .findings
            .extend(police(b, graph, lock, tickets, &policy));
        resolved.findings.extend(expiry(b, today));
    }
    resolved
}
