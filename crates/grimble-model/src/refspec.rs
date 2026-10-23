//! The spelling of a vmodel `ref` (grmb-spec 4.5.1): `PATH#ANCHOR`, `PATH::ANCHOR` or a code symref.

// frob:ticket 01M4FGZ39WXWBRDRHW2ADSY7K8

/// Why `text` is not a well-formed vmodel `ref`, with the spelling to use instead; `None` when it is well-formed.
///
/// Malformed: a `:` in the path part (the v1 `path:ANCHOR` spelling, or a drive path such as
/// `C:/x`), an empty path, an empty anchor, more than one `#`, or an anchor holding
/// whitespace, `{` or `}`.
#[must_use]
pub fn malformed_ref(text: &str) -> Option<String> {
    let cut = text.find(['#', ':']).unwrap_or(text.len());
    let (path, rest) = text.split_at(cut);
    if path.is_empty() {
        return Some(format!(
            "malformed ref `{text}`: it names no file; write `PATH#ANCHOR` or `PATH::ANCHOR`"
        ));
    }
    if let Some(after) = rest.strip_prefix(':')
        && !after.starts_with(':')
    {
        return Some(single_colon(text, path, after));
    }
    if let Some(anchor) = rest.strip_prefix('#') {
        return malformed_anchor(text, anchor);
    }
    None
}

fn single_colon(text: &str, path: &str, after: &str) -> String {
    let drive = path.len() == 1 && (after.starts_with('/') || after.starts_with('\\'));
    if drive {
        format!(
            "malformed ref `{text}`: a drive path is not a repository-relative path; write `PATH#ANCHOR`"
        )
    } else if after.is_empty() {
        format!("malformed ref `{text}`: `:` needs an anchor; write `{path}#ANCHOR`")
    } else {
        format!("malformed ref `{text}`: a single `:` is the v1 spelling; write `{path}#{after}`")
    }
}

fn malformed_anchor(text: &str, anchor: &str) -> Option<String> {
    let why = if anchor.is_empty() {
        "the anchor after `#` is empty"
    } else if anchor.contains('#') {
        "it holds more than one `#`"
    } else if anchor.contains(char::is_whitespace) || anchor.contains(['{', '}']) {
        "an anchor holds no whitespace, `{` or `}`"
    } else {
        return None;
    };
    Some(format!(
        "malformed ref `{text}`: {why}; write `PATH#ANCHOR` with a heading slug, `{{#id}}` or table-row id"
    ))
}
