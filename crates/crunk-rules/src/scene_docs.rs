//! The authored scene documents (`design/scenes/*.scene.html`) as the SCENE rules read them: each
//! parsed through the scene dialect reader, with its text kept so findings can anchor.

// frob:ticket 01M5H30AMSB0THE4GW322D4K54

use crunk_ingest::scene::{SceneDocProblem, load_scene_docs};
use std::sync::OnceLock;

use crunk_layout::output::LayoutSolve;
use crunk_layout::solve::solve_scene_html;
use crunk_layout::style::TokenMap;
use crunk_layout::text::TextMeasurer;
use crunk_scene::SceneDoc;
use crunk_spec::DesignSpec;
use crunk_tokens::TokenSet;

pub use crunk_ingest::scene::SCENE_DOC_SUFFIX;

/// The project directory holding the authored scene files, relative to the root.
pub const SCENES_DIR: &str = "design/scenes";

// frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
/// The spec's tokens as the solver's `var()` map (as `crunk render` builds it); empty, with a
/// warning, when the token set cannot be built (TOKENS rules report that).
fn token_map(spec: &DesignSpec) -> TokenMap {
    match TokenSet::from_spec(spec) {
        Ok(set) => TokenMap::from_pairs(
            set.css_entries()
                .into_iter()
                .map(|(name, value)| (name.to_owned(), value)),
        ),
        Err(e) => {
            tracing::warn!(error = %e, "token set cannot be built; scenes solve with no tokens");
            TokenMap::new()
        }
    }
}

/// One scene document that parsed.
#[derive(Debug, Clone)]
pub struct SceneDocFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The parsed scene.
    pub doc: SceneDoc,
    /// The T1 layout solve, computed on first use.
    solved: OnceLock<Result<LayoutSolve, String>>,
    /// The spec's design tokens, so `var(--token)` in scene styles resolves as `crunk render` does.
    tokens: TokenMap,
}

/// The viewport the SLOP layout tells solve at: a desktop width, where card rows and section
/// bands show.
pub const SOLVE_VIEWPORT: (f32, f32) = (1280.0, 800.0);

impl SceneDocFile {
    /// A scene file whose layout solve has not run yet.
    pub fn new(path: String, text: String, doc: SceneDoc) -> Self {
        Self {
            path,
            text,
            doc,
            solved: OnceLock::new(),
            tokens: TokenMap::new(),
        }
    }

    // frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
    /// This file with `tokens` as the map its solves resolve `var()` against.
    #[must_use]
    pub fn with_tokens(mut self, tokens: TokenMap) -> Self {
        self.tokens = tokens;
        self
    }

    // frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP
    // frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
    /// The T1 layout solve at [`SOLVE_VIEWPORT`] with the spec's tokens; `Err` carries why the
    /// scene does not solve (a missing `data-id`, an undefined `var()`), which geometry rules
    /// must report as Unresolved rather than pass.
    pub fn solve(&self) -> Result<&LayoutSolve, &str> {
        self.solved
            .get_or_init(|| self.solve_at(SOLVE_VIEWPORT))
            .as_ref()
            .map_err(String::as_str)
    }

    // frob:ticket 01M6Z2SXMWBKP1SS1NPE0MT1GQ
    // frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
    /// A fresh T1 layout solve at `viewport` (width, height) with the spec's tokens, uncached;
    /// `Err` carries why the scene does not solve. RESP001 solves each scene at every breakpoint.
    pub fn solve_at(&self, viewport: (f32, f32)) -> Result<LayoutSolve, String> {
        let mut fonts = TextMeasurer::new();
        match solve_scene_html(&self.doc, &self.tokens, viewport, &mut fonts) {
            Ok(solved) => Ok(solved.doc),
            Err(e) => {
                tracing::debug!(path = %self.path, ?viewport, error = %e, "scene does not solve at T1");
                Err(e.to_string())
            }
        }
    }

    // frob:ticket 01M7AV3827P32YDAGDXDVS8CWV
    /// The Unresolved message for a geometry rule when `why` stopped this scene from solving.
    pub fn unsolved_message(why: &str) -> String {
        format!("scene does not solve at T1, so its layout cannot be judged: {why}")
    }
}

impl SceneDocFile {
    // frob:ticket 01M6Z15WBQCQDYSHC0HSXJJYWH
    /// Byte offset of the element whose `data-id` is `id`, so a finding anchors on it; 0 when the
    /// scene has no such element.
    pub fn offset_of(&self, id: &str) -> usize {
        self.doc
            .elements
            .iter()
            .find(|e| e.data_id.as_deref() == Some(id))
            .map_or(0, |e| e.offset)
    }

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
        let tokens = token_map(spec);
        let files = loaded
            .docs
            .into_iter()
            .map(|d| SceneDocFile::new(d.path, d.text, d.doc).with_tokens(tokens.clone()))
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
