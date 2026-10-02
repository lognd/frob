//! Shared test helpers: a terse term builder with automatic locations.
#![allow(dead_code, reason = "each test target uses a different subset")]

use gob_ir::{GroupOrder, Location, NodeId, NodeSpec, Operator, Term, TermBuilder, reserved};
use gob_text::{FileId, FileInterner};

/// A builder that hands out unit-width text locations unless told otherwise.
pub struct B {
    pub tb: TermBuilder,
    pub file: FileId,
    pub files: FileInterner,
    pos: u32,
}

impl B {
    pub fn new(locator: &str, lang: &str) -> Self {
        let mut files = FileInterner::new();
        let file = files.intern(locator);
        Self {
            tb: TermBuilder::new(locator, lang),
            file,
            files,
            pos: 0,
        }
    }

    fn next_loc(&mut self) -> Location {
        let l = Location::text(self.file, self.pos, self.pos + 1);
        self.pos += 1;
        l
    }

    pub fn spec(&mut self, op: Operator) -> NodeSpec {
        let loc = self.next_loc();
        NodeSpec::new(op, loc)
    }

    pub fn add(&mut self, spec: NodeSpec, kids: &[NodeId]) -> NodeId {
        self.tb.node(spec, kids).expect("valid node")
    }

    pub fn node(&mut self, op: Operator, kids: &[NodeId]) -> NodeId {
        let spec = self.spec(op);
        self.add(spec, kids)
    }

    pub fn unit(&mut self, kind: &str, name: &str, binders: &[&str], kids: &[NodeId]) -> NodeId {
        let spec = self
            .spec(Operator::unit(kind, "impl"))
            .named(name)
            .binders(binders);
        self.add(spec, kids)
    }

    pub fn file_unit(&mut self, kids: &[NodeId]) -> NodeId {
        self.node(Operator::unit("file", "impl"), kids)
    }

    pub fn reference(&mut self, name: &str) -> NodeId {
        self.node(Operator::reference(name), &[])
    }

    pub fn lit(&mut self, lexeme: &str) -> NodeId {
        self.node(Operator::lit("str", lexeme), &[])
    }

    pub fn call(&mut self, head: &str, args: &[NodeId]) -> NodeId {
        let h = self.reference(head);
        let mut kids = vec![h];
        kids.extend_from_slice(args);
        self.node(Operator::apply("call"), &kids)
    }

    pub fn doc(&mut self, text: &str) -> NodeId {
        let l = self.lit(text);
        self.node(Operator::attr("doc"), &[l])
    }

    pub fn sig(&mut self, op: Operator, kids: &[NodeId]) -> NodeId {
        let spec = self.spec(op).attr(reserved::FACET, "sig");
        self.add(spec, kids)
    }

    pub fn group(&mut self, order: GroupOrder, kids: &[NodeId]) -> NodeId {
        self.node(Operator::group(order), kids)
    }

    pub fn finish(self, root: NodeId) -> Term {
        self.tb.finish(root).expect("valid term")
    }
}
