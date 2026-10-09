//! Models across files (grmb-spec 3 and 5): include resolution, cycles, names and scoping.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3
// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82

use std::collections::{BTreeMap, BTreeSet};

use gob_walk::Glob;

use crate::ast::{Entity, EntityKind, FileStatus, Include, Item, ModuleKind, ParsedFile};
use crate::parse::parse_file;
use crate::span::{Diagnostic, Span};

/// A pack as enabled in `grimble.toml` and found under `packs/` (grmb-spec 4.6).
#[derive(Clone, PartialEq, Eq, Debug, Default)]
pub struct PackPin {
    /// The exact version available.
    pub version: String,
    /// The digest of the pack contents, when known.
    pub digest: Option<String>,
    /// The capability atoms the pack contributes.
    pub atoms: BTreeSet<String>,
}

/// Everything the model rules need, supplied by the caller (no I/O happens in this crate).
#[derive(Clone, Debug, Default)]
pub struct ModelFiles {
    /// Repo-relative path to raw bytes of every candidate .grmb file.
    pub files: BTreeMap<String, Vec<u8>>,
    /// The root files; empty means every file that declares `module` unless
    /// [`ModelFiles::declared_roots`] is set.
    pub roots: Vec<String>,
    /// True when `roots` is the declared list (`[grimble] models`): empty then means no model
    /// is declared (MDL021) instead of falling back to every file that declares `module`.
    pub declared_roots: bool,
    /// Every repo-relative path of the walk, for MDL005; `None` skips MDL005.
    pub walk: Option<Vec<String>>,
    /// Enabled packs by pack id (the `ref` of a `pack` entity).
    pub packs: BTreeMap<String, PackPin>,
    /// Why an enabled pack could not be loaded, by pack id (a missing or malformed pack file).
    pub pack_problems: BTreeMap<String, String>,
    /// Rule ids accepted by exception clauses besides the registered ones.
    pub extra_rules: BTreeSet<String>,
}

impl ModelFiles {
    /// An empty input.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds a file.
    #[must_use]
    pub fn with_file(mut self, path: &str, bytes: impl Into<Vec<u8>>) -> Self {
        self.files.insert(path.to_owned(), bytes.into());
        self
    }

    /// Declares a root file.
    #[must_use]
    pub fn with_root(mut self, path: &str) -> Self {
        self.roots.push(path.to_owned());
        self
    }

    /// Makes `roots` authoritative: the declared `[grimble] models` list, possibly empty.
    #[must_use]
    pub fn with_declared_roots(mut self, roots: Vec<String>) -> Self {
        self.roots = roots;
        self.declared_roots = true;
        self
    }

    /// Sets the walk (all repo paths).
    #[must_use]
    pub fn with_walk(mut self, paths: Vec<String>) -> Self {
        self.walk = Some(paths);
        self
    }

    /// Enables a pack.
    #[must_use]
    pub fn with_pack(mut self, id: &str, pin: PackPin) -> Self {
        self.packs.insert(id.to_owned(), pin);
        self
    }

    /// Accepts an extra rule id in exception clauses.
    #[must_use]
    pub fn with_rule(mut self, id: &str) -> Self {
        self.extra_rules.insert(id.to_owned());
        self
    }
}

/// One file of a model with the prefix it is mounted under.
#[derive(Clone, Debug)]
pub struct LoadedFile {
    /// The parsed file.
    pub parsed: ParsedFile,
    /// The mount prefix (`api` or `a.b`; empty at the root).
    pub mount: String,
    /// True for the root file.
    pub is_root: bool,
}

/// A diagnostic belonging to a file of a model.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FileDiag {
    /// Index into [`LoadedRoot::files`].
    pub file: usize,
    /// The diagnostic.
    pub diag: Diagnostic,
}

/// The files reachable from one root through `include`.
#[derive(Clone, Debug)]
pub struct LoadedRoot {
    /// The root path.
    pub root: String,
    /// Files in load (depth-first) order; index 0 is the root.
    pub files: Vec<LoadedFile>,
    /// Include-level diagnostics (MDL001, MDL002, MDL003, MDL000).
    pub diags: Vec<FileDiag>,
}

/// Collects every include with the namespace chain enclosing it.
fn includes<'a>(
    items: &'a [Item],
    ns: &mut Vec<String>,
    out: &mut Vec<(&'a Include, Vec<String>)>,
) {
    for item in items {
        match item {
            Item::Include(i) => out.push((i, ns.clone())),
            Item::Namespace(n) => {
                ns.push(n.name.text.clone());
                includes(&n.items, ns, out);
                ns.pop();
            }
            _ => {}
        }
    }
}

fn has_glob_meta(s: &str) -> bool {
    s.contains(['*', '?', '[', '{'])
}

/// Where an include path points, and whether reaching it climbs out of the including directory.
struct IncludePath {
    /// The normalized repo-relative path or glob pattern.
    path: String,
    /// True when the written path has a `..` segment or resolves above the including directory.
    climbs: bool,
}

/// The directory of a repo-relative file path (empty at the repository root).
fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// True when `path` is at or below directory `dir` (the empty directory is the repository root).
fn is_below(dir: &str, path: &str) -> bool {
    dir.is_empty() || path.strip_prefix(dir).is_some_and(|r| r.starts_with('/'))
}

/// Joins `rel` onto the directory of `from` and normalizes (a leading `/` anchors at the
/// repository root); `Err` when it leaves the repository (MDL002).
fn normalize(from: &str, rel: &str) -> Result<IncludePath, String> {
    if rel.contains('\\') {
        return Err(format!(
            "include path `{rel}` must be a relative POSIX path"
        ));
    }
    let mut parts: Vec<&str> = if rel.starts_with('/') {
        Vec::new()
    } else {
        dir_of(from).split('/').filter(|s| !s.is_empty()).collect()
    };
    let mut dotdot = false;
    for seg in rel.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                dotdot = true;
                if parts.pop().is_none() {
                    return Err(format!("include path `{rel}` leaves the repository"));
                }
            }
            s => parts.push(s),
        }
    }
    let path = parts.join("/");
    let climbs = dotdot || !is_below(dir_of(from), &path);
    Ok(IncludePath { path, climbs })
}

struct Loader<'a> {
    input: &'a ModelFiles,
    out: LoadedRoot,
    index: BTreeMap<String, usize>,
    stack: Vec<String>,
    parsed: BTreeMap<String, ParsedFile>,
}

impl Loader<'_> {
    fn parse(&mut self, path: &str) -> Option<ParsedFile> {
        if let Some(p) = self.parsed.get(path) {
            return Some(p.clone());
        }
        let bytes = self.input.files.get(path)?;
        let p = parse_file(path, bytes);
        self.parsed.insert(path.to_owned(), p.clone());
        Some(p)
    }

    fn diag(&mut self, file: usize, rule: &'static str, span: Span, msg: String) {
        self.out.diags.push(FileDiag {
            file,
            diag: Diagnostic::new(rule, span, msg),
        });
    }

    fn visit(&mut self, path: &str, mount: &str, is_root: bool) -> Option<usize> {
        let parsed = self.parse(path)?;
        let idx = self.out.files.len();
        self.index.insert(path.to_owned(), idx);
        self.out.files.push(LoadedFile {
            parsed: parsed.clone(),
            mount: mount.to_owned(),
            is_root,
        });
        self.stack.push(path.to_owned());
        let mut incs = Vec::new();
        includes(&parsed.items, &mut Vec::new(), &mut incs);
        for (inc, ns) in incs {
            self.include(idx, path, inc, &ns, mount);
        }
        self.stack.pop();
        Some(idx)
    }

    /// The files an include names (MDL002 when none, MDL020 when one climbs without `outside`).
    fn targets(
        &mut self,
        from_idx: usize,
        from: &str,
        inc: &Include,
        pattern: &str,
    ) -> Option<Vec<String>> {
        let targets: Vec<String> = if has_glob_meta(pattern) {
            match Glob::parse(pattern) {
                Ok(g) => self
                    .input
                    .files
                    .keys()
                    .filter(|k| g.matches_path(k))
                    .cloned()
                    .collect(),
                Err(e) => {
                    let msg = format!("include glob: {}", e.message);
                    self.diag(from_idx, "MDL002", inc.path.span, msg);
                    return None;
                }
            }
        } else if self.input.files.contains_key(pattern) {
            vec![pattern.to_owned()]
        } else {
            Vec::new()
        };
        if targets.is_empty() {
            let msg = format!("include `{}` matches no file", inc.path.value);
            self.diag(from_idx, "MDL002", inc.path.span, msg);
            return None;
        }
        if !inc.outside
            && let Some(t) = targets.iter().find(|t| !is_below(dir_of(from), t))
        {
            let msg = format!(
                "{} (it matches `{t}`)",
                climb_message(from, &inc.path.value)
            );
            self.diag(from_idx, "MDL020", inc.path.span, msg);
            return None;
        }
        Some(targets)
    }

    fn include(&mut self, from_idx: usize, from: &str, inc: &Include, ns: &[String], mount: &str) {
        let span = inc.span;
        let (pattern, climbs) = match normalize(from, &inc.path.value) {
            Ok(r) => (r.path, r.climbs),
            Err(msg) => {
                self.diag(from_idx, "MDL002", inc.path.span, msg);
                return;
            }
        };
        if climbs && !inc.outside {
            self.diag(
                from_idx,
                "MDL020",
                inc.path.span,
                climb_message(from, &inc.path.value),
            );
            return;
        }
        let Some(targets) = self.targets(from_idx, from, inc, &pattern) else {
            return;
        };
        if targets.len() > 1
            && let Some(m) = &inc.mount
        {
            self.diag(
                from_idx,
                "MDL000",
                m.span,
                "`as` is not allowed on a glob that matches more than one file".to_owned(),
            );
            return;
        }
        let mut parts: Vec<String> = Vec::new();
        if !mount.is_empty() {
            parts.push(mount.to_owned());
        }
        parts.extend(ns.iter().cloned());
        if let Some(m) = &inc.mount {
            parts.push(m.dotted());
        }
        let child_mount = parts.join(".");
        for t in targets {
            if let Some(pos) = self.stack.iter().position(|s| *s == t) {
                let mut cycle: Vec<&str> = self.stack[pos..].iter().map(String::as_str).collect();
                cycle.push(&t);
                self.diag(
                    from_idx,
                    "MDL003",
                    span,
                    format!(
                        "include cycle {}; the include is skipped",
                        cycle.join(" -> ")
                    ),
                );
                continue;
            }
            if let Some(&other) = self.index.get(&t) {
                if self.out.files[other].mount != child_mount {
                    let first = first_entity(&self.out.files[other].parsed)
                        .map_or_else(|| t.clone(), |e| format!("`{e}`"));
                    self.diag(
                        from_idx,
                        "MDL001",
                        span,
                        format!(
                            "`{t}` is included under two different prefixes (`{}` and `{child_mount}`); {first} is declared twice",
                            self.out.files[other].mount
                        ),
                    );
                }
                continue;
            }
            self.visit(&t, &child_mount, false);
        }
    }
}

/// The MDL020 message for an include that climbs out without the `outside` marker.
fn climb_message(from: &str, written: &str) -> String {
    let dir = dir_of(from);
    let dir = if dir.is_empty() {
        "the repository root"
    } else {
        dir
    };
    format!(
        "include `{written}` leaves the directory of `{from}` ({dir}); an include may only name files at or below it, so write `include \"{written}\" outside;` if climbing out is intended"
    )
}

fn first_entity(f: &ParsedFile) -> Option<String> {
    fn walk(items: &[Item]) -> Option<String> {
        items.iter().find_map(|i| match i {
            Item::Entity(e) if !e.extension => Some(e.name.text.clone()),
            Item::Namespace(n) => walk(&n.items),
            _ => None,
        })
    }
    walk(&f.items)
}

/// The roots in force: the declared list, else (library default) every file declaring `module`.
pub fn root_list(input: &ModelFiles) -> Vec<String> {
    if input.declared_roots || !input.roots.is_empty() {
        return input.roots.clone();
    }
    input
        .files
        .iter()
        .filter(|(p, b)| {
            parse_file(p, b)
                .module
                .is_some_and(|m| m.kind == ModuleKind::Module)
        })
        .map(|(p, _)| p.clone())
        .collect()
}

/// Loads one model per root (see [`root_list`]); only files reachable through `include` load.
pub fn load_roots(input: &ModelFiles) -> Vec<LoadedRoot> {
    let roots = root_list(input);
    roots
        .iter()
        .filter_map(|root| {
            let mut l = Loader {
                input,
                out: LoadedRoot {
                    root: root.clone(),
                    files: Vec::new(),
                    diags: Vec::new(),
                },
                index: BTreeMap::new(),
                stack: Vec::new(),
                parsed: BTreeMap::new(),
            };
            if l.visit(root, "", true).is_none() {
                tracing::warn!(%root, "root file is not among the supplied files");
                return None;
            }
            tracing::info!(%root, files = l.out.files.len(), diags = l.out.diags.len(), "model loaded");
            Some(l.out)
        })
        .collect()
}

/// How a name reaches an entity.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Via {
    /// The declared name.
    Name,
    /// An `alias` (permanent).
    Alias,
    /// A `renamed_from` (transitional, MDL012).
    Renamed,
}

/// A declared entity or extension with its context.
#[derive(Clone, Debug)]
pub struct EntityRec<'a> {
    /// Index of the file in [`LoadedRoot::files`].
    pub file: usize,
    /// The AST.
    pub entity: &'a Entity,
    /// The enclosing prefix parts (mount and namespaces).
    pub ctx: Vec<String>,
    /// The full name; for an extension, the resolved target's full name when known.
    pub full: String,
}

/// A top-level exception with its context.
#[derive(Clone, Debug)]
pub struct TopExcRec<'a> {
    /// Index of the file.
    pub file: usize,
    /// The AST.
    pub exc: &'a crate::ast::TopException,
    /// The enclosing prefix parts.
    pub ctx: Vec<String>,
}

/// One claim on a name: an entity, an alias or a `renamed_from`.
#[derive(Clone, Debug)]
pub struct NameDecl {
    /// Index into [`Index::entities`] of the owning (non-extension) entity.
    pub rec: usize,
    /// How the name reaches it.
    pub via: Via,
    /// Index of the file.
    pub file: usize,
    /// The name's span.
    pub span: Span,
}

/// The result of resolving a reference.
#[derive(Clone, Copy, Debug)]
pub struct Resolved {
    /// Index into [`Index::entities`].
    pub rec: usize,
    /// How the name reached it.
    pub via: Via,
    /// A different entity of the same spelling at an outer level (MDL015).
    pub shadows: Option<usize>,
}

/// The name table of one loaded model.
#[derive(Debug)]
pub struct Index<'a> {
    /// The loaded model.
    pub root: &'a LoadedRoot,
    /// Declared (non-extension) entities in canonical (path, byte) order.
    pub entities: Vec<EntityRec<'a>>,
    /// Extensions in canonical order.
    pub extensions: Vec<EntityRec<'a>>,
    /// Top-level exceptions.
    pub top_exceptions: Vec<TopExcRec<'a>>,
    /// Every name claim, canonical order, grouped by full name.
    pub claims: BTreeMap<String, Vec<NameDecl>>,
    /// True when some file holds a hole or is not read (resolution failures are Unresolved).
    pub degraded: bool,
}

fn walk_items<'a>(
    file: usize,
    items: &'a [Item],
    ctx: &mut Vec<String>,
    decls: &mut Vec<EntityRec<'a>>,
    exts: &mut Vec<EntityRec<'a>>,
    tops: &mut Vec<TopExcRec<'a>>,
) {
    for item in items {
        match item {
            Item::Entity(e) => {
                let full = {
                    let mut p = ctx.clone();
                    p.push(e.target.dotted());
                    p.join(".")
                };
                let rec = EntityRec {
                    file,
                    entity: e,
                    ctx: ctx.clone(),
                    full,
                };
                if e.extension {
                    exts.push(rec);
                } else {
                    decls.push(rec);
                }
            }
            Item::Namespace(n) => {
                ctx.push(n.name.text.clone());
                walk_items(file, &n.items, ctx, decls, exts, tops);
                ctx.pop();
            }
            Item::Exception(t) => tops.push(TopExcRec {
                file,
                exc: t,
                ctx: ctx.clone(),
            }),
            Item::Include(_) | Item::Hole { .. } => {}
        }
    }
}

impl<'a> Index<'a> {
    /// Builds the name table of `root` (reports nothing; MDL001 is a rule over [`Index::claims`]).
    pub fn build(root: &'a LoadedRoot) -> Self {
        let mut order: Vec<usize> = (0..root.files.len()).collect();
        order.sort_by(|&a, &b| root.files[a].parsed.path.cmp(&root.files[b].parsed.path));
        let mut entities = Vec::new();
        let mut extensions = Vec::new();
        let mut top_exceptions = Vec::new();
        for &fi in &order {
            let f = &root.files[fi];
            if f.parsed.status != FileStatus::Parsed {
                continue;
            }
            let mut ctx: Vec<String> = if f.mount.is_empty() {
                Vec::new()
            } else {
                f.mount.split('.').map(str::to_owned).collect()
            };
            walk_items(
                fi,
                &f.parsed.items,
                &mut ctx,
                &mut entities,
                &mut extensions,
                &mut top_exceptions,
            );
        }
        let mut claims: BTreeMap<String, Vec<NameDecl>> = BTreeMap::new();
        for (ri, rec) in entities.iter().enumerate() {
            claims.entry(rec.full.clone()).or_default().push(NameDecl {
                rec: ri,
                via: Via::Name,
                file: rec.file,
                span: rec.entity.name.span,
            });
            for c in &rec.entity.clauses {
                let (name, via) = match &c.kind {
                    crate::ast::ClauseKind::Alias(i) => (i, Via::Alias),
                    crate::ast::ClauseKind::RenamedFrom(i) => (i, Via::Renamed),
                    _ => continue,
                };
                let mut p = rec.ctx.clone();
                p.push(name.text.clone());
                claims.entry(p.join(".")).or_default().push(NameDecl {
                    rec: ri,
                    via,
                    file: rec.file,
                    span: name.span,
                });
            }
        }
        let degraded = root
            .files
            .iter()
            .any(|f| f.parsed.holes > 0 || f.parsed.status != FileStatus::Parsed);
        tracing::debug!(
            root = %root.root,
            entities = entities.len(),
            extensions = extensions.len(),
            names = claims.len(),
            degraded,
            "name table built"
        );
        Self {
            root,
            entities,
            extensions,
            top_exceptions,
            claims,
            degraded,
        }
    }

    /// The path of the file at `idx`.
    pub fn path(&self, idx: usize) -> &str {
        &self.root.files[idx].parsed.path
    }

    fn lookup(&self, full: &str) -> Option<(usize, Via)> {
        self.claims
            .get(full)
            .and_then(|v| v.first())
            .map(|d| (d.rec, d.via))
    }

    /// Resolves `path` from inside prefix `ctx` (grmb-spec 5.3): nearest first, `::` anchors at the root.
    pub fn resolve(&self, ctx: &[String], path: &crate::ast::RefPath) -> Option<Resolved> {
        let dotted = path.dotted();
        let levels: Vec<usize> = if path.rooted {
            vec![0]
        } else {
            (0..=ctx.len()).rev().collect()
        };
        let mut first: Option<(usize, Via)> = None;
        let mut shadows = None;
        for k in levels {
            let full = if k == 0 {
                dotted.clone()
            } else {
                format!("{}.{dotted}", ctx[..k].join("."))
            };
            if let Some((rec, via)) = self.lookup(&full) {
                match first {
                    None => first = Some((rec, via)),
                    Some((r0, _)) if r0 != rec && shadows.is_none() => shadows = Some(rec),
                    Some(_) => {}
                }
            }
        }
        first.map(|(rec, via)| Resolved { rec, via, shadows })
    }

    /// The entity kind of record `rec`.
    pub fn kind(&self, rec: usize) -> EntityKind {
        self.entities[rec].entity.kind
    }
}
