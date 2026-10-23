//! Generated report directories (coverage HTML, Playwright reports) that no walk enters by default.
//!
//! The list lives here once; every product walk shares it through [`crate::walk`]. A rule
//! matches a directory by name and then by a marker file inside it, so a hand-written source
//! directory that merely shares the name (`src/coverage/`) is still walked.

use std::path::Path;

// frob:ticket 01M4GKCSFB13Y0VH1E1DDTA99H
/// One generated-directory rule: the directory name and the markers that prove it is a report.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GeneratedDir {
    /// Directory name, matched at any depth.
    pub name: &'static str,
    /// The directory is generated only when it holds at least one of these entries.
    pub markers: &'static [&'static str],
}

// frob:ticket 01M4GKCSFB13Y0VH1E1DDTA99H
/// Report directories skipped by default; `[check] exclude = ["!name/"]` opts one back in.
pub const GENERATED_DIRS: [GeneratedDir; 4] = [
    GeneratedDir {
        name: "coverage",
        markers: &["lcov-report", "prettify.js", "base.css"],
    },
    GeneratedDir {
        name: "lcov-report",
        markers: &["index.html"],
    },
    GeneratedDir {
        name: "htmlcov",
        markers: &["index.html"],
    },
    GeneratedDir {
        name: "playwright-report",
        markers: &["index.html"],
    },
];

/// The rules still in force after `exclude`, where a `!name/` entry opts that default back in.
pub(crate) fn active_rules(exclude: &[String]) -> Vec<GeneratedDir> {
    let opted_in: Vec<&str> = exclude
        .iter()
        .filter_map(|g| g.strip_prefix('!'))
        .map(|g| g.trim_matches('/'))
        .collect();
    let rules: Vec<GeneratedDir> = GENERATED_DIRS
        .iter()
        .filter(|r| !opted_in.contains(&r.name))
        .copied()
        .collect();
    tracing::debug!(
        active = rules.len(),
        opted_in = opted_in.len(),
        "generated-dir rules"
    );
    rules
}

/// True when `dir` is a generated report directory under one of `rules`.
pub(crate) fn is_generated(rules: &[GeneratedDir], dir: &Path) -> bool {
    let Some(name) = dir.file_name() else {
        return false;
    };
    let hit = rules
        .iter()
        .any(|r| name == r.name && r.markers.iter().any(|m| dir.join(m).exists()));
    if hit {
        tracing::debug!(dir = ?dir, "skipping generated report directory");
    }
    hit
}

// frob:ticket 01M5MDT81QR8F0E67N61AYZDN2
/// True when `dir` is a default-excluded generated report directory (no `exclude` opt-ins).
#[must_use]
pub fn is_generated_dir(dir: &Path) -> bool {
    is_generated(&active_rules(&[]), dir)
}
