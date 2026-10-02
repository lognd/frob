//! Property tests: `fmt` is a fixed point and `parse(fmt(m))` equals `m` in U, for generated models.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use grimble_model::dump::u_signature;
use grimble_model::fmt::format_file;
use grimble_model::fold::fold_file;
use grimble_model::parse::parse_file;
use proptest::prelude::*;

fn sp() -> impl Strategy<Value = String> {
    prop_oneof![
        Just(" ".to_owned()),
        Just("\n    ".to_owned()),
        Just("   ".to_owned()),
        Just("\t".to_owned())
    ]
}

fn glob() -> impl Strategy<Value = String> {
    prop::sample::select(vec![
        "\"crates/a/**\"",
        "\"crates/b/src/lib.rs::f\"",
        "\"src/*.rs\"",
        "\"docs/\"",
        "\"x/{a,b}/**\"",
        "\"lib/?.rs::T.*\"",
    ])
    .prop_map(str::to_owned)
}

fn leaf() -> impl Strategy<Value = String> {
    prop_oneof![
        glob(),
        Just("lang(rust)".to_owned()),
        Just("lang(python)".to_owned()),
        Just("kind(function, method)".to_owned()),
        Just("kind(type)".to_owned()),
        Just("attr(vis = \"pub\")".to_owned()),
        Just("attr(timeout <= 30 s)".to_owned()),
        Just("attr(marker)".to_owned()),
    ]
}

fn selector() -> impl Strategy<Value = String> {
    leaf()
        .prop_recursive(3, 12, 3, |inner| {
            prop_oneof![
                (inner.clone(), inner.clone(), sp())
                    .prop_map(|(a, b, s)| format!("({a}{s}&{s}{b})")),
                (inner.clone(), inner.clone(), sp())
                    .prop_map(|(a, b, s)| format!("({a}{s}|{s}{b})")),
                inner.prop_map(|a| format!("!{a}")),
            ]
        })
        .prop_map(|s| {
            // The outer parentheses of a generated group are optional.
            s.strip_prefix('(')
                .and_then(|t| t.strip_suffix(')'))
                .filter(|t| !t.contains('(') || t.matches('(').count() == t.matches(')').count())
                .map_or(s.clone(), str::to_owned)
        })
}

fn comment() -> impl Strategy<Value = String> {
    prop_oneof![
        Just(String::new()),
        Just("// plain\n".to_owned()),
        Just("/* block */\n".to_owned()),
        Just("/// doc text\n".to_owned()),
        Just("// frob:doc docs/x.md#a\n".to_owned()),
    ]
}

fn node_clause() -> impl Strategy<Value = String> {
    prop_oneof![
        Just("kind component;".to_owned()),
        Just("clearance Internal;".to_owned()),
        selector().prop_map(|s| format!("owns {s};")),
        selector().prop_map(|s| format!("surface {s};")),
        (selector(), prop::bool::ANY).prop_map(|(s, at)| if at {
            format!("may fs.read at {s};")
        } else {
            "may exec;".to_owned()
        }),
        Just("may net.connect(\"a.com\", \"b.com\");".to_owned()),
        Just("excuses net.listen because=\"never serves\";".to_owned()),
        Just("attr timeout = 30 s;".to_owned()),
        Just("attr marker;".to_owned()),
        Just("attr tags = [\"a\", \"b\"];".to_owned()),
        Just("alias legacy;".to_owned()),
        Just("accept CAP003 because=\"by design\";".to_owned()),
    ]
}

fn clause_block(clause: BoxedStrategy<String>) -> impl Strategy<Value = String> {
    prop::collection::vec((comment(), clause, sp()), 0..6).prop_map(|cs| {
        let mut out = String::new();
        for (c, t, s) in cs {
            out.push_str(&c);
            out.push_str(&t);
            out.push_str(&s);
        }
        out
    })
}

fn other_entity(i: usize) -> BoxedStrategy<String> {
    let pick = i % 6;
    match pick {
        0 => clause_block(
            prop_oneof![
                Just("label Public;".to_owned()),
                Just("rate 100 req/s;".to_owned()),
                Just("age 5 min;".to_owned()),
                Just("transport http, ipc;".to_owned()),
                selector().prop_map(|s| format!("producer {s};")),
                selector().prop_map(|s| format!("consumer {s};")),
            ]
            .boxed(),
        )
        .prop_map(move |b| format!("flow f{i} : n0 -> n1 {{ {b} }}"))
        .boxed(),
        1 => clause_block(
            prop_oneof![
                selector().prop_map(|s| format!("shape {s};")),
                Just("versioning scheme=semver current=\"1.0.0\" compat=full;".to_owned()),
            ]
            .boxed(),
        )
        .prop_map(move |b| format!("contract c{i} {{ {b} }}"))
        .boxed(),
        2 => clause_block(
            prop_oneof![
                Just("noflow n0 -> n1;".to_owned()),
                Just("proof L2;".to_owned()),
                selector().prop_map(|s| format!("evidence tests {s};")),
                Just("evidence ref \"docs/a.md#x\";".to_owned()),
            ]
            .boxed(),
        )
        .prop_map(move |b| format!("claim k{i} {{ {b} }}"))
        .boxed(),
        3 => clause_block(
            prop_oneof![
                Just("kind artifact;".to_owned()),
                Just("level unit;".to_owned()),
                Just("ref \"d.md#a\";".to_owned()),
                Just("satisfies v0;".to_owned()),
            ]
            .boxed(),
        )
        .prop_map(move |b| format!("vmodel v{i} {{ {b} }}"))
        .boxed(),
        4 => Just(format!(
            "boundary b{i} endorse f0 : foreign -> trusted when \"ok\";"
        ))
        .boxed(),
        _ => Just(format!(
            "pack p{i} {{ ref \"grimble/p{i}\"; version \"1.0.0\"; }}"
        ))
        .boxed(),
    }
}

fn model() -> impl Strategy<Value = String> {
    let nodes = prop::collection::vec((comment(), clause_block(node_clause().boxed())), 1..4);
    let others = prop::collection::vec(0usize..6, 0..5).prop_flat_map(|idxs| {
        idxs.into_iter()
            .enumerate()
            .map(|(n, i)| other_entity(i * 10 + n))
            .collect::<Vec<_>>()
    });
    (nodes, others, comment(), sp()).prop_flat_map(|(nodes, others, head, s)| {
        let mut items: Vec<String> = nodes
            .into_iter()
            .enumerate()
            .map(|(i, (c, b))| format!("{c}node n{i} : trusted {{ {b} }}"))
            .collect();
        items.extend(others);
        Just(items).prop_shuffle().prop_map(move |items| {
            format!("{head}grimble = \"2\";{s}module m;{s}{}\n", items.join(&s))
        })
    })
}

fn signature(path: &str, text: &str) -> (String, bool) {
    let parsed = parse_file(path, text.as_bytes());
    let folded = fold_file(&parsed, "").expect("fold");
    (u_signature(&folded), parsed.is_damaged())
}

fn soup() -> impl Strategy<Value = String> {
    let words = prop::sample::select(vec![
        "grimble",
        "=",
        "\"2\"",
        ";",
        "module",
        "m",
        "part",
        "of",
        "node",
        "flow",
        "claim",
        "{",
        "}",
        "(",
        ")",
        "[",
        "]",
        ":",
        "::",
        "->",
        "<=",
        "&",
        "|",
        "!",
        ",",
        ".",
        "owns",
        "may",
        "at",
        "\"a/**\"",
        "// c\n",
        "/* x",
        "*/",
        "///",
        "30",
        "s",
        "2026-01-01",
        "include",
        "namespace",
        "extend",
        "accept",
        "because",
        "\"",
        "\\",
        "\n",
        "x",
        "trusted",
    ]);
    prop::collection::vec(words, 0..60)
        .prop_map(|w| format!("grimble = \"2\"; module m; {}", w.join(" ")))
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(256))]

    #[test]
    fn the_pipeline_is_total_on_token_soup(src in soup()) {
        let parsed = parse_file("s.grmb", src.as_bytes());
        let folded = fold_file(&parsed, "").expect("a fold never fails");
        let _ = u_signature(&folded);
        let _ = format_file(&parsed);
        let mf = grimble_model::ModelFiles::new().with_file("s.grmb", src.clone());
        let _ = grimble_model::check_model(&mf);
    }

    #[test]
    fn the_pipeline_is_total_on_arbitrary_bytes(bytes in prop::collection::vec(any::<u8>(), 0..200)) {
        let parsed = parse_file("b.grmb", &bytes);
        let folded = fold_file(&parsed, "").expect("a fold never fails");
        let _ = u_signature(&folded);
    }


    #[test]
    fn fmt_is_a_fixed_point_and_preserves_u(src in model()) {
        let parsed = parse_file("g.grmb", src.as_bytes());
        prop_assume!(!parsed.is_damaged());
        let once = format_file(&parsed).expect("formats");
        let again = format_file(&parse_file("g.grmb", once.as_bytes())).expect("formats");
        prop_assert_eq!(&once, &again, "fmt(fmt(x)) == fmt(x)");
        let (a, _) = signature("g.grmb", &src);
        let (b, damaged) = signature("g.grmb", &once);
        prop_assert!(!damaged, "fmt output reparses cleanly");
        prop_assert_eq!(a, b, "parse(fmt(m)) is identical to m in U");
    }

    #[test]
    fn the_generator_makes_valid_models(src in model()) {
        let parsed = parse_file("g.grmb", src.as_bytes());
        prop_assert!(!parsed.is_damaged(), "{:?}\n{}", parsed.diags, src);
    }
}
