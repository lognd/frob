//! `ticket proposals accept`: apply a tracker edit held as a proposal, behind the adopt guards (design: `mirror.md` 3.5).
//!
//! Accepting is a decision a person makes at a terminal. The guards, in order: a TTY on both
//! streams and no agent marker; the proposal exists and is pending; its field is not scope,
//! acceptance, evidence or links; its editor is a mapped tracker user id (never a login). The
//! full value is then fetched from the tracker; when it is gone or no longer matches the
//! recorded digest the proposal closes as unavailable. Otherwise the escaped diff is shown and,
//! once the person confirms, the field changes through a normal ticket update by the accepter,
//! citing the tracker user id, and `proposal-accepted` closes the proposal.
// frob:ticket 01M4052TKZWKG1QBB3CWHQ9MVM

use std::collections::BTreeMap;
use std::io::{BufRead, IsTerminal, Write};

use frob_ledger::event::{EventBody, ProposalCloseData};
use frob_ledger::ops::Patch;
use frob_ledger::proposal::{ProposalState, fold_proposals};
use frob_ledger::schema::get_field;
use frob_ledger::{Ledger, TicketId};
use frob_mirror::adapter::{AdapterError, IssueRef};
use frob_mirror::github::adapter::GithubRest;
use frob_mirror::github::http::NativeTransport;
use frob_mirror::github::read::read_issue;
use frob_mirror::identity::IdentityConfig;
use frob_mirror::journal::value_digest;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use gob_diagnostics::{TextOrigin, escape_for_origin, escape_non_ascii};
use gob_trust::prompt::{Presence, presence};
use schemars::JsonSchema;
use serde::Serialize;

use super::{TicketArg, cli_err, open, resolve};
use crate::config::FrobConfig;
use crate::mirror_recreate_cmd::{TOKEN_VARS, resolve_repo};
use crate::workspace::{Located, config_refusal};

/// Refusal code when no person is at a terminal.
const CODE_NEEDS_HUMAN: &str = "E-PROPOSAL-NEEDS-HUMAN";
/// Refusal code for a proposal accept cannot or may not apply.
const CODE_ACCEPT: &str = "E-PROPOSAL-ACCEPT";
/// The reason recorded when the tracker no longer holds the proposed value.
const UNAVAILABLE: &str = "unavailable";
/// Fields a tracker edit may never change (mirror.md 3.5, security.md 2.11).
const FORBIDDEN_FIELDS: [&str; 5] = ["scope", "acceptance", "evidence", "links", "link"];
/// Fields whose full value the tracker can return.
const FETCHABLE_FIELDS: [&str; 2] = ["title", "body"];

/// How an accept ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum AcceptResult {
    /// The field changed and the proposal closed as accepted.
    Accepted,
    /// The tracker no longer held the value; the proposal closed as unavailable.
    Unavailable,
}

/// Output of `ticket proposals accept`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AcceptData {
    /// The ticket the proposal was held on (`~handle`).
    pub ticket: String,
    /// The tracker event id of the proposal.
    pub tracker_event: String,
    /// The ticket field the edit touched.
    pub field: String,
    /// The tracker user id of the editor, cited on the recorded change.
    pub actor_id: String,
    /// How it ended.
    pub result: AcceptResult,
}

/// Where the full proposed value comes from at accept time.
pub trait TrackerValues {
    /// The current full value of `field` on tracker item `item`; `Ok(None)` when it is gone.
    ///
    /// # Errors
    /// A message when the tracker could not be asked (the proposal then stays pending).
    fn fetch(&self, item: &str, field: &str) -> Result<Option<String>, String>;
}

/// The escaped before/after of one field, as shown to the person before they confirm.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Diff {
    /// The ticket field.
    pub field: String,
    /// The current ticket value, escaped.
    pub old: String,
    /// The proposed tracker value, escaped (origin `tracker`).
    pub new: String,
}

impl Diff {
    /// The diff as text: a header, the old value after `-` and the new one after `+`.
    #[must_use]
    pub fn render(&self) -> String {
        format!("field {}\n- {}\n+ {}\n", self.field, self.old, self.new)
    }
}

fn refuse(message: impl Into<String>) -> CliError {
    Refusal::new(CODE_ACCEPT, RefusalClass::GuardNeedsAction, message).into()
}

/// Refuse unless a person is at a terminal and no agent marker is set.
fn gate(
    stdin_tty: bool,
    stdout_tty: bool,
    env: impl Fn(&str) -> Option<String>,
) -> Result<(), CliError> {
    match presence(stdin_tty, stdout_tty, env) {
        Presence::Human => Ok(()),
        other => {
            tracing::warn!(?other, "proposals accept refused: no person at a terminal");
            Err(Refusal::new(
                CODE_NEEDS_HUMAN,
                RefusalClass::GuardNeedsAction,
                "accepting a tracker edit is a decision a person makes at a terminal",
            )
            .with_remedy("ask the user to run `frob ticket proposals accept` in their own terminal")
            .requiring_human()
            .into())
        }
    }
}

/// Accept the proposal keyed `tracker_event` on ticket `id`, after the guards and the person's `confirm` of the diff.
///
/// `identities` maps frob identities to tracker user ids; `values` fetches the full value; `confirm`
/// is shown the escaped [`Diff`] and answers whether to apply it. Presence (TTY, agent marker) is
/// the caller's guard, see [`Accept`]. Nothing is written on any refusal.
///
/// # Errors
/// A refusal for a closed or unknown proposal, a forbidden or unfetchable field, an unmapped
/// editor, a tracker failure or a declined confirmation; an internal error when the ledger fails.
pub fn accept_with(
    ledger: &Ledger,
    id: TicketId,
    tracker_event: &str,
    identities: &BTreeMap<String, u64>,
    values: &dyn TrackerValues,
    confirm: &mut dyn FnMut(&Diff) -> bool,
) -> Result<AcceptData, CliError> {
    let events = ledger.events(id).map_err(cli_err)?;
    let proposal = fold_proposals(&events)
        .into_iter()
        .find(|p| p.data.tracker_event == tracker_event)
        .ok_or_else(|| {
            CliError::Usage(format!(
                "no proposal with tracker event `{}`; see `frob ticket proposals list`",
                escape_non_ascii(tracker_event)
            ))
        })?;
    if proposal.state != ProposalState::Pending {
        return Err(CliError::Usage(format!(
            "that proposal is already {:?} and is never reopened",
            proposal.state
        )));
    }
    let data = proposal.data;
    let handle = ledger.show(id).map_err(cli_err)?.summary.handle;
    let done = |result| AcceptData {
        ticket: handle.clone(),
        tracker_event: tracker_event.to_owned(),
        field: data.field.clone(),
        actor_id: data.actor_id.clone(),
        result,
    };

    check_editable(id, &data, identities)?;

    let fetched = values
        .fetch(&data.item, &data.field)
        .map_err(|e| refuse(format!("could not fetch the tracker value: {e}")))?;
    let Some(value) = fetched.filter(|v| value_digest(v) == data.digest) else {
        tracing::info!(ticket = %id, key = %tracker_event, "proposal value gone from the tracker; closing as unavailable");
        ledger
            .append(
                id,
                EventBody::ProposalExpired(ProposalCloseData {
                    tracker_event: tracker_event.to_owned(),
                    reason: Some(UNAVAILABLE.to_owned()),
                }),
            )
            .map_err(cli_err)?;
        return Ok(done(AcceptResult::Unavailable));
    };

    let current = ledger.show(id).map_err(cli_err)?.ticket;
    let old = match get_field(&current, &data.field) {
        Some(toml::Value::String(s)) => s,
        _ => String::new(),
    };
    let diff = Diff {
        field: data.field.clone(),
        old: escape_for_origin(&old, &TextOrigin::Ledger).into_owned(),
        new: escape_for_origin(&value, &TextOrigin::Tracker).into_owned(),
    };
    if !confirm(&diff) {
        tracing::info!(ticket = %id, key = %tracker_event, "accept not confirmed; nothing changed");
        return Err(refuse("not confirmed; nothing changed"));
    }

    let patch = Patch {
        sets: vec![(data.field.clone(), Some(toml::Value::String(value)))],
        reason: Some(format!(
            "accepted tracker edit {} by tracker user id {}",
            escape_non_ascii(tracker_event),
            escape_non_ascii(&data.actor_id)
        )),
        ..Patch::default()
    };
    ledger.update(id, &patch).map_err(cli_err)?;
    ledger
        .append(
            id,
            EventBody::ProposalAccepted(ProposalCloseData {
                tracker_event: tracker_event.to_owned(),
                reason: None,
            }),
        )
        .map_err(cli_err)?;
    tracing::info!(ticket = %id, key = %tracker_event, field = %data.field, "proposal accepted");
    Ok(done(AcceptResult::Accepted))
}

/// Refuse a proposal on a forbidden or unfetchable field, or by an editor without an identity mapping.
fn check_editable(
    id: TicketId,
    data: &frob_ledger::event::ProposalData,
    identities: &BTreeMap<String, u64>,
) -> Result<(), CliError> {
    if FORBIDDEN_FIELDS.contains(&data.field.as_str()) {
        tracing::warn!(ticket = %id, field = %data.field, "accept refused: field is never changed by a tracker edit");
        return Err(refuse(format!(
            "a tracker edit never changes `{}`; decline the proposal or change it with a ticket verb",
            data.field
        )));
    }
    if !FETCHABLE_FIELDS.contains(&data.field.as_str()) {
        return Err(refuse(format!(
            "the tracker value of `{}` cannot be fetched for accept; decline it or apply it by hand",
            escape_non_ascii(&data.field)
        )));
    }
    let mapped = data
        .actor_id
        .parse::<u64>()
        .ok()
        .and_then(|u| {
            let cfg = IdentityConfig {
                identities: identities.clone(),
                bot_ids: Vec::new(),
            };
            cfg.frob_identity(u).map(str::to_owned)
        })
        .is_some();
    if !mapped {
        tracing::warn!(ticket = %id, actor = %data.actor_id, "accept refused: editor has no identity mapping");
        return Err(refuse(format!(
            "tracker user id {} is not mapped in [mirror.identities]; map it or decline the proposal",
            escape_non_ascii(&data.actor_id)
        )));
    }
    Ok(())
}

/// The `[mirror.identities]` table of `frob.toml` (frob identity to tracker user id); empty when absent.
fn read_identities(root: &std::path::Path) -> Result<BTreeMap<String, u64>, CliError> {
    let Ok(text) = std::fs::read_to_string(root.join("frob.toml")) else {
        return Ok(BTreeMap::new());
    };
    let doc: toml::Table = text
        .parse()
        .map_err(|e| refuse(format!("frob.toml: {e}")))?;
    let Some(table) = doc
        .get("mirror")
        .and_then(|m| m.get("identities"))
        .and_then(toml::Value::as_table)
    else {
        return Ok(BTreeMap::new());
    };
    table
        .iter()
        .map(|(name, v)| {
            v.as_integer()
                .and_then(|n| u64::try_from(n).ok())
                .map(|n| (name.clone(), n))
                .ok_or_else(|| {
                    refuse(format!(
                        "[mirror.identities] `{}` must be a tracker user id (an integer), never a login",
                        escape_non_ascii(name)
                    ))
                })
        })
        .collect()
}

/// Fetches title and body from a GitHub issue.
struct GithubValues {
    rest: GithubRest<NativeTransport>,
}

impl TrackerValues for GithubValues {
    fn fetch(&self, item: &str, field: &str) -> Result<Option<String>, String> {
        match read_issue(&self.rest, &IssueRef(item.to_owned())) {
            Ok(state) => Ok(match field {
                "title" => Some(state.title),
                "body" => Some(state.body),
                _ => None,
            }),
            Err(AdapterError::NotFound | AdapterError::Gone) => Ok(None),
            Err(e) => Err(e.to_string()),
        }
    }
}

/// The flags of `ticket proposals accept`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AcceptArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        value_name = "TRACKER_EVENT",
        help = "The tracker event id of the proposal, as `proposals list` shows it"
    )]
    tracker_event: String,
    #[arg(
        long,
        value_name = "OWNER/NAME",
        help = "GitHub repository; default [mirror] repo, else the origin remote"
    )]
    repo: Option<String>,
}

/// Accept a pending proposal at a terminal: shows the escaped diff, then changes the field and closes the proposal.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket proposals accept",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct Accept {
    ticket: String,
    tracker_event: String,
    repo: Option<String>,
}

impl Command for Accept {
    type Data = AcceptData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<AcceptArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AcceptArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            tracker_event: a.tracker_event,
            repo: a.repo,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<AcceptData> {
        gate(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |k| std::env::var(k).ok(),
        )?;
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let remote = repo.remote_url("origin").unwrap_or_default();
        let cfg = FrobConfig::load(&root)
            .map_err(|e| config_refusal(&e))?
            .mirror;
        let (owner, name) = resolve_repo(self.repo.as_deref(), &cfg.repo, &remote)
            .ok_or_else(|| refuse("no GitHub repository: pass --repo OWNER/NAME"))?;
        let token = TOKEN_VARS
            .iter()
            .find_map(|v| std::env::var(v).ok().filter(|t| !t.is_empty()))
            .ok_or_else(|| {
                refuse("set GH_TOKEN or GITHUB_TOKEN to a token that can read issues")
            })?;
        let values = GithubValues {
            rest: GithubRest::new(NativeTransport::new(token), &owner, &name, ""),
        };
        let identities = read_identities(&root)?;
        let mut confirm = |diff: &Diff| {
            let mut out = std::io::stdout().lock();
            let _ = write!(out, "{}Apply this change? [y/N] ", diff.render());
            let _ = out.flush();
            let mut line = String::new();
            std::io::stdin().lock().read_line(&mut line).is_ok()
                && matches!(line.trim(), "y" | "Y" | "yes")
        };
        accept_with(
            &ledger,
            id,
            &self.tracker_event,
            &identities,
            &values,
            &mut confirm,
        )
        .map(Payload::new)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/ticket/proposals_accept.rs::gate
    #[test]
    fn no_tty_or_an_agent_marker_refuses_and_a_person_passes() {
        assert!(gate(true, true, |_| None).is_ok());
        assert!(gate(false, true, |_| None).is_err());
        assert!(gate(true, false, |_| None).is_err());
        assert!(gate(true, true, |k| (k == "CLAUDECODE").then(|| "1".to_owned())).is_err());
    }

    // frob:tests crates/frob/src/ticket/proposals_accept.rs::Diff
    #[test]
    fn a_diff_renders_old_and_new_on_marked_lines() {
        let d = Diff {
            field: "title".into(),
            old: "a".into(),
            new: "b".into(),
        };
        assert_eq!(d.render(), "field title\n- a\n+ b\n");
    }

    // frob:tests crates/frob/src/ticket/proposals_accept.rs::read_identities
    #[test]
    fn identities_are_read_by_user_id_and_a_login_is_refused() {
        let dir = tempfile::tempdir().expect("tempdir");
        assert!(read_identities(dir.path()).expect("none").is_empty());
        std::fs::write(
            dir.path().join("frob.toml"),
            "[mirror.identities]\nalice = 42\n",
        )
        .expect("write");
        assert_eq!(read_identities(dir.path()).expect("map")["alice"], 42);
        std::fs::write(
            dir.path().join("frob.toml"),
            "[mirror.identities]\nalice = \"alice-gh\"\n",
        )
        .expect("write");
        assert!(read_identities(dir.path()).is_err());
    }
}
