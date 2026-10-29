//! CAP005: a new or widened `may` grant needs a human's acknowledgement.
//!
//! Approvals live in `grimble.grants.toml` (one `[[grant]]` per approved grant: the node, the atom
//! as written, its string arguments, the selector texts approved, the attester, the reason and
//! the time). A current grant is *pending* when no approval has its identity (it is `added`) or
//! when it covers a file the approved selectors do not match on the current walk (it is
//! `widened`). Narrowing a grant and removing one never need an ack: the files still covered are
//! a subset of the approved ones, and a gone grant has no subject.
//!
//! A CAP001/CAP002 exception (`accept CAP001 atom=ATOM until=DATE ...`) is approved the same way:
//! its ledger row carries the `rule` and the `until` date. A new exception is `added`; one whose
//! `until` is later than the approved date is `widened`. Grant identity is canonical: an alias
//! (`exec`) and its canonical atom (`process.spawn`) are one identity.
//!
//! The check is a snapshot against the ledger, not a diff against git, so it needs no history
//! and merge commits are judged on the merged result like any other commit. A node rename is a
//! new identity and needs a re-ack. An approval whose attester is no longer in frob.toml's
//! `[evidence] attesters` list counts as no approval. A repository with no ledger file opts out
//! (nothing is pending), like `grimble status` with no baseline; creating the ledger is the
//! first `grimble ack --grants`. Deleting a ledger that git history shows existed is *not* an
//! opt-out: it is reported (CAP005) and every grant and exception is pending again.

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_rules::Severity;
use gob_walk::{Selector, WalkResult};
use grimble_model::ast::EntityKind;

use crate::eval::{Cx, Output};
use crate::grants::files_of;
use crate::model::{CapException, Entity, Grant, Model, canonical_atom};
use crate::types::Role;

/// `(node, rule, canonical atom, args)`: the identity of a grant (empty rule) or an exception.
type Identity = (String, String, String, Vec<String>);

/// The approvals ledger, repo-relative.
pub const LEDGER_FILE: &str = "grimble.grants.toml";

/// One approved grant.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Approval {
    /// The node anchor.
    pub node: String,
    /// The atom (canonical for new rows; old rows may hold the written alias).
    pub atom: String,
    /// The string arguments of the grant.
    pub args: Vec<String>,
    /// The excepted rule for an exception row (`CAP001`/`CAP002`); empty for a grant.
    pub rule: String,
    /// The approved `until` date of an exception row; empty for a grant.
    pub until: String,
    /// The selector texts approved: the `at` text, or the node's `owns` texts for a whole-node grant.
    pub selectors: Vec<String>,
    /// The attester identity (an email of `[evidence] attesters`).
    pub attester: String,
    /// Why the grant was approved.
    pub reason: String,
    /// When it was approved (RFC 3339, as the caller supplies).
    pub at: String,
}

impl Approval {
    fn key(&self) -> Identity {
        (
            self.node.clone(),
            self.rule.clone(),
            canonical_atom(&self.atom),
            self.args.clone(),
        )
    }
}

/// The ledger and the attesters it is judged against.
#[derive(Clone, Debug, Default)]
pub struct Ledger {
    /// The approvals on file.
    pub approvals: Vec<Approval>,
    /// `[evidence] attesters` of frob.toml.
    pub attesters: Vec<String>,
    /// The ledger file is gone though git history shows it existed.
    pub removed: bool,
}

/// Why the ledger cannot be read.
#[derive(Debug, thiserror::Error)]
pub enum LedgerError {
    /// The file exists and cannot be read.
    #[error("cannot read {}: {source}", gob_path::Shown::of(path))]
    Io {
        /// The ledger path.
        path: PathBuf,
        /// The io error.
        source: std::io::Error,
    },
    /// The file is not a valid approvals ledger.
    #[error("{} is not a valid grant ledger: {message}", gob_path::Shown::of(path))]
    Parse {
        /// The ledger path.
        path: PathBuf,
        /// What is wrong.
        message: String,
    },
}

fn str_list(v: Option<&toml::Value>) -> Option<Vec<String>> {
    v.and_then(toml::Value::as_array)?
        .iter()
        .map(|x| x.as_str().map(str::to_owned))
        .collect()
}

fn parse_approval(t: &toml::Table) -> Option<Approval> {
    let text = |k: &str| t.get(k)?.as_str().map(str::to_owned);
    Some(Approval {
        node: text("node")?,
        atom: text("atom")?,
        args: str_list(t.get("args"))?,
        rule: text("rule").unwrap_or_default(),
        until: text("until").unwrap_or_default(),
        selectors: str_list(t.get("selectors"))?,
        attester: text("attester")?,
        reason: text("reason")?,
        at: text("at")?,
    })
}

/// Read `<root>/grimble.grants.toml`; `None` when the repository keeps no ledger.
///
/// # Errors
///
/// [`LedgerError`] for an unreadable or malformed file.
pub fn load(root: &Path) -> Result<Option<Vec<Approval>>, LedgerError> {
    let path = root.join(LEDGER_FILE);
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(source) => return Err(LedgerError::Io { path, source }),
    };
    let bad = |message: &str| LedgerError::Parse {
        path: path.clone(),
        message: message.to_owned(),
    };
    let table = text
        .parse::<toml::Table>()
        .map_err(|e| bad(&e.to_string()))?;
    let rows = match table.get("grant") {
        None => &[][..],
        Some(v) => v.as_array().ok_or_else(|| bad("`grant` is not an array"))?,
    };
    let approvals = rows
        .iter()
        .map(|r| {
            r.as_table()
                .and_then(parse_approval)
                .ok_or_else(|| bad("a [[grant]] lacks a field or has a mistyped one"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    tracing::debug!(count = approvals.len(), "grant ledger loaded");
    Ok(Some(approvals))
}

/// The ledger file text for `approvals`, sorted so the bytes are stable.
pub fn render(approvals: &[Approval]) -> String {
    let mut sorted: Vec<&Approval> = approvals.iter().collect();
    sorted.sort_by_key(|a| a.key());
    let strs =
        |v: &[String]| toml::Value::Array(v.iter().cloned().map(toml::Value::String).collect());
    let rows: Vec<toml::Value> = sorted
        .into_iter()
        .map(|a| {
            let mut t = toml::Table::new();
            t.insert("node".into(), a.node.clone().into());
            t.insert("atom".into(), a.atom.clone().into());
            t.insert("args".into(), strs(&a.args));
            if !a.rule.is_empty() {
                t.insert("rule".into(), a.rule.clone().into());
                t.insert("until".into(), a.until.clone().into());
            }
            t.insert("selectors".into(), strs(&a.selectors));
            t.insert("attester".into(), a.attester.clone().into());
            t.insert("reason".into(), a.reason.clone().into());
            t.insert("at".into(), a.at.clone().into());
            toml::Value::Table(t)
        })
        .collect();
    let mut root = toml::Table::new();
    root.insert("grant".into(), toml::Value::Array(rows));
    let body = toml::to_string(&root).unwrap_or_default();
    format!("# Human approvals of capability grants; written by `grimble ack --grants`.\n{body}")
}

/// `[evidence] attesters` of `<root>/frob.toml` (empty when absent: nobody may attest).
pub fn attesters(root: &Path) -> Vec<String> {
    std::fs::read_to_string(root.join("frob.toml"))
        .ok()
        .and_then(|t| t.parse::<toml::Table>().ok())
        .and_then(|t| str_list(t.get("evidence")?.get("attesters")))
        .unwrap_or_default()
}

/// How a pending grant differs from what was approved.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    /// No approval has this grant.
    Added,
    /// It covers files its approval does not.
    Widened,
}

/// A grant that needs an ack.
#[derive(Clone, Debug)]
pub struct Pending {
    /// The node anchor.
    pub node: String,
    /// The grant as written, with its `at`.
    pub name: String,
    /// New or widened.
    pub kind: Kind,
    /// The approval record an ack would write.
    pub approval_scope: Vec<String>,
    /// The canonical atom.
    pub atom: String,
    /// The string arguments.
    pub args: Vec<String>,
    /// The excepted rule for a CAP exception; empty for a grant.
    pub rule: String,
    /// The `until` date of a CAP exception; empty for a grant.
    pub until: String,
    /// The `.grmb` file and span of the grant.
    pub site: (String, (usize, usize)),
}

fn scope_texts(e: &Entity, g: &Grant) -> Vec<String> {
    match &g.at_text {
        Some(t) => vec![t.clone()],
        None => e
            .clauses_of(Role::Owns)
            .filter_map(|c| c.selector_text.clone())
            .collect(),
    }
}

fn covered(selectors: &[String], walk: &WalkResult) -> BTreeSet<String> {
    let parsed: Vec<Selector> = selectors
        .iter()
        .filter_map(|t| Selector::parse(t).ok())
        .collect();
    files_of(&parsed.iter().collect::<Vec<_>>(), walk)
}

fn grant_name(g: &Grant) -> String {
    let mut out = g.written.clone();
    if !g.args.is_empty() {
        let args: Vec<String> = g.args.iter().map(|a| format!("{a:?}")).collect();
        let _ = write!(out, "({})", args.join(", "));
    }
    if let Some(at) = &g.at_text {
        out.push_str(" at ");
        out.push_str(at);
    }
    out
}

/// The grants of `model` that `ledger` does not cover on `walk`.
pub fn pending(model: &Model, walk: &WalkResult, ledger: &Ledger) -> Vec<Pending> {
    let mut out = Vec::new();
    for e in model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        let owned = covered(
            &e.clauses_of(Role::Owns)
                .filter_map(|c| c.selector_text.clone())
                .collect::<Vec<_>>(),
            walk,
        );
        for g in &e.grants {
            let files = match &g.at {
                Some(sel) => files_of(&[sel], walk),
                None => owned.clone(),
            };
            let approval = ledger.approvals.iter().find(|a| {
                a.node == e.anchor
                    && a.rule.is_empty()
                    && canonical_atom(&a.atom) == canonical_atom(&g.written)
                    && a.args == g.args
                    && ledger.attesters.contains(&a.attester)
            });
            let kind = match approval {
                None => Kind::Added,
                Some(a) if !files.is_subset(&covered(&a.selectors, walk)) => Kind::Widened,
                Some(_) => continue,
            };
            out.push(Pending {
                node: e.anchor.clone(),
                name: grant_name(g),
                kind,
                approval_scope: scope_texts(e, g),
                atom: canonical_atom(&g.written),
                args: g.args.clone(),
                rule: String::new(),
                until: String::new(),
                site: (g.file.clone(), (g.span.start, g.span.end)),
            });
        }
        pending_exceptions(e, ledger, &mut out);
    }
    tracing::debug!(pending = out.len(), "pending grant approvals computed");
    out
}

fn exception_name(x: &CapException) -> String {
    format!(
        "{} {} atom={} until={}",
        x.kind,
        x.rule,
        x.written,
        x.until.as_deref().unwrap_or("?")
    )
}

/// The CAP exceptions of `e` that `ledger` does not cover: new, or with a later `until`.
fn pending_exceptions(e: &Entity, ledger: &Ledger, out: &mut Vec<Pending>) {
    for x in &e.cap_exceptions {
        let until = x.until.clone().unwrap_or_default();
        let approval = ledger.approvals.iter().find(|a| {
            a.node == e.anchor
                && a.rule == x.rule
                && canonical_atom(&a.atom) == x.atom
                && ledger.attesters.contains(&a.attester)
        });
        let kind = match approval {
            None => Kind::Added,
            Some(a) if until > a.until => Kind::Widened,
            Some(_) => continue,
        };
        out.push(Pending {
            node: e.anchor.clone(),
            name: exception_name(x),
            kind,
            approval_scope: Vec::new(),
            atom: x.atom.clone(),
            args: Vec::new(),
            rule: x.rule.clone(),
            until,
            site: (x.file.clone(), (x.span.start, x.span.end)),
        });
    }
}

/// What `grimble ack --grants` works from: the pending grants and every live grant identity.
#[derive(Clone, Debug, Default)]
pub struct GrantState {
    /// Grants the ledger on file does not cover (all of them when there is no ledger).
    pub pending: Vec<Pending>,
    /// `(node, rule, canonical atom, args)` of every grant and CAP exception the model states.
    pub live: BTreeSet<Identity>,
}

/// The [`GrantState`] of `model` on `walk` against `ledger`.
pub fn state(model: &Model, walk: &WalkResult, ledger: &Ledger) -> GrantState {
    let live = model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
        .flat_map(|e| {
            let grants = e.grants.iter().map(|g| {
                (
                    e.anchor.clone(),
                    String::new(),
                    canonical_atom(&g.written),
                    g.args.clone(),
                )
            });
            let excepts = e
                .cap_exceptions
                .iter()
                .map(|x| (e.anchor.clone(), x.rule.clone(), x.atom.clone(), Vec::new()));
            grants.chain(excepts).collect::<Vec<_>>()
        })
        .collect();
    GrantState {
        pending: pending(model, walk, ledger),
        live,
    }
}

/// The ledger after `attester` approves every pending grant, and drops approvals of gone grants.
pub fn approve(
    state: &GrantState,
    ledger: &[Approval],
    attester: &str,
    reason: &str,
    at: &str,
) -> Vec<Approval> {
    let (live, pending) = (&state.live, &state.pending);
    let redone: BTreeSet<Identity> = pending
        .iter()
        .map(|p| {
            (
                p.node.clone(),
                p.rule.clone(),
                p.atom.clone(),
                p.args.clone(),
            )
        })
        .collect();
    let mut out: Vec<Approval> = ledger
        .iter()
        .filter(|a| live.contains(&a.key()))
        .filter(|a| !redone.contains(&a.key()))
        .cloned()
        .collect();
    out.extend(pending.iter().map(|p| Approval {
        node: p.node.clone(),
        atom: p.atom.clone(),
        args: p.args.clone(),
        rule: p.rule.clone(),
        until: p.until.clone(),
        selectors: p.approval_scope.clone(),
        attester: attester.to_owned(),
        reason: reason.to_owned(),
        at: at.to_owned(),
    }));
    out
}

/// Fire CAP005 for each pending grant (no ledger, no subject).
pub fn evaluate(cx: &Cx<'_>, out: &mut Output) {
    let Some(ledger) = cx.grant_ledger else {
        tracing::debug!("no grant ledger; CAP005 has no subject");
        return;
    };
    let pending = pending(cx.model, &cx.code.walk, ledger);
    let total: usize = cx
        .model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
        .map(|e| e.grants.len() + e.cap_exceptions.len())
        .sum();
    out.count("CAP005", total);
    if ledger.removed {
        out.fire(
            "CAP005",
            Severity::Error,
            format!(
                "`{LEDGER_FILE}` existed in git history but is gone; restore it or re-approve every grant with `grimble ack --grants --reason \"...\"`"
            ),
            "cap/ledger",
            None,
        );
    }
    for p in &pending {
        let what = match p.kind {
            Kind::Added => "is new",
            Kind::Widened => "is wider than its approval",
        };
        let (word, anchor) = if p.rule.is_empty() {
            ("grant", format!("cap/{}/grant/{}", p.node, p.atom))
        } else {
            (
                "exception",
                format!("cap/{}/exception/{}/{}", p.node, p.rule, p.atom),
            )
        };
        out.fire(
            "CAP005",
            Severity::Error,
            format!(
                "`{}` {word} `{}` {what}; a human must run `grimble ack --grants --reason \"...\"`",
                p.node, p.name
            ),
            &anchor,
            Some((p.site.0.as_str(), p.site.1)),
        );
    }
    tracing::info!(pending = pending.len(), "CAP005 evaluated");
}
