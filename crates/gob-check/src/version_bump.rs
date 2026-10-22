//! Version-bump awareness for public-API breakage: a breaking change is allowed when the package version bump permits it.

// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52

use std::path::Path;

use gob_git::Repo;

use crate::tool_parse::{compare, parse_version};

/// Where the package version is read, at the working tree and at the baseline ref.
const MANIFEST: &str = "pyproject.toml";

/// Whether moving from one package version to another permits a breaking API change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Bump {
    /// A major bump, or a minor bump below 1.0: breakage is allowed.
    Permits,
    /// Same, lower or patch-level version: breakage needs a bigger bump.
    Forbids,
}

/// The leading `MAJOR.MINOR.PATCH` of a PEP 440 style version, ignoring any `rc`/`.post`/`+local` tail.
fn release(version: &str) -> Option<Vec<u64>> {
    let head: String = version
        .trim()
        .trim_start_matches('v')
        .chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.')
        .collect();
    parse_version(head.trim_end_matches('.')).filter(|v| v.len() <= 4)
}

/// Whether the bump from `old` to `new` permits a breaking change; `None` when either does not parse.
///
/// A major increase always permits it. While the major is 0 a minor increase does too, since
/// pre-1.0 releases make no stability promise across minors. Equal, lower and patch-only
/// versions do not, and neither does a major that is still 0 with only the patch moving.
// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
pub(crate) fn bump_permits_break(old: &str, new: &str) -> Option<Bump> {
    let (o, n) = (release(old)?, release(new)?);
    let at = |v: &[u64], i: usize| v.get(i).copied().unwrap_or(0);
    let permits = compare(&n, &o).is_gt()
        && (at(&n, 0) > at(&o, 0) || (at(&o, 0) == 0 && at(&n, 0) == 0 && at(&n, 1) > at(&o, 1)));
    Some(if permits {
        Bump::Permits
    } else {
        Bump::Forbids
    })
}

/// The `version` of a `pyproject.toml` (`[project]`, else `[tool.poetry]`); `None` when absent or dynamic.
// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
pub(crate) fn manifest_version(text: &str) -> Option<String> {
    let doc: toml::Table = text.parse().ok()?;
    let from = |path: &[&str]| {
        let mut cur = doc.get(*path.first()?)?;
        for key in &path[1..] {
            cur = cur.get(*key)?;
        }
        cur.get("version")?.as_str().map(str::to_owned)
    };
    from(&["project"]).or_else(|| from(&["tool", "poetry"]))
}

/// The baseline ref a griffe stage compares against (`--against REF`, `-a REF` or `--against=REF`).
// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
pub(crate) fn against_ref(args: &[String]) -> Option<&str> {
    let mut it = args.iter();
    while let Some(arg) = it.next() {
        if arg == "--against" || arg == "-a" {
            return it.next().map(String::as_str);
        }
        if let Some(rest) = arg.strip_prefix("--against=") {
            return Some(rest);
        }
    }
    None
}

/// The verdict on a set of breaking changes, given the versions around them.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Gate {
    /// The version bump permits the breakage: drop the findings.
    Allowed,
    /// The bump is too small: keep the findings as errors.
    Violation,
    /// A version could not be determined; the reason says which.
    Unresolved(String),
}

/// Decide from the baseline manifest text (`None` when unreadable) and the current manifest text.
// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
pub(crate) fn decide(old_manifest: Option<&str>, new_manifest: Option<&str>) -> Gate {
    let version = |text: Option<&str>, which: &str| {
        text.and_then(manifest_version)
            .ok_or_else(|| format!("no static package version in the {which} {MANIFEST}"))
    };
    let (old, new) = match (
        version(old_manifest, "baseline"),
        version(new_manifest, "current"),
    ) {
        (Ok(o), Ok(n)) => (o, n),
        (Err(e), _) | (_, Err(e)) => return Gate::Unresolved(e),
    };
    match bump_permits_break(&old, &new) {
        Some(Bump::Permits) => Gate::Allowed,
        Some(Bump::Forbids) => Gate::Violation,
        None => Gate::Unresolved(format!(
            "package version `{old}` or `{new}` is not a recognised version"
        )),
    }
}

#[allow(
    clippy::disallowed_methods,
    reason = "the current package version is read from the work tree, which the tool just compared"
)]
/// Gate griffe breakage for the stage `args` against the manifests at `root` and at the baseline ref.
// frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
pub(crate) fn gate_for(root: &Path, args: &[String]) -> Gate {
    let Some(base) = against_ref(args) else {
        return Gate::Unresolved(
            "the stage names no baseline (`--against REF`) to read the old version from".to_owned(),
        );
    };
    let old = Repo::discover(root)
        .ok()
        .and_then(|repo| repo.read_blob_at(base, MANIFEST).ok().flatten())
        .and_then(|b| String::from_utf8(b).ok());
    let new = std::fs::read_to_string(root.join(MANIFEST)).ok();
    let gate = decide(old.as_deref(), new.as_deref());
    tracing::info!(
        baseline = base,
        ?gate,
        "griffe breakage gated on the version bump"
    );
    gate
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest(version: &str) -> String {
        format!("[project]\nname = \"pkg\"\nversion = \"{version}\"\n")
    }

    // frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
    // frob:tests crates/gob-check/src/version_bump.rs::decide
    #[test]
    fn permitting_bump_allows_breakage() {
        let gate = |o: &str, n: &str| decide(Some(&manifest(o)), Some(&manifest(n)));
        assert_eq!(gate("1.4.2", "2.0.0"), Gate::Allowed);
        assert_eq!(gate("0.3.1", "0.4.0"), Gate::Allowed);
        assert_eq!(gate("0.9.0", "1.0.0rc1"), Gate::Allowed);
    }

    // frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
    // frob:tests crates/gob-check/src/version_bump.rs::decide
    #[test]
    fn missing_or_small_bump_keeps_breakage_an_error() {
        let gate = |o: &str, n: &str| decide(Some(&manifest(o)), Some(&manifest(n)));
        assert_eq!(gate("1.4.2", "1.4.2"), Gate::Violation);
        assert_eq!(gate("1.4.2", "1.4.3"), Gate::Violation);
        assert_eq!(gate("1.4.2", "1.5.0"), Gate::Violation);
        assert_eq!(gate("0.3.1", "0.3.2"), Gate::Violation);
        assert_eq!(gate("2.0.0", "1.0.0"), Gate::Violation);
    }

    // frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
    // frob:tests crates/gob-check/src/version_bump.rs::decide
    // frob:tests crates/gob-check/src/version_bump.rs::against_ref
    #[test]
    fn undeterminable_versions_are_unresolved() {
        let ok = manifest("1.0.0");
        assert!(matches!(decide(None, Some(&ok)), Gate::Unresolved(_)));
        assert!(matches!(decide(Some(&ok), None), Gate::Unresolved(_)));
        assert!(matches!(
            decide(Some(&ok), Some("[project]\ndynamic = [\"version\"]\n")),
            Gate::Unresolved(_)
        ));
        assert!(matches!(
            decide(Some(&ok), Some(&manifest("banana"))),
            Gate::Unresolved(_)
        ));
        let args = |s: &[&str]| s.iter().map(|a| (*a).to_owned()).collect::<Vec<_>>();
        assert_eq!(against_ref(&args(&["pkg", "--against", "v1"])), Some("v1"));
        assert_eq!(against_ref(&args(&["pkg", "--against=v1"])), Some("v1"));
        assert_eq!(against_ref(&args(&["pkg"])), None);
    }

    // frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
    // frob:tests crates/gob-check/src/version_bump.rs::manifest_version
    #[test]
    fn poetry_manifests_are_read() {
        let poetry = "[tool.poetry]\nversion = \"3.1.0\"\n";
        assert_eq!(manifest_version(poetry).as_deref(), Some("3.1.0"));
    }
}
