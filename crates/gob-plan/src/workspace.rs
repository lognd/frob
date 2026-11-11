//! A multi-file input as one model: every file's term is grafted under a workspace root and the
//! file texts are joined, so the single-model executor sees all files at once. Shared by the
//! example runner and by hosts (crunk) that run a GRL rule over a whole project.
//!
//! Each grafted file root carries the [`PATH_ATTR`](crate::exec::PATH_ATTR) attribute (its repository path)
//! plus any per-file attributes the caller supplies (crunk's `file.bucket`, `file.component`,
//! `file.outside_css_root`); the workspace root carries [`WORKSPACE_ATTR`](crate::exec::WORKSPACE_ATTR).
//! The `file` kind and `.file.path` read those attributes.

// frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
// frob:ticket 01M71T80ZZPW5Z00CKF3ANQ2X3
use gob_ir::{Location, Model, NodeId, NodeSpec, TermBuilder, TermError};
use gob_text::{TextRange, TextSize};

use crate::exec::{PATH_ATTR, WORKSPACE_ATTR};

/// Why a workspace could not be built.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum WorkspaceError {
    /// A file did not fold, the graft was ill-formed, or no file was given.
    #[error("{0}")]
    Model(String),
}

/// One file of a workspace: its repository path, text and the attributes stamped on its root.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct WorkspaceFile {
    /// The repository path, carried as [`PATH_ATTR`].
    pub path: String,
    /// The file text.
    pub text: String,
    /// Extra `(name, value)` string attributes stamped on the file root.
    pub attrs: Vec<(String, String)>,
}

impl WorkspaceFile {
    /// A file with no extra attributes.
    pub fn new(path: impl Into<String>, text: impl Into<String>) -> Self {
        Self {
            path: path.into(),
            text: text.into(),
            attrs: Vec::new(),
        }
    }
}

/// The joined model of a multi-file input.
pub struct Workspace {
    /// The workspace model.
    pub model: Model,
    /// The files' texts joined by newlines, the text of every node's byte range.
    pub text: String,
    /// The 1-based line of the joined text on which each file starts, in input order.
    pub start_lines: Vec<u32>,
    /// The byte offset of the joined text at which each file starts, in input order.
    pub start_offsets: Vec<u32>,
}

impl Workspace {
    /// The index of the file holding the 1-based `line` of the joined text, and its local line.
    pub fn locate(&self, line: u32) -> (usize, u32) {
        let i = self
            .start_lines
            .iter()
            .rposition(|&s| s <= line)
            .unwrap_or(0);
        (i, line - self.start_lines[i] + 1)
    }

    /// The index of the file holding byte `offset` of the joined text, and its local offset.
    pub fn locate_offset(&self, offset: u32) -> (usize, u32) {
        let i = self
            .start_offsets
            .iter()
            .rposition(|&s| s <= offset)
            .unwrap_or(0);
        (i, offset - self.start_offsets[i])
    }
}

fn shift(range: TextRange, by: u32) -> TextRange {
    let (s, e) = (u32::from(range.start()), u32::from(range.end()));
    TextRange::new(TextSize::from(s + by), TextSize::from(e + by))
}

fn shifted(loc: &Location, by: u32) -> Location {
    match loc {
        Location::Text { file, range } => Location::Text {
            file: *file,
            range: shift(*range, by),
        },
        Location::Notebook { nb, cell, range } => Location::Notebook {
            nb: *nb,
            cell: *cell,
            range: shift(*range, by),
        },
        other => other.clone(),
    }
}

/// Copies the subtree of `node` of `from` into `b`, shifting text ranges by `by`.
fn graft(
    b: &mut TermBuilder,
    from: &gob_ir::Term,
    node: NodeId,
    by: u32,
    root: Option<(&str, &[(String, String)])>,
) -> Result<NodeId, TermError> {
    let n = from.node(node);
    let kids = n
        .children()
        .iter()
        .map(|&c| graft(b, from, c, by, None))
        .collect::<Result<Vec<_>, _>>()?;
    let binders: Vec<&str> = n.binders().iter().map(String::as_str).collect();
    let mut spec = NodeSpec::new(n.op().clone(), shifted(n.location(), by))
        .binders(&binders)
        .lang(n.lang());
    if let Some(name) = n.name() {
        spec = spec.named(name);
    }
    if let Some(p) = n.lang_param() {
        spec = spec.lang_param(p);
    }
    for (k, v) in n.attrs().iter() {
        spec = spec.attr(k, v.clone());
    }
    if let Some((path, attrs)) = root {
        spec = spec.attr(PATH_ATTR, path);
        for (k, v) in attrs {
            spec = spec.attr(k, v.as_str());
        }
    }
    b.node(spec, &kids)
}

/// Joins `files`, each folded by `model_of`, into one model with per-file attributes stamped.
///
/// # Errors
/// [`WorkspaceError::Model`] when a file does not fold, the graft is ill-formed or `files` is empty.
pub fn build<E: std::fmt::Display>(
    files: &[WorkspaceFile],
    model_of: impl Fn(&str, &str) -> Result<Model, E>,
) -> Result<Workspace, WorkspaceError> {
    let bad = |e: &dyn std::fmt::Display| WorkspaceError::Model(e.to_string());
    let mut text = String::new();
    let mut start_lines = Vec::new();
    let mut start_offsets = Vec::new();
    let mut b: Option<TermBuilder> = None;
    let mut roots = Vec::new();
    let mut first: Option<NodeSpec> = None;
    for WorkspaceFile {
        path,
        text: body,
        attrs,
    } in files
    {
        let by = u32::try_from(text.len()).map_err(|e| bad(&e))?;
        start_offsets.push(by);
        let line = 1 + u32::try_from(text.matches('\n').count()).map_err(|e| bad(&e))?;
        start_lines.push(line);
        // Each file is newline-terminated (a markdown heading on the last line needs it to fold
        // as a section), so the joined text holds every range of every file.
        let terminated = if body.ends_with('\n') {
            body.clone()
        } else {
            format!("{body}\n")
        };
        text.push_str(&terminated);
        let model = model_of(path, &terminated).map_err(|e| bad(&e))?;
        let term = model.term();
        let builder = b.get_or_insert_with(|| TermBuilder::new("", term.node(term.root()).lang()));
        if first.is_none() {
            let r = term.node(term.root());
            first = Some(NodeSpec::new(r.op().clone(), r.location().clone()));
        }
        roots
            .push(graft(builder, term, term.root(), by, Some((path, attrs))).map_err(|e| bad(&e))?);
    }
    let (Some(mut b), Some(spec)) = (b, first) else {
        return Err(WorkspaceError::Model(
            "a workspace needs at least one file".to_owned(),
        ));
    };
    let root = b
        .node(spec.attr(WORKSPACE_ATTR, true), &roots)
        .map_err(|e| bad(&e))?;
    let term = b.finish(root).map_err(|e| bad(&e))?;
    tracing::debug!(
        files = files.len(),
        nodes = term.len(),
        "example workspace built"
    );
    Ok(Workspace {
        model: Model::new(term, gob_ir::ScopeGraph::new()),
        text,
        start_lines,
        start_offsets,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-plan/src/workspace.rs::build
    // frob:tests crates/gob-plan/src/workspace.rs::Workspace.locate
    #[test]
    fn files_graft_under_one_root_and_lines_map_back() {
        let files = vec![
            WorkspaceFile::new("a.md", "See [b](b.md)."),
            WorkspaceFile::new("b.md", "# Intro"),
        ];
        let ws = build(&files, gob_symbols::model_of_source_at).expect("builds");
        let term = ws.model.term();
        assert!(term.node(term.root()).attrs().get(WORKSPACE_ATTR).is_some());
        let paths: Vec<_> = term
            .descendants(term.root())
            .into_iter()
            .filter_map(|n| term.node(n).attrs().get_str(PATH_ATTR).map(str::to_owned))
            .collect();
        assert_eq!(paths, ["a.md", "b.md"]);
        assert_eq!(ws.locate(1), (0, 1));
        assert_eq!(ws.locate(2), (1, 1));
        assert_eq!(ws.locate_offset(0), (0, 0));
        assert_eq!(ws.locate_offset(16), (1, 1));
    }

    // frob:tests crates/gob-plan/src/workspace.rs::build
    #[test]
    fn extra_attributes_are_stamped_on_the_file_root() {
        let mut file = WorkspaceFile::new("a.md", "# A");
        file.attrs
            .push(("file.bucket".to_owned(), "components".to_owned()));
        let ws = build(&[file], gob_symbols::model_of_source_at).expect("builds");
        let term = ws.model.term();
        let stamped: Vec<_> = term
            .descendants(term.root())
            .into_iter()
            .filter_map(|n| {
                term.node(n)
                    .attrs()
                    .get_str("file.bucket")
                    .map(str::to_owned)
            })
            .collect();
        assert_eq!(stamped, ["components"]);
    }
}
