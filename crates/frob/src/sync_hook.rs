//! CLI glue for the per-verb auto-refresh policy (`distributed-tickets.md` section 5.3).
//!
//! Read and ledger-write verbs call [`kick`] (a detached refresh, never network inline);
//! `ticket doable` calls [`foreground`] (a probe bounded by `foreground_budget`) and
//! reports its [`frob_ledger::sync_policy::notice`].

// frob:ticket 01M5CW04GHM970H5KR4EV5KK0X

use frob_ledger::RefMode;
use frob_ledger::refresh::RefreshState;
use frob_ledger::sync_policy::{
    KickOutcome, background_kick, foreground_probe, notice, sync_disabled,
};
use gob_cli::Context;
use gob_git::Repo;

use crate::config::FrobConfig;

/// Whether `exe` looks like the frob binary, so a test or embedding binary is never re-run as `refresh`.
fn is_frob_binary(exe: &std::path::Path) -> bool {
    exe.file_stem() == Some(std::ffi::OsStr::new("frob"))
}

/// Start a background refresh for a read or ledger-write verb when one is due.
pub(crate) fn kick(repo: &Repo, cfg: &FrobConfig, ctx: &Context) -> KickOutcome {
    let Ok(exe) = std::env::current_exe() else {
        return KickOutcome::Failed;
    };
    if !is_frob_binary(&exe) {
        tracing::debug!("not the frob binary; no background refresh");
        return KickOutcome::NotDue;
    }
    let out = background_kick(repo, &cfg.sync, &exe, ctx.clock.now().unix(), |k| {
        std::env::var(k).ok()
    });
    tracing::debug!(?out, "background refresh kick");
    out
}

/// Probe in the foreground within the budget and return the freshness notice for the (possibly cached) view.
pub(crate) fn foreground(repo: &Repo, cfg: &FrobConfig, ctx: &Context) -> Option<String> {
    if repo.remote_url(&cfg.sync.remote).is_none() || sync_disabled(|k| std::env::var(k).ok()) {
        return None;
    }
    let now = ctx.clock.now().unix();
    let ledger = cfg.ledger();
    let branch = (ledger.mode == RefMode::Orphan).then_some(ledger.branch.as_str());
    let base = cfg.tickets.r#ref.as_str();
    let state = match foreground_probe(repo, &cfg.sync, base, branch, now) {
        Ok(done) => done.state,
        Err(e) => {
            tracing::warn!(error = %e, "foreground probe failed; using the cache");
            RefreshState::load(repo.common_dir())
        }
    };
    notice(&state, now, &cfg.sync)
}
