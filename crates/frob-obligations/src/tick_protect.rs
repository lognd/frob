//! TICK011: the ledger branch must forbid force pushes and deletion, judged through the hosting API.
// frob:ticket 01M3ZX81C81M8ZQWTGQZK2SR2P
// frob:ticket 01M5BSTR1AMEEDFQMDRR4JF26Z

use gob_rules::{Finding, Rule, Severity};
use serde_json::Value;

use crate::util::finding;

/// The ledger branch allows a force push or deletion, or the hosting API could not say it does not.
///
/// `doctor` and `frob check` ask the hosting API for the ledger branch's protection (security.md
/// 2.11). An answer that force pushes or deletion are allowed is an Error; no token, an
/// unreachable API or an answer that cannot be read is Unresolved, never clean. Enable branch
/// protection on the ticket branch with "allow force pushes" and "allow deletions" both off, or a
/// repository ruleset with the `deletion` and `non_fast_forward` rules, which is also consulted.
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

/// The gap text for a branch that allows force pushes.
const FORCE_PUSH_OPEN: &str = "force pushes are allowed";

/// The gap text for a branch that allows deletion.
const DELETION_OPEN: &str = "deletion is allowed";

/// The hosting-API path of the rules that apply to a branch (repository rulesets).
#[must_use]
pub fn rules_path(owner: &str, repo: &str, branch: &str) -> String {
    format!("/repos/{owner}/{repo}/rules/branches/{branch}")
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
                ("allow_force_pushes", FORCE_PUSH_OPEN),
                ("allow_deletions", DELETION_OPEN),
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
            format!("{FORCE_PUSH_OPEN} (the branch has no classic protection)"),
            format!("{DELETION_OPEN} (the branch has no classic protection)"),
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

/// Fold the rulesets `rules` reply into a classic `verdict`: ruleset rules close the gaps they cover.
///
/// Only an `Unprotected` classic verdict is revisited. A `deletion` rule closes the deletion gap
/// and a `non_fast_forward` rule closes the force-push gap; a reply that cannot be read leaves
/// the branch Unresolved rather than a false Error.
#[must_use]
pub fn judge_with_rules(verdict: Verdict, rules: &Reply) -> Verdict {
    let Verdict::Unprotected(open) = verdict else {
        return verdict;
    };
    if rules.status != 200 {
        return Verdict::Unresolved(format!(
            "classic protection is absent and the branch rules could not be read (http {})",
            rules.status
        ));
    }
    let Ok(Value::Array(list)) = serde_json::from_str::<Value>(&rules.body) else {
        return Verdict::Unresolved("the branch rules answer was not a JSON array".to_owned());
    };
    let has = |kind: &str| {
        list.iter()
            .any(|r| r.get("type").and_then(Value::as_str) == Some(kind))
    };
    let left: Vec<String> = open
        .into_iter()
        .filter(|gap| {
            let covered = if gap.starts_with(FORCE_PUSH_OPEN) {
                has("non_fast_forward")
            } else if gap.starts_with(DELETION_OPEN) {
                has("deletion")
            } else {
                false
            };
            !covered
        })
        .collect();
    if left.is_empty() {
        Verdict::Protected
    } else {
        Verdict::Unprotected(left)
    }
}

/// Ask `probe` about `branch` of `owner/repo` and judge the answer; no reply is Unresolved.
///
/// When classic protection leaves a gap, the repository rulesets for the branch are consulted too.
#[must_use]
pub fn check_branch(probe: &dyn ProtectionProbe, owner: &str, repo: &str, branch: &str) -> Verdict {
    let mut verdict = match probe.get(&protection_path(owner, repo, branch)) {
        Ok(reply) => judge(&reply),
        Err(why) => Verdict::Unresolved(why),
    };
    if matches!(verdict, Verdict::Unprotected(_)) {
        tracing::debug!(
            owner,
            repo,
            branch,
            "classic protection has gaps; asking rulesets"
        );
        verdict = match probe.get(&rules_path(owner, repo, branch)) {
            Ok(rules) => judge_with_rules(verdict, &rules),
            Err(why) => Verdict::Unresolved(why),
        };
    }
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

    /// A probe answering the classic path and the rules path separately.
    struct Split {
        classic: Reply,
        rules: Result<Reply, String>,
    }

    impl ProtectionProbe for Split {
        fn get(&self, path: &str) -> Result<Reply, String> {
            if path.contains("/rules/branches/") {
                self.rules.clone()
            } else {
                Ok(self.classic.clone())
            }
        }
    }

    fn unprotected_404() -> Reply {
        reply(404, r#"{"message":"Branch not protected"}"#)
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::check_branch
    #[test]
    fn a_ruleset_with_both_rules_protects_an_unprotected_classic_branch() {
        let probe = Split {
            classic: unprotected_404(),
            rules: Ok(reply(
                200,
                r#"[{"type":"deletion"},{"type":"non_fast_forward"}]"#,
            )),
        };
        assert_eq!(check_branch(&probe, "o", "r", "b"), Verdict::Protected);
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge_with_rules
    #[test]
    fn a_ruleset_covering_one_gap_leaves_the_other() {
        let v = judge_with_rules(
            judge(&unprotected_404()),
            &reply(200, r#"[{"type":"deletion"}]"#),
        );
        assert!(matches!(&v, Verdict::Unprotected(o) if o.len() == 1 && o[0].starts_with("force")));
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge_with_rules
    #[test]
    fn no_rules_keeps_the_classic_error() {
        let v = judge_with_rules(judge(&unprotected_404()), &reply(200, "[]"));
        assert!(matches!(&v, Verdict::Unprotected(o) if o.len() == 2));
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::judge_with_rules
    #[test]
    fn unreadable_rules_are_unresolved() {
        let v = judge_with_rules(judge(&unprotected_404()), &reply(403, ""));
        assert!(matches!(v, Verdict::Unresolved(_)));
    }

    // frob:tests crates/frob-obligations/src/tick_protect.rs::rules_path
    #[test]
    fn rules_path_names_the_branch_rules_resource() {
        assert_eq!(rules_path("o", "r", "b"), "/repos/o/r/rules/branches/b");
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
