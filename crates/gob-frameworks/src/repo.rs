//! The repository as the framework adapters read it: sources, folded terms, the module graph, constant
//! evaluation and the owning member of every file.

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::collections::BTreeMap;
use std::path::Path;

use gob_ir::const_value::{Budget, ConstValue, Value, const_value_node};
use gob_ir::{Location, Model, NodeId, Operator, Resolution, Universal};
use gob_symbols::{
    ConstProject, Evaluated, Folded, NodeProjects, SymbolGraph, Symref, fold_file,
    is_typescript_path,
};
use gob_walk::FileEntry;
use tracing::{debug, trace, warn};

use crate::registry::in_node_modules;
use crate::types::{Problem, Status};

/// How far a name is followed through constants and imports to the value it stands for.
const FOLLOW_DEPTH: usize = 6;

/// The folded sources of a repository over its module graph.
pub struct Repo<'g> {
    graph: &'g SymbolGraph,
    texts: BTreeMap<String, String>,
    folded: BTreeMap<String, Folded>,
    project: ConstProject<'g>,
    owners: BTreeMap<String, Option<String>>,
    files: Vec<String>,
    problems: Vec<Problem>,
}

impl<'g> Repo<'g> {
    /// Reads and folds every TypeScript and JavaScript file of `files` under `root`.
    ///
    /// A file that cannot be read or folded is recorded in [`Repo::problems`] and left out.
    pub fn load(root: &Path, files: &[FileEntry], graph: &'g SymbolGraph) -> Self {
        let mut projects = NodeProjects::new(root);
        let mut repo = Self {
            graph,
            texts: BTreeMap::new(),
            folded: BTreeMap::new(),
            project: ConstProject::new(graph),
            owners: BTreeMap::new(),
            files: files.iter().map(|f| f.path.clone()).collect(),
            problems: Vec::new(),
        };
        repo.files.sort();
        for entry in files
            .iter()
            .filter(|f| is_typescript_path(&f.path) && !in_node_modules(&f.path))
        {
            let text = match std::fs::read_to_string(root.join(&entry.path)) {
                Ok(t) => t,
                Err(e) => {
                    warn!(path = %entry.path, error = %e, "source not readable");
                    repo.problems.push(Problem {
                        path: entry.path.clone(),
                        reason: e.to_string(),
                    });
                    continue;
                }
            };
            match fold_file(entry, &text) {
                Ok(folded) => {
                    repo.project.add_file(&entry.path, &folded);
                    repo.folded.insert(entry.path.clone(), folded);
                    repo.texts.insert(entry.path.clone(), text);
                    repo.owners
                        .insert(entry.path.clone(), projects.owner(&entry.path));
                }
                Err(e) => {
                    warn!(path = %entry.path, error = %e, "fold failed");
                    repo.problems.push(Problem {
                        path: entry.path.clone(),
                        reason: e.to_string(),
                    });
                }
            }
        }
        debug!(
            sources = repo.texts.len(),
            problems = repo.problems.len(),
            "repository loaded"
        );
        repo
    }

    /// The files that could not be read or folded.
    pub fn problems(&self) -> &[Problem] {
        &self.problems
    }

    /// Every repo-relative file path, sorted.
    pub fn files(&self) -> &[String] {
        &self.files
    }

    /// The loaded source files owned by the member whose manifest is `member`, sorted.
    pub fn member_sources<'a>(&'a self, member: &'a str) -> impl Iterator<Item = &'a str> {
        self.owners
            .iter()
            .filter(move |(_, o)| o.as_deref() == Some(member))
            .map(|(p, _)| p.as_str())
    }

    /// The source text of `path`, when loaded.
    pub fn text(&self, path: &str) -> Option<&str> {
        self.texts.get(path).map(String::as_str)
    }

    /// The folded file `path`, when loaded.
    pub fn folded(&self, path: &str) -> Option<&Folded> {
        self.folded.get(path)
    }

    /// The model of file `path`, when loaded.
    pub fn model(&self, path: &str) -> Option<&Model> {
        self.project.model(path)
    }

    /// The module graph.
    pub fn graph(&self) -> &SymbolGraph {
        self.graph
    }

    /// The bounded value of `node` of `file`, following constants and imports across files.
    pub fn evaluate(&self, file: &str, node: NodeId) -> Evaluated {
        self.project.evaluate(file, node, Budget::default())
    }

    /// The one-based line of `node` in `file` (1 when it has no text location).
    pub fn line(&self, file: &str, node: NodeId) -> u32 {
        let (Some(model), Some(text)) = (self.model(file), self.text(file)) else {
            return 1;
        };
        let Location::Text { range, .. } = model.term().node(node).location() else {
            return 1;
        };
        let start = usize::try_from(u32::from(range.start())).unwrap_or(0);
        let upto = text.as_bytes().get(..start).unwrap_or(text.as_bytes());
        u32::try_from(upto.split(|b| *b == b'\n').count()).unwrap_or(u32::MAX)
    }

    /// The symref text of the unit called `name` in `file`, when there is exactly one.
    fn local_unit(&self, file: &str, name: &str) -> Option<String> {
        let model = self.model(file)?;
        let want = format!("{file}::{name}");
        let mut hits = model
            .term()
            .units()
            .into_iter()
            .filter(|u| u.symref.to_string() == want);
        let first = hits.next()?;
        hits.next().is_none().then(|| first.symref.to_string())
    }

    /// What `name` written in `file` stands for: the symref of its unit (local or through one import), else
    /// the name as written.
    pub fn name_ref(&self, file: &str, name: &str) -> String {
        if let Some(s) = self.local_unit(file, name) {
            return s;
        }
        if let [(symref, Status::Must)] = self.graph.ts_import_targets(file, name).as_slice() {
            symref.to_string()
        } else {
            trace!(file, name, "name not resolved to a unit");
            name.to_owned()
        }
    }

    /// The symref text of the default export of `file`, read from the syntax of its `export default`.
    ///
    /// A named function or class resolves to its unit, an anonymous one to `path::default`, anything else
    /// (an expression) to the file itself.
    pub fn default_export(&self, file: &str) -> String {
        let Some(text) = self.text(file) else {
            return file.to_owned();
        };
        for line in text.lines() {
            let Some(rest) = line.trim_start().strip_prefix("export default ") else {
                continue;
            };
            let rest = rest.trim_start();
            let rest = rest.strip_prefix("async ").unwrap_or(rest).trim_start();
            let (declared, rest) = match rest
                .strip_prefix("function")
                .or_else(|| rest.strip_prefix("class"))
            {
                Some(r) => (true, r.trim_start_matches(['*', ' '])),
                None => (false, rest),
            };
            let ident: String = rest
                .chars()
                .take_while(|c| c.is_alphanumeric() || *c == '_' || *c == '$')
                .collect();
            let after = rest[ident.len()..].trim_start();
            let named =
                !ident.is_empty() && (declared || after.is_empty() || after.starts_with(';'));
            return match (named, declared) {
                (true, _) => self
                    .local_unit(file, &ident)
                    .unwrap_or_else(|| file.to_owned()),
                (false, true) => self
                    .local_unit(file, "default")
                    .unwrap_or_else(|| file.to_owned()),
                (false, false) => file.to_owned(),
            };
        }
        file.to_owned()
    }

    /// The value expression a `ref` node stands for (a constant of this file or of an imported file).
    ///
    /// Non-reference nodes are returned unchanged; `None` when the reference cannot be followed to one
    /// declaration.
    pub fn follow(&self, file: &str, node: NodeId) -> Option<(String, NodeId)> {
        let mut at = (file.to_owned(), node);
        for _ in 0..FOLLOW_DEPTH {
            let model = self.model(&at.0)?;
            let Operator::Universal(Universal::Ref { name }) = model.term().operator(at.1) else {
                return Some(at);
            };
            let next = if let Resolution::Must(d) = model.resolve_node(at.1) {
                let unit = *model.scopes().decl(d).nodes.first()?;
                (at.0.clone(), const_value_node(model, unit)?)
            } else {
                let targets = self.graph.ts_import_targets(&at.0, name);
                let [(symref, Status::Must)] = targets.as_slice() else {
                    return None;
                };
                self.unit_value(symref)?
            };
            at = next;
        }
        None
    }

    /// The value expression of the constant unit `symref`.
    fn unit_value(&self, symref: &Symref) -> Option<(String, NodeId)> {
        let path = symref.path();
        let model = self.model(path)?;
        let want = symref.to_string();
        let unit = model
            .term()
            .units()
            .into_iter()
            .find(|u| u.symref.to_string() == want)?;
        Some((path.to_owned(), const_value_node(model, unit.node)?))
    }

    /// The value of `node` as strings: `(alternatives, status)`, or `None` when it is not statically known.
    pub fn strings(&self, file: &str, node: NodeId) -> Option<(Vec<String>, Status)> {
        let got = self.evaluate(file, node);
        match got.value {
            ConstValue::Known(Value::Str(s)) => Some((vec![s], Status::Must)),
            ConstValue::OneOf(vs) => {
                let strs: Option<Vec<String>> = vs
                    .into_iter()
                    .map(|v| match v {
                        Value::Str(s) => Some(s),
                        _ => None,
                    })
                    .collect();
                strs.map(|s| (s, Status::May))
            }
            _ => None,
        }
    }
}
