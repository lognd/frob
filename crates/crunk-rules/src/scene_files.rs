//! The authored scene files (`design/scenes/*.scene.json`) as the LAYOUT and RESP rules read them:
//! each parsed and solved at T1 (the deterministic layout engine of `crunk-ingest`), with its text
//! kept so findings can anchor.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use crunk_ingest::scene::{
    LayoutSolve, NodeKind, Scene, SceneNode, SolvedNode, parse_scene, solve_scene,
};
use crunk_spec::DesignSpec;

use crate::sheets::site_path;

/// The project directory holding the authored scene files, relative to the root.
pub const SCENES_DIR: &str = "design/scenes";

/// The file suffix that marks a scene file.
pub const SCENE_SUFFIX: &str = ".scene.json";

/// One scene file that parsed and solved.
#[derive(Debug, Clone)]
pub struct SceneFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed scene (viewport, safe area, interactive flags).
    pub scene: Scene,
    /// The solved absolute rectangles, preorder.
    pub solve: LayoutSolve,
}

impl SceneFile {
    /// The solved node with `id`, if the scene has one.
    pub fn solved(&self, id: &str) -> Option<&SolvedNode> {
        self.solve.nodes.iter().find(|n| n.id == id)
    }

    /// Whether the scene node `id` is flagged interactive.
    pub fn is_interactive(&self, id: &str) -> bool {
        fn find<'a>(node: &'a SceneNode, id: &str) -> Option<&'a SceneNode> {
            if node.id == id {
                return Some(node);
            }
            node.children.iter().find_map(|c| find(c, id))
        }
        find(&self.scene.root, id).is_some_and(|n| n.interactive)
    }

    /// Whether the solved node `n` is a text run or an interactive target (what the safe area
    /// protects).
    pub fn is_content(&self, n: &SolvedNode) -> bool {
        n.kind == NodeKind::Text || self.is_interactive(&n.id)
    }

    /// Byte offset of the node `id` in the file text (its `"id"` literal), so a finding anchors on
    /// the node; 0 when the literal cannot be found.
    pub fn offset_of(&self, id: &str) -> usize {
        self.text.find(&format!("\"{id}\"")).unwrap_or(0)
    }
}

/// Every authored scene file of a project that parsed and solved, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct SceneFacts {
    /// The files, in path order.
    pub files: Vec<SceneFile>,
}

impl SceneFacts {
    /// Read, parse and solve `<root>/design/scenes/*.scene.json`; a missing directory gives no
    /// files, and an unreadable, unparsable or unsolvable file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(SCENES_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    p.file_name()
                        .is_some_and(|n| n.to_string_lossy().ends_with(SCENE_SUFFIX))
                })
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<SceneFile> = paths
            .into_iter()
            .filter_map(|path| {
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %path.display(), %err, "scene file unreadable; skipped");
                    })
                    .ok()?;
                let rel = site_path(spec, &path);
                let scene = parse_scene(&text)
                    .inspect_err(|err| tracing::warn!(path = %rel, %err, "scene does not parse; skipped"))
                    .ok()?;
                let solve = solve_scene(&scene)
                    .inspect_err(|err| tracing::warn!(path = %rel, %err, "scene does not solve; skipped"))
                    .ok()?;
                tracing::debug!(path = %rel, nodes = solve.nodes.len(), "scene solved");
                Some(SceneFile {
                    path: rel,
                    text,
                    scene,
                    solve,
                })
            })
            .collect();
        Self { files }
    }

    /// A stable digest of the files' paths and texts, for the repo digest.
    pub fn fingerprint(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        for file in &self.files {
            hasher.update(file.path.as_bytes());
            hasher.update(b"\0");
            hasher.update(file.text.as_bytes());
            hasher.update(b"\0");
        }
        hasher.finalize().to_hex().to_string()
    }
}

/// The overlap tolerance in pixels: solved rectangles are whole pixels, so touching edges and
/// sub-pixel slivers are not an overlap.
pub const EPSILON: f32 = 0.5;

/// The rectangle `(left, top, right, bottom)` of a solved node.
pub fn rect(n: &SolvedNode) -> (f32, f32, f32, f32) {
    (n.x, n.y, n.x + n.width, n.y + n.height)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn file(text: &str) -> SceneFile {
        let scene = parse_scene(text).expect("parses");
        let solve = solve_scene(&scene).expect("solves");
        SceneFile {
            path: "design/scenes/a.scene.json".into(),
            text: text.into(),
            scene,
            solve,
        }
    }

    const TEXT: &str = r#"{"viewport":{"width":100,"height":100},"root":{"id":"r","kind":"box",
        "style":{"width":100,"height":100},
        "children":[{"id":"btn","kind":"box","interactive":true,"style":{"width":10,"height":10}}]}}"#;

    // frob:tests crates/crunk-rules/src/scene_files.rs::SceneFile.is_interactive
    // frob:tests crates/crunk-rules/src/scene_files.rs::SceneFile.solved
    // frob:tests crates/crunk-rules/src/scene_files.rs::SceneFile.offset_of
    #[test]
    fn finds_interactive_nodes_and_offsets() {
        let f = file(TEXT);
        assert!(f.is_interactive("btn"));
        assert!(!f.is_interactive("r"));
        assert_eq!(f.solved("btn").map(|n| n.width), Some(10.0));
        assert!(f.offset_of("btn") > 0);
        assert_eq!(f.offset_of("missing"), 0);
    }

    // frob:tests crates/crunk-rules/src/scene_files.rs::SceneFacts.fingerprint
    #[test]
    fn fingerprint_tracks_content() {
        let a = SceneFacts {
            files: vec![file(TEXT)],
        };
        let b = SceneFacts { files: vec![] };
        assert_ne!(a.fingerprint(), b.fingerprint());
        assert_eq!(a.fingerprint(), a.fingerprint());
    }
}
