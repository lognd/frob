//! `mirror render`: print the tracker-independent `IssueProjection` of one ticket (mirror.md section 2.1).
//!
//! Other adapters (GitLab, Jira) develop and test from recorded projections of this output; the JSON
//! schema it validates against is `docs/schemas/issue-projection.json`.

// frob:ticket 01M3ZX836BNV9H9K9ZCKNMAEDB

use std::collections::BTreeSet;

use frob_ledger::Ledger;
use frob_ledger::model::{Category, LinkKind, Outcome};
use frob_ledger::ops::TicketView;
use frob_mirror::projection::{
    self, Classification, Criterion, EvidenceItem, Identity, IssueProjection, People, Relation,
    RelationKind, State, TicketFacts,
};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};

use crate::ticket::{TicketArg, cli_err, open, resolve};
use crate::workspace::Located;

/// Print the tracker-independent projection of a ticket: identity, sections, classification, state, relations, people and provenance.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "mirror render",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct MirrorRender {
    ticket: String,
}

impl Command for MirrorRender {
    type Data = IssueProjection;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<TicketArg>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TicketArg>(m)?;
        Ok(Self { ticket: a.ticket })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<IssueProjection> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let view = ledger.show(id).map_err(cli_err)?;
        let (repo, _) = Located::discover(&ctx.cwd).into_repo()?;
        let repository = repo.remote_url("origin").unwrap_or_default();
        let facts = facts_of(&ledger, &view, repository)?;
        let projection = projection::project(&facts, &BTreeSet::new(), env!("CARGO_PKG_VERSION"));
        tracing::info!(ticket = %id, digest = %projection.provenance.render_digest, "mirror render");
        Ok(Payload::new(projection))
    }
}

/// Fold one ticket view and its evidence into the facts the producer projects.
pub(crate) fn facts_of(
    ledger: &Ledger,
    view: &TicketView,
    repository: String,
) -> Result<TicketFacts, CliError> {
    let front = &view.ticket.front;
    let id = front.id;
    let ledger_path = ledger
        .ticket_path(id)
        .map_err(cli_err)?
        .unwrap_or_else(|| format!("tickets/{id}/ticket.md"));
    let last_event = ledger
        .events(id)
        .map_err(cli_err)?
        .last()
        .map(|e| e.id.to_string())
        .unwrap_or_default();
    let evidence = frob_evidence::events::list(ledger, id)
        .map_err(CliError::internal)?
        .into_iter()
        .map(|e| EvidenceItem {
            reference: e.record.reference,
            verdict: match e.record.passed {
                Some(true) => "pass",
                Some(false) => "fail",
                None => "unmeasured",
            }
            .to_owned(),
        })
        .collect();
    Ok(TicketFacts {
        identity: Identity {
            ulid: id.to_string(),
            handle: view.summary.handle.clone(),
            aliases: front.aliases.clone(),
            repository,
            ledger_path,
        },
        title: front.title.clone(),
        summary: view.ticket.body.clone(),
        acceptance: front
            .acceptance
            .iter()
            .map(|a| Criterion {
                text: a.text.clone(),
                bound: a.bound,
            })
            .collect(),
        scope: front.scope.clone(),
        evidence,
        classification: Classification {
            ticket_type: Some(front.ty.to_string()),
            labels: (!front.labels.is_empty()).then(|| front.labels.clone()),
            priority: Some(front.priority.to_string()),
            points: front.points.map(|p| u32::from(p.get())),
            milestone: None,
            epic: None,
        },
        state: State {
            category: category(front.category),
            outcome: front.outcome.map(outcome),
            reason: None,
        },
        relations: relations(ledger, view)?,
        people: People {
            owner: Some(front.reporter.clone()),
            assignee: front.assignee.clone(),
        },
        last_event,
    })
}

/// The projection's coarse workflow category of a ledger category.
fn category(c: Category) -> projection::Category {
    match c {
        Category::Triage | Category::Todo => projection::Category::Todo,
        Category::InProgress => projection::Category::Doing,
        Category::Done => projection::Category::Done,
    }
}

/// The projection's outcome of a ledger outcome.
fn outcome(o: Outcome) -> projection::Outcome {
    match o {
        Outcome::Fixed | Outcome::Done => projection::Outcome::Done,
        Outcome::WontFix | Outcome::Invalid => projection::Outcome::Dropped,
        Outcome::Duplicate => projection::Outcome::Duplicate,
    }
}

/// The projection's relation kind of a link kind; kinds a tracker cannot hold flatten to `relates`.
fn relation_kind(k: LinkKind) -> RelationKind {
    match k {
        LinkKind::Blocks => RelationKind::Blocks,
        LinkKind::BlockedBy => RelationKind::BlockedBy,
        LinkKind::Duplicates => RelationKind::Duplicates,
        LinkKind::Supersedes => RelationKind::Supersedes,
        other => {
            tracing::debug!(kind = %other, "link kind flattened to relates");
            RelationKind::Relates
        }
    }
}

/// Typed relations of a ticket: its parent plus every resolvable link, in both directions.
fn relations(ledger: &Ledger, view: &TicketView) -> Result<Vec<Relation>, CliError> {
    let mut out = Vec::new();
    if let Some(parent) = view.ticket.front.parent {
        let p = ledger.show(parent).map_err(cli_err)?;
        out.push(Relation {
            kind: RelationKind::Parent,
            ulid: parent.to_string(),
            handle: p.summary.handle,
        });
    }
    for l in view.outgoing.iter().chain(&view.incoming) {
        let Some(handle) = &l.handle else {
            tracing::warn!(target = %l.id, "dangling link skipped in projection");
            continue;
        };
        out.push(Relation {
            kind: relation_kind(l.kind),
            ulid: l.id.to_string(),
            handle: handle.clone(),
        });
    }
    Ok(out)
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<MirrorRender>()
        .register::<crate::mirror_recreate_cmd::MirrorRecreate>()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn category_and_outcome_map_to_projection_values() {
        // frob:tests crates/frob/src/mirror_cmd.rs::category
        assert_eq!(category(Category::Triage), projection::Category::Todo);
        assert_eq!(category(Category::InProgress), projection::Category::Doing);
        assert_eq!(outcome(Outcome::WontFix), projection::Outcome::Dropped);
        assert_eq!(relation_kind(LinkKind::Causes), RelationKind::Relates);
    }
}
