//! Solver-browser parity: compare the solver's boxes with the browser's, node by node.
//!
//! The solver (`crunk render --engine solve`) and the browser ([`crate::boxes`]) emit the same
//! layout-solve shape. [`compare`] lines the two up by `id` and reports every node whose box
//! differs by more than a pixel tolerance, and every node present on only one side. The CI parity
//! job fails on a non-empty [`ParityReport`], and the failure names the node.
//!
//! # Edge cases
//!
//! - A hidden browser node has no box; it is compared only for presence.
//! - The tolerance is inclusive: a difference equal to it passes.
//! - A node in the solver and absent from the browser (listed in `missing` or not at all) is
//!   [`Mismatch::MissingInBrowser`], never skipped.

// frob:ticket 01M4CXRWBYR6P0WFRW5GBBJGEY

use serde::Deserialize;
use tracing::{debug, info, warn};

use crate::boxes::BrowserBoxes;

/// Default pixel tolerance: the browser's text metrics differ from the solver's fixed metrics.
pub const DEFAULT_TOLERANCE_PX: f64 = 1.0;

/// One solver node; fields the comparison does not need are ignored on read.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct SolverNode {
    /// The `data-id`.
    pub id: String,
    /// Left edge.
    pub x: f64,
    /// Top edge.
    pub y: f64,
    /// Width.
    pub width: f64,
    /// Height.
    pub height: f64,
}

/// The solver's layout-solve document, reduced to what parity compares.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct SolverBoxes {
    /// Solved nodes.
    pub nodes: Vec<SolverNode>,
}

/// A box edge or size that differs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Field {
    /// Left edge.
    X,
    /// Top edge.
    Y,
    /// Width.
    Width,
    /// Height.
    Height,
}

impl Field {
    /// The field's name as written in the document.
    #[must_use]
    const fn name(self) -> &'static str {
        match self {
            Self::X => "x",
            Self::Y => "y",
            Self::Width => "width",
            Self::Height => "height",
        }
    }
}

/// One way the engines disagree about a node.
#[derive(Debug, Clone, PartialEq)]
pub enum Mismatch {
    /// A box field differs by more than the tolerance.
    Differs {
        /// The node's `data-id`.
        id: String,
        /// Which field.
        field: Field,
        /// The solver's value.
        solver: f64,
        /// The browser's value.
        browser: f64,
    },
    /// The solver has the node; the browser does not (missing, or hidden).
    MissingInBrowser {
        /// The node's `data-id`.
        id: String,
    },
    /// The browser measured a node the solver does not know.
    MissingInSolver {
        /// The node's `data-id`.
        id: String,
    },
}

impl std::fmt::Display for Mismatch {
    /// One line that names the node, for the CI log.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Differs {
                id,
                field,
                solver,
                browser,
            } => write!(
                f,
                "node `{id}`: {} solver {solver} vs browser {browser}",
                field.name()
            ),
            Self::MissingInBrowser { id } => {
                write!(f, "node `{id}`: in the solver, not the browser")
            }
            Self::MissingInSolver { id } => {
                write!(f, "node `{id}`: in the browser, not the solver")
            }
        }
    }
}

/// Every disagreement between the two engines for one cell.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ParityReport {
    /// The mismatches, in solver node order then browser-only nodes.
    pub mismatches: Vec<Mismatch>,
}

impl ParityReport {
    /// True when the engines agree within tolerance.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.mismatches.is_empty()
    }

    /// The failure text naming every offending node, one per line; empty when clean.
    #[must_use]
    pub fn summary(&self) -> String {
        self.mismatches
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join("\n")
    }
}

/// Parse a solver layout-solve document.
///
/// # Errors
/// The serde error text when `json` is not a layout-solve document.
pub fn parse_solver(json: &str) -> Result<SolverBoxes, String> {
    serde_json::from_str(json).map_err(|e| e.to_string())
}

/// Compare solver and browser boxes; differences within `tolerance_px` (inclusive) pass.
#[must_use]
pub fn compare(solver: &SolverBoxes, browser: &BrowserBoxes, tolerance_px: f64) -> ParityReport {
    let mut mismatches = Vec::new();
    for s in &solver.nodes {
        let Some(b) = browser.nodes.iter().find(|b| b.id == s.id) else {
            mismatches.push(Mismatch::MissingInBrowser { id: s.id.clone() });
            continue;
        };
        if b.hidden {
            mismatches.push(Mismatch::MissingInBrowser { id: s.id.clone() });
            continue;
        }
        for (field, sv, bv) in [
            (Field::X, s.x, b.x),
            (Field::Y, s.y, b.y),
            (Field::Width, s.width, b.width),
            (Field::Height, s.height, b.height),
        ] {
            if (sv - bv).abs() > tolerance_px {
                debug!(id = %s.id, field = field.name(), sv, bv, "box differs");
                mismatches.push(Mismatch::Differs {
                    id: s.id.clone(),
                    field,
                    solver: sv,
                    browser: bv,
                });
            }
        }
    }
    for b in browser.nodes.iter().filter(|b| !b.hidden) {
        if !solver.nodes.iter().any(|s| s.id == b.id) {
            mismatches.push(Mismatch::MissingInSolver { id: b.id.clone() });
        }
    }
    if mismatches.is_empty() {
        info!(
            nodes = solver.nodes.len(),
            tolerance_px, "solver and browser agree"
        );
    } else {
        warn!(
            count = mismatches.len(),
            tolerance_px, "solver and browser disagree"
        );
    }
    ParityReport { mismatches }
}
