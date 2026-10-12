//! SARIF 2.1.0 reader for bound tools (oxlint, Biome, golangci-lint, Roslyn error logs, the eslint SARIF formatter).
//!
//! Pure: [`parse_sarif`] turns a log into [`RawFinding`]s. The tool's own id
//! (`ruleId`, else `rule.id`, else `rules[ruleIndex].id`) becomes `tool_id`;
//! mapping it to a frob id is `classify`'s job through the stage id map.
//! Results the tool suppressed are kept, flagged, so a native suppression of a
//! bound rule stays visible to EXC017 instead of vanishing.

use serde::Deserialize;

use crate::tool_parse::{ParseError, RawFinding, RawRange, RawSuppression};

#[derive(Deserialize)]
struct Log {
    version: Option<String>,
    runs: Option<Vec<Run>>,
}

#[derive(Deserialize)]
struct Run {
    #[serde(default)]
    tool: Tool,
    #[serde(default)]
    results: Vec<SResult>,
}

#[derive(Deserialize, Default)]
struct Tool {
    #[serde(default)]
    driver: Driver,
}

#[derive(Deserialize, Default)]
struct Driver {
    #[serde(default)]
    rules: Vec<Descriptor>,
}

#[derive(Deserialize)]
struct Descriptor {
    #[serde(default)]
    id: String,
}

#[derive(Deserialize)]
struct SResult {
    #[serde(rename = "ruleId")]
    rule_id: Option<String>,
    #[serde(rename = "ruleIndex")]
    rule_index: Option<i64>,
    rule: Option<RuleRef>,
    kind: Option<String>,
    #[serde(default)]
    message: Message,
    #[serde(default)]
    locations: Vec<Location>,
    #[serde(default)]
    suppressions: Vec<Suppression>,
}

#[derive(Deserialize)]
struct RuleRef {
    id: Option<String>,
}

#[derive(Deserialize, Default)]
struct Message {
    text: Option<String>,
    markdown: Option<String>,
}

#[derive(Deserialize)]
struct Location {
    #[serde(rename = "physicalLocation")]
    physical: Option<Physical>,
}

#[derive(Deserialize)]
struct Physical {
    #[serde(rename = "artifactLocation")]
    artifact: Option<Artifact>,
    region: Option<Region>,
}

#[derive(Deserialize)]
struct Artifact {
    uri: Option<String>,
}

#[derive(Deserialize)]
struct Region {
    #[serde(rename = "startLine")]
    start_line: Option<u32>,
    #[serde(rename = "startColumn")]
    start_column: Option<u32>,
    #[serde(rename = "endLine")]
    end_line: Option<u32>,
    #[serde(rename = "endColumn")]
    end_column: Option<u32>,
}

#[derive(Deserialize)]
struct Suppression {
    kind: Option<String>,
    status: Option<String>,
    justification: Option<String>,
}

/// Decode `%XX` escapes of a URI path; invalid escapes are kept literally.
fn percent_decode(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let hex = |b: u8| char::from(b).to_digit(16);
        if bytes[i] == b'%'
            && let (Some(hi), Some(lo)) = (
                bytes.get(i + 1).copied().and_then(hex),
                bytes.get(i + 2).copied().and_then(hex),
            )
        {
            out.push(
                u8::try_from(hi * 16 + lo)
                    .unwrap_or_else(|_| unreachable!("two hex digits fit a byte")),
            );
            i += 3;
        } else {
            out.push(bytes[i]);
            i += 1;
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// The filesystem path a SARIF artifact URI names (`file:///C:/x` becomes `C:/x`).
fn uri_path(uri: &str) -> String {
    let Some(rest) = uri.strip_prefix("file://") else {
        return percent_decode(uri);
    };
    let path = percent_decode(rest.trim_start_matches("localhost"));
    // `file:///C:/x` leaves `/C:/x`: drop the slash before a drive letter.
    match path.as_bytes() {
        [b'/', d, b':', ..] if d.is_ascii_alphabetic() => path[1..].to_owned(),
        _ => path,
    }
}

fn range_of(region: Option<&Region>) -> RawRange {
    let Some(r) = region else {
        return RawRange::None;
    };
    let Some(line) = r.start_line else {
        return RawRange::None;
    };
    let col = r.start_column.unwrap_or(1).max(1);
    RawRange::CharRange {
        line,
        col,
        end_line: r.end_line.unwrap_or(line).max(line),
        end_col: r.end_column.unwrap_or(col + 1),
    }
}

/// The `RawSuppression` of a result: an accepted (or status-less) suppression counts; a rejected or under-review one does not.
fn suppression_of(list: &[Suppression]) -> Option<RawSuppression> {
    list.iter()
        .find(|s| !matches!(s.status.as_deref(), Some("rejected" | "underReview")))
        .map(|s| RawSuppression {
            kind: s.kind.clone().unwrap_or_else(|| "inSource".to_owned()),
            justification: s.justification.clone().unwrap_or_default(),
        })
}

/// Parse a SARIF 2.1.0 log (all runs) into raw findings.
///
/// Results of kind `pass` or `notApplicable` are not findings and are dropped;
/// a result with no usable id is reported under the id `(no ruleId)`.
///
/// # Errors
///
/// [`ParseError`] when the text is not JSON, is not a SARIF log, or declares a
/// version other than 2.1.0.
pub(crate) fn parse_sarif(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let log: Log = serde_json::from_str(stdout).map_err(|source| ParseError::Json {
        format: "SARIF 2.1.0",
        source,
    })?;
    match log.version.as_deref() {
        Some("2.1.0") => {}
        other => {
            return Err(ParseError::Sarif(format!(
                "`version` is {} (expected \"2.1.0\")",
                other.map_or("missing".to_owned(), |v| format!("\"{v}\""))
            )));
        }
    }
    let Some(runs) = log.runs else {
        return Err(ParseError::Sarif("`runs` is missing".to_owned()));
    };
    let mut out = Vec::new();
    for run in runs {
        for r in run.results {
            if matches!(r.kind.as_deref(), Some("pass" | "notApplicable")) {
                continue;
            }
            let tool_id = r
                .rule_id
                .filter(|s| !s.is_empty())
                .or_else(|| r.rule.and_then(|x| x.id).filter(|s| !s.is_empty()))
                .or_else(|| {
                    usize::try_from(r.rule_index?)
                        .ok()
                        .and_then(|i| run.tool.driver.rules.get(i))
                        .map(|d| d.id.clone())
                        .filter(|s| !s.is_empty())
                })
                .unwrap_or_else(|| "(no ruleId)".to_owned());
            let physical = r.locations.iter().find_map(|l| l.physical.as_ref());
            let path = physical
                .and_then(|p| p.artifact.as_ref())
                .and_then(|a| a.uri.as_deref())
                .map(uri_path)
                .unwrap_or_default();
            out.push(RawFinding {
                path,
                range: range_of(physical.and_then(|p| p.region.as_ref())),
                tool_id,
                message: r.message.text.or(r.message.markdown).unwrap_or_default(),
                suppressed: suppression_of(&r.suppressions),
            });
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    // Real outputs captured 2026-10-08 with the tool versions in the file names (paths rewritten to /work/repo):
    // oxlint 1.87.0 `--format sarif`; Biome 2.5.15 `--reporter=sarif`; golangci-lint 2.14.0 `--output.sarif.path`;
    // ESLint 9.39.5 with @microsoft/eslint-formatter-sarif. The Roslyn log is built by hand from the ErrorLog
    // format (dotnet/roslyn docs/compilers/Error Log Format.md; `/errorlog:path,version=2`) because no dotnet SDK was available.
    const OXLINT: &str = include_str!("../tests/fixtures/sarif-oxlint-1.87.0.json");
    const BIOME: &str = include_str!("../tests/fixtures/sarif-biome-2.5.15.json");
    const GOLANGCI: &str = include_str!("../tests/fixtures/sarif-golangci-lint-2.14.0.json");
    const ESLINT: &str = include_str!("../tests/fixtures/sarif-eslint-9.39.5.json");
    const ROSLYN: &str = include_str!("../tests/fixtures/sarif-roslyn-errorlog-v2.1.json");

    fn ids(found: &[RawFinding]) -> Vec<&str> {
        found.iter().map(|f| f.tool_id.as_str()).collect()
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn oxlint_log_parses_with_its_prefixed_id_and_character_columns() {
        let found = parse_sarif(OXLINT).expect("parse");
        assert_eq!(ids(&found), ["eslint(no-debugger)"]);
        assert_eq!(found[0].path, "a.js");
        assert_eq!(
            found[0].range,
            RawRange::CharRange {
                line: 1,
                col: 1,
                end_line: 1,
                end_col: 10
            }
        );
        assert!(found[0].message.contains("debugger"));
        assert!(found[0].suppressed.is_none());
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn biome_and_golangci_logs_parse() {
        let found = parse_sarif(BIOME).expect("parse");
        assert_eq!(
            ids(&found),
            [
                "lint/suspicious/noDebugger",
                "lint/suspicious/noDoubleEquals"
            ]
        );
        assert_eq!(found[1].path, "/work/repo/a.js");
        let go = parse_sarif(GOLANGCI).expect("parse");
        assert_eq!(ids(&go), ["errcheck"]);
        assert_eq!(go[0].path, "main.go");
        assert_eq!(
            go[0].range,
            RawRange::CharRange {
                line: 3,
                col: 24,
                end_line: 3,
                end_col: 25
            },
            "a region with no end is one column wide"
        );
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn eslint_in_source_suppression_is_kept_and_flagged() {
        let found = parse_sarif(ESLINT).expect("parse");
        assert_eq!(ids(&found), ["no-debugger", "eqeqeq", "eqeqeq"]);
        assert_eq!(
            found[1].path, "/work/repo/a.js",
            "file:// uri becomes a path"
        );
        assert!(found[0].suppressed.is_none() && found[1].suppressed.is_none());
        let s = found[2].suppressed.as_ref().expect("suppressed");
        assert_eq!(s.kind, "inSource");
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn roslyn_log_decodes_uris_and_honours_suppression_status() {
        let found = parse_sarif(ROSLYN).expect("parse");
        assert_eq!(ids(&found), ["CS0168", "UNT0006", "RS0016", "CS8019"]);
        assert_eq!(found[0].path, "C:/work/My Game/Assets/Player.cs");
        assert!(found[0].suppressed.is_none());
        assert_eq!(
            found[1].suppressed.as_ref().map(|s| s.kind.as_str()),
            Some("inSource")
        );
        assert!(
            found[2].suppressed.is_none(),
            "a rejected suppression does not suppress"
        );
        assert_eq!(found[3].range, RawRange::None);
        assert_eq!(found[3].path, "");
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn rule_id_falls_back_to_rule_ref_then_descriptor_index() {
        let log = r#"{"version":"2.1.0","runs":[{"tool":{"driver":{"rules":[{"id":"R0"},{"id":"R1"}]}},
          "results":[{"rule":{"id":"X"},"message":{"text":"a"}},{"ruleIndex":1,"message":{"text":"b"}},
                     {"message":{"text":"c"}},{"ruleId":"P","kind":"pass","message":{"text":"d"}}]}]}"#;
        let found = parse_sarif(log).expect("parse");
        assert_eq!(ids(&found), ["X", "R1", "(no ruleId)"]);
    }

    // frob:tests crates/gob-check/src/sarif.rs::parse_sarif
    #[test]
    fn unreadable_logs_are_errors() {
        assert!(parse_sarif("not json").is_err());
        assert!(parse_sarif("{}").is_err(), "no version");
        assert!(parse_sarif(r#"{"version":"1.0.0","runs":[]}"#).is_err());
        assert!(parse_sarif(r#"{"version":"2.1.0"}"#).is_err(), "no runs");
        assert!(
            parse_sarif(r#"{"version":"2.1.0","runs":[]}"#)
                .expect("empty")
                .is_empty()
        );
    }

    #[test]
    fn uris_decode_percent_escapes_and_drive_letters() {
        assert_eq!(uri_path("file:///home/a%20b/c.cs"), "/home/a b/c.cs");
        assert_eq!(uri_path("file:///C:/x/y.cs"), "C:/x/y.cs");
        assert_eq!(uri_path("src/a%2Bb.go"), "src/a+b.go");
        assert_eq!(uri_path("bad%zz"), "bad%zz");
    }
}
