//! Claim activity observation: what counts as activity on a claim and when THIS clone first saw it (`distributed-tickets.md` sections 4.2 and 4.3).
//!
//! Remote timestamps are never compared. Each clone records, per claim, the
//! latest hard and soft activity key (a commit oid or an event ULID) and the
//! LOCAL time it first observed that key, in
//! `<common_dir>/frob/claims-observed.toml`. Idle time is local now minus the
//! newest first-seen instant, clamped at zero when the local clock jumps back.

// frob:ticket 01M5CW04TYF2SQ101BQB1BGNPJ

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use gob_git::Repo;
use serde::{Deserialize, Serialize};

/// File name of the observation state under `<common_dir>/frob/`.
pub const OBSERVED_FILE: &str = "claims-observed.toml";

/// Bot identity patterns used when `[claims] bot_identities` is not configured.
pub const DEFAULT_BOT_IDENTITIES: &[&str] = &["*[bot]", "github-actions*"];

/// Most commits examined per observation, so a force push cannot make the walk unbounded.
const WALK_LIMIT: usize = 500;

/// How strongly an observation keeps a claim alive.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ActivityKind {
    /// Real work: a non-empty human commit, or an evidence event by the holder.
    Hard,
    /// A heartbeat that is capped by `soft_max_windows`: empty commit, comment, touch.
    Soft,
}

/// The facts about one commit that decide its [`ActivityKind`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitFacts {
    /// Author name.
    pub author_name: String,
    /// Author email.
    pub author_email: String,
    /// The commit changes nothing against its first parent.
    pub empty: bool,
    /// The message carries a `Frob-Sync` trailer (a base or refresh merge).
    pub frob_sync: bool,
}

/// One `(key, first-seen)` observation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Seen {
    /// Commit oid or event ULID.
    pub key: String,
    /// Unix seconds, local clock, at which this clone first saw `key`.
    pub first_seen: i64,
}

/// What this clone has observed of one claim.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClaimObservation {
    /// The remote branch tip last examined, so the next walk covers only new commits.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tip: Option<String>,
    /// Latest hard activity.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hard: Option<Seen>,
    /// Latest soft activity.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub soft: Option<Seen>,
}

/// The whole `claims-observed.toml`: observations keyed by claim (the ticket ULID).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObservedClaims {
    /// Per-claim observations.
    #[serde(default)]
    pub claims: BTreeMap<String, ClaimObservation>,
}

/// Where the observation file lives for a repository.
#[must_use]
pub fn observed_path(repo: &Repo) -> PathBuf {
    repo.common_dir().join("frob").join(OBSERVED_FILE)
}

/// Whether `pattern` (with `*` wildcards, case-insensitive) matches `text`.
fn glob_match(pattern: &str, text: &str) -> bool {
    let (p, t) = (pattern.to_lowercase(), text.to_lowercase());
    let parts: Vec<&str> = p.split('*').collect();
    let (first, rest) = parts.split_first().map_or(("", &[][..]), |(f, r)| (*f, r));
    let Some(mut tail) = t.strip_prefix(first) else {
        return false;
    };
    let Some((last, middle)) = rest.split_last() else {
        return tail.is_empty();
    };
    for part in middle {
        match tail.find(part) {
            Some(i) => tail = &tail[i + part.len()..],
            None => return false,
        }
    }
    tail.ends_with(last)
}

/// Whether the author name or email matches any bot pattern.
#[must_use]
pub fn is_bot(name: &str, email: &str, patterns: &[String]) -> bool {
    patterns
        .iter()
        .any(|p| glob_match(p, name) || glob_match(p, email))
}

/// The activity one commit counts as, or `None` for bot, CI and sync commits.
#[must_use]
pub fn classify_commit(facts: &CommitFacts, bots: &[String]) -> Option<ActivityKind> {
    if facts.frob_sync || is_bot(&facts.author_name, &facts.author_email, bots) {
        return None;
    }
    Some(if facts.empty {
        ActivityKind::Soft
    } else {
        ActivityKind::Hard
    })
}

/// The strongest activity among `commits`, `None` when none counts.
#[must_use]
pub fn classify_commits(commits: &[CommitFacts], bots: &[String]) -> Option<ActivityKind> {
    commits
        .iter()
        .filter_map(|c| classify_commit(c, bots))
        .reduce(|a, b| if a == ActivityKind::Hard { a } else { b })
}

/// The activity a ledger event counts as when the holder wrote it; events by others count as nothing.
#[must_use]
pub fn classify_event(event_type: &str, by_holder: bool) -> Option<ActivityKind> {
    if !by_holder {
        return None;
    }
    match event_type {
        "evidence" => Some(ActivityKind::Hard),
        "comment" | "field" | "link" | "transition" => Some(ActivityKind::Soft),
        _ => None,
    }
}

impl ObservedClaims {
    /// Read the state at `path`; a missing or unreadable file is an empty state (a fresh clone).
    #[must_use]
    pub fn load(path: &Path) -> Self {
        let Ok(text) = std::fs::read_to_string(path) else {
            tracing::debug!(path = %gob_path::Shown::of(path), "no claim observations yet");
            return Self::default();
        };
        toml::from_str(&text).unwrap_or_else(|e| {
            tracing::warn!(path = %gob_path::Shown::of(path), error = %e, "claim observations unreadable; starting empty");
            Self::default()
        })
    }

    /// Write the state to `path` atomically.
    ///
    /// # Errors
    /// The I/O error text when the file cannot be written.
    pub fn save(&self, path: &Path) -> Result<(), String> {
        let text = toml::to_string_pretty(self).map_err(|e| e.to_string())?;
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
        }
        gob_fs::write_atomic(path, text.as_bytes()).map_err(|e| e.to_string())
    }

    /// Record `key` as `kind` activity on `claim` seen at `now`; true when it was new to this clone.
    pub fn observe(&mut self, claim: &str, kind: ActivityKind, key: &str, now: i64) -> bool {
        let entry = self.claims.entry(claim.to_owned()).or_default();
        let slot = match kind {
            ActivityKind::Hard => &mut entry.hard,
            ActivityKind::Soft => &mut entry.soft,
        };
        if slot.as_ref().is_some_and(|s| s.key == key) {
            return false;
        }
        tracing::info!(claim, ?kind, key, "new claim activity observed");
        *slot = Some(Seen {
            key: key.to_owned(),
            first_seen: now,
        });
        true
    }

    /// Seconds since this clone last observed activity on `claim`; `None` when it never has.
    ///
    /// A clock that went backwards clamps to zero.
    #[must_use]
    pub fn idle_secs(&self, claim: &str, now: i64) -> Option<u64> {
        let c = self.claims.get(claim)?;
        let newest = [c.hard.as_ref(), c.soft.as_ref()]
            .into_iter()
            .flatten()
            .map(|s| s.first_seen)
            .max()?;
        Some(u64::try_from(now.saturating_sub(newest)).unwrap_or(0))
    }

    /// Fold the remote `tip` of `claim` into the state: classify the commits new since the last tip and record the strongest.
    ///
    /// An unchanged tip is no activity. A tip with no counting commit (all
    /// bot, sync or nothing new) updates the walk base only. Returns the kind
    /// recorded, if any.
    pub fn observe_tip(
        &mut self,
        claim: &str,
        tip: &str,
        commits: &[CommitFacts],
        bots: &[String],
        now: i64,
    ) -> Option<ActivityKind> {
        let last = self.claims.get(claim).and_then(|c| c.tip.clone());
        if last.as_deref() == Some(tip) {
            return None;
        }
        let kind = classify_commits(commits, bots);
        if let Some(k) = kind {
            self.observe(claim, k, tip, now);
        } else {
            tracing::debug!(claim, tip, "new tip carries no counting commit");
        }
        self.claims.entry(claim.to_owned()).or_default().tip = Some(tip.to_owned());
        kind
    }
}

/// The commits of `tip` not reachable from `since`, as [`CommitFacts`], newest first.
///
/// `since` that does not resolve locally (a force push, a fresh clone) falls
/// back to the whole history up to a limit, which errs toward counting activity.
///
/// # Errors
/// The failure text when git cannot list the commits.
pub fn commit_facts(
    repo: &Repo,
    tip: &str,
    since: Option<&str>,
) -> Result<Vec<CommitFacts>, String> {
    let mut args: Vec<String> = [
        "log",
        "--root",
        "--name-only",
        "--diff-merges=first-parent",
        "--format=%x1e%an%x1f%ae%x1f%(trailers:key=Frob-Sync,valueonly,separator=%x2c)%x1f",
        "-n",
    ]
    .iter()
    .map(|s| (*s).to_owned())
    .collect();
    args.push(WALK_LIMIT.to_string());
    args.push(tip.to_owned());
    if let Some(s) = since.filter(|s| repo.rev_parse(s).is_ok()) {
        args.push(format!("^{s}"));
    }
    let spec = Spec {
        program: Program::Git,
        args,
        cwd: repo.work_dir().map(Path::to_path_buf),
        env: Vec::new(),
        timeout: Duration::from_secs(60),
        capture: true,
    };
    let out = repo.runner().run(&spec).map_err(|e| e.to_string())?;
    if out.status != Outcome::Exited(0) {
        return Err(out.stderr.trim().to_owned());
    }
    Ok(parse_log(&out.stdout))
}

/// Parse the `git log` output of [`commit_facts`].
fn parse_log(text: &str) -> Vec<CommitFacts> {
    text.split('\u{1e}')
        .filter(|rec| !rec.trim().is_empty())
        .filter_map(|rec| {
            let mut f = rec.splitn(4, '\u{1f}');
            let (name, email, trailer, files) = (f.next()?, f.next()?, f.next()?, f.next()?);
            Some(CommitFacts {
                author_name: name.to_owned(),
                author_email: email.to_owned(),
                empty: files.trim().is_empty(),
                frob_sync: !trailer.trim().is_empty(),
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bots() -> Vec<String> {
        DEFAULT_BOT_IDENTITIES
            .iter()
            .map(|s| (*s).to_owned())
            .collect()
    }

    fn facts(name: &str, empty: bool, sync: bool) -> CommitFacts {
        CommitFacts {
            author_name: name.to_owned(),
            author_email: format!("{name}@example.com"),
            empty,
            frob_sync: sync,
        }
    }

    // frob:tests crates/frob-worktree/src/activity.rs::classify_commit
    #[test]
    fn human_commit_is_hard_empty_is_soft() {
        assert_eq!(
            classify_commit(&facts("ann", false, false), &bots()),
            Some(ActivityKind::Hard)
        );
        assert_eq!(
            classify_commit(&facts("ann", true, false), &bots()),
            Some(ActivityKind::Soft)
        );
    }

    // frob:tests crates/frob-worktree/src/activity.rs::classify_commit
    #[test]
    fn bot_and_sync_commits_count_for_nothing() {
        assert_eq!(
            classify_commit(&facts("dependabot[bot]", false, false), &bots()),
            None
        );
        assert_eq!(
            classify_commit(&facts("GitHub-Actions", false, false), &bots()),
            None
        );
        assert_eq!(classify_commit(&facts("ann", false, true), &bots()), None);
    }

    // frob:tests crates/frob-worktree/src/activity.rs::classify_commits
    #[test]
    fn strongest_commit_wins() {
        let cs = [
            facts("ann", true, false),
            facts("ann", false, false),
            facts("ci[bot]", false, false),
        ];
        assert_eq!(classify_commits(&cs, &bots()), Some(ActivityKind::Hard));
        assert_eq!(classify_commits(&cs[2..], &bots()), None);
    }

    // frob:tests crates/frob-worktree/src/activity.rs::classify_event
    #[test]
    fn events_count_only_for_the_holder() {
        assert_eq!(classify_event("evidence", true), Some(ActivityKind::Hard));
        assert_eq!(classify_event("comment", true), Some(ActivityKind::Soft));
        assert_eq!(classify_event("comment", false), None);
        assert_eq!(classify_event("lease", true), None);
    }

    // frob:tests crates/frob-worktree/src/activity.rs::ObservedClaims.observe
    #[test]
    fn same_key_keeps_its_first_seen_time() {
        let mut o = ObservedClaims::default();
        assert!(o.observe("T", ActivityKind::Hard, "a", 100));
        assert!(!o.observe("T", ActivityKind::Hard, "a", 500));
        assert_eq!(o.claims["T"].hard.as_ref().map(|s| s.first_seen), Some(100));
        assert!(o.observe("T", ActivityKind::Hard, "b", 600));
    }

    // frob:tests crates/frob-worktree/src/activity.rs::ObservedClaims.idle_secs
    #[test]
    fn idle_uses_local_first_seen_and_clamps() {
        let mut o = ObservedClaims::default();
        assert_eq!(o.idle_secs("T", 10), None);
        o.observe("T", ActivityKind::Hard, "a", 100);
        o.observe("T", ActivityKind::Soft, "n", 160);
        assert_eq!(o.idle_secs("T", 200), Some(40));
        assert_eq!(o.idle_secs("T", 50), Some(0));
    }

    // frob:tests crates/frob-worktree/src/activity.rs::ObservedClaims.observe_tip
    #[test]
    fn unchanged_or_uncounted_tip_is_not_activity() {
        let mut o = ObservedClaims::default();
        let work = [facts("ann", false, false)];
        assert_eq!(
            o.observe_tip("T", "t1", &work, &bots(), 10),
            Some(ActivityKind::Hard)
        );
        assert_eq!(o.observe_tip("T", "t1", &work, &bots(), 99), None);
        let sync = [facts("ann", false, true)];
        assert_eq!(o.observe_tip("T", "t2", &sync, &bots(), 120), None);
        assert_eq!(o.idle_secs("T", 130), Some(120));
        assert_eq!(o.claims["T"].tip.as_deref(), Some("t2"));
    }

    // frob:tests crates/frob-worktree/src/activity.rs::ObservedClaims.save
    #[test]
    fn state_round_trips_through_toml() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("frob").join(OBSERVED_FILE);
        let mut o = ObservedClaims::default();
        o.observe_tip("T", "t1", &[facts("ann", false, false)], &bots(), 7);
        o.save(&path).unwrap();
        assert_eq!(ObservedClaims::load(&path), o);
    }

    // frob:tests crates/frob-worktree/src/activity.rs::parse_log
    #[test]
    fn log_output_parses_into_facts() {
        let text = "\u{1e}ann\u{1f}a@x\u{1f}\u{1f}\n\nsrc/a.rs\n\u{1e}bob\u{1f}b@x\u{1f}base\u{1f}\n\u{1e}ci[bot]\u{1f}c@x\u{1f}\u{1f}\n\nf\n";
        let v = parse_log(text);
        assert_eq!(v.len(), 3);
        assert!(!v[0].empty && !v[0].frob_sync);
        assert!(v[1].empty && v[1].frob_sync);
        assert_eq!(classify_commits(&v, &bots()), Some(ActivityKind::Hard));
    }

    // frob:tests crates/frob-worktree/src/activity.rs::commit_facts
    #[test]
    fn commit_facts_reads_a_real_history() {
        let dir = tempfile::tempdir().unwrap();
        let repo = Repo::init(dir.path()).unwrap();
        let git = |args: &[&str]| {
            let mut full = vec!["-c", "user.name=ann", "-c", "user.email=a@x"];
            full.extend_from_slice(args);
            let spec = Spec {
                program: Program::Git,
                args: full.iter().map(|a| (*a).to_owned()).collect(),
                cwd: Some(dir.path().to_path_buf()),
                env: Vec::new(),
                timeout: Duration::from_secs(30),
                capture: true,
            };
            let out = repo.runner().run(&spec).unwrap();
            assert_eq!(out.status, Outcome::Exited(0), "{args:?}");
        };
        std::fs::write(dir.path().join("f"), "1").unwrap();
        git(&["add", "f"]);
        git(&["commit", "-q", "-m", "one"]);
        git(&["commit", "-q", "--allow-empty", "-m", "two"]);
        git(&[
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "sync\n\nFrob-Sync: base",
        ]);
        let v = commit_facts(&repo, "HEAD", None).unwrap();
        assert_eq!(v.len(), 3);
        assert!(v[0].frob_sync && v[0].empty);
        assert!(v[1].empty && !v[1].frob_sync);
        assert!(!v[2].empty);
        let since = commit_facts(&repo, "HEAD", Some("HEAD~2")).unwrap();
        assert_eq!(since.len(), 2);
    }
}
