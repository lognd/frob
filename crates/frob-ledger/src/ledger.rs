//! The [`Ledger`]: git access to the ledger ref, the synced index and the commit path.
//!
//! Reads come from the ledger ref's tree (never the worktree), writes go
//! through [`gob_git::Repo::commit_paths`] on that ref, so staged changes of a
//! user can never enter a ledger commit (decision D23).

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use gob_git::{ChangeKind, CommitOptions, Oid, RelPath, Repo, TreeRef};

use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::Event;
use crate::fold::fold;
use crate::id::{EventId, TicketId, compute_handles, display_handle};
use crate::index::Index;
use crate::layout::{self, Layout};
use crate::model::Ticket;
use crate::redact::{RedactError, RuleSet};

const EMPTY_TREE: &str = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";
pub(crate) const MAX_RECONCILE: u32 = 3;

/// Where ledger commits go.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RefMode {
    /// The configured ref (default the trunk branch), whatever is checked out.
    #[default]
    Trunk,
    /// The currently checked-out branch, for protected-trunk and fork flows.
    Branch,
    /// The orphan ticket branch `[tickets] branch` in the ticket-branch layout; `ref` stays the code base branch.
    Orphan,
}

impl std::str::FromStr for RefMode {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s {
            "trunk" => Ok(Self::Trunk),
            "branch" => Ok(Self::Branch),
            "orphan" => Ok(Self::Orphan),
            other => Err(format!(
                "`{other}` is not a ref mode; expected trunk, branch or orphan"
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
    /// Name of the orphan ticket branch (`[tickets] branch`), the ledger ref when `mode` is [`RefMode::Orphan`].
    pub branch: String,
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
            branch: "frob-tickets".to_owned(),
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
    /// Local private-term rules, loaded on first use; a load failure is kept so writes fail closed.
    redact: std::sync::OnceLock<std::result::Result<RuleSet, RedactError>>,
    /// The command's clock: every event and date this ledger stamps comes from it.
    clock: std::sync::Arc<dyn gob_time::Clock>,
    /// Where tickets and events live in the ledger tree.
    layout: Layout,
    /// Ticket-branch scan of the last commit read, so id lookups cost one tree walk per commit.
    branch_scan: std::sync::Mutex<Option<(String, std::sync::Arc<BranchScan>)>>,
    /// Full index rebuilds this handle has performed (the incremental path does not count).
    rebuilds: std::sync::atomic::AtomicUsize,
    /// Git reads that resolve a revision (tree walks and path reads) this handle has made.
    // frob:ticket 01M4DPJG0W39SCKZE5N807V4XM
    git_reads: std::sync::atomic::AtomicUsize,
}

/// What one walk of a ticket-branch commit found: where each ticket file is, by frontmatter ULID.
#[derive(Debug, Default)]
pub(crate) struct BranchScan {
    /// Ticket file path by the ULID its frontmatter names (never by path).
    pub files: std::collections::BTreeMap<TicketId, String>,
    /// Tickets that have an `.events/<ULID>/` directory.
    pub with_events: std::collections::BTreeSet<TicketId>,
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
    /// Notes the caller must surface, e.g. checkouts the commit could not sync.
    pub warnings: Vec<String>,
}

/// One envelope warning per checkout the ledger commit could not sync, naming its paths and the remedy.
pub(crate) fn unsynced_warnings(unsynced: &[gob_git::UnsyncedCheckout]) -> Vec<String> {
    unsynced
        .iter()
        .map(|u| {
            let paths = u.paths_with_local_edits.join(", ");
            tracing::warn!(checkout = %u.path.display(), %paths, "checkout left stale by ledger commit");
            format!(
                "checkout {dir} was not synced to the ledger commit: local edits to {paths}; \
                 run `git -C {dir} diff -- {paths}`, then commit it or `git restore --source=HEAD --staged --worktree -- {paths}`",
                dir = u.path.display(),
            )
        })
        .collect()
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
    /// Open the ledger of `repo` under `cfg`, stamping every event from `clock`.
    pub fn open(repo: Repo, cfg: LedgerConfig, clock: std::sync::Arc<dyn gob_time::Clock>) -> Self {
        let index_path = repo.work_dir().map_or_else(
            || repo.git_dir().join("frob").join("tickets.sqlite"),
            |w| w.join(".frob").join("tickets.sqlite"),
        );
        let layout = if cfg.mode == RefMode::Orphan {
            Layout::Branch
        } else {
            Layout::Dir
        };
        tracing::debug!(index = %index_path.display(), ref_name = %cfg.ref_name, mode = ?cfg.mode, ?layout, "ledger opened");
        Self {
            repo,
            cfg,
            index_path,
            redact: std::sync::OnceLock::new(),
            clock,
            layout,
            branch_scan: std::sync::Mutex::new(None),
            rebuilds: std::sync::atomic::AtomicUsize::new(0),
            git_reads: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Read and write the ledger in `layout` (the ticket-branch layout needs a ref holding that branch).
    #[must_use]
    pub fn with_layout(self, layout: Layout) -> Self {
        tracing::debug!(?layout, "ledger layout selected");
        Self { layout, ..self }
    }

    /// The layout this ledger reads and writes.
    pub fn layout(&self) -> Layout {
        self.layout
    }

    /// Refuse `verb` on the ticket-branch layout, which it does not write yet.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] naming the verb when the layout is [`Layout::Branch`].
    pub(crate) fn require_dir_layout(&self, verb: &str) -> Result<()> {
        if self.layout == Layout::Branch {
            tracing::warn!(
                verb,
                "verb refused: not implemented for the ticket-branch layout"
            );
            return Err(LedgerError::invalid(format!(
                "`{verb}` does not support the ticket-branch layout yet (ref_mode = \"orphan\")"
            )));
        }
        Ok(())
    }

    /// Prefix that turns a path relative to the ledger tree into a repository path.
    pub fn tree_prefix(&self) -> String {
        match self.layout {
            Layout::Dir => format!("{}/", self.cfg.dir),
            Layout::Branch => String::new(),
        }
    }

    /// The clock this ledger stamps with; the one a command reads its dates from.
    pub fn clock(&self) -> &std::sync::Arc<dyn gob_time::Clock> {
        &self.clock
    }

    /// The current instant of the ledger's clock.
    pub(crate) fn now(&self) -> gob_time::Stamp {
        self.clock.now()
    }

    /// Replace the local private-term rules (tests and callers that load rules themselves).
    #[must_use]
    pub fn with_redaction(self, rules: RuleSet) -> Self {
        let cell = std::sync::OnceLock::new();
        let _ = cell.set(Ok(rules));
        Self {
            redact: cell,
            ..self
        }
    }

    /// The local private-term rules (user file plus git-common-dir file), loaded once.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] when a local privacy file is unreadable or malformed: writes refuse
    /// rather than run unprotected.
    pub fn redaction(&self) -> Result<&RuleSet> {
        self.redact
            .get_or_init(|| RuleSet::load_local(self.repo.common_dir()))
            .as_ref()
            .map_err(|e| LedgerError::invalid(e.to_string()))
    }

    /// Refuse `text` that matches a private-term rule, naming the rule label and a pattern hash, never the term.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Redacted`], or [`LedgerError::Invalid`] when the local rules cannot be loaded.
    pub fn refuse_private(&self, text: &str) -> Result<()> {
        let rules = self.redaction()?;
        if let Some(hit) = rules.first_private_hit(text) {
            tracing::warn!(rule = %hit, "write refused: text matches a private-term rule");
            return Err(LedgerError::Redacted {
                label: hit.label,
                hash: hit.hash,
            });
        }
        Ok(())
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
            RefMode::Orphan => {
                let name = full_ref(&self.cfg.branch);
                if self.repo.rev_parse(&name).is_ok() {
                    return Ok(name);
                }
                Err(LedgerError::RefMissing { ref_name: name })
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
        let spec = match self.layout {
            Layout::Dir => format!("{tip}:{}", self.cfg.dir),
            Layout::Branch => format!("{tip}^{{tree}}"),
        };
        match self.repo.rev_parse(&spec) {
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

    /// Blobs below the tree named by `spec` (`<oid>`, `<oid>:<path>`) as `(path relative to it, blob id)`, from one tree walk.
    pub(crate) fn list_blobs(&self, spec: &str) -> Result<Vec<(String, Oid)>> {
        self.count_git_read();
        match self.repo.blobs_at(spec) {
            Ok(blobs) => Ok(blobs),
            Err(e) if is_rev_error(&e) => Ok(Vec::new()),
            Err(e) => Err(e.into()),
        }
    }

    /// Paths below the tree named by `spec` (`<oid>`, `<oid>:<path>`), relative to it.
    pub(crate) fn list_files(&self, spec: &str) -> Result<Vec<String>> {
        Ok(self
            .list_blobs(spec)?
            .into_iter()
            .map(|(path, _)| path)
            .collect())
    }

    /// UTF-8 text of the blob `oid`, which was listed as `path` (named in the error only).
    pub(crate) fn text_of(&self, path: &str, oid: &Oid) -> Result<String> {
        String::from_utf8(self.repo.read_blob(oid)?)
            .map_err(|_| LedgerError::malformed(path, "not valid UTF-8"))
    }

    fn blob(&self, rev: &str, path: &str) -> Result<Option<Vec<u8>>> {
        self.count_git_read();
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
        let Some(path) = self.ticket_file_at(tip, id, None)? else {
            return Ok(None);
        };
        self.text(tip, &path)?
            .map(|t| doc::parse(&path, &t))
            .transpose()
    }

    /// Repository path of the file of ticket `id` at `tip`, if it exists there.
    ///
    /// The legacy layout derives it from the id. The ticket-branch layout never trusts a path
    /// as identity: it tries `hint` (the computed path) and falls back to the ULID in each
    /// candidate file's frontmatter.
    fn ticket_file_at(
        &self,
        tip: &str,
        id: TicketId,
        hint: Option<&str>,
    ) -> Result<Option<String>> {
        if self.layout == Layout::Dir {
            return Ok(Some(format!("{}/{id}/ticket.md", self.cfg.dir)));
        }
        if let Some(h) = hint
            && self
                .text(tip, h)?
                .is_some_and(|t| layout::peek_ticket_id(&t) == Some(id))
        {
            return Ok(Some(h.to_owned()));
        }
        let path = self.branch_scan_at(tip)?.files.get(&id).cloned();
        if let Some(p) = &path {
            tracing::debug!(ticket = %id, path = %p, "ticket file located by frontmatter id");
        }
        Ok(path)
    }

    /// Walk the ticket-branch commit `tip` once: every ticket file by its frontmatter ULID and every
    /// `.events/<ULID>/` directory (cached for the last full-hash commit, which cannot change).
    pub(crate) fn branch_scan_at(&self, tip: &str) -> Result<std::sync::Arc<BranchScan>> {
        let cacheable = tip.len() == 40 && tip.bytes().all(|b| b.is_ascii_hexdigit());
        if cacheable
            && let Ok(guard) = self.branch_scan.lock()
            && let Some((at, scan)) = guard.as_ref()
            && at == tip
        {
            return Ok(scan.clone());
        }
        let mut scan = BranchScan::default();
        for (path, oid) in self.list_blobs(tip)? {
            if let Some(rest) = path.strip_prefix(&format!("{}/", layout::EVENTS_DIR)) {
                if let Some(id) = rest.split('/').next().and_then(|s| s.parse().ok()) {
                    scan.with_events.insert(id);
                }
                continue;
            }
            if !layout::is_branch_ticket_candidate(&path) {
                continue;
            }
            let text = self.text_of(&path, &oid)?;
            let Some(id) = doc::parse(&path, &text)
                .ok()
                .map(|t| t.front.id)
                .or_else(|| layout::peek_ticket_id(&text))
            else {
                tracing::debug!(%path, "markdown file without a ticket id ignored");
                continue;
            };
            if let Some(other) = scan.files.insert(id, path.clone()) {
                tracing::warn!(ticket = %id, first = %other, second = %path, "two files claim one ticket id");
            }
        }
        let scan = std::sync::Arc::new(scan);
        if cacheable && let Ok(mut guard) = self.branch_scan.lock() {
            *guard = Some((tip.to_owned(), scan.clone()));
        }
        Ok(scan)
    }

    /// Path of the file and of the events directory a write for `ticket` touches.
    ///
    /// A new ticket on the ticket branch goes to its computed path (`-<handle>` appended when
    /// another ticket already holds it); an existing one is rewritten where it is, because
    /// files move only in reindex commits (`navigation.md` 2.2).
    fn write_paths(
        &self,
        index: &Index,
        tip: Option<Oid>,
        ticket: &Ticket,
        creating: bool,
    ) -> Result<(String, String)> {
        let id = ticket.front.id;
        if self.layout == Layout::Dir {
            let dir = &self.cfg.dir;
            return Ok((
                format!("{dir}/{id}/ticket.md"),
                format!("{dir}/{id}/events"),
            ));
        }
        let events_dir = layout::branch_events_dir(id);
        let tip_hex = tip.map(|t| t.to_string());
        let short = id.random_part()[..7].to_owned();
        let top = Self::top_epic_slug(index, ticket.front.parent)?;
        let slug = layout::title_slug(&ticket.front.title, &short);
        let mut path = layout::branch_ticket_path(ticket.front.ty, &slug, top.as_deref());
        if let Some(hex) = &tip_hex {
            if !creating && let Some(at) = self.ticket_file_at(hex, id, Some(&path))? {
                return Ok((at, events_dir));
            }
            if self.text(hex, &path)?.is_some() {
                tracing::warn!(ticket = %id, %path, "slug taken in this directory; appending the handle");
                path = layout::branch_ticket_path(
                    ticket.front.ty,
                    &format!("{slug}-{short}"),
                    top.as_deref(),
                );
            }
        }
        Ok((path, events_dir))
    }

    /// Directory slug of the outermost epic among the ancestors starting at `parent`.
    fn top_epic_slug(index: &Index, parent: Option<TicketId>) -> Result<Option<String>> {
        let mut top: Option<Ticket> = None;
        let mut cur = parent;
        for _ in 0..64 {
            let Some(id) = cur else { break };
            let Some(t) = index.get(id)? else { break };
            cur = t.front.parent;
            if t.front.ty == crate::model::TicketType::Epic {
                top = Some(t);
            }
        }
        Ok(top.map(|t| {
            let short = t.front.id.random_part()[..7].to_owned();
            layout::title_slug(&t.front.title, &short)
        }))
    }

    /// Read every event of ticket `id` at commit `tip`, in fold order.
    ///
    /// # Errors
    ///
    /// Git read failures or a malformed event file.
    pub fn read_events_at(&self, tip: &str, id: TicketId) -> Result<Vec<Event>> {
        let dir = match self.layout {
            Layout::Dir => format!("{}/{id}/events", self.cfg.dir),
            Layout::Branch => layout::branch_events_dir(id),
        };
        let mut events = Vec::new();
        for (name, oid) in self.list_blobs(&format!("{tip}:{dir}"))? {
            let Some(stem) = name.strip_suffix(".toml") else {
                continue;
            };
            let Ok(eid) = stem.parse::<EventId>() else {
                tracing::warn!(ticket = %id, file = %name, "ignoring non-ULID file in events/");
                continue;
            };
            let text = self.text_of(&format!("{dir}/{name}"), &oid)?;
            events.push(Event::parse(eid, &text)?);
        }
        crate::event::sort_events(&mut events);
        Ok(events)
    }

    /// Read the events of every ticket in `ids` at commit `tip` with one walk of the tree.
    ///
    /// Tickets without event files map to an empty list; events are in fold order.
    ///
    /// # Errors
    ///
    /// Git read failures or a malformed event file.
    // frob:ticket 01M4BH8WMBDTAT4R0ST9VT321D
    pub fn read_events_many_at(
        &self,
        tip: &str,
        ids: &BTreeSet<TicketId>,
    ) -> Result<BTreeMap<TicketId, Vec<Event>>> {
        let spec = match self.layout {
            Layout::Dir => format!("{tip}:{}", self.cfg.dir),
            Layout::Branch => format!("{tip}^{{tree}}"),
        };
        let mut out: BTreeMap<TicketId, Vec<Event>> =
            ids.iter().map(|id| (*id, Vec::new())).collect();
        // Blobs are read by id from the one walk, so no per-file path or revision lookup happens.
        let mut files = 0_usize;
        for (path, oid) in self.list_blobs(&spec)? {
            let Some((id, name)) = self.event_path_parts(&path) else {
                continue;
            };
            let Some(events) = out.get_mut(&id) else {
                continue;
            };
            let Some(stem) = name.strip_suffix(".toml") else {
                continue;
            };
            let Ok(eid) = stem.parse::<EventId>() else {
                tracing::warn!(ticket = %id, file = %name, "ignoring non-ULID file in events/");
                continue;
            };
            let text = self.text_of(&path, &oid)?;
            events.push(Event::parse(eid, &text)?);
            files += 1;
        }
        for events in out.values_mut() {
            crate::event::sort_events(events);
        }
        tracing::debug!(tickets = ids.len(), files, "events walked once");
        Ok(out)
    }

    /// Read the ticket document of every ticket in `ids` at commit `tip` with one walk of the tree.
    ///
    /// A ticket without a file maps to `None`; a document that does not parse maps to its error,
    /// so one bad card does not hide the rest.
    ///
    /// # Errors
    ///
    /// Git read failures of the walk itself.
    // frob:ticket 01M4DPJG0W39SCKZE5N807V4XM
    pub fn read_tickets_many_at(
        &self,
        tip: &str,
        ids: &[TicketId],
    ) -> Result<BTreeMap<TicketId, Result<Option<Ticket>>>> {
        let (spec, mut wanted): (String, BTreeMap<String, TicketId>) = match self.layout {
            Layout::Dir => (
                format!("{tip}:{}", self.cfg.dir),
                ids.iter()
                    .map(|id| (format!("{id}/ticket.md"), *id))
                    .collect(),
            ),
            Layout::Branch => {
                let scan = self.branch_scan_at(tip)?;
                (
                    format!("{tip}^{{tree}}"),
                    ids.iter()
                        .filter_map(|id| scan.files.get(id).map(|p| (p.clone(), *id)))
                        .collect(),
                )
            }
        };
        let mut out: BTreeMap<TicketId, Result<Option<Ticket>>> =
            ids.iter().map(|id| (*id, Ok(None))).collect();
        for (path, oid) in self.list_blobs(&spec)? {
            let Some(id) = wanted.remove(&path) else {
                continue;
            };
            let parsed = self
                .text_of(&path, &oid)
                .and_then(|t| doc::parse(&path, &t))
                .map(Some);
            out.insert(id, parsed);
        }
        tracing::debug!(tickets = ids.len(), "ticket documents walked once");
        Ok(out)
    }

    /// Split a path listed under the ticket root into (ticket, event file name), if it is an event file.
    fn event_path_parts<'a>(&self, path: &'a str) -> Option<(TicketId, &'a str)> {
        let mut parts = path.split('/');
        match self.layout {
            Layout::Dir => {
                let id = parts.next()?.parse().ok()?;
                (parts.next()? == "events").then_some(())?;
                let name = parts.next()?;
                parts.next().is_none().then_some((id, name))
            }
            Layout::Branch => {
                (parts.next()? == layout::EVENTS_DIR).then_some(())?;
                let id = parts.next()?.parse().ok()?;
                let name = parts.next()?;
                parts.next().is_none().then_some((id, name))
            }
        }
    }

    /// Ids of every ticket at commit `tip`: ticket directories in the legacy layout, ticket files
    /// named by their frontmatter ULID (wherever they sit) on the ticket branch.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn ticket_ids_at(&self, tip: &str) -> Result<Vec<TicketId>> {
        if self.layout == Layout::Branch {
            // BTreeMap keys are already sorted ULIDs.
            return Ok(self.branch_scan_at(tip)?.files.keys().copied().collect());
        }
        let mut ids: Vec<TicketId> = self
            .list_files(&format!("{tip}:{}", self.cfg.dir))?
            .iter()
            .filter_map(|p| p.strip_suffix("/ticket.md"))
            .filter_map(|p| p.parse().ok())
            .collect();
        ids.sort();
        Ok(ids)
    }

    /// Whether the file of ticket `id` exists on `rev` (a ref or commit), found by id in either layout.
    ///
    /// # Errors
    ///
    /// Git failures other than an unresolvable `rev` (which reads as absent).
    pub fn ticket_exists_at(&self, rev: &str, id: &str) -> Result<bool> {
        if self.layout == Layout::Branch {
            let Ok(id) = id.parse::<TicketId>() else {
                return Ok(false);
            };
            let tip = match self.repo.rev_parse(rev) {
                Ok(oid) => oid.to_string(),
                Err(e) if is_rev_error(&e) => return Ok(false),
                Err(e) => return Err(e.into()),
            };
            return Ok(self.ticket_file_at(&tip, id, None)?.is_some());
        }
        let path = format!("{}/{id}/ticket.md", self.cfg.dir);
        match self.repo.read_blob_at(rev, &path) {
            Ok(b) => Ok(b.is_some()),
            Err(e) if is_rev_error(&e) => Ok(false),
            Err(e) => Err(e.into()),
        }
    }

    /// Open the index and bring it up to date with the ledger ref.
    ///
    /// A stale key is first repaired incrementally from the tree diff between the tree the index
    /// reflects and the current one; only an unusable key falls back to a full rebuild.
    pub(crate) fn synced(&self) -> Result<Synced> {
        let ref_name = self.ledger_ref()?;
        let tip = self.tip_of(&ref_name)?;
        let tree = self.tickets_tree(tip)?;
        let key = self.key_of(tree);
        let mut index = Index::open(&self.index_path)?;
        let stored = index.key()?;
        if stored.as_deref() != Some(key.as_str())
            && !self.sync_incrementally(&mut index, stored.as_deref(), tree, &key)?
        {
            let tickets = match tree {
                Some(t) => self.read_all_tickets(&t.to_string())?,
                None => Vec::new(),
            };
            self.rebuilds
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
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

    /// Count one git read that resolves a revision.
    fn count_git_read(&self) {
        self.git_reads
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }

    /// How many revision-resolving git reads (tree walks, path reads) this handle has made (tests and diagnostics).
    pub fn git_reads(&self) -> usize {
        self.git_reads.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// How many full index rebuilds this handle has done (tests and diagnostics).
    pub fn index_rebuilds(&self) -> usize {
        self.rebuilds.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// The tree id and handle length a stored index key names, or `None` when it is not one of ours.
    fn parse_key(stored: &str) -> Option<(Oid, usize)> {
        let (tree, min_len) = stored.split_once('|')?;
        let tree = if tree == "empty" { EMPTY_TREE } else { tree };
        Some((tree.parse().ok()?, min_len.parse().ok()?))
    }

    /// Whether `path` (relative to the tickets tree) is a file the index reads as a ticket.
    fn is_ticket_path(&self, path: &str) -> bool {
        match self.layout {
            Layout::Dir => path
                .strip_suffix("/ticket.md")
                .is_some_and(|id| id.parse::<TicketId>().is_ok()),
            Layout::Branch => layout::is_branch_ticket_candidate(path),
        }
    }

    /// Bring `index` from the tree its key names to `tree` by upserting and deleting only the
    /// tickets whose files changed; `false` means the caller must rebuild in full.
    ///
    /// The result equals a full rebuild: a changed file first drops the ticket its old blob
    /// indexed, then the new blob (if it parses) is upserted, and a file that would make two
    /// files claim one id is refused so the rebuild decides.
    fn sync_incrementally(
        &self,
        index: &mut Index,
        stored: Option<&str>,
        tree: Option<Oid>,
        key: &str,
    ) -> Result<bool> {
        let Some(stored) = stored else {
            return Ok(false);
        };
        let Some((old, min_len)) = Self::parse_key(stored) else {
            tracing::debug!(stored, "index key unreadable; full rebuild");
            return Ok(false);
        };
        if min_len != self.cfg.handle_min_len {
            tracing::debug!(min_len, "handle length changed; full rebuild");
            return Ok(false);
        }
        let empty: Oid = EMPTY_TREE
            .parse()
            .unwrap_or_else(|e| unreachable!("constant is a valid object id: {e}"));
        let new = tree.unwrap_or(empty);
        let changes = match self.repo.diff_names(&TreeRef::Oid(old), &TreeRef::Oid(new)) {
            Ok(c) => c,
            Err(e) => {
                tracing::info!(error = %e, "previous index tree unreadable; full rebuild");
                return Ok(false);
            }
        };
        let (old_hex, new_hex) = (old.to_string(), new.to_string());
        let mut removed: Vec<TicketId> = Vec::new();
        let mut upserts: Vec<Ticket> = Vec::new();
        for change in changes.iter().filter(|c| self.is_ticket_path(&c.path)) {
            if change.kind != ChangeKind::Added
                && let Some(text) = self.text(&old_hex, &change.path)?
                && let Ok(t) = doc::parse(&change.path, &text)
            {
                removed.push(t.front.id);
            }
            if change.kind != ChangeKind::Deleted
                && let Some(text) = self.text(&new_hex, &change.path)?
            {
                match doc::parse(&change.path, &text) {
                    Ok(t) => upserts.push(t),
                    Err(e) => {
                        tracing::warn!(error = %e, "skipping unreadable ticket while indexing");
                    }
                }
            }
        }
        let done = index.patch(stored, key, &removed, &upserts, self.cfg.handle_min_len)?;
        tracing::debug!(
            changed = changes.len(),
            removed = removed.len(),
            upserted = upserts.len(),
            done,
            "index synced by tree diff"
        );
        Ok(done)
    }

    fn read_all_tickets(&self, tree: &str) -> Result<Vec<Ticket>> {
        let mut out = Vec::new();
        for (path, oid) in self.list_blobs(tree)? {
            if !self.is_ticket_path(&path) {
                continue;
            }
            let text = self.text_of(&path, &oid)?;
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
        for ev in new {
            self.refuse_private(&ev.to_toml()?)?;
        }
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
        let (file, events_dir) = self.write_paths(&index, tip, &ticket, creating)?;
        let mut changes = vec![(
            RelPath::new(&file)?,
            Some(doc::render(&ticket)?.into_bytes()),
        )];
        for ev in new {
            tracing::debug!(ticket = %id, event = %ev.id, kind = %ev.kind, "event written");
            changes.push((
                RelPath::new(format!("{events_dir}/{}", ev.file_name()))?,
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
        // frob:ticket 01M42MGNZZ1BY6YCG49BDHEZAT
        let warnings = unsynced_warnings(&out.unsynced);
        self.after_commit(
            &mut index,
            tree,
            &key,
            &ref_name,
            out.oid,
            new,
            &ticket,
            (&file, &events_dir),
        )?;
        Ok(Applied {
            ticket,
            handle,
            events: new.iter().map(|e| e.id).collect(),
            already: false,
            commit: Some(out.oid),
            warnings,
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
        ours: &[Event],
        ticket: &Ticket,
        (file, events_dir): (&str, &str),
    ) -> Result<()> {
        let id = ticket.front.id;
        let prefix = self.tree_prefix();
        let rel = |p: &str| p.strip_prefix(&prefix).unwrap_or(p).to_owned();
        let new_tree = self.tickets_tree(Some(commit))?;
        let new_key = self.key_of(new_tree);
        let mut expected: Vec<String> = vec![rel(file)];
        expected.extend(
            ours.iter()
                .map(|e| rel(&format!("{events_dir}/{}", e.file_name()))),
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
            .any(|p| p.starts_with(&format!("{}/", rel(events_dir))) && !expected.contains(p));
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

    pub(crate) fn reconcile_with(
        &self,
        ref_name: &str,
        id: TicketId,
        attempts: u32,
    ) -> Result<Option<Oid>> {
        for _ in 0..attempts {
            let Some(tip) = self.tip_of(ref_name)? else {
                return Ok(None);
            };
            let hex = tip.to_string();
            let events = self.read_events_at(&hex, id)?;
            let folded = fold(id, &events)?;
            let stored = self.read_ticket_at(&hex, id).unwrap_or_else(|e| {
                tracing::warn!(ticket = %id, error = %e, "ticket.md unreadable; re-rendering it from the events");
                None
            });
            if stored.as_ref() == Some(&folded.ticket) {
                return Ok(None);
            }
            let Some(file) = self.ticket_file_at(&hex, id, None)? else {
                return Err(LedgerError::NotFound {
                    input: id.to_string(),
                });
            };
            let path = RelPath::new(file)?;
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
