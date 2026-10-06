//! The web-engine answer types: markup, style, `const_value` and `class_tokens` on hand-built terms.
#![allow(clippy::many_single_char_names, reason = "terse fixtures")]

// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

use gob_ir::const_value::{
    Budget, CONST_KIND, CallKind, ConstEval, ConstValue, External, ExternalRefs, Fragment, OP,
    OP_ADD, OP_AND, OP_ARRAY, OP_COND, OP_OBJECT, OP_OR, OP_PROP, OP_SPREAD, OP_TEMPLATE, Value,
    const_value,
};
use gob_ir::markup::{self, ELEMENT, TAG, TEXT, TagKind};
use gob_ir::style::{self, ValuePart};
use gob_ir::{GroupOrder, Location, Model, NodeId, NodeSpec, Operator, Status, TermBuilder};
use gob_text::FileInterner;

/// A builder that hands out distinct locations.
struct B {
    tb: TermBuilder,
    f: gob_text::FileId,
    at: u32,
}

impl B {
    fn new(lang: &str) -> Self {
        let mut files = FileInterner::new();
        let f = files.intern("t");
        Self {
            tb: TermBuilder::new("t", lang),
            f,
            at: 0,
        }
    }
    fn spec(&mut self, op: Operator) -> NodeSpec {
        self.at += 1;
        NodeSpec::new(op, Location::text(self.f, self.at, self.at + 1))
    }
    fn add(&mut self, op: Operator, kids: &[NodeId]) -> NodeId {
        let s = self.spec(op);
        self.tb.node(s, kids).unwrap()
    }
    fn named(&mut self, op: Operator, name: &str, kids: &[NodeId]) -> NodeId {
        let s = self.spec(op).named(name);
        self.tb.node(s, kids).unwrap()
    }
    fn lit(&mut self, kind: &str, lexeme: &str) -> NodeId {
        self.add(Operator::lit(kind, lexeme), &[])
    }
    fn s(&mut self, text: &str) -> NodeId {
        self.lit("str", text)
    }
    fn op(&mut self, lexeme: &str, args: &[NodeId]) -> NodeId {
        let head = self.lit(OP, lexeme);
        let mut kids = vec![head];
        kids.extend_from_slice(args);
        self.add(Operator::apply(OP), &kids)
    }
    fn call(&mut self, callee: &str, args: &[NodeId]) -> NodeId {
        let head = self.add(Operator::reference(callee), &[]);
        let mut kids = vec![head];
        kids.extend_from_slice(args);
        self.add(Operator::apply("call"), &kids)
    }
    fn attr(&mut self, name: &str, value: Option<NodeId>) -> NodeId {
        let kids: Vec<NodeId> = value.into_iter().collect();
        self.named(markup::attribute_op(), name, &kids)
    }
    fn element(&mut self, tag: &str, attrs: &[NodeId], kids: &[NodeId]) -> NodeId {
        let head = self.lit(TAG, tag);
        let mut all = vec![head];
        all.extend_from_slice(attrs);
        all.extend_from_slice(kids);
        self.add(Operator::apply(ELEMENT), &all)
    }
    fn finish(self, root: NodeId) -> Model {
        Model::lexical(self.tb.finish(root).unwrap())
    }
}

fn str_of(m: &Model, n: NodeId) -> ConstValue {
    const_value(m, n)
}

#[test]
fn const_value_literals_and_forms() {
    let mut b = B::new("ts");
    let a = b.s("a");
    let c = b.s("-");
    let x = b.s("x");
    let cat = b.op(OP_ADD, &[a, c, x]);
    let one = b.lit("int", "1");
    let two = b.lit("int", "2");
    let sum = b.op(OP_ADD, &[one, two]);
    let t = b.lit("bool", "true");
    let yes = b.s("yes");
    let no = b.s("no");
    let pick = b.op(OP_COND, &[t, yes, no]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[cat, sum, pick]);
    let m = b.finish(root);
    assert_eq!(str_of(&m, cat).known_str(), Some("a-x"));
    assert_eq!(str_of(&m, sum), ConstValue::Known(Value::Int(3)));
    assert_eq!(str_of(&m, pick).known_str(), Some("yes"));
}

#[test]
fn const_value_one_of_fragments_and_unknown() {
    let mut b = B::new("ts");
    let dynamic = b.add(Operator::reference("props"), &[]);
    let (p, q) = (b.s("p"), b.s("q"));
    let either = b.op(OP_COND, &[dynamic, p, q]);
    let pre = b.s("btn-");
    let dyn2 = b.add(Operator::reference("size"), &[]);
    let tpl = b.op(OP_TEMPLATE, &[pre, dyn2]);
    let call = b.call("f", &[]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[either, tpl, call]);
    let m = b.finish(root);
    assert_eq!(
        str_of(&m, either),
        ConstValue::OneOf(vec![Value::Str("p".into()), Value::Str("q".into())])
    );
    assert_eq!(
        str_of(&m, tpl),
        ConstValue::Fragments(vec![Fragment::Known("btn-".into()), Fragment::Unknown])
    );
    assert_eq!(str_of(&m, call), ConstValue::Unknown);
}

#[test]
fn const_value_through_const_binding_and_objects() {
    let mut b = B::new("ts");
    let v = b.s("card");
    let base = b.named(Operator::unit(CONST_KIND, ""), "BASE", &[v]);
    let r = b.add(Operator::reference("BASE"), &[]);
    let (k, kv) = (b.s("w"), b.lit("int", "4"));
    let prop = b.op(OP_PROP, &[k, kv]);
    let obj = b.op(OP_OBJECT, &[prop]);
    let (e1, e2) = (b.s("a"), b.lit("bool", "false"));
    let arr = b.op(OP_ARRAY, &[e1, e2]);
    let missing = b.add(Operator::reference("NOPE"), &[]);
    let root = b.add(
        Operator::group(GroupOrder::Sequence),
        &[base, r, obj, arr, missing],
    );
    let m = b.finish(root);
    assert_eq!(str_of(&m, r).known_str(), Some("card"));
    assert_eq!(str_of(&m, missing), ConstValue::Unknown);
    let ConstValue::Known(Value::Object(o)) = str_of(&m, obj) else {
        panic!("object")
    };
    assert_eq!(o.get("w"), Some(&Value::Int(4)));
    assert_eq!(
        str_of(&m, arr),
        ConstValue::Known(Value::Array(vec![
            Value::Str("a".into()),
            Value::Bool(false)
        ]))
    );
}

#[test]
fn const_value_budget_exhaustion_keeps_known_prefix() {
    let mut b = B::new("ts");
    let parts: Vec<NodeId> = (0..10).map(|i| b.s(&i.to_string())).collect();
    let cat = b.op(OP_ADD, &parts);
    let m = b.finish(cat);
    let mut ev = ConstEval::new(&m, Budget(3));
    assert_eq!(
        ev.eval(cat),
        ConstValue::Fragments(vec![Fragment::Known("01".into()), Fragment::Unknown])
    );
    assert!(ev.exhausted());
    assert!(const_value(&m, cat).known_str().is_some());
}

#[test]
fn markup_elements_attributes_and_spread() {
    let mut b = B::new("tsx");
    let alt = b.s("logo");
    let a1 = b.attr("alt", Some(alt));
    let a2 = b.attr("disabled", None);
    let sp_expr = b.add(Operator::reference("props"), &[]);
    let sp = b.add(markup::spread_op(), &[sp_expr]);
    let text = b.lit(TEXT, "hi");
    let img = b.element("img", &[a1, a2, sp], &[text]);
    let head = b.add(Operator::reference("Button"), &[]);
    let comp = b.add(Operator::apply(ELEMENT), &[head, img]);
    let m = b.finish(comp);
    let els = markup::elements(&m);
    assert_eq!(els.len(), 2);
    let outer = &els[1];
    assert_eq!(outer.kind, TagKind::Component);
    assert_eq!(outer.tag.as_deref(), Some("Button"));
    let el = markup::element(&m, img).unwrap();
    assert_eq!(
        (el.tag.as_deref(), el.kind),
        (Some("img"), TagKind::Intrinsic)
    );
    assert!(el.has_spread());
    assert_eq!(el.children, vec![markup::Child::Text("hi".into())]);
    let alt_attr = el.attribute("alt").unwrap();
    assert_eq!(
        markup::attribute_value(&m, alt_attr).known_str(),
        Some("logo")
    );
    let dis = el.attribute("disabled").unwrap();
    assert_eq!(
        markup::attribute_value(&m, dis),
        ConstValue::Known(Value::Bool(true))
    );
    let spread = el.attributes.last().unwrap();
    assert_eq!((spread.is_spread(), spread.status), (true, Status::May));
    assert_eq!(markup::attribute_value(&m, spread), ConstValue::Unknown);
}

fn tokens_of(m: &Model, el: NodeId) -> markup::ClassTokens {
    let e = markup::element(m, el).unwrap();
    markup::element_class_tokens(m, &e)
}

#[test]
fn class_tokens_static_and_dynamic() {
    let mut b = B::new("tsx");
    let s = b.s("btn  primary");
    let a = b.attr("className", Some(s));
    let e1 = b.element("button", &[a], &[]);
    let pre = b.s("btn-");
    let size = b.add(Operator::reference("size"), &[]);
    let mid = b.s(" lg ");
    let tail = b.add(Operator::reference("extra"), &[]);
    let tpl = b.op(OP_TEMPLATE, &[pre, size, mid, tail]);
    let a2 = b.attr("class", Some(tpl));
    let e2 = b.element("div", &[a2], &[]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[e1, e2]);
    let m = b.finish(root);
    let t1 = tokens_of(&m, e1);
    assert!(t1.is_complete());
    assert_eq!(t1.must().collect::<Vec<_>>(), ["btn", "primary"]);
    let t2 = tokens_of(&m, e2);
    assert!(t2.dynamic);
    assert_eq!(t2.must().collect::<Vec<_>>(), ["lg"]);
}

#[test]
fn class_tokens_through_clsx_with_conditionals() {
    let mut b = B::new("tsx");
    let base = b.s("card");
    let flag = b.add(Operator::reference("active"), &[]);
    let on = b.s("on");
    let and = b.op(OP_AND, &[flag, on]);
    let key = b.s("bold");
    let val = b.add(Operator::reference("b"), &[]);
    let prop = b.op(OP_PROP, &[key, val]);
    let obj = b.op(OP_OBJECT, &[prop]);
    let unk = b.add(Operator::reference("other"), &[]);
    let call = b.call("clsx", &[base, and, obj, unk]);
    let a = b.attr("className", Some(call));
    let e = b.element("div", &[a], &[]);
    let m = b.finish(e);
    let t = tokens_of(&m, e);
    let got: Vec<_> = t
        .tokens
        .iter()
        .map(|t| (t.token.as_str(), t.status))
        .collect();
    assert_eq!(
        got,
        [
            ("card", Status::May),
            ("on", Status::May),
            ("bold", Status::May)
        ]
    );
    assert!(t.dynamic, "an unresolved argument is the dynamic remainder");
}

#[test]
fn class_tokens_spread_is_dynamic_and_other_attrs_ignored() {
    let mut b = B::new("tsx");
    let id = b.s("x y");
    let a = b.attr("id", Some(id));
    let props = b.add(Operator::reference("props"), &[]);
    let sp = b.add(markup::spread_op(), &[props]);
    let e = b.element("p", &[a], &[]);
    let e2 = b.element("p", &[sp], &[]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[e, e2]);
    let m = b.finish(root);
    let t = tokens_of(&m, e);
    assert!(t.tokens.is_empty() && t.is_complete());
    assert!(tokens_of(&m, e2).dynamic);
}

#[test]
fn style_rules_declarations_custom_properties_and_var_refs() {
    let mut b = B::new("css");
    let red = b.lit("color", "#f00");
    let d1 = b.named(style::declaration_op(), "color", &[red]);
    let var = b.add(Operator::reference("--gap"), &[]);
    let px = b.lit("dimension", "2px");
    let d2 = b.named(style::declaration_op(), "margin", &[px, var]);
    let rule = b.named(Operator::unit(style::STYLE_RULE, ""), ".a", &[d1, d2]);
    let def_v = b.lit("dimension", "8px");
    let def = b.named(
        Operator::unit(style::CUSTOM_PROPERTY, ""),
        "--gap",
        &[def_v],
    );
    let root_rule = b.named(Operator::unit(style::STYLE_RULE, ""), ":root", &[def]);
    let inner = b.named(Operator::unit(style::STYLE_RULE, ""), ".b", &[]);
    let media_spec = b
        .spec(Operator::unit(style::AT_RULE, ""))
        .named("media")
        .attr(style::PRELUDE, "(min-width: 1px)");
    let media = b.tb.node(media_spec, &[inner]).unwrap();
    let root = b.add(
        Operator::group(GroupOrder::Sequence),
        &[rule, root_rule, media],
    );
    let m = b.finish(root);
    let sels: Vec<_> = style::style_rules(&m)
        .into_iter()
        .map(|r| r.selector)
        .collect();
    assert_eq!(sels, [".a", ":root", ".b"]);
    let ds = style::declarations(&m);
    assert_eq!(ds.len(), 2);
    assert_eq!(ds[0].property, "color");
    assert_eq!(ds[0].owner, Some(rule));
    assert_eq!(
        ds[1].values[0],
        ValuePart::Lit {
            kind: "dimension".into(),
            text: "2px".into()
        }
    );
    let cps = style::custom_properties(&m);
    assert_eq!(
        (cps[0].name.as_str(), cps[0].owner),
        ("--gap", Some(root_rule))
    );
    let vars = style::var_refs(&m);
    assert_eq!(vars.len(), 1);
    assert_eq!(
        (vars[0].name.as_str(), vars[0].status),
        ("--gap", Status::May)
    );
    let ats = style::at_rules(&m);
    assert_eq!(
        (ats[0].name.as_str(), ats[0].prelude.as_str()),
        ("media", "(min-width: 1px)")
    );
}

// ---- logical operators, spreads, cycles and the external hook (~C2F4ZMQ) ----

#[test]
fn const_value_logical_operators_follow_javascript_truthiness() {
    let mut b = B::new("ts");
    let (l, r) = (b.s("left"), b.s("right"));
    let or_true = b.op(OP_OR, &[l, r]);
    let (e, r2) = (b.s(""), b.s("right"));
    let or_false = b.op(OP_OR, &[e, r2]);
    let (t, v) = (b.lit("bool", "true"), b.s("v"));
    let and_true = b.op(OP_AND, &[t, v]);
    let (dynamic, v2) = (b.add(Operator::reference("flag"), &[]), b.s("v"));
    let and_dyn = b.op(OP_AND, &[dynamic, v2]);
    let root = b.add(
        Operator::group(GroupOrder::Sequence),
        &[or_true, or_false, and_true, and_dyn],
    );
    let m = b.finish(root);
    assert_eq!(str_of(&m, or_true).known_str(), Some("left"));
    assert_eq!(str_of(&m, or_false).known_str(), Some("right"));
    assert_eq!(str_of(&m, and_true).known_str(), Some("v"));
    assert_eq!(
        str_of(&m, and_dyn),
        ConstValue::OneOf(vec![Value::Bool(false), Value::Str("v".into())])
    );
}

#[test]
fn const_value_spreads_splice_known_arrays_and_objects() {
    let mut b = B::new("ts");
    let (x, y) = (b.s("x"), b.s("y"));
    let inner = b.op(OP_ARRAY, &[x, y]);
    let spread = b.op(OP_SPREAD, &[inner]);
    let z = b.s("z");
    let arr = b.op(OP_ARRAY, &[spread, z]);
    let rest = b.add(Operator::reference("rest"), &[]);
    let bad_spread = b.op(OP_SPREAD, &[rest]);
    let bad = b.op(OP_ARRAY, &[bad_spread]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[arr, bad]);
    let m = b.finish(root);
    assert_eq!(
        str_of(&m, arr),
        ConstValue::Known(Value::Array(vec![
            Value::Str("x".into()),
            Value::Str("y".into()),
            Value::Str("z".into())
        ]))
    );
    assert_eq!(str_of(&m, bad), ConstValue::Unknown);
}

#[test]
fn const_value_templates_distribute_over_alternatives() {
    let mut b = B::new("ts");
    let pre = b.s("app-");
    let c = b.add(Operator::reference("c"), &[]);
    let (p, q) = (b.s("a"), b.s("b"));
    let pick = b.op(OP_COND, &[c, p, q]);
    let tpl = b.op(OP_TEMPLATE, &[pre, pick]);
    let m = b.finish(tpl);
    assert_eq!(
        str_of(&m, tpl),
        ConstValue::OneOf(vec![Value::Str("app-a".into()), Value::Str("app-b".into())])
    );
}

#[test]
fn const_value_reference_cycles_are_flagged_not_looped() {
    let mut b = B::new("ts");
    let rb = b.add(Operator::reference("B"), &[]);
    let a = b.named(Operator::unit(CONST_KIND, ""), "A", &[rb]);
    let ra = b.add(Operator::reference("A"), &[]);
    let bb = b.named(Operator::unit(CONST_KIND, ""), "B", &[ra]);
    let use_a = b.add(Operator::reference("A"), &[]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[a, bb, use_a]);
    let m = b.finish(root);
    let mut ev = ConstEval::new(&m, Budget::default());
    assert_eq!(ev.eval(use_a), ConstValue::Unknown);
    assert!(ev.cyclic());
    assert!(!ev.exhausted());
}

/// A hook that knows `cn` as a class-name joiner and resolves `EXT` to a fixed string.
struct Hook;

impl ExternalRefs for Hook {
    fn resolve_ref(&self, model: &Model, node: NodeId, _steps: u32) -> Option<External> {
        match model.term().operator(node) {
            Operator::Universal(gob_ir::Universal::Ref { name }) if name == "EXT" => {
                Some(External {
                    value: ConstValue::Known(Value::Str("far".into())),
                    used: 2,
                    exhausted: false,
                    cyclic: false,
                })
            }
            _ => None,
        }
    }

    fn call_kind(&self, model: &Model, callee: NodeId) -> Option<CallKind> {
        match model.term().operator(callee) {
            Operator::Universal(gob_ir::Universal::Ref { name }) if name == "cn" => {
                Some(CallKind::ClassNames)
            }
            _ => None,
        }
    }
}

#[test]
fn const_value_external_hook_resolves_refs_and_joins_class_names() {
    let mut b = B::new("ts");
    let ext = b.add(Operator::reference("EXT"), &[]);
    let (a, flag) = (b.s("btn"), b.add(Operator::reference("on"), &[]));
    let on = b.s("on");
    let cond = b.op(OP_AND, &[flag, on]);
    let obj_key = b.s("big");
    let t = b.lit("bool", "true");
    let prop = b.op(OP_PROP, &[obj_key, t]);
    let obj = b.op(OP_OBJECT, &[prop]);
    let joined = b.call("cn", &[a, cond, ext, obj]);
    let other = b.call("other", &[a]);
    let root = b.add(Operator::group(GroupOrder::Sequence), &[ext, joined, other]);
    let m = b.finish(root);
    let hook = Hook;
    let mut ev = ConstEval::new(&m, Budget(100)).with_external(&hook);
    assert_eq!(ev.eval(ext).known_str(), Some("far"));
    assert_eq!(ev.remaining(), 100 - 1 - 2);
    assert_eq!(
        ev.eval(joined),
        ConstValue::OneOf(vec![
            Value::Str("btn far big".into()),
            Value::Str("btn on far big".into())
        ])
    );
    assert_eq!(ev.eval(other), ConstValue::Unknown);
}
