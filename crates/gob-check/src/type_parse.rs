//! Parsers for the Python type checkers bound as tools (ty `--output-format gitlab`, pyright `--outputjson`).
// frob:ticket 01M4CXSWZ95SVDADAB97TYG963

use gob_symbols::{TypeFacts, TypesTrust};
use serde::Deserialize;

use crate::config::ToolParser;

use crate::tool_parse::{ParseError, RawFinding, RawMeta, RawRange};

#[derive(Deserialize)]
struct TyFinding {
    description: String,
    check_name: String,
    location: TyLocation,
}

#[derive(Deserialize)]
struct TyLocation {
    path: String,
    positions: TyPositions,
}

#[derive(Deserialize)]
struct TyPositions {
    begin: TyPos,
    end: Option<TyPos>,
}

#[derive(Deserialize)]
struct TyPos {
    line: u32,
    column: u32,
}

/// ty `--output-format gitlab`: a code-quality array with 1-based positions (empty output is no finding).
pub(crate) fn parse_ty_gitlab(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let text = stdout.trim();
    let found: Vec<TyFinding> = if text.is_empty() {
        Vec::new()
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "ty gitlab",
            source,
        })?
    };
    tracing::debug!(count = found.len(), "ty findings parsed");
    Ok(found
        .into_iter()
        .map(|f| {
            let b = f.location.positions.begin;
            let end_col = match f.location.positions.end {
                Some(e) if e.line == b.line && e.column > b.column => e.column,
                _ => b.column + 1,
            };
            RawFinding {
                path: f.location.path,
                range: RawRange::LineCol {
                    line: b.line,
                    col: b.column,
                    end_col,
                },
                tool_id: f.check_name,
                message: f.description,
                suppressed: None,
                meta: RawMeta::default(),
            }
        })
        .collect())
}

#[derive(Deserialize)]
struct PyrightOut {
    #[serde(rename = "generalDiagnostics", default)]
    general_diagnostics: Vec<PyrightDiag>,
}

#[derive(Deserialize)]
struct PyrightDiag {
    file: String,
    severity: String,
    message: String,
    range: PyrightRange,
    rule: Option<String>,
}

#[derive(Deserialize)]
struct PyrightRange {
    start: PyrightPos,
    end: PyrightPos,
}

#[derive(Deserialize)]
struct PyrightPos {
    line: u32,
    character: u32,
}

/// pyright `--outputjson`: only error and warning diagnostics become findings; positions are 0-based and shifted to 1-based.
pub(crate) fn parse_pyright(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let text = stdout.trim();
    let out: PyrightOut = if text.is_empty() {
        PyrightOut {
            general_diagnostics: Vec::new(),
        }
    } else {
        serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: "pyright",
            source,
        })?
    };
    tracing::debug!(count = out.general_diagnostics.len(), "pyright diagnostics parsed");
    Ok(out
        .general_diagnostics
        .into_iter()
        .filter(|d| d.severity == "error" || d.severity == "warning")
        .map(|d| {
            let (s, e) = (d.range.start, d.range.end);
            let end_col = if e.line == s.line && e.character > s.character {
                e.character + 1
            } else {
                s.character + 2
            };
            RawFinding {
                path: d.file,
                range: RawRange::LineCol {
                    line: s.line + 1,
                    col: s.character + 1,
                    end_col,
                },
                tool_id: d.rule.unwrap_or_else(|| "pyright".to_owned()),
                message: d.message,
                suppressed: None,
                meta: RawMeta {
                    group: None,
                    level: Some(d.severity),
                },
            }
        })
        .collect())
}

/// Derive [`TypeFacts`] from a bound checker's stdout: every `(path, text)` file the checker reported nothing on is clean, and ignore comments are scanned from `text`.
///
/// # Errors
///
/// The parse failure message when `stdout` is not the checker's format.
pub fn type_facts_from_output(
    parser: ToolParser,
    stdout: &str,
    trust: TypesTrust,
    files: &[(String, String)],
) -> Result<TypeFacts, String> {
    let found = crate::tool_parse::parse(parser, stdout).map_err(|e| e.to_string())?;
    let mut facts = TypeFacts::new(trust);
    for (path, text) in files {
        let dirty = found.iter().any(|f| {
            let p = f.path.trim_start_matches("./");
            p == path || p.ends_with(&format!("/{path}"))
        });
        if !dirty {
            facts.mark_clean(path);
        }
        facts.scan_ignores(path, text);
    }
    tracing::debug!(files = files.len(), findings = found.len(), "type facts derived");
    Ok(facts)
}

#[cfg(test)]
mod tests {
    use super::*;

    const TY: &str = include_str!("../tests/fixtures/ty-gitlab.json");
    const PYRIGHT: &str = include_str!("../tests/fixtures/pyright.json");

    #[test]
    // frob:tests crates/gob-check/src/type_parse.rs::parse_ty_gitlab
    fn ty_gitlab_parses_positions_and_ids() {
        let f = parse_ty_gitlab(TY).expect("parse");
        assert_eq!(f.len(), 2);
        assert_eq!(f[0].path, "app/main.py");
        assert_eq!(f[0].tool_id, "invalid-assignment");
        assert_eq!(
            f[0].range,
            RawRange::LineCol {
                line: 4,
                col: 5,
                end_col: 9
            }
        );
        assert!(parse_ty_gitlab("").expect("empty").is_empty());
        assert!(parse_ty_gitlab("[").is_err());
    }

    #[test]
    // frob:tests crates/gob-check/src/type_parse.rs::parse_pyright
    fn pyright_keeps_errors_only_and_shifts_to_one_based() {
        let f = parse_pyright(PYRIGHT).expect("parse");
        assert_eq!(f.len(), 1);
        assert_eq!(f[0].tool_id, "reportArgumentType");
        assert_eq!(
            f[0].range,
            RawRange::LineCol {
                line: 4,
                col: 5,
                end_col: 9
            }
        );
        assert!(parse_pyright("").expect("empty").is_empty());
    }

    #[test]
    // frob:tests crates/gob-check/src/type_parse.rs::type_facts_from_output
    fn files_with_findings_are_not_clean() {
        let files = vec![
            ("app/main.py".to_owned(), "x = 1\n".to_owned()),
            ("app/ok.py".to_owned(), "y = 2\n".to_owned()),
        ];
        let facts = type_facts_from_output(ToolParser::TyGitlab, TY, TypesTrust::Checked, &files)
            .expect("facts");
        assert_eq!(facts.weight("app/main.py", 1), gob_symbols::AnnotationWeight::Claimed);
        assert_eq!(facts.weight("app/ok.py", 1), gob_symbols::AnnotationWeight::Exact);
        assert!(type_facts_from_output(ToolParser::TyGitlab, "[", TypesTrust::Checked, &files).is_err());
        assert!(parse_pyright("{").is_err());
    }
}
