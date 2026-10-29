//! Name-computed lookups resolve through the shared gob-ir rule in every language: a literal name
//! denotes the origin symbol exactly as the direct form, any other name is flagged computed.

// frob:ticket 01M6422ZFEPZJYJQDDM6CV37RW

use gob_symbols::path_uses;

/// `(path, computed)` of every use in `src`.
fn uses(lang: &str, src: &str) -> Vec<(String, bool)> {
    path_uses(lang, src)
        .into_iter()
        .map(|u| (u.path, u.computed))
        .collect()
}

fn has(u: &[(String, bool)], path: &str, computed: bool) -> bool {
    u.iter().any(|(p, c)| p == path && *c == computed)
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn python_literal_names_equal_the_direct_form() {
    let direct = uses("python", "import os\nos.system('x')\n");
    assert!(has(&direct, "os.system", false), "{direct:?}");
    for src in [
        "import os\ngetattr(os, 'system')('x')\n",
        "__import__('os').system('x')\n",
        "import importlib\nimportlib.import_module('os').system('x')\n",
        "import os\nG = getattr\nG(os, 'sys' + 'tem')('x')\n",
        "import os\nN = 'system'\ngetattr(os, N)('x')\n",
        "import os\ngetattr(os, 'sys' 'tem')('x')\n",
    ] {
        let u = uses("python", src);
        assert!(has(&u, "os.system", false), "{src}: {u:?}");
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn python_non_literal_names_are_computed() {
    for src in [
        "import os\ndef f(n):\n    getattr(os, n)('x')\n",
        "def f(n):\n    __import__(n)\n",
        "import importlib\ndef f(n):\n    importlib.import_module(n)\n",
        "import os\ndef f(n):\n    getattr(os, f'sys{n}')\n",
        "import os\ndef f(n):\n    vars(os)[n]\n",
        "import os\ndef f(n):\n    os.__dict__[n]\n",
        "import sys\ndef f(n):\n    sys.modules[n]\n",
    ] {
        let u = uses("python", src);
        assert!(u.iter().any(|(_, c)| *c), "{src}: {u:?}");
    }
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn python_f_string_without_interpolation_is_literal_and_shadowing_blocks() {
    let u = uses("python", "import os\ngetattr(os, f'system')('x')\n");
    assert!(has(&u, "os.system", false), "{u:?}");
    let u = uses(
        "python",
        "import os\ndef getattr(o, n):\n    return None\ngetattr(os, 'system')\n",
    );
    assert!(u.iter().all(|(p, _)| p != "os.system"), "{u:?}");
}

// frob:tests crates/gob-symbols/src/lookups.rs::scan
#[test]
fn javascript_literal_names_equal_the_direct_form() {
    for src in [
        "const cp = require('child_process'); cp.exec(x);",
        "const { exec } = require('child_process'); exec(x);",
        "const cp = require('child_' + 'process'); cp['exec'](x);",
    ] {
        let u = uses("javascript", src);
        assert!(
            u.iter().any(|(p, _)| p == "child_process.exec"),
            "{src}: {u:?}"
        );
    }
    let u = uses(
        "typescript",
        "async function f() { const m = await import('x'); m.run(); }",
    );
    assert!(u.iter().any(|(p, _)| p == "x.run"), "{u:?}");
    let u = uses("javascript", "const fs = require('fs'); fs['readFile'](p);");
    assert!(has(&u, "fs.readFile", false), "{u:?}");
}

// frob:tests crates/gob-symbols/src/lookups.rs::scan
#[test]
fn javascript_non_literal_names_are_computed() {
    for src in [
        "function f(n) { return require(n); }",
        "const fs = require('fs'); function f(k) { return fs[k]; }",
        "function f(n) { return import(n); }",
        "function f(n) { return require(`a${n}`); }",
    ] {
        let u = uses("javascript", src);
        assert!(u.iter().any(|(_, c)| *c), "{src}: {u:?}");
    }
}

// frob:tests crates/gob-symbols/src/lookups.rs::scan
#[test]
fn csharp_literal_names_resolve_and_others_are_computed() {
    let u = uses(
        "csharp",
        "class C { void M() { var t = Type.GetType(\"System.Diagnostics.Process\"); } }",
    );
    assert!(has(&u, "System.Diagnostics.Process", false), "{u:?}");
    let u = uses(
        "csharp",
        "class C { void M(string n) { var t = Type.GetType(n); } }",
    );
    assert!(u.iter().any(|(_, c)| *c), "{u:?}");
    let u = uses(
        "csharp",
        "class C { void M(string n) { var t = Type.GetType($\"A.{n}\"); } }",
    );
    assert!(u.iter().any(|(_, c)| *c), "{u:?}");
}
