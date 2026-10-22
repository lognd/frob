//! Readers for public-API compatibility checkers: cargo-semver-checks, griffe and api-extractor become `VERSION001`.

// frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK

use crate::tool_parse::{RawFinding, RawMeta, RawRange};

/// The tool id every public-API finding carries; the default id map sends it to `VERSION001`.
pub(crate) const SEMVER_TOOL_ID: &str = "semver";

/// Where cargo-semver-checks findings land when the tool names no source file.
const NO_FILE: &str = "Cargo.toml";

/// Fields of one `Failed in:` block while it is being read.
#[derive(Default)]
struct Section {
    /// True when the `Checking` header says the version bump is already breaking.
    breaking_bump: bool,
    /// The lint of the failure block being read (`function_missing: pub fn removed or renamed`).
    lint: String,
    /// True while inside a `Failed in:` list.
    in_list: bool,
    /// Findings of this crate, dropped when the bump is breaking.
    found: Vec<RawFinding>,
}

/// Parse cargo-semver-checks output into one finding per reported item.
///
/// A crate whose `Checking` header marks a breaking change (a major bump, or a minor bump
/// below 1.0) has satisfied every lint, so its section yields nothing even if the tool listed items.
// frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
pub(crate) fn parse_semver_checks(text: &str) -> Vec<RawFinding> {
    let mut out = Vec::new();
    let mut sec = Section::default();
    for line in text.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("Checking ") {
            flush(&mut sec, &mut out);
            sec.breaking_bump = is_breaking(rest);
        } else if let Some(rest) = trimmed.strip_prefix("--- failure ") {
            rest.trim_end_matches('-').trim().clone_into(&mut sec.lint);
            sec.in_list = false;
        } else if trimmed == "Failed in:" {
            sec.in_list = true;
        } else if trimmed.is_empty() {
            sec.in_list = false;
        } else if sec.in_list {
            sec.found.push(item_finding(trimmed, &sec.lint));
        }
    }
    flush(&mut sec, &mut out);
    tracing::debug!(count = out.len(), "semver-checks findings parsed");
    out
}

/// Whether a `Checking crate vA -> vB (kind)` header reports a breaking version change.
fn is_breaking(header: &str) -> bool {
    header
        .rsplit_once('(')
        .is_some_and(|(_, kind)| kind.contains("breaking") && !kind.contains("non-breaking"))
}

/// Move a finished crate section's findings to `out`, unless its bump was breaking.
fn flush(sec: &mut Section, out: &mut Vec<RawFinding>) {
    let found = std::mem::take(&mut sec.found);
    if sec.breaking_bump {
        tracing::debug!(
            suppressed = found.len(),
            "breaking version bump; semver findings dropped"
        );
    } else {
        out.extend(found);
    }
    *sec = Section::default();
}

/// One `Failed in:` entry (`function foo::bar, previously in file src/lib.rs:12`) as a finding.
fn item_finding(entry: &str, lint_name: &str) -> RawFinding {
    let (item, location) = match entry.split_once(" in file ") {
        Some((head, loc)) => (head.trim_end_matches(", previously").trim(), Some(loc)),
        None => (entry, None),
    };
    let (path, line) = match location {
        Some(loc) => split_location(loc),
        None => (NO_FILE, None),
    };
    let range = line.map_or(RawRange::None, |line| RawRange::LineCol {
        line,
        col: 1,
        end_col: 1,
    });
    raw(path, range, format!("{item} ({lint_name})"))
}

/// Split `path:LINE` or `path:LINE:COL` into the path and the line.
fn split_location(loc: &str) -> (&str, Option<u32>) {
    let loc = loc.trim();
    let mut path = loc;
    let mut line = None;
    // Peel up to two numeric trailing segments; the earlier one is the line.
    for _ in 0..2 {
        match path.rsplit_once(':') {
            Some((head, num)) if num.parse::<u32>().is_ok() => {
                line = num.parse().ok();
                path = head;
            }
            _ => break,
        }
    }
    (path, line)
}

/// Parse `griffe check` output (`path:LINE: object: message`) into one finding per breakage.
// frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
pub(crate) fn parse_griffe(text: &str) -> Vec<RawFinding> {
    let mut out = Vec::new();
    for line in text.lines() {
        out.extend(griffe_line(line));
    }
    tracing::debug!(count = out.len(), "griffe findings parsed");
    out
}

/// One griffe breakage line, if it is one.
fn griffe_line(line: &str) -> Option<RawFinding> {
    let line = line.trim();
    let (path, rest) = split_after_line_number(line)?;
    let (line_no, rest) = rest;
    let (object, message) = rest.split_once(": ")?;
    let object = object.trim();
    (!object.is_empty()).then(|| {
        raw(
            path,
            RawRange::LineCol {
                line: line_no,
                col: 1,
                end_col: 1,
            },
            format!("{object}: {}", message.trim()),
        )
    })
}

/// Split `path:LINE: rest` at the first `:digits: ` so a path may hold colons.
fn split_after_line_number(line: &str) -> Option<(&str, (u32, &str))> {
    let mut from = 0;
    while let Some(i) = line[from..].find(": ") {
        let at = from + i;
        if let Some((path, num)) = line[..at].rsplit_once(':')
            && let Ok(n) = num.parse::<u32>()
            && !path.is_empty()
        {
            return Some((path, (n, &line[at + 2..])));
        }
        from = at + 2;
    }
    None
}

/// Marker api-extractor prints, in CI mode, when the built API report differs from the committed one.
const API_CHANGED: &str = "changed the public API signature";

/// Marker api-extractor prints when no committed API report exists yet.
const API_MISSING: &str = "API report file is missing";

/// Parse `api-extractor run` output into one finding per drifted API report.
///
/// api-extractor compares the report it builds with the committed one and, outside `--local`
/// mode, errors with `Please copy the file "<built>" to "<committed>"`. That drift is the API
/// diff; it cannot tell additive from breaking, so each drift is one finding on the committed
/// report and a reviewer decides the version bump. Diagnostics (`ae-*`) and noise are ignored.
// frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
pub(crate) fn parse_api_extractor(text: &str) -> Vec<RawFinding> {
    let out: Vec<RawFinding> = text.lines().filter_map(api_report_line).collect();
    tracing::debug!(count = out.len(), "api-extractor findings parsed");
    out
}

/// One api-extractor report-drift line, if it is one.
fn api_report_line(line: &str) -> Option<RawFinding> {
    let line = line.trim();
    let drifted = line.contains(API_CHANGED);
    if !(drifted || line.contains(API_MISSING)) {
        return None;
    }
    let committed = quoted_after_to(line).unwrap_or(NO_API_REPORT);
    let message = if drifted {
        "public API report differs from the committed report; review the diff and bump the version"
    } else {
        "public API report is missing; commit one so later changes can be compared"
    };
    Some(raw(committed, RawRange::None, message.to_owned()))
}

/// Where a drift finding lands when the line names no committed report.
const NO_API_REPORT: &str = "api-extractor.json";

/// The quoted path after the last ` to ` of an api-extractor `copy the file "A" to "B"` message.
fn quoted_after_to(line: &str) -> Option<&str> {
    let (_, tail) = line.rsplit_once("\" to \"")?;
    let (path, _) = tail.split_once('"')?;
    (!path.is_empty()).then_some(path)
}

/// A raw finding carrying the shared tool id.
fn raw(path: &str, range: RawRange, message: String) -> RawFinding {
    RawFinding {
        path: path.to_owned(),
        range,
        tool_id: SEMVER_TOOL_ID.to_owned(),
        message,
        suppressed: None,
        meta: RawMeta::default(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MISSING_FN: &str = "     Checking foo v1.2.0 -> v1.2.1 (no change)\n     Checked [   0.012s] 196 checks: 195 pass, 1 fail, 0 warn, 0 skip\n\n--- failure function_missing: pub fn removed or renamed ---\n\nDescription:\nA publicly-visible function cannot be imported by its prior path.\n        ref: https://example.invalid/a\n\nFailed in:\n  function foo::bar, previously in file src/lib.rs:12\n  function foo::baz, previously in file src/lib.rs:30\n\n     Summary semver requires new major version: 1 major and 0 minor checks failed\n";

    // frob:tests crates/gob-check/src/semver_parse.rs::parse_semver_checks
    #[test]
    fn removed_function_names_the_item_and_its_location() {
        let found = parse_semver_checks(MISSING_FN);
        assert_eq!(found.len(), 2);
        assert_eq!(found[0].path, "src/lib.rs");
        assert!(found[0].message.starts_with("function foo::bar"));
        assert!(found[0].message.contains("function_missing"));
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 12,
                col: 1,
                end_col: 1
            }
        );
    }

    // frob:tests crates/gob-check/src/semver_parse.rs::parse_semver_checks
    #[test]
    fn breaking_bump_suppresses_only_its_own_crate() {
        let text = MISSING_FN.replace("v1.2.1 (no change)", "v2.0.0 (breaking change)");
        assert!(parse_semver_checks(&text).is_empty());
        let both = format!("{text}\n{MISSING_FN}");
        assert_eq!(parse_semver_checks(&both).len(), 2);
    }

    // frob:tests crates/gob-check/src/semver_parse.rs::parse_semver_checks
    #[test]
    fn empty_and_clean_output_yield_nothing() {
        assert!(parse_semver_checks("").is_empty());
        let clean = "     Checking foo v1.0.0 -> v1.0.1 (no change)\n     Checked [   0.01s] 196 checks: 196 pass, 0 skip\n     Summary no semver update required\n";
        assert!(parse_semver_checks(clean).is_empty());
    }

    // frob:tests crates/gob-check/src/semver_parse.rs::parse_semver_checks
    #[test]
    fn entries_without_a_file_fall_back_to_the_manifest() {
        let text =
            "--- failure enum_missing: pub enum removed ---\n\nFailed in:\n  enum foo::E\n\n";
        let found = parse_semver_checks(text);
        assert_eq!(found[0].path, "Cargo.toml");
        assert_eq!(found[0].range, RawRange::None);
    }

    // frob:tests crates/gob-check/src/semver_parse.rs::parse_griffe
    #[test]
    fn griffe_breakage_lines_name_the_object() {
        let text = "pkg/mod.py:12: pkg.mod.func(a): Parameter was removed\nnot a breakage\nsrc/x.py:3: pkg.X: Public object was removed\n";
        let found = parse_griffe(text);
        assert_eq!(found.len(), 2);
        assert_eq!(found[0].path, "pkg/mod.py");
        assert_eq!(found[0].message, "pkg.mod.func(a): Parameter was removed");
        assert!(parse_griffe("").is_empty());
    }

    const API_DRIFT: &str = "Console: API Extractor 7.52.8\nError: You have changed the public API signature for this project. Please copy the file \"temp/foo.api.md\" to \"etc/foo.api.md\", or perform a local build (which does this automatically).\n";

    // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
    // frob:tests crates/gob-check/src/semver_parse.rs::parse_api_extractor
    #[test]
    fn api_extractor_drift_lands_on_the_committed_report() {
        let found = parse_api_extractor(API_DRIFT);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].path, "etc/foo.api.md");
        assert!(found[0].message.contains("bump the version"));
    }

    // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
    // frob:tests crates/gob-check/src/semver_parse.rs::parse_api_extractor
    #[test]
    fn api_extractor_clean_empty_and_malformed_output_yield_nothing() {
        assert!(parse_api_extractor("").is_empty());
        let clean = "Console: API Extractor completed successfully\nWarning: dist/a.d.ts:1:1 - (ae-missing-release-tag) x\n";
        assert!(parse_api_extractor(clean).is_empty());
    }

    // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
    // frob:tests crates/gob-check/src/semver_parse.rs::parse_api_extractor
    #[test]
    fn api_extractor_drift_without_a_named_report_falls_back_to_the_config() {
        let found = parse_api_extractor(
            "Error: You have changed the public API signature for this project.\n",
        );
        assert_eq!(found[0].path, "api-extractor.json");
        let missing = parse_api_extractor(
            "Error: The API report file is missing. Please copy the file \"temp/x.api.md\" to \"etc/x.api.md\"",
        );
        assert_eq!(missing[0].path, "etc/x.api.md");
        assert!(missing[0].message.contains("missing"));
    }
}
