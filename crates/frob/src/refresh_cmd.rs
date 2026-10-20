//! The `refresh` verb: probe the configured remote for freshness and report the cached answer (`distributed-tickets.md` section 5).
//!
//! DT05 covers the probe and its state only; fetch, integrate and publish belong to the
//! follow-up ticket. `--status` reads the cache and never touches the network.

// frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2

use frob_ledger::RefMode;
use frob_ledger::refresh::{ProbeClass, ProbeMode, ProbeOutcome, ProbeReport, RefreshState, probe};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use gob_diagnostics::{Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// `refresh` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RefreshArgs {
    #[arg(
        long,
        help = "Print the cached freshness line; no network, no state change"
    )]
    status: bool,
    #[arg(long, help = "Probe even inside the ttl or a failure backoff window")]
    force: bool,
}

/// Probe the remote for freshness (bounded, never prompts) or, with `--status`, print the cached one-line freshness.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "refresh",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Refresh {
    status: bool,
    force: bool,
}

/// What `frob refresh` reports.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RefreshReport {
    /// The one-line freshness, e.g. `frob:ok` or `frob:2h-stale`.
    pub status: String,
    /// `ok`, `offline`, `timeout`, `auth`, `rate`, `no-base` or `unknown`; `local-only` without a remote.
    pub class: String,
    /// `probed`, `cached`, `busy`, `local-only` or `status`.
    pub outcome: String,
    /// Whether any remote ref moved since the previous probe.
    pub changed: bool,
    /// The remote consulted.
    pub remote: String,
    /// The base branch required on it.
    pub base: String,
    /// Problem text, empty when ok.
    pub detail: String,
}

impl Command for Refresh {
    type Data = RefreshReport;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<RefreshArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RefreshArgs>(m)?;
        Ok(Self {
            status: a.status,
            force: a.force,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<RefreshReport> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let now = ctx.clock.now().unix();
        let base = cfg.tickets.r#ref.clone();
        if self.status {
            let state = RefreshState::load(repo.common_dir());
            tracing::debug!(class = ?state.class, "refresh --status from cache");
            let status = if repo.remote_url(&cfg.sync.remote).is_none() {
                "frob:local-only".to_owned()
            } else {
                state.status_line(now, cfg.sync.ttl_secs)
            };
            return Ok(render(report(&state, status, "status", false)));
        }
        let ledger = cfg.ledger();
        let ledger_branch = (ledger.mode == RefMode::Orphan).then_some(ledger.branch.as_str());
        let mode = if self.force {
            ProbeMode::Force
        } else {
            ProbeMode::Explicit
        };
        let done = probe(&repo, &cfg.sync, &base, ledger_branch, now, mode).map_err(|e| {
            CliError::from(Refusal::new(
                "E-SYNC-PROBE",
                RefusalClass::DomainNegative,
                e.to_string(),
            ))
        })?;
        tracing::info!(outcome = ?done.outcome, class = ?done.state.class, "refresh");
        finish(&done, now, cfg.sync.ttl_secs)
    }
}

/// Build the report from a state and a rendered status line.
fn report(state: &RefreshState, status: String, outcome: &str, changed: bool) -> RefreshReport {
    RefreshReport {
        status,
        class: format!("{:?}", state.class).to_lowercase(),
        outcome: outcome.to_owned(),
        changed,
        remote: state.remote.clone(),
        base: state.base.clone(),
        detail: state.detail.clone(),
    }
}

/// The payload whose rendered text is the one status line.
fn render(r: RefreshReport) -> Payload<RefreshReport> {
    let text = r.status.clone();
    Payload::new(r).with_rendered(vec![text])
}

/// Map a probe result to the exit contract: 0 ok, 3 retryable, 1 needs action.
fn finish(done: &ProbeReport, now: i64, ttl: u32) -> CliOutcome<RefreshReport> {
    let (name, changed) = match &done.outcome {
        ProbeOutcome::Probed { changed } => ("probed", *changed),
        ProbeOutcome::Cached => ("cached", false),
        ProbeOutcome::Busy => ("busy", false),
        ProbeOutcome::LocalOnly => ("local-only", false),
    };
    let status = if done.outcome == ProbeOutcome::LocalOnly {
        "frob:local-only".to_owned()
    } else {
        done.state.status_line(now, ttl)
    };
    let mut rep = report(&done.state, status, name, changed);
    if done.outcome == ProbeOutcome::LocalOnly {
        "local-only".clone_into(&mut rep.class);
    }
    let Some(code) = done.state.class.code() else {
        return Ok(render(rep));
    };
    if done.outcome == ProbeOutcome::Busy {
        return Ok(render(rep));
    }
    let class = if done.state.class == ProbeClass::NoBase {
        RefusalClass::DomainNegative
    } else {
        RefusalClass::GuardRetryByWaiting
    };
    let message = format!("{}: {}", rep.status, rep.detail);
    let refusal = Refusal::new(code, class, message);
    let refusal = match done.state.class {
        ProbeClass::Auth => refusal.with_remedy("run git fetch origin to re-authenticate"),
        ProbeClass::NoBase => {
            refusal.with_remedy("set [tickets] ref to a branch the remote has, or push it")
        }
        _ => refusal,
    };
    Err(refusal.into())
}

/// Register the `refresh` verb.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<Refresh>()
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
    fn done(class: ProbeClass, outcome: ProbeOutcome) -> ProbeReport {
        ProbeReport {
            outcome,
            state: RefreshState {
                class,
                probed_at: 100,
                ..RefreshState::default()
            },
        }
    }

    fn exit_of(r: &CliOutcome<RefreshReport>) -> Option<(String, RefusalClass)> {
        match r {
            Err(CliError::Refusal(x)) => Some((x.code.clone(), x.class)),
            _ => None,
        }
    }

    #[test]
    fn ok_and_busy_and_local_only_exit_zero() {
        assert!(
            finish(
                &done(ProbeClass::Ok, ProbeOutcome::Probed { changed: true }),
                100,
                300
            )
            .is_ok()
        );
        assert!(finish(&done(ProbeClass::Offline, ProbeOutcome::Busy), 100, 300).is_ok());
        let lo = finish(
            &done(ProbeClass::Unknown, ProbeOutcome::LocalOnly),
            100,
            300,
        )
        .expect("ok");
        assert_eq!(lo.data.status, "frob:local-only");
        assert_eq!(lo.data.class, "local-only");
    }

    #[test]
    fn retryable_classes_exit_three_and_no_base_exits_one() {
        for (c, code) in [
            (ProbeClass::Offline, "W-SYNC-OFFLINE"),
            (ProbeClass::Timeout, "W-SYNC-TIMEOUT"),
            (ProbeClass::Auth, "W-SYNC-AUTH"),
            (ProbeClass::Rate, "W-SYNC-RATE"),
        ] {
            let r = finish(&done(c, ProbeOutcome::Probed { changed: false }), 100, 300);
            assert_eq!(
                exit_of(&r),
                Some((code.to_owned(), RefusalClass::GuardRetryByWaiting))
            );
        }
        let r = finish(
            &done(ProbeClass::NoBase, ProbeOutcome::Probed { changed: false }),
            100,
            300,
        );
        assert_eq!(
            exit_of(&r),
            Some(("E-SYNC-NO-BASE".to_owned(), RefusalClass::DomainNegative))
        );
    }
}
