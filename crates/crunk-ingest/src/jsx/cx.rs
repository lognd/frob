//! The view of one folded source the extractors share: the model, the text and line numbers.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use gob_ir::{Location, Model, NodeId, Operator, Universal};

/// Byte offsets of line starts (tree-sitter rows: only `\n` ends a line).
pub(super) struct Lines(Vec<usize>);

impl Lines {
    /// The line starts of `src`.
    pub(super) fn of(src: &str) -> Self {
        let mut starts = vec![0];
        starts.extend(src.match_indices('\n').map(|(i, _)| i + 1));
        Self(starts)
    }

    /// The 1-based line holding byte `offset`.
    pub(super) fn line_of(&self, offset: usize) -> u32 {
        u32::try_from(self.0.partition_point(|&s| s <= offset)).unwrap_or(u32::MAX)
    }
}

/// A folded source and its text.
pub(super) struct Cx<'a> {
    /// The folded file.
    pub model: &'a Model,
    /// The file text the model's ranges address.
    pub src: &'a str,
    /// Line starts of `src`.
    pub lines: Lines,
}

impl<'a> Cx<'a> {
    /// A view over `model` and `src`.
    pub(super) fn new(model: &'a Model, src: &'a str) -> Self {
        Self {
            model,
            src,
            lines: Lines::of(src),
        }
    }

    /// The byte range of `id` in the source, when it has a text location.
    pub(super) fn range(&self, id: NodeId) -> Option<(usize, usize)> {
        match self.model.term().node(id).location() {
            Location::Text { range, .. } => {
                let (s, e) = (
                    usize::try_from(u32::from(range.start())).ok()?,
                    usize::try_from(u32::from(range.end())).ok()?,
                );
                (s <= e && e <= self.src.len()).then_some((s, e))
            }
            _ => None,
        }
    }

    /// The 1-based line `id` starts on (1 without a location).
    pub(super) fn line(&self, id: NodeId) -> u32 {
        self.range(id).map_or(1, |(s, _)| self.lines.line_of(s))
    }

    /// The children of `id`.
    pub(super) fn kids(&self, id: NodeId) -> &'a [NodeId] {
        self.model.term().node(id).children()
    }

    /// The operator of `id`.
    pub(super) fn op(&self, id: NodeId) -> &'a Operator {
        self.model.term().node(id).op()
    }

    /// `(kind, lexeme)` when `id` is a `lit`.
    pub(super) fn lit(&self, id: NodeId) -> Option<(&'a str, &'a str)> {
        match self.op(id) {
            Operator::Universal(Universal::Lit { kind, lexeme }) => Some((kind, lexeme)),
            _ => None,
        }
    }

    /// The name when `id` is a `ref`.
    pub(super) fn reference(&self, id: NodeId) -> Option<&'a str> {
        match self.op(id) {
            Operator::Universal(Universal::Ref { name }) => Some(name),
            _ => None,
        }
    }

    /// True when `id` is `apply(op)` whose head is the `lit(op, lexeme)` operator `lexeme`.
    pub(super) fn is_op(&self, id: NodeId, lexeme: &str) -> bool {
        matches!(self.op(id), Operator::Universal(Universal::Apply { kind }) if kind == "op")
            && self
                .kids(id)
                .first()
                .and_then(|&h| self.lit(h))
                .is_some_and(|(kind, lex)| kind == "op" && lex == lexeme)
    }

    /// True when `id` is the adapter node `typescript.<name>` (a syntax shape the folder kept).
    pub(super) fn is_adapter(&self, id: NodeId, name: &str) -> bool {
        matches!(self.op(id), Operator::Adapter(a) if a.name == name)
    }
}
