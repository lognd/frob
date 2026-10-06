//! A GRL rule over `element` and `attribute` compiles against the catalog and runs on a hand-built U term.

use gob_ir::markup::{self, ELEMENT, TAG};
use gob_ir::{GroupOrder, Location, Model, NodeId, NodeSpec, Operator, TermBuilder};
use gob_plan::catalog;
use gob_plan::exec::{CompileError, compile};
use gob_plan::grl::parse;
use gob_text::FileInterner;

const ALT_RULE: &str = r#"
rule ALT001 "img-alt" {
  lang tsx

  find e: element(tag = "img")
  where not e has attribute(name = "alt")
  report e "img needs an alt attribute"

  example fire """
    const a = <img src="x.png" />;
  """
  example clean """
    const a = <img src="x.png" alt="x" />;
  """

  explain """
    Images need alternative text.
  """
}
"#;

fn compile_src(src: &str) -> Result<gob_plan::exec::Program, CompileError> {
    let file = FileInterner::new().intern("rules/T.grl");
    let parsed = parse(file, src);
    assert!(parsed.is_ok(), "{:#?}", parsed.errors);
    compile(&parsed.file.rules[0])
}

struct Doc {
    tb: TermBuilder,
    f: gob_text::FileId,
    at: u32,
}

impl Doc {
    fn add(&mut self, op: Operator, name: Option<&str>, kids: &[NodeId]) -> NodeId {
        self.at += 1;
        let mut spec = NodeSpec::new(op, Location::text(self.f, self.at, self.at + 1));
        if let Some(n) = name {
            spec = spec.named(n);
        }
        self.tb.node(spec, kids).unwrap()
    }
    fn img(&mut self, attrs: &[(&str, &str)], spread: bool) -> NodeId {
        let head = self.add(Operator::lit(TAG, "img"), None, &[]);
        let mut kids = vec![head];
        for (n, v) in attrs {
            let val = self.add(Operator::lit("str", v), None, &[]);
            kids.push(self.add(markup::attribute_op(), Some(n), &[val]));
        }
        if spread {
            let e = self.add(Operator::reference("props"), None, &[]);
            kids.push(self.add(markup::spread_op(), None, &[e]));
        }
        self.add(Operator::apply(ELEMENT), None, &kids)
    }
}

#[test]
fn element_attribute_rule_runs_on_a_hand_built_term() {
    let mut files = FileInterner::new();
    let mut d = Doc {
        tb: TermBuilder::new("a.tsx", "tsx"),
        f: files.intern("a.tsx"),
        at: 0,
    };
    let bad = d.img(&[("src", "x.png")], false);
    let good = d.img(&[("src", "x.png"), ("alt", "logo")], false);
    let maybe = d.img(&[("src", "y.png")], true);
    let root = d.add(
        Operator::group(GroupOrder::Sequence),
        None,
        &[bad, good, maybe],
    );
    let model = Model::lexical(d.tb.finish(root).unwrap());

    let program = compile_src(ALT_RULE).unwrap();
    assert_eq!((program.rule(), program.var()), ("ALT001", "e"));
    let out = program.run(&model);
    assert_eq!(out.fired, vec![bad]);
    assert_eq!(out.unresolved, vec![maybe], "a spread may supply alt");
    assert_eq!(out.message, "img needs an alt attribute");
}

#[test]
fn attribute_rule_reads_const_values() {
    let src = ALT_RULE
        .replace(
            r#"find e: element(tag = "img")"#,
            r#"find a: attribute(name = "role")"#,
        )
        .replace(
            r#"where not e has attribute(name = "alt")"#,
            r#"where a.value == "presentation""#,
        )
        .replace("report e", "report a");
    let program = compile_src(&src).unwrap();
    let mut files = FileInterner::new();
    let mut d = Doc {
        tb: TermBuilder::new("a.tsx", "tsx"),
        f: files.intern("a.tsx"),
        at: 0,
    };
    let hit = d.img(&[("role", "presentation")], false);
    let miss = d.img(&[("role", "img")], false);
    let root = d.add(Operator::group(GroupOrder::Sequence), None, &[hit, miss]);
    let model = Model::lexical(d.tb.finish(root).unwrap());
    let out = program.run(&model);
    assert_eq!(out.fired.len(), 1);
    assert!(out.unresolved.is_empty());
    let els = markup::elements(&model);
    assert_eq!(out.fired[0], els[0].attributes[0].node);
}

#[test]
fn unknown_kind_and_field_are_grl001() {
    let bad_kind = ALT_RULE.replace("element(", "elemnt(");
    assert!(matches!(
        compile_src(&bad_kind),
        Err(CompileError::UnknownKind { ref word, .. }) if word == "elemnt"
    ));
    let bad_field = ALT_RULE.replace("tag", "tga");
    assert!(matches!(
        compile_src(&bad_field),
        Err(CompileError::UnknownField { kind: "element", ref field, .. }) if field == "tga"
    ));
}

#[test]
fn catalog_names_query_and_languages_for_each_web_kind() {
    for (word, query, lang) in [
        ("element", "Q48 markup", "tsx"),
        ("attribute", "Q48 markup", "html"),
        ("style_rule", "Q49 style", "css"),
        ("declaration", "Q49 style", "jsx"),
        ("custom_property", "Q49 style", "scss"),
    ] {
        let k = catalog::kind(word).unwrap();
        assert_eq!(k.query, query, "{word}");
        assert!(k.answered_in(lang), "{word} in {lang}");
    }
}
