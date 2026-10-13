//! SYS013 over Python: a src-layout import is a Must edge (an Error across owners), and a call
//! on a receiver of unknown type never names an unrelated same-named method (binding.md 6).

// frob:ticket 01M4FGYMCWYPJ04HFYCKPHPNSQ

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

/// Bind a temp repository of `files` under `model`.
fn bind(model: &str, files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::write(dir.path().join("design/m.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let mf = ModelFiles::new().with_file("design/m.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &mf,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn sys013(b: &Binding) -> Vec<&grimble_bind::BindFinding> {
    b.findings.iter().filter(|f| f.rule == "SYS013").collect()
}

fn model(a: &str, b: &str) -> String {
    format!(
        "grimble = \"2\";\nmodule m;\n\nnode tool : trusted {{\n  kind component;\n  owns \"{a}\";\n}}\nnode lib : trusted {{\n  kind component;\n  owns \"{b}\";\n}}\n"
    )
}

// frob:tests crates/gob-symbols/src/graph/python.rs::module_name
// frob:tests crates/grimble-bind/src/edges.rs::sys013
#[test]
fn src_layout_python_import_across_owners_is_an_error() {
    let m = model("backend/tests/**", "backend/src/**");
    let b = bind(
        &m,
        &[
            ("backend/src/pkg/__init__.py", ""),
            ("backend/src/pkg/api/__init__.py", ""),
            (
                "backend/src/pkg/api/health.py",
                "def check():\n    return 1\n",
            ),
            (
                "backend/tests/test_health.py",
                "from pkg.api.health import check\n\n\ndef test_check():\n    assert check() == 1\n",
            ),
        ],
    );
    let f = sys013(&b);
    assert!(
        f.iter().any(|f| f.reason.is_none()),
        "expected an Error finding: {f:?}"
    );
}

// frob:tests crates/grimble-bind/src/edges.rs::sys013
#[test]
fn a_method_name_collision_is_no_edge_and_unknown_receivers_give_one_unresolved() {
    let m = model("app/**", "lib/**");
    let b = bind(
        &m,
        &[
            (
                "app/use.py",
                "def go():\n    cache = {}\n    cache.get('a')\n    return cache.get('k')\n",
            ),
            (
                "lib/doubles.py",
                "class Broken:\n    def get(self, key):\n        return key\n",
            ),
        ],
    );
    let f = sys013(&b);
    assert!(f.iter().all(|f| f.reason.is_some()), "{f:?}");
    assert!(f.iter().all(|f| !f.message.contains("Broken.get")), "{f:?}");
    let from_go: usize = f
        .iter()
        .filter(|f| f.message.contains("use.py::go"))
        .count();
    assert!(from_go <= 1, "{f:?}");
}
