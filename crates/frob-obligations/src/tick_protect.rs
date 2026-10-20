//! TICK011: the ledger branch must forbid force pushes and deletion, judged through the hosting API.
// frob:ticket 01M3ZX81C81M8ZQWTGQZK2SR2P

use gob_rules::{Finding, Rule, Severity};
use serde_json::Value;

use crate::util::finding;

/// The ledger branch allows a force push or deletion, or the hosting API could not say it does not.
///
/// `doctor` and `frob check` ask the hosting API for the ledger branch's protection (security.md
/// 2.11). An answer that force pushes or deletion are allowed is an Error; no token, an
/// unreachable API or an answer that cannot be read is Unresolved, never clean. Enable branch
/// protection on the ticket branch with "allow force pushes" and "allow deletions" both off.
// frob:ticket 01M3ZX81C81M8ZQWTGQZK2SR2P
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK011",
    slug = "ledger-branch-unprotected",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick011;

/// What the hosting API says about the ledger branch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    /// Force pushes and deletion are both forbidden.
    Protected,
    /// The API answered that at least one of them is allowed; each entry says which.
    Unprotected(Vec<String>),
    /// The API could not answer; the entry says why.
    Unresolved(String),
}

/// One raw API reply: HTTP status and body.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reply {
    /// HTTP status code.
    pub status: u16,
    /// Response body text.
    pub body: String,
}

/// Something that can ask the hosting API about a branch's protection.
pub trait ProtectionProbe {
    /// The reply for `GET path` against the hosting API, or why none was obtained.
    ///
    /// # Errors
    /// A human-readable reason when no reply was obtained (no token, unreachable host).
    fn get(&self, path: &str) -> Result<Reply, String>;
}

/// The hosting-API path of the classic branch-protection resource.
#[must_use]
pub fn protection_path(owner: &str, repo: &str, branch: &str) -> String {
    format!("/repos/{owner}/{repo}/branches/{branch}/protection")
}

/// One `{ "enabled": bool }` setting of a protection answer, `None` when absent or malformed.
fn enabled(doc: &Value, key: &str) -> Option<bool> {
    doc.get(key)?.get("enabled")?.as_bool()
}

/// Judge one protection `reply`; pure, so every status maps to exactly one verdict.
#[must_use]
pub fn judge(reply: &Reply) -> Verdict {
    match reply.status {
        200 => {
            let Ok(doc) = serde_json::from_str::<Value>(&reply.body) else {
                return Verdict::Unresolved("the protection answer was not JSON".to_owned());
            };
            let mut open = Vec::new();
            for (key, what) in [
                ("allow_force_pushes", "force pushes are allowed"),
                ("allow_deletions", "deletion is allowed"),
            ] {
                match enabled(&doc, key) {
                    Some(true) => open.push(what.to_owned()),
                    Some(false) => {}
                    None => {
                        return Verdict::Unresolved(format!(
                            "the protection answer carries no `{key}` setting"
                        ));
                    }
                }
            }
            if open.is_empty() {
                Verdict::Protected
            } else {
                Verdict::Unprotected(open)
            }
        }
        404 if reply.body.contains("Branch not protected") => Verdict::Unprotected(vec![
            "the branch has no protection, so force pushes and deletion are allowed".to_owned(),
        ]),
        401 | 403 => Verdict::Unresolved(format!(
            "the token may not read branch protection (http {})",
            reply.status
        )),
        404 => Verdict::Unresolved(
            "the repository or branch is not visible to this token (http 404)".to_owned(),
        ),
        s => Verdict::Unresolved(format!("unexpected answer from the hosting API (http {s})")),
    }
}

/// Ask `probe` about `branch` of `owner/repo` and judge the answer; no reply is Unresolved.
#[must_use]
pub fn check_branch(probe: &dyn ProtectionProbe, owner: &str, repo: &str, branch: &str) -> Verdict {
    let verdict = match probe.get(&protection_path(owner, repo, branch)) {
        Ok(reply) => judge(&reply),
        Err(why) => Verdict::Unresolved(why),
    };
    tracing::info!(
        owner,
        repo,
        branch,
        ?verdict,
        "ledger branch protection judged"
    );
    verdict
}

/// The `TICK011` finding for `verdict`, `None` when the branch is protected.
#[must_use]
pub fn tick011(verdict: &Verdict, branch: &str) -> Option<Finding> {
    let anchor = format!("branch:{branch}");
    match verdict {
        Verdict::Protected => None,
        Verdict::Unprotected(open) => Some(finding(
            &Tick011,
            None,
            format!("ledger branch `{branch}`: {}", open.join("; ")),
            &anchor,
        )),
        Verdict::Unresolved(why) => {
            let mut f = finding(
                &Tick011,
                None,
                format!("ledger branch `{branch}` protection could not be checked: {why}"),
                &anchor,
            );
            f.severity = Severity::Unresolved;
            Some(f)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn reply(status: u16, body: &str) -> Reply {
        Reply {
            status,
            body: body.to_owned(),
        }
    }

    struct Fixed(Result<Reply, String>);

    impl ProtectionProbe for Fixed {
        fn get(&self, _path: &str) -> Result<Reply, String> {
            self.0.clone()
        }
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge
    #[test]
    fn force_push_allowed_is_unprotected() {
        let body = r#"{"allow_force_pushes":{"enabled":true},"allow_deletions":{"enabled":false}}"#;
        let v = judge(&reply(200, body));
        assert_eq!(
            v,
            Verdict::Unprotected(vec!["force pushes are allowed".to_owned()])
        );
        let f = tick011(&v, "frob-tickets").expect("finding");
        assert_eq!(f.severity, Severity::Error);
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge
    #[test]
    fn forbidding_both_is_protected() {
        let body =
            r#"{"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false}}"#;
        assert_eq!(judge(&reply(200, body)), Verdict::Protected);
        assert!(tick011(&Verdict::Protected, "b").is_none());
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge
    #[test]
    fn unprotected_branch_404_is_an_error() {
        let v = judge(&reply(404, r#"{"message":"Branch not protected"}"#));
        assert!(matches!(v, Verdict::Unprotected(_)));
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::check_branch
    #[test]
    fn no_token_or_unreachable_api_is_unresolved_not_clean() {
        let probe = Fixed(Err("no GH_TOKEN".to_owned()));
        let v = check_branch(&probe, "o", "r", "frob-tickets");
        assert!(matches!(v, Verdict::Unresolved(_)));
        let f = tick011(&v, "frob-tickets").expect("finding");
        assert_eq!(f.severity, Severity::Unresolved);
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge
    #[test]
    fn unreadable_answers_are_unresolved() {
        for r in [
            reply(403, ""),
            reply(401, ""),
            reply(404, r#"{"message":"Not Found"}"#),
            reply(500, ""),
            reply(200, "not json"),
            reply(200, "{}"),
        ] {
            assert!(matches!(judge(&r), Verdict::Unresolved(_)), "{r:?}");
        }
    }
}
