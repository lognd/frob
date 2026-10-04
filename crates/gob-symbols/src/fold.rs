//! Shared fold helpers: the term-building context and the F0 folds (adapter-less
//! files and files whose parse failed outright).

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use gob_ir::{
    DeclKind, Location, NodeId, NodeSpec, Operator, Resolution, ScopeGraph, TermBuilder, TermError,
};
use gob_languages::UnresolvedReason;
use gob_text::FileInterner;

use crate::adapter::{Fidelity, FileInput, FoldError, Folded, ParseStatus};
use crate::model::{FileSymbols, LocalBinding, collapse_ws};
use crate::view::{self, Naming};

/// The context of one fold: the term builder, the file id and the source text.
pub(crate) struct Cx<'a> {
    /// The term under construction.
    pub b: TermBuilder,
    /// The interned id of the artifact, for locations.
    pub file: gob_text::FileId,
    /// The source text (empty for adapter-less files).
    pub text: &'a str,
}

impl<'a> Cx<'a> {
    /// A context for `path` whose default language tag is `lang`.
    pub fn new(path: &str, lang: &str, text: &'a str) -> Self {
        let mut files = FileInterner::new();
        let file = files.intern(path);
        Self {
            b: TermBuilder::new(path, lang),
            file,
            text,
        }
    }

    /// A text location from byte offsets.
    pub fn loc(&self, start: usize, end: usize) -> Location {
        let clamp = |n: usize| u32::try_from(n).unwrap_or(u32::MAX);
        Location::text(self.file, clamp(start), clamp(end.max(start)))
    }

    /// The location of a tree-sitter node.
    pub fn node_loc(&self, n: tree_sitter::Node<'_>) -> Location {
        self.loc(n.start_byte(), n.end_byte())
    }

    /// Adds a node built from `spec` over `children`.
    pub fn add(&mut self, spec: NodeSpec, children: &[NodeId]) -> Result<NodeId, TermError> {
        self.b.node(spec, children)
    }

    /// Adds a node with `op` located at `n`.
    pub fn op(
        &mut self,
        op: Operator,
        n: tree_sitter::Node<'_>,
        children: &[NodeId],
    ) -> Result<NodeId, TermError> {
        let spec = NodeSpec::new(op, self.node_loc(n));
        self.b.node(spec, children)
    }

    /// Adds a literal leaf located at `n`.
    pub fn lit(
        &mut self,
        kind: &str,
        text: &str,
        n: tree_sitter::Node<'_>,
    ) -> Result<NodeId, TermError> {
        self.op(Operator::lit(kind, text), n, &[])
    }
}

/// The skeleton of a [`FileSymbols`] for `input`.
pub(crate) fn base_file(input: &FileInput<'_>, language: &str) -> FileSymbols {
    FileSymbols {
        path: input.path.to_owned(),
        file_digest: input.digest.to_owned(),
        size: input.size,
        language: language.to_owned(),
        ..FileSymbols::default()
    }
}

/// F0 fold of a file no adapter claims: one `opaque(reason="no-adapter")` unit (G19).
///
/// # Errors
///
/// [`FoldError`] only on an adapter bug.
pub(crate) fn opaque_file(input: &FileInput<'_>, ext: &str) -> Result<Folded, FoldError> {
    let lang = if ext.is_empty() { "opaque" } else { ext };
    let mut cx = Cx::new(input.path, lang, "");
    let leaf = cx.add(
        NodeSpec::new(
            Operator::opaque("no-adapter", input.digest.as_bytes()),
            cx.loc(0, input.size as usize),
        ),
        &[],
    )?;
    let root = cx.add(file_root_spec(&cx, input.size as usize), &[leaf])?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let mut file = base_file(input, "");
    file.fidelity = Fidelity::F0;
    file.parse_status = ParseStatus::NotParsed;
    let v = view::build(&term, input.path, Naming::Opaque);
    file.symbols = v.symbols;
    tracing::debug!(path = input.path, "no adapter: folded as one opaque unit");
    Ok(Folded { term, scopes, file })
}

/// F0 fold of a file whose parse produced no tree: the root unit holds one hole.
///
/// # Errors
///
/// [`FoldError`] only on an adapter bug.
pub(crate) fn failed_file(
    input: &FileInput<'_>,
    language: &str,
    reason: UnresolvedReason,
) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, language, "");
    let leaf = cx.add(
        NodeSpec::new(
            Operator::hole("parse-failed"),
            cx.loc(0, input.size as usize),
        ),
        &[],
    )?;
    let root = cx.add(file_root_spec(&cx, input.size as usize), &[leaf])?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let mut file = base_file(input, language);
    file.degraded = true;
    file.fidelity = Fidelity::F0;
    file.parse_status = ParseStatus::Failed {
        reason: reason.to_string(),
    };
    tracing::warn!(path = input.path, %reason, "parse failed: file folded as one hole");
    Ok(Folded { term, scopes, file })
}

/// The root unit spec of a parsed file of `size` bytes.
pub(crate) fn file_root_spec(cx: &Cx<'_>, size: usize) -> NodeSpec {
    NodeSpec::new(Operator::unit("file", "impl"), cx.loc(0, size))
}

/// Longest callee text kept for diagnostics.
const MAX_CALL_TEXT: usize = 80;

/// The callee expression `raw` as shown in diagnostics (`x.run(..)`), whitespace collapsed and capped.
pub(crate) fn call_text(raw: &str) -> String {
    let mut t = collapse_ws(raw);
    if t.chars().count() > MAX_CALL_TEXT {
        t = t.chars().take(MAX_CALL_TEXT).collect();
        t.push_str("...");
    }
    format!("{t}(..)")
}

/// One-based source line of `n`.
pub(crate) fn line_of(n: tree_sitter::Node<'_>) -> u32 {
    u32::try_from(n.start_position().row + 1).unwrap_or(u32::MAX)
}

/// The source text of `n`.
pub(crate) fn text_of<'t>(text: &'t str, n: tree_sitter::Node<'_>) -> &'t str {
    &text[n.start_byte()..n.end_byte()]
}

/// All children of `n` (named and anonymous) in source order.
pub(crate) fn children(n: tree_sitter::Node<'_>) -> Vec<tree_sitter::Node<'_>> {
    let mut c = n.walk();
    n.children(&mut c).collect()
}

/// All leaf tokens of `n` in source order, skipping subtrees for which `is_comment` holds.
pub(crate) fn leaves<'t>(
    n: tree_sitter::Node<'t>,
    is_comment: impl Fn(tree_sitter::Node<'t>) -> bool,
) -> Vec<tree_sitter::Node<'t>> {
    let mut out = Vec::new();
    let mut stack = vec![n];
    while let Some(x) = stack.pop() {
        if is_comment(x) {
            continue;
        }
        if x.child_count() == 0 {
            out.push(x);
        } else {
            stack.extend(children(x).into_iter().rev());
        }
    }
    out
}

/// What the file's scope graph says about the callee reference at `node`.
pub(crate) fn local_binding(
    scopes: &ScopeGraph,
    node: Option<NodeId>,
    item_local: bool,
) -> LocalBinding {
    let Some(r) = node.and_then(|n| scopes.ref_at(n)) else {
        return LocalBinding::None;
    };
    let is_binder = |d| scopes.decl(d).kind == DeclKind::Binder;
    let bound = match scopes.resolve(r) {
        Resolution::Must(d) => is_binder(d),
        Resolution::May(ds) => ds.iter().all(|&d| is_binder(d)),
        Resolution::Unknown => false,
    };
    match (bound, item_local) {
        (false, _) => LocalBinding::None,
        (true, true) => LocalBinding::Item,
        (true, false) => LocalBinding::Value,
    }
}
