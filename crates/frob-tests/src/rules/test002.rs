//! `TEST002`: the committed heavy-command profile is stale.

// frob:ticket 01M4P2N1XMDZAGS1EAZPR6WQMQ

use gob_rules::{Finding, RelayRule, RuleDecl, RuleId, rule};
use gob_text::FileInterner;

use crate::heavy::{self, PROFILE_FILE};
use crate::host::TestsHost;

/// `heavy-profile.toml` disagrees with the command telemetry it is derived from.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TEST002",
    slug = "heavy-profile-stale",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = project,
    host = TestsHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Test002;

impl<P: ?Sized + TestsHost> RelayRule<P> for Test002 {
    fn relay(&self, host: &P, _files: &mut FileInterner) -> Vec<Finding> {
        let Some(root) = host.repo_root() else {
            return Vec::new();
        };
        let why = match heavy::check(root, None) {
            Ok(None) => return Vec::new(),
            Ok(Some(why)) => format!("{PROFILE_FILE} is stale: {why}; run `frob agent profile`"),
            Err(e) => format!("{PROFILE_FILE} cannot be checked: {e}"),
        };
        tracing::debug!(%why, "TEST002 fired");
        let id: RuleId = Test002::DEF
            .id
            .parse()
            .unwrap_or_else(|e| unreachable!("the rule macro validates the id: {e}"));
        vec![Finding::new(
            id,
            Test002::DEF.severity,
            None,
            why,
            PROFILE_FILE,
        )]
    }
}
