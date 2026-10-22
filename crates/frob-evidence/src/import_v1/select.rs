//! The selection of the v1 import: which open v1 tickets carry requirements (~TM4E1PN).
//!
//! The selection is data (`docs/migration/v1-selection.toml`, generated from the v1 gap report B):
//! clusters list v1 ids and a disposition, overrides name single tickets. Closed v1 tickets
//! always import as closed history and are not listed. An open ticket that no cluster or override
//! names stops the run, so a new v1 ticket can never slip in or out unreviewed.

// frob:ticket 01M43A53W5X4PBCXWCTTM4E1PN
use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use super::{ImportError, ticket_err};

/// What the import does with one v1 ticket.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Disposition {
    /// Import as open work (a requirement-bearing ticket).
    ImportOpen,
    /// Import closed with outcome wont-fix and the reason, as history only.
    WontFixHistory,
    /// Not imported: v1 machinery that v2 removed on purpose.
    SkipDroppedOnPurpose,
    /// Not imported: v2 already provides the capability.
    SkipBuilt,
    /// Not imported: about a Python-v1 implementation detail with no v2 counterpart.
    SkipV1Internal,
    /// Not imported: already a v2 ticket.
    SkipTicketed,
    /// Not imported: superseded by a v2 design decision.
    SkipSuperseded,
    /// Closed v1 ticket (done or archived), imported as closed history (implicit).
    HistoryDone,
    /// Dropped v1 ticket, imported as closed wont-fix history (implicit).
    HistoryDropped,
}

impl Disposition {
    /// The kebab-case name used in the selection file and the report.
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::ImportOpen => "import-open",
            Self::WontFixHistory => "wont-fix-history",
            Self::SkipDroppedOnPurpose => "skip-dropped-on-purpose",
            Self::SkipBuilt => "skip-built",
            Self::SkipV1Internal => "skip-v1-internal",
            Self::SkipTicketed => "skip-ticketed",
            Self::SkipSuperseded => "skip-superseded",
            Self::HistoryDone => "history-done",
            Self::HistoryDropped => "history-dropped",
        }
    }

    /// Whether a ticket with this disposition becomes a v2 ticket at all.
    #[must_use]
    pub fn imports(self) -> bool {
        matches!(
            self,
            Self::ImportOpen | Self::WontFixHistory | Self::HistoryDone | Self::HistoryDropped
        )
    }
}

/// One cluster of the selection file.
#[derive(Debug, Clone, Deserialize)]
pub struct Cluster {
    /// The cluster title from the B report.
    pub title: String,
    /// The B report status (BUILT, DESIGNED, MISSING, ...), informational.
    pub status: String,
    /// What happens to every ticket of the cluster.
    pub disposition: Disposition,
    /// Optional `area:<value>` label for imported tickets (crunk, per D88).
    #[serde(default)]
    pub area: Option<String>,
    /// The v1 ids (`T-1234`) in the cluster.
    pub ids: Vec<String>,
}

/// A per-ticket override of its cluster's disposition.
#[derive(Debug, Clone, Deserialize)]
pub struct Override {
    /// The disposition of this ticket.
    pub disposition: Disposition,
    /// Why (a proposed-ticket number or the v2 evidence).
    pub reason: String,
}

#[derive(Debug, Deserialize)]
struct SelectionFile {
    #[serde(default)]
    cluster: BTreeMap<String, Cluster>,
    #[serde(default, rename = "override")]
    overrides: BTreeMap<String, Override>,
    #[serde(default)]
    area: BTreeMap<String, String>,
}

/// The decision for one v1 ticket.
#[derive(Debug, Clone)]
pub struct Decision {
    /// What to do.
    pub disposition: Disposition,
    /// The cluster id (`B4`), for open tickets.
    pub cluster: Option<String>,
    /// The `area:` label value, if any.
    pub area: Option<String>,
    /// Why, when an override or a closing disposition carries one.
    pub reason: Option<String>,
}

/// The parsed selection file.
#[derive(Debug, Clone)]
pub struct Selection {
    clusters: BTreeMap<String, Cluster>,
    overrides: BTreeMap<String, Override>,
    areas: BTreeMap<String, String>,
    cluster_of: BTreeMap<String, String>,
}

impl Selection {
    /// Parse the selection file text; rejects a ticket listed in two clusters or an override for an unknown ticket.
    ///
    /// # Errors
    ///
    /// [`ImportError::Ticket`] naming the selection file for malformed TOML or inconsistent entries.
    pub fn parse(text: &str) -> Result<Self, ImportError> {
        let file: SelectionFile =
            toml::from_str(text).map_err(|e| ticket_err("selection", e.to_string()))?;
        let mut cluster_of = BTreeMap::new();
        for (name, c) in &file.cluster {
            for id in &c.ids {
                if let Some(prev) = cluster_of.insert(id.clone(), name.clone()) {
                    return Err(ticket_err(
                        "selection",
                        format!("{id} is in clusters {prev} and {name}"),
                    ));
                }
            }
        }
        for id in file.overrides.keys().chain(file.area.keys()) {
            if !cluster_of.contains_key(id) {
                return Err(ticket_err(
                    "selection",
                    format!("override or area for {id}, which is in no cluster"),
                ));
            }
        }
        tracing::info!(
            clusters = file.cluster.len(),
            overrides = file.overrides.len(),
            tickets = cluster_of.len(),
            "selection loaded"
        );
        Ok(Self {
            clusters: file.cluster,
            overrides: file.overrides,
            areas: file.area,
            cluster_of,
        })
    }

    /// The decision for an open v1 ticket, or `None` when no cluster names it.
    #[must_use]
    pub fn decide(&self, v1_id: &str) -> Option<Decision> {
        let name = self.cluster_of.get(v1_id)?;
        let c = &self.clusters[name];
        let ov = self.overrides.get(v1_id);
        let disposition = ov.map_or(c.disposition, |o| o.disposition);
        let reason = match ov {
            Some(o) => Some(o.reason.clone()),
            None => (!disposition.imports() || disposition == Disposition::WontFixHistory)
                .then(|| format!("v1 cluster {name} ({}): {}", c.status, c.title)),
        };
        Some(Decision {
            disposition,
            cluster: Some(name.clone()),
            area: (disposition == Disposition::ImportOpen)
                .then(|| self.areas.get(v1_id).or(c.area.as_ref()).cloned())
                .flatten(),
            reason,
        })
    }

    /// Open v1 ids that the selection names but the ledger does not hold open (stale entries), sorted.
    #[must_use]
    pub fn stale(&self, open: &BTreeSet<String>) -> Vec<String> {
        self.cluster_of
            .keys()
            .filter(|id| !open.contains(*id))
            .cloned()
            .collect()
    }
}

/// The decision for a closed v1 ticket (done, archived or dropped).
#[must_use]
pub fn closed_decision(dropped: bool) -> Decision {
    Decision {
        disposition: if dropped {
            Disposition::HistoryDropped
        } else {
            Disposition::HistoryDone
        },
        cluster: None,
        area: None,
        reason: None,
    }
}

/// An open v1 ticket that would import, for the dry-run list.
#[derive(Debug, Clone, Serialize)]
pub struct OpenRow {
    /// The v1 id.
    pub v1: String,
    /// The cluster id.
    pub cluster: String,
    /// The `area:` label value, if any.
    pub area: Option<String>,
    /// The v1 priority.
    pub priority: String,
    /// The v1 title (after redaction).
    pub title: String,
    /// The override reason, if the ticket was selected individually.
    pub reason: Option<String>,
}

/// A ticket that is not imported as open work, for the dry-run report.
#[derive(Debug, Clone, Serialize)]
pub struct SkipRow {
    /// The v1 id.
    pub v1: String,
    /// The disposition name.
    pub disposition: String,
    /// The cluster id.
    pub cluster: String,
    /// The reason.
    pub reason: String,
}

/// Render the selection part of a dry run: counts per disposition, skips per cluster, the open list.
#[must_use]
pub fn render_selection(
    counts: &BTreeMap<String, usize>,
    open: &[OpenRow],
    skipped: &[SkipRow],
) -> Vec<String> {
    let mut out = vec!["== disposition counts ==".to_owned()];
    out.extend(counts.iter().map(|(k, v)| format!("{k:<26} {v}")));
    out.push(format!(
        "{:<26} {}",
        "total",
        counts.values().sum::<usize>()
    ));
    let mut per: BTreeMap<(String, String), usize> = BTreeMap::new();
    for s in skipped {
        *per.entry((s.disposition.clone(), s.cluster.clone()))
            .or_default() += 1;
    }
    out.push(String::new());
    out.push("== not imported as open work, per disposition and cluster ==".to_owned());
    out.extend(per.iter().map(|((d, c), n)| format!("{d:<26} {c:<5} {n}")));
    let mut areas: BTreeMap<&str, usize> = BTreeMap::new();
    for r in open {
        *areas
            .entry(r.area.as_deref().unwrap_or("(none)"))
            .or_default() += 1;
    }
    out.push(String::new());
    out.push("== open tickets that would import, per area ==".to_owned());
    out.extend(areas.iter().map(|(a, n)| format!("area:{a:<12} {n}")));
    out.push(String::new());
    out.push(format!(
        "== open tickets that would import ({}) ==",
        open.len()
    ));
    out.push("v1       cluster area   priority title".to_owned());
    out.extend(open.iter().map(|r| {
        format!(
            "{:<8} {:<7} {:<6} {:<8} {}{}",
            r.v1,
            r.cluster,
            r.area.as_deref().unwrap_or("-"),
            r.priority,
            r.title,
            r.reason
                .as_ref()
                .map_or(String::new(), |x| format!("  [override: {x}]"))
        )
    }));
    out
}
