//! The one path-canonicalization function and the pure, style-aware path predicates.
//!
//! `std::fs::canonicalize` returns a verbatim path (`\\?\C:\...`) on Windows, which git and
//! most other tools cannot use. [`canonical`] is the single place the workspace resolves a path
//! against the file system; it strips the verbatim prefix when the path survives without it
//! (the `dunce` approach). The predicates here are pure text functions over a [`Style`], so
//! the Windows rules are tested on any host (docs/design/paths.md section 4).
// frob:ticket 01M42FN1YDHJNZ5NM7QEDPHHFS

use std::io;
use std::path::{Path, PathBuf};

/// The path syntax a string is read in; the pure functions work for either on any host.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Style {
    /// `/` separators, one root, case-sensitive.
    Posix,
    /// `/` and `\` separators, drive, UNC and verbatim prefixes, case-insensitive.
    Windows,
}

impl Style {
    /// The style of the machine this binary runs on.
    pub const fn host() -> Self {
        if cfg!(windows) {
            Self::Windows
        } else {
            Self::Posix
        }
    }
}

/// Resolve `path` against the file system: absolute, symlinks followed, and never verbatim when avoidable.
///
/// # Errors
///
/// The OS error when the path does not exist or cannot be read.
pub fn canonical(path: &Path) -> io::Result<PathBuf> {
    #[expect(
        clippy::disallowed_methods,
        reason = "the one canonicalization function (docs/design/paths.md section 3)"
    )]
    let real = std::fs::canonicalize(path)?;
    let out = simplify(&real);
    tracing::trace!(path = ?path, canonical = ?out, "canonicalized");
    Ok(out)
}

/// `real` without its verbatim prefix when [`simplify_verbatim`] says that is safe.
fn simplify(real: &Path) -> PathBuf {
    if !cfg!(windows) {
        return real.to_path_buf();
    }
    let simple = real.to_str().and_then(simplify_verbatim);
    simple.map_or_else(|| real.to_path_buf(), PathBuf::from)
}

/// The non-verbatim spelling of a verbatim Windows path, or `None` when it must stay verbatim.
///
/// `\\?\C:\a` becomes `C:\a` and `\\?\UNC\srv\share\a` becomes `\\srv\share\a`, only when every
/// component is valid without the prefix: no `.`/`..`, no reserved device name, no trailing dot
/// or space, no `<>:"|?*` or `/`, and the whole stays under `MAX_PATH` (260).
pub fn simplify_verbatim(text: &str) -> Option<String> {
    let (head, rest) = if let Some(r) = text.strip_prefix(r"\\?\UNC\") {
        (r"\\", r)
    } else {
        let r = text.strip_prefix(r"\\?\")?;
        let b = r.as_bytes();
        if b.len() < 2 || !b[0].is_ascii_alphabetic() || b[1] != b':' {
            return None;
        }
        ("", r)
    };
    if text.len() >= 260 || rest.contains('/') {
        return None;
    }
    let is_unc = !head.is_empty();
    for (i, comp) in rest.split('\\').enumerate() {
        let drive = !is_unc && i == 0;
        if !drive && !component_ok_without_prefix(comp) {
            return None;
        }
    }
    if is_unc && rest.split('\\').count() < 2 {
        return None;
    }
    Some(format!("{head}{rest}"))
}

/// True when `comp` names the same file with or without the verbatim prefix.
fn component_ok_without_prefix(comp: &str) -> bool {
    if comp.is_empty() || is_dot(comp) || comp.ends_with('.') || comp.ends_with(' ') {
        return false;
    }
    if comp.contains(['<', '>', ':', '"', '|', '?', '*', '/']) {
        return false;
    }
    let stem = comp
        .split('.')
        .next()
        .unwrap_or(comp)
        .trim_end()
        .to_ascii_uppercase();
    let reserved = matches!(
        stem.as_str(),
        "CON" | "PRN" | "AUX" | "NUL" | "CONIN$" | "CONOUT$"
    ) || ["COM", "LPT"].iter().any(|p| {
        stem.strip_prefix(p)
            .is_some_and(|n| n.len() == 1 && matches!(n.as_bytes()[0], b'1'..=b'9'))
    });
    !reserved
}

/// True for the two components that move within a path.
fn is_dot(comp: &str) -> bool {
    comp == "." || comp == ".."
}

/// True when any component of `text`, split on both `/` and `\` (every style), is `.` or `..`.
pub fn has_dot_component(text: &str) -> bool {
    text.split(['/', '\\']).any(is_dot)
}

/// [`has_dot_component`] for a host path; a path that is not text is refused (treated as having one).
pub fn path_has_dot_component(path: &Path) -> bool {
    let text = path.to_str();
    text.is_none_or(has_dot_component)
}

/// The prefix and normal components of an absolute `text` in `style`, or `None` when it is relative or unsafe.
fn parse_absolute(style: Style, text: &str) -> Option<(String, Vec<String>)> {
    if has_dot_component(text) {
        return None;
    }
    match style {
        Style::Posix => {
            let rest = text.strip_prefix('/')?;
            Some((
                String::new(),
                rest.split('/')
                    .filter(|c| !c.is_empty())
                    .map(str::to_owned)
                    .collect(),
            ))
        }
        Style::Windows => {
            let norm = text.replace('/', "\\");
            let (prefix, rest) = windows_prefix(&norm)?;
            let comps: Vec<String> = rest
                .split('\\')
                .filter(|c| !c.is_empty())
                .map(str::to_owned)
                .collect();
            if comps.iter().any(|c| !component_ok_without_prefix(c)) {
                return None;
            }
            Some((
                prefix.to_ascii_lowercase(),
                comps.iter().map(|c| c.to_lowercase()).collect(),
            ))
        }
    }
}

/// Split a Windows path into its normalized prefix (`c:`, `\\srv\share`) and the rest; `None` unless rooted.
fn windows_prefix(norm: &str) -> Option<(String, &str)> {
    if let Some(r) = norm
        .strip_prefix(r"\\?\UNC\")
        .or_else(|| norm.strip_prefix(r"\\.\UNC\"))
    {
        return unc(r);
    }
    if let Some(r) = norm
        .strip_prefix(r"\\?\")
        .or_else(|| norm.strip_prefix(r"\\.\"))
    {
        return drive(r);
    }
    if let Some(r) = norm.strip_prefix(r"\\") {
        return unc(r);
    }
    drive(norm)
}

/// `X:\rest` as (`x:`, rest); the root separator is required (`C:foo` is drive-relative).
fn drive(s: &str) -> Option<(String, &str)> {
    let b = s.as_bytes();
    if b.len() >= 3 && b[0].is_ascii_alphabetic() && b[1] == b':' && b[2] == b'\\' {
        Some((s[..2].to_owned(), &s[3..]))
    } else {
        None
    }
}

/// `server\share\rest` as (`\\server\share`, rest).
fn unc(s: &str) -> Option<(String, &str)> {
    let mut it = s.splitn(3, '\\');
    let (server, share) = (it.next()?, it.next()?);
    if server.is_empty() || share.is_empty() {
        return None;
    }
    Some((format!(r"\\{server}\{share}"), it.next().unwrap_or("")))
}

/// True when `candidate` lies strictly below `root` by whole components, in `style`.
///
/// Both must be absolute and free of `.`/`..`; Windows compares case-insensitively, treats `/` and
/// `\` alike, and reads verbatim and plain prefixes as the same. Anything not understood is `false`.
pub fn strictly_inside(style: Style, root: &str, candidate: &str) -> bool {
    let (Some((rp, rc)), Some((cp, cc))) = (
        parse_absolute(style, root),
        parse_absolute(style, candidate),
    ) else {
        return false;
    };
    rp == cp && cc.len() > rc.len() && cc.starts_with(&rc)
}

/// [`strictly_inside`] for host paths in the host style; a path that is not text is never inside.
pub fn path_strictly_inside(root: &Path, candidate: &Path) -> bool {
    let (r, c) = (root.to_str(), candidate.to_str());
    r.zip(c)
        .is_some_and(|(r, c)| strictly_inside(Style::host(), r, c))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-exec/src/path.rs::simplify_verbatim
    #[test]
    fn verbatim_prefixes_strip_only_when_safe() {
        assert_eq!(
            simplify_verbatim(r"\\?\C:\Users\a\b").as_deref(),
            Some(r"C:\Users\a\b")
        );
        assert_eq!(
            simplify_verbatim(r"\\?\UNC\srv\share\x").as_deref(),
            Some(r"\\srv\share\x")
        );
        assert_eq!(simplify_verbatim(r"C:\plain"), None);
        assert_eq!(simplify_verbatim(r"\\?\C:\a\NUL"), None);
        assert_eq!(simplify_verbatim(r"\\?\C:\a\com1.txt"), None);
        assert_eq!(simplify_verbatim(r"\\?\C:\a.\b"), None);
        assert_eq!(simplify_verbatim(r"\\?\C:\a\..\b"), None);
        assert_eq!(simplify_verbatim(r"\\?\C:\a/b"), None);
        assert_eq!(simplify_verbatim(r"\\?\Volume{1}\a"), None);
        let long = format!(r"\\?\C:\{}", "a".repeat(300));
        assert_eq!(simplify_verbatim(&long), None);
    }

    // frob:tests crates/gob-exec/src/path.rs::has_dot_component
    #[test]
    fn dot_components_are_found_in_every_style() {
        for bad in [
            "/a/../b",
            "/a/./b",
            r"C:\a\..\b",
            r"\\?\C:\a\..\b",
            r"\\?\C:\a/../b",
            r"\\srv\sh\.\x",
            "..",
            "a/..",
        ] {
            assert!(has_dot_component(bad), "{bad}");
        }
        for ok in ["/a/b..c", "/a/.hidden", r"C:\a\...\b", "/a/target-old"] {
            assert!(!has_dot_component(ok), "{ok}");
        }
    }

    // frob:tests crates/gob-exec/src/path.rs::strictly_inside
    #[test]
    fn windows_style_inputs_are_contained_by_components() {
        let root = r"C:\Work\target";
        for inside in [
            r"C:\Work\target\debug",
            r"c:\work\TARGET\debug\deps",
            r"C:/Work/target/debug",
            r"\\?\C:\Work\target\debug",
            r"\\?\c:\work\target\a\b",
            r"C:\Work\target\\debug",
        ] {
            assert!(strictly_inside(Style::Windows, root, inside), "{inside}");
        }
        for outside in [
            r"C:\Work\target",
            r"C:\Work\target\",
            r"C:\Work\target-old",
            r"C:\Work\target-old\debug",
            r"C:\Work",
            r"D:\Work\target\debug",
            r"C:\Work\target\debug\..\..\target-old",
            r"\\?\C:\Work\target\debug\..\..\target-old",
            r"\\?\C:\Work\target\debug/../../target-old",
            r"C:\Work\target\.\debug",
            r"C:Work\target\debug",
            r"\\srv\share\Work\target\debug",
            r"Work\target\debug",
            r"C:\Work\target\debug.",
            r"C:\Work\target\debug\nul",
            r"C:\Work\target\a:stream",
        ] {
            assert!(!strictly_inside(Style::Windows, root, outside), "{outside}");
        }
        assert!(strictly_inside(
            Style::Windows,
            r"\\srv\share\t",
            r"\\SRV\Share\t\x"
        ));
        assert!(strictly_inside(
            Style::Windows,
            r"\\?\UNC\srv\share\t",
            r"\\srv\share\t\x"
        ));
        assert!(!strictly_inside(
            Style::Windows,
            r"\\srv\share\t",
            r"\\srv\other\t\x"
        ));
        assert!(strictly_inside(
            Style::Posix,
            "/a/target",
            "/a/target/debug"
        ));
        assert!(!strictly_inside(Style::Posix, "/a/target", "/a/target-old"));
        assert!(!strictly_inside(
            Style::Posix,
            "/a/target",
            "/a/target/../x"
        ));
        assert!(!strictly_inside(Style::Posix, "/a/target", "a/target/x"));
    }

    proptest::proptest! {
        // frob:tests crates/gob-exec/src/path.rs::strictly_inside
        /// Whatever Windows-style spelling a candidate takes, one admitted is below the root and has no dot component.
        #[test]
        fn no_admitted_windows_path_escapes_the_root(
            root_parts in proptest::collection::vec("[A-Za-z0-9_-]{1,6}", 1..4),
            cand in proptest::collection::vec("[A-Za-z0-9_.-]{0,6}|\\.\\.|\\.", 0..7),
            sep in proptest::collection::vec(proptest::bool::ANY, 8),
            verbatim in proptest::bool::ANY,
            upper in proptest::bool::ANY,
        ) {
            let root = format!(r"C:\{}", root_parts.join("\\"));
            let mut text = String::from(if verbatim { r"\\?\C:" } else { "C:" });
            for (i, c) in cand.iter().enumerate() {
                text.push(if !verbatim && sep[i % sep.len()] { '/' } else { '\\' });
                text.push_str(c);
            }
            let text = if upper { text.to_uppercase() } else { text };
            if strictly_inside(Style::Windows, &root, &text) {
                proptest::prop_assert!(!has_dot_component(&text));
                let lower = text.replace('/', "\\").to_lowercase();
                let want = format!(r"c:\{}\", root_parts.join("\\").to_lowercase());
                let lower = lower.trim_start_matches(r"\\?\");
                proptest::prop_assert!(lower.starts_with(&want), "{lower} vs {want}");
            }
        }
    }

    // frob:tests crates/gob-exec/src/path.rs::canonical
    #[test]
    fn canonical_resolves_and_errors_on_missing() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let c = canonical(tmp.path()).expect("canonical");
        assert!(c.is_absolute());
        assert!(canonical(&tmp.path().join("missing")).is_err());
    }
}
