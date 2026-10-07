//! JavaScript test runners: which of vitest and jest runs the tests of a workspace member (~RNQ92ZK).
//!
//! The member is the package of the nearest enclosing `package.json` (the TypeScript counterpart of a Cargo
//! package, from the `gob_symbols` node project model); a repository without one is a single member at the
//! root. The runner is vitest when the member's `package.json` lists `vitest` in any dependency table, or
//! it holds a `vitest.config.*` file, or the test file imports from `vitest`; jest likewise (`jest`,
//! `@jest/globals`, `ts-jest`, `jest.config.*`). Vitest wins a tie. A member with no sign of either (a
//! playwright or `node:test` file) has no runner here: it is named in the log and not selected.

use std::path::Path;

use gob_symbols::NodeProjects;

use crate::select::Framework;

/// Extensions of a runner config file such as `vitest.config.ts`.
const CONFIG_EXTENSIONS: [&str; 5] = ["ts", "js", "mjs", "mts", "cjs"];

/// Dependency names that mark a member as using each runner, vitest first.
const MARKERS: [(Framework, &[&str], &str); 2] = [
    (Framework::Vitest, &["vitest"], "vitest.config"),
    (
        Framework::Jest,
        &["jest", "@jest/globals", "ts-jest"],
        "jest.config",
    ),
];

/// Import specifiers in a test file that name each runner.
const IMPORTS: [(Framework, &[&str]); 2] = [
    (Framework::Vitest, &["vitest"]),
    (Framework::Jest, &["@jest/globals"]),
];

/// Resolves the member and the runner of test files under one work tree, caching package reads.
#[derive(Debug)]
pub struct JsMembers {
    root: std::path::PathBuf,
    projects: NodeProjects,
}

/// The member of a test file and the runner that runs it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JsMember {
    /// Member directory relative to the work tree root (empty at the root).
    pub dir: String,
    /// Which runner runs the member's tests.
    pub framework: Framework,
}

impl JsMembers {
    /// A resolver for the work tree at `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            projects: NodeProjects::new(root),
        }
    }

    /// The member directory of repo-relative `file`: its owning package's directory, else the root.
    fn member_dir(&mut self, file: &str) -> (String, Option<std::sync::Arc<gob_symbols::Package>>) {
        let Some(pkg) = self.projects.owner(file) else {
            return (String::new(), None);
        };
        match self.projects.load_package(&pkg) {
            Ok(p) => (p.dir.clone(), Some(p.clone())),
            Err(reason) => {
                tracing::warn!(
                    pkg,
                    reason,
                    "malformed package.json; treating the member by its directory"
                );
                (
                    pkg.rsplit_once('/')
                        .map_or(String::new(), |(d, _)| d.to_owned()),
                    None,
                )
            }
        }
    }

    /// The member and runner of the test file `file`, whose text is `text` when readable; `None` when no runner is evident.
    pub fn resolve(&mut self, file: &str, text: Option<&str>) -> Option<JsMember> {
        let (dir, pkg) = self.member_dir(file);
        for (framework, deps, config) in MARKERS {
            let by_dep = pkg
                .as_ref()
                .is_some_and(|p| deps.iter().any(|d| p.dependencies.contains(*d)));
            let by_config = CONFIG_EXTENSIONS.iter().any(|ext| {
                let name = format!("{config}.{ext}");
                let rel = if dir.is_empty() {
                    name
                } else {
                    format!("{dir}/{name}")
                };
                self.root.join(rel).is_file()
            });
            if by_dep || by_config {
                tracing::debug!(
                    file,
                    dir,
                    ?framework,
                    by_dep,
                    by_config,
                    "JavaScript runner detected"
                );
                return Some(JsMember { dir, framework });
            }
        }
        for (framework, specs) in IMPORTS {
            if text.is_some_and(|t| imports_any(t, specs)) {
                tracing::debug!(
                    file,
                    dir,
                    ?framework,
                    "JavaScript runner detected by import"
                );
                return Some(JsMember { dir, framework });
            }
        }
        tracing::warn!(
            file,
            "no vitest or jest evident for this test file; not selected"
        );
        None
    }
}

/// True when `text` imports or requires one of `specs` with a quoted specifier.
fn imports_any(text: &str, specs: &[&str]) -> bool {
    specs.iter().any(|s| {
        ["\"", "'"].iter().any(|q| {
            let quoted = format!("{q}{s}{q}");
            text.lines().any(|l| {
                let l = l.trim_start();
                (l.starts_with("import") || l.contains("require(")) && l.contains(&quoted)
            })
        })
    })
}

/// True when `path` is a test file the runners find on their own (`*.test.*` or `*.spec.*`), unlike a `tests/` helper.
pub fn is_runner_test_file(path: &str) -> bool {
    gob_symbols::is_typescript_path(path)
        && path
            .rsplit('/')
            .next()
            .is_some_and(|b| b.split('.').skip(1).any(|s| matches!(s, "test" | "spec")))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tree(files: &[(&str, &str)]) -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tempdir");
        for (p, c) in files {
            let full = dir.path().join(p);
            std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
            std::fs::write(full, c).expect("write");
        }
        dir
    }

    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    #[test]
    fn the_runner_is_detected_per_member_by_dependency_config_and_import() {
        // frob:tests crates/frob-tests/src/node.rs::JsMembers.resolve
        let dir = tree(&[
            ("package.json", r#"{"workspaces":["apps/*"]}"#),
            (
                "apps/a/package.json",
                r#"{"devDependencies":{"vitest":"^2"}}"#,
            ),
            (
                "apps/b/package.json",
                r#"{"devDependencies":{"jest":"^29"}}"#,
            ),
            ("apps/c/package.json", "{}"),
            ("apps/c/jest.config.js", ""),
            ("apps/d/package.json", "{}"),
        ]);
        let mut m = JsMembers::new(dir.path());
        let got = |m: &mut JsMembers, f: &str, t: Option<&str>| m.resolve(f, t);
        assert_eq!(
            got(&mut m, "apps/a/x.test.ts", None),
            Some(JsMember {
                dir: "apps/a".into(),
                framework: Framework::Vitest
            })
        );
        assert_eq!(
            got(&mut m, "apps/b/x.test.ts", None).map(|j| j.framework),
            Some(Framework::Jest)
        );
        assert_eq!(
            got(&mut m, "apps/c/x.test.ts", None).map(|j| j.dir),
            Some("apps/c".into())
        );
        assert_eq!(got(&mut m, "apps/d/x.test.ts", None), None);
        let imp = "import { test } from \"vitest\";\n";
        assert_eq!(
            got(&mut m, "apps/d/x.test.ts", Some(imp)).map(|j| j.framework),
            Some(Framework::Vitest)
        );
        let jimp = "import { test } from '@jest/globals';\n";
        assert_eq!(
            got(&mut m, "apps/d/y.test.ts", Some(jimp)).map(|j| j.framework),
            Some(Framework::Jest)
        );
    }

    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    #[test]
    fn only_dot_test_and_dot_spec_files_are_found_by_the_runners() {
        // frob:tests crates/frob-tests/src/node.rs::is_runner_test_file
        assert!(is_runner_test_file("src/a.test.ts"));
        assert!(is_runner_test_file("a.spec.tsx"));
        assert!(!is_runner_test_file("tests/helper.ts"));
        assert!(!is_runner_test_file("src/a.test.css"));
    }
}
