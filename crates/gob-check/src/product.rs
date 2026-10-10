//! The [`Product`] trait: everything that differs between frob, grimble and the other goblins.
//!
//! The pipeline owns the walk, the caches, the stage order, tool stages,
//! exception bookkeeping, fixes, telemetry and the report. A product supplies
//! its own inputs (graph, ledger, lock, ...), its rules grouped for caching,
//! its scope semantics and how exceptions are parsed.

use std::collections::{BTreeSet, HashMap};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use gob_cache::Cache;
use gob_rules::{Exception, Finding, Fingerprint, Resolved, RuleMeta};
use gob_symbols::FileInfo;
use gob_text::FileInterner;

use crate::config::CheckTable;
use crate::core::Core;
use crate::error::CheckError;
use crate::filecheck::FileCheck;
use crate::report::{Stats, Timing};
use crate::rule_set::RuleSet;
use crate::status::LanguageFidelity;

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

/// What a product's external stages (sibling binaries) contributed to one pass.
///
/// The findings join the raw set, so `--only` and the gate treat them as native ones; the
/// suppressed pairs go straight to the report, and `namespaces` keeps the fingerprints the
/// final re-fingerprinting must not overwrite.
#[derive(Debug, Default)]
pub struct External {
    /// Live findings, spans interned into the pass's file table.
    pub findings: Vec<Finding>,
    /// Findings the external product parked, each with its exception.
    pub suppressed: Vec<(Finding, Exception)>,
    /// Fingerprint kept as is, mapped to its namespaced display form (`grimble:<hex>`).
    pub namespaces: HashMap<Fingerprint, String>,
    /// Fidelity rows to merge into the report, keyed by a product-qualified language label.
    pub languages: Vec<(String, LanguageFidelity)>,
    /// Non-fatal notes for the report's warnings.
    pub warnings: Vec<String>,
    /// Ids of every rule the external products reported, for validating `--only` names.
    pub rule_ids: Vec<String>,
    /// Where each external product's binary was found and its version.
    pub siblings: Vec<crate::SiblingRow>,
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
    // frob:ticket 01M4HAJZA6JTNSSGJYV040TA9M
    /// Whether the group is repo-wide (independent of any ticket diff): a ticket-scoped run skips it.
    pub full_only: bool,
}

/// Why a ticket-scoped run reports a [`RepoGroup::full_only`] rule as not evaluated.
pub const FULL_ONLY_REASON: &str = "repo-wide, runs in full check";

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
            full_only: false,
        }
    }

    // frob:ticket 01M4HAJZA6JTNSSGJYV040TA9M
    /// Mark the group repo-wide: a scoped (`--ticket`) run skips it and a full run evaluates it.
    #[must_use]
    pub fn full_only(mut self) -> Self {
        self.full_only = true;
        self
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

    // frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
    /// Directory that receives `telemetry.jsonl`; the state directory under `root` unless a product keeps it out of the worktree.
    fn telemetry_dir(&self, root: &Path) -> PathBuf {
        root.join(self.state_dir())
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

    /// The declared rules (`RuleDef`s) this product runs, from its `product_rules!` list.
    ///
    /// The pipeline runs exactly this set beside the legacy checks and groups below: file rules
    /// per file through the resolver, repo rules cached, `must_measure` through `Measured`. Empty
    /// until the product's rule crates are migrated.
    fn rule_set(&self) -> RuleSet<Self> {
        RuleSet::new()
    }

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

    /// Start external stages (sibling binaries) before the product's own rules run.
    ///
    /// `scope_files` is the resolved scope's file set, when the run is scoped. The default starts
    /// nothing; a product that spawns work here collects it in [`Product::join_external`].
    fn start_external(
        &self,
        _snap: &Snapshot<Self>,
        _table: &CheckTable,
        _scope_files: Option<&BTreeSet<String>>,
    ) {
    }

    // frob:ticket 01M4FH7QN0DHJD45C4HC8N7M9Q
    /// True when `--only` names no rule of this product may still be an external product's rule.
    ///
    /// The run then refuses a name that neither this product nor any external stage knows.
    fn defers_unknown_only(&self) -> bool {
        false
    }

    /// Join the stages started by [`Product::start_external`], timing them outside the budget.
    fn join_external(
        &self,
        _snap: &Snapshot<Self>,
        _files: &mut FileInterner,
        _timing: &mut Timing,
    ) -> External {
        External::default()
    }

    /// Fidelity and parse facts of a walked file; `None` when the product has no symbol graph.
    ///
    /// Products that return facts get the opaque and partial-parse accounting of
    /// `subject_status`; the default keeps every file examined.
    fn file_info(&self, _shared: &Self::Shared, _path: &str) -> Option<FileInfo> {
        None
    }

    // frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
    /// Walked files the product's analysis could not read, with reasons (`READ001`); empty by default.
    fn unreadable(&self, _shared: &Self::Shared) -> Vec<gob_symbols::SkippedFile> {
        Vec::new()
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
