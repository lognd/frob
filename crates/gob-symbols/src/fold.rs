//! Shared fold helpers: the term-building context and the F0 folds (adapter-less
//! files and files whose parse failed outright).

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use gob_ir::{
    DeclKind, Location, NodeId, NodeSpec, Operator, Resolution, ScopeGraph, TermBuilder, TermError,
};
use gob_languages::UnresolvedReason;
use gob_text::FileInterner;

use crate::adapter::{ConcreteTree, Fidelity, FileInput, FoldError, Folded, ParseStatus};
use crate::model::{CallSite, FileSymbols, LocalBinding, Receiver, RefKind, RefSite, collapse_ws};
use crate::symref::Symref;
use crate::view::{self, ATTR_VISIBILITY, Naming};

/// Deepest term nesting before a subtree collapses into one opaque node (the honest fallback).
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
pub(crate) const MAX_DEPTH: usize = 20_000;

/// Syntax depth above which lowering moves to a dedicated large-stack thread.
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
const INLINE_DEPTH: usize = 96;

/// Stack bytes reserved per syntax level when lowering runs on its own thread.
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
const STACK_PER_LEVEL: usize = 64 * 1024;

/// Upper bound on the lowering thread stack (virtual reservation, committed lazily).
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
const STACK_CAP: usize = 2 << 30;

/// Maximum syntax depth under `root`, measured with an explicit cursor (no recursion).
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
pub(crate) fn syntax_depth(root: tree_sitter::Node<'_>) -> usize {
    let mut cur = root.walk();
    let (mut depth, mut max) = (0usize, 0usize);
    loop {
        if cur.goto_first_child() {
            depth += 1;
            max = max.max(depth);
            continue;
        }
        while !cur.goto_next_sibling() {
            if !cur.goto_parent() {
                return max;
            }
            depth -= 1;
        }
    }
}

/// Runs the recursive lowering `lower`, on a depth-sized stack thread when `root` is deeply nested.
// frob:ticket 01M4VWZZ1R3MK67F1ZBB33SE5T
pub(crate) fn with_sized_stack<T: Send>(
    lang: &str,
    path: &str,
    root: tree_sitter::Node<'_>,
    lower: impl FnOnce() -> T + Send,
) -> T {
    let depth = syntax_depth(root);
    if depth <= INLINE_DEPTH {
        return lower();
    }
    let stack = depth.saturating_mul(STACK_PER_LEVEL).min(STACK_CAP);
    tracing::debug!(
        path,
        depth,
        stack,
        "{lang}: deep file, lowering on a sized stack"
    );
    let slot = std::sync::Mutex::new(Some(lower));
    std::thread::scope(|sc| {
        let run = || {
            let f = slot.lock().ok().and_then(|mut g| g.take());
            f.map(|f| f())
        };
        let spawned = std::thread::Builder::new()
            .name(format!("gob-{lang}-fold"))
            .stack_size(stack)
            .spawn_scoped(sc, run);
        match spawned {
            Ok(h) => match h.join() {
                Ok(Some(v)) => v,
                Ok(None) => unreachable!("lowering closure taken twice"),
                Err(e) => std::panic::resume_unwind(e),
            },
            Err(err) => {
                tracing::warn!(path, %err, "{lang}: stack thread refused, lowering inline");
                let f = slot.lock().ok().and_then(|mut g| g.take());
                f.map(|f| f())
                    .expect("lowering closure still present when the spawn failed")
            }
        }
    })
}

/// The context of one fold: the term builder, the file id and the source text.
pub(crate) struct Cx<'a> {
    /// The term under construction.
    pub b: TermBuilder,
    /// The interned id of the artifact, for locations.
    pub file: gob_text::FileId,
    /// The source text (empty for adapter-less files).
    pub text: &'a str,
    /// Byte offset of `text` in the host file (0 unless this is a nested body, see [`Cx::nest`]).
    pub base: usize,
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
            base: 0,
        }
    }

    // frob:ticket 01M48E13W9MYK85YTCWSSRS50S
    /// A context for the nested body `text` that starts at byte `base` of this file.
    ///
    /// The nested context takes over the host builder, so its nodes live in the host term and its
    /// locations are spans in the host file; hand it back with [`Cx::unnest`].
    pub fn nest<'t>(&mut self, text: &'t str, base: usize) -> Cx<'t> {
        let b = std::mem::replace(&mut self.b, TermBuilder::new("", ""));
        tracing::trace!(base, len = text.len(), "nested fold opened");
        Cx {
            b,
            file: self.file,
            text,
            base: self.base + base,
        }
    }

    // frob:ticket 01M48E13W9MYK85YTCWSSRS50S
    /// Takes the builder back from a nested context opened by [`Cx::nest`].
    pub fn unnest(&mut self, nested: Cx<'_>) {
        self.b = nested.b;
    }

    /// A text location from byte offsets.
    pub fn loc(&self, start: usize, end: usize) -> Location {
        let clamp = |n: usize| u32::try_from(n).unwrap_or(u32::MAX);
        let (start, end) = (start + self.base, end.max(start) + self.base);
        Location::text(self.file, clamp(start), clamp(end))
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

/// The byte span `(start, end)` of `n` in its own tree's text.
pub(crate) fn span_of(n: tree_sitter::Node<'_>) -> (usize, usize) {
    (n.start_byte(), n.end_byte())
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

/// One call or value reference found while folding, before it has a `Symref`.
pub(crate) struct Site {
    pub(crate) caller: usize,
    pub(crate) value: bool,
    pub(crate) name: String,
    pub(crate) qualifier: Option<String>,
    pub(crate) method: bool,
    pub(crate) receiver: Option<Receiver>,
    pub(crate) node: Option<NodeId>,
    pub(crate) args: usize,
    pub(crate) qual_path: Vec<String>,
    pub(crate) line: u32,
    pub(crate) span: (usize, usize),
    pub(crate) text: String,
}

/// Files `s` (found in `caller`) as a call or a value reference of `file`.
pub(crate) fn push_site(file: &mut FileSymbols, scopes: &ScopeGraph, s: Site, caller: Symref) {
    if s.value {
        file.refs.push(RefSite {
            from: caller,
            name: s.name,
            qualifier: None,
            kind: RefKind::Value,
        });
        return;
    }
    let local = local_binding(scopes, s.node, false);
    file.calls.push(CallSite {
        caller,
        callee: s.name,
        qualifier: s.qualifier,
        method: s.method,
        local,
        in_macro: false,
        receiver: s.receiver,
        opaque_qualifier: false,
        macro_exact: None,
        args: Some(s.args),
        qual_path: s.qual_path,
        bound: Vec::new(),
        line: s.line,
        text: s.text,
        start: s.span.0,
        end: s.span.1,
    });
}

/// Folds `tree` with `inline` (on a depth-sized stack when deeply nested), or reports it failed.
pub(crate) fn fold_adapter_tree(
    lang: &str,
    tree: &ConcreteTree,
    input: &FileInput<'_>,
    inline: impl FnOnce(&str, tree_sitter::Node<'_>, &FileInput<'_>) -> Result<Folded, FoldError> + Send,
) -> Result<Folded, FoldError> {
    match tree {
        ConcreteTree::Parsed(t) => {
            let root = t.root();
            with_sized_stack(lang, input.path, root, || inline(&t.text, root, input))
        }
        ConcreteTree::Unparsed(reason) => failed_file(input, lang, *reason),
        ConcreteTree::Leaf | ConcreteTree::Source(_) => {
            failed_file(input, lang, UnresolvedReason::GrammarUnavailable)
        }
    }
}

/// Applies `lower` to every child of `n` in source order, stopping at the first error.
pub(crate) fn lower_children(
    n: tree_sitter::Node<'_>,
    mut lower: impl FnMut(tree_sitter::Node<'_>) -> Result<NodeId, TermError>,
) -> Result<Vec<NodeId>, TermError> {
    children(n).into_iter().map(&mut lower).collect()
}

/// The decorator `d`'s name (whitespace removed, via `name_of`) and its call arguments, if any.
pub(crate) fn decorator_parts<'t>(
    d: tree_sitter::Node<'t>,
    call_kind: &str,
    name_of: impl Fn(tree_sitter::Node<'t>) -> String,
) -> (String, Option<tree_sitter::Node<'t>>) {
    let expr = children(d)
        .into_iter()
        .find(|c| c.is_named() && c.kind() != "comment");
    let (name, args) = match expr {
        Some(e) if e.kind() == call_kind => (
            e.child_by_field_name("function").map(&name_of),
            e.child_by_field_name("arguments"),
        ),
        Some(e) => (Some(name_of(e)), None),
        None => (None, None),
    };
    let name = name.unwrap_or_default().split_whitespace().collect();
    (name, args)
}

impl Cx<'_> {
    /// An attribute node for decorator `d` named `name`, with the argument leaves as payload.
    pub(crate) fn decorator_attr_node(
        &mut self,
        d: tree_sitter::Node<'_>,
        name: &str,
        args: Option<tree_sitter::Node<'_>>,
    ) -> Result<NodeId, TermError> {
        let text = self.text;
        let mut payload = Vec::new();
        if let Some(a) = args {
            for l in leaves(a, |c| c.kind() == "comment") {
                payload.push(self.lit(l.kind(), text_of(text, l), l)?);
            }
        }
        self.op(Operator::attr(name), d, &payload)
    }

    /// One opaque `depth-limit` node spanning `nodes`, carrying their joined leaf tokens.
    pub(crate) fn collapse_nodes(
        &mut self,
        path: &str,
        nodes: &[tree_sitter::Node<'_>],
    ) -> Result<NodeId, TermError> {
        let text = self.text;
        let toks: Vec<&str> = nodes
            .iter()
            .flat_map(|n| leaves(*n, |c| c.kind() == "comment"))
            .map(|l| text_of(text, l))
            .collect();
        let (start, end) = nodes
            .first()
            .zip(nodes.last())
            .map_or((0, 0), |(a, b)| (a.start_byte(), b.end_byte()));
        tracing::debug!(path, start, end, "depth limit: subtree collapsed");
        let spec = NodeSpec::new(
            Operator::opaque("depth-limit", toks.join(" ").as_bytes()),
            self.loc(start, end),
        );
        self.add(spec, &[])
    }
}

/// A folder that can collapse a too-deep subtree into one opaque node, still recording its calls.
pub(crate) trait Collapse<'a> {
    /// The term-building context.
    fn cx_mut(&mut self) -> &mut Cx<'a>;
    /// The path of the file being folded, for logging.
    fn file_path(&self) -> &str;
    /// Records the calls inside `root` without building term nodes.
    fn scan(&mut self, root: tree_sitter::Node<'_>);

    /// Collapses `nodes` into one opaque `depth-limit` node after scanning them for calls.
    fn collapse(&mut self, nodes: &[tree_sitter::Node<'_>]) -> Result<NodeId, TermError> {
        for n in nodes {
            self.scan(*n);
        }
        let path = self.file_path().to_owned();
        self.cx_mut().collapse_nodes(&path, nodes)
    }
}

/// One named unit spanning `n` whose body is its source text, with the given visibility.
pub(crate) fn text_unit(
    cx: &mut Cx<'_>,
    text: &str,
    n: tree_sitter::Node<'_>,
    kind: &str,
    name: &str,
    public: bool,
) -> Result<NodeId, TermError> {
    let body = cx.lit("text", text_of(text, n), n)?;
    let vis = if public { "public" } else { "private" };
    let spec = NodeSpec::new(Operator::unit(kind, "impl"), cx.node_loc(n))
        .named(name)
        .attr(ATTR_VISIBILITY, vis);
    cx.add(spec, &[body])
}
