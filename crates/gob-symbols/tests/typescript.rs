//! The TypeScript and JavaScript adapter end to end: folded files linked into the module graph
//! (language-engines.md sections 2 and 3, D96).

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80

use gob_symbols::{
    EdgeKind, FileSymbols, GapReason, JsxKind, ParseStatus, Status, StatusEdge, SymbolGraph,
    SymbolKind, TestRole, Visibility, adapter_for_path, extract_file, fidelity_report, fold_file,
    is_typescript_test_file, jsx_elements, test_items,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn fold(path: &str, src: &str) -> FileSymbols {
    extract_file(&entry(path, src), src)
}

fn graph(files: &[(&str, &str)]) -> SymbolGraph {
    SymbolGraph::from_files(files.iter().map(|(p, s)| fold(p, s)).collect())
}

fn names(f: &FileSymbols) -> Vec<String> {
    f.symbols.iter().map(|s| s.symref.to_string()).collect()
}

fn imports_of<'g>(g: &'g SymbolGraph, from: &str) -> Vec<&'g StatusEdge> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Imports && e.from.path() == from)
        .collect()
}

fn import_status(g: &SymbolGraph, from: &str, name: &str) -> Vec<(Status, Option<GapReason>)> {
    imports_of(g, from)
        .into_iter()
        .filter(|e| e.name.as_deref() == Some(name))
        .map(|e| (e.status, e.reason))
        .collect()
}

fn call_status(g: &SymbolGraph, from: &str, to: &str) -> Option<Status> {
    g.edges_with_status()
        .iter()
        .find(|e| {
            e.kind == EdgeKind::Calls
                && e.from.to_string() == from
                && e.to.as_ref().is_some_and(|t| t.to_string() == to)
        })
        .map(|e| e.status)
}

fn unknown_calls(g: &SymbolGraph, from: &str) -> Vec<(String, Option<GapReason>)> {
    g.edges_with_status()
        .iter()
        .filter(|e| {
            e.kind == EdgeKind::Calls && e.status == Status::Unknown && e.from.to_string() == from
        })
        .map(|e| (e.name.clone().unwrap_or_default(), e.reason))
        .collect()
}

const SAMPLE: &str = r#"/** The widget. */
export class Widget extends Base {
  private secret = 1;
  #hidden = 2;
  static make(): Widget { return new Widget(); }
  constructor(private readonly id: number) { super(); }
  /** Renders. */
  render(): void { this.paint(); helper(); }
  protected paint(): void {}
  handle = () => { this.paint(); };
}
export interface Props { a: number }
export type Id = string | number;
export enum Color { Red, Green }
export function exported(a: number, b = 2): number { return a + b; }
function internal() { const inner = () => 1; function nested() {} nested(); inner(); }
export const arrow = (x: number) => exported(x, 1);
export const VALUE = 42;
let counter = 0;
namespace Outer.Inner { export function deep() {} }
export default function () {}
"#;

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::fold_tree
fn declarations_become_units_with_kinds_and_visibility() {
    let f = fold("src/widget.ts", SAMPLE);
    assert!(f.parse_status.is_complete(), "{:?}", f.parse_status);
    let got: Vec<(String, SymbolKind, Visibility)> = f
        .symbols
        .iter()
        .map(|s| (s.symref.to_string(), s.kind, s.visibility))
        .collect();
    let has = |n: &str, k: SymbolKind, v: Visibility| {
        assert!(
            got.contains(&(format!("src/widget.ts::{n}"), k, v)),
            "missing {n} {k:?} {v:?} in {got:#?}"
        );
    };
    has("Widget", SymbolKind::Class, Visibility::Public);
    has("Widget.constructor", SymbolKind::Method, Visibility::Public);
    has("Widget.make", SymbolKind::Method, Visibility::Public);
    has("Widget.render", SymbolKind::Method, Visibility::Public);
    has("Widget.paint", SymbolKind::Method, Visibility::Crate);
    has("Widget.handle", SymbolKind::Method, Visibility::Public);
    has("Props", SymbolKind::Interface, Visibility::Public);
    has("Id", SymbolKind::TypeAlias, Visibility::Public);
    has("Color", SymbolKind::Enum, Visibility::Public);
    has("exported", SymbolKind::Function, Visibility::Public);
    has("internal", SymbolKind::Function, Visibility::Private);
    has("internal.nested", SymbolKind::Function, Visibility::Private);
    has("arrow", SymbolKind::Function, Visibility::Public);
    has("VALUE", SymbolKind::Const, Visibility::Public);
    has("counter", SymbolKind::Static, Visibility::Private);
    has("Outer", SymbolKind::Namespace, Visibility::Private);
    has("Outer.Inner", SymbolKind::Namespace, Visibility::Public);
    has("Outer.Inner.deep", SymbolKind::Function, Visibility::Public);
    has("default", SymbolKind::Function, Visibility::Public);
    // Private fields are not units; a local arrow is not a unit.
    assert!(
        !names(&f)
            .iter()
            .any(|n| n.ends_with("secret") || n.ends_with("inner") && !n.contains("Outer"))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.seq
fn a_jsdoc_comment_is_the_doc_facet_not_the_body() {
    let documented = fold(
        "a.ts",
        "/** Does it. */\nexport function f() { return 1; }\n",
    );
    let bare = fold("a.ts", "export function f() { return 1; }\n");
    assert_ne!(
        documented.symbols[0].digests.doc,
        bare.symbols[0].digests.doc
    );
    assert_eq!(
        documented.symbols[0].digests.body,
        bare.symbols[0].digests.body
    );
    let changed = fold("a.ts", "export function f() { return 2; }\n");
    assert_ne!(
        changed.symbols[0].digests.body,
        bare.symbols[0].digests.body
    );
    let sig = fold("a.ts", "export function f(x: number) { return 1; }\n");
    assert_ne!(sig.symbols[0].digests.sig, bare.symbols[0].digests.sig);
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.import_stmt
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.module_call
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.bind_require
fn every_import_form_is_an_edge_and_a_binding() {
    let src = r#"import Def, { a as b, c } from './m';
import * as ns from '../n';
import type { T } from './types';
import './side';
import x = require('./legacy');
export { q as r } from './q';
export * from './star';
const lazy = () => import('./lazy');
const cond = () => require('./cond');
const top = require('./top');
const { p, k: l } = require('./destructured');
const pick = require('./pick').one;
const dyn = (n: string) => import(`./plugins/${n}`);
const comp = (n: string) => require(n);
"#;
    let f = fold("src/main.ts", src);
    assert!(f.parse_status.is_complete());
    let edges: Vec<&str> = f.imports.iter().map(|e| e.target.as_str()).collect();
    for want in [
        "./m",
        "../n",
        "./types",
        "./side",
        "./legacy",
        "./q",
        "./star",
        "may:./lazy",
        "may:./cond",
        "./top",
        "./destructured",
        "./pick",
    ] {
        assert!(edges.contains(&want), "missing {want} in {edges:?}");
    }
    let unknown: Vec<&&str> = edges.iter().filter(|e| e.starts_with("unknown:")).collect();
    assert_eq!(unknown.len(), 2, "{edges:?}");
    let uses: Vec<(&str, &str, bool)> = f
        .uses
        .iter()
        .map(|u| (u.local.as_str(), u.target.as_str(), u.public))
        .collect();
    for want in [
        ("Def", "./m#default", false),
        ("b", "./m#a", false),
        ("c", "./m#c", false),
        ("ns", "../n#*", false),
        ("T", "./types#T", false),
        ("x", "./legacy#*", false),
        ("r", "./q#q", true),
        ("*", "./star#*", true),
        ("top", "./top#*", false),
        ("p", "./destructured#p", false),
        ("l", "./destructured#k", false),
        ("pick", "./pick#one", false),
    ] {
        assert!(uses.contains(&want), "missing {want:?} in {uses:#?}");
    }
}

fn web_pages() -> Vec<(&'static str, &'static str)> {
    vec![
        (
            "web/main.ts",
            "import { run } from './app';\nimport Home, { title } from './pages/home';\nimport * as util from './util';\nimport { gone } from './missing';\nimport React from 'react';\nconst lazy = () => import('./lazy');\nconst plug = (n: string) => import(`./plugins/${n}`);\nconst old = require('./legacy');\nconst calc = (n: string) => require(n);\nexport function main() { run(); util.helper(); title(); Home(); gone(); lazy(); plug('x'); old(); }\n",
        ),
        ("web/app.ts", "export function run() {}\n"),
        (
            "web/pages/home.tsx",
            "export default function Home() { return <main className=\"a\"><Header title=\"t\" {...props} /></main>; }\nexport const title = () => 'home';\nfunction Header(p: { title: string }) { return <h1>{p.title}</h1>; }\n",
        ),
        ("web/util/index.ts", "export function helper() {}\n"),
        ("web/lazy.ts", "export const x = 1;\n"),
        (
            "web/legacy.js",
            "function legacy() {}\nmodule.exports = legacy;\n",
        ),
    ]
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::TsIndex.resolve
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.link_typescript_imports
fn web_pages_every_import_is_must_may_or_unknown() {
    let g = graph(&web_pages());
    // Static imports of repository files are Must, the `.tsx` and the directory `index` resolve.
    for spec in ["./app", "./pages/home", "./util"] {
        let got = import_status(&g, "web/main.ts", spec);
        assert!(got.contains(&(Status::Must, None)), "{spec}: {got:?}");
    }
    // A literal dynamic import is May, a top-level require Must.
    assert!(import_status(&g, "web/main.ts", "./lazy").contains(&(Status::May, None)));
    assert!(import_status(&g, "web/main.ts", "./legacy").contains(&(Status::Must, None)));
    // Nothing can be claimed for a missing file, a package or a computed specifier.
    assert_eq!(
        import_status(&g, "web/main.ts", "./missing"),
        [(Status::Unknown, Some(GapReason::Unbound))]
    );
    assert_eq!(
        import_status(&g, "web/main.ts", "react"),
        [(Status::Unknown, Some(GapReason::Unbound))]
    );
    // No import is silently dropped: every ImportEdge of the file has a status edge.
    let f = fold("web/main.ts", web_pages()[0].1);
    for e in &f.imports {
        let spec = e
            .target
            .trim_start_matches("may:")
            .trim_start_matches("unknown:");
        assert!(
            !import_status(&g, "web/main.ts", spec).is_empty(),
            "dropped import {}",
            e.target
        );
    }
    // Symbol-level edges follow the named imports.
    let home_title = import_status(&g, "web/main.ts", "title");
    assert_eq!(home_title, [(Status::Must, None)]);
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.link_typescript_imports
fn dynamic_and_computed_imports_are_unknown_never_dropped() {
    let g = graph(&web_pages());
    let unknown: Vec<&StatusEdge> = imports_of(&g, "web/main.ts")
        .into_iter()
        .filter(|e| e.status == Status::Unknown && e.reason == Some(GapReason::Dynamic))
        .collect();
    assert_eq!(unknown.len(), 2, "{unknown:#?}");
    let names: Vec<&str> = unknown.iter().filter_map(|e| e.name.as_deref()).collect();
    assert!(
        names.iter().any(|n| n.starts_with("import(`./plugins/")),
        "{names:?}"
    );
    assert!(
        names.iter().any(|n| n.starts_with("require(n")),
        "{names:?}"
    );
    assert!(unknown.iter().all(|e| e.to.is_none()));
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::TsIndex.resolve
fn relative_specifiers_try_the_typescript_orders() {
    let files = [
        (
            "src/a.ts",
            "import './b.js'; import './c'; import './d'; import './e.css'; import '../../up'; import './f';",
        ),
        ("src/b.ts", "export const b = 1;"),
        ("src/c/index.tsx", "export const c = 1;"),
        ("src/d.js", "export const d = 1;"),
        ("src/d.ts", "export const d2 = 1;"),
        ("src/e.css", "a {}"),
        ("src/f.mjs", "export const f = 1;"),
    ];
    let g = graph(&files);
    let targets: Vec<(String, Status)> = imports_of(&g, "src/a.ts")
        .into_iter()
        .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
        .collect();
    for want in [
        "src/b.ts",
        "src/c/index.tsx",
        "src/d.ts",
        "src/e.css",
        "src/f.mjs",
    ] {
        assert!(
            targets.contains(&(want.to_owned(), Status::Must)),
            "{want} in {targets:?}"
        );
    }
    assert_eq!(
        import_status(&g, "src/a.ts", "../../up"),
        [(Status::Unknown, Some(GapReason::Unbound))]
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_export
fn barrels_and_aliases_are_followed_to_the_declaring_unit() {
    let g = graph(&[
        (
            "src/index.ts",
            "import { v, other, N } from './barrel';\nimport Main from './a';\nexport function use() { v(); other(); N.f(); Main(); }",
        ),
        (
            "src/barrel.ts",
            "import { value as v } from './a';\nexport { v };\nexport * from './c';\nexport * as N from './ns';",
        ),
        (
            "src/a.ts",
            "export function value() {}\nexport default function main() {}\nexport { main as renamed };",
        ),
        ("src/c.ts", "export function other() {}"),
        ("src/ns.ts", "export function f() {}"),
    ]);
    let from = "src/index.ts::use";
    assert_eq!(call_status(&g, from, "src/a.ts::value"), Some(Status::Must));
    assert_eq!(call_status(&g, from, "src/c.ts::other"), Some(Status::Must));
    assert_eq!(call_status(&g, from, "src/ns.ts::f"), Some(Status::Must));
    assert_eq!(call_status(&g, from, "src/a.ts::main"), Some(Status::Must));
    // The symbol-level import edge lands on the declaring unit.
    let to: Vec<String> = imports_of(&g, "src/index.ts")
        .into_iter()
        .filter_map(|e| e.to.as_ref().map(ToString::to_string))
        .collect();
    assert!(to.contains(&"src/a.ts::value".to_owned()), "{to:?}");
    assert!(to.contains(&"src/c.ts::other".to_owned()), "{to:?}");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.resolve_typescript
fn calls_resolve_by_scope_import_and_receiver() {
    let g = graph(&[
        (
            "src/k.ts",
            r#"import { run } from './run';
import * as util from './util';
import { Thing } from './thing';
export class Box {
  open() { this.close(); run(); util.go(); Thing.create(); new Thing(); }
  close() {}
  other(cb: () => void, x: any) { cb(); x.close(); x.nothing(); (cb())(); fetch('u'); }
}
export function local() { const f = () => 1; f(); helper(); }
function helper() {}
"#,
        ),
        ("src/run.ts", "export function run() {}"),
        ("src/util.ts", "export function go() {}"),
        (
            "src/thing.ts",
            "export class Thing { constructor() {} static create() {} close() {} }",
        ),
    ]);
    let open = "src/k.ts::Box.open";
    assert_eq!(
        call_status(&g, open, "src/k.ts::Box.close"),
        Some(Status::Must)
    );
    assert_eq!(call_status(&g, open, "src/run.ts::run"), Some(Status::Must));
    assert_eq!(call_status(&g, open, "src/util.ts::go"), Some(Status::Must));
    assert_eq!(
        call_status(&g, open, "src/thing.ts::Thing.create"),
        Some(Status::Must)
    );
    assert_eq!(
        call_status(&g, open, "src/thing.ts::Thing.constructor"),
        Some(Status::Must)
    );
    let other = "src/k.ts::Box.other";
    // A method call on an unknown value names every method so called.
    assert_eq!(
        call_status(&g, other, "src/k.ts::Box.close"),
        Some(Status::May)
    );
    assert_eq!(
        call_status(&g, other, "src/thing.ts::Thing.close"),
        Some(Status::May)
    );
    let unknown = unknown_calls(&g, other);
    assert!(
        unknown.contains(&("cb".to_owned(), Some(GapReason::LocalValue))),
        "{unknown:?}"
    );
    assert!(
        unknown.contains(&("nothing".to_owned(), Some(GapReason::Unbound))),
        "{unknown:?}"
    );
    assert!(
        unknown.contains(&("<dynamic>".to_owned(), Some(GapReason::Dynamic))),
        "{unknown:?}"
    );
    assert!(
        unknown.contains(&("fetch".to_owned(), Some(GapReason::Unbound))),
        "{unknown:?}"
    );
    let local = "src/k.ts::local";
    assert_eq!(
        call_status(&g, local, "src/k.ts::helper"),
        Some(Status::Must)
    );
    assert!(unknown_calls(&g, local).contains(&("f".to_owned(), Some(GapReason::LocalValue))));
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.resolve_typescript_value
fn a_function_passed_as_a_value_is_a_may_reference() {
    let g = graph(&[
        (
            "src/ui.tsx",
            "import { onSave } from './handlers';\nexport function Form() { return <button onClick={onSave} />; }\nexport function List() { return [1].map(render); }\nfunction render() {}",
        ),
        ("src/handlers.ts", "export function onSave() {}"),
    ]);
    let refs: Vec<(String, String, Status)> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::References)
        .filter_map(|e| Some((e.from.to_string(), e.to.as_ref()?.to_string(), e.status)))
        .collect();
    assert!(
        refs.contains(&(
            "src/ui.tsx::Form".into(),
            "src/handlers.ts::onSave".into(),
            Status::May
        )),
        "{refs:?}"
    );
    assert!(
        refs.iter()
            .any(|(f, t, _)| f == "src/ui.tsx::List" && t == "src/ui.tsx::render")
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/mod.rs::jsx_elements
fn a_tsx_file_lists_declarations_and_jsx_elements() {
    let src = r#"import { Card } from './card';
import * as ui from './ui';
export function App({ items }: { items: string[] }) {
  return (
    <>
      <Card title="a" {...rest} />
      <ui.Panel>
        <ul className="list">{items.map((i) => <li key={i}>{i}</li>)}</ul>
        <input disabled />
      </ui.Panel>
    </>
  );
}
export const Footer = () => <footer>done</footer>;
"#;
    let folded = fold_file(&entry("src/app.tsx", src), src).expect("fold");
    assert!(
        folded.file.parse_status.is_complete(),
        "{:?}",
        folded.file.parse_status
    );
    assert_eq!(
        names(&folded.file),
        ["src/app.tsx::App", "src/app.tsx::Footer"]
    );
    let els = jsx_elements(&folded.term);
    let tags: Vec<(&str, JsxKind)> = els.iter().map(|e| (e.tag.as_str(), e.kind)).collect();
    for want in [
        ("", JsxKind::Fragment),
        ("Card", JsxKind::Component),
        ("ui.Panel", JsxKind::Member),
        ("ul", JsxKind::Intrinsic),
        ("li", JsxKind::Intrinsic),
        ("input", JsxKind::Intrinsic),
        ("footer", JsxKind::Intrinsic),
    ] {
        assert!(tags.contains(&want), "missing {want:?} in {tags:?}");
    }
    let card = els.iter().find(|e| e.tag == "Card").expect("Card");
    assert_eq!(card.attributes, ["title", "..."]);
    assert_eq!(card.line, 6);
    let ul = els.iter().find(|e| e.tag == "ul").expect("ul");
    assert_eq!(ul.attributes, ["className"]);
    // A component tag is a reference, so `App` reaches `Card` by name in the scope graph.
    assert!(folded.term.ids().any(|id| matches!(
        folded.term.operator(id),
        gob_ir::Operator::Universal(gob_ir::Universal::Ref { name }) if name == "Card"
    )));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/mod.rs::test_items
fn test_runner_calls_are_test_items() {
    let vitest = r#"import { describe, it, expect } from 'vitest';
describe('math', () => {
  it('adds', () => { expect(1 + 1).toBe(2); });
  it.skip('later', () => {});
  it('no body');
});
"#;
    let f = extract_term("src/math.test.ts", vitest);
    let items = test_items(&f.term);
    assert_eq!(items.len(), 3, "{items:?}");
    assert_eq!(items[0].role, TestRole::Suite);
    assert_eq!(items[0].title, "math");
    assert_eq!(items[0].framework, "vitest");
    assert_eq!(items[1].role, TestRole::Case);
    assert_eq!(items[1].title, "adds");
    assert_eq!(items[2].title, "later");

    let pw = "import { test, expect } from '@playwright/test';\ntest.describe('page', () => { test('loads', async ({ page }) => {}); });\n";
    let items = test_items(&extract_term("e2e/home.spec.ts", pw).term);
    assert_eq!(items.len(), 2);
    assert_eq!(
        (items[0].role, items[0].framework.as_str()),
        (TestRole::Suite, "playwright")
    );
    assert_eq!(items[1].role, TestRole::Case);

    let jest = "describe('g', () => { test('t', () => {}); });\n";
    let items = test_items(&extract_term("src/a.test.js", jest).term);
    assert_eq!(items.len(), 2);
    assert_eq!(items[0].framework, "globals");
    // `test(...)` in a non-test file that imports no runner is just a call.
    assert!(test_items(&extract_term("src/lib.ts", jest).term).is_empty());
    assert!(is_typescript_test_file("src/a.test.tsx"));
    assert!(is_typescript_test_file("e2e/flow.ts"));
    assert!(!is_typescript_test_file("src/a.ts"));
    assert!(!is_typescript_test_file("README.md"));
}

fn extract_term(path: &str, src: &str) -> gob_symbols::Folded {
    fold_file(&entry(path, src), src).expect("fold")
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/mod.rs::TypeScriptAdapter
fn javascript_dialects_use_the_same_adapter() {
    for path in [
        "a.js", "a.jsx", "a.mjs", "a.cjs", "a.ts", "a.tsx", "a.mts", "a.cts", "A.TS",
    ] {
        let a = adapter_for_path(path).unwrap_or_else(|| panic!("no adapter for {path}"));
        assert_eq!(a.language(), "typescript", "{path}");
    }
    let js = fold(
        "lib/a.js",
        "function f() { return g(); }\nfunction g() {}\nmodule.exports = { f, g };\n",
    );
    assert_eq!(js.language, "typescript");
    assert_eq!(js.fidelity, gob_symbols::Fidelity::F2);
    assert!(js.parse_status.is_complete());
    assert!(
        js.symbols
            .iter()
            .all(|s| s.visibility == Visibility::Public)
    );
    let jsx = fold(
        "ui/a.jsx",
        "export const A = () => <div id=\"x\">hi</div>;\n",
    );
    assert!(jsx.parse_status.is_complete());
    assert_eq!(names(&jsx), ["ui/a.jsx::A"]);
    let report = fidelity_report();
    let row = report
        .iter()
        .find(|r| r.language == "typescript")
        .expect("row");
    assert!(row.extensions.contains(&"tsx"));
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::scan_exports
fn cjs_exports_make_declarations_public_and_resolvable() {
    let g = graph(&[
        (
            "lib/main.js",
            "const { build } = require('./tool');\nconst d = require('./dflt');\nfunction go() { build(); d(); }\nmodule.exports = { go };\n",
        ),
        (
            "lib/tool.js",
            "function build() {}\nfunction hidden() {}\nexports.build = build;\n",
        ),
        ("lib/dflt.js", "function d() {}\nmodule.exports = d;\n"),
    ]);
    assert_eq!(
        call_status(&g, "lib/main.js::go", "lib/tool.js::build"),
        Some(Status::Must)
    );
    assert_eq!(
        call_status(&g, "lib/main.js::go", "lib/dflt.js::d"),
        Some(Status::Must)
    );
    let tool = fold(
        "lib/tool.js",
        "function build() {}\nfunction hidden() {}\nexports.build = build;\n",
    );
    let vis: Vec<(String, Visibility)> = tool
        .symbols
        .iter()
        .map(|s| (s.symref.to_string(), s.visibility))
        .collect();
    assert_eq!(
        vis,
        [
            ("lib/tool.js::build".to_owned(), Visibility::Public),
            ("lib/tool.js::hidden".to_owned(), Visibility::Private)
        ]
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.tr
fn syntax_errors_and_with_statements_are_partial_parses() {
    let broken = fold("a.ts", "export function f( {\n");
    assert!(
        matches!(broken.parse_status, ParseStatus::Partial { .. }),
        "{:?}",
        broken.parse_status
    );
    let with = fold("a.js", "function f(o) { with (o) { g(); } }\n");
    assert!(
        matches!(with.parse_status, ParseStatus::Partial { holes: 1 }),
        "{:?}",
        with.parse_status
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.collapse
fn deep_nesting_collapses_without_losing_calls_or_imports() {
    let expr = (0..400).map(|_| "1").collect::<Vec<_>>().join(" + ");
    let src =
        format!("function f() {{ const x = {expr}; g(); }}\nconst h = {expr} + require('./z');\n");
    let f = fold("a.ts", &src);
    assert!(f.calls.iter().any(|c| c.callee == "g"));
    assert!(
        f.imports.iter().any(|e| e.target.ends_with("./z")),
        "{:?}",
        f.imports
    );
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/fold.rs::Fold.func_decl
fn calls_are_attributed_to_the_enclosing_unit() {
    let f = fold(
        "a.ts",
        "function outer() { function inner() { leaf(); } inner(); }\nconst top = () => outer();\nclass K { m() { outer(); } p = leaf(); }\n",
    );
    let by: Vec<(String, String)> = f
        .calls
        .iter()
        .map(|c| (c.caller.to_string(), c.callee.clone()))
        .collect();
    for want in [
        ("a.ts::outer.inner", "leaf"),
        ("a.ts::outer", "inner"),
        ("a.ts::top", "outer"),
        ("a.ts::K.m", "outer"),
        ("a.ts::K", "leaf"),
    ] {
        assert!(
            by.contains(&(want.0.to_owned(), want.1.to_owned())),
            "{want:?} in {by:?}"
        );
    }
}

#[test]
// frob:tests crates/gob-symbols/src/typescript/imports.rs::decode_use
fn the_python_module_graph_and_the_typescript_one_agree_on_shared_shapes() {
    let ts = graph(&[
        (
            "pkg/main.ts",
            "import { run } from './app';\nexport function main() { run(); }",
        ),
        ("pkg/app.ts", "export function run() {}"),
    ]);
    let py = SymbolGraph::from_files(vec![
        fold(
            "pkg/main.py",
            "from .app import run\n\ndef main():\n    run()\n",
        ),
        fold("pkg/app.py", "def run():\n    pass\n"),
    ]);
    let file_edge = |g: &SymbolGraph, from: &str, to: &str| {
        g.edges_with_status()
            .iter()
            .find(|e| {
                e.kind == EdgeKind::Imports
                    && e.from.path() == from
                    && e.to.as_ref().is_some_and(|t| t.to_string() == to)
            })
            .map(|e| e.status)
    };
    // Python records its module edge in the graph; both modules link Must.
    assert_eq!(
        file_edge(&ts, "pkg/main.ts", "pkg/app.ts"),
        Some(Status::Must)
    );
    assert_eq!(
        call_status(&ts, "pkg/main.ts::main", "pkg/app.ts::run"),
        Some(Status::Must)
    );
    assert_eq!(
        call_status(&py, "pkg/main.py::main", "pkg/app.py::run"),
        Some(Status::Must)
    );
}
