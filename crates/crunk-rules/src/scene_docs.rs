//! The authored scene documents (`design/scenes/*.scene.html`) as the SCENE rules read them: each
//! parsed through the scene dialect reader, with its text kept so findings can anchor.

// frob:ticket 01M5H30AMSB0THE4GW322D4K54

use crunk_ingest::scene::{SceneDocProblem, load_scene_docs};
use crunk_scene::SceneDoc;
use crunk_spec::DesignSpec;

pub use crunk_ingest::scene::SCENE_DOC_SUFFIX;

/// The project directory holding the authored scene files, relative to the root.
pub const SCENES_DIR: &str = "design/scenes";

/// One scene document that parsed.
#[derive(Debug, Clone)]
pub struct SceneDocFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed scene.
    pub doc: SceneDoc,
}

impl SceneDocFile {
    /// A label for the element that holds byte `offset`: its `data-id`, else its tag, else the
    /// scene itself (the nearest start tag at or before the offset).
    pub fn element_label(&self, offset: usize) -> String {
        let holder = self.doc.elements.iter().rfind(|e| e.offset <= offset);
        match holder {
            Some(e) => match &e.data_id {
                Some(id) => format!("data-id '{id}'"),
                None => format!("<{}>", e.tag),
            },
            None => "the scene".to_owned(),
        }
    }
}

impl SceneDocFile {
    // frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM
    /// The gamepad focus graph of this scene (the GX focus rules' input).
    pub fn focus_graph(&self) -> crunk_layout::FocusGraph {
        crunk_layout::FocusGraph::from_scene(&self.doc)
    }
}

/// Every scene document of a project that parsed, sorted by path, and those that did not.
#[derive(Debug, Clone, Default)]
pub struct SceneDocFacts {
    /// The files, in path order.
    pub files: Vec<SceneDocFile>,
    /// The documents that did not load, and duplicate scene names, in path order.
    pub problems: Vec<SceneDocProblem>,
}

impl SceneDocFacts {
    /// Discover and parse `<root>/design/scenes/**/*.scene.html` through `crunk-ingest`; a missing
    /// directory gives no files, and a file that does not load becomes a [`SceneDocProblem`].
    pub fn load(spec: &DesignSpec) -> Self {
        let loaded = load_scene_docs(&spec.root, SCENES_DIR);
        let files = loaded
            .docs
            .into_iter()
            .map(|d| SceneDocFile {
                path: d.path,
                text: d.text,
                doc: d.doc,
            })
            .collect();
        Self {
            files,
            problems: loaded.problems,
        }
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
        for problem in &self.problems {
            hasher.update(problem.path.as_bytes());
            hasher.update(b"\0");
            hasher.update(problem.message.as_bytes());
            hasher.update(b"\0");
        }
        hasher.finalize().to_hex().to_string()
    }
}
