//! The [`Ledger`]: git access to the ledger ref, the synced index and the commit path.
//!
//! Reads come from the ledger ref's tree (never the worktree), writes go
//! through [`gob_git::Repo::commit_paths`] on that ref, so staged changes of a
//! user can never enter a ledger commit (decision D23).

use std::path::PathBuf;

use gob_git::{CommitOptions, Oid, RelPath, Repo, TreeRef};

use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::Event;
use crate::fold::fold;
use crate::id::{EventId, TicketId, compute_handles, display_handle};
use crate::index::Index;
use crate::model::Ticket;

const EMPTY_TREE: &str = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";
const MAX_RECONCILE: u32 = 3;

/// Where ledger commits go.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RefMode {
    /// The configured ref (default the trunk branch), whatever is checked out.
    #[default]
    Trunk,
    /// The currently checked-out branch, for protected-trunk and fork flows.
    Branch,
}

impl std::str::FromStr for RefMode {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s {
            "trunk" => Ok(Self::Trunk),
            "branch" => Ok(Self::Branch),
            other => Err(format!(
                "`{other}` is not a ref mode; expected trunk or branch"
            )),
        }
    }
}

/// Everything the ledger needs from `[tickets]` and `[git]` configuration.
#[derive(Debug, Clone)]
pub struct LedgerConfig {
    /// Ref holding the ledger in trunk mode (`refs/heads/main`).
    pub ref_name: String,
    /// Trunk or branch mode.
    pub mode: RefMode,
    /// Directory of ticket directories, relative to the repo root.
    pub dir: String,
    /// Compare-and-swap retries (`[git] cas_retries`).
    pub cas_retries: u32,
    /// Minimum handle length (`[tickets] handle_min_len`).
    pub handle_min_len: usize,
    /// Actor override (`[tickets] actor`); git `user.name` when `None`.
    pub actor: Option<String>,
}

impl LedgerConfig {
    /// Whether `path` (repo-relative) lies under the ledger directory, i.e. is ledger bookkeeping.
    ///
    /// frob:ticket 01M419M06CMCGJ39Y4HYPACKXP
    #[must_use]
    pub fn is_ledger_path(&self, path: &str) -> bool {
        path.strip_prefix(self.dir.trim_end_matches('/'))
            .is_some_and(|rest| rest.starts_with('/'))
    }
}

impl Default for LedgerConfig {
    fn default() -> Self {
        Self {
            ref_name: "refs/heads/main".to_owned(),
            mode: RefMode::Trunk,
            dir: "tickets".to_owned(),
            cas_retries: 5,
            handle_min_len: crate::id::DEFAULT_HANDLE_MIN_LEN,
            actor: None,
        }
    }
}

/// An open ledger: a repository plus its configuration.
#[derive(Debug)]
pub struct Ledger {
    pub(crate) repo: Repo,
    pub(crate) cfg: LedgerConfig,
    index_path: PathBuf,
}

/// The index synced to one ledger tip, with the facts a writer needs.
pub(crate) struct Synced {
    pub index: Index,
    pub ref_name: String,
    pub tip: Option<Oid>,
    pub tree: Option<Oid>,
    pub key: String,
}

/// A committed change to one ticket.
#[derive(Debug, Clone)]
pub struct Applied {
    /// The ticket after the change.
    pub ticket: Ticket,
    /// Its handle with `~`.
    pub handle: String,
    /// Ids of the events written (empty when `already`).
    pub events: Vec<EventId>,
    /// True when the request already held and nothing was written.
    pub already: bool,
    /// The ledger commit, when one was made.
    pub commit: Option<Oid>,
}

fn full_ref(name: &str) -> String {
    if name.starts_with("refs/") {
        name.to_owned()
    } else {
        format!("refs/heads/{name}")
    }
}

fn is_rev_error(e: &gob_git::GitError) -> bool {
    matches!(e, gob_git::GitError::Rev { .. })
}

impl Ledger {
    /// Open the ledger of `repo` under `cfg`.
    pub fn open(repo: Repo, cfg: LedgerConfig) -> Self {
        let index_path = repo.work_dir().map_or_else(
            || repo.git_dir().join("frob").join("tickets.sqlite"),
            |w| w.join(".frob").join("tickets.sqlite"),
        );
        tracing::debug!(index = %index_path.display(), ref_name = %cfg.ref_name, mode = ?cfg.mode, "ledger opened");
        Self {
            repo,
            cfg,
            index_path,
        }
    }

    /// The underlying repository.
    pub fn repo(&self) -> &Repo {
        &self.repo
    }

    /// The configuration in force.
    pub fn config(&self) -> &LedgerConfig {
        &self.cfg
    }

    /// The actor recorded on events: `[tickets] actor`, else git `user.name`.
    ///
    /// # Errors
    ///
    /// [`gob_git::GitError::NoIdentity`] when neither is set.
    pub fn actor(&self) -> Result<String> {
        if let Some(a) = self.cfg.actor.as_ref().filter(|a| !a.is_empty()) {
            return Ok(a.clone());
        }
        self.repo
            .config_user()
            .map(|(name, _)| name)
            .ok_or_else(|| gob_git::GitError::NoIdentity.into())
    }

    /// The full name of the ref ledger commits advance.
    ///
    /// In a repository with no commits yet the checked-out branch is used
    /// when the configured ref does not exist, so a fresh `git init` works.
    ///
    /// # Errors
    ///
    /// [`LedgerError::RefMissing`], [`LedgerError::Detached`] or a git error.
    pub fn ledger_ref(&self) -> Result<String> {
        match self.cfg.mode {
            RefMode::Branch => {
                let branch = self.repo.current_branch()?.ok_or(LedgerError::Detached)?;
                Ok(format!("refs/heads/{branch}"))
            }
            RefMode::Trunk => {
                let name = full_ref(&self.cfg.ref_name);
                if self.repo.rev_parse(&name).is_ok() {
                    return Ok(name);
                }
                let head = self.repo.head()?;
                match (head.oid, head.branch) {
                    (None, Some(branch)) => {
                        tracing::info!(configured = %name, using = %branch, "ledger ref missing in an empty repository; using the checked-out branch");
                        Ok(format!("refs/heads/{branch}"))
                    }
                    _ => Err(LedgerError::RefMissing { ref_name: name }),
                }
            }
        }
    }

    pub(crate) fn tip_of(&self, ref_name: &str) -> Result<Option<Oid>> {
        match self.repo.rev_parse(ref_name) {
            Ok(oid) => Ok(Some(oid)),
            Err(e) if is_rev_error(&e) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// The tree of the tickets directory at `tip`, if it exists.
    pub(crate) fn tickets_tree(&self, tip: Option<Oid>) -> Result<Option<Oid>> {
        let Some(tip) = tip else { return Ok(None) };
        match self.repo.rev_parse(&format!("{tip}:{}", self.cfg.dir)) {
            Ok(oid) => Ok(Some(oid)),
            Err(e) if is_rev_error(&e) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    fn key_of(&self, tree: Option<Oid>) -> String {
        format!(
            "{}|{}",
            tree.map_or_else(|| "empty".to_owned(), |t| t.to_string()),
            self.cfg.handle_min_len
        )
    }

    /// Paths below the tree named by `spec` (`<oid>`, `<oid>:<path>`), relative to it.
    pub(crate) fn list_files(&self, spec: &str) -> Result<Vec<String>> {
        let empty: Oid = EMPTY_TREE
            .parse()
            .unwrap_or_else(|e| unreachable!("constant is a valid object id: {e}"));
        match self
            .repo
            .diff_names(&TreeRef::Oid(empty), &TreeRef::Ref(spec.to_owned()))
        {
            Ok(paths) => Ok(paths.into_iter().map(|p| p.path).collect()),
            Err(e) if is_rev_error(&e) => Ok(Vec::new()),
            Err(e) => Err(e.into()),
        }
    }

    fn blob(&self, rev: &str, path: &str) -> Result<Option<Vec<u8>>> {
        Ok(self.repo.read_blob_at(rev, path)?)
    }

    pub(crate) fn text(&self, rev: &str, path: &str) -> Result<Option<String>> {
        self.blob(rev, path)?
            .map(|b| {
                String::from_utf8(b).map_err(|_| LedgerError::malformed(path, "not valid UTF-8"))
            })
            .transpose()
    }

    /// Read ticket `id` at commit `tip` (the document, not the fold).
    ///
    /// # Errors
    ///
    /// Git read failures or a malformed document.
    pub fn read_ticket_at(&self, tip: &str, id: TicketId) -> Result<Option<Ticket>> {
        let path = format!("{}/{id}/ticket.md", self.cfg.dir);
        self.text(tip, &path)?
            .map(|t| doc::parse(&path, &t))
            .transpose()
    }

    /// Read every event of ticket `id` at commit `tip`, in fold order.
    ///
    /// # Errors
    ///
    /// Git read failures or a malformed event file.
    pub fn read_events_at(&self, tip: &str, id: TicketId) -> Result<Vec<Event>> {
        let dir = format!("{}/{id}/events", self.cfg.dir);
        let mut events = Vec::new();
        for name in self.list_files(&format!("{tip}:{dir}"))? {
            let Some(stem) = name.strip_suffix(".toml") else {
                continue;
            };
            let Ok(eid) = stem.parse::<EventId>() else {
                tracing::warn!(ticket = %id, file = %name, "ignoring non-ULID file in events/");
                continue;
            };
            let path = format!("{dir}/{name}");
            let text = self
                .text(tip, &path)?
                .ok_or_else(|| LedgerError::malformed(&path, "listed but unreadable"))?;
            events.push(Event::parse(eid, &text)?);
        }
        crate::event::sort_events(&mut events);
        Ok(events)
    }

    /// Ids of every ticket directory at commit `tip`.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn ticket_ids_at(&self, tip: &str) -> Result<Vec<TicketId>> {
        let mut ids: Vec<TicketId> = self
            .list_files(&format!("{tip}:{}", self.cfg.dir))?
            .iter()
            .filter_map(|p| p.strip_suffix("/ticket.md"))
            .filter_map(|p| p.parse().ok())
            .collect();
        ids.sort();
        Ok(ids)
    }

    /// Whether `tickets/<id>/ticket.md` exists on `rev` (a ref or commit).
    ///
    /// # Errors
    ///
    /// Git failures other than an unresolvable `rev` (which reads as absent).
    pub fn ticket_exists_at(&self, rev: &str, id: &str) -> Result<bool> {
        let path = format!("{}/{id}/ticket.md", self.cfg.dir);
        match self.repo.read_blob_at(rev, &path) {
            Ok(b) => Ok(b.is_some()),
            Err(e) if is_rev_error(&e) => Ok(false),
            Err(e) => Err(e.into()),
        }
    }

    /// Open the index and bring it up to date with the ledger ref.
    pub(crate) fn synced(&self) -> Result<Synced> {
        let ref_name = self.ledger_ref()?;
        let tip = self.tip_of(&ref_name)?;
        let tree = self.tickets_tree(tip)?;
        let key = self.key_of(tree);
        let mut index = Index::open(&self.index_path)?;
        if index.key()?.as_deref() != Some(key.as_str()) {
            let tickets = match tree {
                Some(t) => self.read_all_tickets(&t.to_string())?,
                None => Vec::new(),
            };
            index.rebuild(&key, &tickets, self.cfg.handle_min_len)?;
        }
        Ok(Synced {
            index,
            ref_name,
            tip,
            tree,
            key,
        })
    }

    fn read_all_tickets(&self, tree: &str) -> Result<Vec<Ticket>> {
        let mut out = Vec::new();
        for path in self.list_files(tree)? {
            let Some(id) = path.strip_suffix("/ticket.md") else {
                continue;
            };
            if id.parse::<TicketId>().is_err() {
                continue;
            }
            let Some(text) = self.text(tree, &path)? else {
                continue;
            };
            match doc::parse(&path, &text) {
                Ok(t) => out.push(t),
                Err(e) => tracing::warn!(error = %e, "skipping unreadable ticket while indexing"),
            }
        }
        out.sort_by_key(|t| t.front.id);
        Ok(out)
    }

    /// Handle (with `~`) of `id` among the indexed tickets plus `id` itself.
    pub(crate) fn handle_among(&self, index: &Index, id: TicketId) -> Result<String> {
        let mut ids = index.all_ids()?;
        if !ids.contains(&id) {
            ids.push(id);
        }
        let handles = compute_handles(&ids, self.cfg.handle_min_len);
        let pos = ids.iter().position(|i| *i == id).unwrap_or(0);
        Ok(display_handle(&handles[pos]))
    }

    /// Append `new` events to ticket `id` and commit the result on the ledger ref.
    ///
    /// The frontmatter is re-folded from every event (existing plus new), so
    /// the commit always satisfies `fold == frontmatter`.
    pub(crate) fn commit_events(&self, verb: &str, id: TicketId, new: &[Event]) -> Result<Applied> {
        let Synced {
            mut index,
            ref_name,
            tip,
            tree,
            key,
        } = self.synced()?;
        let creating = new
            .iter()
            .any(|e| matches!(e.body, crate::event::EventBody::Create(_)));
        let existing = match (creating, tip) {
            (false, Some(t)) => self.read_events_at(&t.to_string(), id)?,
            _ => Vec::new(),
        };
        let mut all = existing;
        all.extend(new.iter().cloned());
        let folded = fold(id, &all)?;
        let ticket = folded.ticket;
        let dir = &self.cfg.dir;
        let mut changes = vec![(
            RelPath::new(format!("{dir}/{id}/ticket.md"))?,
            Some(doc::render(&ticket)?.into_bytes()),
        )];
        for ev in new {
            tracing::debug!(ticket = %id, event = %ev.id, kind = %ev.kind, "event written");
            changes.push((
                RelPath::new(format!("{dir}/{id}/events/{}", ev.file_name()))?,
                Some(ev.to_toml()?.into_bytes()),
            ));
        }
        let handle = self.handle_among(&index, id)?;
        let message = format!("tickets({verb}): {handle} {}", ticket.front.title);
        let opts = CommitOptions {
            cas_retries: self.cfg.cas_retries,
            author: None,
        };
        let out = self
            .repo
            .commit_paths(&ref_name, &changes, &message, &opts)?;
        tracing::info!(verb, ticket = %id, commit = %out.oid, events = new.len(), retries = out.retries, "ledger commit");
        self.after_commit(&mut index, tree, &key, &ref_name, out.oid, id, new, &ticket)?;
        Ok(Applied {
            ticket,
            handle,
            events: new.iter().map(|e| e.id).collect(),
            already: false,
            commit: Some(out.oid),
        })
    }

    /// Update the index after our commit, or repair a concurrent writer's frontmatter overwrite.
    #[allow(
        clippy::too_many_arguments,
        reason = "one call site; a struct would only rename the arguments"
    )]
    fn after_commit(
        &self,
        index: &mut Index,
        old_tree: Option<Oid>,
        old_key: &str,
        ref_name: &str,
        commit: Oid,
        id: TicketId,
        ours: &[Event],
        ticket: &Ticket,
    ) -> Result<()> {
        let new_tree = self.tickets_tree(Some(commit))?;
        let new_key = self.key_of(new_tree);
        let mut expected: Vec<String> = vec![format!("{id}/ticket.md")];
        expected.extend(
            ours.iter()
                .map(|e| format!("{id}/events/{}", e.file_name())),
        );
        expected.sort();
        let empty: Oid = EMPTY_TREE
            .parse()
            .unwrap_or_else(|e| unreachable!("constant is a valid object id: {e}"));
        let from = old_tree.map_or(TreeRef::Oid(empty), TreeRef::Oid);
        let to = new_tree.map_or(TreeRef::Oid(empty), TreeRef::Oid);
        let mut changed: Vec<String> = self
            .repo
            .diff_names(&from, &to)?
            .into_iter()
            .map(|c| c.path)
            .collect();
        changed.sort();
        if changed == expected {
            // The ref moved by exactly our change: update the index in place.
            index.apply(
                old_key,
                &new_key,
                std::slice::from_ref(ticket),
                self.cfg.handle_min_len,
            )?;
            return Ok(());
        }
        let foreign_event = changed
            .iter()
            .any(|p| p.starts_with(&format!("{id}/events/")) && !expected.contains(p));
        tracing::debug!(ticket = %id, foreign_event, changed = changed.len(), "ledger moved concurrently");
        if foreign_event {
            tracing::warn!(ticket = %id, "concurrent writer added events to this ticket; reconciling frontmatter");
            self.reconcile_with(ref_name, id, MAX_RECONCILE)?;
        }
        // The index is stale either way; the next read rebuilds it.
        Ok(())
    }

    /// Rewrite `ticket.md` of `id` from the fold of its events, if they differ.
    ///
    /// Returns the commit made, or `None` when the frontmatter already equals the fold.
    ///
    /// # Errors
    ///
    /// Git, parse or fold failures.
    pub fn reconcile(&self, id: TicketId) -> Result<Option<Oid>> {
        let ref_name = self.ledger_ref()?;
        self.reconcile_with(&ref_name, id, MAX_RECONCILE)
    }

    fn reconcile_with(&self, ref_name: &str, id: TicketId, attempts: u32) -> Result<Option<Oid>> {
        for _ in 0..attempts {
            let Some(tip) = self.tip_of(ref_name)? else {
                return Ok(None);
            };
            let hex = tip.to_string();
            let events = self.read_events_at(&hex, id)?;
            let folded = fold(id, &events)?;
            let stored = self.read_ticket_at(&hex, id)?;
            if stored.as_ref() == Some(&folded.ticket) {
                return Ok(None);
            }
            let path = RelPath::new(format!("{}/{id}/ticket.md", self.cfg.dir))?;
            let message = format!(
                "tickets(reconcile): ~{} re-fold frontmatter",
                &id.random_part()[..7]
            );
            let opts = CommitOptions {
                cas_retries: self.cfg.cas_retries,
                author: None,
            };
            let out = self.repo.commit_paths(
                ref_name,
                &[(path, Some(doc::render(&folded.ticket)?.into_bytes()))],
                &message,
                &opts,
            )?;
            tracing::info!(ticket = %id, commit = %out.oid, "frontmatter reconciled");
            // Loop to confirm no further concurrent event landed meanwhile.
            if self.tip_of(ref_name)? == Some(out.oid) {
                return Ok(Some(out.oid));
            }
        }
        Ok(None)
    }
}
