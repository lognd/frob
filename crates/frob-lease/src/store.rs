//! The lease directory under the git common dir, guarded by one lock file.
//!
//! Layout: `<common_dir>/frob/leases/<ticket ulid>.toml` per lease and
//! `<common_dir>/frob/leases.lock`. Every operation that reads, decides and
//! writes (acquire, renew, release, steal, list with pruning) holds the lock
//! for its whole duration, so two callers can never both pass the overlap
//! check. The lock is an advisory `flock` on a file shared by all worktrees of
//! one clone; leases are single-clone by design (decision D26).

// frob:ticket 01M40Q3S4T9QTYX0Z1MPAZP9JM

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
use crate::model::{Holder, Lease, StealRecord};
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
    lock_path: PathBuf,
    cfg: LeaseConfig,
    holder_limit: u32,
    repo_limit: u32,
    expedite_max: u32,
    shared: GlobSet,
    resolver: Resolver,
    clock: Arc<dyn Clock>,
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
        tracing::debug!(dir = %base.display(), ttl_secs = cfg.ttl_secs, "lease store opened");
        Ok(Self {
            dir: base.join("leases"),
            lock_path: base.join("leases.lock"),
            cfg,
            holder_limit: 0,
            repo_limit: 0,
            expedite_max: 1,
            shared,
            resolver: Resolver::new(root),
            clock,
        })
    }

    /// The clock instant at the whole-second precision of lease files.
    fn now(&self) -> Stamp {
        self.clock.now().seconds()
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
            .map_err(|e| LeaseError::io(format!("creating {}", self.dir.display()), e))?;
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(&self.lock_path)
            .map_err(|e| LeaseError::io(format!("opening {}", self.lock_path.display()), e))?;
        let start = Instant::now();
        let limit = Duration::from_millis(self.cfg.lock_timeout_ms);
        loop {
            match file.try_lock() {
                Ok(()) => return Ok(LockGuard(file)),
                Err(TryLockError::WouldBlock) => {
                    if start.elapsed() >= limit {
                        tracing::warn!(path = %self.lock_path.display(), "lease lock timed out");
                        return Err(LeaseError::LockTimeout {
                            path: self.lock_path.clone(),
                            waited_ms: self.cfg.lock_timeout_ms,
                        });
                    }
                    std::thread::sleep(LOCK_POLL);
                }
                Err(TryLockError::Error(e)) => {
                    return Err(LeaseError::io(
                        format!("locking {}", self.lock_path.display()),
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
            Err(e) => return Err(LeaseError::io(format!("reading {}", self.dir.display()), e)),
        };
        let mut out = Vec::new();
        let mut corrupt = Vec::new();
        for entry in entries {
            let path = entry
                .map_err(|e| LeaseError::io(format!("reading {}", self.dir.display()), e))?
                .path();
            if path.extension().is_some_and(|x| x == "toml") {
                match read_lease(&path) {
                    Ok(l) => out.push(l),
                    Err(LeaseError::Format { path, message }) => {
                        tracing::warn!(path = %path.display(), %message, "corrupt lease file skipped");
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
                .map_err(|e| LeaseError::io(format!("quarantining {}", c.path.display()), e))?;
            tracing::info!(from = %c.path.display(), to = %dest.display(), "corrupt lease quarantined");
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
                        return Err(LeaseError::io(format!("removing {}", path.display()), e));
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
            .map_err(|e| LeaseError::io(format!("writing {}", path.display()), e))
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
            tracing::warn!(%ticket, path = %c.path.display(), "acquire refused: own lease file is corrupt");
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
                .filter(|l| l.ticket != ticket && &l.holder == holder)
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
            },
        };
        let already = existing.is_some_and(|e| e.scope == scope);
        self.write(&lock, &lease)?;
        tracing::info!(%ticket, %holder, already, scope = ?lease.scope, "lease acquired");
        Ok(Acquired { lease, already })
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
    /// ([`LeaseError::Held`]); an expired one is removed regardless.
    ///
    /// # Errors
    ///
    /// [`LeaseError::Held`], lock and I/O failures.
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
            return Err(held_by(&lease, SAME_TICKET));
        }
        let path = self.lease_path(ticket);
        fs::remove_file(&path)
            .map_err(|e| LeaseError::io(format!("removing {}", path.display()), e))?;
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
            Err(e) => Err(LeaseError::io(format!("probing {}", path.display()), e)),
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
        .map_err(|e| LeaseError::io(format!("reading {}", path.display()), e))?;
    toml::from_str(&text).map_err(|e| LeaseError::Format {
        path: path.to_path_buf(),
        message: e.to_string(),
    })
}

/// A path normalised for comparing worktrees: canonical when it exists, else as given.
fn same_path(p: &Path) -> PathBuf {
    gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf())
}
