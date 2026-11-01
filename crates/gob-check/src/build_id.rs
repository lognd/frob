//! The build id of this workspace build: the short git sha every product binary shares.
//!
//! Two binaries of one version built from different commits report different ids, which is how
//! `frob check` spots a stale sibling at an equal version (~RP9EDXC). Absent when the build had
//! neither a git checkout nor `FROB_BUILD_ID`; an absent id is never compared.

use std::sync::OnceLock;

/// The build id baked at compile time, or `None` for a build without a git checkout.
// frob:ticket 01M6BFJGKXT2JXSB5TARP9EDXC
pub fn build_id() -> Option<&'static str> {
    option_env!("GOB_BUILD_ID")
}

/// `version` (one per process: the first call's result is cached) with `+<build id>` appended, unless it already carries build metadata or no id exists.
// frob:ticket 01M6BFJGKXT2JXSB5TARP9EDXC
pub fn display_version(version: &'static str) -> &'static str {
    static CELL: OnceLock<String> = OnceLock::new();
    match build_id() {
        Some(id) if !version.contains('+') => CELL.get_or_init(|| format!("{version}+{id}")),
        _ => version,
    }
}

/// True only when both build ids exist and differ (a missing id never compares).
// frob:ticket 01M6BFJGKXT2JXSB5TARP9EDXC
pub fn ids_differ(theirs: Option<&str>, ours: Option<&str>) -> bool {
    match (theirs, ours) {
        (Some(t), Some(o)) => t != o,
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/build_id.rs::ids_differ
    #[test]
    fn only_two_present_unequal_ids_differ() {
        assert!(ids_differ(Some("a"), Some("b")));
        assert!(!ids_differ(Some("a"), Some("a")));
        assert!(!ids_differ(None, Some("a")));
        assert!(!ids_differ(Some("a"), None));
    }

    // frob:tests crates/gob-check/src/build_id.rs::display_version
    #[test]
    fn display_version_keeps_existing_metadata() {
        assert_eq!(display_version("1.0.0-dev+abc"), "1.0.0-dev+abc");
        let v = display_version("1.0.0");
        assert!(v.starts_with("1.0.0"));
        if let Some(id) = build_id() {
            assert_eq!(v, format!("1.0.0+{id}"));
        }
    }
}
