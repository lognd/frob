//! Reader for formatter check-mode output: one `FMT001` raw finding per unformatted file.

use std::collections::BTreeSet;

use crate::tool_parse::{RawFinding, RawMeta, RawRange};

/// The tool id every formatter finding carries; the default id map sends it to `FMT001`.
pub(crate) const FMT_TOOL_ID: &str = "fmt";

// frob:ticket 01M4D94J5J2TZEXTB8GH36992B
/// Parse formatter check output (rustfmt, ruff format, prettier, dotnet format, gofmt) into one file-level finding per distinct path.
pub(crate) fn parse_formatter_list(stdout: &str) -> Vec<RawFinding> {
    let mut seen = BTreeSet::new();
    let mut out = Vec::new();
    for line in stdout.lines() {
        let Some(path) = line_path(line) else {
            continue;
        };
        if seen.insert(path.clone()) {
            out.push(RawFinding {
                path,
                range: RawRange::Bytes { start: 0, end: 0 },
                tool_id: FMT_TOOL_ID.to_owned(),
                message: "file is not formatted".to_owned(),
                suppressed: None,
                meta: RawMeta::default(),
            });
        }
    }
    tracing::debug!(count = out.len(), "formatter findings parsed");
    out
}

/// The unformatted file one output line names, if it names one.
fn line_path(line: &str) -> Option<String> {
    let line = line.trim();
    if line.is_empty() {
        return None;
    }
    if let Some(rest) = line.strip_prefix("Diff in ") {
        return Some(strip_diff_position(rest).to_owned());
    }
    if let Some(rest) = line.strip_prefix("Would reformat: ") {
        return Some(rest.trim().to_owned());
    }
    if let Some(rest) = line.strip_prefix("[warn] ") {
        let rest = rest.trim();
        return (!rest.starts_with("Code style issues")).then(|| rest.to_owned());
    }
    if let Some((head, _)) = line.split_once("): ") {
        let (path, _) = head.rsplit_once('(')?;
        return has_extension(path).then(|| path.to_owned());
    }
    (!line.contains(": ") && has_extension(line)).then(|| line.to_owned())
}

/// Drop rustfmt's `:LINE:` or ` at line N:` tail from a `Diff in` path.
fn strip_diff_position(rest: &str) -> &str {
    if let Some((path, _)) = rest.split_once(" at line ") {
        return path;
    }
    let trimmed = rest.trim_end_matches(':');
    match trimmed.rsplit_once(':') {
        Some((path, num)) if !num.is_empty() && num.bytes().all(|b| b.is_ascii_digit()) => path,
        _ => trimmed,
    }
}

/// Whether the last path component has a non-empty extension.
fn has_extension(path: &str) -> bool {
    let name = path.rsplit(['/', '\\']).next().unwrap_or(path);
    name.rsplit_once('.')
        .is_some_and(|(stem, ext)| !stem.is_empty() && !ext.is_empty() && !ext.contains(' '))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn paths(out: &str) -> Vec<String> {
        parse_formatter_list(out)
            .into_iter()
            .map(|r| r.path)
            .collect()
    }

    // frob:tests crates/gob-check/src/fmt_parse.rs::parse_formatter_list
    #[test]
    fn rustfmt_diffs_collapse_to_one_finding_per_file() {
        let out =
            "Diff in /r/src/a.rs:3:\n-x\n+y\nDiff in /r/src/a.rs:9:\nDiff in /r/b.rs at line 2:\n";
        assert_eq!(paths(out), ["/r/src/a.rs", "/r/b.rs"]);
    }

    // frob:tests crates/gob-check/src/fmt_parse.rs::parse_formatter_list
    #[test]
    fn ruff_format_reports_would_reformat_lines() {
        let out = "Would reformat: a.py\nWould reformat: pkg/b.py\n2 files would be reformatted\n";
        assert_eq!(paths(out), ["a.py", "pkg/b.py"]);
    }

    // frob:tests crates/gob-check/src/fmt_parse.rs::parse_formatter_list
    #[test]
    fn prettier_warn_lines_skip_the_summary() {
        let out = "Checking formatting...\n[warn] web/a.ts\n[warn] b.css\n[warn] Code style issues found in 2 files. Run Prettier with --write to fix.\n";
        assert_eq!(paths(out), ["web/a.ts", "b.css"]);
    }

    // frob:tests crates/gob-check/src/fmt_parse.rs::parse_formatter_list
    #[test]
    fn dotnet_format_diagnostics_name_the_file() {
        let out = "/r/A.cs(3,5): error WHITESPACE: Fix whitespace formatting. [/r/p.csproj]\n/r/A.cs(9,1): error WHITESPACE: x\n";
        assert_eq!(paths(out), ["/r/A.cs"]);
    }

    // frob:tests crates/gob-check/src/fmt_parse.rs::parse_formatter_list
    #[test]
    fn plain_lists_and_noise() {
        let out = "main.go\n\n1 file left unchanged.\nsub dir/x.c\n";
        assert_eq!(paths(out), ["main.go", "sub dir/x.c"]);
        assert!(parse_formatter_list("").is_empty());
    }
}
