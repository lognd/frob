//! `crunk check --static` and `[tailwind] engine = "static"` never execute repository JavaScript.

// frob:ticket 01M7AV37ZMX53C3NNTGFA8TB2V

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A project whose Tailwind config and install each drop a marker file when node loads them.
fn booby_trapped(engine_line: &str) -> (tempfile::TempDir, std::path::PathBuf) {
    let dir = tempfile::tempdir().expect("tempdir");
    let marker = dir.path().join("EXECUTED");
    let trap = format!(
        "require('fs').writeFileSync({:?}, 'ran');\nmodule.exports = {{ theme: {{}} }};\n",
        marker.to_string_lossy()
    );
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    write(
        dir.path(),
        "crunk.toml",
        &format!(
            "{spec}\n[tailwind]\nconfig = \"tailwind.config.js\"\n{engine_line}\n[jsx]\nglobs = [\"src/**/*\"]\n"
        ),
    );
    write(dir.path(), "styles/base/a.css", ".a { margin: 0; }\n");
    write(dir.path(), "styles/tokens.css", ":root {}\n");
    write(
        dir.path(),
        "src/A.tsx",
        "export const A = () => <div className=\"p-4\" />;\n",
    );
    write(dir.path(), "tailwind.config.js", &trap);
    write(
        dir.path(),
        "node_modules/tailwindcss/package.json",
        "{\"name\":\"tailwindcss\",\"version\":\"3.4.0\",\"main\":\"index.js\"}\n",
    );
    for js in [
        "index.js",
        "resolveConfig.js",
        "lib/index.js",
        "lib/util/resolveConfig.js",
    ] {
        write(dir.path(), &format!("node_modules/tailwindcss/{js}"), &trap);
    }
    (dir, marker)
}

// frob:tests crates/crunk-check/src/tailwind.rs::collect
#[test]
fn the_static_flag_never_executes_repository_javascript() {
    let (dir, marker) = booby_trapped("");
    let opts = CheckOptions {
        static_tailwind: true,
        ..CheckOptions::default()
    };
    run(dir.path(), &opts).expect("run");
    assert!(!marker.exists(), "repository JavaScript ran under --static");
}

// frob:tests crates/crunk-check/src/tailwind.rs::collect
#[test]
fn engine_static_in_crunk_toml_never_executes_repository_javascript() {
    let (dir, marker) = booby_trapped("engine = \"static\"");
    run(dir.path(), &CheckOptions::default()).expect("run");
    assert!(
        !marker.exists(),
        "repository JavaScript ran under engine = static"
    );
}
