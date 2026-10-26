//! The frozen Python capture: the command matrix cases and the working copy they run in.

use std::path::{Path, PathBuf};

use serde_json::Value;

/// The matrix projects, in capture order (the Python capture ran them in this order too).
pub const PROJECTS: [&str; 4] = [
    "int04_default",
    "init_default",
    "gallery005_routes",
    "screens_v1_1",
];

/// The `tests/crunk-parity` directory.
pub fn parity_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/crunk-parity")
}

/// One captured Python invocation and its golden output.
#[derive(Debug, Clone)]
pub struct Case {
    /// `<project>/<name>`: the id divergences refer to.
    pub id: String,
    /// The matrix project the command ran in.
    pub project: String,
    /// The Python argv, after the program name.
    pub argv: Vec<String>,
    /// The Python exit code.
    pub exit: i64,
    /// The Python stdout with the `<WORK>` placeholder still in it.
    pub stdout: String,
}

fn read(path: &Path) -> String {
    std::fs::read_to_string(path).unwrap_or_else(|e| panic!("read corpus file: {e}"))
}

/// Every captured case of every matrix project, in a stable order.
#[expect(
    clippy::disallowed_methods,
    reason = "test-only: capture file names are ASCII ids"
)]
pub fn load_cases() -> Vec<Case> {
    let mut cases = Vec::new();
    for project in PROJECTS {
        let dir = parity_root().join("expected/matrix").join(project);
        let mut names: Vec<String> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("read corpus file: {e}"))
            .flatten()
            .filter_map(|e| e.file_name().into_string().ok())
            .filter_map(|n| n.strip_suffix(".cmd.json").map(str::to_owned))
            .collect();
        names.sort();
        for name in names {
            let meta: Value = serde_json::from_str(&read(&dir.join(format!("{name}.cmd.json"))))
                .expect("cmd.json is json");
            cases.push(Case {
                id: format!("{project}/{name}"),
                project: project.to_owned(),
                argv: meta["argv"]
                    .as_array()
                    .expect("argv")
                    .iter()
                    .map(|a| a.as_str().expect("argv item").to_owned())
                    .collect(),
                exit: meta["exit"].as_i64().expect("exit"),
                stdout: read(&dir.join(format!("{name}.stdout"))),
            });
        }
    }
    cases
}

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("mkdir");
    for entry in std::fs::read_dir(from).expect("read_dir").flatten() {
        let (src, dst) = (entry.path(), to.join(entry.file_name()));
        if src.is_dir() {
            copy_tree(&src, &dst);
        } else {
            std::fs::copy(&src, &dst).expect("copy");
        }
    }
}

/// A scratch copy of the static fixtures, so a run that writes files cannot dirty the corpus.
pub fn work_copy(parent: &Path) -> PathBuf {
    let work = parent.join("work");
    copy_tree(&parity_root().join("fixtures/static"), &work);
    for project in PROJECTS {
        disable_ramp(&work.join(project));
    }
    work
}

/// Opt the `crunk.toml` in `dir` out of the severity ramp; a no-op when absent or already set.
fn disable_ramp(dir: &Path) {
    let path = dir.join("crunk.toml");
    let Ok(text) = std::fs::read_to_string(&path) else {
        return;
    };
    if !text.contains("[rules]") {
        std::fs::write(&path, format!("{text}\n[rules]\nramp = false\n")).expect("write");
    }
}
