//! The authored flow files (`design/flows/*.flow.toml`) as the GX rules read them: each parsed
//! into a [`FlowFile`], reduced to the screen-to-screen transitions the focus atlas joins scenes by.

// frob:ticket 01M5HA924E3PTBVH6J8EBXP7XW

use crunk_spec::{DesignSpec, FlowFile, parse_flow_file};

use crate::file_problem::DesignFileProblem;
use crate::sheets::site_path;

/// The project directory holding the authored flow files, relative to the root.
pub const FLOWS_DIR: &str = "design/flows";

/// The file suffix that marks a flow file.
pub const FLOW_SUFFIX: &str = ".flow.toml";

/// Every authored flow file of a project that parsed, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct FlowFacts {
    /// The parsed flows with their project-relative paths, in path order.
    pub files: Vec<(String, FlowFile)>,
    /// The files that could not be read or parsed, in path order.
    pub problems: Vec<DesignFileProblem>,
}

/// The screen id of a flow node `screen:state`.
#[must_use]
pub fn screen_of(node: &str) -> &str {
    node.split_once(':').map_or(node, |(screen, _)| screen)
}

impl FlowFacts {
    /// Read and parse `<root>/design/flows/*.flow.toml`; a missing directory gives no files, and an
    /// unreadable or invalid file becomes a [`DesignFileProblem`].
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(FLOWS_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    p.file_name()
                        .is_some_and(|n| n.to_string_lossy().ends_with(FLOW_SUFFIX))
                })
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let mut facts = Self::default();
        for path in paths {
            let rel = site_path(spec, &path);
            let text = match std::fs::read_to_string(&path) {
                Ok(text) => text,
                Err(err) => {
                    facts
                        .problems
                        .push(DesignFileProblem::new(&rel, "flow file unreadable", &err));
                    continue;
                }
            };
            match parse_flow_file(&text) {
                Ok(flow) => {
                    tracing::debug!(path = %rel, edges = flow.edges.len(), "flow file loaded");
                    facts.files.push((rel, flow));
                }
                Err(err) => {
                    facts
                        .problems
                        .push(DesignFileProblem::new(&rel, "flow file invalid", &err))
                }
            }
        }
        facts
    }

    /// Every transition between two different screens, as (from screen id, to screen id) pairs in
    /// file then edge order; moves between states of one screen are not scene-to-scene.
    #[must_use]
    pub fn transitions(&self) -> Vec<(String, String)> {
        self.files
            .iter()
            .flat_map(|(_, flow)| &flow.edges)
            .map(|e| (screen_of(&e.from), screen_of(&e.to)))
            .filter(|(from, to)| from != to)
            .map(|(from, to)| (from.to_owned(), to.to_owned()))
            .collect()
    }
}
