//! The [`Product`] trait: everything that differs between frob, grimble and the other goblins.
//!
//! The pipeline owns the walk, the caches, the stage order, tool stages,
//! exception bookkeeping, fixes, telemetry and the report. A product supplies
//! its own inputs (graph, ledger, lock, ...), its rules grouped for caching,
//! its scope semantics and how exceptions are parsed.

use std::collections::BTreeSet;
use std::sync::Arc;

use gob_cache::Cache;
use gob_rules::{Finding, Resolved, RuleMeta};
use gob_symbols::FileInfo;
use gob_text::FileInterner;

use crate::config::CheckTable;
use crate::core::Core;
use crate::error::CheckError;
use crate::filecheck::FileCheck;
use crate::report::{Stats, Timing};

/// A resolved scope: a label for the report and the files per-file rules are limited to.
pub trait ScopeView {
    /// Report label (frob: the ticket handle with `~`).
    fn label(&self) -> &str;
    /// Repo-relative files per-file rules and located findings are limited to.
    fn files(&self) -> &BTreeSet<String>;
}

/// The scope type of a product without scopes; never constructed.
#[derive(Debug)]
pub enum NoScope {}

impl ScopeView for NoScope {
    fn label(&self) -> &str {
        match *self {}
    }

    fn files(&self) -> &BTreeSet<String> {
        match *self {}
    }
}

/// Everything the rules read, built once per pass.
pub struct Snapshot<P: Product> {
    /// The walk.
    pub core: Core,
    /// Thread-safe product facts used for applicability and cache keys.
    pub shared: P::Shared,
    /// Everything else the product's rules read.
    pub inputs: P::Inputs,
    /// Findings the product's collection stage already produced (frob: directive scan problems).
    pub findings: Vec<Finding>,
}

/// What [`Product::collect`] returns.
pub struct Collected<P: Product> {
    /// Thread-safe facts for applicability and cache keys.
    pub shared: P::Shared,
    /// The product's rule inputs.
    pub inputs: P::Inputs,
    /// Findings found while collecting; kept only inside a `--scope` file set.
    pub findings: Vec<Finding>,
}

/// What [`Product::collect`] may read and record.
pub struct CollectCx<'a> {
    /// The walk.
    pub core: &'a Core,
    /// The `[check]` table in force.
    pub table: &'a CheckTable,
    /// The artifact cache under the product's state directory.
    pub cache: &'a Cache,
    /// Stage timings; push one per collection stage.
    pub timing: &'a mut Timing,
    /// Counters; set the graph counters here.
    pub stats: &'a mut Stats,
}

/// Findings of the scope-specific rules and what they examined.
#[derive(Debug, Default)]
pub struct ScopedFindings {
    /// Raw findings.
    pub findings: Vec<Finding>,
    /// `(rule id, subjects examined)` for each rule that ran.
    pub subjects: Vec<(&'static str, usize)>,
}

/// A repo group's computation: the snapshot and the extendable interner in, raw findings out.
pub type RunFn<P> = Box<dyn Fn(&Snapshot<P>, &mut FileInterner) -> Vec<Finding>>;

/// A repo group's subject counter: `(rule id, subjects examined)` pairs.
pub type CountFn<P> = Box<dyn Fn(&Snapshot<P>) -> Vec<(&'static str, usize)>>;

/// Repo-scope rules computed together and cached per rule.
pub struct RepoGroup<P: Product> {
    /// Name used in timing (`repo:obligations`).
    pub name: &'static str,
    /// Rules the group emits; each gets its own cache row.
    pub metas: Vec<&'static RuleMeta>,
    /// Compute the raw findings; new files may be interned into the given interner.
    pub run: RunFn<P>,
    /// `(rule id, subjects examined)` per rule, evaluated on every run (cache hit or not).
    pub subjects: CountFn<P>,
}

impl<P: Product> RepoGroup<P> {
    /// A group without subject accounting; chain [`RepoGroup::counting`] to add it.
    pub fn new(
        name: &'static str,
        metas: Vec<&'static RuleMeta>,
        run: impl Fn(&Snapshot<P>, &mut FileInterner) -> Vec<Finding> + 'static,
    ) -> Self {
        Self {
            name,
            metas,
            run: Box::new(run),
            subjects: Box::new(|_| Vec::new()),
        }
    }

    /// Attach the per-rule subject counter of this group.
    #[must_use]
    pub fn counting(
        mut self,
        subjects: impl Fn(&Snapshot<P>) -> Vec<(&'static str, usize)> + 'static,
    ) -> Self {
        self.subjects = Box::new(subjects);
        self
    }
}

/// A product the shared pipeline can drive.
pub trait Product: Sized + Sync {
    /// Thread-safe facts for applicability and cache keys (read inside the parallel stage).
    type Shared: Sync;
    /// Everything else the product's rules read; need not be `Sync`.
    type Inputs;
    /// The product's resolved scope (use [`NoScope`] when it has none).
    type Scope: ScopeView;

    /// Product name; names the config file (`<name>.toml`) and state directory (`.<name>`).
    fn name(&self) -> &'static str;

    /// Directory under the root holding cache and telemetry; excluded from the walk.
    fn state_dir(&self) -> String {
        format!(".{}", self.name())
    }

    /// Whether `meta` is one of this product's rules (validates `--only` and picks `must_measure` rules).
    fn includes(&self, meta: &RuleMeta) -> bool {
        meta.product == self.name()
    }

    /// Build the product's inputs once per pass.
    ///
    /// # Errors
    ///
    /// Any [`CheckError`] that stops the run (a malformed lock, a bad config table).
    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError>;

    /// The per-file checks of this run.
    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>>;

    /// The repo-scope rule groups of this run (the pipeline appends the neutral ones).
    fn repo_groups(&self) -> Vec<RepoGroup<Self>>;

    /// Bytes folded into the repo-rule cache key beside the walked files (frob: ledger tip, invariants).
    fn repo_digest(&self, snap: &Snapshot<Self>) -> Vec<u8>;

    /// Resolve the `--scope` reference into a file set.
    ///
    /// # Errors
    ///
    /// [`CheckError`] when the reference cannot be resolved; the default refuses every scope.
    fn resolve_scope(
        &self,
        _snap: &Snapshot<Self>,
        _table: &CheckTable,
        reference: &str,
    ) -> Result<Self::Scope, CheckError> {
        Err(CheckError::Ticket(format!(
            "`{reference}`: {} has no scopes",
            self.name()
        )))
    }

    /// Rules that only run under a scope (frob: `SCOPE001`, `TICK002`).
    fn scoped_rules(
        &self,
        _snap: &Snapshot<Self>,
        _scope: &Self::Scope,
        _table: &CheckTable,
    ) -> ScopedFindings {
        ScopedFindings::default()
    }

    /// Apply the product's exceptions to `raw` and add the findings that police them.
    fn resolve_exceptions(
        &self,
        snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved;

    /// Fidelity and parse facts of a walked file; `None` when the product has no symbol graph.
    ///
    /// Products that return facts get the opaque and partial-parse accounting of
    /// `subject_status`; the default keeps every file examined.
    fn file_info(&self, _shared: &Self::Shared, _path: &str) -> Option<FileInfo> {
        None
    }

    /// True when the product's scanner reads comments and directives of `path` without an adapter.
    fn scans_text(&self, _path: &str) -> bool {
        false
    }

    /// Whether a `must_measure` rule has a non-empty scope in this repository.
    ///
    /// A rule whose whole scope is not applicable (no ledger configured, no
    /// language with a test capability) emits nothing; only an applicable rule
    /// that examined zero subjects is Unresolved.
    fn applicable(&self, _snap: &Snapshot<Self>, _meta: &RuleMeta) -> bool {
        true
    }
}
