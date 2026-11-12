//! Disjoint-set (union-find) over dense indices, shared by the COH rules that cluster statements.

/// A disjoint-set forest over `0..n`; `.0[i]` is the parent of `i`.
pub(crate) struct Union(pub(crate) Vec<usize>);

impl Union {
    /// A forest of `n` singleton sets.
    pub(crate) fn new(n: usize) -> Self {
        Self((0..n).collect())
    }

    /// The root of `x`'s set, compressing the path.
    pub(crate) fn find(&mut self, x: usize) -> usize {
        let p = self.0[x];
        if p == x {
            return x;
        }
        let r = self.find(p);
        self.0[x] = r;
        r
    }

    /// Merges the sets of `a` and `b`, keeping the smaller root.
    pub(crate) fn join(&mut self, a: usize, b: usize) {
        let (a, b) = (self.find(a), self.find(b));
        self.0[a.max(b)] = a.min(b);
    }
}
