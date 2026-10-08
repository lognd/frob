//! The `crunk:waive` comment: `crunk:waive RULE reason="why"`.
//!
//! The directive itself is registered with the shared directive scanner in `crunk-ingest`
//! (namespace `crunk`, verb `waive`); per D120 it adds no verb: it is an `accept` exception on one
//! rule at one place, so a waiver with a reason becomes an [`Exception`] of kind
//! [`ExceptionKind::Accept`] bound to the region it covers, and the pipeline's
//! [`apply_exceptions`](gob_rules::apply_exceptions) suppresses and counts it like every other
//! exception. A waiver without a reason suppresses nothing and is WAIVE001's finding.
//!
//! # Reading a comment
//!
//! A file rule sees text only (no path, no syntax tree), so [`scan`] reads comment openers
//! (`/*`, `//`, `#`, `<!--`) followed by `crunk:waive` and the argument grammar of the directive
//! DSL (a bare word, `key=value`, `key="quoted"` with `\"` and `\\` escapes). A malformed comment
//! is the directive scanner's PARSE001, not ours: [`scan`] skips it.
//!
//! # What a waiver covers
//!
//! The declaration its comment trails on the same line, else the next declaration after it (the
//! same attachment as the Python crunk's `_attach_waivers`): from the first code on that line up
//! to the first `;` (or the end of the line holding `}`).

// frob:ticket 01M43ATASM383KB9130JY79XVV

use std::ops::Range;

use gob_rules::{BoundException, Exception, ExceptionKind, RuleId};

use crate::family::is_waivable;

/// The verb text every waiver comment starts with.
const MARKER: &str = "crunk:waive";

/// Comment openers a waiver may follow (CSS and JS blocks, line comments, shell/TOML, HTML).
const OPENERS: [&str; 4] = ["/*", "//", "#", "<!--"];

/// Comment closers that end a waiver's arguments on its line.
const CLOSERS: [&str; 2] = ["*/", "-->"];

/// One `crunk:waive` comment as written.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WaiverComment {
    /// The waived rule id as written (not validated).
    pub rule: String,
    /// The `reason`, when given and not blank.
    pub reason: Option<String>,
    /// Byte offset of `crunk:waive` in the text.
    pub offset: usize,
    /// 1-based line of the comment.
    pub line: u32,
    /// The byte region the waiver covers; `None` when no declaration follows (an orphan).
    pub covers: Option<Range<usize>>,
}

/// Every well-formed `crunk:waive` comment of `text`, in source order.
pub fn scan(text: &str) -> Vec<WaiverComment> {
    let mut out = Vec::new();
    for (offset, _) in text.match_indices(MARKER) {
        let line_start = text[..offset].rfind('\n').map_or(0, |i| i + 1);
        let before = text[line_start..offset].trim_end();
        if !OPENERS.iter().any(|o| before.ends_with(o)) {
            continue;
        }
        let after = &text[offset + MARKER.len()..];
        if !after.starts_with(|c: char| c.is_whitespace()) {
            continue;
        }
        let line_end = after
            .find('\n')
            .map_or(text.len(), |i| offset + MARKER.len() + i);
        let tail = &text[offset + MARKER.len()..line_end];
        let tail = CLOSERS
            .iter()
            .filter_map(|c| tail.find(c))
            .min()
            .map_or(tail, |i| &tail[..i]);
        let Some((rule, reason)) = parse_args(tail) else {
            tracing::debug!(offset, "malformed crunk:waive skipped (PARSE001's finding)");
            continue;
        };
        let line = u32::try_from(text[..offset].matches('\n').count() + 1).unwrap_or(u32::MAX);
        let covers = covered_region(text, line_start, offset, line_end);
        tracing::trace!(%rule, has_reason = reason.is_some(), line, "waiver comment read");
        out.push(WaiverComment {
            rule,
            reason,
            offset,
            line,
            covers,
        });
    }
    out
}

/// The rule (first bare word) and non-blank `reason` of a waiver's argument tail; `None` when the
/// rule is missing or a quote never closes.
fn parse_args(tail: &str) -> Option<(String, Option<String>)> {
    let mut rule = None;
    let mut reason = None;
    let mut rest = tail.trim_start();
    while !rest.is_empty() {
        let word_end = rest
            .find(|c: char| c.is_whitespace() || c == '=')
            .unwrap_or(rest.len());
        let word = &rest[..word_end];
        rest = &rest[word_end..];
        if let Some(value_text) = rest.strip_prefix('=') {
            let (value, remaining) = if let Some(quoted) = value_text.strip_prefix('"') {
                unquote(quoted)?
            } else {
                let end = value_text
                    .find(char::is_whitespace)
                    .unwrap_or(value_text.len());
                (value_text[..end].to_owned(), &value_text[end..])
            };
            if word == "reason" && reason.is_none() {
                reason = Some(value);
            }
            rest = remaining;
        } else if rule.is_none() && !word.is_empty() {
            rule = Some(word.to_owned());
        }
        rest = rest.trim_start();
    }
    let reason = reason.filter(|r| !r.trim().is_empty());
    rule.map(|r| (r, reason))
}

/// The unescaped text up to the closing quote, and what follows it.
fn unquote(after_open: &str) -> Option<(String, &str)> {
    let mut value = String::new();
    let mut chars = after_open.char_indices();
    while let Some((i, c)) = chars.next() {
        match c {
            '"' => return Some((value, &after_open[i + 1..])),
            '\\' => match chars.next() {
                Some((_, e @ ('"' | '\\'))) => value.push(e),
                Some((_, other)) => {
                    value.push('\\');
                    value.push(other);
                }
                None => return None,
            },
            other => value.push(other),
        }
    }
    None
}

/// The region a waiver at `offset` covers: its own line when code precedes the comment there,
/// else from the next line carrying code to the first `;` (or the end of that line). `None` when
/// nothing follows.
fn covered_region(
    text: &str,
    line_start: usize,
    offset: usize,
    line_end: usize,
) -> Option<Range<usize>> {
    if code_before_opener(&text[line_start..offset]) {
        return Some(line_start..line_end);
    }
    let mut pos = line_end + 1;
    while pos < text.len() {
        let end = text[pos..].find('\n').map_or(text.len(), |i| pos + i);
        let trimmed = text[pos..end].trim();
        if !trimmed.is_empty() && !is_comment_only(trimmed) {
            let stop = text[pos..].find(';').map_or(end, |i| pos + i + 1);
            return Some(pos..stop);
        }
        pos = end + 1;
    }
    None
}

/// True when anything but whitespace precedes the comment opener on its line.
fn code_before_opener(before: &str) -> bool {
    let cut = OPENERS
        .iter()
        .filter_map(|o| before.rfind(o))
        .max()
        .unwrap_or(0);
    !before[..cut].trim().is_empty()
}

fn is_comment_only(trimmed: &str) -> bool {
    OPENERS.iter().any(|o| trimmed.starts_with(o)) || trimmed.starts_with('*')
}

/// The exceptions a file's waivers grant: one `accept` per waiver that has a reason, names a
/// waivable rule and covers a declaration. Waivers without a reason grant nothing (WAIVE001).
pub fn exceptions(path: &str, text: &str) -> Vec<BoundException> {
    scan(text)
        .into_iter()
        .filter_map(|w| {
            let reason = w.reason?;
            let range = w.covers?;
            let rule: RuleId = w.rule.parse().ok()?;
            if !is_waivable(rule.as_str()) {
                tracing::debug!(%rule, path, line = w.line, "waiver names a non-waivable rule; ignored");
                return None;
            }
            Some(BoundException {
                exception: Exception {
                    kind: ExceptionKind::Accept,
                    rule,
                    reason,
                    ticket: None,
                    until: None,
                },
                path: path.to_owned(),
                range: Some(range),
            })
        })
        .collect()
}
