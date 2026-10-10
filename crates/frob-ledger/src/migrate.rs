//! One-shot move of a legacy `tickets/<ULID>/` ledger onto the orphan ticket branch (`navigation.md` 2.3).
//!
//! Event files are copied byte for byte under `.events/<ULID>/`, ticket files are the fold of
//! those events at their computed `<top-epic-slug>/<slug>.md` path, and milestone and cycle
//! objects keep their relative layout at the branch root. Before anything is written the plan is
//! checked in memory (every ticket's file parses back to its fold); after the commit every file is
//! read back from the branch and compared.

use std::collections::{BTreeMap, BTreeSet};

use gob_git::{CommitOptions, Oid, RelPath};

use crate::branch::{BranchInit, init_branch};
use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::{Event, sort_events};
use crate::fold::fold;
use crate::id::{EventId, TicketId};
use crate::layout::{self, Layout};
use crate::ledger::Ledger;
use crate::model::{Ticket, TicketType};

/// What a migration planned or did.
#[derive(Debug, Clone)]
pub struct MigrateReport {
    /// The orphan branch.
    pub branch: String,
    /// Tickets moved.
    pub tickets: usize,
    /// Ticket event files copied.
    pub events: usize,
    /// Milestone and cycle files copied.
    pub object_files: usize,
    /// Tickets whose `ticket.md` on the old branch differed from the fold of its events.
    pub drifted: Vec<TicketId>,
    /// Each ticket and the branch path it gets, sorted by path.
    pub mapping: Vec<(TicketId, String)>,
    /// The migration commit; `None` for a dry run or when the branch already held the ledger.
    pub commit: Option<Oid>,
    /// The branch already held a migrated ledger; nothing was written.
    pub already: bool,
}

/// Everything read from the old ledger: tickets with their raw event files, and passthrough files.
struct Source {
    tickets: BTreeMap<TicketId, Ticket>,
    events: BTreeMap<TicketId, Vec<(EventId, Vec<u8>)>>,
    objects: Vec<(String, Vec<u8>)>,
    drifted: Vec<TicketId>,
}

/// The short random part the writer appends to a colliding slug.
fn short(id: TicketId) -> String {
    id.random_part()[..7].to_owned()
}

/// Directory slug of the epic `id`, with every colliding top-level epic suffixed.
fn epic_dirs(tickets: &BTreeMap<TicketId, Ticket>) -> BTreeMap<TicketId, String> {
    let is_top = |t: &Ticket| {
        t.front.ty == TicketType::Epic && ancestors_epic(tickets, t.front.parent).is_none()
    };
    let mut by_slug: BTreeMap<String, Vec<TicketId>> = BTreeMap::new();
    for t in tickets.values().filter(|t| is_top(t)) {
        let slug = layout::title_slug(&t.front.title, &short(t.front.id));
        by_slug.entry(slug).or_default().push(t.front.id);
    }
    let mut out = BTreeMap::new();
    for (slug, ids) in by_slug {
        for id in &ids {
            let name = if ids.len() > 1 {
                format!("{slug}-{}", short(*id))
            } else {
                slug.clone()
            };
            out.insert(*id, name);
        }
    }
    out
}

/// The outermost epic among the ancestors starting at `parent`.
fn ancestors_epic(
    tickets: &BTreeMap<TicketId, Ticket>,
    parent: Option<TicketId>,
) -> Option<TicketId> {
    let mut top = None;
    let mut cur = parent;
    for _ in 0..64 {
        let Some(id) = cur else { break };
        let Some(t) = tickets.get(&id) else { break };
        cur = t.front.parent;
        if t.front.ty == TicketType::Epic {
            top = Some(id);
        }
    }
    top
}

/// Branch path of every ticket; slugs that collide inside one directory all get `-<short>`.
fn paths(tickets: &BTreeMap<TicketId, Ticket>) -> BTreeMap<TicketId, String> {
    let dirs = epic_dirs(tickets);
    let mut groups: BTreeMap<(Option<String>, String), Vec<TicketId>> = BTreeMap::new();
    let mut out = BTreeMap::new();
    for t in tickets.values() {
        let id = t.front.id;
        let slug = layout::title_slug(&t.front.title, &short(id));
        match ancestors_epic(tickets, t.front.parent) {
            None if t.front.ty == TicketType::Epic => {
                out.insert(id, layout::branch_ticket_path(t.front.ty, &dirs[&id], None));
            }
            top => {
                let dir = top.and_then(|e| dirs.get(&e).cloned());
                groups.entry((dir, slug)).or_default().push(id);
            }
        }
    }
    for ((dir, slug), ids) in groups {
        let clash = ids.len() > 1 || slug.eq_ignore_ascii_case("epic");
        for id in ids {
            let name = if clash {
                format!("{slug}-{}", short(id))
            } else {
                slug.clone()
            };
            out.insert(
                id,
                layout::branch_ticket_path(tickets[&id].front.ty, &name, dir.as_deref()),
            );
        }
    }
    out
}

impl Ledger {
    /// Read the legacy ledger at its tip into a [`Source`].
    fn read_source(&self) -> Result<Source> {
        let ref_name = self.ledger_ref()?;
        let tip = self
            .tip_of(&ref_name)?
            .ok_or_else(|| LedgerError::invalid("the ledger has no commits to migrate"))?;
        let dir = self.config().dir.clone();
        let mut src = Source {
            tickets: BTreeMap::new(),
            events: BTreeMap::new(),
            objects: Vec::new(),
            drifted: Vec::new(),
        };
        let mut docs: BTreeMap<TicketId, String> = BTreeMap::new();
        let mut unknown = Vec::new();
        for (rel, oid) in self.list_blobs(&format!("{tip}:{dir}"))? {
            let parts: Vec<&str> = rel.split('/').collect();
            let bytes = || self.repo().read_blob(&oid);
            let tid = parts[0].parse::<TicketId>().ok();
            match (parts.as_slice(), tid) {
                ([head, ..], _) if head.starts_with('_') => {
                    src.objects.push((rel.clone(), bytes()?));
                }
                ([_, "ticket.md"], Some(tid)) => {
                    let text = String::from_utf8(bytes()?)
                        .map_err(|_| LedgerError::malformed(rel.clone(), "not valid UTF-8"))?;
                    docs.insert(tid, text);
                }
                ([_, "events", file], Some(tid)) => {
                    let eid = file
                        .strip_suffix(".toml")
                        .and_then(|s| s.parse::<EventId>().ok());
                    match eid {
                        Some(eid) => src.events.entry(tid).or_default().push((eid, bytes()?)),
                        None => unknown.push(rel.clone()),
                    }
                }
                _ => unknown.push(rel.clone()),
            }
        }
        if !unknown.is_empty() {
            return Err(LedgerError::invalid(format!(
                "{} file(s) under {dir}/ are neither tickets, events nor milestone or cycle objects, e.g. {}; migrating would lose them",
                unknown.len(),
                unknown[0]
            )));
        }
        for (id, raw) in &src.events {
            let mut events = Vec::with_capacity(raw.len());
            for (eid, bytes) in raw {
                let text = String::from_utf8_lossy(bytes);
                events.push(Event::parse(*eid, &text)?);
            }
            sort_events(&mut events);
            let folded = fold(*id, &events)?.ticket;
            match docs.get(id).map(|t| doc::parse("ticket.md", t)) {
                Some(Ok(old)) if old.front == folded.front => {}
                _ => src.drifted.push(*id),
            }
            src.tickets.insert(*id, folded);
        }
        let orphans: Vec<_> = docs
            .keys()
            .filter(|id| !src.tickets.contains_key(id))
            .collect();
        if let Some(id) = orphans.first() {
            return Err(LedgerError::invalid(format!(
                "ticket {id} has a ticket.md but no events; it cannot be folded ({} such tickets)",
                orphans.len()
            )));
        }
        tracing::info!(
            tickets = src.tickets.len(),
            drifted = src.drifted.len(),
            objects = src.objects.len(),
            "legacy ledger read for migration"
        );
        Ok(src)
    }

    /// Copy the legacy ledger onto the orphan branch `[tickets] branch`, verifying the result.
    ///
    /// With `dry_run` nothing is written. The branch is created when missing; when it already
    /// holds `.events/` the call writes nothing and reports `already`. Verification failures
    /// leave the branch for inspection and return an error.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] for a ledger already on the ticket branch layout, an unrecognized
    /// file or a verification mismatch; fold, malformed-file and git failures.
    pub fn migrate_to_branch(&self, dry_run: bool) -> Result<MigrateReport> {
        if self.layout() != Layout::Dir {
            return Err(LedgerError::invalid(
                "the ledger is already on the ticket-branch layout",
            ));
        }
        let src = self.read_source()?;
        let mapping = paths(&src.tickets);
        let mut files: Vec<(String, Vec<u8>)> = Vec::new();
        for (id, ticket) in &src.tickets {
            let text = doc::render(ticket)?;
            let back = doc::parse("ticket.md", &text)?;
            if back.front != ticket.front {
                return Err(LedgerError::invalid(format!(
                    "ticket {id} does not survive rendering; migration aborted"
                )));
            }
            files.push((mapping[id].clone(), text.into_bytes()));
            for (eid, bytes) in src.events.get(id).into_iter().flatten() {
                files.push((
                    format!("{}/{eid}.toml", layout::branch_events_dir(*id)),
                    bytes.clone(),
                ));
            }
        }
        let events = files.len() - src.tickets.len();
        files.extend(src.objects.iter().cloned());
        let names: BTreeSet<&String> = files.iter().map(|(p, _)| p).collect();
        if names.len() != files.len() {
            return Err(LedgerError::invalid("two migrated files share one path"));
        }
        let mut report = MigrateReport {
            branch: self.config().branch.clone(),
            tickets: src.tickets.len(),
            events,
            object_files: src.objects.len(),
            drifted: src.drifted,
            mapping: {
                let mut m: Vec<_> = mapping.into_iter().collect();
                m.sort_by(|a, b| a.1.cmp(&b.1));
                m
            },
            commit: None,
            already: false,
        };
        if dry_run {
            return Ok(report);
        }
        let branch = report.branch.clone();
        let full = format!("refs/heads/{branch}");
        let init = init_branch(&self.repo, &branch, self.config().cas_retries)
            .map_err(|e| LedgerError::invalid(e.to_string()))?;
        if let BranchInit::Already(tip) = init
            && !self
                .list_blobs(&format!("{tip}:{}", layout::EVENTS_DIR))?
                .is_empty()
        {
            tracing::info!(%branch, "ticket branch already holds a ledger; nothing migrated");
            report.already = true;
            return Ok(report);
        }
        let mut changes = Vec::with_capacity(files.len());
        for (path, bytes) in &files {
            changes.push((RelPath::new(path.clone())?, Some(bytes.clone())));
        }
        let opts = CommitOptions {
            cas_retries: self.config().cas_retries,
            author: None,
        };
        let out = self.repo.commit_paths(
            &full,
            &changes,
            &format!(
                "tickets(migrate): {} tickets, {} events, {} object files",
                report.tickets, report.events, report.object_files
            ),
            &opts,
        )?;
        self.verify_branch(&full, &files)?;
        tracing::info!(%branch, commit = %out.oid, files = files.len(), "legacy ledger migrated and verified");
        report.commit = Some(out.oid);
        Ok(report)
    }

    /// Read every planned file back from `branch_ref` and compare bytes; any difference is an error.
    fn verify_branch(&self, branch_ref: &str, planned: &[(String, Vec<u8>)]) -> Result<()> {
        let tip = self.repo.rev_parse(branch_ref)?;
        let found: BTreeMap<String, Oid> = self.list_blobs(&tip.to_string())?.into_iter().collect();
        for (path, bytes) in planned {
            let Some(oid) = found.get(path) else {
                return Err(LedgerError::invalid(format!(
                    "verification failed: {path} is missing on {branch_ref}"
                )));
            };
            if self.repo.read_blob(oid)? != *bytes {
                return Err(LedgerError::invalid(format!(
                    "verification failed: {path} differs on {branch_ref}"
                )));
            }
        }
        let extra = found
            .keys()
            .filter(|p| !planned.iter().any(|(q, _)| q == *p))
            .filter(|p| !matches!(p.as_str(), "README.md" | ".gitattributes"))
            .count();
        if extra > 0 {
            return Err(LedgerError::invalid(format!(
                "verification failed: {extra} unexpected file(s) on {branch_ref}"
            )));
        }
        Ok(())
    }
}
