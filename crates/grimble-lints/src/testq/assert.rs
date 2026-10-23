//! `TESTQ001`: does a test (or a helper it calls) assert anything?
//!
//! The verdict is three-valued. A test that reaches an assertion, directly or through same-file
//! helpers, is clean. One whose every call is decided and none asserts is `No`. A call into a
//! helper whose body is out of sight (imported from a support module, a `mod x;` file, a mixin
//! base) makes the verdict `Unknown`, which the consumer reports as Unresolved, never as a hit.

// frob:ticket 01M4D957J2HZ655A1H8DJ4K8YD

use std::collections::HashSet;

use tree_sitter::Node;

use super::ctx::{Callee, Ctx};
use super::lang::Lang;

/// How far helper-to-helper resolution goes before giving up as Unknown.
const MAX_DEPTH: usize = 8;

/// Words that mark an import path or name as test support code.
const HELPER_WORDS: &[&str] = &[
    "helper", "support", "common", "util", "fixture", "harness", "setup", "testing",
];

/// Python standard-library roots: calls into them are never test helpers.
const STDLIB: &[&str] = &[
    "os",
    "sys",
    "re",
    "json",
    "math",
    "time",
    "datetime",
    "random",
    "itertools",
    "functools",
    "collections",
    "pathlib",
    "typing",
    "asyncio",
    "subprocess",
    "shutil",
    "tempfile",
    "io",
    "logging",
    "copy",
    "uuid",
    "threading",
    "contextlib",
    "dataclasses",
    "enum",
    "string",
    "struct",
    "operator",
    "decimal",
    "fractions",
    "hashlib",
    "base64",
    "pickle",
    "secrets",
];

/// JavaScript/Node standard-library roots: calls into them are never test helpers.
const JS_STDLIB: &[&str] = &[
    "fs",
    "path",
    "os",
    "util",
    "events",
    "http",
    "https",
    "crypto",
    "stream",
    "url",
    "child_process",
    "buffer",
    "zlib",
    "net",
];

/// C# standard-library root namespace.
const CS_STDLIB: &[&str] = &["System"];

/// C# types whose static members are assertions (`using static Xunit.Assert;`).
pub(super) const CS_ASSERT_TYPES: &[&str] = &[
    "Assert",
    "CollectionAssert",
    "StringAssert",
    "FileAssert",
    "DirectoryAssert",
];

/// Segments that make a JS call chain an assertion (`assert.equal`, `x.should.eql`, `chai.expect`).
const JS_ASSERT_SEGS: &[&str] = &["assert", "expect", "should"];

/// Receiver-method names of ava/tape style `t.ok(...)` assertions.
const JS_T_METHODS: &[&str] = &[
    "ok",
    "equal",
    "notEqual",
    "is",
    "not",
    "deepEqual",
    "notDeepEqual",
    "true",
    "truthy",
    "falsy",
    "false",
    "throws",
    "notThrows",
    "rejects",
    "pass",
    "fail",
    "same",
    "notSame",
    "match",
    "notMatch",
    "snapshot",
    "assert",
    "error",
];

/// Segments that make a `C#` call chain an assertion (`xUnit`, `NUnit`, `MSTest`, `FluentAssertions`, `NSubstitute`).
const CS_ASSERT_SEGS: &[&str] = &[
    "Assert",
    "CollectionAssert",
    "StringAssert",
    "FileAssert",
    "DirectoryAssert",
    "Should",
    "Received",
    "DidNotReceive",
    "Check",
];

/// Name prefixes that read as a check in either language.
const PREFIXES: &[&str] = &[
    "assert",
    "debug_assert",
    "prop_assert",
    "verify",
    "should",
    "ensure",
    "check",
    "validate",
    "require",
    "must_",
    "expect_",
];

/// The outcome of looking for an assertion; ordered by how much it settles.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum Verdict {
    /// Nothing reachable asserts.
    No,
    /// A helper out of sight may assert.
    Unknown,
    /// An assertion is reachable.
    Asserts,
}

/// True when the macro `name` checks something or ends the test on purpose.
pub(super) fn macro_asserts(name: &str) -> bool {
    name_asserts(Lang::Rust, name)
        || matches!(
            name,
            "panic" | "unreachable" | "expect" | "ensure" | "todo" | "unimplemented" | "bail"
        )
}

/// True when a call named `name` reads as an assertion in `lang`.
pub(super) fn name_asserts(lang: Lang, name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    if PREFIXES.iter().any(|p| lower.starts_with(p)) {
        return true;
    }
    match lang {
        Lang::Rust => matches!(name, "unwrap_err" | "expect_err"),
        Lang::Python => name == "expect",
        Lang::Script => matches!(name, "expect" | "expectTypeOf" | "expectAsync" | "fail"),
        Lang::CSharp => false,
    }
}

/// True when `word` reads as test support (`helpers`, `fixtures`, `testing-library`).
pub(super) fn helper_word(word: &str) -> bool {
    let l = word.to_ascii_lowercase();
    HELPER_WORDS.iter().any(|w| l.contains(w))
}

fn helperish(path: &[String]) -> bool {
    path.iter().any(|s| helper_word(s))
}

/// True when the JS call path `e` is an assertion no prefix rule catches.
fn script_special(e: &[String]) -> bool {
    e.iter().any(|s| JS_ASSERT_SEGS.contains(&s.as_str()))
        || (e.len() >= 2 && e[0] == "t" && JS_T_METHODS.contains(&e[e.len() - 1].as_str()))
}

/// True when the C# call path `e` is an assertion no prefix rule catches.
fn cs_special(e: &[String]) -> bool {
    e.iter().any(|s| CS_ASSERT_SEGS.contains(&s.as_str()))
}

fn py_special(e: &[String]) -> bool {
    let Some(last) = e.last().map(String::as_str) else {
        return false;
    };
    let n = e.len();
    (n >= 2
        && e[n - 2] == "pytest"
        && matches!(
            last,
            "raises" | "warns" | "fail" | "deprecated_call" | "skip" | "importorskip"
        ))
        || (n >= 2 && e[0] == "self" && matches!(last, "fail" | "skipTest"))
}

/// Resolves callees against one file's definitions.
pub(super) struct Resolver<'a, 't> {
    cx: &'a Ctx<'t>,
    class_open: bool,
    visited: HashSet<usize>,
}

impl<'a, 't> Resolver<'a, 't> {
    /// A resolver for tests of a class that is (`class_open`) or is not open to unseen mixins.
    pub fn new(cx: &'a Ctx<'t>, class_open: bool) -> Self {
        Self {
            cx,
            class_open,
            visited: HashSet::new(),
        }
    }

    /// The verdict for the function `f`, a test or a helper, at helper depth `depth`.
    pub fn function(&mut self, f: Node<'t>, depth: usize) -> Verdict {
        if depth > MAX_DEPTH {
            return Verdict::Unknown;
        }
        if !self.visited.insert(f.id()) {
            return Verdict::No;
        }
        let Some(body) = f.child_by_field_name("body") else {
            return Verdict::No;
        };
        let b = self.cx.scan_body(body);
        if b.direct {
            return Verdict::Asserts;
        }
        let mut out = Verdict::No;
        for c in &b.calls {
            match self.callee(c, depth) {
                Verdict::Asserts => return Verdict::Asserts,
                Verdict::Unknown => out = Verdict::Unknown,
                Verdict::No => {}
            }
        }
        out
    }

    fn by_name(&mut self, name: &str, depth: usize) -> Option<Verdict> {
        let defs = self.cx.defs.get(name)?.clone();
        let mut out = Verdict::No;
        for d in defs {
            out = out.max(self.function(d, depth + 1));
        }
        Some(out)
    }

    fn imported(&self, path: &[String], relative: bool) -> Verdict {
        let root = path.first().map(String::as_str).unwrap_or_default();
        let stdlib = match self.cx.lang {
            Lang::Rust => matches!(root, "std" | "core" | "alloc"),
            Lang::Python => STDLIB.contains(&root),
            Lang::Script => JS_STDLIB.contains(&root),
            Lang::CSharp => CS_STDLIB.contains(&root),
        };
        if stdlib {
            return Verdict::No;
        }
        let in_bodyless = path.iter().any(|s| self.cx.bodyless_mods.contains(s));
        if relative || helperish(path) || in_bodyless {
            Verdict::Unknown
        } else {
            Verdict::No
        }
    }

    fn callee(&mut self, c: &Callee<'t>, depth: usize) -> Verdict {
        let cx = self.cx;
        let expanded = cx.expand(&c.segs);
        let last = c.segs.last().map(String::as_str).unwrap_or_default();
        let elast = expanded.last().map(String::as_str).unwrap_or_default();
        if name_asserts(cx.lang, last)
            || name_asserts(cx.lang, elast)
            || (cx.lang == Lang::Python && py_special(&expanded))
            || (cx.lang == Lang::Script && script_special(&expanded))
            || (cx.lang == Lang::CSharp && cs_special(&expanded))
        {
            return Verdict::Asserts;
        }
        if c.method {
            return self.by_name(last, depth).unwrap_or(Verdict::No);
        }
        let first = c.segs[0].as_str();
        if c.segs.len() == 1 {
            if let Some(v) = self.by_name(last, depth) {
                return v;
            }
            if let Some(full) = cx.aliases.get(first) {
                return self.imported(full, cx.relative.contains(first));
            }
            if cx.lang == Lang::CSharp && cx.assert_statics {
                return Verdict::Asserts;
            }
            if cx.lang == Lang::CSharp && self.class_open {
                return Verdict::Unknown;
            }
            return if cx.wildcards.iter().any(|(m, rel)| *rel || helperish(m)) {
                Verdict::Unknown
            } else {
                Verdict::No
            };
        }
        if matches!(
            first,
            "Self" | "self" | "this" | "super" | "base" | "crate" | "cls"
        ) {
            if let Some(v) = self.by_name(last, depth) {
                return v;
            }
            let open = matches!(first, "super" | "base" | "crate")
                || (matches!(cx.lang, Lang::Python | Lang::CSharp) && self.class_open);
            return if open { Verdict::Unknown } else { Verdict::No };
        }
        if cx.aliases.contains_key(first) {
            return self.imported(&expanded, cx.relative.contains(first));
        }
        if cx.local_types.contains(first) {
            return self.by_name(last, depth).unwrap_or(Verdict::No);
        }
        if cx.bodyless_mods.contains(first) {
            return Verdict::Unknown;
        }
        if matches!(cx.lang, Lang::Script | Lang::CSharp) {
            if let Some(v) = self.by_name(last, depth) {
                return v;
            }
            if helperish(&c.segs) {
                return Verdict::Unknown;
            }
        }
        Verdict::No
    }
}
