//! Rewrite absolute local paths in captured text to placeholders.
//!
//! Ledger events are committed and pushed, so a transcript that names
//! `/home/<user>/projects/<repo>-wt/<ticket>/...` would publish the user name and
//! directory layout. [`PathScrub`] rewrites the worktree root to `<worktree>`, the
//! repository root to `<repo>` and the home directory to `~` (longest root first),
//! only where the root ends at a path boundary. [`crate::provider::build_record`]
//! applies it to the transcript before the digest is computed, so the digest, the
//! stored text and the inline text all describe the same scrubbed bytes.

use std::path::{Path, PathBuf};

use frob_ledger::privacy::find_home_root;
use gob_git::Repo;

// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q

/// Placeholder for the worktree root.
pub const WORKTREE: &str = "<worktree>";
/// Placeholder for the repository root.
pub const REPO: &str = "<repo>";
/// Placeholder for the home directory.
pub const HOME: &str = "~";
/// Placeholder for the home directory of someone else (a foreign user name), used only by a repair.
pub const OTHER_HOME: &str = "~other";

/// Absolute roots to rewrite and the placeholder each becomes, longest root first.
#[derive(Debug, Clone, Default)]
pub struct PathScrub {
    rules: Vec<(String, String)>,
    /// Rewrite any remaining `/home/<name>` style root to [`OTHER_HOME`] (repair only).
    foreign: bool,
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
        let mut scrub = Self::default();
        scrub.add(worktree, WORKTREE);
        scrub.add(repo, REPO);
        if let Some(h) = home {
            scrub.add(h, HOME);
        }
        scrub.finish()
    }

    /// A scrub that repairs paths written on any machine of this repository: the checkout, its linked
    /// worktrees and the local origin (all rewritten to `<repo>`, `<worktree>` or the form relative to the
    /// repository parent, like `app-wt/T1`), the home directory, and every other home root to `~other`.
    ///
    /// Used by `ticket doctor --fix` on ledgers written before new evidence was scrubbed.
    pub fn for_repair(repo: &Repo, worktree: &Path) -> Self {
        let home = ["HOME", "USERPROFILE"]
            .iter()
            .find_map(std::env::var_os)
            .map(PathBuf::from);
        let main = main_root(repo, worktree);
        let mut roots = vec![main.clone()];
        if let Some(origin) = repo.remote_url("origin").and_then(|u| local_path(&u)) {
            roots.push(origin);
        }
        let mut scrub = Self {
            foreign: true,
            ..Self::default()
        };
        let parent_of = |r: &Path| r.parent().map(Path::to_path_buf);
        let mut siblings: Vec<PathBuf> = Vec::new();
        for w in repo.list_worktrees().unwrap_or_default() {
            if w.path != main && w.path != worktree {
                siblings.push(w.path);
            }
        }
        for root in &roots {
            let (Some(parent), Some(name)) = (parent_of(root), root.file_name()) else {
                continue;
            };
            let dir = format!("{}-wt", name.to_string_lossy());
            scrub.add_text(&parent.join(&dir), &dir);
            for w in siblings.iter().filter(|w| w.starts_with(&parent)) {
                if let Ok(rel) = w.strip_prefix(&parent) {
                    scrub.add_text(w, &rel.to_string_lossy().replace('\\', "/"));
                }
            }
        }
        for root in &roots {
            scrub.add(root, REPO);
        }
        scrub.add(worktree, WORKTREE);
        if let Some(h) = &home {
            scrub.add(h, HOME);
        }
        scrub.finish()
    }

    /// Register every spelling of `root` as rewriting to `placeholder`, unless an earlier rule owns it.
    fn add(&mut self, root: &Path, placeholder: &str) {
        self.add_text(root, placeholder);
    }

    fn add_text(&mut self, root: &Path, placeholder: &str) {
        for form in forms(root) {
            if !self.rules.iter().any(|(n, _)| *n == form) {
                self.rules.push((form, placeholder.to_owned()));
            }
        }
    }

    /// Order the rules longest root first.
    fn finish(mut self) -> Self {
        self.rules.sort_by_key(|(n, _)| std::cmp::Reverse(n.len()));
        tracing::debug!(
            rules = self.rules.len(),
            foreign = self.foreign,
            "path scrub built"
        );
        self
    }

    /// `text` with every configured root replaced by its placeholder.
    pub fn apply(&self, text: &str) -> String {
        let mut out = text.to_owned();
        for (needle, placeholder) in &self.rules {
            out = replace_rooted(&out, needle, placeholder);
        }
        if self.foreign {
            out = rewrite_foreign_homes(&out);
        }
        if out != text {
            tracing::debug!("absolute paths in captured text rewritten to placeholders");
        }
        out
    }
}

/// The work tree root of the main checkout of `repo`, falling back to `worktree`.
fn main_root(repo: &Repo, worktree: &Path) -> PathBuf {
    let common = repo.common_dir();
    if common.file_name().is_some_and(|n| n == ".git") {
        common.parent().unwrap_or(worktree).to_path_buf()
    } else {
        worktree.to_path_buf()
    }
}

/// The filesystem path a remote URL names, when it is a local path or a `file://` URL.
fn local_path(url: &str) -> Option<PathBuf> {
    let path = url.strip_prefix("file://").unwrap_or(url);
    (path.starts_with('/') && !path.contains(':'))
        .then(|| PathBuf::from(path.trim_end_matches('/')))
}

/// Replace every remaining `/home/<name>` style root by [`OTHER_HOME`], keeping the rest of the path.
fn rewrite_foreign_homes(text: &str) -> String {
    let mut out = text.to_owned();
    // Rescan the whole text each time so a hit is judged with the byte before it.
    while let Some(range) = find_home_root(out.as_bytes()) {
        out.replace_range(range, OTHER_HOME);
    }
    out
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

    /// A repair scrub sends sibling worktrees to the parent-relative form and foreign homes to `~other`.
    // frob:tests crates/frob-evidence/src/scrub.rs::rewrite_foreign_homes
    #[test]
    fn repair_rewrites_foreign_homes_and_is_idempotent() {
        let mut s = scrub();
        s.foreign = true;
        s.add_text(Path::new("/home/ann/projects/app-wt"), "app-wt");
        s.rules.sort_by_key(|(n, _)| std::cmp::Reverse(n.len()));
        let got = s.apply(
            "lease in /home/ann/projects/app-wt/T9; /home/bob/x and C:\\\\Users\\\\cy\\\\p and /home/ann/home/zed/q",
        );
        assert_eq!(
            got,
            "lease in app-wt/T9; ~other/x and ~other\\\\p and ~/home/zed/q"
        );
        assert_eq!(s.apply(&got), got, "a second pass changes nothing");
    }
}
