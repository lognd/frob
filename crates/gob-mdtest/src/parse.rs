//! Parsing of markdown suites into cases and marker expectations.

use std::collections::BTreeMap;

use gob_rules::{RuleId, Severity};

/// Whether a block must produce findings or none.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Expect {
    /// The rule must fire.
    Fire,
    /// The rule must stay silent.
    Clean,
}

impl std::fmt::Display for Expect {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Fire => "fire",
            Self::Clean => "clean",
        })
    }
}

/// A finding asserted by an inline marker comment.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Marker {
    /// 1-based line within the block.
    pub line: u32,
    /// Rule named by the marker.
    pub rule: RuleId,
    /// `Error` for `error:`, `Warn` for `warn:`.
    pub severity: Severity,
}

/// One parsed fenced block, before it is handed to the runner.
#[derive(Debug, Clone)]
pub struct Block {
    /// Heading path plus ordinal, for reports.
    pub name: String,
    /// 1-based line of the opening fence in the markdown file.
    pub fence_line: usize,
    /// Block language (first info token).
    pub language: String,
    /// Virtual file name.
    pub file_name: String,
    /// Block body text.
    pub text: String,
    /// Rule under test.
    pub rule: RuleId,
    /// Fire or clean.
    pub expect: Expect,
    /// Optional inline TOML config.
    pub config: Option<String>,
    /// Inline marker expectations.
    pub markers: Vec<Marker>,
    /// True when the `snapshot-diagnostics` suite header was in force.
    pub snapshot: bool,
}

/// Why a suite could not be parsed into cases.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("line {line}: {message}")]
pub struct ParseError {
    /// 1-based markdown line of the offending fence.
    pub line: usize,
    /// What is wrong.
    pub message: String,
}

/// Split an info string into tokens, honouring double quotes after `key=`.
fn tokenize(info: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut quoted = false;
    for c in info.chars() {
        match c {
            '"' => quoted = !quoted,
            c if c.is_whitespace() && !quoted => {
                if !cur.is_empty() {
                    out.push(std::mem::take(&mut cur));
                }
            }
            c => cur.push(c),
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Default file extension for a language tag.
fn extension(lang: &str) -> &str {
    match lang {
        "rust" | "rs" => "rs",
        "python" | "py" => "py",
        "javascript" | "js" => "js",
        "typescript" | "ts" => "ts",
        "markdown" | "md" => "md",
        "yaml" | "yml" => "yaml",
        "shell" | "bash" | "sh" => "sh",
        "" => "txt",
        other => other,
    }
}

/// Extract markers from a block body.
fn markers(text: &str, line_err: usize) -> Result<Vec<Marker>, ParseError> {
    let mut out = Vec::new();
    for (i, l) in text.lines().enumerate() {
        let Some(c) = ["//", "#", "<!--"].iter().filter_map(|t| l.find(t)).min() else {
            continue;
        };
        let comment = &l[c..];
        for (key, severity) in [("error:", Severity::Error), ("warn:", Severity::Warn)] {
            if let Some(p) = comment.find(key) {
                let id: String = comment[p + key.len()..]
                    .trim_start()
                    .chars()
                    .take_while(char::is_ascii_alphanumeric)
                    .collect();
                let rule = id.parse::<RuleId>().map_err(|e| ParseError {
                    line: line_err,
                    message: format!("bad marker on block line {}: {e}", i + 1),
                })?;
                let line = u32::try_from(i + 1).unwrap_or(u32::MAX);
                out.push(Marker {
                    line,
                    rule,
                    severity,
                });
            }
        }
    }
    Ok(out)
}

/// Parse a markdown suite into blocks.
///
/// # Errors
///
/// Returns [`ParseError`] for a malformed info string, missing `rule` or
/// `expect`, an unterminated fence, or markers inside an `expect=clean` block.
pub fn parse_suite(md: &str) -> Result<Vec<Block>, ParseError> {
    let mut blocks = Vec::new();
    let mut h1 = String::new();
    let mut h2 = String::new();
    let mut default_rule: Option<RuleId> = None;
    let mut snapshot = false;
    let mut lines = md.lines().enumerate();
    while let Some((i, line)) = lines.next() {
        let t = line.trim_start();
        let fence = ["```", "~~~"].into_iter().find(|f| t.starts_with(f));
        let Some(fence) = fence else {
            parse_outside(
                line,
                &mut h1,
                &mut h2,
                &mut default_rule,
                &mut snapshot,
                i + 1,
            )?;
            continue;
        };
        let ticks = t.chars().take_while(|c| fence.starts_with(*c)).count();
        let info = t[ticks..].trim();
        let mut body = String::new();
        let mut closed = false;
        for (_, l) in lines.by_ref() {
            let lt = l.trim_start();
            if lt.chars().take_while(|c| fence.starts_with(*c)).count() >= ticks
                && lt
                    .trim_start_matches(fence.chars().next().unwrap_or('`'))
                    .trim()
                    .is_empty()
            {
                closed = true;
                break;
            }
            body.push_str(l);
            body.push('\n');
        }
        let fence_line = i + 1;
        if !closed {
            return Err(ParseError {
                line: fence_line,
                message: "unterminated fence".into(),
            });
        }
        let toks = tokenize(info);
        let language = toks.first().cloned().unwrap_or_default();
        let opts: BTreeMap<&str, &str> = toks
            .iter()
            .skip(1)
            .filter_map(|t| t.split_once('='))
            .collect();
        // Blocks without `expect` are plain documentation, not cases.
        let Some(expect) = opts.get("expect") else {
            continue;
        };
        let err = |m: String| ParseError {
            line: fence_line,
            message: m,
        };
        let expect = match *expect {
            "fire" => Expect::Fire,
            "clean" => Expect::Clean,
            o => return Err(err(format!("expect must be fire or clean, got `{o}`"))),
        };
        let rule = match opts.get("rule") {
            Some(r) => r.parse::<RuleId>().map_err(|e| err(e.to_string()))?,
            None => default_rule
                .clone()
                .ok_or_else(|| err("no rule=ID and no suite default".into()))?,
        };
        let marks = markers(&body, fence_line)?;
        if expect == Expect::Clean && !marks.is_empty() {
            return Err(err("expect=clean block must not carry markers".into()));
        }
        let file_name = opts.get("file").map_or_else(
            || format!("case.{}", extension(&language)),
            |f| (*f).to_owned(),
        );
        let name = format!("{h1} / {h2} #{} (line {fence_line})", blocks.len() + 1);
        blocks.push(Block {
            name,
            fence_line,
            language,
            file_name,
            text: body,
            rule,
            expect,
            config: opts.get("config").map(|c| (*c).to_owned()),
            markers: marks,
            snapshot,
        });
    }
    Ok(blocks)
}

/// Handle a non-fence line: headings and the suite header comment.
fn parse_outside(
    line: &str,
    h1: &mut String,
    h2: &mut String,
    default_rule: &mut Option<RuleId>,
    snapshot: &mut bool,
    n: usize,
) -> Result<(), ParseError> {
    if let Some(h) = line.strip_prefix("## ") {
        h.trim().clone_into(h2);
    } else if let Some(h) = line.strip_prefix("# ") {
        h.trim().clone_into(h1);
        h2.clear();
    } else if line.trim() == "<!-- snapshot-diagnostics -->" {
        tracing::debug!(line = n, "snapshot-diagnostics header");
        *snapshot = true;
    } else if let Some(rest) = line
        .trim()
        .strip_prefix("<!-- mdtest:")
        .and_then(|r| r.strip_suffix("-->"))
    {
        for tok in rest.split_whitespace() {
            if tok == "snapshot-diagnostics" {
                tracing::debug!(line = n, "snapshot-diagnostics header");
                *snapshot = true;
            }
            if let Some(r) = tok.strip_prefix("rule=") {
                *default_rule =
                    Some(
                        r.parse()
                            .map_err(|e: gob_rules::ParseRuleIdError| ParseError {
                                line: n,
                                message: e.to_string(),
                            })?,
                    );
            }
        }
    }
    Ok(())
}
