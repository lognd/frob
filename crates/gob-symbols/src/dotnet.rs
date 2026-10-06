//! .NET project model: `.sln` solutions and `.csproj` assemblies as packages.
//!
//! Each project file is one package (the C# counterpart of a Cargo crate,
//! code-model.md section 3 "Packages and project files"): a `.cs` file belongs
//! to the nearest enclosing project, `bin/` and `obj/` under the project are
//! ignored, and a `ProjectReference` is a package dependency edge. A project
//! file that cannot be parsed is kept as a malformed project (never dropped),
//! so reach through it stays unresolved instead of being ruled out.
//!
//! `MSBuild` conditions are not evaluated: every `PropertyGroup` and `ItemGroup`
//! contributes, later properties win, and property references (`$(Name)`) in
//! item paths stay verbatim (and so match nothing).

// frob:ticket 01M44YQW33GJMXQ8PQBECEBCQ1

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use crate::crates::join_rel;

/// Solution project type GUID of a solution folder (not a real project).
const FOLDER_GUID: &str = "2150E333-8FDC-42A3-9474-D2E70F8ED6FD";

/// Namespaces the base SDK imports when `ImplicitUsings` is on.
const BASE_USINGS: [&str; 7] = [
    "System",
    "System.Collections.Generic",
    "System.IO",
    "System.Linq",
    "System.Net.Http",
    "System.Threading",
    "System.Threading.Tasks",
];

/// Extra namespaces of the Web SDK.
const WEB_USINGS: [&str; 9] = [
    "System.Net.Http.Json",
    "Microsoft.AspNetCore.Builder",
    "Microsoft.AspNetCore.Hosting",
    "Microsoft.AspNetCore.Http",
    "Microsoft.AspNetCore.Routing",
    "Microsoft.Extensions.Configuration",
    "Microsoft.Extensions.DependencyInjection",
    "Microsoft.Extensions.Hosting",
    "Microsoft.Extensions.Logging",
];

/// Extra namespaces of the Worker SDK.
const WORKER_USINGS: [&str; 5] = [
    "System.Net.Http.Json",
    "Microsoft.Extensions.Configuration",
    "Microsoft.Extensions.DependencyInjection",
    "Microsoft.Extensions.Hosting",
    "Microsoft.Extensions.Logging",
];

/// Why a `.sln` or project file could not be modelled.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum DotnetError {
    /// The file could not be read.
    #[error("cannot read {path}: {reason}")]
    Io {
        /// Repo-relative path.
        path: String,
        /// The operating system error text.
        reason: String,
    },
    /// The XML is not well formed.
    #[error("malformed XML at line {line}: {reason}")]
    Xml {
        /// 1-based line of the fault.
        line: usize,
        /// What is wrong.
        reason: String,
    },
    /// The XML is well formed but its root is not `Project`.
    #[error("root element is not <Project>")]
    NotProject,
    /// The solution lacks the `Microsoft Visual Studio Solution File` header.
    #[error("missing solution file header")]
    SolutionHeader,
}

/// A project file that could not be modelled; its package stays Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MalformedProject {
    /// Repo-relative path of the `.csproj` or `.sln`.
    pub path: String,
    /// The error text.
    pub reason: String,
}

/// One `<Compile>` item: an include (with excludes) or a remove.
#[derive(Debug, Clone, PartialEq, Eq)]
struct CompileItem {
    remove: bool,
    patterns: Vec<String>,
    excludes: Vec<String>,
}

/// A parsed `.csproj`: one package.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Project {
    /// Repo-relative path of the project file (the package id).
    pub path: String,
    /// Repo-relative directory of the project file (empty at the root).
    pub dir: String,
    /// True for SDK-style projects (`Sdk` attribute or SDK import).
    pub sdk_style: bool,
    /// The SDK name without version (`Microsoft.NET.Sdk`), when SDK-style.
    pub sdk: Option<String>,
    /// `AssemblyName`, defaulting to the file stem.
    pub assembly_name: String,
    /// `RootNamespace`, defaulting to the file stem.
    pub root_namespace: String,
    /// `TargetFramework` and `TargetFrameworks` entries (legacy `TargetFrameworkVersion` included).
    pub target_frameworks: Vec<String>,
    /// `LangVersion`, when set.
    pub lang_version: Option<String>,
    /// Whether `ImplicitUsings` is enabled.
    pub implicit_usings: bool,
    /// Repo-relative paths of `ProjectReference` targets.
    pub project_refs: Vec<String>,
    /// `PackageReference` names.
    pub package_refs: Vec<String>,
    enable_default_compile: bool,
    compile: Vec<CompileItem>,
    usings: Vec<(bool, String)>,
}

impl Project {
    /// Namespaces imported project-wide by the SDK (`ImplicitUsings`) and `<Using>` items, sorted and distinct.
    pub fn implicit_usings(&self) -> Vec<String> {
        let mut out: Vec<String> = Vec::new();
        if self.implicit_usings {
            out.extend(BASE_USINGS.iter().map(|s| (*s).to_owned()));
            let extra: &[&str] = match self.sdk.as_deref() {
                Some("Microsoft.NET.Sdk.Web") => &WEB_USINGS,
                Some("Microsoft.NET.Sdk.Worker") => &WORKER_USINGS,
                _ => &[],
            };
            out.extend(extra.iter().map(|s| (*s).to_owned()));
        }
        for (add, ns) in &self.usings {
            if *add {
                out.push(ns.clone());
            } else {
                out.retain(|u| u != ns);
            }
        }
        out.sort();
        out.dedup();
        out
    }

    /// True when `rel` (project-directory relative, `/` separated) is a build output (`bin/` or `obj/`).
    pub fn is_output(rel: &str) -> bool {
        matches!(rel.split('/').next(), Some("bin" | "obj")) && rel.contains('/')
    }

    /// True when the compile items of this project include `file` (repo-relative).
    pub fn compiles(&self, file: &str) -> bool {
        let Some(rel) = relative_to(&self.dir, file) else {
            return false;
        };
        if Self::is_output(&rel) {
            return false;
        }
        let mut included = self.sdk_style
            && self.enable_default_compile
            && rel.rsplit_once('.').is_some_and(|(_, e)| e == "cs")
            && !rel.split('/').any(|seg| seg.starts_with('.'));
        for item in &self.compile {
            let hit = item.patterns.iter().any(|p| glob_match(p, &rel));
            if !hit {
                continue;
            }
            if item.remove {
                included = false;
            } else if !item.excludes.iter().any(|p| glob_match(p, &rel)) {
                included = true;
            }
        }
        included
    }
}

/// True when `path` has extension `ext`, ignoring case.
pub(crate) fn has_ext(path: &str, ext: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case(ext))
}

/// `file` relative to directory `dir` (both repo-relative), if it is inside it.
fn relative_to(dir: &str, file: &str) -> Option<String> {
    if dir.is_empty() {
        return Some(file.to_owned());
    }
    file.strip_prefix(dir)
        .and_then(|r| r.strip_prefix('/'))
        .map(str::to_owned)
}

/// `MSBuild` path pattern normalised: backslashes to slashes, leading `./` dropped.
fn norm_pattern(p: &str) -> String {
    let s = p.trim().replace('\\', "/");
    s.strip_prefix("./").unwrap_or(&s).to_owned()
}

/// Matches one path segment against a pattern with `*` and `?`.
fn seg_match(pat: &[char], text: &[char]) -> bool {
    match pat.split_first() {
        None => text.is_empty(),
        Some(('*', rest)) => (0..=text.len()).any(|i| seg_match(rest, &text[i..])),
        Some(('?', rest)) => !text.is_empty() && seg_match(rest, &text[1..]),
        Some((c, rest)) => text.first().is_some_and(|t| t == c) && seg_match(rest, &text[1..]),
    }
}

/// Matches `path` against an `MSBuild` glob (`*`, `?`, `**` spanning directories).
fn glob_match(pattern: &str, path: &str) -> bool {
    fn go(pat: &[&str], path: &[&str]) -> bool {
        match pat.split_first() {
            None => path.is_empty(),
            Some((&"**", rest)) => (0..=path.len()).any(|i| go(rest, &path[i..])),
            Some((seg, rest)) => path.split_first().is_some_and(|(p, tail)| {
                let s: Vec<char> = seg.chars().collect();
                let t: Vec<char> = p.chars().collect();
                seg_match(&s, &t) && go(rest, tail)
            }),
        }
    }
    let pat = norm_pattern(pattern);
    let pat: Vec<&str> = pat.split('/').collect();
    let path: Vec<&str> = path.split('/').collect();
    go(&pat, &path)
}

/// One XML element in document order.
#[derive(Debug)]
struct Element {
    name: String,
    attrs: Vec<(String, String)>,
    text: String,
    parent: Option<usize>,
}

impl Element {
    fn attr(&self, key: &str) -> Option<&str> {
        self.attrs
            .iter()
            .find(|(k, _)| k.eq_ignore_ascii_case(key))
            .map(|(_, v)| v.as_str())
    }
    fn is(&self, name: &str) -> bool {
        self.name.eq_ignore_ascii_case(name)
    }
}

fn line_of(text: &str, at: usize) -> usize {
    text[..at.min(text.len())].matches('\n').count() + 1
}

fn decode(s: &str) -> String {
    s.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&apos;", "'")
        .replace("&amp;", "&")
}

/// Parses an `MSBuild` project file into elements; fails on any well-formedness fault.
fn parse_xml(text: &str) -> Result<Vec<Element>, DotnetError> {
    let err = |at: usize, reason: &str| DotnetError::Xml {
        line: line_of(text, at),
        reason: reason.to_owned(),
    };
    let mut out: Vec<Element> = Vec::new();
    let mut stack: Vec<usize> = Vec::new();
    let mut roots = 0usize;
    let mut i = 0usize;
    while i < text.len() {
        let rest = &text[i..];
        let Some(lt) = rest.find('<') else {
            if let Some(&top) = stack.last() {
                out[top].text.push_str(&decode(rest));
            }
            break;
        };
        if let Some(&top) = stack.last() {
            out[top].text.push_str(&decode(&rest[..lt]));
        }
        i += lt;
        let rest = &text[i..];
        if rest.starts_with("<!--") {
            let end = rest
                .find("-->")
                .ok_or_else(|| err(i, "unterminated comment"))?;
            i += end + 3;
        } else if rest.starts_with("<![CDATA[") {
            let end = rest
                .find("]]>")
                .ok_or_else(|| err(i, "unterminated CDATA"))?;
            if let Some(&top) = stack.last() {
                out[top].text.push_str(&rest[9..end]);
            }
            i += end + 3;
        } else if rest.starts_with("<?") {
            let end = rest
                .find("?>")
                .ok_or_else(|| err(i, "unterminated declaration"))?;
            i += end + 2;
        } else if rest.starts_with("<!") {
            let end = rest
                .find('>')
                .ok_or_else(|| err(i, "unterminated declaration"))?;
            i += end + 1;
        } else if let Some(close) = rest.strip_prefix("</") {
            let end = close
                .find('>')
                .ok_or_else(|| err(i, "unterminated end tag"))?;
            let name = close[..end].trim();
            let Some(top) = stack.pop() else {
                return Err(err(i, "end tag without start tag"));
            };
            if out[top].name != name {
                return Err(err(
                    i,
                    &format!("end tag </{name}> closes <{}>", out[top].name),
                ));
            }
            i += end + 3;
        } else {
            let (el, used, self_closing) = parse_start_tag(&rest[1..]).map_err(|r| err(i, &r))?;
            let parent = stack.last().copied();
            if parent.is_none() {
                roots += 1;
                if roots > 1 {
                    return Err(err(i, "more than one root element"));
                }
            }
            out.push(Element { parent, ..el });
            if !self_closing {
                stack.push(out.len() - 1);
            }
            i += used + 2;
        }
    }
    if let Some(&open) = stack.last() {
        return Err(err(
            text.len(),
            &format!("unclosed element <{}>", out[open].name),
        ));
    }
    match out.first() {
        None => Err(err(0, "no root element")),
        Some(root) if !root.is("Project") => Err(DotnetError::NotProject),
        Some(_) => Ok(out),
    }
}

/// Parses `name attr="v" ... >` (after the `<`), returning the element, bytes used, self-closing.
fn parse_start_tag(s: &str) -> Result<(Element, usize, bool), String> {
    let bytes = s.as_bytes();
    let mut p = 0usize;
    while p < bytes.len() && !bytes[p].is_ascii_whitespace() && !matches!(bytes[p], b'/' | b'>') {
        p += 1;
    }
    if p == 0 {
        return Err("empty element name".to_owned());
    }
    let name = s[..p].to_owned();
    let mut attrs = Vec::new();
    loop {
        while p < bytes.len() && bytes[p].is_ascii_whitespace() {
            p += 1;
        }
        match bytes.get(p) {
            None => return Err(format!("unterminated start tag <{name}")),
            Some(b'>') => {
                let el = Element {
                    name,
                    attrs,
                    text: String::new(),
                    parent: None,
                };
                return Ok((el, p, false));
            }
            Some(b'/') => {
                if bytes.get(p + 1) == Some(&b'>') {
                    let el = Element {
                        name,
                        attrs,
                        text: String::new(),
                        parent: None,
                    };
                    return Ok((el, p + 1, true));
                }
                return Err(format!("stray '/' in <{name}"));
            }
            Some(_) => {
                let start = p;
                while p < bytes.len() && !bytes[p].is_ascii_whitespace() && bytes[p] != b'=' {
                    p += 1;
                }
                let key = s[start..p].to_owned();
                while p < bytes.len() && bytes[p].is_ascii_whitespace() {
                    p += 1;
                }
                if bytes.get(p) != Some(&b'=') {
                    return Err(format!("attribute {key} of <{name}> has no value"));
                }
                p += 1;
                while p < bytes.len() && bytes[p].is_ascii_whitespace() {
                    p += 1;
                }
                let quote = match bytes.get(p) {
                    Some(q @ (b'"' | b'\'')) => *q,
                    _ => return Err(format!("attribute {key} of <{name}> is not quoted")),
                };
                p += 1;
                let vstart = p;
                while p < bytes.len() && bytes[p] != quote {
                    p += 1;
                }
                if p >= bytes.len() {
                    return Err(format!("unterminated value of attribute {key}"));
                }
                attrs.push((key, decode(&s[vstart..p])));
                p += 1;
            }
        }
    }
}

/// Splits an `MSBuild` `;` list, trimming and dropping empties.
fn split_list(s: &str) -> Vec<String> {
    s.split(';')
        .map(str::trim)
        .filter(|x| !x.is_empty())
        .map(str::to_owned)
        .collect()
}

fn truthy(s: &str) -> bool {
    matches!(s.trim().to_ascii_lowercase().as_str(), "true" | "enable")
}

/// The `<Compile>` item of `e` (an include with excludes, or a remove), if it has either attribute.
fn compile_item(e: &Element) -> Option<CompileItem> {
    let pats = |v: &str| split_list(v).iter().map(|s| norm_pattern(s)).collect();
    if let Some(inc) = e.attr("Include") {
        Some(CompileItem {
            remove: false,
            patterns: pats(inc),
            excludes: e.attr("Exclude").map(pats).unwrap_or_default(),
        })
    } else {
        e.attr("Remove").map(|rm| CompileItem {
            remove: true,
            patterns: pats(rm),
            excludes: Vec::new(),
        })
    }
}

/// Parses the project file `text` located at repo-relative `path`.
///
/// # Errors
///
/// [`DotnetError`] when the XML is malformed or the root is not `Project`.
pub fn parse_project(path: &str, text: &str) -> Result<Project, DotnetError> {
    let els = parse_xml(text)?;
    let dir = path.rsplit_once('/').map_or("", |(d, _)| d).to_owned();
    let stem = path
        .rsplit('/')
        .next()
        .and_then(|f| f.rsplit_once('.').map(|(s, _)| s))
        .unwrap_or(path)
        .to_owned();
    let in_group = |e: &Element, group: &str| e.parent.is_some_and(|p| els[p].is(group));
    let mut sdk = els[0]
        .attr("Sdk")
        .map(|s| s.split('/').next().unwrap_or(s).to_owned());
    for e in els.iter().filter(|e| e.is("Import")) {
        if sdk.is_none()
            && let Some(s) = e.attr("Sdk")
        {
            sdk = Some(s.split('/').next().unwrap_or(s).to_owned());
        }
    }
    let mut p = Project {
        path: path.to_owned(),
        dir: dir.clone(),
        sdk_style: sdk.is_some(),
        sdk,
        assembly_name: stem.clone(),
        root_namespace: stem,
        target_frameworks: Vec::new(),
        lang_version: None,
        implicit_usings: false,
        project_refs: Vec::new(),
        package_refs: Vec::new(),
        enable_default_compile: true,
        compile: Vec::new(),
        usings: Vec::new(),
    };
    for e in &els {
        if in_group(e, "PropertyGroup") {
            let v = e.text.trim();
            match e.name.to_ascii_lowercase().as_str() {
                "assemblyname" if !v.is_empty() => v.clone_into(&mut p.assembly_name),
                "rootnamespace" if !v.is_empty() => v.clone_into(&mut p.root_namespace),
                "targetframework" | "targetframeworks" | "targetframeworkversion" => {
                    for tf in split_list(v) {
                        if !p.target_frameworks.contains(&tf) {
                            p.target_frameworks.push(tf);
                        }
                    }
                }
                "langversion" if !v.is_empty() => p.lang_version = Some(v.to_owned()),
                "implicitusings" => p.implicit_usings = truthy(v),
                "enabledefaultcompileitems" => p.enable_default_compile = truthy(v),
                _ => {}
            }
        } else if in_group(e, "ItemGroup") {
            if e.is("Compile") {
                p.compile.extend(compile_item(e));
            } else if e.is("ProjectReference") {
                if let Some(inc) = e.attr("Include") {
                    let target = join_rel(&dir, &norm_pattern(inc));
                    if !p.project_refs.contains(&target) {
                        p.project_refs.push(target);
                    }
                }
            } else if e.is("PackageReference") {
                if let Some(inc) = e.attr("Include").or_else(|| e.attr("Update")) {
                    let name = inc.trim().to_owned();
                    if !p.package_refs.contains(&name) {
                        p.package_refs.push(name);
                    }
                }
            } else if e.is("Using") && e.attr("Alias").is_none() && e.attr("Static").is_none() {
                if let Some(inc) = e.attr("Include") {
                    p.usings.push((true, inc.trim().to_owned()));
                } else if let Some(rm) = e.attr("Remove") {
                    p.usings.push((false, rm.trim().to_owned()));
                }
            }
        }
    }
    tracing::debug!(
        path,
        sdk_style = p.sdk_style,
        refs = p.project_refs.len(),
        packages = p.package_refs.len(),
        "parsed project file"
    );
    Ok(p)
}

/// One `Project(...)` entry of a solution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SolutionEntry {
    /// The display name.
    pub name: String,
    /// Repo-relative path of the project file (empty for a folder).
    pub path: String,
    /// True for a solution folder (not a project).
    pub folder: bool,
}

/// Parses solution `text` located at repo-relative `path` into its project entries.
///
/// # Errors
///
/// [`DotnetError::SolutionHeader`] when the header line is missing.
pub fn parse_solution(path: &str, text: &str) -> Result<Vec<SolutionEntry>, DotnetError> {
    if !text.lines().any(|l| {
        l.trim_start_matches('\u{feff}')
            .trim()
            .starts_with("Microsoft Visual Studio Solution File")
    }) {
        return Err(DotnetError::SolutionHeader);
    }
    let dir = path.rsplit_once('/').map_or("", |(d, _)| d);
    let mut out = Vec::new();
    for line in text.lines().map(str::trim) {
        if !line.starts_with("Project(") {
            continue;
        }
        let q: Vec<&str> = line.split('"').collect();
        // Project("{type}") = "name", "path", "{guid}": quoted strings sit at odd indexes.
        if q.len() < 7 {
            continue;
        }
        let kind = q[1].trim_matches(|c| c == '{' || c == '}');
        let folder = kind.eq_ignore_ascii_case(FOLDER_GUID);
        let rel = q[5].replace('\\', "/");
        out.push(SolutionEntry {
            name: q[3].to_owned(),
            path: if folder {
                String::new()
            } else {
                join_rel(dir, &rel)
            },
            folder,
        });
    }
    Ok(out)
}

/// What a `.cs` file maps to in the project model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Assignment {
    /// The file belongs to this project (repo-relative `.csproj` path).
    Project(String),
    /// The file sits in a project's `bin/` or `obj/` and is ignored.
    Ignored,
    /// No project file encloses the file.
    None,
}

/// Lazily loaded project files of one work tree.
#[derive(Debug)]
pub struct DotnetProjects {
    root: PathBuf,
    loaded: HashMap<String, Result<Project, String>>,
    dirs: HashMap<String, Vec<String>>,
}

impl DotnetProjects {
    /// An empty project set for the work tree `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            loaded: HashMap::new(),
            dirs: HashMap::new(),
        }
    }

    /// The project file at repo-relative `path`, parsed once; the error text when it is malformed.
    pub fn load(&mut self, path: &str) -> &Result<Project, String> {
        if !self.loaded.contains_key(path) {
            let parsed = std::fs::read_to_string(self.root.join(path))
                .map_err(|e| DotnetError::Io {
                    path: path.to_owned(),
                    reason: e.to_string(),
                })
                .and_then(|t| parse_project(path, &t))
                .map_err(|e| e.to_string());
            match &parsed {
                Ok(_) => tracing::debug!(path, "project loaded"),
                Err(reason) => tracing::warn!(path, reason, "malformed project file; Unresolved"),
            }
            self.loaded.insert(path.to_owned(), parsed);
        }
        &self.loaded[path]
    }

    /// The `.csproj` files directly in repo-relative `dir`, sorted.
    fn projects_in(&mut self, dir: &str) -> Vec<String> {
        if let Some(hit) = self.dirs.get(dir) {
            return hit.clone();
        }
        let mut found: Vec<String> = std::fs::read_dir(self.root.join(dir))
            .into_iter()
            .flatten()
            .flatten()
            .filter_map(|e| e.file_name().into_string().ok())
            .filter(|n| n.ends_with(".csproj"))
            .map(|n| {
                if dir.is_empty() {
                    n
                } else {
                    format!("{dir}/{n}")
                }
            })
            .collect();
        found.sort();
        self.dirs.insert(dir.to_owned(), found.clone());
        found
    }

    /// The project owning repo-relative `file`: the nearest enclosing project, `bin/` and `obj/` ignored.
    pub fn assign(&mut self, file: &str) -> Assignment {
        let mut cur = file.rsplit_once('/').map_or("", |(d, _)| d).to_owned();
        loop {
            let candidates = self.projects_in(&cur);
            if !candidates.is_empty() {
                let rel = relative_to(&cur, file).unwrap_or_default();
                if Project::is_output(&rel) {
                    tracing::debug!(file, "build output ignored");
                    return Assignment::Ignored;
                }
                let claiming = candidates
                    .iter()
                    .find(|c| matches!(self.load(c), Ok(p) if p.compiles(file)))
                    .cloned();
                let chosen = claiming.unwrap_or_else(|| candidates[0].clone());
                return Assignment::Project(chosen);
            }
            match cur.rsplit_once('/') {
                Some((up, _)) => cur = up.to_owned(),
                None if cur.is_empty() => return Assignment::None,
                None => cur = String::new(),
            }
        }
    }

    /// The package dependency edges of project `path`: its `ProjectReference` targets.
    pub fn references(&mut self, path: &str) -> Vec<String> {
        self.load(path)
            .as_ref()
            .map(|p| p.project_refs.clone())
            .unwrap_or_default()
    }

    /// The assembly name of project `path` (the file stem when it is malformed).
    pub fn assembly_name(&mut self, path: &str) -> String {
        match self.load(path) {
            Ok(p) => p.assembly_name.clone(),
            Err(_) => path
                .rsplit('/')
                .next()
                .map_or(path, |f| f.strip_suffix(".csproj").unwrap_or(f))
                .to_owned(),
        }
    }

    /// True when project `path` is malformed or unreadable (its reach cannot be ruled out).
    pub fn is_unresolved(&mut self, path: &str) -> bool {
        self.load(path).is_err()
    }

    /// The malformed project and solution files seen among repo-relative `files`, sorted by path.
    pub fn malformed(&mut self, files: &[&str]) -> Vec<MalformedProject> {
        let mut out = Vec::new();
        for f in files {
            if f.ends_with(".csproj") {
                if let Err(reason) = self.load(f) {
                    out.push(MalformedProject {
                        path: (*f).to_owned(),
                        reason: reason.clone(),
                    });
                }
            } else if has_ext(f, "sln") {
                let res = std::fs::read_to_string(self.root.join(f))
                    .map_err(|e| e.to_string())
                    .and_then(|t| parse_solution(f, &t).map_err(|e| e.to_string()));
                if let Err(reason) = res {
                    tracing::warn!(path = f, %reason, "malformed solution file; Unresolved");
                    out.push(MalformedProject {
                        path: (*f).to_owned(),
                        reason,
                    });
                }
            }
        }
        out.sort_by(|a, b| a.path.cmp(&b.path));
        out
    }

    /// The `.csproj` paths a solution lists (folders and other project kinds dropped).
    ///
    /// # Errors
    ///
    /// [`DotnetError`] when the solution is unreadable or has no header.
    pub fn solution_projects(&self, sln: &str) -> Result<Vec<String>, DotnetError> {
        let text = std::fs::read_to_string(self.root.join(sln)).map_err(|e| DotnetError::Io {
            path: sln.to_owned(),
            reason: e.to_string(),
        })?;
        Ok(parse_solution(sln, &text)?
            .into_iter()
            .filter(|e| !e.folder && e.path.ends_with(".csproj"))
            .map(|e| e.path)
            .collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SDK: &str = r#"<Project Sdk="Microsoft.NET.Sdk.Web">
  <!-- comment -->
  <PropertyGroup>
    <TargetFrameworks>net8.0;net6.0</TargetFrameworks>
    <ImplicitUsings>enable</ImplicitUsings>
    <LangVersion>12</LangVersion>
    <RootNamespace>Acme.App</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <ProjectReference Include="..\Lib\Lib.csproj" />
    <Using Include="Acme.Extras" />
    <Using Remove="System.IO" />
    <Compile Remove="Skip\**" />
  </ItemGroup>
</Project>"#;

    // frob:tests crates/gob-symbols/src/dotnet.rs::parse_project
    #[test]
    fn sdk_project_fields_and_implicit_usings() {
        let p = parse_project("src/App/App.csproj", SDK).expect("parses");
        assert!(p.sdk_style);
        assert_eq!(p.target_frameworks, ["net8.0", "net6.0"]);
        assert_eq!(p.lang_version.as_deref(), Some("12"));
        assert_eq!(p.root_namespace, "Acme.App");
        assert_eq!(p.assembly_name, "App");
        assert_eq!(p.project_refs, ["src/Lib/Lib.csproj"]);
        assert_eq!(p.package_refs, ["Newtonsoft.Json"]);
        let u = p.implicit_usings();
        assert!(u.contains(&"System.Linq".to_owned()));
        assert!(u.contains(&"Microsoft.AspNetCore.Builder".to_owned()));
        assert!(u.contains(&"Acme.Extras".to_owned()));
        assert!(!u.contains(&"System.IO".to_owned()));
    }

    #[test]
    fn default_globs_ignore_outputs_and_removed_dirs() {
        let p = parse_project("src/App/App.csproj", SDK).expect("parses");
        assert!(p.compiles("src/App/Program.cs"));
        assert!(p.compiles("src/App/Deep/X.cs"));
        assert!(!p.compiles("src/App/obj/Debug/X.cs"));
        assert!(!p.compiles("src/App/bin/X.cs"));
        assert!(!p.compiles("src/App/Skip/a/X.cs"));
        assert!(!p.compiles("src/Other/X.cs"));
        assert!(!p.compiles("src/App/readme.md"));
    }

    #[test]
    fn legacy_project_lists_compile_items() {
        let legacy = r#"<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="15.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup><AssemblyName>Old.Thing</AssemblyName><TargetFrameworkVersion>v4.7.2</TargetFrameworkVersion></PropertyGroup>
  <ItemGroup><Compile Include="A.cs" /><Compile Include="Sub\*.cs" Exclude="Sub\Gen.cs" /></ItemGroup>
</Project>"#;
        let p = parse_project("Old.csproj", legacy).expect("parses");
        assert!(!p.sdk_style);
        assert_eq!(p.assembly_name, "Old.Thing");
        assert_eq!(p.target_frameworks, ["v4.7.2"]);
        assert!(p.compiles("A.cs"));
        assert!(p.compiles("Sub/B.cs"));
        assert!(!p.compiles("Sub/Gen.cs"));
        assert!(!p.compiles("Unlisted.cs"));
    }

    #[test]
    fn malformed_projects_are_errors() {
        for bad in [
            "<Project><PropertyGroup></Project>",
            "<Project>",
            "<Other/>",
            "<Project Sdk=Microsoft.NET.Sdk/>",
            "",
            "<Project/><Project/>",
        ] {
            assert!(parse_project("a.csproj", bad).is_err(), "{bad:?}");
        }
    }

    #[test]
    fn solution_entries_and_folders() {
        let sln = "\u{feff}\nMicrosoft Visual Studio Solution File, Format Version 12.00\nProject(\"{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}\") = \"App\", \"src\\App\\App.csproj\", \"{1}\"\nEndProject\nProject(\"{2150E333-8FDC-42A3-9474-D2E70F8ED6FD}\") = \"Docs\", \"Docs\", \"{2}\"\nEndProject\n";
        let e = parse_solution("My.sln", sln).expect("parses");
        assert_eq!(e.len(), 2);
        assert_eq!(e[0].path, "src/App/App.csproj");
        assert!(e[1].folder);
        assert_eq!(
            parse_solution("x.sln", "nope"),
            Err(DotnetError::SolutionHeader)
        );
    }

    #[test]
    fn globs() {
        assert!(glob_match("**/*.cs", "a/b/c.cs"));
        assert!(glob_match("**/*.cs", "c.cs"));
        assert!(glob_match("Sub\\*.cs", "Sub/x.cs"));
        assert!(!glob_match("Sub/*.cs", "Sub/d/x.cs"));
        assert!(glob_match("a?.cs", "ab.cs"));
    }
}
