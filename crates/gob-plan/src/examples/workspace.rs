//! A multi-file example as one model: every file's term is grafted under a workspace root and the
//! file texts are joined, so the single-model executor sees all files of the example at once.
//!
//! Each grafted file root carries the [`PATH_ATTR`](crate::exec::PATH_ATTR) attribute (its repository path); the workspace
//! root carries [`WORKSPACE_ATTR`](crate::exec::WORKSPACE_ATTR). The `file` kind and `.file.path` read those attributes.

// frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
use gob_ir::{Location, Model, NodeId, NodeSpec, TermBuilder, TermError};
use gob_text::{TextRange, TextSize};

use super::runner::RunError;
use crate::exec::{PATH_ATTR, WORKSPACE_ATTR};

/// The joined model of a multi-file example.
pub(crate) struct Workspace {
    /// The workspace model.
    pub(crate) model: Model,
    /// The files' texts joined by newlines, the text of every node's byte range.
    pub(crate) text: String,
    /// The 1-based line of the joined text on which each file starts, in input order.
    pub(crate) start_lines: Vec<u32>,
}

impl Workspace {
    /// The index of the file holding the 1-based `line` of the joined text, and its local line.
    pub(crate) fn locate(&self, line: u32) -> (usize, u32) {
        let i = self
            .start_lines
            .iter()
            .rposition(|&s| s <= line)
            .unwrap_or(0);
        (i, line - self.start_lines[i] + 1)
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
    path: Option<&str>,
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
    if let Some(p) = path {
        spec = spec.attr(PATH_ATTR, p);
    }
    b.node(spec, &kids)
}

/// Joins the `(path, text)` files of an example, each folded by `model_of`, into one model.
///
/// # Errors
/// [`RunError::Model`] when a file does not fold or the graft is ill-formed.
pub(crate) fn build<E: std::fmt::Display>(
    files: &[(String, String)],
    model_of: impl Fn(&str, &str) -> Result<Model, E>,
) -> Result<Workspace, RunError> {
    let bad = |e: &dyn std::fmt::Display| RunError::Model(e.to_string());
    let mut text = String::new();
    let mut start_lines = Vec::new();
    let mut b: Option<TermBuilder> = None;
    let mut roots = Vec::new();
    let mut first: Option<NodeSpec> = None;
    for (path, body) in files {
        let by = u32::try_from(text.len()).map_err(|e| bad(&e))?;
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
        roots.push(graft(builder, term, term.root(), by, Some(path)).map_err(|e| bad(&e))?);
    }
    let (Some(mut b), Some(spec)) = (b, first) else {
        return Err(RunError::Model(
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
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-plan/src/examples/workspace.rs::build
    // frob:tests crates/gob-plan/src/examples/workspace.rs::Workspace::locate
    #[test]
    fn files_graft_under_one_root_and_lines_map_back() {
        let files = vec![
            ("a.md".to_owned(), "See [b](b.md).".to_owned()),
            ("b.md".to_owned(), "# Intro".to_owned()),
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
    }
}
