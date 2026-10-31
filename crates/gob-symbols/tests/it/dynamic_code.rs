//! Python `eval`, `exec` and `compile` resolve symbolically: a constant source is scanned in the
//! scopes of the call, anything else is an unresolved (computed) use naming the builtin.

// frob:ticket 01M6422ZJ6EGH0AP4ZYT78E2WZ

use gob_symbols::path_uses;

/// `(path, computed)` of every use in `src`.
fn uses(src: &str) -> Vec<(String, bool)> {
    path_uses("python", src)
        .into_iter()
        .map(|u| (u.path, u.computed))
        .collect()
}

fn unresolved(src: &str, builtin: &str) -> bool {
    uses(src).iter().any(|(p, c)| p == builtin && *c)
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_non_constant_source_is_unresolved_for_each_builtin() {
    for name in ["eval", "exec", "compile"] {
        let want = format!("builtins.{name}");
        for src in [
            format!("def go(s):\n    {name}(s)\n"),
            format!("def go(s):\n    {name}('a' + s)\n"),
            format!("def go(s):\n    {name}(f'a{{s}}')\n"),
            format!("def go(s):\n    {name}()\n"),
            format!("def go(s):\n    {name}(*s)\n"),
            format!("def go(s):\n    {name}(source=s)\n"),
        ] {
            assert!(unresolved(&src, &want), "{src}: {:?}", uses(&src));
        }
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn aliases_of_the_builtin_are_resolved_symbolically() {
    for src in [
        "e = eval\n\n\ndef go(s):\n    e(s)\n",
        "import builtins\n\n\ndef go(s):\n    builtins.eval(s)\n",
        "import builtins as b\n\n\ndef go(s):\n    b.eval(s)\n",
        "from builtins import eval as e\n\n\ndef go(s):\n    e(s)\n",
        "import builtins\n\n\ndef go(s):\n    getattr(builtins, 'eval')(s)\n",
        "def go(s):\n    __builtins__.eval(s)\n",
        "def go(s):\n    __builtins__['eval'](s)\n",
        "def go(s):\n    globals()['eval'](s)\n",
        "def go(s):\n    (eval)(s)\n",
    ] {
        assert!(unresolved(src, "builtins.eval"), "{src}: {:?}", uses(src));
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_computed_builtin_lookup_is_unresolved_under_builtins() {
    for src in [
        "import builtins\n\n\ndef go(n, s):\n    getattr(builtins, n)(s)\n",
        "def go(n, s):\n    __builtins__[n](s)\n",
    ] {
        assert!(unresolved(src, "builtins"), "{src}: {:?}", uses(src));
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_function_valued_reference_is_unresolved() {
    let src = "def go(xs):\n    return list(map(eval, xs))\n";
    assert!(unresolved(src, "builtins.eval"), "{:?}", uses(src));
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_constant_source_is_scanned_in_the_scopes_of_the_call() {
    for src in [
        "import os\n\n\ndef go():\n    eval(\"os.system('x')\")\n",
        "import os as o\n\n\ndef go():\n    exec('o.system(' + \"'x')\")\n",
        "import os\nCODE = \"os.system('x')\"\n\n\ndef go():\n    exec(CODE)\n",
        "def go():\n    eval(\"__import__('os').system('x')\")\n",
        "import os\n\n\ndef go():\n    eval(\"eval('os.system(1)')\")\n",
    ] {
        let u = uses(src);
        assert!(
            u.iter().any(|(p, c)| p == "os.system" && !*c),
            "{src}: {u:?}"
        );
        assert!(!u.iter().any(|(p, _)| p == "builtins.eval"), "{src}: {u:?}");
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_constant_source_that_cannot_be_read_stays_unresolved() {
    for src in [
        "def go():\n    eval('1 +')\n",
        "def go():\n    eval(\"eval('eval(\\\"eval(1)\\\")')\")\n",
    ] {
        assert!(unresolved(src, "builtins.eval"), "{src}: {:?}", uses(src));
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_shadowing_binding_is_not_the_builtin() {
    for src in [
        "def eval(s):\n    return s\n\n\ndef go(s):\n    eval(s)\n",
        "def go(eval, s):\n    eval(s)\n",
        "import mylib\n\n\ndef go(s):\n    mylib.eval(s)\n",
        "def go(o, s):\n    o.eval(s)\n",
    ] {
        let u = uses(src);
        assert!(
            u.iter().all(|(p, _)| !p.starts_with("builtins")),
            "{src}: {u:?}"
        );
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn strings_and_comments_never_match() {
    let src = "# eval(s)\nDOC = 'eval(s) and exec(s)'\n\n\ndef go():\n    \"\"\"compile(s)\"\"\"\n";
    assert!(uses(src).is_empty(), "{:?}", uses(src));
}
