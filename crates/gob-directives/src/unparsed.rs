//! Lexical directive scan for files whose extension has no registered grammar.

use std::borrow::Cow;

use gob_rules::{Finding, RuleId, RuleMeta};
use gob_symbols::FileSymbols;
use gob_text::{FileId, LineIndex, Span};

use crate::comments::Segment;
use crate::legacy;
use crate::lex::range_at;
use crate::rules::{Parse001, Parse002};
use crate::scan::{Ctx, ScanResult, Scanner};

/// Comment leaders recognised in a file with no grammar; a known set, never guessed.
pub const LEXICAL_LEADERS: [&str; 5] = ["#", "//", ";", "--", "%"];

/// Verbs of the retired v1 DSL that are no longer registered; still named when not honourable.
const V1_VERBS: [&str; 2] = ["waive", "debt"];

/// A comment-closing token trimmed from the tail of a lexical segment.
const BLOCK_CLOSER: &str = "-->";

/// The in-text marker every lexically derived finding and honoured directive carries.
pub fn lexical_marker(path: &str) -> String {
    let name = path.rsplit('/').next().unwrap_or(path);
    let ext = match name.rsplit_once('.') {
        Some((stem, e)) if !stem.is_empty() && !e.is_empty() => format!(".{e}"),
        _ => "no extension".to_owned(),
    };
    format!("matched lexically (no grammar for {ext}; text scan, not parsed)")
}

fn finding(meta: &RuleMeta, span: Span, message: String, anchor: &str) -> Finding {
    let id: RuleId = meta
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("derive validated rule id {}: {e}", meta.id));
    Finding::new(id, meta.severity, Some(span), message, anchor)
}

/// True when the text before a namespace ends in a recognised comment leader.
fn has_leader(before: &str) -> bool {
    LEXICAL_LEADERS.iter().any(|l| before.ends_with(l))
}

/// True when text before `frob:` could be a foreign comment opener rather than prose or data.
fn looks_like_foreign_comment(before: &str) -> bool {
    before
        .chars()
        .last()
        .is_none_or(|c| !c.is_alphanumeric() && !matches!(c, '"' | '\'' | '`'))
}

impl Scanner {
    // frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
    /// Scan `text` of a file with no grammar by text, honouring `frob:` directives behind a known comment leader.
    ///
    /// There is no token stream to ask which text is a comment, and the namespace is a fixed
    /// literal prefix (`frob:`) that must follow a comment leader (`#`, `//`, `;`, `--`, `%`),
    /// so a line scan is sound here and used ONLY here: parsed languages go through
    /// [`Scanner::scan_in`]. Every finding carries the lexical marker; a directive behind an
    /// unrecognised comment syntax is reported (PARSE001), never dropped silently.
    pub fn scan_unparsed_in(&self, file: FileId, text: &str, symbols: &FileSymbols) -> ScanResult {
        let mut result = ScanResult::default();
        let Ok(index) = LineIndex::new(text) else {
            tracing::warn!(path = %symbols.path, "file too large to scan for directives");
            return result;
        };
        let ctx = Ctx {
            file,
            language: None,
            text,
            index: &index,
            symbols,
        };
        let marker = lexical_marker(&symbols.path);
        let mut line_start = 0usize;
        for line in text.split_inclusive('\n') {
            self.scan_line(&ctx, line, line_start, &marker, &mut result);
            line_start += line.len();
        }
        for f in &mut result.findings {
            f.message = format!("{} [{marker}]", f.message);
        }
        let honoured: Vec<Finding> = result
            .directives
            .iter()
            .map(|d| {
                finding(
                    &Parse002::META,
                    d.span,
                    format!(
                        "`{}:{}` {marker}: directive honoured, but this file stays unparsed and invisible to structural gates",
                        d.namespace, d.verb
                    ),
                    &symbols.path,
                )
            })
            .collect();
        result.findings.extend(honoured);
        tracing::debug!(
            path = %symbols.path,
            directives = result.directives.len(),
            findings = result.findings.len(),
            "lexical directive scan done"
        );
        result
    }

    /// Find each `<namespace>:` in one line and honour or report it.
    fn scan_line(
        &self,
        ctx: &Ctx<'_>,
        line: &str,
        line_start: usize,
        marker: &str,
        out: &mut ScanResult,
    ) {
        for ns in self.namespaces() {
            let needle = format!("{ns}:");
            let mut from = 0usize;
            while let Some(rel) = line[from..].find(&needle) {
                let pos = from + rel;
                from = pos + needle.len();
                let before = line[..pos].trim_end();
                let word_before = line[..pos]
                    .chars()
                    .last()
                    .is_some_and(|c| c.is_alphanumeric() || c == '_');
                if word_before {
                    continue;
                }
                let tail = line[pos..].trim_end();
                let tail = tail.strip_suffix(BLOCK_CLOSER).unwrap_or(tail).trim_end();
                let after = &tail[needle.len()..];
                let verb = after.split(char::is_whitespace).next().unwrap_or("");
                if has_leader(before) {
                    tracing::debug!(path = %ctx.symbols.path, %ns, verb, "lexical directive");
                    let seg = Segment {
                        offset: line_start + pos,
                        text: Cow::Borrowed(tail),
                        inner_doc: false,
                    };
                    self.handle(ctx, &seg, out);
                } else if looks_like_foreign_comment(before)
                    && (self.knows(ns, verb)
                        || legacy::lookup(ns, verb).is_some()
                        || V1_VERBS.contains(&verb))
                {
                    tracing::warn!(path = %ctx.symbols.path, %ns, verb, "directive behind unrecognised comment syntax");
                    let span = ctx.span(range_at(line_start + pos, 0, tail.len()));
                    out.findings.push(finding(
                        &Parse001::META,
                        span,
                        format!(
                            "`{ns}:{verb}` not honoured: no grammar for this file and its comment syntax is not one of {}; {marker}",
                            LEXICAL_LEADERS.join(" ")
                        ),
                        &ctx.symbols.path,
                    ));
                }
            }
        }
    }
}
