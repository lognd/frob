//! The frob join with grimble planning entities (pm-and-releases.md section 10, grmb-spec.md 17).
//!
//! A ticket's `implements design:<anchor>` link is validated against `grimble graph --json`
//! (`grimble.graph/1`), and the ledger overlay (planned, in-progress, done, test verdict) is computed
//! onto each linked anchor. grimble never reads tickets (D28); this module only reads its graph export.

// frob:ticket 01M6BYKR12BCNQ3P3BR3J3AR58
// frob:ticket 01M4FDBDC401KMNN4C12QTA3PK
// frob:ticket 01M6BYM5XMG4WD49JAQXZR3S4S

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};

use serde_json::Value;

use crate::id::TicketId;
use crate::model::{Category, Outcome};

/// The prefix that marks a design link target (`design:impl/web_app.checkout.system.shows_total`).
pub const LINK_PREFIX: &str = "design:";

/// A failure to read or use the grimble graph export.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum DesignError {
    /// The link is not `design:<kind>/<name>`.
    #[error(
        "`{0}` is not a design link; write `design:<kind>/<name>`, for example `design:impl/web_app.checkout.system.shows_total`"
    )]
    BadLink(String),
    /// The anchor is well formed but names no entity of the graph.
    #[error("design anchor `{anchor}` is not in the grimble graph{hint}")]
    UnknownAnchor {
        /// The refused anchor.
        anchor: String,
        /// A ready-made `; did you mean ...` suffix (possibly empty).
        hint: String,
    },
    /// `grimble` is absent, failed, or printed something that is not a graph.
    #[error("grimble graph is unavailable: {0}")]
    Unavailable(String),
}

/// A design status rung of grmb-spec 12.8, ordered `declared < bound < verified`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum DesignStatus {
    /// Nothing binds the entity yet.
    Declared,
    /// A realization binds it.
    Bound,
    /// Its own evidence passes.
    Verified,
}

impl DesignStatus {
    /// The rung named by `s`, or `None` for an unknown word.
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "declared" => Some(Self::Declared),
            "bound" => Some(Self::Bound),
            "verified" => Some(Self::Verified),
            _ => None,
        }
    }

    /// The rung's graph-JSON word.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Declared => "declared",
            Self::Bound => "bound",
            Self::Verified => "verified",
        }
    }
}

/// One planning entity of the graph.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entity {
    /// The entity anchor such as `impl/web_app.checkout.system.shows_total`.
    pub anchor: String,
    /// The entity kind (`goal`, `scenario`, `impl`, ...).
    pub kind: String,
    /// Design status from `lo`; `None` for a non-planning kind.
    pub status: Option<DesignStatus>,
    /// Design status from `hi`.
    pub status_hi: Option<DesignStatus>,
    /// The entity's doc summary or name, used as a ticket title.
    pub name: String,
    /// Realization and `verified_by` files the export names for the entity; seeds a ticket scope.
    pub files: Vec<String>,
}

/// One PLAN obligation of the graph (`unrealized_goal`, `unimplemented_step`, `unbound_impl`, ...).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Obligation {
    /// The PLAN rule id that reported it.
    pub rule: String,
    /// The obligation kind.
    pub kind: String,
    /// The entity it is about.
    pub anchor: String,
    /// The human detail.
    pub detail: String,
}

/// The parsed `grimble graph --json` export: entities, obligations and the design ancestry edges.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DesignGraph {
    entities: BTreeMap<String, Entity>,
    obligations: Vec<Obligation>,
    // child anchor -> parent anchors, over `impl_for`, `realizes` and `refines` edges
    ancestors: BTreeMap<String, BTreeSet<String>>,
    // anchor -> anchors it `requires` (a goal's prerequisite goals)
    requires: BTreeMap<String, BTreeSet<String>>,
}

/// The anchor of a `design:<anchor>` link, or an error when the shape is wrong.
///
/// # Errors
///
/// [`DesignError::BadLink`] when the prefix or the `<kind>/<name>` shape is missing.
pub fn anchor_of(link: &str) -> Result<&str, DesignError> {
    let bad = || DesignError::BadLink(link.to_owned());
    let anchor = link.strip_prefix(LINK_PREFIX).ok_or_else(bad)?;
    match anchor.split_once('/') {
        Some((kind, name))
            if !kind.is_empty()
                && !name.is_empty()
                && kind.chars().all(|c| c.is_ascii_lowercase() || c == '_')
                && !anchor.contains(char::is_whitespace) =>
        {
            Ok(anchor)
        }
        _ => Err(bad()),
    }
}

/// The `design:` link text for `anchor`.
pub fn link_of(anchor: &str) -> String {
    format!("{LINK_PREFIX}{anchor}")
}

impl DesignGraph {
    /// Parse a `grimble graph --json` envelope (the entities live under `data`, or at top level).
    ///
    /// # Errors
    ///
    /// [`DesignError::Unavailable`] when `json` is not a graph document.
    pub fn from_json(json: &str) -> Result<Self, DesignError> {
        let doc: Value = serde_json::from_str(json)
            .map_err(|e| DesignError::Unavailable(format!("not JSON: {e}")))?;
        let data = if doc["data"].is_object() {
            &doc["data"]
        } else {
            &doc
        };
        let Some(entities) = data["entities"].as_array() else {
            return Err(DesignError::Unavailable("no `entities` array".to_owned()));
        };
        let text = |v: &Value, k: &str| v[k].as_str().unwrap_or_default().to_owned();
        let mut graph = Self::default();
        for e in entities {
            let anchor = text(e, "anchor");
            if anchor.is_empty() {
                continue;
            }
            let entity = Entity {
                kind: text(e, "kind"),
                status: e["status"].as_str().and_then(DesignStatus::parse),
                status_hi: e["status_hi"].as_str().and_then(DesignStatus::parse),
                name: text(e, "name"),
                files: e["files"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .filter_map(|f| f.as_str().map(str::to_owned))
                    .collect(),
                anchor: anchor.clone(),
            };
            graph.entities.insert(anchor, entity);
        }
        for o in data["obligations"].as_array().into_iter().flatten() {
            graph.obligations.push(Obligation {
                rule: text(o, "rule"),
                kind: text(o, "kind"),
                anchor: text(o, "anchor"),
                detail: text(o, "detail"),
            });
        }
        for edge in data["edges"].as_array().into_iter().flatten() {
            if edge["kind"].as_str() == Some("requires")
                && let (Some(from), Some(to)) = (edge["from"].as_str(), edge["to"].as_str())
            {
                graph
                    .requires
                    .entry(from.to_owned())
                    .or_default()
                    .insert(to.to_owned());
            }
            if matches!(
                edge["kind"].as_str(),
                Some("impl_for" | "impl_of" | "realizes" | "refines")
            ) && let (Some(from), Some(to)) = (edge["from"].as_str(), edge["to"].as_str())
            {
                graph
                    .ancestors
                    .entry(from.to_owned())
                    .or_default()
                    .insert(to.to_owned());
            }
        }
        tracing::debug!(
            entities = graph.entities.len(),
            obligations = graph.obligations.len(),
            "design graph parsed"
        );
        Ok(graph)
    }

    /// Run `grimble graph --json` in `root` and parse it; `grimble` is the sibling of the running executable, else on `PATH`.
    ///
    /// # Errors
    ///
    /// [`DesignError::Unavailable`] when grimble is absent, exits non-zero or prints no graph.
    pub fn load(root: &Path) -> Result<Self, DesignError> {
        // FROB_GRIMBLE pins the binary (tests, odd installs); otherwise the sibling beside frob, then PATH.
        let program = match std::env::var_os("FROB_GRIMBLE") {
            Some(path) => Program::Hook {
                path: std::path::PathBuf::from(path),
            },
            None => Program::Sibling {
                name: "grimble".to_owned(),
            },
        };
        tracing::debug!(?program, root = ?root, "running grimble graph --json");
        let spec = Spec {
            program,
            args: vec!["graph".to_owned(), "--json".to_owned()],
            cwd: Some(root.to_path_buf()),
            env: Vec::new(),
            timeout: Duration::from_secs(120),
            capture: true,
        };
        let out = Runner::new(Limits::default())
            .run(&spec)
            .map_err(|e| DesignError::Unavailable(format!("cannot run grimble: {e}")))?;
        if out.status != ExecOutcome::Exited(0) {
            tracing::warn!(status = ?out.status, "grimble graph failed");
            return Err(DesignError::Unavailable(format!(
                "grimble graph ended with {:?}",
                out.status
            )));
        }
        Self::from_json(&out.stdout_raw)
    }

    /// The entity at `anchor`, if the graph has it.
    pub fn entity(&self, anchor: &str) -> Option<&Entity> {
        self.entities.get(anchor)
    }

    /// Every entity, ordered by anchor.
    pub fn entities(&self) -> impl Iterator<Item = &Entity> {
        self.entities.values()
    }

    /// Every obligation of the graph, ordered as grimble listed them.
    pub fn obligations(&self) -> &[Obligation] {
        &self.obligations
    }

    /// Validate a `design:<anchor>` link against the graph and return its entity.
    ///
    /// # Errors
    ///
    /// [`DesignError::BadLink`] for a malformed link; [`DesignError::UnknownAnchor`] when the graph lacks the anchor.
    pub fn validate(&self, link: &str) -> Result<&Entity, DesignError> {
        let anchor = anchor_of(link)?;
        self.entities.get(anchor).ok_or_else(|| {
            let prefix = anchor.rsplit_once('.').map_or(anchor, |(p, _)| p);
            let near = self
                .entities
                .keys()
                .find(|k| k.starts_with(prefix) && k.split('/').next() == anchor.split('/').next());
            tracing::debug!(anchor, "design anchor not in graph");
            DesignError::UnknownAnchor {
                anchor: anchor.to_owned(),
                hint: near.map_or_else(String::new, |n| format!("; did you mean `{n}`?")),
            }
        })
    }

    /// The anchors `anchor` directly `requires`, in order.
    pub fn requires_of(&self, anchor: &str) -> Vec<String> {
        self.requires
            .get(anchor)
            .into_iter()
            .flatten()
            .cloned()
            .collect()
    }

    /// `anchor` and every design ancestor of it (impl to scenario and step, scenario to goal, goal to parent goal).
    pub fn self_and_ancestors(&self, anchor: &str) -> BTreeSet<String> {
        let mut seen = BTreeSet::new();
        let mut stack = vec![anchor.to_owned()];
        while let Some(a) = stack.pop() {
            if !seen.insert(a.clone()) {
                continue;
            }
            stack.extend(self.ancestors.get(&a).into_iter().flatten().cloned());
        }
        seen
    }
}

/// The ledger facts about one ticket that the overlay needs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TicketFacts {
    /// The ticket.
    pub id: TicketId,
    /// Its workflow category.
    pub category: Category,
    /// Its outcome, when done.
    pub outcome: Option<Outcome>,
}

impl TicketFacts {
    /// True unless the ticket ended `wont-fix`, `invalid` or `duplicate` (those do not plan anything).
    pub fn is_live(&self) -> bool {
        !matches!(
            self.outcome,
            Some(Outcome::WontFix | Outcome::Invalid | Outcome::Duplicate)
        )
    }
}

/// The overlay state of one anchor (pm-and-releases.md 10.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Overlay {
    /// No live ticket implements the entity.
    Unplanned,
    /// A live ticket implements it and none has started.
    Planned,
    /// A live implementing ticket is in progress, or only some are done.
    InProgress,
    /// Every live implementing ticket is done, and there is at least one.
    Done,
}

impl Overlay {
    /// The overlay word for output.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Unplanned => "unplanned",
            Self::Planned => "planned",
            Self::InProgress => "in-progress",
            Self::Done => "done",
        }
    }
}

/// The overlay of one anchor: its state, implementing tickets and the grimble test verdict.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorOverlay {
    /// The anchor.
    pub anchor: String,
    /// The ledger state.
    pub state: Overlay,
    /// The live tickets implementing it.
    pub tickets: Vec<TicketId>,
    /// The graph's `status` for the entity: the test verdict (`verified` when its evidence passes).
    pub verdict: Option<DesignStatus>,
}

/// Compute the overlay of every anchor in `graph` from the tickets and the anchors each implements.
///
/// `links` pairs a ticket with its `design:` link texts; a link to an anchor the graph lacks is ignored here
/// (validation refused it already).
pub fn overlay(
    graph: &DesignGraph,
    links: &[(TicketFacts, Vec<String>)],
) -> BTreeMap<String, AnchorOverlay> {
    let mut by_anchor: BTreeMap<&str, Vec<TicketFacts>> = BTreeMap::new();
    for (facts, targets) in links {
        if !facts.is_live() {
            continue;
        }
        for target in targets {
            if let Ok(anchor) = anchor_of(target) {
                by_anchor.entry(anchor).or_default().push(*facts);
            }
        }
    }
    graph
        .entities()
        .map(|e| {
            let tickets = by_anchor
                .get(e.anchor.as_str())
                .cloned()
                .unwrap_or_default();
            let done = tickets
                .iter()
                .filter(|t| t.category == Category::Done)
                .count();
            let started = tickets.iter().any(|t| t.category == Category::InProgress);
            let state = if tickets.is_empty() {
                Overlay::Unplanned
            } else if done == tickets.len() {
                Overlay::Done
            } else if started || done > 0 {
                Overlay::InProgress
            } else {
                Overlay::Planned
            };
            (
                e.anchor.clone(),
                AnchorOverlay {
                    anchor: e.anchor.clone(),
                    state,
                    tickets: tickets.iter().map(|t| t.id).collect(),
                    verdict: e.status,
                },
            )
        })
        .collect()
}

// frob:ticket 01M6BYM5XMG4WD49JAQXZR3S4S
/// The verdict of one `manual` `verified_by` row (grmb-spec 12.8, D202).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RowVerdict {
    /// A passed attestation on a live implementing ticket carries the row's anchor.
    Pass,
    /// No such attestation exists.
    NotRun,
}

// frob:ticket 01M6BYM5XMG4WD49JAQXZR3S4S
/// Split a design clause anchor `KIND/NAME/verified_by[i]` into its entity anchor and clause index, or `None` when the shape is wrong.
pub fn row_anchor_parts(row: &str) -> Option<(&str, usize)> {
    let (entity, clause) = row.rsplit_once('/')?;
    let index = clause
        .strip_prefix("verified_by[")?
        .strip_suffix(']')?
        .parse::<usize>()
        .ok()?;
    let (kind, name) = entity.split_once('/')?;
    let well_formed = !kind.is_empty()
        && !name.is_empty()
        && kind.chars().all(|c| c.is_ascii_lowercase() || c == '_')
        && !row.contains(char::is_whitespace);
    well_formed.then_some((entity, index))
}

// frob:ticket 01M6BYM5XMG4WD49JAQXZR3S4S
/// The verdict of the `manual` row `row`: `Pass` when a passed attestation carrying `row` sits on a live ticket implementing the entity or a design ancestor.
///
/// `links` pairs each ticket with its `design:` link texts (as for [`overlay`]); `passed` pairs a ticket with the facts of each of its passed attestations. A row whose entity the graph lacks is `NotRun`.
pub fn manual_row_verdict(
    graph: &DesignGraph,
    links: &[(TicketFacts, Vec<String>)],
    passed: &[(TicketId, Vec<String>)],
    row: &str,
) -> RowVerdict {
    let Some((entity, _)) = row_anchor_parts(row) else {
        tracing::debug!(row, "not a design clause anchor");
        return RowVerdict::NotRun;
    };
    if graph.entity(entity).is_none() {
        tracing::debug!(row, "manual row names an entity the graph lacks");
        return RowVerdict::NotRun;
    }
    let reach = graph.self_and_ancestors(entity);
    let verdict = passed
        .iter()
        .filter(|(_, facts)| facts.iter().any(|f| f == row))
        .any(|(ticket, _)| {
            links.iter().any(|(facts, targets)| {
                facts.id == *ticket
                    && facts.is_live()
                    && targets
                        .iter()
                        .filter_map(|t| anchor_of(t).ok())
                        .any(|a| reach.contains(a))
            })
        });
    tracing::debug!(row, verdict, "manual row verdict");
    if verdict {
        RowVerdict::Pass
    } else {
        RowVerdict::NotRun
    }
}

/// PM038: a task whose implemented entity is still `declared` at `status_hi` may not close as done.
#[derive(Debug, Clone)]
pub struct DesignBoundGuard {
    root: std::path::PathBuf,
}

impl DesignBoundGuard {
    /// A guard that loads the grimble graph from `root` only when the closing ticket implements a design anchor.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }
}

impl crate::guards::CloseGuard for DesignBoundGuard {
    fn name(&self) -> &'static str {
        "design_bound"
    }

    fn check(
        &self,
        cx: &crate::guards::CloseContext<'_>,
    ) -> Result<(), crate::guards::GuardFailure> {
        let links = &cx.ticket.front.implements;
        if links.is_empty() || cx.outcome != Some(Outcome::Done) {
            return Ok(());
        }
        let fail = |message: String, remedy: &str| crate::guards::GuardFailure {
            code: "PM038".to_owned(),
            message,
            remedy: Some(remedy.to_owned()),
        };
        let graph = DesignGraph::load(&self.root).map_err(|e| {
            tracing::warn!(ticket = cx.handle, error = %e, "design_bound cannot read the graph");
            fail(
                format!(
                    "PM038: {} implements design anchors but the graph is unavailable ({e})",
                    cx.handle
                ),
                "install grimble and fix the model, then retry the close",
            )
        })?;
        judge(&graph, cx)
    }
}

/// Apply PM038 to one closing ticket against an already loaded graph.
///
/// # Errors
///
/// A [`crate::guards::GuardFailure`] (PM038) when an implemented anchor is still declared at `status_hi`.
pub fn judge(
    graph: &DesignGraph,
    cx: &crate::guards::CloseContext<'_>,
) -> Result<(), crate::guards::GuardFailure> {
    let links = &cx.ticket.front.implements;
    let fail = |message: String, remedy: &str| crate::guards::GuardFailure {
        code: "PM038".to_owned(),
        message,
        remedy: Some(remedy.to_owned()),
    };
    for link in links {
        let entity = graph.validate(link).map_err(|e| {
            fail(
                format!("PM038: {} implements `{link}`: {e}", cx.handle),
                "frob ticket new --implements <valid anchor>",
            )
        })?;
        if entity.status_hi == Some(DesignStatus::Declared) {
            tracing::info!(ticket = cx.handle, anchor = %entity.anchor, "design_bound refused: still declared");
            return Err(fail(
                format!(
                    "PM038: {} implements `{link}` whose status_hi is still declared; closing as done would leave the design unbound",
                    cx.handle
                ),
                "bind the entity (realize it with a frob:ticket directive and evidence), or close with --outcome wont-fix",
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const GRAPH: &str = r#"{"data":{"entities":[
      {"anchor":"goal/w.c.place","kind":"goal","name":"place","status":"declared","status_hi":"declared"},
      {"anchor":"scenario/w.checkout","kind":"scenario","name":"checkout","status":"declared","status_hi":"declared"},
      {"anchor":"impl/w.checkout.system.shows","kind":"impl","name":"shows","status":"declared","status_hi":"declared"},
      {"anchor":"impl/w.checkout.system.pays","kind":"impl","name":"pays","status":"bound","status_hi":"verified"}],
     "obligations":[{"rule":"PLAN009","kind":"unbound_impl","anchor":"impl/w.checkout.system.shows","detail":"d"}],
     "edges":[{"from":"impl/w.checkout.system.shows","kind":"impl_for","to":"scenario/w.checkout"},
              {"from":"scenario/w.checkout","kind":"realizes","to":"goal/w.c.place"}]}}"#;

    fn id() -> TicketId {
        TicketId::mint()
    }

    // frob:tests crates/frob-ledger/src/design.rs::DesignGraph.from_json
    // frob:tests crates/frob-ledger/src/design.rs::DesignGraph.validate
    // frob:tests crates/frob-ledger/src/design.rs::anchor_of
    #[test]
    fn an_unknown_or_malformed_anchor_is_refused_and_a_known_one_resolves() {
        let g = DesignGraph::from_json(GRAPH).expect("graph");
        assert_eq!(g.entities().count(), 4);
        assert!(g.validate("design:impl/w.checkout.system.shows").is_ok());
        assert!(matches!(
            g.validate("design:impl/w.checkout.system.nope"),
            Err(DesignError::UnknownAnchor { .. })
        ));
        assert!(matches!(
            g.validate("impl/w.checkout"),
            Err(DesignError::BadLink(_))
        ));
        assert!(matches!(
            anchor_of("design:nokind"),
            Err(DesignError::BadLink(_))
        ));
        assert!(matches!(
            DesignGraph::from_json("{}"),
            Err(DesignError::Unavailable(_))
        ));
    }

    // frob:tests crates/frob-ledger/src/design.rs::DesignGraph.self_and_ancestors
    #[test]
    fn ancestry_walks_impl_scenario_goal() {
        let g = DesignGraph::from_json(GRAPH).expect("graph");
        let up = g.self_and_ancestors("impl/w.checkout.system.shows");
        assert!(up.contains("scenario/w.checkout") && up.contains("goal/w.c.place"));
    }

    // frob:tests crates/frob-ledger/src/design.rs::overlay
    // frob:tests crates/frob-ledger/src/design.rs::TicketFacts.is_live
    #[test]
    fn the_overlay_folds_live_tickets_onto_the_anchor() {
        let g = DesignGraph::from_json(GRAPH).expect("graph");
        let a = "design:impl/w.checkout.system.shows".to_owned();
        let facts = |category, outcome| TicketFacts {
            id: id(),
            category,
            outcome,
        };
        let state = |links: Vec<(TicketFacts, Vec<String>)>| {
            overlay(&g, &links)["impl/w.checkout.system.shows"].state
        };
        assert_eq!(state(vec![]), Overlay::Unplanned);
        let todo = (facts(Category::Todo, None), vec![a.clone()]);
        let prog = (facts(Category::InProgress, None), vec![a.clone()]);
        let done = (facts(Category::Done, Some(Outcome::Done)), vec![a.clone()]);
        let dead = (
            facts(Category::Done, Some(Outcome::WontFix)),
            vec![a.clone()],
        );
        assert_eq!(state(vec![todo.clone()]), Overlay::Planned);
        assert_eq!(state(vec![prog]), Overlay::InProgress);
        assert_eq!(state(vec![done.clone(), todo]), Overlay::InProgress);
        assert_eq!(state(vec![done.clone(), dead.clone()]), Overlay::Done);
        assert_eq!(state(vec![dead]), Overlay::Unplanned);
        let o = overlay(&g, &[done]);
        assert_eq!(
            o["impl/w.checkout.system.pays"].verdict,
            Some(DesignStatus::Bound)
        );
    }

    // frob:tests crates/frob-ledger/src/design.rs::manual_row_verdict
    // frob:tests crates/frob-ledger/src/design.rs::row_anchor_parts
    #[test]
    fn a_passed_attestation_on_an_implementing_or_ancestor_ticket_passes_the_manual_row() {
        let g = DesignGraph::from_json(GRAPH).expect("graph");
        let row = "impl/w.checkout.system.shows/verified_by[0]";
        assert_eq!(
            row_anchor_parts(row),
            Some(("impl/w.checkout.system.shows", 0))
        );
        assert_eq!(row_anchor_parts("impl/x/verified_by[a]"), None);
        assert_eq!(row_anchor_parts("impl/x"), None);
        let tid = id();
        let facts = |outcome| TicketFacts {
            id: tid,
            category: Category::Done,
            outcome,
        };
        let on = |link: &str, outcome| vec![(facts(outcome), vec![link.to_owned()])];
        let passed = vec![(tid, vec![row.to_owned()])];
        let verdict =
            |links: &[(TicketFacts, Vec<String>)], p, r| manual_row_verdict(&g, links, p, r);
        let own = on("design:impl/w.checkout.system.shows", Some(Outcome::Done));
        let ancestor = on("design:goal/w.c.place", Some(Outcome::Done));
        let dead = on(
            "design:impl/w.checkout.system.shows",
            Some(Outcome::WontFix),
        );
        let sibling = on("design:impl/w.checkout.system.pays", Some(Outcome::Done));
        assert_eq!(verdict(&own, &passed, row), RowVerdict::Pass);
        assert_eq!(verdict(&ancestor, &passed, row), RowVerdict::Pass);
        assert_eq!(verdict(&dead, &passed, row), RowVerdict::NotRun);
        assert_eq!(verdict(&sibling, &passed, row), RowVerdict::NotRun);
        assert_eq!(verdict(&own, &[], row), RowVerdict::NotRun);
        let other = vec![(
            tid,
            vec!["impl/w.checkout.system.shows/verified_by[1]".to_owned()],
        )];
        assert_eq!(verdict(&own, &other, row), RowVerdict::NotRun);
        let unknown = "impl/w.nope/verified_by[0]";
        let p2 = vec![(tid, vec![unknown.to_owned()])];
        assert_eq!(verdict(&own, &p2, unknown), RowVerdict::NotRun);
    }
}
