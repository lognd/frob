//! JSX and TS source ingest: the ported vectors of the Python `test_ingest_jsx.py` (style props,
//! className sites, `.ts` class constants, `createElement`) and the Rust-only behaviour (dynamic
//! sites, not-fixable JSX sheets).

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

mod common;

use crunk_ingest::{Bucket, ParsedJsx, ingest_tree, parse_jsx_source};
use crunk_values::LengthKind;
use gob_cache::Cache;

const RFS: f64 = 16.0;

fn tsx(source: &str) -> ParsedJsx {
    let parsed = parse_jsx_source("a.tsx", source, RFS).unwrap();
    assert!(parsed.errors.is_empty(), "{:?}", parsed.errors);
    parsed
}

fn ts(source: &str) -> ParsedJsx {
    parse_jsx_source("a.ts", source, RFS).unwrap()
}

fn set(p: &ParsedJsx) -> std::collections::BTreeSet<&str> {
    names(p).into_iter().collect()
}

fn names(p: &ParsedJsx) -> Vec<&str> {
    p.utilities.iter().map(|u| u.name.as_str()).collect()
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn style_prop_camelcase_and_units() {
    let source = "const C = () => (\n  <div style={{ backgroundColor: \"#282828\", zIndex: 5, width: 44 }} />\n);\n";
    let p = tsx(source);
    let by = |prop: &str| p.declarations.iter().find(|d| d.prop == prop).unwrap();
    assert_eq!(by("background-color").value, "#282828");
    assert_eq!(by("background-color").colors[0].color.to_hex(), "#282828");
    assert_eq!(by("z-index").value, "5");
    assert!(by("z-index").lengths.is_empty());
    let width = by("width");
    assert_eq!(width.value, "44");
    assert_eq!(width.lengths[0].length.px, Some(44.0));
    assert_eq!(width.lengths[0].length.kind, LengthKind::Px);
    for d in &p.declarations {
        assert_eq!(&source[d.span.0..d.span.1], d.value);
    }
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn style_prop_string_value_facts_extracted() {
    let source = "<div style={{ margin: \"4px 13px\" }} />";
    let p = tsx(source);
    assert_eq!(p.declarations.len(), 1);
    let d = &p.declarations[0];
    assert_eq!((d.prop.as_str(), d.value.as_str()), ("margin", "4px 13px"));
    assert_eq!(&source[d.span.0..d.span.1], d.value);
    assert_eq!(
        d.lengths.iter().map(|l| l.length.px).collect::<Vec<_>>(),
        [Some(4.0), Some(13.0)]
    );
    for l in &d.lengths {
        assert_eq!(&source[l.span.0..l.span.1], l.length.raw);
    }
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn style_prop_computed_and_interpolated_skipped() {
    let source = "<div style={{ ...base, color: computeColor(), [dynamicKey]: \"red\", label: `${prefix}-x` }} />";
    assert!(tsx(source).declarations.is_empty());
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn style_prop_multiline_lines() {
    let p = tsx("<div\n  style={{\n    background: \"#fff\",\n    width: 10,\n  }}\n/>\n");
    let line = |prop: &str| p.declarations.iter().find(|d| d.prop == prop).unwrap().line;
    assert_eq!((line("background"), line("width")), (3, 4));
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn classname_utilities_split() {
    let p = tsx("<div className=\"bg-[#282828] p-[13px] hover:bg-red-500 [&>x]:text-sm\" />");
    assert_eq!(
        names(&p),
        ["bg-[#282828]", "p-[13px]", "bg-red-500", "text-sm"]
    );
    assert!(p.utilities.iter().all(|u| u.line == 1));
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn classname_template_without_interpolation_is_a_string() {
    assert_eq!(
        names(&tsx("<div className={`bg-red-500 p-4`} />")),
        ["bg-red-500", "p-4"]
    );
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn classname_interpolated_keeps_the_static_segment() {
    assert_eq!(
        names(&tsx("<div className={`bg-red-500 ${extra}`} />")),
        ["bg-red-500"]
    );
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn template_boundary_tokens_are_dropped() {
    assert_eq!(
        names(&tsx("<div className={`a z-footer ${c}`} />")),
        ["a", "z-footer"]
    );
    assert!(tsx("<div className={`z-${x}`} />").utilities.is_empty());
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn helper_calls_ternaries_and_nested_braces_are_scanned() {
    assert_eq!(
        names(&tsx("<div className={clsx(\"p-4 flex\", extraCls)} />")),
        ["p-4", "flex"]
    );
    assert_eq!(
        names(&tsx(
            "<div className={open ? \"bg-red-500\" : \"bg-blue-500\"} />"
        )),
        ["bg-red-500", "bg-blue-500"]
    );
    assert_eq!(
        names(&tsx(
            "<div className={`a ${fn({ x: 1, y: { z: 2 } })} b`} />"
        )),
        ["a", "b"]
    );
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn utility_variants_keep_their_order() {
    let p = tsx("<div className=\"hover:md:flex bg-red-500\" />");
    let by = |n: &str| p.utilities.iter().find(|u| u.name == n).unwrap();
    assert_eq!(by("flex").variants, ["hover", "md"]);
    assert!(by("bg-red-500").variants.is_empty());
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn cva_and_tw_merge_call_literals_are_scanned() {
    let p = tsx(
        "<div className={cva(\"base-class\", { variants: { intent: { primary: \"text-blue-500\", danger: \"text-red-500\" } } })({ intent: \"primary\" })} />",
    );
    let n = names(&p);
    for want in ["base-class", "text-blue-500", "text-red-500"] {
        assert!(n.contains(&want), "{want} in {n:?}");
    }
    let p = tsx("<div className={twMerge(\"p-4 flex\", twJoin(\"gap-2\", cond && \"hidden\"))} />");
    assert_eq!(names(&p), ["p-4", "flex", "gap-2", "hidden"]);
    assert_eq!(
        names(&tsx(
            "<div className={`static-token ${fullyDynamicExpr()}`} />"
        )),
        ["static-token"]
    );
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn ts_class_constants_pass_the_class_list_gate() {
    let p = ts("export const FOCUS_RING = \"outline outline-2 outline-offset-2\";\n");
    assert_eq!(names(&p), ["outline", "outline-2", "outline-offset-2"]);
    assert!(p.utilities.iter().all(|u| u.line == 1));
    assert!(
        ts("export const GREETING = \"Hello, world!\";\n")
            .utilities
            .is_empty()
    );
    assert!(
        ts("export const CLS = `bg-red-500 ${extra}`;\n")
            .utilities
            .is_empty()
    );
    assert_eq!(
        names(&ts("export const BG = \"bg-[#123456]\";\n")),
        ["bg-[#123456]"]
    );
    assert_eq!(
        names(&ts(
            "export const CLS = `flex gap-2 ${extra} outline outline-2`;\n"
        )),
        ["flex", "gap-2", "outline", "outline-2"]
    );
    let p = ts("export const CLS = \"md:hidden lg:flex items-center\";\n");
    let by = |n: &str| p.utilities.iter().find(|u| u.name == n).unwrap();
    assert_eq!(by("hidden").variants, ["md"]);
    assert_eq!(by("flex").variants, ["lg"]);
    assert!(by("items-center").variants.is_empty());
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn ts_call_arguments_and_variant_maps_are_scanned() {
    let p = ts(
        "export const badgeVariants = cva('inline-flex items-center', {\n  variants: {\n    intent: {\n      primary: 'bg-blue-500 text-white',\n      danger: 'bg-red-500 text-white',\n    },\n  },\n});\n",
    );
    let n = names(&p);
    for want in ["inline-flex", "bg-blue-500", "bg-red-500"] {
        assert!(n.contains(&want), "{want} in {n:?}");
    }
    let p = ts("export const classes = twMerge('p-4 flex', 'gap-2 items-center');\n");
    assert!(names(&p).contains(&"p-4") && names(&p).contains(&"gap-2"));
}

// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_jsx_source
#[test]
fn a_comment_apostrophe_does_not_desync_the_scan() {
    let p = ts(
        "// this is crunk's comment, with an unmatched apostrophe\nexport const ERROR_TEXT_CLASS = 'rounded-4 bg-red-500 text-white';\n",
    );
    assert_eq!(names(&p), ["rounded-4", "bg-red-500", "text-white"]);
}

// frob:tests crates/crunk-ingest/src/jsx/classes.rs::from_create_element
#[test]
fn create_element_class_entries_resolve() {
    let p = ts(
        "const className = 'text-accent font-semibold'\ncreateElement('span', { className }, label)\n",
    );
    assert_eq!(set(&p), ["font-semibold", "text-accent"].into());
    assert_eq!(
        p.utilities[0].line, 1,
        "the line of the constant's declaration"
    );

    // A `.ts` file is also scanned for class-list literals, so a literal in a props object is
    // found twice, as in Python.
    let p = ts("createElement('span', { className: 'p-4 flex' }, label)\n");
    assert_eq!(set(&p), ["flex", "p-4"].into());

    let p = tsx("React.cloneElement(el, { className: 'bg-red-500' })\n");
    assert_eq!(names(&p), ["bg-red-500"]);

    let p = ts(
        "createElement('a', { className: 'sr-only focus:z-skiplink' + \n  ' focus:outline-accent-orange' }, 'Skip to content')\n",
    );
    assert_eq!(
        set(&p),
        ["outline-accent-orange", "sr-only", "z-skiplink"].into()
    );

    let p = ts(
        "const BASE = 'base-token'\ncreateElement('a', { className: BASE + ' extra-token' }, label)\n",
    );
    assert_eq!(set(&p), ["base-token", "extra-token"].into());
}

// frob:tests crates/crunk-ingest/src/jsx/classes.rs::from_create_element
#[test]
fn create_element_computed_shapes_are_dynamic_not_guessed() {
    let p = ts("createElement('span', getProps(), label)\n");
    assert!(p.utilities.is_empty() && p.dynamic_classes.is_empty());

    let p = ts("createElement('a', { className: 'static-token' + dynamicFn() }, l)\n");
    assert!(
        p.utilities.is_empty(),
        "no partial guess at the static operand"
    );
    assert_eq!(p.dynamic_classes.len(), 1);

    let p = ts("createElement('a', { className: unknownName }, l)\n");
    assert!(p.utilities.is_empty());
    assert_eq!(p.dynamic_classes.len(), 1);
}

// frob:tests crates/crunk-ingest/src/jsx/classes.rs::from_create_element
#[test]
fn create_element_ambiguous_shorthand_is_never_guessed() {
    // Two candidate constants (the adapter scopes at function level): neither is taken, and the
    // site is flagged instead of dropped silently.
    let p = ts(
        "const className = 'text-accent'\nif (x) { const className = 'other-token' }\ncreateElement('span', { className }, label)\n",
    );
    assert!(p.utilities.is_empty(), "{:?}", p.utilities);
    assert_eq!(p.dynamic_classes.len(), 1);
}

// frob:tests crates/crunk-ingest/src/jsx/classes.rs::from_attributes
#[test]
fn the_dynamic_part_of_a_classname_is_flagged() {
    let source = "<div style={{ margin: '13px' }} className={\"p-[7px] \" + x} />";
    let p = tsx(source);
    assert_eq!(p.declarations.len(), 1);
    assert_eq!(
        (
            p.declarations[0].prop.as_str(),
            p.declarations[0].value.as_str()
        ),
        ("margin", "13px")
    );
    assert_eq!(names(&p), ["p-[7px]"], "the static fragment is produced");
    assert_eq!(p.dynamic_classes.len(), 1, "the dynamic part is flagged");
    assert_eq!(p.dynamic_classes[0].line, 1);
    let fully_static = tsx("<div className=\"p-[7px] flex\" />");
    assert!(fully_static.dynamic_classes.is_empty());
}

// frob:tests crates/crunk-ingest/src/model.rs::Stylesheet.is_fixable
#[test]
fn a_style_prop_site_is_not_fixable() {
    let (_dir, spec) = common::synthetic_jsx(
        &["web/**/*.tsx"],
        &[
            ("styles/base/a.css", ".a { margin: 3px; }\n"),
            (
                "web/Card.tsx",
                "export const C = () => <div style={{ margin: '13px' }} className=\"p-[7px]\" />;\n",
            ),
        ],
    );
    let got = ingest_tree(&spec, &Cache::null()).unwrap().styles;
    let jsx = got
        .sheets
        .iter()
        .find(|s| s.bucket == Some(Bucket::Jsx))
        .expect("jsx sheet");
    assert!(!jsx.is_fixable());
    assert_eq!(jsx.declarations.len(), 1);
    assert_eq!(jsx.component.as_deref(), Some("Card"));
    let css = got
        .sheets
        .iter()
        .find(|s| s.bucket == Some(Bucket::Base))
        .expect("css sheet");
    assert!(css.is_fixable());
}

// frob:tests crates/crunk-ingest/src/jsx/style.rs::declarations
#[test]
fn documented_style_divergences_from_python() {
    // React's unitless list: `flex: 1` is no length (Python read 1px).
    let p =
        tsx("<div style={{ flex: 1, WebkitMask: 'none', '--accentColor': '#fff', width: 3 }} />");
    let by = |prop: &str| p.declarations.iter().find(|d| d.prop == prop).unwrap();
    assert!(by("flex").lengths.is_empty());
    assert_eq!(by("width").lengths.len(), 1);
    // CSS spelling of vendor prefixes and custom properties.
    assert_eq!(by("-webkit-mask").value, "none");
    assert_eq!(by("--accentColor").value, "#fff");
    // A wrapped object literal is still an inline style.
    let p = tsx("<div style={{ margin: '4px' } as React.CSSProperties} />");
    assert_eq!(p.declarations.len(), 1);
}

// Syntax that does not parse becomes a diagnostic; the rest of the file still ingests.
// frob:tests crates/crunk-ingest/src/jsx/mod.rs::parse_in_project
#[test]
fn a_syntax_error_is_reported_and_the_rest_of_the_file_still_counts() {
    // The adapter keeps a parse-error hole where tree-sitter could not recover; a lone missing
    // token it repairs silently is not reported.
    let source = "const x = <div className=\"p-4 flex\" />;\nif (x) {\n";
    let p = parse_jsx_source("a.tsx", source, RFS).unwrap();
    assert_eq!(names(&p), ["p-4", "flex"]);
    assert!(
        p.errors
            .iter()
            .any(|e| e.starts_with("jsx syntax error at line")),
        "{:?}",
        p.errors
    );
}

// frob:tests crates/crunk-ingest/src/jsx/project.rs::ingest
#[test]
fn the_walk_reads_globbed_sources_caches_them_and_survives_a_broken_file() {
    let (dir, spec) = common::synthetic_jsx(
        &["web/**/*.tsx"],
        &[
            (
                "web/A.tsx",
                "export const A = () => <b className=\"p-4 flex\" />;\n",
            ),
            ("web/other.css", ".a { color: red; }\n"),
            (
                "lib/B.tsx",
                "export const B = () => <b className=\"never-seen\" />;\n",
            ),
        ],
    );
    std::fs::write(dir.path().join("web/Broken.tsx"), b"\xff\xfe\x00not-utf8").unwrap();
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());
    let first = ingest_tree(&spec, &cache).unwrap();
    let jsx: Vec<_> = first
        .styles
        .sheets
        .iter()
        .filter(|s| s.bucket == Some(Bucket::Jsx))
        .collect();
    assert_eq!(
        jsx.len(),
        1,
        "only the glob matches, and not the broken file"
    );
    assert_eq!(jsx[0].utilities.len(), 2);
    assert!(
        first
            .styles
            .diagnostics
            .iter()
            .any(|d| d.path.ends_with("Broken.tsx")),
        "{:?}",
        first.styles.diagnostics
    );
    assert_eq!((first.stats.jsx_parsed, first.stats.jsx_cached), (1, 0));

    let second = ingest_tree(&spec, &cache).unwrap();
    assert_eq!((second.stats.jsx_parsed, second.stats.jsx_cached), (0, 1));
    assert!(
        first.styles == second.styles,
        "the cached result differs from the parsed one"
    );

    // A change to any TS source (here one the globs do not match) invalidates the tree.
    common::write(dir.path(), "lib/B.tsx", "export const B = 1;\n");
    let third = ingest_tree(&spec, &cache).unwrap();
    assert_eq!((third.stats.jsx_parsed, third.stats.jsx_cached), (1, 0));
}

// frob:tests crates/crunk-ingest/src/jsx/project.rs::ingest
#[test]
fn no_globs_means_no_jsx_and_named_paths_narrow_the_sources() {
    let files = [
        (
            "web/A.tsx",
            "export const A = () => <b className=\"p-4 flex\" />;\n",
        ),
        (
            "web/B.tsx",
            "export const B = () => <b className=\"gap-2 mt-1\" />;\n",
        ),
    ];
    let (_off, spec_off) = common::synthetic(&files);
    let got = ingest_tree(&spec_off, &Cache::null()).unwrap();
    assert!(
        got.styles
            .sheets
            .iter()
            .all(|s| s.bucket != Some(Bucket::Jsx))
    );

    let (dir, spec) = common::synthetic_jsx(&["web/**/*.tsx"], &files);
    let named = vec![dir.path().join("web/B.tsx")];
    let got = crunk_ingest::ingest_paths(&named, &spec, &Cache::null()).unwrap();
    let jsx: Vec<_> = got
        .styles
        .sheets
        .iter()
        .filter(|s| s.bucket == Some(Bucket::Jsx))
        .collect();
    assert_eq!(jsx.len(), 1);
    assert!(jsx[0].path.ends_with("web/B.tsx"));
    let dir_named = vec![dir.path().join("web")];
    let got = crunk_ingest::ingest_paths(&dir_named, &spec, &Cache::null()).unwrap();
    assert_eq!(
        got.styles
            .sheets
            .iter()
            .filter(|s| s.bucket == Some(Bucket::Jsx))
            .count(),
        2
    );
}

// frob:tests crates/crunk-ingest/src/jsx/classes.rs::from_attributes
#[test]
fn every_certain_class_token_of_the_engine_is_among_the_utilities() {
    use gob_ir::{Model, markup};
    use gob_symbols::fold_file;
    use gob_walk::{Digest, FileEntry, LanguageHint};

    let source = "export const A = (p) => <div className=\"hover:flex p-4\" />;\nexport const B = (p) => <div className={`gap-2 ${p.x} mt-1`} />;\nexport const C = (p) => <div className={clsx(\"a b\", p.on && \"c\", { d: p.y })} />;\n";
    let entry = FileEntry {
        path: "a.tsx".into(),
        size: source.len() as u64,
        digest: Digest::of(source.as_bytes()),
        language: LanguageHint::from_path("a.tsx"),
    };
    let folded = fold_file(&entry, source).unwrap();
    let model = Model::new(folded.term, folded.scopes);
    let parsed = tsx(source);
    let have: std::collections::BTreeSet<String> = parsed
        .utilities
        .iter()
        .map(|u| {
            u.variants
                .iter()
                .map(String::as_str)
                .chain([u.name.as_str()])
                .collect::<Vec<_>>()
                .join(":")
        })
        .collect();
    let mut checked = 0;
    for el in markup::elements(&model) {
        for attr in &el.attributes {
            for token in markup::class_tokens(&model, attr).must() {
                assert!(have.contains(token), "{token} missing from {have:?}");
                checked += 1;
            }
        }
    }
    assert!(checked >= 4, "the engine answered {checked} certain tokens");
}
