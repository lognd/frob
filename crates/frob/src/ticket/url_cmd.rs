//! `ticket url`: the web URL of a ticket file on the ticket branch and of its mirrored issue (`navigation.md` section 1).
// frob:ticket 01M3ZX88FHDWF9C082QZR1PXXA

use frob_ledger::layout::Layout;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, get, open, resolve, ticket_arg};
use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// Output of `ticket url`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct UrlData {
    /// Handle with `~`.
    pub handle: String,
    /// The ticket-branch relative path of the ticket file right now.
    pub path: String,
    /// The blob URL of the ticket file on the ticket branch.
    pub url: String,
    /// The URL of the mirrored issue, when the ticket has a map shard.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub issue_url: Option<String>,
}

/// Print the current blob URL of the ticket file on the ticket branch, and the mirrored issue URL when one exists.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket url",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Url {
    ticket: String,
}

impl Command for Url {
    type Data = UrlData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<UrlData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let handle = ledger.show(id).map_err(cli_err)?.summary.handle;
        if ledger.layout() != Layout::Branch {
            return Err(refuse(
                "E-TICKET-URL-LAYOUT",
                "tickets are not on a ticket branch yet".to_owned(),
                "frob ticket migrate",
            ));
        }
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let remote = repo.remote_url("origin").ok_or_else(|| {
            refuse(
                "E-TICKET-URL-NO-REMOTE",
                "the repository has no `origin` remote to build a web URL from".to_owned(),
                "git remote add origin <url>",
            )
        })?;
        let base = web_base(&remote).ok_or_else(|| {
            refuse(
                "E-TICKET-URL-REMOTE",
                format!("cannot derive a web URL from the origin remote `{remote}`"),
                "point origin at an https or ssh remote of the form host/owner/repo",
            )
        })?;
        let path = ledger
            .ticket_path(id)
            .map_err(cli_err)?
            .ok_or_else(|| CliError::internal("ticket branch has no tip"))?;
        let url = format!("{base}/blob/{}/{path}", cfg.tickets.branch);
        let issue_url = ledger
            .mirror_issue(id)
            .map_err(cli_err)?
            .map(|n| format!("{base}/issues/{n}"));
        tracing::info!(ticket = %id, %url, mirrored = issue_url.is_some(), "ticket url");
        Ok(Payload::new(UrlData {
            handle,
            path,
            url,
            issue_url,
        }))
    }
}

/// A user-fixable refusal with a remedy.
fn refuse(code: &'static str, message: String, remedy: &str) -> CliError {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
        .with_remedy(remedy)
        .into()
}

/// The `https://host/owner/repo` web base of a git remote URL (https, ssh or scp-like), `None` when it has no host and path.
pub(crate) fn web_base(remote: &str) -> Option<String> {
    let remote = remote.trim();
    let rest = remote.split_once("://").map_or(remote, |(_, rest)| rest);
    let rest = rest.rsplit_once('@').map_or(rest, |(_, r)| r);
    let (host, path) = if remote.contains("://") {
        rest.split_once('/')?
    } else {
        rest.split_once(':')?
    };
    let host = host.split(':').next().filter(|h| !h.is_empty())?;
    let path = path.trim_matches('/');
    let path = path.strip_suffix(".git").unwrap_or(path);
    (path.contains('/') && !path.starts_with('/')).then(|| format!("https://{host}/{path}"))
}

#[cfg(test)]
mod tests {
    use super::web_base;

    #[test]
    fn web_base_reads_https_ssh_and_scp_remotes() {
        // frob:tests crates/frob/src/ticket/url_cmd.rs::web_base
        let want = Some("https://github.com/o/r".to_owned());
        assert_eq!(web_base("https://github.com/o/r.git"), want);
        assert_eq!(web_base("https://tok@github.com/o/r/"), want);
        assert_eq!(web_base("git@github.com:o/r.git"), want);
        assert_eq!(web_base("ssh://git@github.com:22/o/r"), want);
        assert_eq!(web_base("/some/local/path"), None);
        assert_eq!(web_base("github.com"), None);
    }
}
