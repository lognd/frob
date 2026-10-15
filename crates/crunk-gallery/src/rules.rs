//! GALLERY001 to GALLERY005.
//!
//! GALLERY has its own dispatch (its input is a manifest, not a file), so these are plain functions
//! rather than `#[rule]` declarations. Severity comes from the spec (`[lint]` over the catalog);
//! a rule set to `off` yields nothing.
//!
//! - GALLERY001: a cell has no render.
//! - GALLERY002: a cell's render is not approved (no verdict, or still pending).
//! - GALLERY003: an approval has expired (`expires_at` is before today).
//! - GALLERY004: a cell's render was rejected.
//! - GALLERY005 (warn): a route the router declares has no screen.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use crunk_spec::{DesignSpec, Severity};
use gob_time::Day;
use serde::Serialize;

use crate::cells::Cell;
use crate::manifest::{Manifest, Status};

/// One rule finding.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Finding {
    /// Rule id, `GALLERY001` to `GALLERY005`.
    pub rule: &'static str,
    /// Effective severity (never `off`).
    pub severity: Severity,
    /// What is wrong and how to fix it.
    pub message: String,
    /// Screen concerned.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub screen: Option<String>,
    /// State concerned.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub state: Option<String>,
    /// Platform concerned.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub platform: Option<String>,
}

fn finding(
    spec: &DesignSpec,
    rule: &'static str,
    message: String,
    cell: Option<&Cell>,
) -> Option<Finding> {
    let severity = spec.severity(rule);
    (severity != Severity::Off).then(|| Finding {
        rule,
        severity,
        message,
        screen: cell.map(|c| c.screen.clone()),
        state: cell.map(|c| c.state.clone()),
        platform: cell.map(|c| c.platform.clone()),
    })
}

/// GALLERY001 to GALLERY004 over `cells` against `manifest`, judged as of `today`.
pub fn check_cells(
    spec: &DesignSpec,
    cells: &[Cell],
    manifest: &Manifest,
    today: Day,
) -> Vec<Finding> {
    let mut out = Vec::new();
    for cell in cells {
        let label = format!("{}/{} on {}", cell.screen, cell.state, cell.platform);
        let entry = manifest.find(&cell.screen, &cell.state, &cell.platform);
        let rendered = entry.is_some_and(|e| e.render.is_some());
        if !rendered {
            out.extend(finding(
                spec,
                "GALLERY001",
                format!("{label} has no render; run the gallery render, then triage it"),
                Some(cell),
            ));
            continue;
        }
        let verdict = entry.and_then(|e| e.verdict.as_ref());
        match verdict.map(|v| v.status) {
            None | Some(Status::Pending) => out.extend(finding(
                spec,
                "GALLERY002",
                format!("{label} is rendered but not approved; triage it"),
                Some(cell),
            )),
            Some(Status::Rejected) => out.extend(finding(
                spec,
                "GALLERY004",
                format!("{label} was rejected; fix the screen and render it again"),
                Some(cell),
            )),
            Some(Status::Approved) => {
                let expiry = verdict.and_then(|v| v.expires_at.as_deref());
                let expires = expiry.and_then(|d| d.parse::<Day>().ok());
                if let Some(expires) = expires.filter(|e| *e < today) {
                    out.extend(finding(
                        spec,
                        "GALLERY003",
                        format!("{label} approval expired on {expires}; review it again"),
                        Some(cell),
                    ));
                }
            }
        }
    }
    tracing::debug!(
        findings = out.len(),
        cells = cells.len(),
        "gallery cell rules run"
    );
    out
}

/// A route reduced to its comparable path: no query or fragment, no trailing slash (but `/`).
pub fn normalize_route(route: &str) -> String {
    let path = route.split(['?', '#']).next().unwrap_or("");
    let trimmed = path.trim_end_matches('/');
    if trimmed.is_empty() {
        "/".to_owned()
    } else {
        trimmed.to_owned()
    }
}

/// GALLERY005: each of `routes` (as the router declares them) that no screen `entry` covers.
///
/// The `*` catch-all never needs a screen.
pub fn check_routes(spec: &DesignSpec, routes: &[String]) -> Vec<Finding> {
    let covered: Vec<String> = spec
        .screens
        .values()
        .map(|s| normalize_route(&s.entry))
        .collect();
    let mut out = Vec::new();
    for route in routes.iter().filter(|r| r.trim() != "*") {
        if !covered.contains(&normalize_route(route)) {
            out.extend(finding(
                spec,
                "GALLERY005",
                format!("route {route} has no [[screen]] with that entry"),
                None,
            ));
        }
    }
    out
}
