//! Small tree-sitter helpers and the language tag shared by the flow scanners (PATH, TIME).

// frob:ticket 01M41RV691XZQ5W2EW821PHK3V
// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use tree_sitter::Node;

/// The languages whose adapters carry the roles the flow scanners need.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Lang {
    /// Rust.
    Rust,
    /// Python.
    Python,
}

impl Lang {
    /// The role-bearing tag of `language`, or `None` when its adapter has no such roles.
    pub(crate) fn of(language: gob_languages::Language) -> Option<Self> {
        match language {
            gob_languages::Language::Rust => Some(Self::Rust),
            gob_languages::Language::Python => Some(Self::Python),
            _ => None,
        }
    }
}

/// The source text of `n`.
pub(crate) fn text<'a>(n: Node<'_>, src: &'a str) -> &'a str {
    &src[n.byte_range()]
}

/// Every child of `n`, anonymous tokens included.
pub(crate) fn children(n: Node<'_>) -> Vec<Node<'_>> {
    let mut cur = n.walk();
    n.children(&mut cur).collect()
}

/// Every identifier text in the subtree (token-tree identifiers included).
pub(crate) fn idents(node: Node<'_>, src: &str, out: &mut Vec<String>) {
    if node.kind() == "identifier" {
        out.push(text(node, src).to_owned());
    }
    for c in children(node) {
        idents(c, src, out);
    }
}
