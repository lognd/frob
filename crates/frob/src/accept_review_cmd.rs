//! `frob accept-review RULE PATH`: a second identity reviews a `frob:accept` on an Error-severity rule.
//!
//! The review is recorded as an Approved `[[review]]` row in `frob.lock` under the subject
//! `accept:<path>:<RULE>` and committed on the current branch. It is an audit trail, not an
//! authorization control: the reviewer is the git identity, which anyone can set. The verb refuses
//! when that identity is the one that last changed the file, unless `--owner` names the reviewer as
//! an owner (`[exceptions] owners` is not yet read from config).

// frob:ticket R8NFWKA

use std::collections::BTreeMap;
use std::time::Duration;

use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_git::{CommitOptions, RelPath};
use gob_lock::{LockFile, ReviewEntry, ReviewVerdict};
use gob_rules::RuleId;
use schemars::JsonSchema;
use serde::Serialize;

use crate::pretty::PrettyExt;
use crate::workspace::Located;

/// The lock subject a review of the accept of `rule` in `path` is recorded under.
#[must_use]
pub fn subject(path: &str, rule: &str) -> String {
    format!("accept:{path}:{rule}")
}

/// Why a review was refused.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SelfReview {
    /// The reviewer is the identity that last changed the accepting file.
    SameIdentity(String),
}

/// Pure check: a reviewer must differ from the accept's author unless an owner.
///
/// `author` is `None` when the file has no history, which never blocks a review.
///
/// # Errors
/// [`SelfReview::SameIdentity`] when `reviewer` equals `author` and `owner` is false.
pub fn check_second_identity(
    author: Option<&str>,
    reviewer: &str,
    owner: bool,
) -> Result<(), SelfReview> {
    match author {
        Some(a) if !owner && a.trim().eq_ignore_ascii_case(reviewer.trim()) => {
            Err(SelfReview::SameIdentity(a.to_owned()))
        }
        _ => Ok(()),
    }
}

/// Record an Approved review of `subject` into `lock`; replaces an earlier review of it.
pub fn record_review(
    lock: &mut LockFile,
    subject: &str,
    digest: &str,
    reviewer: &str,
    at: &str,
    note: Option<&str>,
) {
    lock.reviews.insert(
        subject.to_owned(),
        ReviewEntry {
            digest: digest.to_owned(),
            verdict: ReviewVerdict::Approved,
            reviewer: reviewer.to_owned(),
            at: at.to_owned(),
            note: note.map(str::to_owned),
            render: None,
            non_interactive: true,
            inputs: BTreeMap::new(),
        },
    );
}

/// Output of `frob accept-review`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AcceptReviewData {
    /// The lock subject reviewed.
    pub subject: String,
    /// The reviewing identity.
    pub reviewer: String,
    /// The commit that recorded the review.
    pub commit: Option<String>,
}

/// The flags of `accept-review`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AcceptReviewArgs {
    #[arg(
        required = true,
        value_name = "RULE",
        help = "Rule id the accept covers"
    )]
    rule: String,
    #[arg(
        required = true,
        value_name = "PATH",
        help = "Repo-relative file holding the frob:accept"
    )]
    path: String,
    #[arg(long, value_name = "TEXT", help = "Why the accept is approved")]
    note: Option<String>,
    #[arg(long, help = "Review as an owner, who may review their own accept")]
    owner: bool,
}

/// Record a second-identity review of the `frob:accept` of `RULE` in `PATH`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "accept-review",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct AcceptReview {
    rule: String,
    path: String,
    note: Option<String>,
    owner: bool,
}

/// `Name <email>` of whoever last committed `path`, when it has history.
fn last_author(root: &std::path::Path, path: &str) -> Option<String> {
    let spec = Spec {
        program: Program::Git,
        args: ["log", "-1", "--format=%an <%ae>", "--", path]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).ok()?;
    let s = out.stdout_raw.trim().to_owned();
    (matches!(out.status, ExecOutcome::Exited(0)) && !s.is_empty()).then_some(s)
}

impl Command for AcceptReview {
    type Data = AcceptReviewData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<AcceptReviewArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AcceptReviewArgs>(m)?;
        Ok(Self {
            rule: a.rule,
            path: a.path,
            note: a.note,
            owner: a.owner,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AcceptReviewData> {
        let rule: RuleId = self
            .rule
            .parse()
            .map_err(|e| CliError::Usage(format!("`{}` is not a rule id: {e}", self.rule)))?;
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let bytes = std::fs::read(root.join(&self.path))
            .map_err(|e| CliError::Usage(format!("cannot read `{}`: {e}", self.path)))?;
        let text = String::from_utf8_lossy(&bytes);
        if !text.contains("frob:accept") || !text.contains(&self.rule) {
            return Err(CliError::Usage(format!(
                "`{}` has no `frob:accept` naming {rule}",
                self.path
            )));
        }
        let (name, email) = repo.config_user().ok_or_else(|| {
            CliError::from(Refusal::new(
                "E-GIT-IDENTITY",
                RefusalClass::GuardNeedsAction,
                "no reviewer identity; set user.name and user.email in git config".to_owned(),
            ))
        })?;
        let reviewer = format!("{name} <{email}>");
        if let Err(SelfReview::SameIdentity(a)) = check_second_identity(
            last_author(&root, &self.path).as_deref(),
            &reviewer,
            self.owner,
        ) {
            return Err(Refusal::new(
                "E-ACCEPT-SELF-REVIEW",
                RefusalClass::GuardNeedsAction,
                format!(
                    "{a} last changed `{}`; a second identity must review it (or pass --owner)",
                    self.path
                ),
            )
            .into());
        }
        let lock_name = gob_lock::file_name("frob");
        let lock_path = root.join(&lock_name);
        let mut lock = if lock_path.exists() {
            LockFile::load(&lock_path).map_err(CliError::internal)?
        } else {
            LockFile::default()
        };
        let subj = subject(&self.path, &rule.to_string());
        let digest = blake3::hash(&bytes).to_hex().to_string();
        record_review(
            &mut lock,
            &subj,
            &digest,
            &reviewer,
            &ctx.clock.now().to_string(),
            self.note.as_deref(),
        );
        let branch = repo
            .current_branch()
            .map_err(CliError::internal)?
            .ok_or_else(|| CliError::Usage("HEAD is detached; check out a branch".to_owned()))?;
        let toml = lock.to_toml().map_err(CliError::internal)?;
        let done = repo
            .commit_paths(
                &branch,
                &[(
                    RelPath::new(lock_name).map_err(CliError::internal)?,
                    Some(toml.into_bytes()),
                )],
                &format!("review: accept of {rule} in {}", self.path),
                &CommitOptions::default(),
            )
            .map_err(CliError::internal)?;
        let rows = vec![format!("reviewed {subj} as {reviewer}")];
        Ok(Payload::new(AcceptReviewData {
            subject: subj,
            reviewer,
            commit: Some(done.oid.to_string()),
        })
        .with_pretty(rows))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/accept_review_cmd.rs::check_second_identity
    #[test]
    fn the_author_cannot_review_their_own_accept_unless_owner() {
        let me = "A <a@x>";
        assert!(check_second_identity(Some(me), me, false).is_err());
        assert!(check_second_identity(Some(me), me, true).is_ok());
        assert!(check_second_identity(Some(me), "B <b@x>", false).is_ok());
        assert!(check_second_identity(None, me, false).is_ok());
    }

    // frob:tests crates/frob/src/accept_review_cmd.rs::record_review
    #[test]
    fn a_review_is_keyed_by_subject_and_replaced() {
        let mut lock = LockFile::default();
        let s = subject("a.rs", "DOC001");
        record_review(&mut lock, &s, "d1", "B <b@x>", "t1", Some("ok"));
        record_review(&mut lock, &s, "d2", "C <c@x>", "t2", None);
        assert_eq!(lock.reviews.len(), 1);
        assert_eq!(lock.reviews[&s].reviewer, "C <c@x>");
        assert_eq!(lock.reviews[&s].verdict, ReviewVerdict::Approved);
    }
}
