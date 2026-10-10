//! `ticket fragment`: write the reviewed changelog fragment skeleton of a ticket (documentation.md 6).
// frob:ticket 01M4069WHH6KXYWDAJD3TXB8SR
// frob:ticket 01M4FDQXEST75DK0NHDH4P5H15

use std::path::PathBuf;

use frob_release::fragment::sentence_required;
use frob_release::skeleton::{Request, default_kind, write};
use frob_release::{Kind, SkeletonError};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, get, open, resolve, text_flag, ticket_arg};
use crate::config::FrobConfig;
use crate::workspace::Located;

/// Output of `ticket fragment`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FragmentData {
    /// Full ULID of the ticket.
    pub id: String,
    /// Handle with `~`.
    pub handle: String,
    /// Fragment type written.
    pub kind: String,
    /// File name inside changelog.d.
    pub file: String,
    /// Full path written.
    pub path: PathBuf,
    /// The text written, to be edited and committed.
    pub text: String,
    /// Existing fragments of the ticket that `--force` replaced.
    pub replaced: Vec<String>,
}

/// Write `changelog.d/<ULID>.<type>.md` from the ticket title (or `--sentence`, required for bug, security and incident; `--text` is the global output format); never commits.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket fragment",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct Fragment {
    ticket: String,
    kind: Option<String>,
    text: Option<String>,
    force: bool,
}

impl Command for Fragment {
    type Data = FragmentData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(
                Arg::new("type")
                    .long("type")
                    .value_name("VALUE")
                    .value_parser(gob_cli::clap::builder::PossibleValuesParser::new(
                        Kind::ALL.map(Kind::as_str),
                    ))
                    .help(
                        "Fragment type (default from the ticket type: bug and incident fixed, security security, story and epic added, anything else changed)",
                    ),
            )
            .arg(text_flag(
                "sentence",
                "The user-facing sentence (default: `<ticket title>.`, after `[release] fragment_prefix`; required for bug, security and incident tickets, whose titles describe the problem)",
            ))
            .arg(
                Arg::new("force")
                    .long("force")
                    .action(ArgAction::SetTrue)
                    .help("Replace an existing fragment of the ticket"),
            )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            kind: get(m, "type"),
            text: get(m, "sentence"),
            force: m.get_flag("force"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<FragmentData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let view = ledger.show(id).map_err(cli_err)?;
        let front = &view.ticket.front;
        // frob:ticket 01M41JTGCWXZWWSPXYM9QNMT4D
        if self.text.is_none() && sentence_required(front.ty.as_str()) {
            tracing::info!(ty = front.ty.as_str(), "ticket fragment needs --sentence");
            return Err(CliError::Usage(format!(
                "a {} ticket's title describes the problem, not the change; pass the sentence: frob ticket fragment {} --sentence \"<what changed for the user>\"",
                front.ty.as_str(),
                view.summary.handle
            )));
        }
        // frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
        for text in [Some(front.title.as_str()), self.text.as_deref()]
            .into_iter()
            .flatten()
        {
            ledger.refuse_private(text).map_err(cli_err)?;
        }
        let kind = self
            .kind
            .as_deref()
            .and_then(Kind::parse)
            .unwrap_or_else(|| default_kind(front.ty.as_str()));
        let (root, prefix) = fragment_root(ctx, id)?;
        let ulid = id.to_string();
        let resolver = |u: &str| -> Option<String> {
            let t: frob_ledger::TicketId = u.parse().ok()?;
            ledger.show(t).ok().map(|v| v.summary.handle)
        };
        let req = Request {
            root: &root,
            ulid: &ulid,
            title: &front.title,
            prefix: &prefix,
            kind,
            text: self.text.as_deref(),
            force: self.force,
        };
        let written = write(&req, &resolver).map_err(|e| refuse(&e, &view.summary.handle))?;
        tracing::info!(file = %written.file, root = %root.display(), "ticket fragment written");
        Ok(Payload::new(FragmentData {
            id: ulid,
            handle: view.summary.handle,
            kind: kind.as_str().to_owned(),
            file: written.file,
            path: written.path,
            text: written.body.trim_end().to_owned(),
            replaced: written.replaced,
        }))
    }
}

/// The worktree to write into (the live lease holder's for the ticket, else the repository of the cwd) and the configured fragment prefix.
fn fragment_root(ctx: &Context, id: frob_ledger::TicketId) -> Result<(PathBuf, String), CliError> {
    let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| crate::workspace::config_refusal(&e))?;
    let held = frob_lease::open_store(&ctx.cwd, cfg.lease, ctx.clock.clone())
        .ok()
        .and_then(|(store, _)| store.live_lease(id).ok().flatten())
        .map(|l| l.holder.worktree);
    match held {
        Some(wt) if wt.is_dir() => {
            tracing::debug!(worktree = %wt.display(), "writing into the lease holder's worktree");
            Ok((wt, cfg.release.fragment_prefix))
        }
        _ => Ok((root, cfg.release.fragment_prefix)),
    }
}

/// Map a skeleton error to an exit-3 refusal with its remedy, or internal for I/O.
fn refuse(e: &SkeletonError, handle: &str) -> CliError {
    let (code, remedy) = match e {
        SkeletonError::Io(_) => return CliError::internal(e.to_string()),
        SkeletonError::Exists { .. } => (
            "E-FRAGMENT-EXISTS",
            format!("edit the file, or: frob ticket fragment {handle} --force"),
        ),
        SkeletonError::UnknownTicket { .. } => ("E-FRAGMENT-TICKET", "frob ticket list".to_owned()),
        SkeletonError::Invalid(_) => (
            "E-FRAGMENT-INVALID",
            format!("frob ticket fragment {handle} --sentence \"<one user-facing sentence>\""),
        ),
    };
    tracing::info!(code, "ticket fragment refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(remedy)
        .into()
}
