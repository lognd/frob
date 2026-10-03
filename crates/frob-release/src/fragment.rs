//! Reading and validating `changelog.d/<ulid>.<type>.md` fragments.

use std::fs;
use std::path::Path;

use crate::error::FragmentError;

/// Products a fragment may name, in rendering order; unprefixed fragments belong to the first.
pub const PRODUCTS: [&str; 4] = ["frob", "gob", "grimble", "crunk"];

/// Fragment type, declared in rendering order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Kind {
    /// New capability.
    Added,
    /// Changed behaviour.
    Changed,
    /// Bug fix.
    Fixed,
    /// Removed capability.
    Removed,
    /// Will be removed later.
    Deprecated,
    /// Security fix.
    Security,
}

impl Kind {
    /// Every type in rendering order.
    pub const ALL: [Kind; 6] = [
        Kind::Added,
        Kind::Changed,
        Kind::Fixed,
        Kind::Removed,
        Kind::Deprecated,
        Kind::Security,
    ];

    /// The lowercase file-name segment.
    pub fn as_str(self) -> &'static str {
        match self {
            Kind::Added => "added",
            Kind::Changed => "changed",
            Kind::Fixed => "fixed",
            Kind::Removed => "removed",
            Kind::Deprecated => "deprecated",
            Kind::Security => "security",
        }
    }

    /// The section heading, e.g. `Added`.
    pub fn title(self) -> &'static str {
        match self {
            Kind::Added => "Added",
            Kind::Changed => "Changed",
            Kind::Fixed => "Fixed",
            Kind::Removed => "Removed",
            Kind::Deprecated => "Deprecated",
            Kind::Security => "Security",
        }
    }

    /// Parse a file-name segment.
    pub fn parse(s: &str) -> Option<Kind> {
        Kind::ALL.into_iter().find(|k| k.as_str() == s)
    }

    /// Comma-separated valid segments, for error messages.
    pub fn valid_list() -> String {
        Kind::ALL.map(Kind::as_str).join(", ")
    }
}

/// A validated fragment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fragment {
    /// File name inside changelog.d.
    pub file: String,
    /// The ticket ULID (upper case).
    pub ulid: String,
    /// The ticket handle the resolver returned, with `~`.
    pub handle: String,
    /// Fragment type.
    pub kind: Kind,
    /// Product the entry belongs to (one of [`PRODUCTS`]).
    pub product: &'static str,
    /// The entry text as one line.
    pub text: String,
}

/// Maps a ticket ULID to its display handle; `None` when the ledger has no such ticket.
pub trait TicketResolver {
    /// The `~HANDLE` of the ticket, or `None` when it does not exist.
    fn handle(&self, ulid: &str) -> Option<String>;
}

impl<F: Fn(&str) -> Option<String>> TicketResolver for F {
    fn handle(&self, ulid: &str) -> Option<String> {
        self(ulid)
    }
}

/// Split a body into its product and one-line text.
///
/// A leading `word:` naming a product is the prefix. A word within edit distance 2 of a
/// product (but not equal) is a probable typo and is refused with a did-you-mean; any other
/// word and colon (for example `Note:`) is ordinary text and files under the first product.
fn split_product(file: &str, body: &str) -> Result<(&'static str, String), FragmentError> {
    let first = body.trim_start();
    if let Some((head, rest)) = first.split_once(':')
        && !head.is_empty()
        && head.bytes().all(|b| b.is_ascii_alphabetic())
    {
        let word = head.to_ascii_lowercase();
        if let Some(p) = PRODUCTS.iter().find(|p| **p == word) {
            return Ok((p, join_lines(rest)));
        }
        if let Some(p) = PRODUCTS.iter().find(|p| edit_distance(p, &word) <= 2) {
            return Err(FragmentError::UnknownProduct {
                file: file.to_owned(),
                got: head.to_owned(),
                suggestion: (*p).to_owned(),
            });
        }
    }
    Ok((PRODUCTS[0], join_lines(first)))
}

/// Levenshtein distance between two ASCII words.
fn edit_distance(a: &str, b: &str) -> usize {
    let (a, b) = (a.as_bytes(), b.as_bytes());
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.iter().enumerate() {
        let mut cur = vec![i + 1];
        for (j, cb) in b.iter().enumerate() {
            cur.push(
                (prev[j] + usize::from(ca != cb))
                    .min(prev[j + 1] + 1)
                    .min(cur[j] + 1),
            );
        }
        prev = cur;
    }
    prev[b.len()]
}

fn join_lines(s: &str) -> String {
    s.lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .collect::<Vec<_>>()
        .join(" ")
}

/// Parse a fragment file name `<ULID>.<type>.md` into its upper-case ULID and type.
///
/// # Errors
///
/// [`FragmentError::BadName`] for a wrong shape or non-ULID stem,
/// [`FragmentError::UnknownType`] for a type outside [`Kind::ALL`].
pub fn parse_name(file: &str) -> Result<(String, Kind), FragmentError> {
    let bad = |why: &str| FragmentError::BadName {
        file: file.to_owned(),
        why: why.to_owned(),
    };
    let parts: Vec<&str> = file.split('.').collect();
    if parts.len() != 3 || parts[2] != "md" {
        return Err(bad(
            "expected exactly three dot-separated parts ending in .md",
        ));
    }
    let ulid = parts[0].to_ascii_uppercase();
    if ulid.parse::<ulid::Ulid>().is_err() {
        return Err(bad("the first part is not a ULID"));
    }
    let Some(kind) = Kind::parse(parts[1]) else {
        return Err(FragmentError::UnknownType {
            file: file.to_owned(),
            got: parts[1].to_owned(),
        });
    };
    Ok((ulid, kind))
}

/// Validate one fragment's name and body.
pub(crate) fn parse_one(
    file: &str,
    body: &str,
    resolver: &dyn TicketResolver,
) -> Result<Fragment, FragmentError> {
    let (ulid, kind) = parse_name(file)?;
    let Some(handle) = resolver.handle(&ulid) else {
        return Err(FragmentError::UnknownTicket {
            file: file.to_owned(),
            ulid,
        });
    };
    if let Some(at) = body.bytes().position(|b| !b.is_ascii()) {
        return Err(FragmentError::NonAscii {
            file: file.to_owned(),
            at,
        });
    }
    let (product, text) = split_product(file, body)?;
    if text.is_empty() {
        return Err(FragmentError::Empty {
            file: file.to_owned(),
        });
    }
    Ok(Fragment {
        file: file.to_owned(),
        ulid,
        handle,
        kind,
        product,
        text,
    })
}

/// Read every fragment in `dir`, collecting all problems; the result is sorted by type, then ULID.
///
/// # Errors
/// Every invalid fragment, not just the first.
///
/// A missing directory is an empty set. `.gitkeep` is ignored.
pub fn read_all(
    dir: &Path,
    resolver: &dyn TicketResolver,
) -> Result<Vec<Fragment>, Vec<FragmentError>> {
    let Ok(rd) = fs::read_dir(dir) else {
        tracing::debug!(dir = %dir.display(), "no changelog.d directory");
        return Ok(Vec::new());
    };
    let mut names: Vec<String> = rd
        .filter_map(Result::ok)
        .filter(|e| e.path().is_file())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .filter(|n| n != ".gitkeep")
        .collect();
    names.sort();
    let (mut ok, mut errs) = (Vec::new(), Vec::new());
    for name in names {
        let res = match fs::read_to_string(dir.join(&name)) {
            Ok(body) => parse_one(&name, &body, resolver),
            Err(e) => Err(FragmentError::Unreadable {
                file: name.clone(),
                reason: e.to_string(),
            }),
        };
        match res {
            Ok(f) => ok.push(f),
            Err(e) => {
                tracing::warn!(error = %e, "invalid fragment");
                errs.push(e);
            }
        }
    }
    if !errs.is_empty() {
        return Err(errs);
    }
    ok.sort_by(|a, b| (a.kind, &a.ulid).cmp(&(b.kind, &b.ulid)));
    Ok(ok)
}
