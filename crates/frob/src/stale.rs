//! Stale-binary detection: warn when this binary was built from a commit other than the checkout's HEAD.
//!
//! The build script bakes the full HEAD sha and the checkout root; when `frob check` runs inside
//! that same checkout and HEAD has moved, findings may come from old code (the stale-binary false
//! findings of the audit, H4), so the check reports a loud warning first.

// frob:ticket 01M7AV6DHZ6KG77GJ74CAT8CDF

use std::path::Path;
use std::process::Command;

/// Full git sha this binary was built from; empty when built without git.
const BUILD_HEAD: &str = env!("FROB_BUILD_HEAD");
/// Checkout root this binary was built in; empty when built without git.
const BUILD_TOPLEVEL: &str = env!("FROB_BUILD_TOPLEVEL");

/// Warning text when `built` differs from `current` HEAD for a binary built from `top` and run in `root`.
pub(crate) fn stale_message(built: &str, top: &str, root: &Path, current: &str) -> Option<String> {
    if built.is_empty() || top.is_empty() || built == current {
        return None;
    }
    let same = match (Path::new(top).canonicalize(), root.canonicalize()) {
        (Ok(a), Ok(b)) => a == b,
        _ => false,
    };
    same.then(|| {
        let short = |s: &str| s.chars().take(9).collect::<String>();
        format!(
            "this frob binary is STALE: built from {} but the checkout is at {}; rebuild before trusting findings",
            short(built),
            short(current)
        )
    })
}

/// HEAD sha of the repository at `root`, when git can report one.
fn head_of(root: &Path) -> Option<String> {
    let out = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(["rev-parse", "HEAD"])
        .output()
        .ok()?;
    let text = String::from_utf8(out.stdout).ok()?;
    let text = text.trim();
    (out.status.success() && !text.is_empty()).then(|| text.to_owned())
}

/// The stale-binary warning for a run rooted at `root`, if this binary is out of date with its own checkout.
pub(crate) fn stale_warning(root: &Path) -> Option<String> {
    if BUILD_HEAD.is_empty() {
        return None;
    }
    let msg = stale_message(BUILD_HEAD, BUILD_TOPLEVEL, root, &head_of(root)?);
    if let Some(m) = &msg {
        tracing::warn!(root = ?root, "{m}");
    }
    msg
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn differing_head_in_own_checkout_warns() {
        let d = tempfile::tempdir().unwrap();
        let top = d.path().to_str().unwrap();
        let m = stale_message("aaaaaaaaaaaa", top, d.path(), "bbbbbbbbbbbb").unwrap();
        assert!(m.contains("STALE") && m.contains("aaaaaaaaa") && m.contains("bbbbbbbbb"));
    }

    #[test]
    fn same_head_other_checkout_or_unknown_is_quiet() {
        let d = tempfile::tempdir().unwrap();
        let o = tempfile::tempdir().unwrap();
        let top = d.path().to_str().unwrap();
        assert!(stale_message("aaa", top, d.path(), "aaa").is_none());
        assert!(stale_message("aaa", top, o.path(), "bbb").is_none());
        assert!(stale_message("", top, d.path(), "bbb").is_none());
        assert!(stale_message("aaa", "", d.path(), "bbb").is_none());
    }
}
