//! The `[release]` table of `frob.toml`.

// frob:ticket 01M4069WYA9D1EGVEBC4PT3KZB
use gob_config::ConfigTable;

/// Release policy knobs read by `frob release status` and the `release cut` readiness gate.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "release", materialize)]
pub struct ReleaseConfig {
    /// When true, a CI result that cannot be read (no checks, `gh` missing or unauthenticated, no network, non-GitHub remote) blocks the release like a red one; false reports it as Unresolved only. Unknown is never treated as green.
    #[config(default = true, enforcement)]
    pub require_ci: bool,
}
