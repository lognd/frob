//! The status header of a document under `docs/`: one fixed vocabulary, read the same way by the
//! DOC003 rule and by the generated documentation index.

// frob:ticket 01M4H0RKJHHWWT0XC17W5JD1VG

/// The marker that opens a generated page (the first line), instead of a header block.
const GENERATED_MARK: &str = "<!-- GENERATED";
/// The key of the status line.
const STATUS_KEY: &str = "Status";
/// The key of the owner line.
const OWNER_KEY: &str = "Owner";
/// The words that open a `superseded-by` status.
const SUPERSEDED: &str = "superseded-by";

/// A document status from the fixed vocabulary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DocStatus {
    /// Decided and, where it names code, built.
    Current,
    /// Decided or proposed but not (fully) built, or still under review.
    Draft,
    /// Kept as a record; nothing new is built from it.
    Historical,
    /// Written by a generator; carries a marker instead of a header block.
    Generated,
    /// Replaced by the named document.
    SupersededBy(String),
}

/// Why a document has no valid status.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StatusProblem {
    /// No `Status:` line in the header block.
    Missing,
    /// A status outside the vocabulary (the text as written).
    Unknown(String),
    /// `superseded-by` with nothing after it.
    NoTarget,
}

/// What the header block of one document says.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocHeader {
    /// The text of the first `# ` title, when there is one.
    pub title: Option<String>,
    /// The parsed status, or why there is none.
    pub status: Result<DocStatus, StatusProblem>,
    /// The 1-based line the status sits on, or 1 when there is no status line.
    pub status_line: u32,
    /// The `Owner:` value, when present.
    pub owner: Option<String>,
}

/// True when `text` opens with the generator marker, so it needs no header block.
#[must_use]
pub fn is_generated(text: &str) -> bool {
    text.trim_start().starts_with(GENERATED_MARK)
}

/// The `Key: value` pair on `line`, when it is one (a capitalised word, a colon, a value).
fn pair(line: &str) -> Option<(&str, &str)> {
    let (key, value) = line.split_once(':')?;
    let mut chars = key.chars();
    let first = chars.next()?;
    // A trailing HTML comment (an mdtest marker, say) is not part of the value.
    let value = value.split("<!--").next().unwrap_or(value).trim();
    (first.is_ascii_uppercase() && chars.all(|c| c.is_ascii_alphabetic())).then_some((key, value))
}

/// Parse the status text of a `Status:` line.
fn parse_status(value: &str) -> Result<DocStatus, StatusProblem> {
    match value {
        "current" => Ok(DocStatus::Current),
        "draft" => Ok(DocStatus::Draft),
        "historical" => Ok(DocStatus::Historical),
        "generated" => Ok(DocStatus::Generated),
        other => match other.strip_prefix(SUPERSEDED) {
            Some(rest) if rest.starts_with(' ') => {
                let target = rest.trim().trim_matches('`').trim();
                if target.is_empty() {
                    Err(StatusProblem::NoTarget)
                } else {
                    Ok(DocStatus::SupersededBy(target.to_owned()))
                }
            }
            Some("") => Err(StatusProblem::NoTarget),
            _ => Err(StatusProblem::Unknown(other.to_owned())),
        },
    }
}

/// Read the header block of `text`: the `Key: value` lines right after the first `# ` title.
///
/// Only that block is read, so a `Status:` sentence further down the page is never mistaken for a
/// header. A generated page reports [`DocStatus::Generated`].
#[must_use]
pub fn parse_header(text: &str) -> DocHeader {
    let generated = is_generated(text);
    let mut title = None;
    let mut status = None;
    let mut owner = None;
    let mut status_line = 1;
    let mut in_block = false;
    let mut seen_pair = false;
    for (index, line) in text.lines().enumerate() {
        if title.is_none() {
            if let Some(t) = line.strip_prefix("# ") {
                title = Some(t.trim().to_owned());
                in_block = true;
            }
            continue;
        }
        if !in_block {
            break;
        }
        if line.trim().is_empty() {
            if seen_pair {
                break;
            }
            continue;
        }
        let Some((key, value)) = pair(line) else {
            break;
        };
        seen_pair = true;
        if key == STATUS_KEY {
            status = Some(parse_status(value));
            status_line = u32::try_from(index + 1).unwrap_or(1);
        } else if key == OWNER_KEY {
            owner = Some(value.to_owned());
        }
    }
    let status = match status {
        _ if generated => Ok(DocStatus::Generated),
        Some(parsed) => parsed,
        None => Err(StatusProblem::Missing),
    };
    DocHeader {
        title,
        status,
        status_line,
        owner,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests parse_header
    #[test]
    fn reads_each_status_in_the_vocabulary() {
        for (word, want) in [
            ("current", DocStatus::Current),
            ("draft", DocStatus::Draft),
            ("historical", DocStatus::Historical),
            (
                "superseded-by `x.md`",
                DocStatus::SupersededBy("x.md".to_owned()),
            ),
        ] {
            let h = parse_header(&format!("# T\n\nStatus: {word}\nOwner: frob\n"));
            assert_eq!(h.status, Ok(want));
            assert_eq!(h.owner.as_deref(), Some("frob"));
            assert_eq!(h.status_line, 3);
        }
    }

    // frob:tests parse_header
    #[test]
    fn rejects_missing_unknown_and_targetless_statuses() {
        assert_eq!(
            parse_header("# T\n\nbody\n").status,
            Err(StatusProblem::Missing)
        );
        assert_eq!(
            parse_header("# T\n\nStatus: DRAFT\n").status,
            Err(StatusProblem::Unknown("DRAFT".to_owned()))
        );
        assert_eq!(
            parse_header("# T\n\nStatus: superseded-by\n").status,
            Err(StatusProblem::NoTarget)
        );
    }

    // frob:tests parse_header
    #[test]
    fn ignores_status_prose_below_the_header_block() {
        let h = parse_header("# T\n\nOwner: frob\n\nStatus: current is a word here\n");
        assert_eq!(h.status, Err(StatusProblem::Missing));
    }

    // frob:tests parse_header
    #[test]
    fn generated_pages_need_no_header() {
        let h = parse_header("<!-- GENERATED by frob v1: DO NOT EDIT. -->\n# T\n");
        assert_eq!(h.status, Ok(DocStatus::Generated));
    }
}
