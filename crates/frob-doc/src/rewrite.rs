//! Rewriting the references in one file: links, directives, `.grmb` refs and prose citations.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use std::ops::Range;

use gob_languages::{
    Language, ParseLimits, ParseResult, markdown_link_destinations, parse, parse_comment_spans,
};
use gob_symbols::{DocStatus, is_generated, parse_header};
use gob_text::{Citation, Locator, scan_line, scan_markdown};

use crate::edit::{Edit, apply};
use crate::moved::{MOVED_PATH, MovedError, MovedMap, Resolved};

/// Path components under which files hold fixed samples, never live references.
const SKIPPED_DIRS: &[&str] = &["corpus", "fixtures", "testdata", "snapshots"];
/// Directive words whose token names a doc place.
const DIRECTIVES: &[&str] = &["frob:describes", "frob:doc"];

/// True when `path` (repo-relative) may be rewritten: under `crates/` or `docs/`, never the map itself,
/// `tickets/`, `notes/` or sample directories.
#[must_use]
pub fn in_scope(path: &str) -> bool {
    let path = path.trim_start_matches("./");
    if path == MOVED_PATH || path.starts_with("tickets/") || path.starts_with("notes/") {
        return false;
    }
    if !(path.starts_with("crates/") || path.starts_with("docs/")) {
        return false;
    }
    !path.split('/').any(|c| SKIPPED_DIRS.contains(&c))
}

/// `base/rel` with `.` and `..` folded away; `None` when `..` climbs out of the root.
fn normalize(base: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = Vec::new();
    for seg in base.split('/').chain(rel.split('/')) {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// The path of `target` as seen from directory `dir` (both repo-relative, forward slashes).
fn relative(dir: &str, target: &str) -> String {
    let d: Vec<&str> = dir.split('/').filter(|s| !s.is_empty()).collect();
    let t: Vec<&str> = target.split('/').filter(|s| !s.is_empty()).collect();
    let common = d.iter().zip(&t).take_while(|(a, b)| a == b).count();
    let mut out: Vec<&str> = vec![".."; d.len() - common];
    out.extend(&t[common..]);
    out.join("/")
}

/// The directory part of a repo-relative file path.
fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// The edit for a markdown link destination `dest` at `range`, when the map moves its target.
fn link_edit(
    path: &str,
    dest: &str,
    range: Range<usize>,
    map: &MovedMap,
) -> Result<Option<Edit>, MovedError> {
    if dest.is_empty()
        || dest.starts_with('#')
        || dest.contains("://")
        || dest.starts_with("mailto:")
    {
        return Ok(None);
    }
    let (file, anchor) = match dest.split_once('#') {
        Some((f, a)) => (f, Some(a)),
        None => (dest, None),
    };
    let rooted = file.starts_with('/');
    let dir = dir_of(path);
    let norm = if rooted {
        normalize("", file)
    } else {
        normalize(dir, file)
    };
    let Some(norm) = norm else { return Ok(None) };
    let loc = anchor.map(|a| Locator::Anchor(a.to_owned()));
    let Resolved::Moved(to) = map.resolve(&norm, loc.as_ref(), true)? else {
        return Ok(None);
    };
    let mut text = if rooted {
        format!("/{}", to.file)
    } else {
        relative(dir, &to.file)
    };
    if let Some(Locator::Anchor(a)) = &to.locator {
        text.push('#');
        text.push_str(a);
    }
    tracing::debug!(path, from = dest, to = %text, "link rewritten");
    Ok(Some(Edit {
        start: range.start,
        len: range.len(),
        text,
    }))
}

/// The edit for a `file`, `file#anchor` or `file::symbol` token at `start`, when the map moves its file.
fn token_edit(token: &str, start: usize, map: &MovedMap) -> Result<Option<Edit>, MovedError> {
    let cut = token
        .find('#')
        .into_iter()
        .chain(token.find("::"))
        .min()
        .unwrap_or(token.len());
    let (file, suffix) = token.split_at(cut);
    let anchor = suffix.strip_prefix('#');
    let loc = anchor.map(|a| Locator::Anchor(a.to_owned()));
    let Resolved::Moved(to) = map.resolve(file, loc.as_ref(), true)? else {
        return Ok(None);
    };
    let tail = match (&to.locator, anchor) {
        (Some(Locator::Anchor(a)), Some(_)) => format!("#{a}"),
        _ => suffix.to_owned(),
    };
    Ok(Some(Edit {
        start,
        len: token.len(),
        text: format!("{}{tail}", to.file),
    }))
}

/// Directive tokens (`frob:doc X`, `frob:describes X`) in `text`: `(offset, token)`.
fn directive_tokens(text: &str) -> Vec<(usize, &str)> {
    let mut out = Vec::new();
    for word in DIRECTIVES {
        for (i, _) in text.match_indices(word) {
            let after = &text[i + word.len()..];
            if !after.starts_with(char::is_whitespace) {
                continue;
            }
            let ws = after.len() - after.trim_start().len();
            let rest = &after[ws..];
            let len = rest.find(char::is_whitespace).unwrap_or(rest.len());
            if len > 0 {
                out.push((i + word.len() + ws, &rest[..len]));
            }
        }
    }
    out
}

/// Quoted `ref "..."` strings of a `.grmb` text outside comments: `(offset, content)`.
fn grmb_refs<'a>(text: &'a str, comments: &[Range<usize>]) -> Vec<(usize, &'a str)> {
    let mut out = Vec::new();
    for (i, _) in text.match_indices("ref") {
        let before_ok = text[..i]
            .chars()
            .next_back()
            .is_none_or(|c| !(c.is_alphanumeric() || c == '_'));
        let after = &text[i + 3..];
        if !before_ok || !after.starts_with(char::is_whitespace) {
            continue;
        }
        if comments.iter().any(|c| c.contains(&i)) {
            continue;
        }
        let ws = after.len() - after.trim_start().len();
        let Some(body) = after[ws..].strip_prefix('"') else {
            continue;
        };
        if let Some(end) = body.find('"') {
            out.push((i + 3 + ws + 1, &body[..end]));
        }
    }
    out
}

/// Citation edits for prose `line` at `base`, skipping those overlapping `skip` ranges.
fn citation_edits(
    cites: &[Citation],
    skip: &[Range<usize>],
    map: &MovedMap,
    out: &mut Vec<Edit>,
) -> Result<(), MovedError> {
    for c in cites {
        let span = c.start..c.start + c.len;
        if skip
            .iter()
            .any(|s| s.start < span.end && span.start < s.end)
        {
            continue;
        }
        if let Resolved::Moved(to) = map.resolve(&c.file, Some(&c.locator), false)? {
            let Some(locator) = to.locator else { continue };
            let new = Citation {
                file: to.file,
                locator,
                start: c.start,
                len: c.len,
            };
            out.push(Edit {
                start: c.start,
                len: c.len,
                text: new.quoted(),
            });
        }
    }
    Ok(())
}

/// Rewrite the old places `text` (the file at repo-relative `path`) refers to; `None` when nothing changes.
///
/// Generated files and historical or superseded markdown are left alone.
///
/// # Errors
/// [`MovedError::Cycle`] when a reference's rows never settle.
pub fn remap_text(path: &str, text: &str, map: &MovedMap) -> Result<Option<String>, MovedError> {
    if is_generated(text) {
        return Ok(None);
    }
    let Some(lang) = Language::detect(path) else {
        return Ok(None);
    };
    let mut edits = Vec::new();
    let comments = parse_comment_spans(lang, text);
    if lang == Language::Markdown {
        if matches!(
            parse_header(text).status,
            Ok(DocStatus::Historical | DocStatus::SupersededBy(_))
        ) {
            return Ok(None);
        }
        let mut dests = Vec::new();
        if let ParseResult::Parsed(tree) = parse(lang, text, &ParseLimits::default()) {
            dests = markdown_link_destinations(&tree);
        }
        for r in &dests {
            edits.extend(link_edit(path, &text[r.clone()], r.clone(), map)?);
        }
        citation_edits(&scan_markdown(text), &dests, map, &mut edits)?;
    } else {
        let mut cites = Vec::new();
        for span in &comments {
            let mut pos = span.start;
            for raw in text[span.clone()].split_inclusive('\n') {
                scan_line(raw.trim_end_matches(['\n', '\r']), pos, &mut cites);
                pos += raw.len();
            }
        }
        citation_edits(&cites, &[], map, &mut edits)?;
    }
    for span in &comments {
        for (off, token) in directive_tokens(&text[span.clone()]) {
            edits.extend(token_edit(token, span.start + off, map)?);
        }
    }
    if lang == Language::Grmb {
        for (off, token) in grmb_refs(text, &comments) {
            edits.extend(token_edit(token, off, map)?);
        }
    }
    let (applied, out) = apply(text, edits);
    tracing::debug!(path, applied, "file remapped");
    Ok((applied > 0).then_some(out))
}
