//! The lease directory under the git common dir, guarded by one lock file.
//!
//! Layout: `<common_dir>/frob/leases/<ticket ulid>.toml` per lease and
//! `<common_dir>/frob/leases.lock`. Every operation that reads, decides and
//! writes (acquire, renew, release, steal, list with pruning) holds the lock
//! for its whole duration, so two callers can never both pass the overlap
//! check. The lock is an advisory `flock` on a file shared by all worktrees of
//! one clone; leases are single-clone by design (decision D26).

// frob:ticket 01M40Q3S4T9QTYX0Z1MPAZP9JM

use gob_path::Shown;
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions, TryLockError};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{Duration, Instant};

use frob_ledger::TicketId;
use frob_ledger::model::Stamp;
use globset::GlobSet;
use gob_git::Repo;
use gob_time::Clock;
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::LeaseConfig;
use crate::error::{LeaseError, SAME_TICKET};
use crate::model::{Holder, Lease, StealRecord, Waiter};
use crate::overlap::{Resolver, covers_foreign_fragments, glob_set, scopes_overlap};

/// How often a blocked caller retries the lock.
const LOCK_POLL: Duration = Duration::from_millis(5);

/// The result of [`LeaseStore::acquire`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Acquired {
    /// The lease now in force.
    pub lease: Lease,
    /// True when the same holder already held it with the same scope.
    pub already: bool,
}

/// The result of [`LeaseStore::steal`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Stolen {
    /// The lease after the takeover.
    pub lease: Lease,
    /// Who held it before, for the caller to log as an event.
    pub previous: Holder,
}

/// A file declared by two or more live leases.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Contended {
    /// Repository-relative path.
    pub file: String,
    /// The tickets whose leases declare it.
    pub tickets: Vec<TicketId>,
}

/// A lease file that cannot be read as a lease; it grants and blocks nothing.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CorruptLease {
    /// The unreadable file.
    pub path: PathBuf,
    /// What is wrong with it.
    pub message: String,
}

/// A queued waiter as reported: how long it has waited and which live leases block it (frob:ticket 01M41ZRNYEWRY4V2MXT3WMXBBJ).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct WaiterInfo {
    /// The queued ticket.
    pub ticket: TicketId,
    /// Who is waiting.
    pub holder: Holder,
    /// Whole seconds in the queue.
    pub age_secs: i64,
    /// Tickets whose live leases overlap the waiter's scope, plus earlier overlapping waiters.
    pub blockers: Vec<TicketId>,
}

/// Proof that the lease lock is held; unlocks on drop.
struct LockGuard(File);

impl Drop for LockGuard {
    fn drop(&mut self) {
        if let Err(e) = self.0.unlock() {
            tracing::warn!(error = %e, "lease lock release failed");
        }
    }
}

/// The lease store of one clone.
#[derive(Debug)]
pub struct LeaseStore {
    dir: PathBuf,
    waiters_dir: PathBuf,
    lock_path: PathBuf,
    cfg: LeaseConfig,
    holder_limit: u32,
    repo_limit: u32,
    expedite_max: u32,
    shared: GlobSet,
    resolver: Resolver,
    clock: Arc<dyn Clock>,
    agent: Option<String>,
}

impl LeaseStore {
    /// The store of `repo`: leases in its common dir, scopes resolved in its work tree, ages judged by `clock`.
    ///
    /// # Errors
    ///
    /// [`LeaseError::BadGlob`] when `[lease] shared_files` holds an invalid glob.
    pub fn open(repo: &Repo, cfg: LeaseConfig, clock: Arc<dyn Clock>) -> Result<Self, LeaseError> {
        let root = repo
            .work_dir()
            .unwrap_or_else(|| repo.common_dir())
            .to_path_buf();
        Self::open_at(repo.common_dir(), root, cfg, clock)
    }

    /// A store over an explicit common dir and work tree root.
    ///
    /// # Errors
    ///
    /// [`LeaseError::BadGlob`] when `[lease] shared_files` holds an invalid glob.
    pub fn open_at(
        common_dir: &Path,
        root: PathBuf,
        cfg: LeaseConfig,
        clock: Arc<dyn Clock>,
    ) -> Result<Self, LeaseError> {
        let base = common_dir.join("frob");
        // frob:ticket 01M4GPWWWZFCHYMKYNKB3S3XGJ
        let shared = glob_set(cfg.shared_files.iter().chain(&cfg.generated_files))?;
        tracing::debug!(dir = %Shown::of(&base), ttl_secs = cfg.ttl_secs, "lease store opened");
        Ok(Self {
            dir: base.join("leases"),
            waiters_dir: base.join("waiters"),
            lock_path: base.join("leases.lock"),
            cfg,
            holder_limit: 0,
            repo_limit: 0,
            expedite_max: 1,
            shared,
            resolver: Resolver::new(root),
            clock,
            agent: std::env::var(frob_ledger::claim_agent::AGENT_ENV)
                .ok()
                .filter(|a| !a.trim().is_empty()),
        })
    }

    /// The clock instant at the whole-second precision of lease files.
    fn now(&self) -> Stamp {
        self.clock.now().seconds()
    }

    /// Set the agent label stamped on newly taken claims (default: `FROB_AGENT` at open time).
    #[must_use]
    pub fn with_agent(mut self, agent: Option<String>) -> Self {
        self.agent = agent;
        self
    }

    /// Replace the clock (tests of TTL expiry).
    #[must_use]
    pub fn with_clock(mut self, clock: Arc<dyn Clock>) -> Self {
        self.clock = clock;
        self
    }

    /// Cap the live leases one holder may own (`[pm.wip] in_progress_per_identity`, the single per-holder knob); 0 turns it off.
    #[must_use]
    pub fn with_holder_limit(mut self, limit: u32) -> Self {
        tracing::debug!(limit, "per-holder lease limit set");
        self.holder_limit = limit;
        self
    }

    /// Record the repository-wide in-progress limit (`[pm.wip] in_progress`) next to the per-holder one; 0 is off. The store only carries it, `frob-worktree` enforces it because it needs the ledger.
    #[must_use]
    pub fn with_repo_limit(mut self, limit: u32) -> Self {
        tracing::debug!(limit, "repository in-progress limit set");
        self.repo_limit = limit;
        self
    }

    /// The repository-wide in-progress limit, 0 when off.
    pub fn repo_limit(&self) -> u32 {
        self.repo_limit
    }

    /// Record how many expedite tickets may be in progress at once (`[pm.classes] expedite_max`, default 1); like the repository limit the store only carries it and `frob-worktree` enforces it.
    #[must_use]
    pub fn with_expedite_max(mut self, max: u32) -> Self {
        tracing::debug!(max, "expedite lane size set");
        self.expedite_max = max;
        self
    }

    /// How many expedite tickets may be in progress at once; 0 closes the lane (expedite then gets no exception).
    pub fn expedite_max(&self) -> u32 {
        self.expedite_max
    }

    /// The configuration in force.
    pub fn config(&self) -> &LeaseConfig {
        &self.cfg
    }

    /// The compiled `[lease] shared_files` and `generated_files` patterns.
    pub fn shared(&self) -> &GlobSet {
        &self.shared
    }

    /// The resolver over this store's work tree.
    pub fn resolver(&self) -> &Resolver {
        &self.resolver
    }

    /// Match `scope` and every live lease's scope against the work tree before the lock is taken.
    ///
    /// The tree walk and glob matching dominate an overlap check; doing them here keeps them out of
    /// the critical section (the in-lock check then hits the resolver cache). Best effort: a failure
    /// here resurfaces, typed, from the in-lock check.
    fn prewarm(&self, scope: &[String]) {
        let started = std::time::Instant::now();
        let _ = self.resolver.matching(scope);
        for lease in self.live_snapshot().unwrap_or_default() {
            let _ = self.resolver.matching(&lease.scope);
        }
        tracing::debug!(
            elapsed_ms = ?started.elapsed(),
            "lease scopes prewarmed outside the lock"
        );
    }

    fn lease_path(&self, ticket: TicketId) -> PathBuf {
        self.dir.join(format!("{ticket}.toml"))
    }

    fn lock(&self) -> Result<LockGuard, LeaseError> {
        fs::create_dir_all(&self.dir)
            .map_err(|e| LeaseError::io(format!("creating {}", Shown::of(&self.dir)), e))?;
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(&self.lock_path)
            .map_err(|e| LeaseError::io(format!("opening {}", Shown::of(&self.lock_path)), e))?;
        let start = Instant::now();
        let limit = Duration::from_millis(self.cfg.lock_timeout_ms);
        loop {
            match file.try_lock() {
                Ok(()) => return Ok(LockGuard(file)),
                Err(TryLockError::WouldBlock) => {
                    if start.elapsed() >= limit {
                        tracing::warn!(path = %Shown::of(&self.lock_path), "lease lock timed out");
                        return Err(LeaseError::LockTimeout {
                            path: self.lock_path.clone(),
                            waited_ms: self.cfg.lock_timeout_ms,
                        });
                    }
                    std::thread::sleep(LOCK_POLL);
                }
                Err(TryLockError::Error(e)) => {
                    return Err(LeaseError::io(
                        format!("locking {}", Shown::of(&self.lock_path)),
                        e,
                    ));
                }
            }
        }
    }

    /// Every readable lease file plus every unreadable one, leases ordered by ticket.
    ///
    /// A corrupt file is reported, never deleted, and never counted as a lease:
    /// it cannot be proven to grant or block anything.
    fn scan(&self) -> Result<(Vec<Lease>, Vec<CorruptLease>), LeaseError> {
        let entries = match fs::read_dir(&self.dir) {
            Ok(e) => e,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                return Ok((Vec::new(), Vec::new()));
            }
            Err(e) => {
                return Err(LeaseError::io(
                    format!("reading {}", Shown::of(&self.dir)),
                    e,
                ));
            }
        };
        let mut out = Vec::new();
        let mut corrupt = Vec::new();
        for entry in entries {
            let path = entry
                .map_err(|e| LeaseError::io(format!("reading {}", Shown::of(&self.dir)), e))?
                .path();
            if path.extension().is_some_and(|x| x == "toml") {
                match read_lease(&path) {
                    Ok(l) => out.push(l),
                    Err(LeaseError::Format { path, message }) => {
                        tracing::warn!(path = %Shown::of(&path), %message, "corrupt lease file skipped");
                        corrupt.push(CorruptLease { path, message });
                    }
                    Err(e) => return Err(e),
                }
            }
        }
        out.sort_by_key(|l| l.ticket);
        corrupt.sort_by(|a, b| a.path.cmp(&b.path));
        Ok((out, corrupt))
    }

    /// Every readable lease file, live or expired, ordered by ticket.
    fn read_all(&self) -> Result<Vec<Lease>, LeaseError> {
        Ok(self.scan()?.0)
    }

    /// The lease files that cannot be read (read-only; for `lease list` and doctor).
    ///
    /// # Errors
    ///
    /// I/O failures reading the lease directory.
    pub fn corrupt_leases(&self) -> Result<Vec<CorruptLease>, LeaseError> {
        Ok(self.scan()?.1)
    }

    /// Move every corrupt lease file aside as `<name>.toml.corrupt` (kept, not deleted); returns the new paths.
    ///
    /// # Errors
    ///
    /// Lock and I/O failures.
    pub fn quarantine_corrupt(&self) -> Result<Vec<PathBuf>, LeaseError> {
        let _lock = self.lock()?;
        let mut moved = Vec::new();
        for c in self.scan()?.1 {
            let dest = c.path.with_extension("toml.corrupt");
            fs::rename(&c.path, &dest)
                .map_err(|e| LeaseError::io(format!("quarantining {}", Shown::of(&c.path)), e))?;
            tracing::info!(from = %Shown::of(&c.path), to = %Shown::of(&dest), "corrupt lease quarantined");
            moved.push(dest);
        }
        Ok(moved)
    }

    /// Live leases, deleting expired ones (requires the lock).
    fn live_pruned(&self, _lock: &LockGuard, now: Stamp) -> Result<Vec<Lease>, LeaseError> {
        let mut live = Vec::new();
        for lease in self.read_all()? {
            if lease.is_live(now) {
                live.push(lease);
            } else {
                let path = self.lease_path(lease.ticket);
                tracing::info!(ticket = %lease.ticket, holder = %lease.holder, "lease expired and removed");
                match fs::remove_file(&path) {
                    Ok(()) => {}
                    Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                    Err(e) => {
                        return Err(LeaseError::io(format!("removing {}", Shown::of(&path)), e));
                    }
                }
            }
        }
        Ok(live)
    }

    fn write(&self, _lock: &LockGuard, lease: &Lease) -> Result<(), LeaseError> {
        let path = self.lease_path(lease.ticket);
        let text = toml::to_string_pretty(lease).map_err(|e| LeaseError::Format {
            path: path.clone(),
            message: e.to_string(),
        })?;
        gob_fs::write_atomic(&path, text.as_bytes())
            .map_err(|e| LeaseError::io(format!("writing {}", Shown::of(&path)), e))
    }

    /// Take (or re-take) the lease on `ticket` for `holder` over `scope`.
    ///
    /// Atomic under the lock file. The same holder asking again renews the
    /// lease and gets `already: true` when the scope is unchanged. Another
    /// holder of the ticket, or any live lease on another ticket whose scope
    /// overlaps (see [`crate::overlap`]), refuses with [`LeaseError::Held`].
    ///
    /// # Errors
    ///
    /// [`LeaseError::Held`], [`LeaseError::WipLimit`], [`LeaseError::LockTimeout`],
    /// [`LeaseError::BadGlob`] and I/O or format failures.
    pub fn acquire(
        &self,
        ticket: TicketId,
        holder: &Holder,
        scope: &[String],
    ) -> Result<Acquired, LeaseError> {
        self.acquire_admitting(ticket, holder, scope, |_| Ok(()))
    }

    /// [`LeaseStore::acquire`] with an admission check run inside the same critical section.
    ///
    /// `admit` receives every live lease (this ticket's own included) while the
    /// lock is held, after the same-ticket holder check and before anything is
    /// written, so a count of live holders and the new lease are one atomic
    /// step: two callers racing for the last slot cannot both be admitted. An
    /// `Err` from `admit` aborts the acquisition and is returned unchanged.
    ///
    /// # Errors
    ///
    /// Whatever `admit` returns, plus everything [`LeaseStore::acquire`] can.
    pub fn acquire_admitting<E: From<LeaseError>>(
        &self,
        ticket: TicketId,
        holder: &Holder,
        scope: &[String],
        admit: impl FnOnce(&[Lease]) -> Result<(), E>,
    ) -> Result<Acquired, E> {
        self.prewarm(scope);
        let lock = self.lock()?;
        let now = self.now();
        if let Some(c) = self
            .corrupt_leases()?
            .into_iter()
            .find(|c| c.path == self.lease_path(ticket))
        {
            tracing::warn!(%ticket, path = %Shown::of(&c.path), "acquire refused: own lease file is corrupt");
            return Err(LeaseError::Format {
                path: c.path,
                message: c.message,
            }
            .into());
        }
        let live = self.live_pruned(&lock, now)?;
        let existing = live.iter().find(|l| l.ticket == ticket);
        if let Some(e) = existing.filter(|e| &e.holder != holder) {
            tracing::info!(%ticket, holder = %e.holder, "acquire refused: ticket held");
            return Err(LeaseError::Held {
                holder: e.holder.clone(),
                ticket,
                since: e.acquired_at,
                overlap: SAME_TICKET.to_owned(),
            }
            .into());
        }
        admit(&live)?;
        let limit = self.holder_limit;
        if limit > 0 {
            let count = live
                .iter()
                .filter(|l| l.ticket != ticket && &l.holder == holder && !l.queued)
                .count();
            if count >= limit as usize {
                tracing::info!(%ticket, %holder, count, limit, "acquire refused: wip limit");
                return Err(LeaseError::WipLimit {
                    holder: holder.clone(),
                    count,
                    limit,
                }
                .into());
            }
        }
        if existing.is_none() {
            self.check_queue(ticket, scope, now)?;
        }
        for other in live.iter().filter(|l| l.ticket != ticket) {
            if let Some(overlap) = scopes_overlap(
                (scope, ticket),
                (&other.scope, other.ticket),
                &self.shared,
                &self.resolver,
            )? {
                tracing::info!(%ticket, other = %other.ticket, holder = %other.holder, %overlap, "acquire refused: overlap");
                return Err(LeaseError::Held {
                    holder: other.holder.clone(),
                    ticket: other.ticket,
                    since: other.acquired_at,
                    overlap,
                }
                .into());
            }
        }
        let lease = match existing {
            Some(e) => Lease {
                scope: scope.to_vec(),
                renewed_at: now,
                ttl_secs: self.cfg.ttl_secs,
                queued: false,
                ..e.clone()
            },
            None => Lease {
                ticket,
                holder: holder.clone(),
                scope: scope.to_vec(),
                acquired_at: now,
                renewed_at: now,
                ttl_secs: self.cfg.ttl_secs,
                history: Vec::new(),
                queued: false,
                agent: self.agent.clone(),
                touched_at: None,
                touch_note: None,
                base: None,
            },
        };
        let already = existing.is_some_and(|e| e.scope == scope);
        self.write(&lock, &lease)?;
        self.remove_waiter(ticket)?;
        tracing::info!(%ticket, %holder, already, scope = ?lease.scope, "lease acquired");
        Ok(Acquired { lease, already })
    }

    fn waiter_path(&self, ticket: TicketId) -> PathBuf {
        self.waiters_dir.join(format!("{ticket}.toml"))
    }

    /// Every readable waiter record, oldest first (FIFO: enqueue time, then ticket); unreadable files are skipped with a warning.
    fn read_waiters(&self) -> Result<Vec<Waiter>, LeaseError> {
        let entries = match fs::read_dir(&self.waiters_dir) {
            Ok(e) => e,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(e) => {
                return Err(LeaseError::io(
                    format!("reading {}", Shown::of(&self.waiters_dir)),
                    e,
                ));
            }
        };
        let mut out = Vec::new();
        for entry in entries {
            let path = entry
                .map_err(|e| {
                    LeaseError::io(format!("reading {}", Shown::of(&self.waiters_dir)), e)
                })?
                .path();
            if path.extension().is_none_or(|x| x != "toml") {
                continue;
            }
            let text = fs::read_to_string(&path)
                .map_err(|e| LeaseError::io(format!("reading {}", Shown::of(&path)), e))?;
            match toml::from_str::<Waiter>(&text) {
                Ok(w) => out.push(w),
                Err(e) => {
                    tracing::warn!(path = %Shown::of(&path), error = %e, "corrupt waiter file skipped");
                }
            }
        }
        out.sort_by_key(|w| (w.enqueued_at.unix(), w.ticket));
        Ok(out)
    }

    /// Live waiters in FIFO order, deleting dead ones (requires the lock).
    fn live_waiters_pruned(&self, now: Stamp) -> Result<Vec<Waiter>, LeaseError> {
        let mut live = Vec::new();
        for w in self.read_waiters()? {
            if w.is_live(now) {
                live.push(w);
            } else {
                tracing::info!(ticket = %w.ticket, holder = %w.holder, "dead waiter reaped");
                self.remove_waiter(w.ticket)?;
            }
        }
        Ok(live)
    }

    fn remove_waiter(&self, ticket: TicketId) -> Result<(), LeaseError> {
        let path = self.waiter_path(ticket);
        match fs::remove_file(&path) {
            Ok(()) => {
                tracing::debug!(%ticket, "waiter dequeued");
                Ok(())
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(LeaseError::io(format!("removing {}", Shown::of(&path)), e)),
        }
    }

    /// Refuse with [`LeaseError::Queued`] when a live waiter ahead of `ticket` (every waiter if `ticket` is not one) overlaps `scope`; requires the lock.
    fn check_queue(
        &self,
        ticket: TicketId,
        scope: &[String],
        now: Stamp,
    ) -> Result<(), LeaseError> {
        let waiters = self.live_waiters_pruned(now)?;
        let own = waiters.iter().position(|w| w.ticket == ticket);
        let ahead = &waiters[..own.unwrap_or(waiters.len())];
        for w in ahead {
            if let Some(overlap) = scopes_overlap(
                (scope, ticket),
                (&w.scope, w.ticket),
                &self.shared,
                &self.resolver,
            )? {
                tracing::info!(%ticket, waiter = %w.ticket, %overlap, "acquire refused: queued waiter ahead");
                return Err(LeaseError::Queued {
                    waiter: w.ticket,
                    holder: Box::new(w.holder.clone()),
                    age_secs: w.age_secs(now),
                    overlap,
                });
            }
        }
        Ok(())
    }

    /// Join (or heartbeat in) the wait queue for `scope`; the first call fixes the FIFO position.
    ///
    /// # Errors
    ///
    /// Lock, I/O and format failures.
    pub fn enqueue(
        &self,
        ticket: TicketId,
        holder: &Holder,
        scope: &[String],
    ) -> Result<Waiter, LeaseError> {
        let _lock = self.lock()?;
        let now = self.now();
        fs::create_dir_all(&self.waiters_dir)
            .map_err(|e| LeaseError::io(format!("creating {}", Shown::of(&self.waiters_dir)), e))?;
        let previous = self
            .read_waiters()?
            .into_iter()
            .find(|w| w.ticket == ticket);
        let enqueued_at = previous
            .filter(|w| w.is_live(now))
            .map_or(now, |w| w.enqueued_at);
        let waiter = Waiter {
            ticket,
            holder: holder.clone(),
            scope: scope.to_vec(),
            enqueued_at,
            renewed_at: now,
            ttl_secs: self.cfg.waiter_ttl_secs,
        };
        let path = self.waiter_path(ticket);
        let text = toml::to_string_pretty(&waiter).map_err(|e| LeaseError::Format {
            path: path.clone(),
            message: e.to_string(),
        })?;
        gob_fs::write_atomic(&path, text.as_bytes())
            .map_err(|e| LeaseError::io(format!("writing {}", Shown::of(&path)), e))?;
        tracing::debug!(%ticket, %holder, "waiter enqueued or heartbeat");
        Ok(waiter)
    }

    /// Leave the wait queue (the wait ended without a lease); a no-op when not queued.
    ///
    /// # Errors
    ///
    /// Lock and I/O failures.
    pub fn dequeue(&self, ticket: TicketId) -> Result<(), LeaseError> {
        let _lock = self.lock()?;
        self.remove_waiter(ticket)
    }

    /// Live waiters in FIFO order with their age and blockers, reaping dead ones.
    ///
    /// # Errors
    ///
    /// Lock, I/O, glob and walk failures.
    pub fn waiters(&self) -> Result<Vec<WaiterInfo>, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let live = self.live_pruned(&lock, now)?;
        let waiters = self.live_waiters_pruned(now)?;
        let mut out = Vec::new();
        for (i, w) in waiters.iter().enumerate() {
            let mut blockers = Vec::new();
            let others = live
                .iter()
                .filter(|l| l.ticket != w.ticket)
                .map(|l| (l.ticket, &l.scope))
                .chain(waiters[..i].iter().map(|e| (e.ticket, &e.scope)));
            for (other, other_scope) in others {
                if scopes_overlap(
                    (&w.scope, w.ticket),
                    (other_scope, other),
                    &self.shared,
                    &self.resolver,
                )?
                .is_some()
                {
                    blockers.push(other);
                }
            }
            out.push(WaiterInfo {
                ticket: w.ticket,
                holder: w.holder.clone(),
                age_secs: w.age_secs(now),
                blockers,
            });
        }
        tracing::debug!(count = out.len(), "waiters listed");
        Ok(out)
    }

    /// Heartbeat: push the expiry of `holder`'s lease on `ticket` forward.
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] with no lease, [`LeaseError::Held`] for another holder, plus lock and I/O failures.
    pub fn renew(&self, ticket: TicketId, holder: &Holder) -> Result<Lease, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            return Err(held_by(&lease, SAME_TICKET));
        }
        lease.renewed_at = now;
        lease.ttl_secs = self.cfg.ttl_secs;
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, "lease renewed");
        Ok(lease)
    }

    /// Soft heartbeat (`frob claim touch`): renew `holder`'s lease and record the touch time and `note`.
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] with no lease, [`LeaseError::Held`] for another holder, plus lock and I/O failures.
    pub fn touch(
        &self,
        ticket: TicketId,
        holder: &Holder,
        note: Option<&str>,
    ) -> Result<Lease, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            return Err(held_by(&lease, SAME_TICKET));
        }
        lease.renewed_at = now;
        lease.ttl_secs = self.cfg.ttl_secs;
        lease.touched_at = Some(now);
        lease.touch_note = note.map(str::to_owned);
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, "claim touched");
        Ok(lease)
    }

    /// Record `base` (a commit id) as the diff base of `holder`'s lease, keeping an earlier one.
    ///
    /// frob:ticket 01M4CTV0F8HWA7DPXYYDBE4TDJ
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] with no lease, [`LeaseError::Held`] for another holder, plus lock and I/O failures.
    pub fn set_base(
        &self,
        ticket: TicketId,
        holder: &Holder,
        base: &str,
    ) -> Result<Lease, LeaseError> {
        let lock = self.lock()?;
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            return Err(held_by(&lease, SAME_TICKET));
        }
        if lease.base.is_none() {
            lease.base = Some(base.to_owned());
            self.write(&lock, &lease)?;
            tracing::info!(%ticket, %holder, base, "lease diff base recorded");
        } else {
            tracing::debug!(%ticket, "lease keeps its earlier diff base");
        }
        Ok(lease)
    }

    /// The diff base recorded on a live lease held from `worktree`, if any.
    ///
    /// frob:ticket 01M4CTV0F8HWA7DPXYYDBE4TDJ
    ///
    /// # Errors
    ///
    /// I/O and format failures.
    pub fn base_for_worktree(&self, worktree: &Path) -> Result<Option<String>, LeaseError> {
        let now = self.now();
        let want = same_path(worktree);
        Ok(self
            .read_all()?
            .into_iter()
            .find(|l| l.is_live(now) && same_path(&l.holder.worktree) == want && l.base.is_some())
            .and_then(|l| l.base))
    }

    /// Re-claim as `agent` (`Some` label) or as a human (`None`): the lease's window kind switches (`lease` op `rekind`).
    ///
    /// The touch record is cleared because the idle clock restarts.
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] with no lease, [`LeaseError::Held`] for another holder, plus lock and I/O failures.
    pub fn rekind(
        &self,
        ticket: TicketId,
        holder: &Holder,
        agent: Option<String>,
    ) -> Result<Lease, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            return Err(held_by(&lease, SAME_TICKET));
        }
        let before = lease.holder_kind();
        lease.agent = agent;
        if lease.holder_kind() == before {
            tracing::debug!(%ticket, "rekind is a no-op");
            return Ok(lease);
        }
        lease.renewed_at = now;
        lease.ttl_secs = self.cfg.ttl_secs;
        lease.touched_at = None;
        lease.touch_note = None;
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, from = ?before, to = ?lease.holder_kind(), "claim rekinded");
        Ok(lease)
    }

    /// Mark `holder`'s lease on `ticket` as waiting on the land train (`queued`) or taken back; a queued lease no longer counts toward WIP.
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] with no lease, [`LeaseError::Held`] for another holder, plus lock and I/O failures.
    pub fn set_queued(
        &self,
        ticket: TicketId,
        holder: &Holder,
        queued: bool,
    ) -> Result<Lease, LeaseError> {
        let lock = self.lock()?;
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            return Err(held_by(&lease, SAME_TICKET));
        }
        lease.queued = queued;
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, queued, "lease queued flag set");
        Ok(lease)
    }

    /// Heartbeat from observed activity: renew every live lease held from `worktree`.
    ///
    /// Only a live lease whose current holder's worktree is `worktree` is
    /// touched, so a lease stolen by another holder is never extended by the
    /// old holder's activity, and an expired lease is never revived here (that
    /// is [`LeaseStore::reclaim`], which re-checks overlap). Returns the
    /// renewed leases, empty when nothing was held from `worktree`.
    ///
    /// # Errors
    ///
    /// Lock, I/O and format failures.
    pub fn renew_for_worktree(&self, worktree: &Path) -> Result<Vec<Lease>, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let want = same_path(worktree);
        let mut renewed = Vec::new();
        for mut lease in self.read_all()? {
            if !lease.is_live(now) || same_path(&lease.holder.worktree) != want {
                continue;
            }
            lease.renewed_at = now;
            lease.ttl_secs = self.cfg.ttl_secs;
            self.write(&lock, &lease)?;
            tracing::info!(ticket = %lease.ticket, holder = %lease.holder, "lease renewed by activity");
            renewed.push(lease);
        }
        Ok(renewed)
    }

    /// The lease file of `ticket` whether or not it has expired (read-only).
    ///
    /// # Errors
    ///
    /// I/O and format failures.
    pub fn recorded_lease(&self, ticket: TicketId) -> Result<Option<Lease>, LeaseError> {
        self.find(ticket)
    }

    /// Renew `holder`'s lease on `ticket`, re-taking it when it expired unclaimed.
    ///
    /// A live lease of the same holder is renewed. When the lease expired or
    /// was pruned, it is re-acquired over `scope`, which succeeds only while no
    /// other holder holds the ticket or a live lease overlapping `scope`:
    /// a takeover is never renewed across.
    ///
    /// # Errors
    ///
    /// [`LeaseError::Held`] when another holder took the ticket or an
    /// overlapping scope since, plus everything [`LeaseStore::acquire`] can.
    pub fn reclaim(
        &self,
        ticket: TicketId,
        holder: &Holder,
        scope: &[String],
    ) -> Result<Lease, LeaseError> {
        if let Some(l) = self.live_lease(ticket)?
            && &l.holder == holder
        {
            return self.renew(ticket, holder);
        }
        let got = self.acquire(ticket, holder, scope)?;
        tracing::info!(%ticket, %holder, "expired lease reclaimed: no overlapping lease was taken since");
        Ok(got.lease)
    }

    /// Replace the scope of `holder`'s live lease on `ticket` with `new_scope`.
    ///
    /// Used when the ticket's scope changes while it is leased. Under the lock,
    /// a scope that adds any glob is re-checked against every other live lease
    /// (glob text and resolved files, shared files exempt) and refused with
    /// [`LeaseError::Held`] naming the other holder on overlap; a pure narrowing
    /// cannot conflict and skips the check. The change is appended to the
    /// lease's `history` (a [`StealRecord`] with the same holder on both sides) and the lease is renewed. Asking for the scope
    /// already in force changes nothing (idempotent).
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] without a live lease, [`LeaseError::Held`] when
    /// `holder` does not hold it or the new scope overlaps another lease,
    /// [`LeaseError::BadGlob`], lock and I/O failures.
    pub fn rescope(
        &self,
        ticket: TicketId,
        holder: &Holder,
        new_scope: &[String],
        cfg: &LeaseConfig,
    ) -> Result<Lease, LeaseError> {
        self.prewarm(new_scope);
        let lock = self.lock()?;
        let now = self.now();
        let live = self.live_pruned(&lock, now)?;
        let mut lease = live
            .iter()
            .find(|l| l.ticket == ticket)
            .cloned()
            .ok_or(LeaseError::NotHeld { ticket })?;
        if &lease.holder != holder {
            tracing::info!(%ticket, holder = %lease.holder, caller = %holder, "rescope refused: not the holder");
            return Err(held_by(&lease, SAME_TICKET));
        }
        if lease.scope == new_scope {
            tracing::debug!(%ticket, "rescope: scope already in force");
            return Ok(lease);
        }
        let widens = new_scope.iter().any(|g| !lease.scope.contains(g));
        if let Some(glob) = new_scope
            .iter()
            .find(|g| !lease.scope.contains(g) && covers_foreign_fragments(g))
        {
            tracing::info!(%ticket, %glob, "rescope refused: glob covers other tickets' fragments");
            return Err(LeaseError::FragmentGlob { glob: glob.clone() });
        }
        if widens {
            for other in live.iter().filter(|l| l.ticket != ticket) {
                if let Some(overlap) = scopes_overlap(
                    (new_scope, ticket),
                    (&other.scope, other.ticket),
                    &self.shared,
                    &self.resolver,
                )? {
                    tracing::info!(%ticket, other = %other.ticket, holder = %other.holder, %overlap, "rescope refused: overlap");
                    return Err(LeaseError::Held {
                        holder: other.holder.clone(),
                        ticket: other.ticket,
                        since: other.acquired_at,
                        overlap,
                    });
                }
            }
        }
        lease.history.push(StealRecord {
            at: now,
            from: holder.clone(),
            to: holder.clone(),
            reason: format!(
                "rescope: [{}] -> [{}]",
                lease.scope.join(", "),
                new_scope.join(", ")
            ),
        });
        lease.scope = new_scope.to_vec();
        lease.renewed_at = now;
        lease.ttl_secs = cfg.ttl_secs;
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, scope = ?lease.scope, widens, "lease rescoped");
        Ok(lease)
    }

    /// Release the lease on `ticket`; `None` when there was none.
    ///
    /// With `as_actor`, a live lease held by a different actor is refused
    /// ([`LeaseError::ActorMismatch`], naming both identities); an expired one is removed regardless.
    ///
    /// # Errors
    ///
    /// [`LeaseError::ActorMismatch`], lock and I/O failures.
    pub fn release(
        &self,
        ticket: TicketId,
        as_actor: Option<&str>,
    ) -> Result<Option<Lease>, LeaseError> {
        let _lock = self.lock()?;
        let now = self.now();
        let Some(lease) = self.find(ticket)? else {
            tracing::debug!(%ticket, "release: no lease");
            return Ok(None);
        };
        if let Some(actor) = as_actor
            && lease.is_live(now)
            && lease.holder.actor != actor
        {
            tracing::warn!(%ticket, holder = %lease.holder, actor, "release refused: actor mismatch");
            return Err(LeaseError::ActorMismatch {
                ticket,
                holder: lease.holder.clone(),
                actor: actor.to_owned(),
            });
        }
        let path = self.lease_path(ticket);
        fs::remove_file(&path)
            .map_err(|e| LeaseError::io(format!("removing {}", Shown::of(&path)), e))?;
        tracing::info!(%ticket, holder = %lease.holder, "lease released");
        Ok(Some(lease))
    }

    /// Take over the lease on `ticket` for `by`, recording `reason` in its history.
    ///
    /// The scope stays as the previous holder declared it. The caller logs the
    /// returned previous holder as a ledger event.
    ///
    /// # Errors
    ///
    /// [`LeaseError::NotHeld`] when the ticket has no lease (acquire instead), lock and I/O failures.
    pub fn steal(&self, ticket: TicketId, by: &Holder, reason: &str) -> Result<Stolen, LeaseError> {
        let lock = self.lock()?;
        let now = self.now();
        let mut lease = self.find(ticket)?.ok_or(LeaseError::NotHeld { ticket })?;
        let previous = lease.holder.clone();
        if &previous != by {
            lease.history.push(StealRecord {
                at: now,
                from: previous.clone(),
                to: by.clone(),
                reason: reason.to_owned(),
            });
            lease.holder = by.clone();
            lease.acquired_at = now;
        }
        lease.renewed_at = now;
        lease.ttl_secs = self.cfg.ttl_secs;
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, from = %previous, to = %by, reason, "lease stolen");
        Ok(Stolen { lease, previous })
    }

    /// Live leases ordered by ticket, removing expired ones on the way.
    ///
    /// # Errors
    ///
    /// Lock, I/O and format failures.
    pub fn list(&self) -> Result<Vec<Lease>, LeaseError> {
        let lock = self.lock()?;
        let live = self.live_pruned(&lock, self.now())?;
        tracing::debug!(count = live.len(), "leases listed");
        Ok(live)
    }

    /// Live leases without taking the lock or deleting anything (read-only snapshot).
    ///
    /// # Errors
    ///
    /// I/O and format failures.
    pub fn live_snapshot(&self) -> Result<Vec<Lease>, LeaseError> {
        let now = self.now();
        Ok(self
            .read_all()?
            .into_iter()
            .filter(|l| l.is_live(now))
            .collect())
    }

    /// The live lease on `ticket`, if any (read-only).
    ///
    /// # Errors
    ///
    /// I/O and format failures.
    pub fn live_lease(&self, ticket: TicketId) -> Result<Option<Lease>, LeaseError> {
        let now = self.now();
        Ok(self.find(ticket)?.filter(|l| l.is_live(now)))
    }

    fn find(&self, ticket: TicketId) -> Result<Option<Lease>, LeaseError> {
        let path = self.lease_path(ticket);
        match path.try_exists() {
            Ok(true) => read_lease(&path).map(Some),
            Ok(false) => Ok(None),
            Err(e) => Err(LeaseError::io(format!("probing {}", Shown::of(&path)), e)),
        }
    }

    /// Files declared by two or more live leases, most contended first.
    ///
    /// Shared files are included: they are exempt from refusals, not from the report.
    ///
    /// # Errors
    ///
    /// Lock, I/O, glob and walk failures.
    pub fn contention(&self) -> Result<Vec<Contended>, LeaseError> {
        let live = self.list()?;
        let none = GlobSet::empty();
        let mut by_file: BTreeMap<String, Vec<TicketId>> = BTreeMap::new();
        for lease in &live {
            for file in self.resolver.resolve(&lease.scope, &none)? {
                by_file.entry(file).or_default().push(lease.ticket);
            }
        }
        let mut out: Vec<Contended> = by_file
            .into_iter()
            .filter(|(_, t)| t.len() > 1)
            .map(|(file, tickets)| Contended { file, tickets })
            .collect();
        out.sort_by(|a, b| {
            b.tickets
                .len()
                .cmp(&a.tickets.len())
                .then(a.file.cmp(&b.file))
        });
        tracing::debug!(files = out.len(), "contention computed");
        Ok(out)
    }
}

fn held_by(lease: &Lease, overlap: &str) -> LeaseError {
    LeaseError::Held {
        holder: lease.holder.clone(),
        ticket: lease.ticket,
        since: lease.acquired_at,
        overlap: overlap.to_owned(),
    }
}

fn read_lease(path: &Path) -> Result<Lease, LeaseError> {
    let text = fs::read_to_string(path)
        .map_err(|e| LeaseError::io(format!("reading {}", Shown::of(path)), e))?;
    toml::from_str(&text).map_err(|e| LeaseError::Format {
        path: path.to_path_buf(),
        message: e.to_string(),
    })
}

/// A path normalised for comparing worktrees: canonical when it exists, else as given.
fn same_path(p: &Path) -> PathBuf {
    gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf())
}
