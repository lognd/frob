//! Binding a `[[check.tool]]` stage to a std tool definition (tool-binding.md section 2).
//!
//! A stage with `tool = "<name>"` takes command, parser, version range, probe, exit classes and
//! id map from the definition; keys the stage sets itself win. The command line is chosen from
//! the definition's variants once the tool version is known. Also here: the project-local tool
//! path and the (version, config digest) part of the result cache key.

use std::path::{Path, PathBuf};

use gob_packs::{ToolDef, Variant, std_tool};

use crate::config::{ToolParser, ToolStage};
use crate::tool_parse::in_range;

/// Directories under the repository root searched for a tool before `PATH`.
const PROJECT_BIN_DIRS: [&str; 3] = [".venv/bin", ".venv/Scripts", "node_modules/.bin"];

/// A stage with its definition's static fields applied, plus the definition for variant choice.
pub(crate) struct Bound {
    /// The effective stage.
    pub stage: ToolStage,
    /// The definition, when the stage names one.
    pub def: Option<ToolDef>,
}

/// Apply the std definition named by `stage.tool`; `Err` names an unknown definition or parser.
pub(crate) fn bind(stage: &ToolStage) -> Result<Bound, String> {
    let Some(name) = stage.tool.as_deref() else {
        return Ok(Bound {
            stage: stage.clone(),
            def: None,
        });
    };
    let def = std_tool(name).ok_or_else(|| format!("no std tool definition named `{name}`"))?;
    let parser = ToolParser::from_id(&def.parser)
        .ok_or_else(|| format!("definition `{name}` names unknown parser `{}`", def.parser))?;
    let mut out = stage.clone();
    if out.command.is_empty() {
        out.command.clone_from(&def.command);
    }
    if out.parser == ToolParser::None {
        out.parser = parser;
    }
    out.min_version = out.min_version.or_else(|| def.min_version.clone());
    out.max_version = out.max_version.or_else(|| def.max_version.clone());
    out.version_args = out.version_args.or_else(|| Some(def.version_args.clone()));
    out.exit_codes = out.exit_codes.or_else(|| Some(def.exit.declared()));
    for (tool_id, rule) in &def.id_map {
        out.id_map
            .entry(tool_id.clone())
            .or_insert_with(|| rule.clone());
    }
    tracing::debug!(stage = %out.name, tool = name, "stage bound to std definition");
    Ok(Bound {
        stage: out,
        def: Some(def),
    })
}

/// The first variant whose version range holds `version`.
fn pick<'a>(variants: &'a [Variant], version: &str) -> Option<&'a Variant> {
    variants
        .iter()
        .find(|v| in_range(version, v.min_version.as_deref(), v.max_version.as_deref()))
}

/// The arguments to run: the stage's own, else the definition's variant for `version`.
///
/// # Errors
///
/// A message when the stage relies on variants but none covers the (possibly unknown) version.
pub(crate) fn command_args(bound: &Bound, version: Option<&str>) -> Result<Vec<String>, String> {
    if !bound.stage.args.is_empty() {
        return Ok(bound.stage.args.clone());
    }
    let Some(def) = &bound.def else {
        return Ok(Vec::new());
    };
    let chosen = version.and_then(|v| pick(&def.variants, v));
    match chosen {
        Some(v) => {
            tracing::info!(stage = %bound.stage.name, version = version.unwrap_or(""), "command variant chosen");
            Ok(v.args.clone())
        }
        None => Err(format!(
            "no command variant of `{}` covers version {}",
            def.name,
            version.unwrap_or("(unreadable)")
        )),
    }
}

/// The project's own copy of `command` (first of `.venv/bin`, `node_modules/.bin`), if present.
pub(crate) fn project_tool(root: &Path, command: &str) -> Option<PathBuf> {
    let found = PROJECT_BIN_DIRS
        .iter()
        .flat_map(|d| {
            [
                root.join(d).join(command),
                root.join(d).join(format!("{command}.exe")),
            ]
        })
        .find(|p| p.is_file());
    if let Some(path) = &found {
        tracing::info!(command, path = %path.display(), "using the project's own tool");
    }
    found
}

/// The cache key of a stage's results: tool version plus the digest of its config files.
///
/// File digests of the inspected inputs are mixed in by the result store (ticket filed).
pub(crate) fn cache_key(root: &Path, def: Option<&ToolDef>, version: Option<&str>) -> String {
    let mut h = blake3::Hasher::new();
    h.update(version.unwrap_or("unknown").as_bytes());
    if let Some(def) = def {
        for file in &def.config_files {
            if let Ok(bytes) = std::fs::read(root.join(file)) {
                h.update(file.as_bytes());
                h.update(&bytes);
            }
        }
    }
    let key = h.finalize().to_hex().to_string();
    tracing::debug!(%key, "tool cache key");
    key
}

#[cfg(test)]
mod tests {
    use super::*;

    fn stage(tool: &str) -> ToolStage {
        ToolStage {
            name: tool.to_owned(),
            command: String::new(),
            args: Vec::new(),
            timeout_secs: 30,
            fail_on_nonzero: true,
            parser: ToolParser::None,
            labels: Vec::new(),
            id_map: std::collections::BTreeMap::new(),
            min_version: None,
            max_version: None,
            version_args: None,
            optional: false,
            tool: Some(tool.to_owned()),
            exit_codes: None,
        }
    }

    // frob:tests crates/gob-check/src/tool_bind.rs::bind
    #[test]
    fn zizmor_and_ruff_bind_from_data() {
        let z = bind(&stage("zizmor")).expect("zizmor");
        assert_eq!(z.stage.parser, ToolParser::ZizmorJsonV1);
        assert_eq!(
            z.stage.id_map.get("artipacked").map(String::as_str),
            Some("CI010")
        );
        assert_eq!(
            z.stage.exit_codes.as_deref(),
            Some(&[0, 10, 11, 12, 13, 14][..])
        );
        let r = bind(&stage("ruff")).expect("ruff");
        assert_eq!(
            (r.stage.command.as_str(), r.stage.parser),
            ("ruff", ToolParser::RuffJson)
        );
        assert!(bind(&stage("nope")).is_err());
    }

    // frob:tests crates/gob-check/src/tool_bind.rs::command_args
    #[test]
    fn the_variant_matching_the_version_is_used() {
        let r = bind(&stage("ruff")).expect("ruff");
        let old = command_args(&r, Some("0.0.291")).expect("old");
        assert_eq!(old[1], "--format");
        let new = command_args(&r, Some("0.8.6")).expect("new");
        assert_eq!(new[1], "--output-format");
        assert!(command_args(&r, None).is_err());
    }

    // frob:tests crates/gob-check/src/tool_bind.rs::command_args
    #[test]
    fn stage_args_beat_variants() {
        let mut s = stage("ruff");
        s.args = vec!["x".to_owned()];
        let r = bind(&s).expect("ruff");
        assert_eq!(command_args(&r, Some("0.8.6")).expect("args"), ["x"]);
    }

    // frob:tests crates/gob-check/src/tool_bind.rs::cache_key
    #[test]
    fn the_key_changes_with_version_and_config() {
        let dir = tempfile::tempdir().expect("tmp");
        let r = bind(&stage("ruff")).expect("ruff");
        let a = cache_key(dir.path(), r.def.as_ref(), Some("1.0.0"));
        assert_ne!(a, cache_key(dir.path(), r.def.as_ref(), Some("1.0.1")));
        std::fs::write(dir.path().join("ruff.toml"), "line-length = 100").expect("write");
        assert_ne!(a, cache_key(dir.path(), r.def.as_ref(), Some("1.0.0")));
    }

    // frob:tests crates/gob-check/src/tool_bind.rs::project_tool
    #[test]
    fn project_bin_dirs_are_searched() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(project_tool(dir.path(), "oxlint").is_none());
        let bin = dir.path().join("node_modules/.bin");
        std::fs::create_dir_all(&bin).expect("mkdir");
        std::fs::write(bin.join("oxlint"), "").expect("write");
        assert_eq!(project_tool(dir.path(), "oxlint"), Some(bin.join("oxlint")));
    }
}
