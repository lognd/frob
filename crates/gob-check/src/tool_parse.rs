//! Parsers for bound tool output (zizmor, actionlint), id maps and version ranges.
//!
//! Pure functions: they turn a tool's stdout into [`RawFinding`]s and decide
//! the rule id and severity; locating them in the repository is `tools.rs`.

use std::cmp::Ordering;
use std::collections::BTreeMap;

use gob_rules::{RuleId, Severity};
use serde::Deserialize;

use crate::config::{ToolParser, ToolStage};

/// Where a tool placed a finding, in the tool's own terms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum RawRange {
    /// No usable location.
    None,
    /// Byte offsets into the file (zizmor).
    Bytes { start: u32, end: u32 },
    /// 1-based line and byte column, end column exclusive (actionlint).
    LineCol { line: u32, col: u32, end_col: u32 },
}

/// One tool finding before it becomes a frob [`gob_rules::Finding`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct RawFinding {
    /// Path as the tool printed it (not yet normalized).
    pub path: String,
    /// Location inside `path`.
    pub range: RawRange,
    /// The tool's finding id (zizmor ident, actionlint kind).
    pub tool_id: String,
    /// The tool's message.
    pub message: String,
}

/// Why a tool's output could not be read.
#[derive(Debug, thiserror::Error)]
pub(crate) enum ParseError {
    /// The output is not the JSON shape the parser expects.
    #[error("output is not valid {format} JSON: {source}")]
    Json {
        /// Parser name.
        format: &'static str,
        /// The underlying error.
        source: serde_json::Error,
    },
}

#[derive(Deserialize)]
struct ZFinding {
    ident: String,
    desc: String,
    #[serde(default)]
    ignored: bool,
    #[serde(default)]
    locations: Vec<ZLocation>,
}

#[derive(Deserialize)]
struct ZLocation {
    symbolic: ZSymbolic,
    concrete: Option<ZConcrete>,
}

#[derive(Deserialize)]
struct ZSymbolic {
    key: ZKey,
    #[serde(default)]
    annotation: String,
    #[serde(default)]
    kind: String,
}

#[derive(Deserialize)]
struct ZKey {
    #[serde(rename = "Local")]
    local: Option<ZLocal>,
}

#[derive(Deserialize)]
struct ZLocal {
    verbatim_path: String,
}

#[derive(Deserialize)]
struct ZConcrete {
    location: ZSpanHolder,
}

#[derive(Deserialize)]
struct ZSpanHolder {
    offset_span: ZOffsets,
}

#[derive(Deserialize)]
struct ZOffsets {
    start: u32,
    end: u32,
}

#[derive(Deserialize)]
struct AFinding {
    message: String,
    filepath: String,
    line: u32,
    column: u32,
    kind: String,
    #[serde(default)]
    end_column: u32,
}

/// Parse `stdout` of the stage's tool; `ToolParser::None` yields nothing.
///
/// # Errors
///
/// [`ParseError`] when the output is not the expected JSON array.
pub(crate) fn parse(parser: ToolParser, stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    match parser {
        ToolParser::None => Ok(Vec::new()),
        ToolParser::ZizmorJsonV1 => parse_zizmor(stdout),
        ToolParser::ActionlintJson => parse_actionlint(stdout),
    }
}

fn parse_zizmor(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let findings: Vec<ZFinding> =
        serde_json::from_str(stdout).map_err(|source| ParseError::Json {
            format: "zizmor json-v1",
            source,
        })?;
    let mut out = Vec::new();
    for f in findings.into_iter().filter(|f| !f.ignored) {
        let primary = f
            .locations
            .iter()
            .find(|l| l.symbolic.kind == "Primary")
            .or_else(|| f.locations.first());
        let (path, range, note) = match primary {
            Some(l) => (
                l.symbolic
                    .key
                    .local
                    .as_ref()
                    .map(|k| k.verbatim_path.clone())
                    .unwrap_or_default(),
                l.concrete
                    .as_ref()
                    .map_or(RawRange::None, |c| RawRange::Bytes {
                        start: c.location.offset_span.start,
                        end: c.location.offset_span.end,
                    }),
                l.symbolic.annotation.clone(),
            ),
            None => (String::new(), RawRange::None, String::new()),
        };
        let message = if note.is_empty() {
            f.desc
        } else {
            format!("{} ({note})", f.desc)
        };
        out.push(RawFinding {
            path,
            range,
            tool_id: f.ident,
            message,
        });
    }
    Ok(out)
}

fn parse_actionlint(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    // actionlint prints `null` for zero findings with some templates.
    let text = stdout.trim();
    let findings: Vec<AFinding> = if text == "null" || text.is_empty() {
        Vec::new()
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "actionlint",
            source,
        })?
    };
    Ok(findings
        .into_iter()
        .map(|f| RawFinding {
            path: f.filepath,
            range: RawRange::LineCol {
                line: f.line,
                col: f.column,
                end_col: f.end_column.max(f.column + 1),
            },
            tool_id: f.kind,
            message: f.message,
        })
        .collect())
}

/// The built-in tool id to rule id map of `parser`.
pub(crate) fn default_id_map(parser: ToolParser) -> BTreeMap<&'static str, &'static str> {
    match parser {
        ToolParser::ZizmorJsonV1 => BTreeMap::from([
            ("unpinned-uses", "CI001"),
            ("dangerous-triggers", "CI006"),
            ("template-injection", "CI007"),
            ("artipacked", "CI010"),
            ("excessive-permissions", "CI003"),
        ]),
        ToolParser::ActionlintJson | ToolParser::None => BTreeMap::new(),
    }
}

/// Rule used for a tool id that no map covers.
fn fallback(parser: ToolParser) -> &'static str {
    match parser {
        ToolParser::ActionlintJson => "CI014",
        _ => "TOOL002",
    }
}

/// Default severity of a rule this module can produce.
fn default_severity(rule: &str) -> Severity {
    match rule {
        "CI006" | "CI007" => Severity::Error,
        "CI001" | "CI003" | "CI014" => Severity::Warn,
        _ => Severity::Advisory,
    }
}

/// The rule id (and severity) for `raw`, or `None` when the finding is dropped.
///
/// A configured `id_map` entry wins over the parser default; an invalid
/// target id falls back to the parser's catch-all. An actionlint
/// `runner-label` finding is dropped when the label is in `stage.labels`,
/// and is Advisory when no labels are configured (it cannot be told apart
/// from label noise).
pub(crate) fn classify(stage: &ToolStage, raw: &RawFinding) -> Option<(RuleId, Severity)> {
    let mut severity_override = None;
    if stage.parser == ToolParser::ActionlintJson && raw.tool_id == "runner-label" {
        if let Some(label) = unknown_label(&raw.message)
            && stage.labels.iter().any(|l| l == label)
        {
            tracing::debug!(stage = %stage.name, label, "runner label is configured; dropped");
            return None;
        }
        if stage.labels.is_empty() {
            severity_override = Some(Severity::Advisory);
        }
    }
    let defaults = default_id_map(stage.parser);
    let target = stage
        .id_map
        .get(&raw.tool_id)
        .map(String::as_str)
        .or_else(|| defaults.get(raw.tool_id.as_str()).copied())
        .unwrap_or_else(|| fallback(stage.parser));
    let id = target.parse::<RuleId>().unwrap_or_else(|err| {
        tracing::warn!(stage = %stage.name, tool_id = %raw.tool_id, %err, "bad id_map target; using the fallback");
        fallback(stage.parser)
            .parse()
            .unwrap_or_else(|e| unreachable!("fallback ids are valid: {e}"))
    });
    let severity = severity_override.unwrap_or_else(|| default_severity(id.as_str()));
    Some((id, severity))
}

/// The label named by an actionlint `label "x" is unknown` message.
fn unknown_label(message: &str) -> Option<&str> {
    let rest = message.strip_prefix("label \"")?;
    rest.split_once('"').map(|(label, _)| label)
}

/// Parse a dotted version (`1.30.1`) into numeric components.
pub(crate) fn parse_version(text: &str) -> Option<Vec<u64>> {
    text.trim()
        .split('.')
        .map(|p| p.parse::<u64>().ok())
        .collect::<Option<Vec<_>>>()
        .filter(|v| !v.is_empty())
}

/// The first dotted number found in a tool's `--version` output.
pub(crate) fn find_version(output: &str) -> Option<String> {
    output
        .split(|c: char| !(c.is_ascii_digit() || c == '.'))
        .map(|t| t.trim_matches('.'))
        .find(|t| t.contains('.') && parse_version(t).is_some())
        .map(str::to_owned)
}

/// Compare dotted versions numerically, padding the shorter with zeros.
fn compare(a: &[u64], b: &[u64]) -> Ordering {
    let n = a.len().max(b.len());
    (0..n)
        .map(|i| {
            a.get(i)
                .copied()
                .unwrap_or(0)
                .cmp(&b.get(i).copied().unwrap_or(0))
        })
        .find(|o| *o != Ordering::Equal)
        .unwrap_or(Ordering::Equal)
}

/// The verdict of checking a tool version against a stage's range.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum VersionVerdict {
    /// Inside the range, or no range configured.
    Ok,
    /// Outside the range or unreadable: the stage's output is not trusted.
    Lag(String),
}

/// Check `found` (the tool's version text) against `min_version`..`max_version`.
pub(crate) fn check_version(stage: &ToolStage, found: Option<&str>) -> VersionVerdict {
    if stage.min_version.is_none() && stage.max_version.is_none() {
        return VersionVerdict::Ok;
    }
    let range = format!(
        "{}..{}",
        stage.min_version.as_deref().unwrap_or("*"),
        stage.max_version.as_deref().unwrap_or("*")
    );
    let Some(found) = found else {
        return VersionVerdict::Lag(format!(
            "could not read its version to compare with the supported range {range}"
        ));
    };
    let Some(have) = parse_version(found) else {
        return VersionVerdict::Lag(format!(
            "version `{found}` is not a dotted number (range {range})"
        ));
    };
    let below = stage
        .min_version
        .as_deref()
        .and_then(parse_version)
        .is_some_and(|min| compare(&have, &min) == Ordering::Less);
    let above = stage
        .max_version
        .as_deref()
        .and_then(parse_version)
        .is_some_and(|max| compare(&have, &max) == Ordering::Greater);
    if below || above {
        VersionVerdict::Lag(format!(
            "version {found} is outside the supported range {range}; its schema may lag or lead GitHub's, so its output is not trusted"
        ))
    } else {
        VersionVerdict::Ok
    }
}

/// The default arguments that print `parser`'s tool version.
pub(crate) fn default_version_args(parser: ToolParser) -> Option<Vec<String>> {
    match parser {
        ToolParser::ZizmorJsonV1 => Some(vec!["--version".to_owned()]),
        ToolParser::ActionlintJson => Some(vec!["-version".to_owned()]),
        ToolParser::None => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ZIZMOR: &str = include_str!("../tests/fixtures/zizmor-json-v1.json");
    const ACTIONLINT: &str = include_str!("../tests/fixtures/actionlint.json");

    fn stage(parser: ToolParser) -> ToolStage {
        ToolStage {
            name: "t".to_owned(),
            command: "t".to_owned(),
            args: Vec::new(),
            timeout_secs: 5,
            fail_on_nonzero: true,
            parser,
            labels: Vec::new(),
            id_map: BTreeMap::new(),
            min_version: None,
            max_version: None,
            version_args: None,
            optional: false,
            inputs: Vec::new(),
            unscoped_packages: vec!["--workspace".to_owned()],
        }
    }

    // frob:tests crates/gob-check/src/tool_parse.rs::parse
    #[test]
    fn zizmor_output_parses_with_byte_spans() {
        let found = parse(ToolParser::ZizmorJsonV1, ZIZMOR).expect("parse");
        assert_eq!(found.len(), 3, "the ignored finding is skipped");
        assert_eq!(found[0].tool_id, "unpinned-uses");
        assert_eq!(found[0].path, "./.github/workflows/ci.yml");
        assert_eq!(
            found[0].range,
            RawRange::Bytes {
                start: 305,
                end: 324
            }
        );
        assert!(found[0].message.contains("not pinned to a hash"));
    }

    #[test]
    fn actionlint_output_parses_with_line_and_column() {
        let found = parse(ToolParser::ActionlintJson, ACTIONLINT).expect("parse");
        assert_eq!(found.len(), 3);
        assert_eq!(found[0].tool_id, "runner-label");
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 4,
                col: 14,
                end_col: 25
            }
        );
        assert!(
            parse(ToolParser::ActionlintJson, "null")
                .expect("null")
                .is_empty()
        );
        assert!(parse(ToolParser::ActionlintJson, "[").is_err());
    }

    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn zizmor_ids_map_to_ci_ids_and_the_rest_is_tool002() {
        let st = stage(ToolParser::ZizmorJsonV1);
        let found = parse(ToolParser::ZizmorJsonV1, ZIZMOR).expect("parse");
        let ids: Vec<_> = found
            .iter()
            .filter_map(|f| classify(&st, f))
            .map(|(id, sev)| (id.to_string(), sev))
            .collect();
        assert_eq!(
            ids,
            [
                ("CI001".to_owned(), Severity::Warn),
                ("CI010".to_owned(), Severity::Advisory),
                ("TOOL002".to_owned(), Severity::Advisory)
            ]
        );
    }

    #[test]
    fn id_map_overrides_and_bad_targets_fall_back() {
        let mut st = stage(ToolParser::ZizmorJsonV1);
        st.id_map
            .insert("unpinned-uses".to_owned(), "CI007".to_owned());
        st.id_map
            .insert("artipacked".to_owned(), "nonsense".to_owned());
        let found = parse(ToolParser::ZizmorJsonV1, ZIZMOR).expect("parse");
        let ids: Vec<_> = found
            .iter()
            .filter_map(|f| classify(&st, f))
            .map(|(id, _)| id.to_string())
            .collect();
        assert_eq!(ids, ["CI007", "TOOL002", "TOOL002"]);
    }

    #[test]
    fn actionlint_runner_labels_follow_the_labels_knob() {
        let mut st = stage(ToolParser::ActionlintJson);
        let found = parse(ToolParser::ActionlintJson, ACTIONLINT).expect("parse");
        let sev = |st: &ToolStage| -> Vec<Option<Severity>> {
            found.iter().map(|f| classify(st, f).map(|c| c.1)).collect()
        };
        assert_eq!(
            sev(&st),
            [
                Some(Severity::Advisory),
                Some(Severity::Warn),
                Some(Severity::Warn)
            ],
            "no labels configured: runner-label is Advisory"
        );
        st.labels = vec!["blacksmith-4".to_owned()];
        assert_eq!(sev(&st)[0], None, "a configured label is dropped");
        st.labels = vec!["other".to_owned()];
        assert_eq!(sev(&st)[0], Some(Severity::Warn), "unknown after the knob");
        assert!(
            found
                .iter()
                .all(|f| classify(&st, f).is_none_or(|c| c.0.as_str() == "CI014"))
        );
    }

    // frob:tests crates/gob-check/src/tool_parse.rs::check_version
    #[test]
    fn version_range_is_inclusive_and_numeric() {
        let mut st = stage(ToolParser::ZizmorJsonV1);
        assert_eq!(check_version(&st, Some("0.1")), VersionVerdict::Ok);
        st.min_version = Some("1.9".to_owned());
        st.max_version = Some("1.30.1".to_owned());
        assert_eq!(check_version(&st, Some("1.30.1")), VersionVerdict::Ok);
        assert_eq!(check_version(&st, Some("1.10.0")), VersionVerdict::Ok);
        assert!(matches!(
            check_version(&st, Some("1.8.9")),
            VersionVerdict::Lag(_)
        ));
        assert!(matches!(
            check_version(&st, Some("1.30.2")),
            VersionVerdict::Lag(_)
        ));
        assert!(matches!(check_version(&st, None), VersionVerdict::Lag(_)));
    }

    #[test]
    fn versions_are_found_in_banner_text() {
        assert_eq!(find_version("zizmor 1.30.1\n").as_deref(), Some("1.30.1"));
        assert_eq!(
            find_version("1.7.12\ninstalled by downloading\nbuilt with go1.26.1 compiler")
                .as_deref(),
            Some("1.7.12")
        );
        assert_eq!(find_version("no digits"), None);
    }
}
