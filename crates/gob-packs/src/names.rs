//! Reserved pack names and provenance prefixes (security.md 2.8, SEC-30).
//!
//! Names starting with a built-in prefix belong to built-in packs, so a
//! repository or external pack claiming one is refused as PACK005. Every
//! pack is shown with a provenance prefix (`builtin:`, `repo:packs/NAME` or
//! `ext:HOST/NAME`) so a spoofed origin is visible in prompts and reports.

// frob:ticket 01M3ZX80EYSD0XF6T2DPWS7RWW

use crate::error::PackError;

/// Name prefixes reserved for built-in packs (security.md 2.8).
pub const RESERVED_PREFIXES: [&str; 6] = ["std", "grimble", "frob", "crunk", "core", "gob"];

/// Refuses a repository or external pack whose name starts with a reserved prefix.
///
/// # Errors
/// PACK005 [`PackError::Malformed`] naming `pack.name` and the reserved prefix it starts with.
pub fn check_reserved(file: &str, name: &str) -> Result<(), PackError> {
    match RESERVED_PREFIXES.iter().find(|p| name.starts_with(**p)) {
        Some(prefix) => {
            tracing::debug!(file, name, prefix, "pack name rejected: reserved prefix");
            Err(PackError::malformed(
                file,
                "pack.name",
                format!(
                    "`{name}` starts with the reserved prefix `{prefix}` (built-in packs only)"
                ),
            ))
        }
        None => Ok(()),
    }
}

/// Where a pack came from, shown as its provenance prefix.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Provenance {
    /// Compiled into the product.
    Builtin,
    /// Vendored in the repository under `packs/`.
    Repo,
    /// Fetched from an external host and vendored.
    External {
        /// The host the pack was fetched from.
        host: String,
    },
}

impl Provenance {
    /// The label shown for pack `name`, for example `ext:example.org/py-safety`.
    pub fn label(&self, name: &str) -> String {
        match self {
            Self::Builtin => format!("builtin:{name}"),
            Self::Repo => format!("repo:packs/{name}"),
            Self::External { host } => format!("ext:{host}/{name}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::load;

    const PACK: &str = "[pack]\nname = \"NAME\"\nversion = \"1.0.0\"\n";

    /// Writes a pack.toml named `name` into a fresh directory and loads it.
    fn load_named(name: &str) -> Result<crate::Manifest, PackError> {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("pack.toml");
        std::fs::write(&path, PACK.replace("NAME", name)).unwrap();
        load(&path)
    }

    // frob:ticket 01M3ZX80EYSD0XF6T2DPWS7RWW
    // frob:tests crates/gob-packs/src/names.rs::check_reserved
    #[test]
    fn repo_pack_named_grimble_extras_is_pack005_naming_the_prefix() {
        let e = load_named("grimble-extras").unwrap_err();
        assert_eq!(e.code().as_str(), "PACK005");
        let msg = e.to_string();
        assert!(msg.contains("pack.name"), "{msg}");
        assert!(msg.contains("reserved prefix `grimble`"), "{msg}");
    }

    // frob:ticket 01M3ZX80EYSD0XF6T2DPWS7RWW
    // frob:tests crates/gob-packs/src/names.rs::check_reserved
    #[test]
    fn every_reserved_prefix_is_refused_and_others_pass() {
        for p in RESERVED_PREFIXES {
            let e = check_reserved("pack.toml", &format!("{p}-x")).unwrap_err();
            assert_eq!(e.code().as_str(), "PACK005");
        }
        assert!(check_reserved("pack.toml", "py-safety").is_ok());
        assert!(load_named("py-safety").is_ok());
    }

    // frob:ticket 01M3ZX80EYSD0XF6T2DPWS7RWW
    // frob:tests crates/gob-packs/src/names.rs::check_reserved
    #[test]
    fn config_table_outside_packs_is_pack005() {
        // The closed schema admits no table but [pack], [provides] and [effects]:
        // a pack may only configure itself under [packs.NAME] (security.md 2.8).
        let text = "[pack]\nname = \"py-safety\"\nversion = \"1.0.0\"\n\n[grimble.x]\nv = 1\n";
        let e = crate::Manifest::parse("pack.toml", text).unwrap_err();
        assert_eq!(e.code().as_str(), "PACK005");
        assert!(e.to_string().contains("grimble"), "{e}");
    }

    // frob:ticket 01M3ZX80EYSD0XF6T2DPWS7RWW
    // frob:tests crates/gob-packs/src/names.rs::label
    #[test]
    fn provenance_labels_match_the_three_origins() {
        assert_eq!(Provenance::Builtin.label("std"), "builtin:std");
        assert_eq!(Provenance::Repo.label("py-safety"), "repo:packs/py-safety");
        let ext = Provenance::External {
            host: "example.org".to_owned(),
        };
        assert_eq!(ext.label("py-safety"), "ext:example.org/py-safety");
    }
}
