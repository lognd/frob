//! Parsers for bound tool output (zizmor, actionlint, stylelint), id maps and version ranges.
//!
//! Pure functions: they turn a tool's stdout into [`RawFinding`]s and decide
//! the rule id and severity; locating them in the repository is `tools.rs`.

use std::cmp::Ordering;
use std::collections::BTreeMap;

use gob_rules::{RuleId, Severity};
use serde::{Deserialize, Serialize};

use crate::config::{ToolParser, ToolStage};

/// Where a tool placed a finding, in the tool's own terms.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) enum RawRange {
    /// No usable location.
    None,
    /// Byte offsets into the file (zizmor).
    Bytes { start: u32, end: u32 },
    /// 1-based line and byte column, end column exclusive (actionlint).
    LineCol { line: u32, col: u32, end_col: u32 },
    /// 1-based line and character column of start and end, end exclusive (SARIF regions).
    CharRange {
        line: u32,
        col: u32,
        end_line: u32,
        end_col: u32,
    },
}

/// A native suppression the tool applied to a result it still reported (SARIF `suppressions`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct RawSuppression {
    /// SARIF suppression kind: `inSource` or `external`.
    pub kind: String,
    /// The author's justification, possibly empty.
    pub justification: String,
}

/// Parser-specific facts that steer the rule id and severity of a [`RawFinding`].
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct RawMeta {
    /// The lint group the tool reports for the finding (`correctness` for deny-by-default clippy lints).
    #[serde(default)]
    pub group: Option<String>,
    /// The tool's own level (`warning`, `error`).
    #[serde(default)]
    pub level: Option<String>,
}

/// One tool finding before it becomes a frob [`gob_rules::Finding`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct RawFinding {
    /// Path as the tool printed it (not yet normalized).
    pub path: String,
    /// Location inside `path`.
    pub range: RawRange,
    /// The tool's finding id (zizmor ident, actionlint kind).
    pub tool_id: String,
    /// The tool's message.
    pub message: String,
    /// Set when the tool reported the result as suppressed; such a result is not a finding (EXC017 reads it).
    pub suppressed: Option<RawSuppression>,
    /// Extra facts a parser hands to `classify` (cargo diagnostics: clippy group and level).
    #[serde(default)]
    pub meta: RawMeta,
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
    /// The JSON is not a SARIF 2.1.0 log.
    #[error("output is not a SARIF 2.1.0 log: {0}")]
    Sarif(String),
    /// The text is not the line format the parser expects.
    #[error("output is not valid {format} text: {message}")]
    Text {
        /// Parser name.
        format: &'static str,
        /// What was wrong.
        message: String,
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

// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
#[derive(Deserialize)]
struct RFinding {
    code: Option<String>,
    message: String,
    filename: String,
    location: RPos,
    end_location: Option<RPos>,
}

// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
#[derive(Deserialize)]
struct RPos {
    row: u32,
    column: u32,
}

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
#[derive(Deserialize)]
struct SFile {
    source: String,
    #[serde(default)]
    warnings: Vec<SWarning>,
}

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
#[derive(Deserialize)]
struct SWarning {
    line: u32,
    column: u32,
    #[serde(rename = "endLine", default)]
    end_line: u32,
    #[serde(rename = "endColumn", default)]
    end_column: u32,
    rule: String,
    text: String,
}

// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
/// One file of `eslint -f json`.
#[derive(Deserialize)]
struct EFile {
    #[serde(rename = "filePath")]
    file_path: String,
    #[serde(default)]
    messages: Vec<EMessage>,
}

// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
/// One message of an eslint file; `ruleId` is null for parse errors.
#[derive(Deserialize)]
struct EMessage {
    #[serde(rename = "ruleId")]
    rule_id: Option<String>,
    message: String,
    #[serde(default)]
    line: u32,
    #[serde(default)]
    column: u32,
    #[serde(rename = "endLine", default)]
    end_line: Option<u32>,
    #[serde(rename = "endColumn", default)]
    end_column: Option<u32>,
}

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
/// Parse `stdout` of the stage's tool; `ToolParser::None` yields nothing.
///
/// # Errors
///
/// [`ParseError`] when the output is not the expected JSON array.
pub(crate) fn parse(parser: ToolParser, stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    match parser {
        ToolParser::None => Ok(Vec::new()),
        ToolParser::FormatterList => Ok(crate::fmt_parse::parse_formatter_list(stdout)),
        // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
        ToolParser::SemverChecksText => Ok(crate::semver_parse::parse_semver_checks(stdout)),
        ToolParser::GriffeText => Ok(crate::semver_parse::parse_griffe(stdout)),
        // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
        ToolParser::ApiExtractorText => Ok(crate::semver_parse::parse_api_extractor(stdout)),
        ToolParser::ZizmorJsonV1 => parse_zizmor(stdout),
        ToolParser::ActionlintJson => parse_actionlint(stdout),
        ToolParser::Sarif | ToolParser::RoslynSarif => crate::sarif::parse_sarif(stdout),
        ToolParser::CargoJson => crate::cargo_json::parse_cargo_json(stdout),
        ToolParser::StylelintJson => parse_stylelint(stdout),
        ToolParser::RuffJson => parse_ruff(stdout),
        ToolParser::TyGitlab => crate::type_parse::parse_ty_gitlab(stdout),
        ToolParser::PyrightJson => crate::type_parse::parse_pyright(stdout),
        ToolParser::TscText => crate::type_parse::parse_tsc(stdout),
        ToolParser::TyposJson => parse_typos(stdout),
        ToolParser::EslintJson => parse_eslint(stdout),
    }
}

// frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
/// One line of `typos --format json`; only `type = "typo"` lines are findings.
#[derive(Deserialize)]
struct TLine {
    #[serde(rename = "type")]
    kind: String,
    #[serde(default)]
    path: String,
    #[serde(default)]
    line_num: u32,
    #[serde(default)]
    byte_offset: u32,
    #[serde(default)]
    typo: String,
    #[serde(default)]
    corrections: Vec<String>,
}

// frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
/// typos `--format json`: JSON lines, one per typo, with a 1-based line and 0-based byte offset; the corrections go in the message as the remedy (empty output is no finding).
fn parse_typos(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let mut out = Vec::new();
    for text in stdout.lines().map(str::trim).filter(|l| !l.is_empty()) {
        let line: TLine = serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "typos",
            source,
        })?;
        if line.kind != "typo" {
            continue;
        }
        let col = line.byte_offset + 1;
        let width = u32::try_from(line.typo.len()).unwrap_or(u32::MAX).max(1);
        let remedy = match line.corrections.as_slice() {
            [] => "no correction known".to_owned(),
            fixes => format!("did you mean {}?", fixes.join(" or ")),
        };
        out.push(RawFinding {
            path: line.path,
            range: RawRange::LineCol {
                line: line.line_num,
                col,
                end_col: col.saturating_add(width),
            },
            tool_id: "typo".to_owned(),
            message: format!("`{}` is a typo; {remedy}", line.typo),
            suppressed: None,
            meta: RawMeta::default(),
        });
    }
    tracing::debug!(count = out.len(), "typos findings parsed");
    Ok(out)
}

// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
/// eslint `-f json`: one entry per file with 1-based line and column messages (empty output is no finding).
fn parse_eslint(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let text = stdout.trim();
    let files: Vec<EFile> = if text.is_empty() {
        Vec::new()
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "eslint",
            source,
        })?
    };
    let mut out = Vec::new();
    for file in files {
        for m in file.messages {
            // A parse error carries no rule id; it is not a lint finding.
            let Some(rule) = m.rule_id else {
                tracing::debug!(path = %file.file_path, "eslint message without a rule id; skipped");
                continue;
            };
            let end_col = match (m.end_line, m.end_column) {
                (Some(l), Some(c)) if l == m.line && c > m.column => c,
                _ => m.column + 1,
            };
            out.push(RawFinding {
                path: file.file_path.clone(),
                range: RawRange::LineCol {
                    line: m.line,
                    col: m.column,
                    end_col,
                },
                tool_id: rule,
                message: m.message,
                suppressed: None,
                meta: RawMeta::default(),
            });
        }
    }
    tracing::debug!(count = out.len(), "eslint findings parsed");
    Ok(out)
}

// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
/// The built-in rule for an eslint rule id, by plugin prefix; `None` falls through to `LINT001`.
fn eslint_target(rule: &str) -> Option<&'static str> {
    if rule.starts_with("jsx-a11y/") {
        return Some("A11Y001");
    }
    if rule.starts_with("react-hooks/") || rule.starts_with("react/") {
        return Some("REACT001");
    }
    match rule.strip_prefix("@typescript-eslint/")? {
        "no-floating-promises" | "no-misused-promises" | "await-thenable" | "require-await" => {
            Some("CONC001")
        }
        "no-explicit-any" => Some("TYPING001"),
        name if name.starts_with("no-unsafe-") => Some("TYPING001"),
        _ => None,
    }
}

// frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
/// The built-in rule for a Roslyn diagnostic id; `None` falls through to `LINT001`.
fn roslyn_target(rule: &str) -> Option<&'static str> {
    let digits = |prefix: &str| {
        rule.strip_prefix(prefix)
            .is_some_and(|d| !d.is_empty() && d.bytes().all(|b| b.is_ascii_digit()))
    };
    if digits("UNT") {
        return Some("UNITY101");
    }
    if rule.starts_with("VSTHRD") {
        return Some("CONC001");
    }
    // Unused usings, members, parameters and locals; the USP suppressors keep engine-called messages out of IDE0051.
    // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
    // PublicApiAnalyzers: a public symbol missing from or removed from PublicAPI.Shipped.txt.
    if matches!(rule, "RS0016" | "RS0017") {
        return Some("VERSION001");
    }
    matches!(
        rule,
        "IDE0051" | "IDE0052" | "IDE0060" | "IDE0005" | "CS8019" | "CS0168" | "CS0219"
    )
    .then_some("DEAD001")
}

// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
/// ruff `--output-format=json`: an array of violations with 1-based row and character column (empty output is no finding).
fn parse_ruff(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let text = stdout.trim();
    let findings: Vec<RFinding> = if text.is_empty() {
        Vec::new()
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "ruff",
            source,
        })?
    };
    tracing::debug!(count = findings.len(), "ruff findings parsed");
    Ok(findings
        .into_iter()
        .filter_map(|f| {
            // A syntax error carries no rule code; the parse failure is not a lint finding.
            let code = f.code?;
            let start = f.location;
            let end_col = match f.end_location {
                Some(e) if e.row == start.row && e.column > start.column => e.column,
                _ => start.column + 1,
            };
            Some(RawFinding {
                path: f.filename,
                range: RawRange::LineCol {
                    line: start.row,
                    col: start.column,
                    end_col,
                },
                tool_id: code,
                message: f.message,
                suppressed: None,
                meta: RawMeta::default(),
            })
        })
        .collect())
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
            suppressed: None,
            meta: RawMeta::default(),
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
            suppressed: None,
            meta: RawMeta::default(),
        })
        .collect())
}

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
/// stylelint `--formatter json`: one entry per file, each with its warnings (empty output is no finding).
fn parse_stylelint(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let text = stdout.trim();
    let files: Vec<SFile> = if text.is_empty() {
        Vec::new()
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "stylelint",
            source,
        })?
    };
    let mut out = Vec::new();
    for file in files {
        for w in file.warnings {
            // The range type is one line wide: a warning that spans lines is underlined to its first column.
            let end_col = if w.end_line == w.line && w.end_column > w.column {
                w.end_column
            } else {
                w.column + 1
            };
            out.push(RawFinding {
                path: file.source.clone(),
                range: RawRange::LineCol {
                    line: w.line,
                    col: w.column,
                    end_col,
                },
                tool_id: w.rule,
                message: w.text,
                suppressed: None,
                meta: RawMeta::default(),
            });
        }
    }
    Ok(out)
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
        // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
        // The crunk web-CSS family: specificity wars, id selectors and `!important` (all Advisory).
        ToolParser::StylelintJson => BTreeMap::from([
            ("no-descending-specificity", "WCSS001"),
            ("selector-max-compound-selectors", "WCSS001"),
            ("selector-max-specificity", "WCSS001"),
            ("selector-max-id", "WCSS002"),
            ("declaration-no-important", "WCSS003"),
        ]),
        ToolParser::ActionlintJson
        | ToolParser::Sarif
        | ToolParser::CargoJson
        | ToolParser::RuffJson
        | ToolParser::TyGitlab
        | ToolParser::PyrightJson
        | ToolParser::TscText
        | ToolParser::EslintJson
        | ToolParser::RoslynSarif
        | ToolParser::None => BTreeMap::new(),
        // frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
        ToolParser::TyposJson => BTreeMap::from([("typo", "SPELL001")]),
        // frob:ticket 01M4D94J5J2TZEXTB8GH36992B
        ToolParser::FormatterList => BTreeMap::from([(crate::fmt_parse::FMT_TOOL_ID, "FMT001")]),
        // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
        ToolParser::SemverChecksText | ToolParser::GriffeText | ToolParser::ApiExtractorText => {
            BTreeMap::from([(crate::semver_parse::SEMVER_TOOL_ID, "VERSION001")])
        }
    }
}

// frob:ticket 01M5F0A96X8KCH10HNHTXCDEKR
/// True when `id` is a rule a bound stage can report but another product declares.
///
/// `CI003` is declared by `grimble-ci`; the zizmor stage still raises it here, so `--only CI003`
/// must stay a known name even though no frob declaration carries it.
pub(crate) fn is_sibling_bound_id(id: &str) -> bool {
    SIBLING_OWNED.contains(&id)
}

/// Rule ids a frob stage raises that a sibling product declares.
const SIBLING_OWNED: [&str; 1] = ["CI003"];

/// Rule used for a tool id that no map covers.
fn fallback(parser: ToolParser) -> &'static str {
    match parser {
        ToolParser::ActionlintJson => "CI014",
        ToolParser::FormatterList => "FMT001",
        ToolParser::SemverChecksText | ToolParser::GriffeText | ToolParser::ApiExtractorText => {
            "VERSION001"
        }
        ToolParser::CargoJson
        | ToolParser::RuffJson
        | ToolParser::TyGitlab
        | ToolParser::PyrightJson
        | ToolParser::TscText
        | ToolParser::EslintJson
        | ToolParser::RoslynSarif => "LINT001",
        _ => "TOOL002",
    }
}

/// The built-in rule for a cargo diagnostic the id map does not name, by lint shape.
///
/// `unused_*` and `dead_code` are dead code, `too_many_arguments` is the
/// parameter-count rule and a deny-by-default clippy lint (the correctness
/// group) is a logic finding; anything else stays a generic lint.
fn cargo_target(raw: &RawFinding) -> Option<&'static str> {
    let name = raw.tool_id.rsplit("::").next().unwrap_or(&raw.tool_id);
    if raw.meta.group.as_deref() == Some("correctness") {
        Some("LOGIC001")
    } else if name.starts_with("unused") || name == "dead_code" {
        Some("DEAD001")
    } else if name == "too_many_arguments" {
        Some("NEAT002")
    } else {
        None
    }
}

/// What the ruff code table says about one code.
enum RuffRule {
    /// The rule is switched off (`PLR2004` magic values; the lint catalogue keeps it off).
    Off,
    /// The code belongs to this frob rule.
    Maps(&'static str),
    /// No family claims the code; it falls through to `LINT001`.
    Unmapped,
}

// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
/// The built-in rule for a ruff code the id map does not name, by code family.
fn ruff_target(code: &str) -> RuffRule {
    let target = match code {
        "PLR2004" => return RuffRule::Off,
        "S110" => "ERR001",
        "BLE001" | "E722" => "ERR003",
        _ if code.starts_with("F401") || code.starts_with("F841") || code.starts_with("ARG") => {
            "DEAD001"
        }
        _ if code.starts_with("ASYNC") => "CONC001",
        _ if code.starts_with("PT") => "TESTQ001",
        _ if code.starts_with('B') && code[1..].bytes().all(|b| b.is_ascii_digit()) => "LOGIC001",
        _ => return RuffRule::Unmapped,
    };
    RuffRule::Maps(target)
}

/// Default severity of a rule this module can produce.
fn default_severity(rule: &str) -> Severity {
    match rule {
        // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
        // VERSION001: a removed public item under an unchanged major version breaks consumers.
        "CI006" | "CI007" | "VERSION001" => Severity::Error,
        // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
        "CI001" | "CI003" | "CI014" | "DEAD001" | "FMT001" | "ERR001" | "ERR003" | "CONC001"
        | "TESTQ001" | "LOGIC001" | "A11Y001" | "REACT001" | "TYPING001" | "UNITY101" => {
            Severity::Warn
        }
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
    let ruff = if stage.parser == ToolParser::RuffJson && !stage.id_map.contains_key(&raw.tool_id) {
        ruff_target(&raw.tool_id)
    } else {
        RuffRule::Unmapped
    };
    if matches!(ruff, RuffRule::Off) {
        tracing::debug!(stage = %stage.name, code = %raw.tool_id, "ruff rule is off; dropped");
        return None;
    }
    let target = stage
        .id_map
        .get(&raw.tool_id)
        .map(String::as_str)
        .or_else(|| defaults.get(raw.tool_id.as_str()).copied())
        .or(match ruff {
            RuffRule::Maps(id) => Some(id),
            _ => None,
        })
        .or_else(|| {
            (stage.parser == ToolParser::EslintJson)
                .then(|| eslint_target(&raw.tool_id))
                .flatten()
        })
        .or_else(|| {
            (stage.parser == ToolParser::RoslynSarif)
                .then(|| roslyn_target(&raw.tool_id))
                .flatten()
        })
        .or_else(|| {
            (stage.parser == ToolParser::CargoJson)
                .then(|| cargo_target(raw))
                .flatten()
        })
        .unwrap_or_else(|| fallback(stage.parser));
    let id = target.parse::<RuleId>().unwrap_or_else(|err| {
        tracing::warn!(stage = %stage.name, tool_id = %raw.tool_id, %err, "bad id_map target; using the fallback");
        fallback(stage.parser)
            .parse()
            .unwrap_or_else(|e| unreachable!("fallback ids are valid: {e}"))
    });
    if stage.parser == ToolParser::CargoJson {
        // rustc's level is the lint's configured severity (`-D warnings` makes it an error).
        severity_override = Some(match raw.meta.level.as_deref() {
            Some("error") => Severity::Error,
            _ => Severity::Warn,
        });
    }
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
pub(crate) fn compare(a: &[u64], b: &[u64]) -> Ordering {
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

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
/// The default arguments that print `parser`'s tool version.
pub(crate) fn default_version_args(parser: ToolParser) -> Option<Vec<String>> {
    match parser {
        ToolParser::ZizmorJsonV1
        | ToolParser::StylelintJson
        | ToolParser::RuffJson
        | ToolParser::TyGitlab
        | ToolParser::PyrightJson
        | ToolParser::TscText
        | ToolParser::EslintJson
        | ToolParser::RoslynSarif
        | ToolParser::FormatterList
        | ToolParser::SemverChecksText
        | ToolParser::GriffeText
        | ToolParser::ApiExtractorText
        | ToolParser::TyposJson => Some(vec!["--version".to_owned()]),
        ToolParser::ActionlintJson => Some(vec!["-version".to_owned()]),
        ToolParser::Sarif | ToolParser::CargoJson | ToolParser::None => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ZIZMOR: &str = include_str!("../tests/fixtures/zizmor-json-v1.json");
    const ACTIONLINT: &str = include_str!("../tests/fixtures/actionlint.json");
    const RUFF: &str = include_str!("../tests/fixtures/ruff.json");
    const ESLINT: &str = include_str!("../tests/fixtures/eslint.json");
    const UNITY_SARIF: &str = include_str!("../tests/fixtures/sarif-roslyn-unity.json");

    fn stage(parser: ToolParser) -> ToolStage {
        ToolStage {
            name: "t".to_owned(),
            def: None,
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
            tier: crate::ToolTier::Ticket,
            unscoped_packages: vec!["--workspace".to_owned()],
        }
    }

    // frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
    // frob:tests crates/gob-check/src/tool_parse.rs::parse
    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn typos_json_lines_become_advisory_spell001_with_the_correction() {
        // Built at runtime so the repository's own typos stage does not flag the fixture.
        let (bad, good) = (["te", "h"].concat(), "the");
        let out = format!(
            "{{\"type\":\"typo\",\"path\":\"src/a.rs\",\"line_num\":3,\"byte_offset\":4,\"typo\":\"{bad}\",\"corrections\":[\"{good}\"]}}\n{{\"type\":\"binary_file\",\"path\":\"x.bin\"}}\n"
        );
        let found = parse(ToolParser::TyposJson, &out).expect("parse");
        assert_eq!(found.len(), 1, "non-typo lines are skipped");
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 3,
                col: 5,
                end_col: 8
            }
        );
        assert!(found[0].message.contains("did you mean the?"));
        let (id, sev) = classify(&stage(ToolParser::TyposJson), &found[0]).expect("kept");
        assert_eq!(
            (id.to_string(), sev),
            ("SPELL001".to_owned(), Severity::Advisory)
        );
        // typos prints nothing for words its typos.toml allowlists, so no finding.
        assert!(parse(ToolParser::TyposJson, "").expect("empty").is_empty());
        assert!(parse(ToolParser::TyposJson, "{").is_err());
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

    // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
    // frob:tests crates/gob-check/src/tool_parse.rs::parse
    #[test]
    fn ruff_output_parses_with_row_and_column() {
        let found = parse(ToolParser::RuffJson, RUFF).expect("parse");
        assert_eq!(found.len(), 8);
        assert_eq!(found[0].tool_id, "F401");
        assert_eq!(found[0].path, "/work/app/main.py");
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 1,
                col: 8,
                end_col: 10
            }
        );
        // A multi-row violation is underlined to its first column.
        assert_eq!(
            found[4].range,
            RawRange::LineCol {
                line: 18,
                col: 5,
                end_col: 6
            }
        );
        assert!(parse(ToolParser::RuffJson, "").expect("empty").is_empty());
        assert!(parse(ToolParser::RuffJson, "[").is_err());
    }

    // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn ruff_codes_map_to_families_and_plr2004_is_off() {
        let st = stage(ToolParser::RuffJson);
        let found = parse(ToolParser::RuffJson, RUFF).expect("parse");
        let ids: Vec<_> = found
            .iter()
            .filter_map(|f| classify(&st, f).map(|(id, _)| (f.tool_id.as_str(), id.to_string())))
            .collect();
        let want = [
            ("F401", "DEAD001"),
            ("BLE001", "ERR003"),
            ("E722", "ERR003"),
            ("S110", "ERR001"),
            ("ASYNC110", "CONC001"),
            ("PT011", "TESTQ001"),
            ("E501", "LINT001"),
        ];
        assert_eq!(
            ids,
            want.map(|(a, b)| (a, b.to_owned())),
            "PLR2004 is dropped"
        );
        let mut on = stage(ToolParser::RuffJson);
        on.id_map.insert("PLR2004".to_owned(), "LINT001".to_owned());
        assert!(
            found
                .iter()
                .any(|f| f.tool_id == "PLR2004" && classify(&on, f).is_some())
        );
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

    // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
    const STYLELINT: &str = include_str!("../tests/fixtures/stylelint.json");

    // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
    // frob:tests crates/gob-check/src/tool_parse.rs::parse_stylelint
    #[test]
    fn stylelint_output_parses_with_line_and_column() {
        let found = parse(ToolParser::StylelintJson, STYLELINT).expect("parse");
        assert_eq!(found.len(), 3, "the clean file adds nothing");
        assert_eq!(found[0].tool_id, "declaration-no-important");
        assert_eq!(found[0].path, "/work/site/app.css");
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 2,
                col: 3,
                end_col: 24
            }
        );
        assert_eq!(
            found[1].range,
            RawRange::LineCol {
                line: 5,
                col: 1,
                end_col: 2
            },
            "a warning that spans lines ends one column after its start"
        );
        assert!(
            parse(ToolParser::StylelintJson, "")
                .expect("empty")
                .is_empty()
        );
        assert!(parse(ToolParser::StylelintJson, "not json").is_err());
    }

    // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn stylelint_findings_carry_crunk_ids_and_are_advisory() {
        let st = stage(ToolParser::StylelintJson);
        let found = parse(ToolParser::StylelintJson, STYLELINT).expect("parse");
        let got: Vec<(String, Severity)> = found
            .iter()
            .filter_map(|f| classify(&st, f))
            .map(|(id, sev)| (id.to_string(), sev))
            .collect();
        assert_eq!(
            got,
            [
                ("WCSS003".to_owned(), Severity::Advisory),
                ("WCSS002".to_owned(), Severity::Advisory),
                ("TOOL002".to_owned(), Severity::Advisory),
            ]
        );
        let mut mapped = stage(ToolParser::StylelintJson);
        mapped
            .id_map
            .insert("color-named".to_owned(), "WCSS009".to_owned());
        assert_eq!(
            classify(&mapped, &found[2]).map(|c| c.0.to_string()),
            Some("WCSS009".to_owned()),
            "a configured id_map entry wins"
        );
    }

    // frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
    // frob:tests crates/gob-check/src/tool_parse.rs::parse_eslint
    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn eslint_output_parses_and_plugin_ids_map_to_families() {
        let found = parse(ToolParser::EslintJson, ESLINT).expect("parse");
        assert_eq!(
            found.len(),
            6,
            "the parse error and the clean file add nothing"
        );
        assert_eq!(
            found[0].range,
            RawRange::LineCol {
                line: 7,
                col: 5,
                end_col: 22
            }
        );
        assert_eq!(
            found[1].range,
            RawRange::LineCol {
                line: 12,
                col: 3,
                end_col: 4
            },
            "a multi-line message ends one column after its start"
        );
        let st = stage(ToolParser::EslintJson);
        let got: Vec<(String, String, Severity)> = found
            .iter()
            .filter_map(|f| {
                classify(&st, f).map(|(id, sev)| (f.tool_id.clone(), id.to_string(), sev))
            })
            .collect();
        let want = [
            ("jsx-a11y/alt-text", "A11Y001", Severity::Warn),
            ("react-hooks/exhaustive-deps", "REACT001", Severity::Warn),
            ("react/no-array-index-key", "REACT001", Severity::Warn),
            (
                "@typescript-eslint/no-floating-promises",
                "CONC001",
                Severity::Warn,
            ),
            (
                "@typescript-eslint/no-explicit-any",
                "TYPING001",
                Severity::Warn,
            ),
            ("no-console", "LINT001", Severity::Advisory),
        ];
        assert_eq!(got, want.map(|(a, b, c)| (a.to_owned(), b.to_owned(), c)));
        assert!(parse(ToolParser::EslintJson, "").expect("empty").is_empty());
        assert!(parse(ToolParser::EslintJson, "not json").is_err());
    }

    // frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
    // frob:tests crates/gob-check/src/tool_parse.rs::roslyn_target
    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn unity_analyzer_ids_map_to_unity101_and_suppressed_dead_code_is_set_aside() {
        let found = parse(ToolParser::RoslynSarif, UNITY_SARIF).expect("parse");
        let st = stage(ToolParser::RoslynSarif);
        let live: Vec<(String, String)> = found
            .iter()
            .filter(|f| f.suppressed.is_none())
            .filter_map(|f| classify(&st, f).map(|(id, _)| (f.tool_id.clone(), id.to_string())))
            .collect();
        let want = [
            ("UNT0008", "UNITY101"),
            ("UNT0001", "UNITY101"),
            ("VSTHRD100", "CONC001"),
            ("IDE0051", "DEAD001"),
            ("CA1822", "LINT001"),
        ];
        assert_eq!(live, want.map(|(a, b)| (a.to_owned(), b.to_owned())));
        assert!(
            found
                .iter()
                .any(|f| f.tool_id == "IDE0051" && f.suppressed.is_some()),
            "the engine-called message's IDE0051 is flagged suppressed by the USP suppressor"
        );
        let (_, sev) = classify(&st, &found[0]).expect("classified");
        assert_eq!(sev, Severity::Warn);
    }

    // frob:tests crates/gob-check/src/tool_parse.rs::classify
    #[test]
    fn cargo_lints_map_to_dead_neat_logic_and_lint_with_the_level_as_severity() {
        let st = stage(ToolParser::CargoJson);
        let found = parse(
            ToolParser::CargoJson,
            include_str!("../tests/fixtures/cargo-clippy.jsonl"),
        )
        .expect("parse");
        let got: Vec<(String, Severity)> = found
            .iter()
            .filter_map(|f| classify(&st, f))
            .map(|(id, sev)| (id.to_string(), sev))
            .collect();
        assert_eq!(
            got,
            [
                ("DEAD001".to_owned(), Severity::Warn),
                ("NEAT002".to_owned(), Severity::Error),
                ("LOGIC001".to_owned(), Severity::Error),
                ("LINT001".to_owned(), Severity::Error),
                ("LINT001".to_owned(), Severity::Error),
            ]
        );
        let mut mapped = stage(ToolParser::CargoJson);
        mapped
            .id_map
            .insert("clippy::needless_return".to_owned(), "NEAT013".to_owned());
        assert_eq!(
            classify(&mapped, &found[3]).map(|c| c.0.to_string()),
            Some("NEAT013".to_owned()),
            "a configured id_map entry wins"
        );
    }
}
