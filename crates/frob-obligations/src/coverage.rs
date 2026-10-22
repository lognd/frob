//! COV004: measured lcov coverage per scope against the `[coverage]` minimums.

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2

use std::collections::BTreeMap;
use std::path::Path;

use globset::{Glob, GlobSet, GlobSetBuilder};
use gob_path::RelPath;
use gob_rules::{Finding, RuleDecl as _, Severity};
use gob_text::{FileInterner, Span};

use crate::config::{CoverageConfig, CoverageThreshold};
use crate::rules::cov004::Cov004;
use crate::todo::range;
use crate::util::{def_id, finding_def};

/// The file the thresholds are written in, which findings point at.
const CONFIG_FILE: &str = "frob.toml";

/// The header of one threshold entry.
const ENTRY_HEADER: &str = "[[coverage.threshold]]";

/// Hit and found counts of one file.
#[derive(Debug, Default)]
struct FileCov {
    /// Highest hit count per line number.
    lines: BTreeMap<u64, u64>,
    /// Whether each (line, block, branch) was taken at least once.
    branches: BTreeMap<(u64, u64, u64), bool>,
}

/// Hit and found counts of a scope.
#[derive(Debug, Default, Clone, Copy)]
struct Tally {
    /// Items executed or taken.
    hit: usize,
    /// Items instrumented.
    found: usize,
}

impl Tally {
    /// The covered share in percent, `None` when nothing was instrumented.
    #[allow(clippy::cast_precision_loss, reason = "counts stay far below 2^52")]
    fn percent(self) -> Option<f64> {
        (self.found > 0).then(|| self.hit as f64 * 100.0 / self.found as f64)
    }
}

/// The path `sf` as the repo-relative, forward-slash path the globs match.
fn normalize(sf: &str, root: &Path) -> String {
    let flat = sf.replace('\\', "/");
    let path = Path::new(&flat);
    let rebased = if path.is_absolute() {
        RelPath::from_host(root, path)
            .ok()
            .map(|r| r.as_str().to_owned())
    } else {
        None
    };
    let rel = rebased.unwrap_or(flat);
    rel.strip_prefix('.')
        .and_then(|r| r.strip_prefix('/'))
        .unwrap_or(&rel)
        .to_owned()
}

/// Parse the `DA:<line>,<hits>[,<checksum>]` payload into `(line, hits)`.
fn parse_da(payload: &str) -> Option<(u64, u64)> {
    let mut it = payload.split(',');
    let line = it.next()?.trim().parse().ok()?;
    let hits = it.next()?.trim().parse().ok()?;
    Some((line, hits))
}

/// Parse the `BRDA:<line>,<block>,<branch>,<taken>` payload into its key and whether it was taken.
fn parse_brda(payload: &str) -> Option<((u64, u64, u64), bool)> {
    let f: Vec<&str> = payload.split(',').map(str::trim).collect();
    let [line, block, branch, taken] = f.as_slice() else {
        return None;
    };
    let key = (
        line.parse().ok()?,
        block.parse().ok()?,
        branch.parse().ok()?,
    );
    Some((key, taken.parse::<u64>().is_ok_and(|t| t > 0)))
}

/// Parse an lcov `text` into per-file coverage; unrecognised or malformed records are skipped.
fn parse_lcov(text: &str, root: &Path) -> BTreeMap<String, FileCov> {
    let mut out: BTreeMap<String, FileCov> = BTreeMap::new();
    let mut current: Option<String> = None;
    for raw in text.lines() {
        let line = raw.trim();
        if let Some(sf) = line.strip_prefix("SF:") {
            current = Some(normalize(sf, root));
            continue;
        }
        if line == "end_of_record" {
            current = None;
            continue;
        }
        let Some(file) = current.as_ref() else {
            continue;
        };
        if let Some(da) = line.strip_prefix("DA:") {
            if let Some((n, hits)) = parse_da(da) {
                let slot = out
                    .entry(file.clone())
                    .or_default()
                    .lines
                    .entry(n)
                    .or_default();
                *slot = (*slot).max(hits);
            } else {
                tracing::debug!(record = line, "skipping malformed DA record");
            }
        } else if let Some(br) = line.strip_prefix("BRDA:") {
            if let Some((key, hit)) = parse_brda(br) {
                *out.entry(file.clone())
                    .or_default()
                    .branches
                    .entry(key)
                    .or_default() |= hit;
            } else {
                tracing::debug!(record = line, "skipping malformed BRDA record");
            }
        }
    }
    out
}

/// A matcher for `scope`: the glob itself, plus everything below it when it has no glob characters.
fn scope_matcher(scope: &str) -> Result<GlobSet, globset::Error> {
    let mut b = GlobSetBuilder::new();
    b.add(Glob::new(scope)?);
    if !scope.contains(['*', '?', '[', '{']) {
        let mut below = scope.trim_end_matches('/').to_owned();
        below.push('/');
        below.push_str("**");
        b.add(Glob::new(&below)?);
    }
    b.build()
}

/// Line and branch tallies of every reported file `matcher` accepts, with the file count.
fn tally(report: &BTreeMap<String, FileCov>, matcher: &GlobSet) -> (Tally, Tally, usize) {
    let (mut lines, mut branches, mut files) = (Tally::default(), Tally::default(), 0);
    for (path, cov) in report.iter().filter(|(p, _)| matcher.is_match(p.as_str())) {
        files += 1;
        lines.found += cov.lines.len();
        lines.hit += cov.lines.values().filter(|h| **h > 0).count();
        branches.found += cov.branches.len();
        branches.hit += cov.branches.values().filter(|t| **t).count();
        tracing::trace!(file = %path, "counted in scope");
    }
    (lines, branches, files)
}

/// The byte range of the `index`th threshold header in `<root>/frob.toml` (offset 0 when absent).
fn entry_span(root: &Path, index: usize, files: &mut FileInterner) -> Span {
    let (start, len) = std::fs::read_to_string(root.join(CONFIG_FILE))
        .ok()
        .and_then(|text| {
            let mut offset = 0;
            let mut seen = 0;
            for line in text.split_inclusive('\n') {
                if line.trim() == ENTRY_HEADER {
                    if seen == index {
                        return Some((offset, ENTRY_HEADER.len()));
                    }
                    seen += 1;
                }
                offset += line.len();
            }
            None
        })
        .unwrap_or((0, 0));
    Span::new(files.intern(CONFIG_FILE), range(start, len))
}

/// An unresolved COV004 finding for threshold `index`: nothing could be measured.
fn unresolved(
    root: &Path,
    index: usize,
    scope: &str,
    why: &str,
    files: &mut FileInterner,
) -> Finding {
    tracing::warn!(index, scope, why, "coverage threshold not measurable");
    Finding::new(
        def_id(Cov004::DEF),
        Severity::Unresolved,
        Some(entry_span(root, index, files)),
        format!("[coverage] scope `{scope}` could not be measured: {why}"),
        &format!("threshold[{index}]:{scope}"),
    )
}

/// Whether `pct` is a usable minimum.
fn valid_percent(pct: f64) -> bool {
    (0.0..=100.0).contains(&pct)
}

/// COV004 over the repo: every `[[coverage.threshold]]` entry against the lcov report.
pub(crate) fn cov004(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let config = match CoverageConfig::load(root) {
        Ok(c) => c,
        Err(err) => {
            tracing::warn!(%err, "[coverage] table unreadable");
            return vec![Finding::new(
                def_id(Cov004::DEF),
                Severity::Unresolved,
                Some(entry_span(root, 0, files)),
                format!("[coverage] table could not be read: {err}"),
                "coverage-config",
            )];
        }
    };
    if config.threshold.is_empty() {
        return Vec::new();
    }
    let report = std::fs::read_to_string(root.join(&config.report))
        .map(|t| parse_lcov(&t, root))
        .map_err(|e| format!("report `{}` is unreadable ({e})", config.report));
    let mut out = Vec::new();
    for (i, t) in config.threshold.iter().enumerate() {
        check_entry(root, i, t, &report, files, &mut out);
    }
    out
}

/// Evaluate threshold `t` (entry `index`) against `report`, pushing its findings onto `out`.
fn check_entry(
    root: &Path,
    index: usize,
    t: &CoverageThreshold,
    report: &Result<BTreeMap<String, FileCov>, String>,
    files: &mut FileInterner,
    out: &mut Vec<Finding>,
) {
    if t.line.is_none() && t.branch.is_none() {
        out.push(unresolved(
            root,
            index,
            &t.scope,
            "no `line` or `branch` minimum is set",
            files,
        ));
        return;
    }
    if let Some(bad) = [t.line, t.branch]
        .into_iter()
        .flatten()
        .find(|p| !valid_percent(*p))
    {
        let why = format!("minimum {bad} is not a percent between 0 and 100");
        out.push(unresolved(root, index, &t.scope, &why, files));
        return;
    }
    let matcher = match scope_matcher(&t.scope) {
        Ok(m) => m,
        Err(err) => {
            let why = format!("scope is not a valid glob ({err})");
            out.push(unresolved(root, index, &t.scope, &why, files));
            return;
        }
    };
    let report = match report {
        Ok(r) => r,
        Err(why) => {
            out.push(unresolved(root, index, &t.scope, why, files));
            return;
        }
    };
    let (by_line, by_branch, in_scope) = tally(report, &matcher);
    if in_scope == 0 {
        out.push(unresolved(
            root,
            index,
            &t.scope,
            "no file of the scope is in the report",
            files,
        ));
        return;
    }
    for (metric, required, tally) in [("line", t.line, by_line), ("branch", t.branch, by_branch)] {
        let Some(required) = required else { continue };
        let Some(measured) = tally.percent() else {
            let why = format!("the report holds no {metric} data for the scope");
            out.push(unresolved(root, index, &t.scope, &why, files));
            continue;
        };
        if measured < required {
            tracing::info!(scope = %t.scope, metric, measured, required, "coverage below threshold");
            out.push(finding_def(
                Cov004::DEF,
                Some(entry_span(root, index, files)),
                format!(
                    "scope `{}`: {metric} coverage {measured:.2}% ({}/{}) is below the required {required:.2}%",
                    t.scope, tally.hit, tally.found
                ),
                &format!("{}:{metric}", t.scope),
            ));
        } else {
            tracing::debug!(scope = %t.scope, metric, measured, required, "coverage meets threshold");
        }
    }
}
