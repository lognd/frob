//! SYS006 contract skew, SYS007 changed since ack and SYS008 renamed, over `grimble.lock`
//! (binding.md 5 and 6.6 to 6.8).
//!
//! Every rule is P0: it fires only when both sides of a comparison are Exact, certifies clean
//! only then, and is Unresolved with a reason code otherwise. A lock written under another
//! format or digest scheme yields one SYS007 `scheme` finding per entry and nothing else: its
//! digests are not comparable, so nothing is silently accepted (the REATTEST state of the
//! exceptions design is this same comparison, not a separate rule).

//! # SYS006 and `versioning compat=backward`
//!
//! Two comparisons feed one finding per flow. The end comparison checks each end's Contract
//! digest against the one recorded at ack. The shape comparison runs when both ends of the lock
//! entry carry a `shape_contract` and the flow names a contract: with `S_p`, `S_c` the recorded
//! digests and `S_live` the Contract facet of the contract's one Must shape identity, it fires
//! when `S_p != S_c`, `S_live != S_p` or `S_live != S_c`; a non-Exact `S_live` is Unresolved.
//! The severity is `Warn` only when the contract writes `versioning compat=backward` and every
//! comparison that fired shows nothing but a consumer behind a producer that moved forward
//! (end mode: the producer end changed since a consistent ack while the consumer end did not;
//! shape mode: `S_p == S_live != S_c`). Any other skew, and any skew under `compat=none`,
//! `forward`, `full` or no `versioning`, is an `Error`; `compat` never decides whether skew
//! exists.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4

use std::collections::{BTreeMap, BTreeSet};

use gob_lock::{LockEntry, LockFile};
use gob_rules::Severity;

use crate::code::Code;
use crate::live::{Live, LiveSymbol, body_tokens};
use crate::model::FlowContract;
use crate::rules::{Output, path_of};
use crate::types::{Reason, Role, Row, Source, Status};

/// The lock file as a finding anchor and site.
pub const LOCK_ANCHOR: &str = "grimble.lock";

/// Everything the lock rules read.
pub struct DriftCx<'a> {
    /// The folded code.
    pub code: &'a Code,
    /// The symbols as they stand now.
    pub live: &'a Live,
    /// The rows of B.
    pub rows: &'a [Row],
    /// The lock as recorded.
    pub lock: &'a LockFile,
    /// The contract each flow names, with its compat.
    pub contracts: &'a BTreeMap<String, FlowContract>,
    /// A Body with fewer atoms than this cannot be paired as a rename (binding.md 5.4 item 3).
    pub rename_min_tokens: usize,
}

fn short(d: &str) -> &str {
    d.get(..12).unwrap_or(d)
}

fn extension(path: &str) -> &str {
    path.rsplit_once('.').map_or("", |(_, e)| e)
}

fn lock_site() -> (&'static str, (usize, usize)) {
    (LOCK_ANCHOR, (0, 0))
}

fn site_of(l: &LiveSymbol) -> (&str, (usize, usize)) {
    (l.path.as_str(), l.span)
}

fn changed_facets(e: &LockEntry, l: &LiveSymbol) -> Vec<&'static str> {
    [
        ("sig", &e.sig, &l.facets.sig),
        ("body", &e.body, &l.facets.body),
        ("doc", &e.doc, &l.facets.doc),
        ("attr", &e.attr, &l.facets.attr),
    ]
    .into_iter()
    .filter(|(_, was, now)| was != now)
    .map(|(n, _, _)| n)
    .collect()
}

/// New identities: live symbols nobody acked, indexed by Body digest (exact bodies only).
fn unacked_by_body(cx: &DriftCx<'_>) -> BTreeMap<String, Vec<String>> {
    let mut idx: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for (k, l) in &cx.live.symbols {
        if cx.lock.entries.contains_key(k) || l.unknown.iter().any(|u| u == "body") {
            continue;
        }
        idx.entry(l.facets.body.clone())
            .or_default()
            .push(k.clone());
    }
    idx
}

/// True when a new same-language symbol has an Unknown Body, or an unreadable file could hold one.
fn hidden_candidate(cx: &DriftCx<'_>, gone: &str) -> bool {
    let ext = extension(path_of(gone));
    cx.live.unreadable.iter().any(|p| extension(p) == ext)
        || cx.live.symbols.iter().any(|(k, l)| {
            !cx.lock.entries.contains_key(k)
                && extension(&l.path) == ext
                && l.unknown.iter().any(|u| u == "body")
        })
}

fn sys007_symbol(
    cx: &DriftCx<'_>,
    key: &str,
    e: &LockEntry,
    by_body: &mut Option<BTreeMap<String, Vec<String>>>,
    out: &mut Output,
    hidden_gone: &mut BTreeSet<String>,
) {
    out.count("SYS007", 1);
    if let Some(l) = cx.live.symbols.get(key) {
        if let Some(reason) = l.inexact() {
            out.unresolved(
                "SYS007",
                reason,
                &format!(
                    "{key} is acked but its facets are not Exact now ({}); the ack cannot be compared",
                    if reason == Reason::Fidelity {
                        "language fidelity below F2"
                    } else {
                        "a facet holds a parse hole"
                    }
                ),
                key,
                Some(site_of(l)),
            );
            return;
        }
        let changed = changed_facets(e, l);
        if !changed.is_empty() {
            out.fire(
                "SYS007",
                Severity::Error,
                format!(
                    "kind facet: {key} changed since ack ({}) by {} at {}",
                    changed.join(", "),
                    e.acked_by,
                    e.acked_at
                ),
                key,
                Some(site_of(l)),
            );
        }
        return;
    }
    let idx = by_body.get_or_insert_with(|| unacked_by_body(cx));
    let candidates: Vec<&str> = idx
        .get(&e.body)
        .into_iter()
        .flatten()
        .map(String::as_str)
        .filter(|c| {
            extension(path_of(c)) == extension(path_of(key))
                && cx
                    .live
                    .symbols
                    .get(*c)
                    .is_some_and(|l| body_tokens(cx.code, &l.path, c) >= cx.rename_min_tokens)
        })
        .collect();
    if !candidates.is_empty() {
        out.fire(
            "SYS008",
            Severity::Advisory,
            format!(
                "{key} is gone and its Body now appears at {}; if it is a rename run `grimble ack --rename {key} {}`",
                candidates.join(", "),
                candidates[0]
            ),
            key,
            Some(lock_site()),
        );
        return;
    }
    if hidden_candidate(cx, key) {
        hidden_gone.insert(key.to_owned());
        out.unresolved(
            "SYS007",
            Reason::UnseenRemainder,
            &format!("{key} is gone but a same-language file hides units that could hold it"),
            key,
            Some(lock_site()),
        );
        return;
    }
    out.fire(
        "SYS007",
        Severity::Error,
        format!(
            "kind gone: {key} was acked by {} at {} and no longer exists",
            e.acked_by, e.acked_at
        ),
        key,
        Some(lock_site()),
    );
}

/// One end of a flow as it stands now.
pub(crate) enum End {
    /// The flow has no row for the role.
    Absent,
    Exact {
        /// The identity bound at Must.
        identity: String,
        /// Its Contract digest (hex).
        contract: String,
    },
    /// Not Exact: the reason code and a sentence.
    Unresolved(Reason, String),
}

/// The end of `flow` in `role`: the Must identity (the `recorded` one when it is among several)
/// and its Contract digest, or why that cannot be said.
pub(crate) fn live_end(
    rows: &[Row],
    live: &Live,
    flow: &str,
    role: Role,
    recorded: Option<&str>,
) -> End {
    let rows: Vec<&Row> = rows
        .iter()
        .filter(|r| r.entity == flow && r.role == role)
        .collect();
    if rows.is_empty() {
        return End::Absent;
    }
    let musts: Vec<&str> = rows
        .iter()
        .filter(|r| r.status == Status::Must && r.source != Source::Residual)
        .filter_map(|r| r.identity.as_deref())
        .collect();
    let name = role.as_str();
    let identity = if let Some(r) = recorded.filter(|r| musts.contains(r)) {
        r
    } else if let [one] = musts.as_slice() {
        one
    } else if musts.is_empty() {
        let reason = if rows.iter().any(|r| r.source == Source::Residual) {
            Reason::UnseenRemainder
        } else {
            Reason::MayOnlyOwner
        };
        return End::Unresolved(
            reason,
            format!("the {name} end binds only May rows or hidden units"),
        );
    } else {
        return End::Unresolved(
            Reason::MayOnlyOwner,
            format!(
                "the {name} end binds {} identities and not the acked one",
                musts.len()
            ),
        );
    };
    match live.symbols.get(identity) {
        None => End::Unresolved(
            Reason::Fidelity,
            format!("the {name} end {identity} has no facet digests (no unit of an adapter)"),
        ),
        Some(l) => match l.inexact() {
            Some(reason) => End::Unresolved(
                reason,
                format!("the {name} end {identity}: its Contract facet is not Exact"),
            ),
            None => End::Exact {
                identity: identity.to_owned(),
                contract: l.facets.contract.clone(),
            },
        },
    }
}

/// The shape of a flow's contract as it stands now.
pub(crate) enum Shape {
    /// The contract has no `shape` row.
    Absent,
    /// Its one Must shape identity and that identity's Contract digest (hex).
    Exact(String),
    /// Not Exact: the reason code and a sentence.
    Unresolved(Reason, String),
}

/// The live Contract digest of the one `shape` identity of the contract entity `contract`.
pub(crate) fn live_shape(rows: &[Row], live: &Live, contract: &str) -> Shape {
    let rows: Vec<&Row> = rows
        .iter()
        .filter(|r| r.entity == contract && r.role == Role::Shape)
        .collect();
    if rows.is_empty() {
        return Shape::Absent;
    }
    let musts: Vec<&str> = rows
        .iter()
        .filter(|r| r.status == Status::Must && r.source != Source::Residual)
        .filter_map(|r| r.identity.as_deref())
        .collect();
    let [id] = musts.as_slice() else {
        let reason = if musts.is_empty() && rows.iter().any(|r| r.source == Source::Residual) {
            Reason::UnseenRemainder
        } else {
            Reason::MayOnlyOwner
        };
        return Shape::Unresolved(
            reason,
            format!(
                "{contract} has {} Must shape identities, need one",
                musts.len()
            ),
        );
    };
    match live.symbols.get(*id) {
        None => Shape::Unresolved(
            Reason::Fidelity,
            format!("the shape {id} of {contract} has no facet digests"),
        ),
        Some(l) => l.inexact().map_or_else(
            || Shape::Exact(l.facets.contract.clone()),
            |reason| {
                Shape::Unresolved(
                    reason,
                    format!("the shape {id} of {contract}: its Contract facet is not Exact"),
                )
            },
        ),
    }
}

/// Skew over the end identities' Contract digests: the reasons, and whether the only skew is a
/// consumer behind a producer that moved forward from a consistent ack.
fn end_skew(
    fe: &gob_lock::FlowEntry,
    (pi, pc): (&str, &str),
    (ci, cc): (&str, &str),
    why: &mut Vec<String>,
) -> bool {
    let (p_moved, c_moved) = (pc != fe.producer.contract, cc != fe.consumer.contract);
    let before = fe.producer.contract == fe.consumer.contract;
    if pc != cc {
        why.push(format!(
            "the ends differ: producer {} vs consumer {}",
            short(pc),
            short(cc)
        ));
    }
    if p_moved {
        why.push(format!(
            "the producer end {pi} is ahead of its ack ({} acked, {} now)",
            short(&fe.producer.contract),
            short(pc)
        ));
    }
    if c_moved {
        why.push(format!(
            "the consumer end {ci} is ahead of its ack ({} acked, {} now)",
            short(&fe.consumer.contract),
            short(cc)
        ));
    }
    p_moved && !c_moved && before
}

/// Skew over the contract shape digests (binding.md 6.6): fires when `S_p != S_c` or `S_live`
/// differs from either; the only skew is "consumer behind" when `S_p == S_live != S_c`.
fn shape_skew(sp: &str, sc: &str, live: &str, why: &mut Vec<String>) -> bool {
    if sp != sc {
        why.push(format!(
            "the ends were attested against different contract shapes: producer {} vs consumer {}",
            short(sp),
            short(sc)
        ));
    }
    if live != sp {
        why.push(format!(
            "the contract shape changed since the producer ack ({} acked, {} now)",
            short(sp),
            short(live)
        ));
    }
    if live != sc {
        why.push(format!(
            "the contract shape changed since the consumer ack ({} acked, {} now)",
            short(sc),
            short(live)
        ));
    }
    sp == live && sc != live
}

/// The severity of a skew: `Warn` only under `versioning compat=backward` when every compared
/// side shows nothing but a consumer behind a producer that moved forward; otherwise `Error`.
fn skew_severity(compat: Option<&str>, only_consumer_behind: bool) -> Severity {
    if compat == Some("backward") && only_consumer_behind {
        Severity::Warn
    } else {
        Severity::Error
    }
}

fn sys006(cx: &DriftCx<'_>, key: &str, out: &mut Output) {
    let Some(fe) = cx.lock.flows.get(key) else {
        return;
    };
    let (rows, live) = (cx.rows, cx.live);
    let p = live_end(rows, live, key, Role::Producer, Some(&fe.producer.identity));
    let c = live_end(rows, live, key, Role::Consumer, Some(&fe.consumer.identity));
    let (
        End::Exact {
            identity: pi,
            contract: pc,
        },
        End::Exact {
            identity: ci,
            contract: cc,
        },
    ) = (&p, &c)
    else {
        for end in [&p, &c] {
            if let End::Unresolved(reason, why) = end {
                out.count("SYS006", 1);
                out.unresolved(
                    "SYS006",
                    *reason,
                    &format!("{key}: {why}"),
                    key,
                    Some(lock_site()),
                );
                return;
            }
        }
        tracing::debug!(
            flow = key,
            "an end is not bound now; SYS009 and SYS007 speak for it"
        );
        return;
    };
    out.count("SYS006", 1);
    let mut why = Vec::new();
    let mut only_consumer_behind = true;
    let mut skewed = false;
    let ends_skewed = pc != cc || *pc != fe.producer.contract || *cc != fe.consumer.contract;
    if ends_skewed {
        only_consumer_behind &= end_skew(fe, (pi, pc), (ci, cc), &mut why);
        skewed = true;
    }
    let contract = cx.contracts.get(key);
    if let (Some(sp), Some(sc), Some(k)) = (
        &fe.producer.shape_contract,
        &fe.consumer.shape_contract,
        contract,
    ) {
        match live_shape(rows, live, &k.anchor) {
            Shape::Exact(sl) => {
                if sp != sc || *sl != **sp || *sl != **sc {
                    only_consumer_behind &= shape_skew(sp, sc, &sl, &mut why);
                    skewed = true;
                }
            }
            Shape::Unresolved(reason, text) => {
                out.unresolved(
                    "SYS006",
                    reason,
                    &format!("{key}: {text}"),
                    key,
                    Some(lock_site()),
                );
                return;
            }
            Shape::Absent => {
                tracing::debug!(flow = key, contract = %k.anchor, "contract has no shape row; shape skew not compared");
            }
        }
    }
    if !skewed {
        return;
    }
    let behind = match (*pc != fe.producer.contract, *cc != fe.consumer.contract) {
        (true, false) => format!("the consumer {ci} is behind"),
        (false, true) => format!("the producer {pi} is behind"),
        _ => format!("producer {pi} and consumer {ci}"),
    };
    let compat = contract.and_then(|k| k.compat.as_deref());
    let severity = skew_severity(compat, only_consumer_behind);
    tracing::debug!(flow = key, ?compat, ?severity, "contract skew found");
    out.fire(
        "SYS006",
        severity,
        format!("contract skew on {key}: {behind}; {}", why.join("; ")),
        key,
        Some(lock_site()),
    );
}

/// Why SYS008 has no subject, or `None` when `grimble.lock` records symbol anchors.
///
/// The fact SYS008 depends on is that a lock with entries exists: each entry is examined for
/// being gone with a rename candidate. With such a lock, zero gone anchors is a measured clean,
/// not an inapplicable rule; with no lock or no entry there is nothing to pair.
pub fn sys008_inapplicable(lock: &gob_lock::LockFile) -> Option<&'static str> {
    lock.entries
        .is_empty()
        .then_some("grimble.lock is absent or records no symbol anchor, so no rename can be paired")
}

/// Evaluate SYS006, SYS007 and SYS008 over the lock; counts a subject per entry.
pub fn evaluate(cx: &DriftCx<'_>, out: &mut Output) {
    // Every lock entry is a SYS008 subject (examined for being gone with a rename candidate).
    // Whether the rule applies at all was decided before evaluation ([`sys008_inapplicable`]).
    out.count("SYS008", cx.lock.entries.len());
    if !cx.lock.flows.is_empty() {
        out.subjects.entry("SYS006").or_default();
    }
    if !cx.lock.entries.is_empty() || !cx.lock.flows.is_empty() {
        out.subjects.entry("SYS007").or_default();
    }
    let stale = cx.lock.reattest();
    if !stale.is_empty() {
        for r in &stale {
            out.count("SYS007", 1);
            out.fire(
                "SYS007",
                Severity::Error,
                format!("kind scheme: {} {}", r.key, r.why()),
                &r.key,
                Some(lock_site()),
            );
        }
        return;
    }
    let mut by_body = None;
    let mut hidden_gone = BTreeSet::new();
    for (key, e) in &cx.lock.entries {
        sys007_symbol(cx, key, e, &mut by_body, out, &mut hidden_gone);
    }
    if !hidden_gone.is_empty() {
        out.unresolved(
            "SYS008",
            Reason::UnseenRemainder,
            &format!(
                "{} gone identities may have been renamed into units that hide their Body",
                hidden_gone.len()
            ),
            LOCK_ANCHOR,
            Some(lock_site()),
        );
    }
    for key in cx.lock.flows.keys() {
        sys006(cx, key, out);
    }
    tracing::info!(
        entries = cx.lock.entries.len(),
        flows = cx.lock.flows.len(),
        "lock rules evaluated"
    );
}
