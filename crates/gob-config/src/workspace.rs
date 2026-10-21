//! Nested config discovery: a nested `grimble.toml` loads only when the root
//! manifest lists its directory in `[workspace] members` (security.md 2.9).
//!
//! Discovery never walks the tree, so vendored, ignored and submodule
//! directories cannot trigger nested loading unless explicitly listed.

use std::path::{Component, Path, PathBuf};

use crate::ConfigError;

/// Expand `[workspace] members` of the manifest text into directories under `root`.
///
/// Entries are relative directories; a trailing `/*` lists the immediate child
/// directories. Absolute paths and `..` components are rejected.
///
/// # Errors
/// [`ConfigError`] when the manifest is not valid TOML, `members` is malformed,
/// an entry escapes the root, or a wildcard directory cannot be read.
pub fn workspace_members(root: &Path, manifest: &str) -> Result<Vec<PathBuf>, ConfigError> {
    let table: toml::Table = manifest
        .parse()
        .map_err(|e: toml::de::Error| ConfigError::Parse {
            path: root.to_path_buf(),
            message: e.to_string(),
        })?;
    let invalid = |message: String| ConfigError::Invalid {
        table: "workspace".to_owned(),
        message,
    };
    let Some(ws) = table.get("workspace") else {
        return Ok(Vec::new());
    };
    let members = ws
        .get("members")
        .map(|m| {
            m.as_array()
                .ok_or_else(|| invalid("`members` must be an array".to_owned()))
        })
        .transpose()?;
    let mut out = Vec::new();
    for entry in members.into_iter().flatten() {
        let text = entry
            .as_str()
            .ok_or_else(|| invalid("`members` entries must be strings".to_owned()))?;
        let (base, wildcard) = match text.strip_suffix("/*") {
            Some(base) => (base, true),
            None => (text, false),
        };
        let rel = Path::new(base);
        if rel
            .components()
            .any(|c| !matches!(c, Component::Normal(_) | Component::CurDir))
        {
            tracing::warn!(member = text, "workspace member escapes the root; rejected");
            return Err(invalid(format!(
                "member `{text}` must be a relative path inside the root"
            )));
        }
        let dir = root.join(rel);
        if wildcard {
            let read = std::fs::read_dir(&dir).map_err(|source| ConfigError::Io {
                path: dir.clone(),
                source,
            })?;
            let mut kids: Vec<PathBuf> = read
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| p.is_dir())
                .collect();
            kids.sort();
            out.extend(kids);
        } else {
            out.push(dir);
        }
    }
    tracing::debug!(count = out.len(), "workspace members expanded");
    Ok(out)
}

/// Directories whose nested `file_name` config loads as its own root: listed members that contain it.
///
/// # Errors
/// [`ConfigError`] when the root manifest cannot be read or its members are invalid.
pub fn nested_config_dirs(root: &Path, file_name: &str) -> Result<Vec<PathBuf>, ConfigError> {
    let manifest_path = root.join(file_name);
    let text = match std::fs::read_to_string(&manifest_path) {
        Ok(text) => text,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(source) => {
            return Err(ConfigError::Io {
                path: manifest_path,
                source,
            });
        }
    };
    let dirs = workspace_members(root, &text)?
        .into_iter()
        .filter(|d| d.join(file_name).is_file())
        .collect::<Vec<_>>();
    for d in &dirs {
        tracing::debug!(dir = ?d, "nested config accepted via workspace members");
    }
    Ok(dirs)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tree(members: &str) -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        std::fs::write(
            root.join("grimble.toml"),
            format!("[workspace]\nmembers = [{members}]\n"),
        )
        .unwrap();
        std::fs::create_dir_all(root.join("vendor/dep")).unwrap();
        std::fs::write(root.join("vendor/dep/grimble.toml"), "").unwrap();
        dir
    }

    #[test]
    fn unlisted_vendored_config_is_not_loaded() {
        let dir = tree("");
        assert!(
            nested_config_dirs(dir.path(), "grimble.toml")
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn listed_member_loads_as_its_own_root() {
        let dir = tree("\"vendor/dep\"");
        let got = nested_config_dirs(dir.path(), "grimble.toml").unwrap();
        assert_eq!(got, vec![dir.path().join("vendor/dep")]);
    }

    #[test]
    fn escaping_member_is_rejected() {
        let dir = tree("\"../x\"");
        assert!(matches!(
            nested_config_dirs(dir.path(), "grimble.toml"),
            Err(ConfigError::Invalid { .. })
        ));
    }
}
