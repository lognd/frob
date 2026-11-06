//! `frob plan --from-design [--apply]`: propose (or create) a ticket for every unplanned design entity.
//!
//! The planning join (pm-and-releases.md 10.3): each grimble `goal` becomes an epic, each `scenario` a
//! story and each `impl` a task, every one carrying `implements design:<anchor>`. Re-running proposes
//! nothing for an anchor that a live ticket already implements, so `--apply` twice is idempotent.
//! The anchor is also the ticket's idempotency key, scope is seeded from the entity's files (a story
//! takes the union of its children's), acceptance is seeded per type, and `requires` becomes
//! `blocked-by`. `--findings` lists the anchors that cannot be mapped to a ticket.

// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK
// frob:ticket 01M6PJTS38G6EGSH32FPD01BKM

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::TicketId;
use frob_ledger::design::{DesignGraph, DesignStatus, Entity, Overlay, link_of, overlay};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};

use crate::pretty::PrettyExt;
use schemars::JsonSchema;
use serde::Serialize;

use crate::ticket::{cli_err, open};
use crate::workspace::Located;

/// One proposed or created ticket.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlanRow {
    /// The design anchor the ticket implements.
    pub anchor: String,
    /// The ticket type it gets (`epic`, `story` or `task`).
    #[serde(rename = "type")]
    pub ty: String,
    /// The proposed title.
    pub title: String,
    /// The handle of the created ticket; absent on a dry run.
    pub handle: Option<String>,
    /// The scope globs seeded from the design files.
    pub scope: Vec<String>,
    /// The anchors whose tickets block this one (from `requires`).
    pub blocked_by: Vec<String>,
}

/// Output of `frob plan --from-design`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlanData {
    /// True when the tickets were created.
    pub applied: bool,
    /// The tickets proposed (dry run) or created (`--apply`); empty when everything is planned.
    pub proposed: Vec<PlanRow>,
    /// With `--findings`: anchors that cannot be mapped to a ticket (unmappable kind or unknown target); else empty.
    pub unmapped: Vec<String>,
}

/// The flags of `plan`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct PlanArgs {
    #[arg(
        long,
        required = true,
        help = "Plan from the grimble design: one ticket per unplanned goal, scenario and impl"
    )]
    from_design: bool,
    #[arg(long, help = "Create the tickets (default: only propose them)")]
    apply: bool,
    #[arg(
        long,
        help = "List the design anchors that cannot be mapped to a ticket"
    )]
    findings: bool,
}

/// Propose or create tickets for design entities no live ticket implements; goal to epic, scenario to story, impl to task.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "plan",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Plan {
    apply: bool,
    findings: bool,
}

/// The ticket type a design kind is planned as, with its depth (goal 0, scenario 1, impl 2).
fn plan_type(kind: &str) -> Option<(usize, TicketType)> {
    match kind {
        "goal" => Some((0, TicketType::Epic)),
        "scenario" => Some((1, TicketType::Story)),
        "impl" => Some((2, TicketType::Task)),
        _ => None,
    }
}

/// The unplanned entities of `graph` in parent-first order, each paired with its type.
fn unplanned<'g>(
    graph: &'g DesignGraph,
    state: &BTreeMap<String, frob_ledger::design::AnchorOverlay>,
) -> Vec<(usize, TicketType, &'g Entity)> {
    let mut rows: Vec<_> = graph
        .entities()
        .filter(|e| e.status != Some(DesignStatus::Verified))
        .filter(|e| {
            state
                .get(&e.anchor)
                .is_some_and(|o| o.state == Overlay::Unplanned)
        })
        .filter_map(|e| plan_type(&e.kind).map(|(d, t)| (d, t, e)))
        .collect();
    rows.sort_by(|a, b| (a.0, &a.2.anchor).cmp(&(b.0, &b.2.anchor)));
    rows
}

/// The scope seeded for `entity`: its own files, or for a story the union of its children's.
fn seed_scope(graph: &DesignGraph, entity: &Entity) -> Vec<String> {
    let mut files: BTreeSet<String> = entity.files.iter().cloned().collect();
    if entity.kind == "scenario" {
        for child in graph.entities() {
            if child.anchor != entity.anchor
                && graph
                    .self_and_ancestors(&child.anchor)
                    .contains(&entity.anchor)
            {
                files.extend(child.files.iter().cloned());
            }
        }
    }
    files.into_iter().collect()
}

/// The acceptance criteria seeded for a ticket of `ty` implementing `entity`.
fn seed_acceptance(ty: TicketType, entity: &Entity) -> Vec<String> {
    match ty {
        TicketType::Story => vec![format!(
            "Given the scenario {} is set up, when it runs, then it reaches its terminal",
            entity.name
        )],
        TicketType::Task => vec![
            "Given the realization selectors and verified_by tests, when checked, then the selectors resolve and the tests pass"
                .to_owned(),
        ],
        _ => Vec::new(),
    }
}

/// Anchors that cannot be mapped: obligations on unmappable entities and `requires` targets outside the graph.
fn unmapped_anchors(graph: &DesignGraph) -> Vec<String> {
    let mut out = BTreeSet::new();
    for o in graph.obligations() {
        let mappable = graph
            .entity(&o.anchor)
            .is_some_and(|e| plan_type(&e.kind).is_some());
        if !mappable {
            out.insert(o.anchor.clone());
        }
    }
    for e in graph.entities() {
        for r in graph.requires_of(&e.anchor) {
            if graph
                .entity(&r)
                .is_none_or(|t| plan_type(&t.kind).is_none())
            {
                out.insert(r);
            }
        }
    }
    out.into_iter().collect()
}

/// Order `rows` so every row follows the rows it `requires` (cycles keep their original order).
fn order_by_requires<'g>(
    graph: &DesignGraph,
    rows: Vec<(usize, TicketType, &'g Entity)>,
) -> Vec<(usize, TicketType, &'g Entity)> {
    let mut pending = rows;
    let mut out = Vec::with_capacity(pending.len());
    while !pending.is_empty() {
        let waiting: BTreeSet<String> = pending.iter().map(|r| r.2.anchor.clone()).collect();
        let pos = pending
            .iter()
            .position(|r| {
                graph
                    .requires_of(&r.2.anchor)
                    .iter()
                    .all(|q| !waiting.contains(q) || *q == r.2.anchor)
            })
            .unwrap_or(0);
        out.push(pending.remove(pos));
    }
    out
}

impl Command for Plan {
    type Data = PlanData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<PlanArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<PlanArgs>(m)?;
        Ok(Self {
            apply: a.apply,
            findings: a.findings,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<PlanData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let graph = DesignGraph::load(&root)
            .map_err(|e| CliError::Usage(format!("cannot plan from design: {e}")))?;
        let ledger = open(ctx)?;
        let links = ledger.design_links().map_err(cli_err)?;
        let state = overlay(&graph, &links);
        // anchor -> ticket of every live implementer, so a child can name its parent
        let mut tickets: BTreeMap<String, TicketId> = state
            .values()
            .filter_map(|o| o.tickets.first().map(|t| (o.anchor.clone(), *t)))
            .collect();
        let mut rows = Vec::new();
        for (depth, ty, entity) in order_by_requires(&graph, unplanned(&graph, &state)) {
            let parent = graph
                .self_and_ancestors(&entity.anchor)
                .into_iter()
                .filter(|a| *a != entity.anchor)
                .filter(|a| {
                    graph
                        .entity(a)
                        .and_then(|e| plan_type(&e.kind))
                        .is_some_and(|(d, _)| d < depth)
                })
                .find_map(|a| tickets.get(&a).copied());
            let scope = seed_scope(&graph, entity);
            let blocked_anchors = graph.requires_of(&entity.anchor);
            let mut row = PlanRow {
                anchor: entity.anchor.clone(),
                ty: ty.as_str().to_owned(),
                title: entity.name.clone(),
                handle: None,
                scope: scope.clone(),
                blocked_by: blocked_anchors.clone(),
            };
            if self.apply {
                let mut req = NewTicket::new(entity.name.clone(), ty);
                req.implements = vec![link_of(&entity.anchor)];
                req.parent = parent;
                req.idempotency_key = Some(entity.anchor.clone());
                req.scope = scope;
                req.acceptance = seed_acceptance(ty, entity);
                req.blocked_by = blocked_anchors
                    .iter()
                    .filter_map(|a| tickets.get(a).copied())
                    .collect();
                if ty == TicketType::Story {
                    req.persona = Some("user".to_owned());
                    req.capability = Some(entity.name.clone());
                    req.outcome_text = Some("the scenario holds".to_owned());
                }
                let applied = ledger.new_ticket(req).map_err(cli_err)?;
                tickets.insert(entity.anchor.clone(), applied.ticket.front.id);
                row.handle = Some(applied.handle.clone());
                tracing::info!(anchor = %entity.anchor, handle = %applied.handle, "planned from design");
            } else {
                tracing::debug!(anchor = %entity.anchor, "would plan from design");
            }
            rows.push(row);
        }
        let unmapped = if self.findings {
            unmapped_anchors(&graph)
        } else {
            Vec::new()
        };
        for a in &unmapped {
            tracing::warn!(anchor = %a, "design anchor cannot be mapped to a ticket");
        }
        let mut text = if rows.is_empty() {
            vec!["every design entity is planned".to_owned()]
        } else {
            rows.iter()
                .map(|r| {
                    format!(
                        "{} {} {} {}",
                        if self.apply { "created" } else { "propose" },
                        r.ty,
                        r.anchor,
                        r.handle.as_deref().unwrap_or("")
                    )
                })
                .collect::<Vec<_>>()
        };
        text.extend(unmapped.iter().map(|a| format!("unmapped {a}")));
        Ok(Payload::new(PlanData {
            applied: self.apply,
            proposed: rows,
            unmapped,
        })
        .with_pretty(text))
    }
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<Plan>()
}
