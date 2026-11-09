//! `frob trust`: the interactive trust review (security.md 2.3).
//!
//! The verb takes no arguments and no flags: there is no `--yes`, no `--all` and no scope flag, so
//! nothing can pre-decide the answer. It refuses (exit 3) unless stdin and stdout are terminals and
//! no agent marker is set, and the refusal never names a pack or prints a command line a script
//! could act on; the envelope carries `requires_human = true`.

// frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z

use crate::pretty::PrettyExt;
use std::collections::BTreeMap;
use std::io::IsTerminal;
use std::path::Path;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_diagnostics::RemedyCommand;
use gob_git::Repo;
use gob_trust::prompt::{Delta, EffectLine, Presence, ReviewFacts, presence};
use gob_trust::{MachineKey, RepoIdentity, TrustStore, Verdict, default_store_path};
use schemars::JsonSchema;
use serde::Serialize;

/// Refusal code when the review cannot run in this session.
const CODE_NEEDS_HUMAN: &str = "E-TRUST-NEEDS-HUMAN";

/// Output of `frob trust`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrustData {
    /// Packs the person approved in this session.
    pub approved: Vec<String>,
    /// Packs the person denied in this session.
    pub denied: Vec<String>,
}

/// Review untrusted packs interactively; needs a terminal and a person, and takes no flags.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(verb = "trust", product = "frob", exits(ok, refused, usage, internal))]
pub struct Trust;

/// The refusal for a session without a person, deliberately free of pack names and commands.
fn needs_human(why: Presence) -> Refusal {
    let message = match why {
        Presence::Agent => {
            "trust is a review a person performs at a terminal; stop and tell the user a pack is untrusted"
        }
        _ => "trust is a review a person performs at a terminal",
    };
    Refusal::new(CODE_NEEDS_HUMAN, RefusalClass::GuardNeedsAction, message)
        .with_command(RemedyCommand::new("frob", "trust"))
        .requiring_human()
}

/// Run the review gate for the given session facts; `Ok` only when a person may be present.
///
/// # Errors
/// `E-TRUST-NEEDS-HUMAN` (exit 3, `requires_human`) off a terminal or under an agent marker.
pub fn gate(
    stdin_tty: bool,
    stdout_tty: bool,
    env: impl Fn(&str) -> Option<String>,
) -> Result<(), Refusal> {
    match presence(stdin_tty, stdout_tty, env) {
        Presence::Human => Ok(()),
        other => {
            tracing::warn!(?other, "trust refused: no person at a terminal");
            Err(needs_human(other))
        }
    }
}

/// The pack lock at the repository root (the file `frob check --trust-from` reads).
const LOCK_FILE: &str = "frob.packs.lock";

/// Shown where the host cannot derive a fact (the author of the last commit touching a pack).
const UNKNOWN: &str = "unknown";

/// The lock fields the review needs; the rest of the lock is ignored.
#[derive(Debug, serde::Deserialize)]
struct LockDoc {
    #[serde(default)]
    pack: Vec<LockEntry>,
}

/// One pinned pack as the lock records it.
#[derive(Debug, serde::Deserialize)]
struct LockEntry {
    name: String,
    tree: String,
    #[serde(default)]
    effects: BTreeMap<String, Vec<String>>,
}

/// The review facts for every pack in `lock_text` that `is_trusted` does not vouch for (by tree digest).
///
/// A pack never trusted before has no prior effect set, so every effect it requests is a widening.
///
/// # Errors
/// The TOML error text when `lock_text` is not a pack lock.
fn awaiting_review(
    lock_text: &str,
    is_trusted: impl Fn(&str) -> bool,
) -> Result<Vec<ReviewFacts>, String> {
    let doc: LockDoc = toml::from_str(lock_text).map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    for entry in doc.pack {
        if is_trusted(&entry.tree) {
            tracing::debug!(pack = %entry.name, "pack already trusted; not pending");
            continue;
        }
        let subprocess = entry.effects.contains_key("subprocess");
        let effects = entry
            .effects
            .iter()
            .flat_map(|(family, items)| {
                items.iter().map(move |i| EffectLine {
                    effect: format!("{family} {i}"),
                    delta: Delta::Added,
                })
            })
            .collect();
        tracing::info!(pack = %entry.name, "pack awaits review");
        out.push(ReviewFacts {
            pack: entry.name,
            tree_digest: entry.tree,
            effects,
            binaries: Vec::new(),
            on_protected_branch: false,
            reproduced: false,
            signed: false,
            last_author: UNKNOWN.to_owned(),
            subprocess,
        });
    }
    Ok(out)
}

/// The id of the repository's first root commit, or empty when it cannot be read.
fn root_commit(root: &Path) -> String {
    let spec = gob_exec::Spec {
        program: gob_exec::Program::Git,
        args: ["rev-list", "--max-parents=0", "HEAD"]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_owned()),
        env: Vec::new(),
        timeout: std::time::Duration::from_secs(10),
        capture: true,
    };
    gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
        .run(&spec)
        .ok()
        .and_then(|o| o.stdout.lines().min().map(str::to_owned))
        .unwrap_or_default()
}

/// The identity of the repository rooted at `root`, as the trust store keys its grants.
fn identity_of(repo: &Repo, root: &Path) -> RepoIdentity {
    RepoIdentity {
        root: gob_fs::canonical(root).unwrap_or_else(|_| root.to_path_buf()),
        root_commit: root_commit(root),
        remote_url: Repo::remote_url(repo, "origin").unwrap_or_default(),
    }
}

/// The text of the repository's pack lock, or `None` when it has none.
///
/// # Errors
/// An internal [`CliError`] when the lock exists but cannot be read.
fn read_lock(root: &Path) -> Result<Option<String>, CliError> {
    match std::fs::read_to_string(root.join(LOCK_FILE)) {
        Ok(t) => Ok(Some(t)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::info!(lock = LOCK_FILE, "no pack lock; nothing awaits review");
            Ok(None)
        }
        Err(e) => Err(CliError::internal(e)),
    }
}

/// The packs awaiting review: those in the repository's pack lock with no live trust-store grant.
///
/// A missing lock means no pack awaits review.
///
/// # Errors
/// An internal [`CliError`] when the lock, the machine key or the trust store cannot be read.
fn pending(cwd: &Path, clock: &dyn gob_time::Clock) -> Result<Vec<ReviewFacts>, CliError> {
    let (repo, root) = crate::workspace::Located::discover(cwd).into_repo()?;
    match read_lock(&root)? {
        Some(text) => ungranted(&text, &repo, &root, clock),
        None => Ok(Vec::new()),
    }
}

/// The packs in `text` (the lock) that the machine's trust store holds no live grant for.
///
/// # Errors
/// An internal [`CliError`] when the machine key, the trust store or the lock text cannot be read.
fn ungranted(
    text: &str,
    repo: &Repo,
    root: &Path,
    clock: &dyn gob_time::Clock,
) -> Result<Vec<ReviewFacts>, CliError> {
    let key = MachineKey::load_or_create().map_err(CliError::internal)?;
    let store_path = default_store_path().map_err(CliError::internal)?;
    let store = TrustStore::open(&store_path, key).map_err(CliError::internal)?;
    let identity = identity_of(repo, root);
    let now = u64::try_from(clock.now().unix()).unwrap_or(0);
    awaiting_review(text, |tree| {
        matches!(store.consult(&identity, tree, now), Verdict::Trusted(_))
    })
    .map_err(|why| CliError::internal(std::io::Error::other(format!("{LOCK_FILE}: {why}"))))
}

impl Command for Trust {
    type Data = TrustData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<TrustData> {
        gate(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |k| std::env::var(k).ok(),
        )?;
        let (mut approved, mut denied) = (Vec::new(), Vec::new());
        for facts in pending(&ctx.cwd, &gob_time::SystemClock)? {
            let decision = gob_trust::prompt::review(
                &facts,
                &mut std::io::stdin().lock(),
                // frob:accept LOG001 because="the interactive trust review is the command's primary output"
                &mut std::io::stdout().lock(),
            )
            .map_err(CliError::internal)?;
            match decision {
                gob_trust::prompt::Decision::Approve => approved.push(facts.pack),
                gob_trust::prompt::Decision::Deny => denied.push(facts.pack),
            }
        }
        tracing::info!(
            approved = approved.len(),
            denied = denied.len(),
            "trust session done"
        );
        let rows = if approved.is_empty() && denied.is_empty() {
            vec!["no pack awaits review".to_owned()]
        } else {
            Vec::new()
        };
        Ok(Payload::new(TrustData { approved, denied }).with_pretty(rows))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const LOCK: &str = r#"
lock_version = 1
digest_scheme = 1

[[pack]]
name = "alpha"
version = "1.0.0"
tree = "blake3:aa"
[pack.effects]
subprocess = ["git"]

[[pack]]
name = "beta"
version = "1.0.0"
tree = "blake3:bb"
"#;

    // frob:tests awaiting_review
    #[test]
    fn untrusted_packs_are_pending_with_widening_effects() {
        let got = awaiting_review(LOCK, |_| false).unwrap();
        assert_eq!(got.len(), 2);
        assert_eq!(got[0].pack, "alpha");
        assert!(got[0].subprocess && got[0].widens());
        assert_eq!(got[0].effects[0].effect, "subprocess git");
        assert!(!got[1].subprocess && got[1].effects.is_empty());
    }

    // frob:tests awaiting_review
    #[test]
    fn trusted_trees_are_not_pending() {
        let got = awaiting_review(LOCK, |t| t == "blake3:aa").unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].pack, "beta");
    }

    // frob:tests awaiting_review
    #[test]
    fn malformed_lock_is_an_error() {
        assert!(awaiting_review("pack = 3", |_| false).is_err());
    }
}
