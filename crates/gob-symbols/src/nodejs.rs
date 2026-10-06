//! Node project model: `package.json` packages, workspaces and `tsconfig.json` path aliases.
//!
//! Each `package.json` is one package (the TypeScript counterpart of a Cargo crate, language-engines.md
//! section 2 `project_model`); a source file belongs to the nearest enclosing package. A package's
//! `workspaces` (or a `pnpm-workspace.yaml`) name its member packages, a dependency on a member is a
//! package edge, and a `tsconfig.json` (or `jsconfig.json`) contributes `baseUrl` and `paths` aliases to
//! the files it covers (`extends` chains followed, `references` consulted one level for solution-style
//! configs).
//!
//! Resolving a bare specifier yields [`JsResolution`]: candidate repository paths in the order they are
//! tried (the caller probes extensions and `index` files against the walked file set) and whether the
//! specifier is a declared or installed dependency or a Node builtin, which is external. A specifier that
//! is neither stays unresolved (Unknown, never dropped).
//!
//! Approximations (never silent): `exports` conditions are tried in a fixed order (`types`, `import`,
//! `module`, `node`, `browser`, `default`, `require`) instead of object order; a workspace package whose
//! entry points into a build directory (`dist`, `build`, `lib`, `out`) is also tried under `src`; a
//! `tsconfig.*.json` other than `tsconfig.json` is only reached through `references` or `extends`.

// frob:ticket 01M47QKTN549397AFFSC3DEAQX

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use serde_json::{Map, Value};

use crate::crates::join_rel;
use crate::dotnet::{glob_match, seg_match};

/// Config file names tried in a directory, in order.
const CONFIG_NAMES: [&str; 2] = ["tsconfig.json", "jsconfig.json"];

/// `exports` conditions tried, most specific first.
const CONDITIONS: [&str; 7] = [
    "types", "import", "module", "node", "browser", "default", "require",
];

/// Build output directories a workspace package entry may point into; the same path under `src` is also tried.
const OUTPUT_DIRS: [&str; 4] = ["dist", "build", "lib", "out"];

/// Deepest `extends` chain and `references` nesting followed.
const MAX_CONFIG_DEPTH: usize = 8;

/// Deepest directory recursion of a `**` workspace pattern.
const MAX_GLOB_DEPTH: usize = 6;

/// Node core modules, which are external without being installed.
const BUILTINS: [&str; 46] = [
    "assert",
    "async_hooks",
    "buffer",
    "child_process",
    "cluster",
    "console",
    "constants",
    "crypto",
    "dgram",
    "diagnostics_channel",
    "dns",
    "domain",
    "events",
    "fs",
    "http",
    "http2",
    "https",
    "inspector",
    "module",
    "net",
    "os",
    "path",
    "perf_hooks",
    "process",
    "punycode",
    "querystring",
    "readline",
    "repl",
    "stream",
    "string_decoder",
    "sys",
    "test",
    "timers",
    "tls",
    "trace_events",
    "tty",
    "url",
    "util",
    "v8",
    "vm",
    "wasi",
    "worker_threads",
    "zlib",
    "sea",
    "sqlite",
    "bun",
];

/// Why a `package.json` or tsconfig could not be modelled.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum NodeError {
    /// The file could not be read.
    #[error("cannot read {path}: {reason}")]
    Io {
        /// Repo-relative path.
        path: String,
        /// The operating system error text.
        reason: String,
    },
    /// The text is not JSON.
    #[error("malformed JSON in {path}: {reason}")]
    Json {
        /// Repo-relative path.
        path: String,
        /// The parser's message.
        reason: String,
    },
    /// The JSON root is not an object.
    #[error("{path} is not a JSON object")]
    NotObject {
        /// Repo-relative path.
        path: String,
    },
}

/// A parsed `package.json`: one package.
#[derive(Debug, Clone, PartialEq)]
pub struct Package {
    /// Repo-relative path of the `package.json` (the package id).
    pub path: String,
    /// Repo-relative directory (empty at the root).
    pub dir: String,
    /// The `name`, when set.
    pub name: Option<String>,
    /// Entry fields in the order tried: `types`, `typings`, `module`, `main`.
    pub entries: Vec<String>,
    /// The `exports` map, when set.
    pub exports: Option<Value>,
    /// The `imports` map (`#` specifiers), when set.
    pub imports: Option<Value>,
    /// Workspace member patterns (`workspaces` array or `workspaces.packages`), negations kept with `!`.
    pub workspaces: Vec<String>,
    /// Every dependency name of every dependency table.
    pub dependencies: BTreeSet<String>,
}

/// One `paths` entry: a pattern and its target patterns, repo-relative.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathAlias {
    /// The specifier pattern, at most one `*`.
    pub pattern: String,
    /// Target patterns (repo-relative, `*` kept).
    pub targets: Vec<String>,
}

/// The effective `tsconfig.json`, `extends` merged.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TsConfig {
    /// Repo-relative path of the config file.
    pub path: String,
    /// Repo-relative directory of the config file.
    pub dir: String,
    /// `compilerOptions.baseUrl`, repo-relative.
    pub base_url: Option<String>,
    /// `compilerOptions.paths`, targets resolved against `baseUrl` (or the defining config).
    pub aliases: Vec<PathAlias>,
    /// `include` patterns, repo-relative.
    pub include: Option<Vec<String>>,
    /// `files`, repo-relative.
    pub files: Option<Vec<String>>,
    /// `exclude` patterns, repo-relative.
    pub exclude: Option<Vec<String>>,
    /// `references`, as repo-relative config file paths.
    pub references: Vec<String>,
    /// True when an `extends` could not be followed (the aliases may be incomplete).
    pub incomplete: bool,
}

impl TsConfig {
    /// True when this config's `files`/`include`/`exclude` cover repo-relative `file`.
    pub fn covers(&self, file: &str) -> bool {
        if self
            .files
            .as_ref()
            .is_some_and(|f| f.iter().any(|p| p == file))
        {
            return true;
        }
        let include: Vec<String> = match (&self.include, &self.files) {
            (Some(i), _) => i.clone(),
            (None, Some(_)) => Vec::new(),
            (None, None) => vec![join_rel(&self.dir, "**/*")],
        };
        let hit = |pats: &[String]| {
            pats.iter().any(|p| {
                glob_match(p, file) || (!p.is_empty() && glob_match(&format!("{p}/**"), file))
            })
        };
        let excluded = file.split('/').any(|s| s == "node_modules")
            || self.exclude.as_deref().is_some_and(hit);
        hit(&include) && !excluded
    }
}

/// What a bare specifier resolves to.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct JsResolution {
    /// Repo-relative paths to probe (exact, extension-mapped, then `index`), in order.
    pub candidates: Vec<String>,
    /// True when the specifier is a dependency, an installed package or a Node builtin.
    pub external: bool,
}

/// Removes `//` and `/* */` comments and trailing commas from tsconfig-style JSON.
fn strip_jsonc(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    let mut in_str = false;
    while i < chars.len() {
        let c = chars[i];
        if in_str {
            out.push(c);
            if c == '\\' && i + 1 < chars.len() {
                out.push(chars[i + 1]);
                i += 1;
            } else if c == '"' {
                in_str = false;
            }
        } else if c == '"' {
            in_str = true;
            out.push(c);
        } else if c == '/' && chars.get(i + 1) == Some(&'/') {
            while i < chars.len() && chars[i] != '\n' {
                i += 1;
            }
            continue;
        } else if c == '/' && chars.get(i + 1) == Some(&'*') {
            i += 2;
            while i + 1 < chars.len() && !(chars[i] == '*' && chars[i + 1] == '/') {
                i += 1;
            }
            i += 2;
            continue;
        } else if c == ',' {
            let next = chars[i + 1..].iter().find(|n| !n.is_whitespace());
            if !matches!(next, Some('}' | ']')) {
                out.push(c);
            }
        } else {
            out.push(c);
        }
        i += 1;
    }
    out
}

fn parse_object(path: &str, text: &str, jsonc: bool) -> Result<Map<String, Value>, NodeError> {
    let cleaned;
    let src = if jsonc {
        cleaned = strip_jsonc(text);
        cleaned.as_str()
    } else {
        text
    };
    match serde_json::from_str::<Value>(src) {
        Ok(Value::Object(m)) => Ok(m),
        Ok(_) => Err(NodeError::NotObject {
            path: path.to_owned(),
        }),
        Err(e) => Err(NodeError::Json {
            path: path.to_owned(),
            reason: e.to_string(),
        }),
    }
}

fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

fn parent_dir(dir: &str) -> Option<String> {
    (!dir.is_empty()).then(|| dir.rsplit_once('/').map_or("", |(u, _)| u).to_owned())
}

fn string_list(v: Option<&Value>) -> Option<Vec<String>> {
    v.and_then(Value::as_array).map(|a| {
        a.iter()
            .filter_map(Value::as_str)
            .map(str::to_owned)
            .collect()
    })
}

/// `path` with `.json` appended unless it already has that extension.
fn with_json(path: String) -> String {
    if is_json(&path) {
        path
    } else {
        format!("{path}.json")
    }
}

/// True when `path` has the extension `json`, ignoring case.
fn is_json(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("json"))
}

/// Parses `package.json` text at repo-relative `path`.
///
/// # Errors
///
/// [`NodeError`] when the text is not a JSON object.
pub fn parse_package(path: &str, text: &str) -> Result<Package, NodeError> {
    let m = parse_object(path, text, false)?;
    let field = |k: &str| m.get(k).and_then(Value::as_str).map(str::to_owned);
    let workspaces = match m.get("workspaces") {
        Some(Value::Array(_)) => string_list(m.get("workspaces")),
        Some(Value::Object(o)) => string_list(o.get("packages")),
        _ => None,
    }
    .unwrap_or_default();
    let mut dependencies = BTreeSet::new();
    for table in [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ] {
        if let Some(Value::Object(o)) = m.get(table) {
            dependencies.extend(o.keys().cloned());
        }
    }
    Ok(Package {
        path: path.to_owned(),
        dir: dir_of(path).to_owned(),
        name: field("name"),
        entries: ["types", "typings", "module", "main"]
            .iter()
            .filter_map(|k| field(k))
            .collect(),
        exports: m.get("exports").cloned(),
        imports: m.get("imports").cloned(),
        workspaces,
        dependencies,
    })
}

/// One config file before `extends` is merged.
struct RawConfig {
    extends: Vec<String>,
    base_url: Option<String>,
    paths: Option<Vec<(String, Vec<String>)>>,
    include: Option<Vec<String>>,
    files: Option<Vec<String>>,
    exclude: Option<Vec<String>>,
    references: Vec<String>,
}

fn parse_raw_config(path: &str, text: &str) -> Result<RawConfig, NodeError> {
    let m = parse_object(path, text, true)?;
    let dir = dir_of(path);
    let rel = |v: Vec<String>| -> Vec<String> { v.iter().map(|p| join_rel(dir, p)).collect() };
    let opts = m.get("compilerOptions").and_then(Value::as_object);
    let extends = match m.get("extends") {
        Some(Value::String(s)) => vec![s.clone()],
        v => string_list(v).unwrap_or_default(),
    };
    let paths = opts
        .and_then(|o| o.get("paths"))
        .and_then(Value::as_object)
        .map(|p| {
            p.iter()
                .map(|(k, v)| (k.clone(), string_list(Some(v)).unwrap_or_default()))
                .collect()
        });
    let references = m
        .get("references")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|r| r.get("path").and_then(Value::as_str))
        .map(|p| {
            let full = join_rel(dir, p);
            if is_json(&full) {
                full
            } else {
                join_rel(&full, "tsconfig.json")
            }
        })
        .collect();
    Ok(RawConfig {
        extends,
        base_url: opts
            .and_then(|o| o.get("baseUrl"))
            .and_then(Value::as_str)
            .map(|b| join_rel(dir, b)),
        paths,
        include: string_list(m.get("include")).map(rel),
        files: string_list(m.get("files")).map(rel),
        exclude: string_list(m.get("exclude")).map(rel),
        references,
    })
}

/// Picks the entry of `map` that `key` selects: an exact key, else the longest `*` pattern; with the `*` match.
fn lookup_map<'a>(map: &'a Map<String, Value>, key: &str) -> Option<(&'a Value, Option<String>)> {
    if let Some(v) = map.get(key) {
        return Some((v, None));
    }
    map.iter()
        .filter_map(|(pat, v)| {
            let (pre, post) = pat.split_once('*')?;
            let mid = key.strip_prefix(pre)?.strip_suffix(post)?;
            (key.len() >= pre.len() + post.len()).then(|| (pre.len(), v, mid.to_owned()))
        })
        .max_by_key(|(n, _, _)| *n)
        .map(|(_, v, mid)| (v, Some(mid)))
}

/// The `./` targets a `package.json` `exports` or `imports` value names, with `star` substituted.
fn targets_of(v: &Value, star: Option<&str>) -> Vec<String> {
    match v {
        Value::String(s) => vec![star.map_or_else(|| s.clone(), |m| s.replace('*', m))],
        Value::Array(a) => a
            .iter()
            .map(|x| targets_of(x, star))
            .find(|t| !t.is_empty())
            .unwrap_or_default(),
        Value::Object(o) => CONDITIONS
            .iter()
            .filter_map(|c| o.get(*c))
            .map(|x| targets_of(x, star))
            .find(|t| !t.is_empty())
            .unwrap_or_default(),
        _ => Vec::new(),
    }
}

/// The targets of `exports` for `subpath` (`.` or `./x`); `None` when the map does not export it.
fn export_targets(exports: &Value, subpath: &str) -> Option<Vec<String>> {
    match exports {
        Value::Object(o) if o.keys().any(|k| k.starts_with('.')) => {
            lookup_map(o, subpath).map(|(v, star)| targets_of(v, star.as_deref()))
        }
        other => (subpath == ".").then(|| targets_of(other, None)),
    }
}

/// `path` (package-relative) also under `src` when it starts in a build directory.
fn source_twin(dir: &str, rel: &str) -> Option<String> {
    let rel = rel.strip_prefix("./").unwrap_or(rel);
    let (head, tail) = rel.split_once('/')?;
    OUTPUT_DIRS
        .contains(&head)
        .then(|| join_rel(dir, &format!("src/{tail}")))
}

/// The package name of a bare specifier (`@s/n` for scoped, else the first segment) and the rest.
fn split_package(spec: &str) -> (&str, &str) {
    let end = if spec.starts_with('@') {
        spec.match_indices('/')
            .nth(1)
            .map_or(spec.len(), |(i, _)| i)
    } else {
        spec.find('/').unwrap_or(spec.len())
    };
    (&spec[..end], spec[end..].trim_start_matches('/'))
}

fn is_builtin(spec: &str) -> bool {
    if spec.starts_with("node:") {
        return true;
    }
    BUILTINS.contains(&split_package(spec).0)
}

/// Patterns of a `pnpm-workspace.yaml` `packages:` list.
fn pnpm_patterns(text: &str) -> Vec<String> {
    let mut in_packages = false;
    let mut out = Vec::new();
    for raw in text.lines() {
        let line = raw.split('#').next().unwrap_or("").trim_end();
        if line.trim().is_empty() {
            continue;
        }
        if !line.starts_with([' ', '\t', '-']) {
            in_packages = line.trim_end() == "packages:";
        } else if in_packages && let Some(item) = line.trim().strip_prefix('-') {
            out.push(item.trim().trim_matches(['"', '\'']).to_owned());
        }
    }
    out
}

/// Lazily loaded packages, configs and workspaces of one work tree.
#[derive(Debug)]
pub struct NodeProjects {
    root: PathBuf,
    files: HashMap<String, bool>,
    packages: HashMap<String, Result<Arc<Package>, String>>,
    owners: HashMap<String, Option<String>>,
    configs: HashMap<String, Result<Arc<TsConfig>, String>>,
    governing: HashMap<String, Option<Arc<TsConfig>>>,
    workspace_roots: HashMap<String, Option<String>>,
    members: HashMap<String, BTreeMap<String, String>>,
}

impl NodeProjects {
    /// An empty project set for the work tree `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            files: HashMap::new(),
            packages: HashMap::new(),
            owners: HashMap::new(),
            configs: HashMap::new(),
            governing: HashMap::new(),
            workspace_roots: HashMap::new(),
            members: HashMap::new(),
        }
    }

    fn is_file(&mut self, rel: &str) -> bool {
        if let Some(&b) = self.files.get(rel) {
            return b;
        }
        let b = self.root.join(rel).is_file();
        self.files.insert(rel.to_owned(), b);
        b
    }

    fn is_dir(&self, rel: &str) -> bool {
        self.root.join(rel).is_dir()
    }

    /// The package at repo-relative `path`, parsed once; the error text when it is malformed.
    pub fn load_package(&mut self, path: &str) -> &Result<Arc<Package>, String> {
        if !self.packages.contains_key(path) {
            let parsed = std::fs::read_to_string(self.root.join(path))
                .map_err(|e| NodeError::Io {
                    path: path.to_owned(),
                    reason: e.to_string(),
                })
                .and_then(|t| parse_package(path, &t))
                .map(Arc::new)
                .map_err(|e| e.to_string());
            match &parsed {
                Ok(_) => tracing::debug!(path, "package loaded"),
                Err(reason) => tracing::warn!(path, reason, "malformed package.json; Unresolved"),
            }
            self.packages.insert(path.to_owned(), parsed);
        }
        &self.packages[path]
    }

    fn package(&mut self, path: &str) -> Option<Arc<Package>> {
        self.load_package(path).as_ref().ok().cloned()
    }

    /// The package owning repo-relative `file`: the nearest enclosing `package.json`.
    pub fn owner(&mut self, file: &str) -> Option<String> {
        let start = dir_of(file).to_owned();
        if let Some(hit) = self.owners.get(&start) {
            return hit.clone();
        }
        let mut cur = start.clone();
        let found = loop {
            let cand = join_rel(&cur, "package.json");
            if self.is_file(&cand) {
                break Some(cand);
            }
            match parent_dir(&cur) {
                Some(p) => cur = p,
                None => break None,
            }
        };
        self.owners.insert(start, found.clone());
        found
    }

    /// The nearest workspace root directory at or above package directory `dir`.
    fn workspace_root(&mut self, dir: &str) -> Option<String> {
        if let Some(hit) = self.workspace_roots.get(dir) {
            return hit.clone();
        }
        let mut cur = dir.to_owned();
        let found = loop {
            let pkg = join_rel(&cur, "package.json");
            let has_workspaces =
                self.is_file(&pkg) && self.package(&pkg).is_some_and(|p| !p.workspaces.is_empty());
            if has_workspaces || self.is_file(&join_rel(&cur, "pnpm-workspace.yaml")) {
                break Some(cur.clone());
            }
            match parent_dir(&cur) {
                Some(p) => cur = p,
                None => break None,
            }
        };
        self.workspace_roots.insert(dir.to_owned(), found.clone());
        found
    }

    fn expand(&self, base: &str, segs: &[&str], depth: usize, out: &mut Vec<String>) {
        let Some((seg, rest)) = segs.split_first() else {
            out.push(base.to_owned());
            return;
        };
        let subdirs = || -> Vec<String> {
            let mut v: Vec<String> = std::fs::read_dir(self.root.join(base))
                .into_iter()
                .flatten()
                .flatten()
                .filter(|e| e.path().is_dir())
                .filter_map(|e| e.file_name().into_string().ok())
                .filter(|n| n != "node_modules" && !n.starts_with('.'))
                .collect();
            v.sort();
            v
        };
        if *seg == "**" {
            self.expand(base, rest, depth, out);
            if depth < MAX_GLOB_DEPTH {
                for d in subdirs() {
                    self.expand(&join_rel(base, &d), segs, depth + 1, out);
                }
            }
        } else if seg.contains(['*', '?']) {
            let pat: Vec<char> = seg.chars().collect();
            for d in subdirs() {
                let name: Vec<char> = d.chars().collect();
                if seg_match(&pat, &name) {
                    self.expand(&join_rel(base, &d), rest, depth, out);
                }
            }
        } else {
            self.expand(&join_rel(base, seg), rest, depth, out);
        }
    }

    /// Workspace members visible from package directory `dir`: package name to `package.json` path.
    pub fn workspace_members(&mut self, dir: &str) -> BTreeMap<String, String> {
        let Some(root) = self.workspace_root(dir) else {
            return BTreeMap::new();
        };
        if let Some(hit) = self.members.get(&root) {
            return hit.clone();
        }
        let mut patterns = self
            .package(&join_rel(&root, "package.json"))
            .map(|p| p.workspaces.clone())
            .unwrap_or_default();
        if let Ok(text) = std::fs::read_to_string(self.root.join(&root).join("pnpm-workspace.yaml"))
        {
            patterns.extend(pnpm_patterns(&text));
        }
        let (negated, positive): (Vec<String>, Vec<String>) =
            patterns.into_iter().partition(|p| p.starts_with('!'));
        let mut dirs: Vec<String> = Vec::new();
        for p in &positive {
            let segs: Vec<&str> = p
                .trim_start_matches("./")
                .trim_end_matches('/')
                .split('/')
                .filter(|s| !s.is_empty())
                .collect();
            self.expand(&root, &segs, 0, &mut dirs);
        }
        dirs.push(root.clone());
        dirs.sort();
        dirs.dedup();
        let mut map = BTreeMap::new();
        for d in dirs {
            let rel = d.strip_prefix(&root).unwrap_or(&d).trim_start_matches('/');
            if negated
                .iter()
                .any(|n| glob_match(n.trim_start_matches('!').trim_start_matches("./"), rel))
            {
                continue;
            }
            let pkg = join_rel(&d, "package.json");
            if !self.is_file(&pkg) {
                continue;
            }
            if let Some(name) = self.package(&pkg).and_then(|p| p.name.clone()) {
                map.entry(name).or_insert(pkg);
            }
        }
        tracing::debug!(root, members = map.len(), "workspace members found");
        self.members.insert(root, map.clone());
        map
    }

    /// The workspace members package `pkg` depends on: (name, member `package.json` path).
    pub fn workspace_deps(&mut self, pkg: &str) -> Vec<(String, String)> {
        let Some(p) = self.package(pkg) else {
            return Vec::new();
        };
        let members = self.workspace_members(&p.dir);
        p.dependencies
            .iter()
            .filter_map(|d| members.get(d).map(|path| (d.clone(), path.clone())))
            .filter(|(_, path)| path != pkg)
            .collect()
    }

    /// The package name of `pkg`, or its directory name when it has none or is malformed.
    pub fn package_name(&mut self, pkg: &str) -> String {
        self.package(pkg)
            .and_then(|p| p.name.clone())
            .unwrap_or_else(|| dir_of(pkg).rsplit('/').next().unwrap_or("").to_owned())
    }

    /// True when package `pkg` is malformed or unreadable (its reach cannot be ruled out).
    pub fn is_unresolved(&mut self, pkg: &str) -> bool {
        self.package(pkg).is_none()
    }

    fn extends_target(&mut self, dir: &str, spec: &str) -> Option<String> {
        if spec.starts_with("./") || spec.starts_with("../") {
            return Some(with_json(join_rel(dir, spec)));
        }
        let (name, sub) = split_package(spec);
        let sub = if sub.is_empty() { "tsconfig.json" } else { sub };
        let members = self.workspace_members(dir);
        let mut homes: Vec<String> = Vec::new();
        if let Some(pkg) = members.get(name) {
            homes.push(dir_of(pkg).to_owned());
        }
        let mut cur = dir.to_owned();
        loop {
            homes.push(join_rel(&cur, &format!("node_modules/{name}")));
            match parent_dir(&cur) {
                Some(p) => cur = p,
                None => break,
            }
        }
        homes
            .into_iter()
            .map(|h| with_json(join_rel(&h, sub)))
            .find(|c| self.is_file(c))
    }

    fn load_config(&mut self, path: &str, depth: usize) -> Result<Arc<TsConfig>, String> {
        if let Some(hit) = self.configs.get(path) {
            return hit.clone();
        }
        let res = self.build_config(path, depth);
        match &res {
            Ok(_) => tracing::debug!(path, "tsconfig loaded"),
            Err(reason) => tracing::warn!(path, reason, "malformed tsconfig; aliases unknown"),
        }
        self.configs.insert(path.to_owned(), res.clone());
        res
    }

    fn build_config(&mut self, path: &str, depth: usize) -> Result<Arc<TsConfig>, String> {
        let dir = dir_of(path).to_owned();
        let text = std::fs::read_to_string(self.root.join(path)).map_err(|e| {
            NodeError::Io {
                path: path.to_owned(),
                reason: e.to_string(),
            }
            .to_string()
        })?;
        let raw = parse_raw_config(path, &text).map_err(|e| e.to_string())?;
        let mut cfg = TsConfig {
            path: path.to_owned(),
            dir: dir.clone(),
            base_url: None,
            aliases: Vec::new(),
            include: None,
            files: None,
            exclude: None,
            references: Vec::new(),
            incomplete: false,
        };
        let mut inherited: Vec<PathAlias> = Vec::new();
        for spec in &raw.extends {
            let target = self.extends_target(&dir, spec);
            let base = match target {
                Some(t) if depth < MAX_CONFIG_DEPTH && t != path => self.load_config(&t, depth + 1),
                _ => Err(format!("extends {spec} not found")),
            };
            match base {
                Ok(b) => {
                    cfg.base_url = b.base_url.clone().or(cfg.base_url);
                    cfg.include = b.include.clone().or(cfg.include);
                    cfg.files = b.files.clone().or(cfg.files);
                    cfg.exclude = b.exclude.clone().or(cfg.exclude);
                    cfg.incomplete |= b.incomplete;
                    if !b.aliases.is_empty() {
                        inherited.clone_from(&b.aliases);
                    }
                }
                Err(reason) => {
                    tracing::warn!(path, spec, reason, "tsconfig extends not followed");
                    cfg.incomplete = true;
                }
            }
        }
        cfg.base_url = raw.base_url.or(cfg.base_url);
        cfg.include = raw.include.or(cfg.include);
        cfg.files = raw.files.or(cfg.files);
        cfg.exclude = raw.exclude.or(cfg.exclude);
        cfg.references = raw.references;
        // A config's own `paths` replace the inherited ones; they resolve against `baseUrl`, else this config.
        cfg.aliases = match raw.paths {
            Some(own) => {
                let anchor = cfg.base_url.clone().unwrap_or_else(|| dir.clone());
                own.into_iter()
                    .map(|(pattern, targets)| PathAlias {
                        pattern,
                        targets: targets.iter().map(|t| join_rel(&anchor, t)).collect(),
                    })
                    .collect()
            }
            None => inherited,
        };
        Ok(Arc::new(cfg))
    }

    /// The config files `names` found directly in `dir`.
    fn configs_in(&mut self, dir: &str) -> Vec<String> {
        let mut found = Vec::new();
        for n in CONFIG_NAMES {
            let p = join_rel(dir, n);
            if self.is_file(&p) {
                found.push(p);
                break;
            }
        }
        found
    }

    fn covering(&mut self, config: &str, file: &str, depth: usize) -> Option<Arc<TsConfig>> {
        let cfg = self.load_config(config, 0).ok()?;
        if cfg.covers(file) {
            return Some(cfg);
        }
        if depth >= 2 {
            return None;
        }
        cfg.references
            .iter()
            .find_map(|r| self.covering(r, file, depth + 1))
    }

    /// The config governing repo-relative `file`: the nearest one above it that covers it.
    pub fn config_for(&mut self, file: &str) -> Option<Arc<TsConfig>> {
        let start = dir_of(file).to_owned();
        let key = format!("{start}\0{file}");
        if let Some(hit) = self.governing.get(&key) {
            return hit.clone();
        }
        let mut cur = start;
        let found = loop {
            let here = self.configs_in(&cur);
            if let Some(c) = here.iter().find_map(|c| self.covering(c, file, 0)) {
                break Some(c);
            }
            match parent_dir(&cur) {
                Some(p) => cur = p,
                None => break None,
            }
        };
        self.governing.insert(key, found.clone());
        found
    }

    /// True when `name` is a declared dependency of a package above `dir` or installed in a `node_modules` above it.
    fn is_dependency(&mut self, dir: &str, name: &str) -> bool {
        let mut cur = dir.to_owned();
        loop {
            let pkg = join_rel(&cur, "package.json");
            if self.is_file(&pkg)
                && self
                    .package(&pkg)
                    .is_some_and(|p| p.dependencies.contains(name))
            {
                return true;
            }
            if self.is_dir(&join_rel(&cur, &format!("node_modules/{name}"))) {
                return true;
            }
            match parent_dir(&cur) {
                Some(p) => cur = p,
                None => return false,
            }
        }
    }

    fn package_entry(pkg: &Package, sub: &str) -> Vec<String> {
        let mut out = Vec::new();
        let mut push = |rel: &str| {
            out.push(join_rel(&pkg.dir, rel));
            if let Some(t) = source_twin(&pkg.dir, rel) {
                out.push(t);
            }
        };
        if let Some(exports) = &pkg.exports {
            let key = if sub.is_empty() {
                ".".to_owned()
            } else {
                format!("./{sub}")
            };
            for t in export_targets(exports, &key).unwrap_or_default() {
                push(&t);
            }
            return out;
        }
        if sub.is_empty() {
            for e in &pkg.entries {
                push(e);
            }
            out.push(join_rel(&pkg.dir, "src/index"));
            out.push(join_rel(&pkg.dir, "index"));
        } else {
            out.push(join_rel(&pkg.dir, sub));
            out.push(join_rel(&pkg.dir, &format!("src/{sub}")));
        }
        out
    }

    /// Resolves the non-relative `spec` imported by repo-relative `file`.
    pub fn resolve(&mut self, file: &str, spec: &str) -> JsResolution {
        let mut out = JsResolution::default();
        let owner = self.owner(file).and_then(|p| self.package(&p));
        let pkg_dir = owner
            .as_ref()
            .map_or_else(|| dir_of(file).to_owned(), |p| p.dir.clone());
        if spec.starts_with('#') {
            let map = owner.as_ref().and_then(|p| match &p.imports {
                Some(Value::Object(o)) => {
                    lookup_map(o, spec).map(|(v, s)| targets_of(v, s.as_deref()))
                }
                _ => None,
            });
            for t in map.unwrap_or_default() {
                if t.starts_with("./") {
                    out.candidates.push(join_rel(&pkg_dir, &t));
                } else {
                    out.external |=
                        is_builtin(&t) || self.is_dependency(&pkg_dir, split_package(&t).0);
                }
            }
            return out;
        }
        if let Some(cfg) = self.config_for(file) {
            let best = cfg
                .aliases
                .iter()
                .filter_map(|a| alias_targets(a, spec).map(|t| (a.pattern.len(), t)))
                .max_by_key(|(n, _)| *n);
            if let Some((_, targets)) = best {
                out.candidates.extend(targets);
            }
            if let Some(b) = &cfg.base_url {
                out.candidates.push(join_rel(b, spec));
            }
        }
        let (name, sub) = split_package(spec);
        let members = self.workspace_members(&pkg_dir);
        let own = owner
            .as_ref()
            .and_then(|p| p.name.clone().map(|n| (n, p.path.clone())));
        let member = members
            .get(name)
            .cloned()
            .or_else(|| own.filter(|(n, _)| n == name).map(|(_, p)| p));
        if let Some(path) = member
            && let Some(p) = self.package(&path)
        {
            tracing::debug!(file, spec, package = %p.path, "workspace package specifier");
            out.candidates.extend(Self::package_entry(&p, sub));
            return out;
        }
        out.external = is_builtin(spec) || self.is_dependency(&pkg_dir, name);
        out
    }

    /// The malformed `package.json` and tsconfig files among repo-relative `files`, as (path, reason).
    pub fn malformed(&mut self, files: &[&str]) -> Vec<(String, String)> {
        let mut out = Vec::new();
        for f in files {
            let name = f.rsplit('/').next().unwrap_or(f);
            if name == "package.json" {
                if let Err(r) = self.load_package(f) {
                    out.push(((*f).to_owned(), r.clone()));
                }
            } else if CONFIG_NAMES.contains(&name)
                && let Err(r) = self.load_config(f, 0)
            {
                out.push(((*f).to_owned(), r));
            }
        }
        out
    }
}

/// The targets of `alias` for `spec`, `*` substituted; `None` when the alias does not accept `spec`.
fn alias_targets(alias: &PathAlias, spec: &str) -> Option<Vec<String>> {
    match alias.pattern.split_once('*') {
        None => (alias.pattern == spec).then(|| alias.targets.clone()),
        Some((pre, post)) => {
            let mid = spec.strip_prefix(pre)?.strip_suffix(post)?;
            (spec.len() >= pre.len() + post.len())
                .then(|| alias.targets.iter().map(|t| t.replace('*', mid)).collect())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jsonc_comments_and_trailing_commas_are_stripped() {
        let t = "{ // c\n \"a\": \"x//y\", /* b */ \"l\": [1, 2,],\n}";
        let v: Value = serde_json::from_str(&strip_jsonc(t)).expect("json");
        assert_eq!(v["a"], "x//y");
        assert_eq!(v["l"].as_array().map(Vec::len), Some(2));
    }

    #[test]
    fn scoped_and_plain_names_split() {
        assert_eq!(split_package("@s/n/deep/x"), ("@s/n", "deep/x"));
        assert_eq!(split_package("@s/n"), ("@s/n", ""));
        assert_eq!(split_package("react-dom/client"), ("react-dom", "client"));
    }

    #[test]
    fn exports_conditions_patterns_and_blocks() {
        let v: Value = serde_json::from_str(
            r#"{".":{"import":"./esm/i.js","default":"./c.js"},"./f/*":"./src/f/*.ts","./x":null}"#,
        )
        .expect("json");
        assert_eq!(export_targets(&v, "."), Some(vec!["./esm/i.js".to_owned()]));
        assert_eq!(
            export_targets(&v, "./f/a/b"),
            Some(vec!["./src/f/a/b.ts".to_owned()])
        );
        assert_eq!(export_targets(&v, "./x"), Some(Vec::new()));
        assert_eq!(export_targets(&v, "./nope"), None);
    }

    #[test]
    fn pnpm_workspace_lists_packages() {
        let t = "packages:\n  - 'apps/*'\n  - \"libs/**\" # c\nother:\n  - no\n";
        assert_eq!(pnpm_patterns(t), ["apps/*", "libs/**"]);
    }

    #[test]
    fn alias_patterns_match_prefix_and_suffix() {
        let a = PathAlias {
            pattern: "@app/*".to_owned(),
            targets: vec!["s/*".to_owned()],
        };
        assert_eq!(
            alias_targets(&a, "@app/x/y"),
            Some(vec!["s/x/y".to_owned()])
        );
        assert_eq!(alias_targets(&a, "@ap/x"), None);
    }
}
