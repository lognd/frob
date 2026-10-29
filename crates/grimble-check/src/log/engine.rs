//! The shared symbolic engine behind LOG001/LOG002: scope frames of import and alias bindings,
//! the cross-file export table, and hit recording that the per-language scanners drive.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

use std::collections::BTreeMap;

use tree_sitter::Node;

use super::catalogue::{Args, Group};

/// A resolved symbol path as dotted segments (`["sys", "stdout"]`).
pub type SymPath = Vec<String>;

/// What a name is bound to in a scope frame.
#[derive(Debug, Clone)]
pub enum Binding {
    /// The name stands for this canonical symbol path (import, alias, re-export).
    Alias(SymPath),
    /// The name is a local value (parameter, definition, call result): it shadows any symbol.
    Opaque,
}

/// One reported hit: the catalogue atom that matched and where.
#[derive(Debug, Clone)]
pub struct Hit {
    /// Index into [`Group::atoms`].
    pub atom: usize,
    /// Byte range start.
    pub start: usize,
    /// Byte range end.
    pub end: usize,
    /// The resolved symbol path, dotted.
    pub path: String,
}

/// A dynamic form the resolver cannot place (`getattr(sys, name)`).
#[derive(Debug, Clone)]
pub struct Unres {
    /// Byte range start.
    pub start: usize,
    /// Byte range end.
    pub end: usize,
    /// What could not be resolved.
    pub what: String,
}

/// The project-wide module exports used to follow re-exports across files.
#[derive(Debug, Clone, Default)]
pub struct Project {
    /// Module key (every dotted suffix of the file's module path) to exported name to canonical path.
    pub modules: BTreeMap<String, BTreeMap<String, SymPath>>,
    /// Canonical paths of project-wide imports (`global using static System.Console`).
    pub globals: Vec<SymPath>,
}

impl Project {
    /// Rewrite `path` through a project module's export when its module prefix names one.
    #[must_use]
    pub fn link(&self, path: SymPath) -> SymPath {
        for i in (1..path.len()).rev() {
            let key = path[..i].join(".");
            if let Some(target) = self.modules.get(&key).and_then(|m| m.get(&path[i])) {
                let mut out = target.clone();
                out.extend_from_slice(&path[i + 1..]);
                return out;
            }
        }
        path
    }

    /// Register `exports` under every dotted suffix of `module_key`.
    pub fn register(&mut self, module_key: &str, exports: &BTreeMap<String, SymPath>) {
        let parts: Vec<&str> = module_key.split('.').collect();
        for i in 0..parts.len() {
            let key = parts[i..].join(".");
            self.modules.insert(key, exports.clone());
        }
    }
}

/// Per-file inputs the scanners need beyond the tree.
pub struct FileCtx<'a> {
    /// The repo-relative file path.
    pub path: &'a str,
    /// The cross-file export table of the previous round.
    pub project: &'a Project,
    /// Logging-crate roots (`tracing`, `logging`, ...) as symbol paths.
    pub roots: &'a [SymPath],
}

/// What one file scan produced.
#[derive(Debug, Default)]
pub struct FileScan {
    /// Reported direct-output hits in source order.
    pub hits: Vec<Hit>,
    /// Dynamic forms that could not be resolved.
    pub unresolved: Vec<Unres>,
    /// True when the file resolves a path rooted at a logging crate.
    pub logging_seen: bool,
    /// Module-level alias bindings, for re-export linking.
    pub exports: BTreeMap<String, SymPath>,
}

/// The mutable walk state shared by the language scanners.
pub struct State<'a> {
    /// The atoms of the file's language group.
    pub group: &'a Group,
    /// Per-file inputs.
    pub ctx: &'a FileCtx<'a>,
    /// The file text.
    pub src: &'a str,
    /// Scope frames, outermost first.
    pub frames: Vec<BTreeMap<String, Binding>>,
    /// Glob-import prefixes (`from sys import *`, `using System;`).
    pub globs: Vec<SymPath>,
    /// Recorded hits.
    pub hits: Vec<Hit>,
    /// Recorded unresolved dynamic forms.
    pub unresolved: Vec<Unres>,
    /// Whether a logging-crate path was seen.
    pub logging_seen: bool,
    /// True while visiting the arguments of a hit call: bare path references there are not hits.
    pub suppress: bool,
    /// True while visiting the callee chain of a hit call: chained calls are not separate hits.
    pub in_chain: bool,
}

impl<'a> State<'a> {
    /// A fresh state with one (module) frame.
    #[must_use]
    pub fn new(group: &'a Group, ctx: &'a FileCtx<'a>, src: &'a str) -> Self {
        Self {
            group,
            ctx,
            src,
            frames: vec![BTreeMap::new()],
            globs: Vec::new(),
            hits: Vec::new(),
            unresolved: Vec::new(),
            logging_seen: false,
            suppress: false,
            in_chain: false,
        }
    }

    /// The source text of `n`.
    #[must_use]
    pub fn txt(&self, n: Node<'_>) -> &'a str {
        &self.src[n.byte_range()]
    }

    /// Open a scope frame.
    pub fn push(&mut self) {
        self.frames.push(BTreeMap::new());
    }

    /// Close the innermost scope frame.
    pub fn pop(&mut self) {
        if self.frames.len() > 1 {
            self.frames.pop();
        }
    }

    /// Bind `name` in the innermost frame; a logging-rooted alias marks logging as seen.
    pub fn bind(&mut self, name: &str, b: Binding) {
        if let Binding::Alias(p) = &b {
            self.note(p);
        }
        if let Some(f) = self.frames.last_mut() {
            f.insert(name.to_owned(), b);
        }
    }

    /// The nearest binding of `name`.
    #[must_use]
    pub fn lookup(&self, name: &str) -> Option<&Binding> {
        self.frames.iter().rev().find_map(|f| f.get(name))
    }

    /// Note `path`: if it is rooted at a logging crate the file shows logging configured.
    pub fn note(&mut self, path: &[String]) {
        if self
            .ctx
            .roots
            .iter()
            .any(|r| path.len() >= r.len() && path[..r.len()] == r[..])
        {
            self.logging_seen = true;
        }
    }

    /// Record a call hit for `path` when a reportable atom accepts `args`; true when recorded.
    pub fn hit_call(&mut self, node: Node<'_>, path: &[String], args: &Args) -> bool {
        self.note(path);
        if self.in_chain {
            return false;
        }
        let Some(atom) = self.group.first_match(path, args) else {
            return false;
        };
        self.record(node, atom, path);
        true
    }

    /// Record a bare reference hit (`map(print, xs)`, `sys.stdout`); true when recorded.
    pub fn hit_ref(&mut self, node: Node<'_>, path: &[String]) -> bool {
        self.note(path);
        if self.suppress || self.in_chain {
            return false;
        }
        let Some(atom) = self.group.first_ref(path) else {
            return false;
        };
        self.record(node, atom, path);
        true
    }

    fn record(&mut self, node: Node<'_>, atom: usize, path: &[String]) {
        tracing::debug!(atom = %self.group.atoms[atom].id, path = %path.join("."), file = %self.ctx.path, "output hit");
        self.hits.push(Hit {
            atom,
            start: node.start_byte(),
            end: node.end_byte(),
            path: path.join("."),
        });
    }

    /// Record an unresolved dynamic form.
    pub fn unres(&mut self, node: Node<'_>, what: &str) {
        self.unresolved.push(Unres {
            start: node.start_byte(),
            end: node.end_byte(),
            what: what.to_owned(),
        });
    }

    /// Finish: the module frame's aliases become the file's exports.
    #[must_use]
    pub fn finish(self) -> FileScan {
        let exports = self
            .frames
            .first()
            .map(|f| {
                f.iter()
                    .filter_map(|(k, v)| match v {
                        Binding::Alias(p) => Some((k.clone(), p.clone())),
                        Binding::Opaque => None,
                    })
                    .collect()
            })
            .unwrap_or_default();
        FileScan {
            hits: self.hits,
            unresolved: self.unresolved,
            logging_seen: self.logging_seen,
            exports,
        }
    }
}

/// Named children of `n`, collected (cursor borrow-free iteration).
#[must_use]
pub fn kids(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.named_children(&mut c).collect()
}

/// All children of `n` including anonymous tokens.
#[must_use]
pub fn all_kids(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.children(&mut c).collect()
}

/// The default logging-crate roots per language group, plus configured extras (`a.b` or `a::b`).
#[must_use]
pub fn logging_roots(group: &str, extra: &[String]) -> Vec<SymPath> {
    let base: &[&str] = match group {
        "rust" => &[
            "tracing",
            "log",
            "slog",
            "tracing_subscriber",
            "tracing_appender",
        ],
        "python" => &["logging", "structlog", "loguru"],
        "javascript" => &["pino", "winston", "bunyan", "log4js", "loglevel", "consola"],
        "csharp" => &["Microsoft.Extensions.Logging", "Serilog", "NLog", "log4net"],
        _ => &[],
    };
    base.iter()
        .map(|s| (*s).to_owned())
        .chain(extra.iter().cloned())
        .map(|s| {
            s.replace("::", ".")
                .split('.')
                .map(str::to_owned)
                .collect::<Vec<_>>()
        })
        .collect()
}
