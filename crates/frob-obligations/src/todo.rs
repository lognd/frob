//! TODO001 (bare work markers) and TODO002 (markers owned by terminal tickets).

use gob_directives::frob::Todo;
use gob_directives::{Directive, DirectiveRecord, is_full_ulid};
use gob_languages::Language;
use gob_rules::Finding;
use gob_text::{FileId, LineIndex, Span, TextRange, TextSize};

use crate::comments::comment_lines;
use crate::rules::{Todo001, Todo002};
use crate::tickets::{Standing, Tickets};
use crate::util::{finding, is_marker};

/// 1-based line of byte `offset`, or 0 when it cannot be computed.
fn line_of(index: &LineIndex, offset: usize) -> u32 {
    u32::try_from(offset)
        .ok()
        .and_then(|o| index.line_col(TextSize::new(o)))
        .map_or(0, |lc| lc.line)
}

/// The byte range of `[start, start+len)` as a [`TextRange`], clamped to `u32`.
pub(crate) fn range(start: usize, len: usize) -> TextRange {
    let clamp = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
    TextRange::new(clamp(start), clamp(start + len))
}

/// The first marker word of `line` that is not owned by an inline `(ULID)`.
fn bare_marker(line: &str) -> Option<(usize, &str)> {
    let mut word_start: Option<usize> = None;
    let bytes = line.as_bytes();
    for i in 0..=bytes.len() {
        let in_word = bytes
            .get(i)
            .is_some_and(|b| b.is_ascii_alphanumeric() || *b == b'_');
        match (word_start, in_word) {
            (None, true) => word_start = Some(i),
            (Some(s), false) => {
                word_start = None;
                let w = &line[s..i];
                if is_marker(w) && !inline_owner(&line[i..]) {
                    return Some((s, w));
                }
            }
            _ => {}
        }
    }
    None
}

/// True when `rest` starts with `(<full ULID>)`.
fn inline_owner(rest: &str) -> bool {
    rest.strip_prefix('(')
        .and_then(|r| r.split_once(')'))
        .is_some_and(|(id, _)| is_full_ulid(id.trim()))
}

/// TODO001 over one file: bare markers without a `frob:todo` on the same or previous line.
pub(crate) fn todo001(
    file: FileId,
    path: &str,
    text: &str,
    directives: &[&DirectiveRecord],
) -> Vec<Finding> {
    let Some(language) = Language::detect(path) else {
        return Vec::new();
    };
    let Ok(index) = LineIndex::new(text) else {
        tracing::warn!(path, "file too large for TODO001");
        return Vec::new();
    };
    let owner_lines: Vec<u32> = directives
        .iter()
        .filter(|d| d.verb == "todo" && Todo::parse_args(&d.args).is_ok())
        .map(|d| {
            line_of(
                &index,
                usize::try_from(u32::from(d.span.range.start())).unwrap_or(0),
            )
        })
        .collect();
    let mut out = Vec::new();
    for cl in comment_lines(language, text) {
        let Some((at, word)) = bare_marker(cl.text) else {
            continue;
        };
        let start = cl.offset + at;
        let line = line_of(&index, start);
        if owner_lines.iter().any(|&l| l == line || l + 1 == line) {
            continue;
        }
        tracing::debug!(path, line, word, "bare work marker");
        out.push(finding(
            &Todo001,
            Some(Span::new(file, range(start, word.len()))),
            format!(
                "bare `{word}` in a comment; own it with a `frob:todo <ulid>` directive on this or the previous line"
            ),
            path,
        ));
    }
    out
}

/// TODO002 over the whole repo: `frob:todo` directives whose ticket is terminal.
pub(crate) fn todo002(directives: &[DirectiveRecord], tickets: &Tickets<'_>) -> Vec<Finding> {
    let mut out = Vec::new();
    for d in directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "todo")
    {
        let Ok(todo) = Todo::parse_args(&d.args) else {
            continue;
        };
        if let Standing::Terminal(outcome) = tickets.standing(&todo.id) {
            out.push(finding(
                &Todo002,
                Some(d.span),
                format!(
                    "`frob:todo {}` points at a ticket that is already done ({outcome}); do the work, remove the marker or re-point it",
                    todo.id
                ),
                &todo.id,
            ));
        }
    }
    out
}
