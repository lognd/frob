//! Discovery and loading of authored HTML scene documents (`*.scene.html`).
//!
//! [`load_scene_docs`] walks a project's scenes directory (ignore files honored, nested
//! directories included), reads each `.scene.html` file and parses it through
//! [`crunk_scene::parse_scene_bytes`]. A file that cannot be read, is too large, is not UTF-8,
//! has no elements or does not parse becomes a [`SceneDocProblem`], never a panic, so the caller can report it
//! as a finding. Output order is the byte order of the project-relative path.

// frob:ticket 01M5H30AT7FM2BAXCTTDEGWV6J

use std::collections::BTreeMap;
use std::path::Path;

use crunk_scene::{SceneDoc, SceneError, parse_scene_bytes};
use gob_walk::{WalkConfig, walk_paths};

use crate::walk::posix;

/// The file suffix that marks an HTML scene document, matched case-insensitively.
pub const SCENE_DOC_SUFFIX: &str = ".scene.html";

/// One scene document that was read and parsed.
#[derive(Debug, Clone)]
pub struct LoadedSceneDoc {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed scene.
    pub doc: SceneDoc,
}

/// Why a discovered scene document is a problem.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SceneDocProblemKind {
    /// The file could not be read.
    Unreadable,
    /// The file is larger than the walk's size cap and was not read.
    TooLarge,
    /// The bytes are not UTF-8.
    NotUtf8,
    /// The scene reader failed on the text (a reader bug, not bad markup).
    Unparsable,
    /// Another document already took this scene name (file name without the suffix).
    DuplicateName,
    /// The file holds no elements (empty, blank or comments only); it loads as an empty document.
    Empty,
}

/// A scene document that could not be loaded, or that clashes with another.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SceneDocProblem {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// What went wrong.
    pub kind: SceneDocProblemKind,
    /// A one-line human reason.
    pub message: String,
}

/// Everything discovery found under the scenes directory.
#[derive(Debug, Clone, Default)]
pub struct SceneDocLoad {
    /// The documents that parsed, in path order.
    pub docs: Vec<LoadedSceneDoc>,
    /// The documents that did not load (and duplicate names), in path order.
    pub problems: Vec<SceneDocProblem>,
}

/// Whether `path` names a scene document: its file name ends in `.scene.html`, any case.
pub fn is_scene_doc_path(path: &str) -> bool {
    let name = file_name(path);
    name.len() > SCENE_DOC_SUFFIX.len() && name.to_ascii_lowercase().ends_with(SCENE_DOC_SUFFIX)
}

/// The last component of a root-relative path.
fn file_name(path: &str) -> &str {
    Path::new(path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or(path)
}

/// The scene name of `path`: the file name without the suffix, lowercased.
fn scene_name(path: &str) -> String {
    let name = file_name(path).to_ascii_lowercase();
    name.strip_suffix(SCENE_DOC_SUFFIX)
        .unwrap_or(&name)
        .to_owned()
}

fn problem(path: &str, kind: SceneDocProblemKind, message: String) -> SceneDocProblem {
    tracing::warn!(path, ?kind, %message, "scene document problem");
    SceneDocProblem {
        path: path.to_owned(),
        kind,
        message,
    }
}

/// Load every `.scene.html` under `<root>/<scenes_dir>`.
///
/// A missing or unwalkable directory gives an empty load. Each file is read once and parsed
/// with [`parse_scene_bytes`]; failures land in [`SceneDocLoad::problems`]. A second file with
/// the same scene name is still loaded but also reported as a duplicate.
pub fn load_scene_docs(root: &Path, scenes_dir: &str) -> SceneDocLoad {
    let dir = root.join(scenes_dir);
    let walked = match walk_paths(&dir, &WalkConfig::default()) {
        Ok(w) => w,
        Err(err) => {
            tracing::debug!(dir = scenes_dir, %err, "scene discovery: nothing to walk");
            return SceneDocLoad::default();
        }
    };
    let rooted = |rel: &str| posix(&Path::new(scenes_dir).join(rel));
    let mut load = SceneDocLoad::default();
    for big in walked
        .oversized
        .iter()
        .filter(|o| is_scene_doc_path(&o.path))
    {
        let path = rooted(&big.path);
        let message = format!("scene is {} bytes, over the size cap", big.size);
        load.problems
            .push(problem(&path, SceneDocProblemKind::TooLarge, message));
    }
    let mut names: BTreeMap<String, String> = BTreeMap::new();
    for entry in walked.files.iter().filter(|e| is_scene_doc_path(&e.path)) {
        let path = rooted(&entry.path);
        let bytes = match std::fs::read(dir.join(&entry.path)) {
            Ok(b) => b,
            Err(err) => {
                load.problems.push(problem(
                    &path,
                    SceneDocProblemKind::Unreadable,
                    format!("cannot read scene: {err}"),
                ));
                continue;
            }
        };
        let parsed = parse_scene_bytes(&bytes);
        let doc = match parsed {
            Ok(doc) => doc,
            Err(err) => {
                let kind = match err {
                    SceneError::NotUtf8 { .. } => SceneDocProblemKind::NotUtf8,
                    SceneError::Fold(_) => SceneDocProblemKind::Unparsable,
                };
                load.problems.push(problem(&path, kind, err.to_string()));
                continue;
            }
        };
        let Ok(text) = String::from_utf8(bytes) else {
            // parse_scene_bytes already accepted these bytes as UTF-8.
            continue;
        };
        if let Some(first) = names.get(&scene_name(&path)) {
            let message = format!("scene name already used by {first}");
            load.problems
                .push(problem(&path, SceneDocProblemKind::DuplicateName, message));
        } else {
            names.insert(scene_name(&path), path.clone());
        }
        if doc.elements.is_empty() {
            load.problems.push(problem(
                &path,
                SceneDocProblemKind::Empty,
                "scene document has no elements".to_owned(),
            ));
        }
        tracing::debug!(path = %path, elements = doc.elements.len(), "scene document parsed");
        load.docs.push(LoadedSceneDoc { path, text, doc });
    }
    load.problems.sort_by(|a, b| a.path.cmp(&b.path));
    tracing::info!(
        docs = load.docs.len(),
        problems = load.problems.len(),
        "scene discovery complete"
    );
    load
}
