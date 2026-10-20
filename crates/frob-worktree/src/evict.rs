//! Claim eviction: park the holder's work, delete the claim by compare-and-swap, and recover from every crash point (`distributed-tickets.md` sections 4.5 to 4.7).
//!
//! The protocol is ordered so a crash anywhere is safe. First a create-only
//! push of `parked/<handle>-<n>` whose tip is one additive metadata commit on
//! top of the observed holder tip `X`; then a delete of `ticket/<handle>` with
//! `--force-with-lease` against `X`. A moved tip means the holder is alive and
//! the parked ref is withdrawn. The ledger record (`lease` op `evict`) is the
//! caller's step; [`needs_completion`] recognises the crash between delete and
//! record so any sync can finish it from the metadata commit
//! ([`read_park_record`]).
//!
//! Everything that decides is a pure function ([`check_evictable`],
//! [`holder_return`], [`reclaim_plan`], [`evict_batch`]); only [`evict`],
//! [`parked_refs`] and [`read_park_record`] touch git.

// frob:ticket 01M5CW051RTDRTFH0X96CVW7F9

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use gob_git::{RemoteProbe, RemoteRun, Repo};

use crate::claim::{remote_claim, sync_settings};
use crate::error::WorktreeError;

/// Refusal code when the holder moved the branch between observation and delete.
pub const E_CLAIM_ACTIVE: &str = "E-CLAIM-ACTIVE";

/// Warning code shown to a holder whose claim was evicted while they were away.
pub const W_CLAIM_EVICTED: &str = "W-CLAIM-EVICTED";

/// Most `parked/<handle>-<n>` names tried when create-only pushes keep colliding.
const PARK_ATTEMPTS: u32 = 5;

/// Commit message trailer keys of the park commit, in the order written.
const KEY_TICKET: &str = "Frob-Ticket";
const KEY_EVICTOR: &str = "Frob-Evictor";
const KEY_HOLDER: &str = "Frob-Holder";
const KEY_OBSERVED: &str = "Frob-Observed";
const KEY_IDLE: &str = "Frob-Idle-Secs";
const KEY_WINDOW: &str = "Frob-Window-Secs";
const KEY_REASON: &str = "Frob-Reason";

/// What an eviction needs to know about the claim it ends.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvictRequest {
    /// Ticket handle without the tilde; the branch is `ticket/<handle>`.
    pub handle: String,
    /// Who held the claim.
    pub holder: String,
    /// Who is evicting.
    pub evictor: String,
    /// The holder's branch tip this clone observed (`X`).
    pub observed: String,
    /// Idle seconds this clone measured.
    pub idle_secs: u64,
    /// The window in seconds that idle time passed.
    pub window_secs: u64,
    /// Why the claim is being evicted.
    pub reason: String,
}

/// How an eviction attempt ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvictOutcome {
    /// The work is parked and the claim branch deleted; `parked` is the new ref (`parked/<handle>-<n>`).
    Evicted {
        /// The parked ref name.
        parked: String,
    },
    /// The holder pushed since `observed`: `E-CLAIM-ACTIVE`, the parked ref was withdrawn.
    Active {
        /// The holder's current tip.
        tip: String,
    },
    /// Another evictor won: the claim branch was already gone.
    AlreadyEvicted,
    /// The remote could not be reached or has no remote configured; nothing changed.
    Offline(String),
}

/// Why an eviction is refused before touching the remote.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvictRefusal {
    /// The clone is offline: eviction never happens offline.
    Offline,
    /// No window applies (`0` means never evict).
    NoWindow,
    /// This clone's own observed idle time has not reached the window.
    NotIdle,
    /// A hold or a pause (blocked, queued, in review) stops the clock.
    Held,
    /// The evictor used up `evict_rate` for today.
    RateLimited,
    /// A reclaim happened less than one window ago.
    FlapGuard,
    /// Running in CI: automation never evicts.
    InCi,
}

impl EvictRefusal {
    /// The stable refusal code and one-line reason.
    #[must_use]
    pub fn describe(self) -> (&'static str, &'static str) {
        match self {
            Self::Offline => (
                "E-CLAIM-OFFLINE",
                "eviction needs the remote; you are offline",
            ),
            Self::NoWindow => (
                "E-CLAIM-NO-WINDOW",
                "this claim never expires (window is 0)",
            ),
            Self::NotIdle => (
                "E-CLAIM-NOT-IDLE",
                "this clone has not observed the claim idle for a full window",
            ),
            Self::Held => ("E-CLAIM-HELD", "the claim is held or paused"),
            Self::RateLimited => ("E-CLAIM-RATE", "evict_rate for today is used up"),
            Self::FlapGuard => (
                "E-CLAIM-FLAP",
                "the claim was reclaimed less than one window ago",
            ),
            Self::InCi => ("E-CLAIM-CI", "eviction is refused in CI"),
        }
    }
}

/// The facts [`check_evictable`] weighs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(clippy::struct_excessive_bools)]
pub struct EvictContext {
    /// A fetch inside this command succeeded.
    pub online: bool,
    /// The window in seconds; `None` or `Some(0)` means never evict.
    pub window_secs: Option<u64>,
    /// This clone's observed idle seconds.
    pub idle_secs: u64,
    /// The claim has an active hold or pause.
    pub held_or_paused: bool,
    /// Evictions this actor already made today.
    pub evictions_today: u32,
    /// `[claims] evict_rate`.
    pub evict_rate: u32,
    /// Seconds since the last reclaim of this claim, when there was one.
    pub since_reclaim_secs: Option<u64>,
    /// The process runs in CI.
    pub in_ci: bool,
}

/// Apply the preconditions of section 4.5; the first failing one is the refusal.
///
/// # Errors
/// The [`EvictRefusal`] that applies.
pub fn check_evictable(c: &EvictContext) -> Result<(), EvictRefusal> {
    let window = match c.window_secs {
        Some(w) if w > 0 => w,
        _ => return Err(EvictRefusal::NoWindow),
    };
    let refusal = if !c.online {
        Some(EvictRefusal::Offline)
    } else if c.in_ci {
        Some(EvictRefusal::InCi)
    } else if c.held_or_paused {
        Some(EvictRefusal::Held)
    } else if c.idle_secs < window {
        Some(EvictRefusal::NotIdle)
    } else if c.evictions_today >= c.evict_rate {
        Some(EvictRefusal::RateLimited)
    } else if c.since_reclaim_secs.is_some_and(|s| s < window) {
        Some(EvictRefusal::FlapGuard)
    } else {
        None
    };
    match refusal {
        Some(r) => {
            tracing::info!(refusal = ?r, "eviction refused by precondition");
            Err(r)
        }
        None => Ok(()),
    }
}

/// The parked ref name for `handle` and sequence `n`.
#[must_use]
pub fn parked_name(handle: &str, n: u32) -> String {
    format!("parked/{handle}-{n}")
}

/// The sequence number of a `parked/<handle>-<n>` ref (full or short name), when it is one for `handle`.
#[must_use]
pub fn parked_seq(refname: &str, handle: &str) -> Option<u32> {
    let short = refname.strip_prefix("refs/heads/").unwrap_or(refname);
    short
        .strip_prefix(&format!("parked/{handle}-"))?
        .parse()
        .ok()
}

/// The next free sequence number for `handle` among `existing` parked refs (1 when there are none).
#[must_use]
pub fn next_parked_seq(existing: &[String], handle: &str) -> u32 {
    existing
        .iter()
        .filter_map(|r| parked_seq(r, handle))
        .max()
        .map_or(1, |n| n + 1)
}

/// The newest parked ref for `handle` among `existing`, when any.
#[must_use]
pub fn newest_parked<'a>(existing: &'a [String], handle: &str) -> Option<&'a str> {
    existing
        .iter()
        .filter_map(|r| parked_seq(r, handle).map(|n| (n, r.as_str())))
        .max_by_key(|(n, _)| *n)
        .map(|(_, r)| r)
}

/// The metadata recorded in a park commit: enough to finish the eviction after a crash.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParkRecord {
    /// Ticket handle without the tilde.
    pub handle: String,
    /// Who evicted.
    pub evictor: String,
    /// Who held the claim.
    pub holder: String,
    /// The holder tip that was parked.
    pub observed: String,
    /// Idle seconds at eviction.
    pub idle_secs: u64,
    /// Window seconds at eviction.
    pub window_secs: u64,
    /// The eviction reason.
    pub reason: String,
}

/// Render the park commit message for `req`.
#[must_use]
pub fn park_message(req: &EvictRequest) -> String {
    format!(
        "chore(claims): park ~{h} after eviction\n\n{KEY_TICKET}: {h}\n{KEY_EVICTOR}: {e}\n{KEY_HOLDER}: {o}\n{KEY_OBSERVED}: {x}\n{KEY_IDLE}: {i}\n{KEY_WINDOW}: {w}\n{KEY_REASON}: {r}\n",
        h = req.handle,
        e = req.evictor,
        o = req.holder,
        x = req.observed,
        i = req.idle_secs,
        w = req.window_secs,
        r = req.reason.replace('\n', " "),
    )
}

/// Parse a park commit message back into its [`ParkRecord`]; `None` when it is not one.
#[must_use]
pub fn parse_park_message(message: &str) -> Option<ParkRecord> {
    let get = |key: &str| -> Option<String> {
        message
            .lines()
            .find_map(|l| l.strip_prefix(key)?.strip_prefix(": "))
            .map(str::to_owned)
    };
    Some(ParkRecord {
        handle: get(KEY_TICKET)?,
        evictor: get(KEY_EVICTOR)?,
        holder: get(KEY_HOLDER)?,
        observed: get(KEY_OBSERVED)?,
        idle_secs: get(KEY_IDLE)?.parse().ok()?,
        window_secs: get(KEY_WINDOW)?.parse().ok()?,
        reason: get(KEY_REASON)?,
    })
}

/// Whether a sync must finish an eviction: the ticket is still in progress, its branch is gone, and a parked ref exists.
#[must_use]
pub fn needs_completion(
    ticket_in_progress: bool,
    branch_present: bool,
    parked: &[String],
    handle: &str,
) -> bool {
    ticket_in_progress && !branch_present && newest_parked(parked, handle).is_some()
}

/// The git failure text as a [`WorktreeError`] usage-free config error.
fn git_failed(what: &str, text: &str) -> WorktreeError {
    WorktreeError::Config(format!("{what}: {}", text.trim()))
}

/// Run one local git command in `repo`, returning trimmed stdout.
fn git_out(repo: &Repo, args: &[&str], cwd: Option<&Path>) -> Result<String, WorktreeError> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: cwd
            .map(Path::to_path_buf)
            .or_else(|| repo.work_dir().map(Path::to_path_buf)),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = repo
        .runner()
        .run(&spec)
        .map_err(|e| git_failed("git", &e.to_string()))?;
    if out.status == Outcome::Exited(0) {
        Ok(out.stdout.trim().to_owned())
    } else {
        Err(git_failed(&args.join(" "), &out.stderr))
    }
}

/// Read the [`ParkRecord`] from the park commit at `oid` (it must be present locally).
///
/// # Errors
/// [`WorktreeError::Config`] when git cannot read the commit.
pub fn read_park_record(repo: &Repo, oid: &str) -> Result<Option<ParkRecord>, WorktreeError> {
    let msg = git_out(repo, &["log", "-1", "--format=%B", oid], None)?;
    Ok(parse_park_message(&msg))
}

/// The parked refs for `handle` on `remote`: `Ok(Err(text))` when the remote did not answer.
///
/// # Errors
/// [`WorktreeError::Git`] when git cannot be started.
pub fn parked_refs(
    repo: &Repo,
    remote: &str,
    handle: &str,
    timeout: Duration,
) -> Result<Result<Vec<String>, String>, WorktreeError> {
    let pattern = format!("refs/heads/parked/{handle}-*");
    Ok(
        match repo.ls_remote(remote, std::slice::from_ref(&pattern), timeout)? {
            RemoteProbe::Refs { refs, .. } => Ok(refs.into_iter().map(|r| r.name).collect()),
            RemoteProbe::TimedOut => Err("the remote timed out".to_owned()),
            RemoteProbe::Failed { text, .. } => Err(text.trim().to_owned()),
        },
    )
}

/// Create the park commit for `req`: no tree change, first parent `observed`, metadata in the message.
fn park_commit(repo: &Repo, req: &EvictRequest) -> Result<String, WorktreeError> {
    let tree = format!("{}^{{tree}}", req.observed);
    git_out(
        repo,
        &[
            "commit-tree",
            &tree,
            "-p",
            &req.observed,
            "-m",
            &park_message(req),
        ],
        None,
    )
}

/// Evict: park, then delete `ticket/<handle>` only if its tip is still `observed`.
///
/// Preconditions are the caller's ([`check_evictable`]); this is the remote
/// protocol of section 4.5 steps 1 and 2. The observed tip must be present
/// locally (the caller fetched it).
///
/// # Errors
/// [`WorktreeError`] when git cannot be started or the park commit cannot be made.
pub fn evict(repo: &Repo, req: &EvictRequest) -> Result<EvictOutcome, WorktreeError> {
    let (remote, timeout) = sync_settings(repo);
    if repo.remote_url(&remote).is_none() {
        return Ok(EvictOutcome::Offline("no remote configured".to_owned()));
    }
    let branch = format!("ticket/{}", req.handle);
    let existing = match parked_refs(repo, &remote, &req.handle, timeout)? {
        Ok(v) => v,
        Err(why) => return Ok(EvictOutcome::Offline(why)),
    };
    let park_oid = park_commit(repo, req)?;
    let mut n = next_parked_seq(&existing, &req.handle);
    let mut parked = None;
    for _ in 0..PARK_ATTEMPTS {
        let name = parked_name(&req.handle, n);
        let dst = format!("refs/heads/{name}");
        match repo.push_cas(&remote, &park_oid, &dst, None, timeout)? {
            RemoteRun::Done => {
                tracing::info!(parked = %name, observed = %req.observed, "claim parked");
                parked = Some(name);
                break;
            }
            RemoteRun::Rejected(_) => {
                tracing::debug!(parked = %name, "parked name taken; trying the next");
                n += 1;
            }
            RemoteRun::TimedOut => return Ok(EvictOutcome::Offline("the push timed out".into())),
            RemoteRun::Failed { text, .. } => return Ok(EvictOutcome::Offline(text)),
        }
    }
    let Some(parked) = parked else {
        return Ok(EvictOutcome::Offline(
            "could not reserve a parked ref name".to_owned(),
        ));
    };
    let ticket_dst = format!("refs/heads/{branch}");
    let deleted = repo.push_cas(&remote, "", &ticket_dst, Some(&req.observed), timeout)?;
    match deleted {
        RemoteRun::Done => Ok(EvictOutcome::Evicted { parked }),
        RemoteRun::Rejected(_) => {
            let outcome = match remote_claim(repo, &remote, &branch, timeout)? {
                Ok(Some(tip)) => EvictOutcome::Active { tip },
                Ok(None) => EvictOutcome::AlreadyEvicted,
                Err(why) => {
                    tracing::warn!(parked = %parked, why = %why, "delete rejected and the remote went away; parked ref kept for crash completion");
                    return Ok(EvictOutcome::Offline(why));
                }
            };
            withdraw(repo, &remote, &parked, &park_oid, timeout)?;
            tracing::info!(?outcome, "eviction lost the race");
            Ok(outcome)
        }
        RemoteRun::TimedOut => Ok(EvictOutcome::Offline("the delete timed out".into())),
        RemoteRun::Failed { text, .. } => Ok(EvictOutcome::Offline(text)),
    }
}

/// Delete our own parked ref after losing the race (only if it is still the park commit we made).
fn withdraw(
    repo: &Repo,
    remote: &str,
    parked: &str,
    park_oid: &str,
    timeout: Duration,
) -> Result<(), WorktreeError> {
    let dst = format!("refs/heads/{parked}");
    let run = repo.push_cas(remote, "", &dst, Some(park_oid), timeout)?;
    if run != RemoteRun::Done {
        tracing::warn!(parked, ?run, "could not withdraw the parked ref");
    }
    Ok(())
}

/// What the returning holder's refresh does on seeing an `evict` event naming them (section 4.6).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HolderReturn {
    /// Where their new local commits go instead of `ticket/<handle>`.
    pub push_to: String,
    /// The `W-CLAIM-EVICTED` message.
    pub warning: String,
}

/// Plan the returning holder's push: never `ticket/<handle>`, always the next parked ref.
#[must_use]
pub fn holder_return(record: &ParkRecord, parked: &[String], evicted_on: &str) -> HolderReturn {
    let next = parked_name(&record.handle, next_parked_seq(parked, &record.handle));
    let tenths = record.idle_secs.saturating_mul(10) / 86_400;
    let days = format!("{}.{}", tenths / 10, tenths % 10);
    let warning = format!(
        "{W_CLAIM_EVICTED}: ~{h} evicted by {e} on {evicted_on} after {days} idle days; your work is safe at {next}; frob work ~{h} --reclaim",
        h = record.handle,
        e = record.evictor,
    );
    HolderReturn {
        push_to: next,
        warning,
    }
}

/// Why `--reclaim` is refused.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReclaimRefusal {
    /// Someone else holds the ticket now; coordinate with them.
    HeldBy(String),
    /// There is no parked ref to restore from.
    NothingParked,
}

/// Plan `frob work ~X --reclaim`: with the ticket still `todo` and a parked ref, restore from the newest.
///
/// # Errors
/// [`ReclaimRefusal`] when someone else holds the ticket or nothing is parked.
pub fn reclaim_plan(
    other_holder: Option<&str>,
    parked: &[String],
    handle: &str,
) -> Result<String, ReclaimRefusal> {
    if let Some(h) = other_holder {
        return Err(ReclaimRefusal::HeldBy(h.to_owned()));
    }
    newest_parked(parked, handle)
        .map(|r| r.strip_prefix("refs/heads/").unwrap_or(r).to_owned())
        .ok_or(ReclaimRefusal::NothingParked)
}

/// The result of one item of a batch eviction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BatchItem {
    /// The attempt ran with this outcome.
    Ran(EvictOutcome),
    /// Not attempted: `evict_rate` ran out before this item.
    RateLimited,
}

/// Evict many claims in order, stopping at `rate_left` successful evictions (the actor's remaining `evict_rate`).
///
/// # Errors
/// The first [`WorktreeError`] from [`evict`]; earlier results are lost with it.
pub fn evict_batch(
    repo: &Repo,
    requests: &[EvictRequest],
    rate_left: u32,
) -> Result<Vec<(String, BatchItem)>, WorktreeError> {
    let mut left = rate_left;
    let mut out = Vec::with_capacity(requests.len());
    for req in requests {
        if left == 0 {
            tracing::info!(handle = %req.handle, "batch evict stopped by evict_rate");
            out.push((req.handle.clone(), BatchItem::RateLimited));
            continue;
        }
        let outcome = evict(repo, req)?;
        if matches!(outcome, EvictOutcome::Evicted { .. }) {
            left -= 1;
        }
        out.push((req.handle.clone(), BatchItem::Ran(outcome)));
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn req() -> EvictRequest {
        EvictRequest {
            handle: "ABC".into(),
            holder: "ann".into(),
            evictor: "bob".into(),
            observed: "deadbeef".into(),
            idle_secs: 276_480,
            window_secs: 259_200,
            reason: "gone\nfishing".into(),
        }
    }

    fn ctx() -> EvictContext {
        EvictContext {
            online: true,
            window_secs: Some(100),
            idle_secs: 150,
            held_or_paused: false,
            evictions_today: 0,
            evict_rate: 5,
            since_reclaim_secs: None,
            in_ci: false,
        }
    }

    // frob:tests check_evictable
    #[test]
    fn idle_claim_is_evictable_and_each_precondition_refuses() {
        assert_eq!(check_evictable(&ctx()), Ok(()));
        let cases = [
            (
                EvictContext {
                    online: false,
                    ..ctx()
                },
                EvictRefusal::Offline,
            ),
            (
                EvictContext {
                    window_secs: Some(0),
                    ..ctx()
                },
                EvictRefusal::NoWindow,
            ),
            (
                EvictContext {
                    window_secs: None,
                    ..ctx()
                },
                EvictRefusal::NoWindow,
            ),
            (
                EvictContext {
                    idle_secs: 99,
                    ..ctx()
                },
                EvictRefusal::NotIdle,
            ),
            (
                EvictContext {
                    held_or_paused: true,
                    ..ctx()
                },
                EvictRefusal::Held,
            ),
            (
                EvictContext {
                    evictions_today: 5,
                    ..ctx()
                },
                EvictRefusal::RateLimited,
            ),
            (
                EvictContext {
                    since_reclaim_secs: Some(10),
                    ..ctx()
                },
                EvictRefusal::FlapGuard,
            ),
            (
                EvictContext {
                    in_ci: true,
                    ..ctx()
                },
                EvictRefusal::InCi,
            ),
        ];
        for (c, want) in cases {
            assert_eq!(check_evictable(&c), Err(want), "{want:?}");
        }
        let ok = EvictContext {
            since_reclaim_secs: Some(100),
            ..ctx()
        };
        assert_eq!(check_evictable(&ok), Ok(()));
    }

    // frob:tests EvictRefusal.describe
    #[test]
    fn every_refusal_has_a_distinct_code() {
        let all = [
            EvictRefusal::Offline,
            EvictRefusal::NoWindow,
            EvictRefusal::NotIdle,
            EvictRefusal::Held,
            EvictRefusal::RateLimited,
            EvictRefusal::FlapGuard,
            EvictRefusal::InCi,
        ];
        let codes: std::collections::BTreeSet<_> = all.iter().map(|r| r.describe().0).collect();
        assert_eq!(codes.len(), all.len());
    }

    // frob:tests parked_name
    // frob:tests parked_seq
    // frob:tests next_parked_seq
    // frob:tests newest_parked
    #[test]
    fn parked_names_sequence_per_handle() {
        let refs = vec![
            "refs/heads/parked/ABC-1".to_owned(),
            "refs/heads/parked/ABC-2".to_owned(),
            "refs/heads/parked/ABCD-9".to_owned(),
            "refs/heads/parked/XYZ-4".to_owned(),
        ];
        assert_eq!(parked_name("ABC", 3), "parked/ABC-3");
        assert_eq!(parked_seq("parked/ABC-7", "ABC"), Some(7));
        assert_eq!(parked_seq("parked/ABCD-9", "ABC"), None);
        assert_eq!(next_parked_seq(&refs, "ABC"), 3);
        assert_eq!(next_parked_seq(&refs, "NEW"), 1);
        assert_eq!(newest_parked(&refs, "ABC"), Some("refs/heads/parked/ABC-2"));
        assert_eq!(newest_parked(&refs, "NEW"), None);
    }

    // frob:tests park_message
    // frob:tests parse_park_message
    #[test]
    fn park_message_round_trips() {
        let msg = park_message(&req());
        let rec = parse_park_message(&msg).expect("parses");
        assert_eq!(rec.handle, "ABC");
        assert_eq!(rec.evictor, "bob");
        assert_eq!(rec.holder, "ann");
        assert_eq!(rec.observed, "deadbeef");
        assert_eq!(rec.idle_secs, 276_480);
        assert_eq!(rec.window_secs, 259_200);
        assert_eq!(rec.reason, "gone fishing");
        assert_eq!(parse_park_message("just a commit"), None);
    }

    // frob:tests needs_completion
    #[test]
    fn crash_between_delete_and_record_is_recognised() {
        let parked = vec!["refs/heads/parked/ABC-1".to_owned()];
        assert!(needs_completion(true, false, &parked, "ABC"));
        assert!(!needs_completion(true, true, &parked, "ABC"));
        assert!(!needs_completion(false, false, &parked, "ABC"));
        assert!(!needs_completion(true, false, &parked, "OTHER"));
        assert!(!needs_completion(true, false, &[], "ABC"));
    }

    // frob:tests holder_return
    #[test]
    fn returning_holder_pushes_to_the_next_parked_ref() {
        let rec = parse_park_message(&park_message(&req())).expect("parses");
        let parked = vec!["refs/heads/parked/ABC-1".to_owned()];
        let r = holder_return(&rec, &parked, "2026-10-20");
        assert_eq!(r.push_to, "parked/ABC-2");
        assert!(
            r.warning.starts_with(
                "W-CLAIM-EVICTED: ~ABC evicted by bob on 2026-10-20 after 3.2 idle days"
            )
        );
        assert!(r.warning.ends_with("frob work ~ABC --reclaim"));
    }

    // frob:tests reclaim_plan
    #[test]
    fn reclaim_restores_from_newest_unless_someone_holds_it() {
        let parked = vec![
            "refs/heads/parked/ABC-1".to_owned(),
            "refs/heads/parked/ABC-2".to_owned(),
        ];
        assert_eq!(
            reclaim_plan(None, &parked, "ABC"),
            Ok("parked/ABC-2".to_owned())
        );
        assert_eq!(
            reclaim_plan(Some("carl"), &parked, "ABC"),
            Err(ReclaimRefusal::HeldBy("carl".to_owned()))
        );
        assert_eq!(
            reclaim_plan(None, &[], "ABC"),
            Err(ReclaimRefusal::NothingParked)
        );
    }
}
