//! Table-row id anchors of a markdown document (grmb-spec 4.5.1 rule 3).

// frob:ticket 01M4FGZ39WXWBRDRHW2ADSY7K8

use std::collections::HashMap;

use gob_symbols::slugify;

/// The unit kind a table-row anchor reports.
pub const ROW_KIND: &str = "table-row";

/// The anchors of the table-row ids of `text`, in document order.
///
/// `taken` holds the anchors already in use (heading slugs); a repeated slug gets `-1`, `-2`
/// like a heading's, while an explicit `{#ID}` is taken verbatim.
#[must_use]
pub fn row_anchors(text: &str, taken: &[String]) -> Vec<String> {
    let mut used: HashMap<String, usize> = taken.iter().map(|t| (t.clone(), 1)).collect();
    let mut out = Vec::new();
    let mut fence: Option<&str> = None;
    let mut prev: Option<&str> = None;
    let mut in_body = false;
    for line in text.lines() {
        let t = line.trim_start();
        if let Some(open) = fence {
            if t.starts_with(open) {
                fence = None;
            }
            continue;
        }
        if let Some(mark) = ["```", "~~~"].into_iter().find(|m| t.starts_with(m)) {
            fence = Some(mark);
            in_body = false;
            prev = None;
            continue;
        }
        if in_body {
            if t.contains('|') {
                if let Some(a) = first_cell_anchor(t, &mut used) {
                    out.push(a);
                }
                continue;
            }
            in_body = false;
        } else if prev.is_some_and(|p| p.contains('|')) && is_separator(t) {
            in_body = true;
            continue;
        }
        prev = Some(t);
    }
    tracing::debug!(rows = out.len(), "table-row anchors scanned");
    out
}

fn cells(line: &str) -> Vec<&str> {
    let body = line.trim();
    let body = body.strip_prefix('|').unwrap_or(body);
    let body = body.strip_suffix('|').unwrap_or(body);
    body.split('|').map(str::trim).collect()
}

fn is_separator(line: &str) -> bool {
    line.contains('-')
        && cells(line).iter().all(|c| {
            let c = c.trim_matches(':');
            !c.is_empty() && c.chars().all(|ch| ch == '-')
        })
}

fn first_cell_anchor(line: &str, used: &mut HashMap<String, usize>) -> Option<String> {
    let first = *cells(line).first()?;
    if let Some(at) = first.rfind("{#")
        && first.ends_with('}')
    {
        let id = &first[at + 2..first.len() - 1];
        let valid = !id.is_empty()
            && id
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_');
        return valid.then(|| id.to_owned());
    }
    let token = first
        .strip_prefix('`')
        .and_then(|r| r.strip_suffix('`'))
        .unwrap_or(first);
    if token.is_empty() || token.contains(char::is_whitespace) || token.contains('`') {
        return None;
    }
    let base = slugify(token);
    if base.is_empty() {
        return None;
    }
    let n = used.entry(base.clone()).or_default();
    let slug = if *n == 0 {
        base.clone()
    } else {
        format!("{base}-{n}")
    };
    *n += 1;
    if slug != base {
        used.entry(slug.clone()).or_insert(1);
    }
    Some(slug)
}
