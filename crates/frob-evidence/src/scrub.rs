//! Rewrite absolute local paths in captured text to placeholders.
//!
//! Ledger events are committed and pushed, so a transcript that names
//! `/home/<user>/projects/<repo>-wt/<ticket>/...` would publish the user name and
//! directory layout. [`PathScrub`] rewrites the worktree root to `<worktree>`, the
//! repository root to `<repo>` and the home directory to `~` (longest root first),
//! only where the root ends at a path boundary. [`crate::provider::build_record`]
//! applies it to the transcript before the digest is computed, so the digest, the
//! stored text and the inline text all describe the same scrubbed bytes.

use std::path::Path;

// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A

/// Placeholder for the worktree root.
pub const WORKTREE: &str = "<worktree>";
/// Placeholder for the repository root.
pub const REPO: &str = "<repo>";
/// Placeholder for the home directory.
pub const HOME: &str = "~";

/// Absolute roots to rewrite and the placeholder each becomes, longest root first.
#[derive(Debug, Clone, Default)]
pub struct PathScrub {
    rules: Vec<(String, &'static str)>,
}

impl PathScrub {
    /// A scrub for `worktree` and `repo`, plus the home directory from `HOME` or `USERPROFILE`.
    pub fn new(repo: &Path, worktree: &Path) -> Self {
        let home = ["HOME", "USERPROFILE"]
            .iter()
            .find_map(std::env::var_os)
            .map(std::path::PathBuf::from);
        Self::with_home(repo, worktree, home.as_deref())
    }

    /// A scrub for `worktree`, `repo` and an explicit `home` (none skips the home rule).
    pub fn with_home(repo: &Path, worktree: &Path, home: Option<&Path>) -> Self {
        let mut rules: Vec<(String, &'static str)> = Vec::new();
        let mut add = |root: &Path, placeholder: &'static str| {
            for form in forms(root) {
                if !rules.iter().any(|(n, _)| *n == form) {
                    rules.push((form, placeholder));
                }
            }
        };
        add(worktree, WORKTREE);
        add(repo, REPO);
        if let Some(h) = home {
            add(h, HOME);
        }
        rules.sort_by_key(|(n, _)| std::cmp::Reverse(n.len()));
        tracing::debug!(rules = rules.len(), "path scrub built");
        Self { rules }
    }

    /// `text` with every configured root replaced by its placeholder.
    pub fn apply(&self, text: &str) -> String {
        let mut out = text.to_owned();
        for (needle, placeholder) in &self.rules {
            out = replace_rooted(&out, needle, placeholder);
        }
        if out != text {
            tracing::debug!("absolute paths in captured text rewritten to placeholders");
        }
        out
    }
}

/// The spellings of `root` worth matching: as given, canonical, with `/` separators and with doubled backslashes.
fn forms(root: &Path) -> Vec<String> {
    let mut bases = vec![root.to_string_lossy().into_owned()];
    if let Ok(c) = std::fs::canonicalize(root) {
        bases.push(c.to_string_lossy().into_owned());
    }
    let mut out = Vec::new();
    for b in bases {
        let b = b.trim_end_matches(['/', '\\']).to_owned();
        if b.len() < 2 {
            continue;
        }
        if b.contains('\\') {
            out.push(b.replace('\\', "/"));
            out.push(b.replace('\\', "\\\\"));
        }
        out.push(b);
    }
    out.sort();
    out.dedup();
    out
}

/// True for a character that continues a path component, so a root followed by it is a different path.
fn continues_name(c: char) -> bool {
    c.is_alphanumeric() || matches!(c, '_' | '.' | '-')
}

/// Replace `needle` by `with` wherever the next character does not continue a path component.
fn replace_rooted(text: &str, needle: &str, with: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut last = 0;
    for (at, _) in text.match_indices(needle) {
        if at < last {
            continue;
        }
        let end = at + needle.len();
        if text[end..].chars().next().is_some_and(continues_name) {
            continue;
        }
        out.push_str(&text[last..at]);
        out.push_str(with);
        last = end;
    }
    out.push_str(&text[last..]);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scrub() -> PathScrub {
        PathScrub::with_home(
            Path::new("/home/ann/projects/app"),
            Path::new("/home/ann/projects/app-wt/T1"),
            Some(Path::new("/home/ann")),
        )
    }

    /// Roots become placeholders, longest first, keeping the rest of the path.
    #[test]
    fn rewrites_worktree_repo_and_home() {
        let got = scrub().apply(
            "at /home/ann/projects/app-wt/T1/crates/x and /home/ann/projects/app/src and /home/ann/.cargo/bin",
        );
        assert_eq!(
            got,
            "at <worktree>/crates/x and <repo>/src and ~/.cargo/bin"
        );
    }

    /// A root that is only a prefix of a longer name is left alone.
    #[test]
    fn respects_path_boundaries() {
        let got = scrub().apply("/home/ann/projects/application and /home/annie/x");
        assert_eq!(got, "~/projects/application and /home/annie/x");
    }

    /// Windows roots match with both separators and doubled backslashes.
    #[test]
    fn windows_forms() {
        let s = PathScrub::with_home(
            Path::new("C:\\Users\\bo\\app"),
            Path::new("C:\\Users\\bo\\app-wt\\T1"),
            Some(Path::new("C:\\Users\\bo")),
        );
        assert_eq!(
            s.apply("C:\\Users\\bo\\app\\src C:/Users/bo/app/src C:\\\\Users\\\\bo\\\\x"),
            "<repo>\\src <repo>/src ~\\\\x"
        );
    }
}
