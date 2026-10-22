//! The authored scene documents (`design/scenes/*.scene.html`) as the SCENE rules read them: each
//! parsed through the scene dialect reader, with its text kept so findings can anchor.

// frob:ticket 01M5H30AMSB0THE4GW322D4K54

use crunk_scene::{SceneDoc, parse_scene_html};
use crunk_spec::DesignSpec;

use crate::sheets::site_path;

/// The project directory holding the authored scene files, relative to the root.
pub const SCENES_DIR: &str = "design/scenes";

/// The file suffix that marks an HTML scene document.
pub const SCENE_DOC_SUFFIX: &str = ".scene.html";

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

/// Every scene document of a project that parsed, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct SceneDocFacts {
    /// The files, in path order.
    pub files: Vec<SceneDocFile>,
}

impl SceneDocFacts {
    /// Read and parse `<root>/design/scenes/*.scene.html`; a missing directory gives no files and
    /// an unreadable or unparsable file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(SCENES_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    p.file_name()
                        .is_some_and(|n| n.to_string_lossy().ends_with(SCENE_DOC_SUFFIX))
                })
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<SceneDocFile> = paths
            .into_iter()
            .filter_map(|path| {
                let rel = site_path(spec, &path);
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %rel, %err, "scene document unreadable; skipped");
                    })
                    .ok()?;
                let doc = parse_scene_html(&text)
                    .inspect_err(|err| tracing::warn!(path = %rel, %err, "scene does not parse; skipped"))
                    .ok()?;
                tracing::debug!(path = %rel, elements = doc.elements.len(), "scene document parsed");
                Some(SceneDocFile {
                    path: rel,
                    text,
                    doc,
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
