//! Guard: every per-language capability scanner resolves parsed nodes (imports, aliases, scopes),
//! never raw source text.
//!
//! The check is behavioural, not a grep of the scanner source: a grep is itself a lexical check,
//! and is defeated by a helper, a re-spelling or a regex built at run time. Instead each guarded
//! language is driven through the public [`path_uses`] entry with probes a text search cannot
//! get right. A scanner that decides from text FAILS at least one probe:
//!
//! - `alias`: the capability is reached through an import alias, so the vocabulary name never
//!   appears at the use (a text search finds nothing, and must be absent to be right);
//! - `string`: the vocabulary is spelled only inside a string literal and a comment (a text
//!   search finds it, and must not);
//! - `shadow`: the file declares its own binding with the vocabulary's name (a text search
//!   finds a use, and must not).
//!
//! The completeness test ties the table to the adapter registry, so a new adapter cannot ship
//! without a row here or an explicit, reasoned exemption. A deliberately lexical scanner
//! (`lexical_scan`) proves the guard bites.

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE
// frob:ticket 01M67VHPB1J3X7KNF3WYJYDBPP

use gob_symbols::{PathUse, adapters, path_uses};

/// What a probe demands of a scanner.
#[derive(Clone, Copy)]
enum Want {
    /// Some use resolves to exactly this path.
    Path(&'static str),
    /// No use's path contains this fragment.
    Absent(&'static str),
}

/// One adversarial probe for a language.
struct Probe {
    /// The probe's role: `alias`, `string` or `shadow`.
    kind: &'static str,
    src: &'static str,
    want: Want,
}

/// A guarded language: the `path_uses` tags that share its probes, and the probes.
struct Guarded {
    /// The adapter tag in the registry.
    adapter: &'static str,
    /// The `path_uses` language tags this adapter's scanner serves.
    tags: &'static [&'static str],
    probes: &'static [Probe],
}

/// A scanner under test: `(language tag, source) -> uses`.
type Scan = fn(&str, &str) -> Vec<PathUse>;

const GUARDED: &[Guarded] = &[
    Guarded {
        adapter: "python",
        tags: &["python"],
        probes: &[
            Probe {
                kind: "alias",
                src: "import os as o\no.system('x')\n",
                want: Want::Path("os.system"),
            },
            Probe {
                kind: "string",
                src: "s = \"os.system('x')\"  # os.system(1)\n",
                want: Want::Absent("system"),
            },
            Probe {
                kind: "shadow",
                src: "import os\ndef f(os):\n    os.system('x')\n",
                want: Want::Absent("system"),
            },
        ],
    },
    Guarded {
        adapter: "rust",
        tags: &["rust"],
        probes: &[
            Probe {
                kind: "alias",
                src: "use std::process::Command as C;\nfn f() { C::new(\"ls\"); }\n",
                want: Want::Path("std::process::Command::new"),
            },
            Probe {
                kind: "string",
                src: "fn f() { let _s = \"std::process::Command::new\"; /* Command::new */ }\n",
                want: Want::Absent("process"),
            },
            Probe {
                kind: "shadow",
                src: "struct Command;\nimpl Command { fn new(_a: &str) -> Self { Command } }\nfn f() { Command::new(\"x\"); }\n",
                want: Want::Absent("process"),
            },
        ],
    },
    Guarded {
        adapter: "go",
        tags: &["go"],
        probes: &[
            Probe {
                kind: "alias",
                src: "package m\nimport e \"os/exec\"\nfunc f() { e.Command(\"ls\") }\n",
                want: Want::Path("os/exec.Command"),
            },
            Probe {
                kind: "string",
                src: "package m\nfunc f() { _ = \"exec.Command(ls)\" // exec.Command\n}\n",
                want: Want::Absent("Command"),
            },
            Probe {
                kind: "shadow",
                src: "package m\nimport \"os/exec\"\nfunc f() {\n\texec := struct{ Command func(string) }{}\n\texec.Command(\"ls\")\n}\n",
                want: Want::Absent("Command"),
            },
        ],
    },
    Guarded {
        adapter: "java",
        tags: &["java"],
        probes: &[
            Probe {
                kind: "alias",
                src: "class A { void f() { Runtime rt = Runtime.getRuntime(); rt.exec(\"x\"); } }\n",
                want: Want::Path("java.lang.Runtime.exec"),
            },
            Probe {
                kind: "string",
                src: "class A { String s = \"new ProcessBuilder(x)\"; // new ProcessBuilder(y)\n}\n",
                want: Want::Absent("ProcessBuilder"),
            },
            Probe {
                kind: "shadow",
                src: "class ProcessBuilder { ProcessBuilder(String s) {} }\nclass A { void f() { new ProcessBuilder(\"x\"); } }\n",
                want: Want::Absent("java.lang.ProcessBuilder"),
            },
        ],
    },
    Guarded {
        adapter: "typescript",
        tags: &["typescript", "tsx", "javascript", "jsx"],
        probes: &[
            Probe {
                kind: "alias",
                src: "import * as cp from \"node:child_process\";\ncp.exec(\"x\");\n",
                want: Want::Path("child_process.exec"),
            },
            Probe {
                kind: "string",
                src: "const s = \"child_process.exec(x) fetch(y)\"; // child_process.exec\n",
                want: Want::Absent("exec"),
            },
            Probe {
                kind: "shadow",
                src: "const fetch = (u: string) => u;\nfetch(\"x\");\n",
                want: Want::Absent("fetch"),
            },
        ],
    },
    Guarded {
        adapter: "csharp",
        tags: &["csharp"],
        probes: &[
            Probe {
                kind: "alias",
                src: "using P = System.Diagnostics.Process;\nclass A { void F() { P.Start(\"x\"); } }\n",
                want: Want::Path("System.Diagnostics.Process.Start"),
            },
            Probe {
                kind: "string",
                src: "class A { string s = \"Process.Start(x)\"; // Process.Start(y)\n}\n",
                want: Want::Absent("Start"),
            },
            Probe {
                kind: "shadow",
                src: "class Process { public static void Start(string s) {} }\nclass A { void F() { Process.Start(\"x\"); } }\n",
                want: Want::Absent("System.Diagnostics"),
            },
        ],
    },
];

/// Adapters with no capability scanner, each with the reason: they read data or markup, and
/// decide no capability from source code.
const EXEMPT: &[(&str, &str)] = &[
    ("markdown", "prose; no executable code"),
    (
        "yaml",
        "data; workflow capabilities come from the actions adapter",
    ),
    (
        "github-actions",
        "structured workflow data folded from the yaml tree",
    ),
    (
        "dockerfile",
        "instruction tree; image facts, not code capabilities",
    ),
    ("dotenv", "key/value data"),
    ("css", "style sheets"),
    (
        "html",
        "markup; script bodies are routed to the typescript scanner",
    ),
];

/// Runs every probe of `g` through `scan` for every tag; returns the failures.
fn violations(scan: Scan, g: &Guarded) -> Vec<String> {
    let mut out = Vec::new();
    for tag in g.tags {
        for p in g.probes {
            let uses = scan(tag, p.src);
            let ok = match p.want {
                Want::Path(w) => uses.iter().any(|u| u.path == w),
                Want::Absent(w) => uses.iter().all(|u| !u.path.contains(w)),
            };
            if !ok {
                let got: Vec<&str> = uses.iter().map(|u| u.path.as_str()).collect();
                out.push(format!(
                    "{tag}/{}: scanner decided from text, got {got:?}",
                    p.kind
                ));
            }
        }
    }
    out
}

/// Every violation across all guarded languages.
fn all_violations(scan: Scan) -> Vec<String> {
    GUARDED.iter().flat_map(|g| violations(scan, g)).collect()
}

/// A deliberately lexical scanner: reports any known vocabulary word found anywhere in the text.
fn lexical_scan(language: &str, source: &str) -> Vec<PathUse> {
    const VOCAB: &[&str] = &[
        "system",
        "Command",
        "exec",
        "ProcessBuilder",
        "Start",
        "fetch",
    ];
    let mut out = Vec::new();
    for word in VOCAB {
        let mut from = 0;
        while let Some(i) = source[from..].find(word) {
            let offset = from + i;
            tracing::debug!(language, word, offset, "lexical fixture hit");
            out.push(PathUse {
                offset,
                line: 1,
                spelled: (*word).to_owned(),
                path: (*word).to_owned(),
                call: true,
                dynamic: false,
                external_root: false,
                computed: false,
                wildcards: Vec::new(),
                maybe: false,
            });
            from = offset + word.len();
        }
    }
    out
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn every_capability_scanner_resolves_nodes_not_text() {
    let v = all_violations(path_uses);
    assert!(v.is_empty(), "lexical scanners found:\n{}", v.join("\n"));
}

// frob:tests crates/gob-symbols/src/canon.rs::path_uses
#[test]
fn a_lexical_scanner_fails_the_guard() {
    for g in GUARDED {
        let v = violations(lexical_scan, g);
        assert!(
            !v.is_empty(),
            "{} lexical fixture passed the guard",
            g.adapter
        );
    }
}

#[test]
fn guard_covers_every_registered_adapter() {
    let tags: Vec<&str> = adapters().iter().map(|a| a.language()).collect();
    for t in &tags {
        let guarded = GUARDED.iter().any(|g| g.adapter == *t);
        let exempt = EXEMPT.iter().any(|(e, _)| e == t);
        assert!(
            guarded ^ exempt,
            "adapter `{t}` needs exactly one of a GUARDED row or an EXEMPT reason"
        );
    }
    for g in GUARDED {
        assert!(tags.contains(&g.adapter), "stale guard row {}", g.adapter);
    }
    for (e, why) in EXEMPT {
        assert!(tags.contains(e), "stale exemption {e}");
        assert!(!why.is_empty());
    }
}
