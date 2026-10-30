//! Receiver types of Python method calls, from the constructor that built the receiver (ticket
//! 01M6422ZRSX74XT6RD0BG4T2RC, audit cases p12 and p13).
//!
//! `s = socket.socket(); s.connect(addr)` names the capability only through the type of `s`, which
//! no callee text spells, and `from socket import socket as S` or `import socket as sk` hide even
//! the constructor. [`python_receiver_calls`] resolves each constructor call through the import
//! aware [`path_uses`] pass and follows it into the receiver of a later method call: an
//! assignment, a `with ... as` target, a one-hop alias (`t = s`) or a directly chained
//! `ctor().m()`. A receiver whose every binding in scope agrees on one constructor is typed; one
//! with a parameter, a loop target, a differing rebinding, an attribute (`self.sock`) or any other
//! source is [`ReceiverCall::ty`] `None`: unresolved, which a consumer reports as a May use and
//! never passes silently. Only syntax-tree nodes are read.

// frob:ticket 01M6422ZRSX74XT6RD0BG4T2RC

use std::collections::{BTreeMap, BTreeSet};

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

use crate::canon::path_uses;

/// Deepest alias chain followed (`a = b; b = c; ..`).
const MAX_ALIAS_DEPTH: usize = 8;

/// One method call `recv.method(..)` on a Python receiver, with the receiver's constructor path.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReceiverCall {
    /// Byte offset of the receiver expression (the start of the callee `recv.method`).
    pub offset: usize,
    /// One-based line of the call.
    pub line: u32,
    /// The called method name.
    pub method: String,
    /// The receiver as written (`s`, `self.sock`, `socket.socket()`).
    pub recv: String,
    /// The fully qualified constructor path that built the receiver (`socket.socket`), or `None`
    /// when the receiver's origin is not one provable constructor call.
    pub ty: Option<String>,
}

/// Every method call of a Python file with its receiver's constructor, and the distinct
/// import-resolved paths the file uses (what modules it reaches).
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct PythonReceivers {
    /// The method calls on a name, a chained constructor call or another expression.
    pub calls: Vec<ReceiverCall>,
    /// Every import-resolved path the file calls or references, and every module it imports.
    pub reached: BTreeSet<String>,
}

impl PythonReceivers {
    /// True when the file uses `root` or anything under it (`socket`, `socket.socket`).
    #[must_use]
    pub fn reaches(&self, root: &str) -> bool {
        let under = format!("{root}.");
        self.reached
            .iter()
            .any(|p| p == root || p.starts_with(&under))
    }
}

/// What one binding of a name gives it.
#[derive(Clone, Debug)]
enum Bound {
    /// The result of calling a constructor with this qualified path.
    Ctor(String),
    /// A copy of another name in the same scope.
    Alias(String),
    /// Anything else: a parameter, a loop target, an import, an unresolved call.
    Other,
}

/// One lexical scope: its bindings and its parent.
struct Scope {
    parent: Option<usize>,
    class: bool,
    bound: BTreeMap<String, Vec<Bound>>,
}

/// The syntax-tree walk's state.
struct Walk<'a> {
    src: &'a str,
    ctors: BTreeMap<usize, String>,
    scopes: Vec<Scope>,
    poisoned: BTreeSet<String>,
    imported: BTreeSet<String>,
    pending: Vec<(usize, ReceiverCall, Option<Recv>)>,
}

/// A receiver awaiting resolution once every binding is known.
#[derive(Clone, Debug)]
enum Recv {
    Name(String),
    Ctor(String),
}

/// The method calls of Python `source` with their receivers' constructors.
///
/// Returns an empty result when the file does not parse.
#[must_use]
pub fn python_receiver_calls(source: &str) -> PythonReceivers {
    let ParseResult::Parsed(tree) = parse(Language::Python, source, &ParseLimits::default()) else {
        tracing::debug!("pyrecv: file not parsed, no receiver calls");
        return PythonReceivers::default();
    };
    let uses = path_uses("python", source);
    let mut reached: BTreeSet<String> = uses
        .iter()
        .filter(|u| !u.dynamic && u.wildcards.is_empty())
        .map(|u| u.path.clone())
        .collect();
    let ctors = uses
        .into_iter()
        .filter(|u| u.call && !u.dynamic && !u.computed && !u.maybe && u.wildcards.is_empty())
        .map(|u| (u.offset, u.path))
        .collect();
    let mut w = Walk {
        src: &tree.text,
        ctors,
        scopes: vec![Scope {
            parent: None,
            class: false,
            bound: BTreeMap::new(),
        }],
        poisoned: BTreeSet::new(),
        imported: BTreeSet::new(),
        pending: Vec::new(),
    };
    w.visit(tree.root(), 0);
    reached.extend(std::mem::take(&mut w.imported));
    let pending = std::mem::take(&mut w.pending);
    let calls: Vec<ReceiverCall> = pending
        .into_iter()
        .map(|(scope, mut call, recv)| {
            call.ty = match recv {
                Some(Recv::Ctor(p)) => Some(p),
                Some(Recv::Name(n)) => w.resolve(&n, scope, 0),
                None => None,
            };
            call
        })
        .collect();
    tracing::debug!(calls = calls.len(), "pyrecv: receiver calls typed");
    PythonReceivers { calls, reached }
}

impl Walk<'_> {
    fn text(&self, n: Node<'_>) -> String {
        self.src[n.start_byte()..n.end_byte()].to_owned()
    }

    fn bind(&mut self, scope: usize, name: String, b: Bound) {
        self.scopes[scope].bound.entry(name).or_default().push(b);
    }

    /// The qualified constructor path of `n` when it is a call of an import-resolved callee.
    fn ctor_of(&self, n: Node<'_>) -> Option<String> {
        if n.kind() != "call" {
            return None;
        }
        let f = n.child_by_field_name("function")?;
        self.ctors.get(&f.start_byte()).cloned()
    }

    /// Marks every name a pattern binds as bound to something unknown.
    fn bind_pattern_other(&mut self, n: Node<'_>, scope: usize) {
        match n.kind() {
            "identifier" => {
                let name = self.text(n);
                self.bind(scope, name, Bound::Other);
            }
            "attribute" | "subscript" => {}
            _ => {
                let mut c = n.walk();
                for k in n.named_children(&mut c) {
                    self.bind_pattern_other(k, scope);
                }
            }
        }
    }

    /// Binds the simple target `name` to what `value` is, else to `Other`.
    fn bind_value(&mut self, target: Node<'_>, value: Option<Node<'_>>, scope: usize) {
        if target.kind() != "identifier" {
            self.bind_pattern_other(target, scope);
            return;
        }
        let name = self.text(target);
        let b = match value {
            Some(v) => match (self.ctor_of(v), v.kind()) {
                (Some(p), _) => Bound::Ctor(p),
                (None, "identifier") => Bound::Alias(self.text(v)),
                _ => Bound::Other,
            },
            None => Bound::Other,
        };
        self.bind(scope, name, b);
    }

    fn bind_params(&mut self, params: Node<'_>, scope: usize) {
        let mut c = params.walk();
        for p in params.named_children(&mut c) {
            let name = match p.kind() {
                "identifier" => Some(p),
                "default_parameter" | "typed_default_parameter" => p.child_by_field_name("name"),
                _ => {
                    let mut k = p.walk();
                    p.named_children(&mut k).find(|x| x.kind() == "identifier")
                }
            };
            if let Some(n) = name {
                self.bind_pattern_other(n, scope);
            }
        }
    }

    fn new_scope(&mut self, parent: usize, class: bool) -> usize {
        self.scopes.push(Scope {
            parent: Some(parent),
            class,
            bound: BTreeMap::new(),
        });
        self.scopes.len() - 1
    }

    fn visit(&mut self, n: Node<'_>, scope: usize) {
        let mut inner = scope;
        match n.kind() {
            "function_definition" | "lambda" => {
                if let Some(name) = n.child_by_field_name("name") {
                    self.bind_pattern_other(name, scope);
                }
                inner = self.new_scope(scope, false);
                if let Some(p) = n.child_by_field_name("parameters") {
                    self.bind_params(p, inner);
                }
            }
            "class_definition" => {
                if let Some(name) = n.child_by_field_name("name") {
                    self.bind_pattern_other(name, scope);
                }
                inner = self.new_scope(scope, true);
            }
            "assignment" => {
                if let Some(left) = n.child_by_field_name("left") {
                    let right = n.child_by_field_name("right");
                    self.bind_value(left, right, scope);
                }
            }
            "augmented_assignment" | "named_expression" => {
                if let Some(left) = n
                    .child_by_field_name("left")
                    .or_else(|| n.child_by_field_name("name"))
                {
                    self.bind_pattern_other(left, scope);
                }
            }
            "for_statement" | "for_in_clause" => {
                if let Some(left) = n.child_by_field_name("left") {
                    self.bind_pattern_other(left, scope);
                }
            }
            "as_pattern" => {
                let mut c = n.walk();
                let value = n.named_children(&mut c).next();
                if let Some(alias) = n.child_by_field_name("alias") {
                    let target = if alias.kind() == "as_pattern_target" {
                        alias.named_child(0).unwrap_or(alias)
                    } else {
                        alias
                    };
                    self.bind_value(target, value.filter(|v| v.kind() == "call"), scope);
                }
            }
            "import_statement" | "import_from_statement" => {
                self.bind_import(n, scope);
            }
            "global_statement" | "nonlocal_statement" => {
                let mut c = n.walk();
                for id in n.named_children(&mut c) {
                    let name = self.text(id);
                    self.poisoned.insert(name);
                }
            }
            "call" => self.note_call(n, scope),
            _ => {}
        }
        let mut c = n.walk();
        for k in n.children(&mut c) {
            self.visit(k, inner);
        }
    }

    /// Every name an import statement binds becomes `Other`.
    fn bind_import(&mut self, n: Node<'_>, scope: usize) {
        if let Some(m) = n.child_by_field_name("module_name") {
            let m = self.text(m);
            self.imported.insert(m);
        }
        let mut c = n.walk();
        for k in n.named_children(&mut c) {
            let module = match k.kind() {
                "aliased_import" => k.child_by_field_name("name"),
                "dotted_name" if n.kind() == "import_statement" => Some(k),
                _ => None,
            };
            if let Some(m) = module {
                let m = self.text(m);
                self.imported.insert(m);
            }
            let bound = match k.kind() {
                "aliased_import" => k.child_by_field_name("alias"),
                "dotted_name" => k.named_child(0),
                _ => None,
            };
            if let Some(b) = bound {
                let name = self.text(b);
                self.bind(scope, name, Bound::Other);
            }
        }
    }

    /// Records `recv.method(..)` for later resolution.
    fn note_call(&mut self, call: Node<'_>, scope: usize) {
        let Some(f) = call.child_by_field_name("function") else {
            return;
        };
        if f.kind() != "attribute" {
            return;
        }
        let (Some(obj), Some(attr)) = (
            f.child_by_field_name("object"),
            f.child_by_field_name("attribute"),
        ) else {
            return;
        };
        let recv = match obj.kind() {
            "identifier" => Some(Recv::Name(self.text(obj))),
            _ => self.ctor_of(obj).map(Recv::Ctor),
        };
        let rc = ReceiverCall {
            offset: f.start_byte(),
            line: u32::try_from(call.start_position().row + 1).unwrap_or(u32::MAX),
            method: self.text(attr),
            recv: self.text(obj),
            ty: None,
        };
        self.pending.push((scope, rc, recv));
    }

    /// The scope that owns `name` as seen from `scope` (class scopes are visible only directly).
    fn owner(&self, name: &str, scope: usize) -> Option<usize> {
        let mut cur = Some(scope);
        while let Some(i) = cur {
            let s = &self.scopes[i];
            if (i == scope || !s.class) && s.bound.contains_key(name) {
                return Some(i);
            }
            cur = s.parent;
        }
        None
    }

    /// The one constructor every binding of `name` agrees on, else `None`.
    fn resolve(&self, name: &str, scope: usize, depth: usize) -> Option<String> {
        if depth > MAX_ALIAS_DEPTH || self.poisoned.contains(name) {
            return None;
        }
        let owner = self.owner(name, scope)?;
        let mut found: Option<String> = None;
        for b in &self.scopes[owner].bound[name] {
            let p = match b {
                Bound::Ctor(p) => p.clone(),
                Bound::Alias(other) if other != name => self.resolve(other, owner, depth + 1)?,
                Bound::Alias(_) | Bound::Other => return None,
            };
            match &found {
                Some(f) if *f != p => return None,
                _ => found = Some(p),
            }
        }
        found
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tys(src: &str) -> Vec<(String, String, Option<String>)> {
        python_receiver_calls(src)
            .calls
            .into_iter()
            .map(|c| (c.recv, c.method, c.ty))
            .collect()
    }

    fn sock(t: &[(String, String, Option<String>)], m: &str) -> Option<String> {
        t.iter()
            .find(|(_, mm, _)| mm == m)
            .and_then(|c| c.2.clone())
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p12_cap_a_constructor_result_keeps_its_type() {
        let t = tys("import socket\ndef go():\n    s = socket.socket()\n    s.connect(1)\n");
        assert_eq!(sock(&t, "connect").as_deref(), Some("socket.socket"));
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p12_cap_aliased_imports_resolve_the_constructor() {
        let t = tys("from socket import socket as S\ndef go():\n    s = S()\n    s.send(b'')\n");
        assert_eq!(sock(&t, "send").as_deref(), Some("socket.socket"));
        let t = tys(
            "import socket as sk\ndef go():\n    s = sk.create_connection(1)\n    s.sendall(b'')\n",
        );
        assert_eq!(
            sock(&t, "sendall").as_deref(),
            Some("socket.create_connection")
        );
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p13_cap_with_alias_and_chained_forms_are_typed() {
        let t = tys(
            "import socket\ndef go():\n    with socket.socket() as s:\n        t = s\n        t.connect(1)\n",
        );
        assert_eq!(sock(&t, "connect").as_deref(), Some("socket.socket"));
        let t = tys("import socket\nsocket.socket().connect(1)\n");
        assert_eq!(sock(&t, "connect").as_deref(), Some("socket.socket"));
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p13_cap_unprovable_receivers_stay_untyped() {
        for src in [
            "import socket\ndef go(s):\n    s.connect(1)\n",
            "import socket\ndef go():\n    s = socket.socket()\n    s = make()\n    s.connect(1)\n",
            "import socket\nclass A:\n    def go(self):\n        self.sock.connect(1)\n",
            "import socket\ndef go():\n    for s in many():\n        s.connect(1)\n",
            "import socket\ndef go():\n    s = socket.socket()\n    t = other.make()\n    s = t\n    s.connect(1)\n",
        ] {
            assert_eq!(sock(&tys(src), "connect"), None, "{src}");
        }
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p13_cap_a_name_rebound_to_different_constructors_is_untyped() {
        let t = tys(
            "import socket, sqlite3\ndef go(c):\n    s = socket.socket()\n    if c:\n        s = sqlite3.connect('x')\n    s.connect(1)\n",
        );
        assert_eq!(sock(&t, "connect"), None);
    }

    // frob:tests crates/gob-symbols/src/pyrecv.rs::python_receiver_calls
    #[test]
    fn p12_cap_reached_paths_name_the_modules_a_file_uses() {
        let r = python_receiver_calls("import socket as sk\nsk.socket()\n");
        assert!(r.reaches("socket") && !r.reaches("sock"));
        assert!(python_receiver_calls("import socket\n").reaches("socket"));
        assert!(python_receiver_calls("from socket import socket\n").reaches("socket"));
        assert!(!python_receiver_calls("import os\n").reaches("socket"));
    }
}
