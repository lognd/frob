//! Element, variant and std-return type inference: each narrowing has a positive case (the call is
//! Must) and a case that must stay May, because a guess here would be a wrong coverage claim.

// frob:ticket 01M3ZVQAA1DNM1BJ5TZG5B3CFR

use gob_symbols::{EdgeKind, FileSymbols, Status, SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn extract(path: &str, text: &str) -> FileSymbols {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    extract_file(&entry, text)
}

/// The graph of one crate file holding `body` after the shared `Foo`/`Bar` prelude.
fn graph(body: &str) -> SymbolGraph {
    let text = format!("{PRELUDE}\n{body}\n");
    SymbolGraph::from_files(vec![extract("c/src/lib.rs", &text)])
}

/// Two unrelated types with a method of the same name: a call is Must only when its receiver is proven.
const PRELUDE: &str = "\
use std::collections::HashMap;
pub struct Foo;
impl Foo { pub fn go(&self) {} pub fn me(&self) -> Foo { Foo } }
pub struct Bar;
impl Bar { pub fn go(&self) {} }
pub struct Holder { pub items: Vec<Foo>, pub by_name: HashMap<String, Foo>, pub one: Option<Foo> }
pub enum Kind { Tuple(Foo), Named { inner: Foo }, Plain }
pub fn make() -> Vec<Foo> { Vec::new() }
pub fn unknown() -> Vec<Bar> { Vec::new() }
pub fn mystery() -> Box<dyn Iterator<Item = Foo>> { todo!() }
";

type Edge = (String, Status);

/// The targets of `caller`'s edges whose symref contains `needle`, with their status, sorted.
fn edges_to(g: &SymbolGraph, caller: &str, needle: &str) -> Vec<Edge> {
    let from = format!("c/src/lib.rs::{caller}");
    let mut v: Vec<Edge> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string() == from)
        .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
        .filter(|(t, _)| t.contains(needle))
        .collect();
    v.sort();
    v.dedup();
    v
}

/// The `go` call edges out of `caller`.
fn go_edges(g: &SymbolGraph, caller: &str) -> Vec<Edge> {
    edges_to(g, caller, ".go")
}

/// Asserts the only `go` target of `caller` is `Foo.go`, Must.
fn assert_foo_must(g: &SymbolGraph, caller: &str) {
    assert_eq!(
        go_edges(g, caller),
        vec![("c/src/lib.rs::Foo.go".to_owned(), Status::Must)],
        "{caller}"
    );
}

/// Asserts `caller` reaches both `go` methods, only as May.
fn assert_both_may(g: &SymbolGraph, caller: &str) {
    let edges = go_edges(g, caller);
    assert_eq!(edges.len(), 2, "{caller}: {edges:?}");
    assert!(
        edges.iter().all(|(_, s)| *s == Status::May),
        "{caller}: {edges:?}"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn enum_variant_fields_type_match_and_if_let_bindings() {
    let g = graph(
        "pub fn t1(k: Kind) { match k { Kind::Tuple(x) => x.go(), _ => {} } }
         pub fn t2(k: Kind) { match k { Kind::Named { inner } => inner.go(), _ => {} } }
         pub fn t3(k: Kind) { if let Kind::Tuple(x) = k { x.go() } }
         pub fn t4(k: Kind) { match k { Kind::Named { inner: z } => z.go(), _ => {} } }
         pub fn s1(k: Kind) { match k { Kind::Tuple(x) | Kind::Named { inner: x } => x.go(), _ => {} } }
         pub fn s2(k: Kind, x: Bar) { if let Kind::Tuple(y) = k { } x.go() }
         pub fn s3(k: Other) { match k { Other::Tuple(x) => x.go(), _ => {} } }
         pub fn s4(k: Kind) { match k { Tuple(x) => x.go(), _ => {} } }",
    );
    for t in ["t1", "t2", "t3", "t4"] {
        assert_foo_must(&g, t);
    }
    // An or-pattern, an enum of another name and an unqualified variant stay unknown receivers.
    for s in ["s1", "s3", "s4"] {
        assert_both_may(&g, s);
    }
    // The binding does not leak out of its arm: `x` after the `if let` is the parameter.
    assert_eq!(
        go_edges(&g, "s2"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn unit_variants_and_variant_constructors_are_their_enum() {
    let g = graph(
        "impl Kind { pub fn go(&self) {} }
         pub fn t1() { Kind::Plain.go() }
         pub fn t2() { Kind::Tuple(Foo).go() }
         pub fn t3() { Kind::Named { inner: Foo }.go() }
         pub fn s1() { Other::Plain.go() }",
    );
    for t in ["t1", "t2", "t3"] {
        assert_eq!(
            go_edges(&g, t),
            vec![("c/src/lib.rs::Kind.go".to_owned(), Status::Must)],
            "{t}"
        );
    }
    // `Other` is no enum of this crate: nothing is proven, every `go` stays possible.
    let s1 = go_edges(&g, "s1");
    assert!(
        s1.len() >= 2 && s1.iter().all(|(_, s)| *s == Status::May),
        "{s1:?}"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn for_loops_type_their_variable_by_the_collection() {
    let g = graph(
        "pub fn t1(items: Vec<Foo>) { for x in items { x.go() } }
         pub fn t2(items: &[Foo]) { for x in items { x.go() } }
         pub fn t3(items: &[Foo; 3]) { for x in items.iter() { x.go() } }
         pub fn t4(h: &Holder) { for x in &h.items { x.go() } }
         pub fn t5(h: &Holder) { for (_, x) in &h.by_name { x.go() } }
         pub fn t6(h: &Holder) { for x in h.by_name.values() { x.go() } }
         pub fn t7() { for x in make() { x.go() } }
         pub fn t8(items: Vec<Foo>) { for (i, x) in items.iter().enumerate() { x.go(); let _ = i; } }
         pub fn t9(items: Vec<Foo>) { for x in items.iter().rev().skip(1).filter(|_| true) { x.go() } }
         pub fn s1(items: Vec<Foo>) { for x in other() { x.go() } }
         pub fn s2(items: Vec<_>) { for x in items { x.go() } }
         pub fn s3(items: Vec<Foo>) { for x in items.iter().zip(items.iter()) { x.0.go() } }
         pub fn s4(items: Vec<Foo>) { for x in items.iter().map(|x| other(x)) { x.go() } }
         pub fn s5(items: Vec<Foo>, x: Bar) { for x in items { } x.go() }
         pub fn s6(items: Vec<Foo>) { for x in items { let x = other(); x.go() } }",
    );
    for t in ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"] {
        assert_foo_must(&g, t);
    }
    // Unknown iterable, `_` element, zip (not modelled), a map whose closure result is unknown, a shadow.
    for s in ["s1", "s2", "s3", "s4", "s6"] {
        assert_both_may(&g, s);
    }
    // The loop variable does not outlive the loop.
    assert_eq!(
        go_edges(&g, "s5"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn map_and_option_lookups_type_their_results() {
    let g = graph(
        "pub fn t1(h: &Holder) { if let Some(x) = h.by_name.get(\"k\") { x.go() } }
         pub fn t2(h: &Holder) { match h.by_name.get(\"k\") { Some(x) => x.go(), None => {} } }
         pub fn t3(h: &Holder) { h.by_name.get(\"k\").unwrap().go() }
         pub fn t4(h: &Holder) { if let Some(x) = &h.one { x.go() } }
         pub fn t5(h: &Holder) { h.one.as_ref().unwrap_or_else(|| other()).go() }
         pub fn t6(h: &Holder) { if let Some(x) = h.items.first() { x.go() } }
         pub fn t7(h: &Holder) { while let Some(x) = h.items.clone().pop() { x.go() } }
         pub fn t8(h: &Holder) { if let Some(x) = h.items.get(0) { x.go() } }
         pub fn s1(h: &Holder) { if let Some(x) = h.items.get(1..2) { x.go() } }
         pub fn s2(h: &Holder) { if let Some(x) = other() { x.go() } }
         pub fn s3(h: &Holder) { if let Err(x) = h.by_name.get(\"k\") { x.go() } }
         pub fn s4(h: &Holder, x: Bar) { if let Some(x) = h.one.as_ref() { } x.go() }",
    );
    for t in ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"] {
        assert_foo_must(&g, t);
    }
    // A range `get` is a slice, an unknown source and an `Err` payload are untyped.
    for s in ["s1", "s2", "s3"] {
        assert_both_may(&g, s);
    }
    assert_eq!(
        go_edges(&g, "s4"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn closure_parameters_take_the_item_of_a_typed_iterator() {
    let g = graph(
        "pub fn t1(items: Vec<Foo>) { items.iter().for_each(|x| x.go()) }
         pub fn t2(items: Vec<Foo>) -> bool { items.iter().any(|x| { x.go(); true }) }
         pub fn t3(items: Vec<Foo>) { items.iter().filter(|x| { x.go(); true }).count(); }
         pub fn t4(h: &Holder) { h.one.as_ref().map(|x| x.go()); }
         pub fn t5(items: Vec<Foo>) { items.iter().fold(0, |n, x| { x.go(); n }); }
         pub fn t6(items: Vec<Foo>) { items.iter().enumerate().for_each(|(_, x)| x.go()) }
         pub fn t7(mut items: Vec<Foo>) { items.retain(|x| { x.go(); true }) }
         pub fn t8(items: Vec<Foo>) { items.iter().for_each(|x: &Bar| x.go()) }
         pub fn s1() { other().iter().for_each(|x| x.go()) }
         pub fn s2(h: &Holder) { h.by_name.iter().for_each(|x| x.go()) }
         pub fn s3(mut h: Holder) { h.by_name.retain(|k, v| { v.go(); true }) }
         pub fn s4(items: Vec<Foo>) { items.iter().for_each(|x| { let x = other(); x.go() }) }
         pub fn s5(items: Vec<Foo>, x: Bar) { items.iter().for_each(|x| ()); x.go() }",
    );
    for t in ["t1", "t2", "t3", "t4", "t5", "t6", "t7"] {
        assert_foo_must(&g, t);
    }
    // An annotation wins over the item type.
    assert_eq!(
        go_edges(&g, "t8"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
    // Unknown iterator; `retain` on a map takes two parameters; a shadowing `let`.
    for s in ["s1", "s3", "s4"] {
        assert_both_may(&g, s);
    }
    // A map iterates (key, value) tuples: `|x|` is one, and a tuple has neither `go`.
    assert!(go_edges(&g, "s2").is_empty());
    assert_eq!(
        go_edges(&g, "s5"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn closure_results_and_collects_keep_their_item_type() {
    let g = graph(
        "pub fn t1(items: Vec<Foo>) { items.iter().map(|x| x.me()).for_each(|m| m.go()) }
         pub fn t2(items: Vec<Foo>) { let v: Vec<_> = items.iter().map(|x| x.me()).collect(); v[0].go() }
         pub fn t3(items: Vec<Foo>) { let v: Vec<_> = items.iter().collect(); for x in &v { x.go() } }
         pub fn t4(items: Vec<Foo>) { let v = items.iter().cloned().collect::<Vec<_>>(); v[0].go() }
         pub fn t5(h: &Holder) { h.one.as_ref().and_then(|x| Some(x)).unwrap().go() }
         pub fn s1(items: Vec<Foo>) { let v: Vec<_> = other().collect(); v[0].go() }
         pub fn s2(items: Vec<Foo>) { items.iter().map(|x| other(x)).for_each(|m| m.go()) }
         pub fn s3(items: Vec<Foo>) { let v: Vec<_> = items.iter().map(|x| other(x)).collect(); v[0].go() }",
    );
    for t in ["t1", "t2", "t3", "t4"] {
        assert_foo_must(&g, t);
    }
    // `and_then`'s closure returns an `Option` this crate cannot see through: untyped.
    for s in ["t5", "s1", "s2", "s3"] {
        assert_both_may(&g, s);
    }
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn slices_arrays_and_indexing_type_their_elements() {
    let g = graph(
        "pub fn t1(items: &[Foo]) { items[0].go() }
         pub fn t2(items: [Foo; 2]) { items[1].go() }
         pub fn t3(items: Vec<Foo>) { items[1..].iter().for_each(|x| x.go()) }
         pub fn t4(h: &Holder) { h.by_name[\"k\"].go() }
         pub fn s1(items: &[Foo]) { items[1..][0].go() }
         pub fn s2(h: &Holder) { h.items[other()].go(); other()[0].go() }",
    );
    for t in ["t1", "t2", "t4"] {
        assert_foo_must(&g, t);
    }
    // A slice of a Vec is a slice of Foo (`[]` head keeps the element), so t3 is typed too.
    assert_foo_must(&g, "t3");
    // Indexing the slice again stays typed; `other()[0]` is unknown, so the caller keeps May edges.
    assert_foo_must(&g, "s1");
    assert!(go_edges(&g, "s2").iter().any(|(_, s)| *s == Status::May));
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn std_method_results_exclude_repository_methods() {
    let g = graph(
        "pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } pub fn is_empty(&self) -> bool { true } }
         pub struct Sink; impl Sink { pub fn len(&self) -> usize { 0 } }
         pub fn t1(s: &str) { s.trim().len(); }
         pub fn t2(s: String) { s.to_lowercase().is_empty(); }
         pub fn t3(s: &str) { for l in s.lines() { l.trim().len(); } }
         pub fn t4(s: &str) { s.split(',').map(|p| p.len()).count(); }
         pub fn t5(s: &str) { let t = &s[1..]; t.len(); }
         pub fn t6() { format!(\"{}\", 1).len(); \"lit\".len(); (1..3).contains(&2); }
         pub fn t7(v: Vec<Foo>) { v.len(); v.iter().count(); }
         pub fn s1() { other().len(); }
         pub fn s2(s: &str) { s.parse::<u8>().unwrap().len(); }",
    );
    for t in ["t1", "t2", "t3", "t4", "t5", "t6", "t7"] {
        assert!(
            edges_to(&g, t, ".len").is_empty() && edges_to(&g, t, ".is_empty").is_empty(),
            "{t}: {:?}",
            edges_to(&g, t, ".")
        );
    }
    for s in ["s1", "s2"] {
        let e = edges_to(&g, s, ".len");
        assert_eq!(e.len(), 2, "{s}: {e:?}");
        assert!(e.iter().all(|(_, st)| *st == Status::May));
    }
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn std_functions_and_paths_have_known_return_types() {
    let g = graph(
        "use std::fs;
         use std::path::{Path, PathBuf};
         pub struct Node; impl Node { pub fn parent(&self) {} pub fn path(&self) {} }
         pub struct Failure; impl Failure { pub fn code(&self) {} }
         pub fn t1(p: &Path) { p.join(\"a\").parent(); }
         pub fn t2(p: PathBuf) { p.parent().unwrap().to_path_buf().file_name(); }
         pub fn t3() { fs::read_to_string(\"x\").unwrap().trim().len(); Path::new(\"a\").parent(); }
         pub fn t4() { std::fs::read_to_string(\"x\").unwrap_or_default().lines().count(); }
         pub fn t5(e: std::process::Output) { e.status.code(); e.stdout.len(); }
         pub fn s1(p: &Path) { other().parent(); }",
    );
    for t in ["t1", "t2", "t3", "t4", "t5"] {
        assert!(
            edges_to(&g, t, ".parent").is_empty(),
            "{t}: {:?}",
            edges_to(&g, t, ".")
        );
    }
    assert!(edges_to(&g, "t5", ".code").is_empty());
    assert_eq!(edges_to(&g, "s1", ".parent").len(), 1);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn a_repository_type_named_like_a_standard_one_vetoes_the_std_tables() {
    let g = graph(
        "pub struct Vec { pub items: Foo }
         impl Vec { pub fn iter(&self) -> Foo { Foo } pub fn go(&self) {} }
         pub fn s1(v: Vec) { v.iter().go(); }",
    );
    // `Vec` here is the repository's own: `iter` is its method, not the standard `Vec::iter`.
    assert_eq!(
        go_edges(&g, "s1"),
        vec![("c/src/lib.rs::Foo.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn constants_and_associated_constants_are_typed_by_their_declaration() {
    let g = graph(
        "pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } }
         const NAMES: &[&str] = &[\"a\"];
         const DUP: &[&str] = &[\"a\"];
         mod inner { pub const DUP: Foo = Foo; }
         pub struct Table;
         impl Table { pub const ALL: [Foo; 2] = [Foo, Foo]; pub fn run() { for x in Self::ALL.iter() { x.go() } } }
         pub fn t1() { NAMES.len(); NAMES.contains(&\"a\"); }
         pub fn t2() { for x in Table::ALL { x.go() } }
         pub fn t3() { for x in Table::ALL.iter() { x.go() } }
         pub fn s1() { DUP.len(); }
",
    );
    assert!(edges_to(&g, "t1", ".len").is_empty());
    assert_foo_must(&g, "t2");
    assert_foo_must(&g, "t3");
    assert_eq!(
        go_edges(&g, "Table.run"),
        vec![("c/src/lib.rs::Foo.go".to_owned(), Status::Must)]
    );
    // A name declared twice in the file is not typed.
    assert_eq!(edges_to(&g, "s1", ".len").len(), 1);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn a_wildcard_keeps_the_position_of_the_tuple_elements() {
    let g = graph(
        "pub fn pair() -> (Bar, Foo) { (Bar, Foo) }
         pub fn t1() { let (_, b) = pair(); b.go() }
         pub fn t2() { let (a, _) = pair(); a.go() }
         pub fn t3() { let (a, ..) = pair(); a.go() }
         pub fn t4() { let (.., b) = pair(); b.go() }
         pub fn t5(x: Foo) { let (a, b) = (x, Bar); a.go(); b.go(); }
         pub fn t6(x: Foo) { match (x, other()) { (a, _) => a.go() } }",
    );
    assert_foo_must(&g, "t1");
    assert_eq!(
        go_edges(&g, "t2"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
    assert_eq!(
        go_edges(&g, "t3"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
    // After `..` the positions are unknown: no typing at all.
    assert_both_may(&g, "t4");
    assert_eq!(go_edges(&g, "t5").len(), 2);
    assert!(go_edges(&g, "t5").iter().all(|(_, s)| *s == Status::Must));
    assert_foo_must(&g, "t6");
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn an_inferred_placeholder_is_not_a_type() {
    let g = graph(
        "pub fn s1(v: Vec<_>) { for x in v { x.go() } }
         pub fn s2() { let v: Vec<_> = other(); v[0].go() }
         pub fn s3() { let v: Vec<_> = Vec::new(); v.iter().for_each(|x| x.go()) }",
    );
    for s in ["s1", "s2", "s3"] {
        assert_both_may(&g, s);
    }
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn trait_objects_inside_containers_dispatch_through_the_trait() {
    let g = graph(
        "pub trait Tr { fn act(&self); }
         pub struct A; impl Tr for A { fn act(&self) {} }
         pub struct B; impl Tr for B { fn act(&self) {} }
         pub struct Reg { pub all: Vec<Box<dyn Tr>>, pub one: std::sync::Arc<dyn Tr> }
         pub fn t1(r: &Reg) { for t in &r.all { t.act() } }
         pub fn t2(ts: &[std::sync::Arc<dyn Tr>]) { ts.iter().for_each(|t| t.act()) }
         pub fn s1() { for t in other() { t.act() } }",
    );
    let act = |c: &str| edges_to(&g, c, ".act");
    for t in ["t1", "t2"] {
        let e = act(t);
        // Must to the trait declaration, May to every implementation.
        assert!(
            e.contains(&("c/src/lib.rs::Tr.act".to_owned(), Status::Must)),
            "{t}: {e:?}"
        );
        assert!(
            e.iter().filter(|(_, s)| *s == Status::May).count() >= 2,
            "{t}: {e:?}"
        );
    }
    // An unknown source is only possible, never proven.
    assert!(act("s1").iter().all(|(_, s)| *s == Status::May));
    assert!(!act("s1").is_empty());
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn impl_iterator_returns_and_cells_are_typed() {
    let g = graph(
        "use std::cell::RefCell;
         use std::sync::Mutex;
         pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } }
         pub fn items() -> impl Iterator<Item = &'static Foo> { std::iter::empty() }
         pub struct Cells { pub c: RefCell<Foo>, pub m: Mutex<Foo>, pub v: RefCell<Vec<Foo>> }
         impl Cells {
             pub fn t1(&self) { for x in items() { x.go() } }
             pub fn t2(&self) { self.c.borrow().go(); self.c.borrow_mut().go(); }
             pub fn t3(&self) { self.m.lock().unwrap().go() }
             pub fn t4(&self) { self.v.borrow().len(); }
             pub fn s1(&self) { self.m.lock().go() }
         }",
    );
    assert_foo_must(&g, "Cells.t1");
    assert_foo_must(&g, "Cells.t2");
    assert_foo_must(&g, "Cells.t3");
    // The borrowed `Vec` is a standard type: its `len` is not the repository's.
    assert!(edges_to(&g, "Cells.t4", ".len").is_empty());
    // `lock()` is a `Result`, not the guarded `Foo`: the `go` call is not proven.
    assert!(
        go_edges(&g, "Cells.s1")
            .iter()
            .all(|(_, s)| *s != Status::Must)
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn macro_arguments_scope_their_closure_parameters() {
    let g = graph(
        "pub fn t1(items: Vec<Foo>) { assert!(items.iter().any(|x| { x.go(); true })); }
         pub fn t2(k: Kind) { assert!(matches!(k, Kind::Tuple(ref x) if { x.go(); true })); }
         pub fn t3(items: Vec<Foo>) { let n = vec![items.iter().filter(|x| { x.go(); true }).count(); 2]; }
         pub fn t4(items: Vec<Foo>, x: Bar) { assert!(items.iter().any(|x| true), \"{}\", x.go()); }
         pub fn s1(items: Vec<Foo>) { assert!(other().iter().any(|x| { x.go(); true })); }
         pub fn s2(items: Vec<Foo>) { assert!(items.iter().any(|x| { let x = other(); x.go(); true })); }",
    );
    assert_foo_must(&g, "t1");
    assert_foo_must(&g, "t2");
    assert_foo_must(&g, "t3");
    // The closure's `x` is gone after the closure: the message argument sees the parameter `x: Bar`.
    assert_eq!(
        go_edges(&g, "t4"),
        vec![("c/src/lib.rs::Bar.go".to_owned(), Status::Must)]
    );
    // Calls in a macro stay capped at May unless the macro is a std one; an untyped source stays May.
    assert_both_may(&g, "s1");
    assert_both_may(&g, "s2");
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn crate_paths_resolve_in_source_files_only() {
    let lib = "pub mod util { pub fn load<T>() {} pub struct S; impl S { pub fn open() {} } }
               pub fn load<T>() {}
               pub fn t1() { crate::load::<u8>(); crate::util::load::<u8>(); crate::util::S::open(); }
               pub fn s1() { crate::missing(); }
               pub fn s2() { self::load::<u8>(); }";
    let g = SymbolGraph::from_files(vec![extract("c/src/lib.rs", lib)]);
    let edges = |c: &str| {
        let from = format!("c/src/lib.rs::{c}");
        g.edges_with_status()
            .iter()
            .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string() == from)
            .map(|e| (e.to.as_ref().map(ToString::to_string), e.status))
            .collect::<Vec<_>>()
    };
    let t1 = edges("t1");
    assert_eq!(t1.len(), 3, "{t1:?}");
    assert!(
        t1.iter().all(|(t, s)| t.is_some() && *s == Status::Must),
        "{t1:?}"
    );
    assert_eq!(edges("s1"), vec![(None, Status::Unknown)]);
    // `self::` depends on inline modules the file alone cannot name: left unresolved.
    assert_eq!(edges("s2"), vec![(None, Status::Unknown)]);
    // An integration test file is its own crate: `crate::` there is not this library's root.
    let test = SymbolGraph::from_files(vec![
        extract("c/src/lib.rs", lib),
        extract(
            "c/tests/it.rs",
            "pub fn load<T>() {}\n#[test] fn t() { crate::load::<u8>(); }\n",
        ),
    ]);
    let t: Vec<_> = test
        .edges_with_status()
        .iter()
        .filter(|e| e.from.to_string() == "c/tests/it.rs::t")
        .map(|e| e.status)
        .collect();
    assert_eq!(t, vec![Status::Unknown]);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn derived_traits_reach_the_declaring_trait_or_generated_std_code() {
    let g = SymbolGraph::from_files(vec![
        extract(
            "c/src/lib.rs",
            "pub trait Schema { fn describe() -> Desc; fn name(&self) -> u8; }
             pub struct Desc; impl Desc { pub fn docs(&self) {} }
             pub struct Other; impl Other { pub fn docs(&self) {} }",
        ),
        extract(
            "c/src/user.rs",
            "#[derive(Default, Clone, Schema)]
             pub struct Mine { pub n: u8 }
             #[derive(Default)]
             pub struct Plain;
             pub fn t1() { Mine::describe().docs(); }
             pub fn t2(m: &Mine) { m.name(); }
             pub fn t3() { Mine::default(); Plain::default(); }
             pub fn t4(m: &Mine) { m.clone(); }
             pub fn s1(p: &Plain) { p.name(); }
             pub fn s2() { Plain::describe(); }",
        ),
    ]);
    let edges = |c: &str| {
        let from = format!("c/src/user.rs::{c}");
        g.edges_with_status()
            .iter()
            .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string() == from)
            .map(|e| (e.to.as_ref().map(ToString::to_string), e.status))
            .collect::<Vec<_>>()
    };
    let must = |t: &str| (Some(t.to_owned()), Status::Must);
    let t1 = edges("t1");
    // `describe()` reaches the trait declaration and its declared return type types `.docs()`.
    assert!(
        t1.contains(&must("c/src/lib.rs::Schema.describe")),
        "{t1:?}"
    );
    assert!(t1.contains(&must("c/src/lib.rs::Desc.docs")), "{t1:?}");
    assert!(
        !t1.iter()
            .any(|(t, _)| t.as_deref() == Some("c/src/lib.rs::Other.docs"))
    );
    assert_eq!(edges("t2"), vec![must("c/src/lib.rs::Schema.name")]);
    // Standard derives generate code outside the repository: no edge, nothing unknown.
    assert!(edges("t3").is_empty(), "{:?}", edges("t3"));
    assert!(edges("t4").is_empty(), "{:?}", edges("t4"));
    // `Plain` does not derive `Schema`: the call stays unproven (unknown or only possible).
    for c in ["s1", "s2"] {
        assert!(
            edges(c).iter().all(|(_, s)| *s != Status::Must),
            "{c}: {:?}",
            edges(c)
        );
    }
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn unit_struct_values_and_struct_literals_are_typed() {
    let g = graph(
        "pub struct Unit; impl Unit { pub fn go(&self) {} }
         pub enum E { Unit }
         pub fn t1() { Unit.go() }
         pub fn t2() { Holder { items: Vec::new(), by_name: HashMap::new(), one: None }.items.iter().for_each(|x| x.go()) }
         pub fn s1() { Missing.go() }",
    );
    assert_eq!(
        go_edges(&g, "t1").first(),
        Some(&("c/src/lib.rs::Unit.go".to_owned(), Status::Must))
    );
    assert_foo_must(&g, "t2");
    // `Missing` names no struct of the crate.
    assert!(go_edges(&g, "s1").iter().all(|(_, s)| *s == Status::May));
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn a_type_declared_once_in_the_calling_file_is_that_type() {
    let a = "pub struct Fx; impl Fx { pub fn only_a(&self) {} pub fn shared(&self) {} }
             pub fn t(f: Fx) { f.only_a(); }";
    let b = "pub struct Fx; impl Fx { pub fn only_b(&self) {} pub fn shared(&self) {} }
             pub fn t(f: Fx) { f.only_b(); f.shared(); }";
    let g = SymbolGraph::from_files(vec![extract("c/tests/a.rs", a), extract("c/tests/b.rs", b)]);
    let calls = |file: &str| {
        g.edges_with_status()
            .iter()
            .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string() == format!("{file}::t"))
            .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
            .collect::<Vec<_>>()
    };
    // Integration tests are separate crates: each file's `Fx` is its own.
    assert_eq!(
        calls("c/tests/a.rs"),
        vec![("c/tests/a.rs::Fx.only_a".to_owned(), Status::Must)]
    );
    let b_calls = calls("c/tests/b.rs");
    assert!(b_calls.contains(&("c/tests/b.rs::Fx.only_b".to_owned(), Status::Must)));
    // `shared` exists on both `Fx`: not provably this file's.
    assert!(
        b_calls
            .iter()
            .filter(|(t, _)| t.ends_with(".shared"))
            .all(|(_, s)| *s == Status::May)
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn json_values_and_clone_and_to_string_are_typed_without_repository_types() {
    let g = graph(
        "use serde_json::Value;
         pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } pub fn is_empty(&self) -> bool { true } }
         pub fn t1(v: &Value) { v[\"a\"].as_array().unwrap().len(); v.get(\"b\").unwrap().as_str(); }
         pub fn t2(v: &Value) { for x in v[\"a\"].as_array().unwrap() { x[\"k\"].as_str().unwrap().len(); } }
         pub fn t3(f: Foo) { f.clone().go(); f.me().clone().go(); }
         pub fn t4(f: Foo) { f.to_string().len(); }
         pub fn s1(v: &Other) { v[\"a\"].as_array().unwrap().len(); }",
    );
    assert!(
        edges_to(&g, "t1", ".len").is_empty(),
        "{:?}",
        edges_to(&g, "t1", ".")
    );
    assert!(edges_to(&g, "t2", ".len").is_empty());
    assert_foo_must(&g, "t3");
    assert!(edges_to(&g, "t4", ".len").is_empty());
    assert_eq!(edges_to(&g, "s1", ".len").len(), 1);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn to_string_is_unknown_when_the_repository_declares_one() {
    let g = graph(
        "pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } }
         pub struct Weird; impl Weird { pub fn to_string(&self) -> Rel { Rel } }
         pub fn s1(f: Foo) { f.to_string().len(); }",
    );
    // A repository method named `to_string` could return anything: the chain is untyped.
    assert_eq!(edges_to(&g, "s1", ".len").len(), 1);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn from_default_and_cow_results_are_typed_only_where_the_type_is_certain() {
    let g = graph(
        "use std::borrow::Cow;
         pub struct Rel; impl Rel { pub fn len(&self) -> usize { 0 } }
         #[derive(Default)] pub struct W;
         impl W { pub fn go(&self) {} pub fn make() { Self::default().go() } }
         impl From<u8> for W { fn from(_: u8) -> W { W } }
         impl From<u16> for W { fn from(_: u16) -> W { W } }
         pub fn name() -> Cow<'static, str> { Cow::Borrowed(\"a\") }
         pub fn foos() -> Cow<'static, Foo> { todo!() }
         pub fn t1() { W::from(1u8).go(); }
         pub fn t2() { name().len(); name().into_owned().len(); }
         pub fn s1() { Missing::from(1).go(); }
         pub fn s2() { foos().go(); }",
    );
    // `From::from` is `Self` whichever impl it picks; both impls are only possible, the result is certain.
    let t1 = go_edges(&g, "t1");
    assert!(
        t1.contains(&("c/src/lib.rs::W.go".to_owned(), Status::Must)),
        "{t1:?}"
    );
    assert_eq!(
        go_edges(&g, "W.make"),
        vec![("c/src/lib.rs::W.go".to_owned(), Status::Must)]
    );
    assert!(edges_to(&g, "t2", ".len").is_empty());
    // An unknown type has no such certainty, and `Cow` of a repository type is not read through.
    assert!(go_edges(&g, "s1").iter().all(|(_, s)| *s == Status::May));
    let s2 = go_edges(&g, "s2");
    assert!(
        s2.len() >= 2 && s2.iter().all(|(_, s)| *s == Status::May),
        "{s2:?}"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.link_calls
#[test]
fn aliased_and_generic_elements_and_foreign_trait_impls_stay_possible() {
    let g = graph(
        "type Item = Bar;
         pub trait Tr { fn act(&self); }
         impl Tr for Vec<Foo> { fn act(&self) {} }
         pub struct Rel; impl Rel { pub fn act(&self) {} }
         pub fn s1(v: Vec<Item>) { for x in v { x.go() } }
         pub fn s2<T: Tr>(v: Vec<T>) { for x in v { x.act() } }
         pub fn s3(v: Vec<Foo>) { v.act() }",
    );
    // An alias may stand for any type: not read as `Bar`.
    assert_both_may(&g, "s1");
    // A generic element is not a repository type: `act` stays possible on every `act`.
    let s2 = edges_to(&g, "s2", ".act");
    assert!(
        !s2.iter().any(|(_, s)| *s == Status::Must && s2.len() == 1),
        "{s2:?}"
    );
    // A trait implemented for `Vec<Foo>` is the only `act` a `Vec` can have, but trait impls stay May.
    assert!(
        edges_to(&g, "s3", ".act")
            .iter()
            .all(|(_, s)| *s == Status::May)
    );
}
