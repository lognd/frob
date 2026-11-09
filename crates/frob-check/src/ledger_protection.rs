//! `TICK011` in `frob check`: the ledger branch's protection, asked of the hosting API.
// frob:ticket 01M5BSTQWD096Z3AKQNNB0YFYT

use frob_ledger::{Ledger, RefMode};
use frob_mirror::github::adapter::{HttpRequest, HttpTransport, Method};
use frob_mirror::github::http::NativeTransport;
use frob_obligations::tick_protect::{self, ProtectionProbe, Reply, Verdict};
use gob_rules::Finding;

/// Environment variables that may hold a GitHub token, in order of preference.
const GITHUB_TOKEN_VARS: [&str; 2] = ["GH_TOKEN", "GITHUB_TOKEN"];

/// The first non-empty GitHub token in the environment.
pub(crate) fn github_token() -> Option<String> {
    GITHUB_TOKEN_VARS
        .iter()
        .find_map(|v| std::env::var(v).ok().filter(|t| !t.is_empty()))
}

/// A [`ProtectionProbe`] over the native GitHub transport, with the token from the environment.
pub struct GithubProbe;

impl ProtectionProbe for GithubProbe {
    fn get(&self, path: &str) -> Result<Reply, String> {
        let token = github_token().ok_or_else(|| "no GH_TOKEN or GITHUB_TOKEN set".to_owned())?;
        let req = HttpRequest {
            method: Method::Get,
            path: path.to_owned(),
            query: vec![],
            body: None,
        };
        NativeTransport::new(token)
            .send(&req)
            .map(|r| Reply {
                status: r.status,
                body: r.body,
            })
            .map_err(|e| format!("hosting API unreachable: {e}"))
    }
}

/// The `(owner, name)` of the repository holding the ledger: `[mirror] repo` (`OWNER/NAME`), else the `origin` URL.
fn repo_of(mirror_repo: &str, remote: &str) -> Result<(String, String), String> {
    if let Some((owner, name)) = mirror_repo
        .split_once('/')
        .filter(|(o, n)| !o.is_empty() && !n.is_empty())
    {
        return Ok((owner.to_owned(), name.to_owned()));
    }
    frob_release::ci::parse_remote(remote)
        .map(|r| (r.owner, r.name))
        .map_err(|_| "no GitHub repository: set [mirror] repo or an origin remote".to_owned())
}

/// Ask `probe` about `branch` of the repository named by `mirror_repo` or `remote`.
pub fn branch_verdict(
    probe: &dyn ProtectionProbe,
    mirror_repo: &str,
    remote: &str,
    branch: &str,
) -> Verdict {
    match repo_of(mirror_repo, remote) {
        Ok((owner, repo)) => tick_protect::check_branch(probe, &owner, &repo, branch),
        Err(why) => Verdict::Unresolved(why),
    }
}

/// The `TICK011` finding for `branch`, `None` when it is protected.
pub fn protection_finding(
    probe: &dyn ProtectionProbe,
    mirror_repo: &str,
    remote: &str,
    branch: &str,
) -> Option<Finding> {
    tick_protect::tick011(&branch_verdict(probe, mirror_repo, remote, branch), branch)
}

/// The `TICK011` finding for `ledger`'s ticket branch; `None` when protected or when the layout has no ledger branch.
// frob:ticket 01M5BSTQWD096Z3AKQNNB0YFYT
pub(crate) fn ledger_finding(
    ledger: &Ledger,
    mirror_repo: &str,
    probe: &dyn ProtectionProbe,
) -> Option<Finding> {
    let config = ledger.config();
    if config.mode != RefMode::Orphan {
        tracing::debug!("TICK011 skipped: not the orphan ticket-branch layout");
        return None;
    }
    let remote = ledger.repo().remote_url("origin").unwrap_or_default();
    tracing::debug!(branch = %config.branch, "TICK011 asking the hosting API");
    protection_finding(probe, mirror_repo, &remote, &config.branch)
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Fixed(Result<Reply, String>);

    impl ProtectionProbe for Fixed {
        fn get(&self, _path: &str) -> Result<Reply, String> {
            self.0.clone()
        }
    }

    fn open_reply() -> Fixed {
        Fixed(Ok(Reply {
            status: 200,
            body: r#"{"allow_force_pushes":{"enabled":true},"allow_deletions":{"enabled":false}}"#
                .to_owned(),
        }))
    }

    // frob:tests crates/frob-check/src/ledger_protection.rs::protection_finding
    #[test]
    fn an_open_branch_yields_a_tick011_finding() {
        let f = protection_finding(&open_reply(), "o/n", "", "frob-tickets");
        assert_eq!(f.map(|f| f.rule.to_string()), Some("TICK011".to_owned()));
    }

    // frob:tests crates/frob-check/src/ledger_protection.rs::protection_finding
    #[test]
    fn a_protected_branch_yields_no_finding() {
        let body =
            r#"{"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false}}"#;
        let probe = Fixed(Ok(Reply {
            status: 200,
            body: body.to_owned(),
        }));
        assert!(protection_finding(&probe, "o/n", "", "b").is_none());
    }

    // frob:tests crates/frob-check/src/ledger_protection.rs::branch_verdict
    #[test]
    fn no_repository_is_unresolved() {
        let v = branch_verdict(&open_reply(), "", "", "b");
        assert!(matches!(v, Verdict::Unresolved(_)));
    }

    // frob:tests crates/frob-check/src/ledger_protection.rs::branch_verdict
    #[test]
    fn the_origin_remote_names_the_repository() {
        let v = branch_verdict(&open_reply(), "", "https://github.com/o/n.git", "b");
        assert!(matches!(v, Verdict::Unprotected(_)));
    }
}
