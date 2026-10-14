//! The builtin function operands `slug(s)` and `resolve(path, from)` (grl-spec.md 3.4).
//!
//! Both are pure text functions; an argument that is not statically readable text makes the
//! result Unknown, and an argument the node simply lacks makes it Absent.

use super::field::{Datum, Scalar};

/// The text of a datum, or the datum standing for "no text" (Absent/Unknown pass through).
pub(super) fn text_of(d: Datum) -> Result<String, Datum> {
    match d {
        Datum::Known(Scalar::Str(s)) => Ok(s),
        Datum::Absent => Err(Datum::Absent),
        _ => Err(Datum::Unknown),
    }
}

/// `slug(s)`: the GitHub-style heading anchor of `s`.
pub(super) fn slug(s: Datum) -> Datum {
    match text_of(s) {
        Ok(t) => Datum::text(gob_symbols::slugify(&t)),
        Err(d) => d,
    }
}

/// `resolve(path, from)`: `path` against the directory of the file path `from`.
pub(super) fn resolve(path: Datum, from: Datum) -> Datum {
    match (text_of(path), text_of(from)) {
        (Ok(p), Ok(f)) => resolve_path(&p, &f).map_or(Datum::Absent, Datum::text),
        (Err(Datum::Absent), _) | (_, Err(Datum::Absent)) => Datum::Absent,
        _ => Datum::Unknown,
    }
}

/// Joins `path` onto the directory of `from`, normalising `.` and `..`; a leading `/` is
/// relative to the repository root. None when the result escapes the root.
fn resolve_path(path: &str, from: &str) -> Option<String> {
    let mut parts: Vec<&str> = Vec::new();
    let base = match path.strip_prefix('/') {
        Some(_) => "",
        None => from.rsplit_once('/').map_or("", |(dir, _)| dir),
    };
    for seg in base.split('/').chain(path.split('/')) {
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

#[cfg(test)]
mod tests {
    use super::resolve_path;

    #[test]
    fn paths_join_onto_the_directory_of_the_source_file() {
        assert_eq!(
            resolve_path("b.md", "docs/a.md").as_deref(),
            Some("docs/b.md")
        );
        assert_eq!(
            resolve_path("../b.md", "docs/a.md").as_deref(),
            Some("b.md")
        );
        assert_eq!(resolve_path("./x/b.md", "a.md").as_deref(), Some("x/b.md"));
        assert_eq!(
            resolve_path("/r/b.md", "docs/a.md").as_deref(),
            Some("r/b.md")
        );
        assert_eq!(resolve_path("../../b.md", "docs/a.md"), None);
    }
}
