//! Parsers for the type checkers bound as tools (ty `--output-format gitlab`, pyright `--outputjson`, tsc `--pretty false`).
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
    tracing::debug!(
        count = out.general_diagnostics.len(),
        "pyright diagnostics parsed"
    );
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

/// Splits `path(line,col): error TSnnnn: message` into its parts; `None` for any other line.
fn tsc_diag(line: &str) -> Option<(&str, u32, u32, &str, &str, &str)> {
    let (head, rest) = line.split_once("): ")?;
    let (path, pos) = head.rsplit_once('(')?;
    let (l, c) = pos.split_once(',')?;
    let (level, rest) = rest.split_once(' ')?;
    let (code, message) = rest.split_once(": ")?;
    if !matches!(level, "error" | "warning") || !code.starts_with("TS") {
        return None;
    }
    Some((path, l.parse().ok()?, c.parse().ok()?, level, code, message))
}

/// tsc `--pretty false`: one `path(line,col): error TSnnnn: message` per diagnostic with indented continuation lines; a diagnostic with no file (`error TS5023: ...`) means the run did not check the project, so the parse fails.
pub(crate) fn parse_tsc(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let mut out: Vec<RawFinding> = Vec::new();
    for line in stdout.lines() {
        if let Some((path, l, c, level, code, message)) = tsc_diag(line) {
            out.push(RawFinding {
                path: path.to_owned(),
                range: RawRange::LineCol {
                    line: l,
                    col: c,
                    end_col: c + 1,
                },
                tool_id: code.to_owned(),
                message: message.to_owned(),
                suppressed: None,
                meta: RawMeta {
                    group: None,
                    level: Some(level.to_owned()),
                },
            });
        } else if line.starts_with(char::is_whitespace) && !line.trim().is_empty() {
            if let Some(last) = out.last_mut() {
                last.message.push(' ');
                last.message.push_str(line.trim());
            }
        } else if line.starts_with("error TS") || line.starts_with("warning TS") {
            return Err(ParseError::Text {
                format: "tsc",
                message: line.to_owned(),
            });
        }
    }
    tracing::debug!(count = out.len(), "tsc diagnostics parsed");
    Ok(out)
}

/// Whether `stage` is a type checker whose clean verdict means strict: Python checkers always, `tsc` only with an explicit `--strict` argument (a bare `tsc` run proves nothing about `any`).
// frob:ticket 01M4CXSY224VNMR2R5Q69D9E89
pub fn is_strict_checker(stage: &crate::config::ToolStage) -> bool {
    match stage.parser {
        ToolParser::TscText => stage.args.iter().any(|a| a == "--strict"),
        ToolParser::TyGitlab | ToolParser::PyrightJson => true,
        _ => false,
    }
}

/// Whether `path` is a TypeScript or JavaScript source (comments use `//`, not `#`).
fn is_ts_path(path: &str) -> bool {
    [".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"]
        .iter()
        .any(|e| path.ends_with(e))
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
        if is_ts_path(path) {
            facts.scan_ts_ignores(path, text);
        } else {
            facts.scan_ignores(path, text);
        }
    }
    tracing::debug!(
        files = files.len(),
        findings = found.len(),
        "type facts derived"
    );
    Ok(facts)
}

#[cfg(test)]
mod tests {
    use super::*;

    const TY: &str = include_str!("../tests/fixtures/ty-gitlab.json");
    const TSC: &str = include_str!("../tests/fixtures/tsc.txt");
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
    // frob:tests crates/gob-check/src/type_parse.rs::is_strict_checker
    fn tsc_needs_an_explicit_strict_flag() {
        let stage = |args: &str| -> crate::config::ToolStage {
            let toml = format!(
                "name = \"t\"\ncommand = \"tsc\"\nargs = [{args}]\nparser = \"tsc-text\"\n"
            );
            toml::from_str(&toml).expect("stage")
        };
        assert!(is_strict_checker(&stage("\"--noEmit\", \"--strict\"")));
        assert!(!is_strict_checker(&stage("\"--noEmit\"")));
    }

    #[test]
    // frob:tests crates/gob-check/src/type_parse.rs::parse_tsc
    fn tsc_parses_diagnostics_continuations_and_global_errors() {
        let f = parse_tsc(TSC).expect("parse");
        assert_eq!(f.len(), 2);
        assert_eq!(f[0].path, "src/bad.ts");
        assert_eq!(f[0].tool_id, "TS2322");
        assert_eq!(
            f[0].range,
            RawRange::LineCol {
                line: 4,
                col: 7,
                end_col: 8
            }
        );
        assert!(f[1].message.contains("is missing"));
        assert!(f[1].message.contains("required in type"));
        assert!(parse_tsc("").expect("empty").is_empty());
        assert!(parse_tsc("error TS5023: Unknown compiler option 'x'.\n").is_err());
    }

    #[test]
    // frob:tests crates/gob-check/src/type_parse.rs::type_facts_from_output
    fn tsc_facts_mark_unreported_files_clean() {
        let files = vec![
            ("src/bad.ts".to_owned(), "x.run();\n".to_owned()),
            (
                "src/ok.ts".to_owned(),
                "// @ts-ignore\nx.run();\ny.run();\n".to_owned(),
            ),
        ];
        let facts = type_facts_from_output(ToolParser::TscText, TSC, TypesTrust::Checked, &files)
            .expect("facts");
        assert_eq!(
            facts.weight("src/bad.ts", 1),
            gob_symbols::AnnotationWeight::Claimed
        );
        assert_eq!(
            facts.weight("src/ok.ts", 3),
            gob_symbols::AnnotationWeight::Exact
        );
        assert_eq!(
            facts.weight("src/ok.ts", 2),
            gob_symbols::AnnotationWeight::Claimed
        );
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
        assert_eq!(
            facts.weight("app/main.py", 1),
            gob_symbols::AnnotationWeight::Claimed
        );
        assert_eq!(
            facts.weight("app/ok.py", 1),
            gob_symbols::AnnotationWeight::Exact
        );
        assert!(
            type_facts_from_output(ToolParser::TyGitlab, "[", TypesTrust::Checked, &files).is_err()
        );
        assert!(parse_pyright("{").is_err());
    }
}
