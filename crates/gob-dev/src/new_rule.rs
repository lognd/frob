//! `cargo dev new-rule`: scaffold one rule as the two colocated files of D107 (`src/rules/<id>.rs`
//! and `<id>.md`) in its owning crate, regenerate that crate's rule index and run the crate's
//! freshness test. There is no registration step: the index is generated from the files.
//!
//! `cargo dev new-rule --prove` is the CI step (`ci.yml`, step `new-rule`): it scaffolds one
//! universal and one language rule into a temporary copy of a rule crate and compiles and tests
//! it, so the scaffold can never drift from the `#[rule]` attribute. Design:
//! `docs/design/shared/rules.md` section 11.6.
// frob:ticket 01M48R06SBXJZJ79GB8R20ASKS

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

use crate::render::rules_index::{self, RulesIndexError};

/// Longest the compile and test of a scaffolded rule may take (a cold build of a rule crate).
const TEST_TIMEOUT: Duration = Duration::from_secs(3600);

/// The crate `--prove` copies by default: it has a rule, a blanket host and few dependencies.
pub const PROVE_CRATE: &str = "frob-lease";

/// Directory (under `crates/`) the temporary copy of `--prove` lives in; a workspace member by glob.
const PROVE_DIR: &str = "zz-newrule-proof";

/// Which files a rule applies to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Applies {
    /// Every file whose language can supply the needed capabilities.
    Universal,
    /// Only the named `gob_caps::Lang` variants (for example `Rust`, `Python`).
    Languages(Vec<String>),
}

/// Whether the rule judges one file or the whole repository.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Scope {
    /// One file at a time (`FileRule`).
    File,
    /// The repository at once (`RepoRule`).
    Repo,
}

/// Everything the scaffold needs to know about the new rule.
#[derive(Debug, Clone)]
pub struct RuleSpec {
    /// The rule id: 2 to 8 capital letters then three digits (`COV007`).
    pub id: String,
    /// The kebab-case slug (`untested-thing`).
    pub slug: String,
    /// Universal or language-specific.
    pub applies: Applies,
    /// File or repo scope.
    pub scope: Scope,
    /// `gob_caps::Capability` names the rule reads; empty means `Comments`.
    pub needs: Vec<String>,
    /// The owning crate's directory name; derived from the family when `None`.
    pub krate: Option<String>,
    /// The host trait; derived from the crate's existing rules when `None`.
    pub host: Option<String>,
}

/// Why a rule could not be scaffolded.
#[derive(Debug, thiserror::Error)]
pub enum NewRuleError {
    /// The id is not `LETTERS` plus three digits.
    #[error("rule id `{0}` must be 2 to 8 capital letters then three digits, for example COV007")]
    BadId(String),
    /// The slug is not lowercase kebab-case.
    #[error("slug `{0}` must be lowercase kebab-case, for example untested-thing")]
    BadSlug(String),
    /// A name in `--needs` or `--lang` is not a bare identifier.
    #[error("`{0}` is not a capability or language name (an identifier such as Comments or Rust)")]
    BadName(String),
    /// No crate declares the rule's family and `--crate` was not given.
    #[error(
        "no crate lists family `{0}` in [package.metadata.gob] families; pass --crate <dir-name>"
    )]
    NoOwner(String),
    /// The chosen crate has no generated rule index to extend.
    #[error(
        "crate {0} has no src/rules/mod.rs; create the rules module with an existing rule first"
    )]
    NoRulesModule(String),
    /// The rule files already exist.
    #[error("{0} already exists; refusing to overwrite a rule")]
    Exists(String),
    /// The crate has no rule to read the host trait from and `--host` was not given.
    #[error(
        "cannot infer the host trait of crate {0}; pass --host <Trait> (a trait in crate::host)"
    )]
    NoHost(String),
    /// The workspace version is missing, so `since` cannot be set.
    #[error("workspace Cargo.toml has no [workspace.package] version")]
    NoVersion,
    /// A file or directory could not be read or written.
    #[error("{}: {source}", gob_path::Shown::with_home(path, None))]
    Io {
        /// The path.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// The index could not be regenerated.
    #[error(transparent)]
    Index(#[from] RulesIndexError),
    /// The compile or test of the scaffold failed.
    #[error("the scaffolded rule did not build and pass: {0}")]
    Test(String),
}

/// The scaffold's two files, rendered but not written.
#[derive(Debug, PartialEq, Eq)]
pub struct Rendered {
    /// Contents of `<id>.rs`.
    pub rs: String,
    /// Contents of `<id>.md`.
    pub md: String,
}

/// Wrap an I/O error with its path.
fn io(path: &Path) -> impl FnOnce(std::io::Error) -> NewRuleError + '_ {
    move |source| NewRuleError::Io {
        path: path.to_path_buf(),
        source,
    }
}

/// True for a bare identifier (letters and digits, not starting with a digit).
fn is_ident(s: &str) -> bool {
    s.chars().next().is_some_and(|c| c.is_ascii_alphabetic())
        && s.chars().all(|c| c.is_ascii_alphanumeric())
}

/// The family letters of a valid id (2 to 8 capitals before the last three digits).
fn family(id: &str) -> Option<&str> {
    let letters = id.trim_end_matches(|c: char| c.is_ascii_digit());
    let shaped = id.len() - letters.len() == 3 && (2..=8).contains(&letters.len());
    (shaped && letters.bytes().all(|b| b.is_ascii_uppercase())).then_some(letters)
}

/// Whether `slug` is lowercase kebab-case.
fn slug_ok(slug: &str) -> bool {
    !slug.is_empty()
        && !slug.starts_with('-')
        && !slug.ends_with('-')
        && !slug.contains("--")
        && slug
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// The first name in `spec` (needs, then languages) that is not a bare identifier, if any.
fn bad_name(spec: &RuleSpec) -> Option<&String> {
    let langs: &[String] = match &spec.applies {
        Applies::Universal => &[],
        Applies::Languages(l) => l,
    };
    spec.needs.iter().chain(langs).find(|n| !is_ident(n))
}

/// Check the id, slug and names of `spec` before touching the disk.
///
/// # Errors
/// [`NewRuleError`] naming the first malformed field.
pub fn validate(spec: &RuleSpec) -> Result<(), NewRuleError> {
    let empty_langs = matches!(&spec.applies, Applies::Languages(l) if l.is_empty());
    match (family(&spec.id), slug_ok(&spec.slug), bad_name(spec)) {
        (None, _, _) => Err(NewRuleError::BadId(spec.id.clone())),
        (_, false, _) => Err(NewRuleError::BadSlug(spec.slug.clone())),
        (_, _, Some(name)) => Err(NewRuleError::BadName(name.clone())),
        _ if empty_langs => Err(NewRuleError::BadName(String::new())),
        _ => Ok(()),
    }
}

/// `CovSeven`-style struct name of an id: first letter upper, the rest lower, digits kept.
fn type_name(id: &str) -> String {
    let mut chars = id.chars();
    chars
        .next()
        .map(|c| c.to_string() + &chars.as_str().to_ascii_lowercase())
        .unwrap_or_default()
}

/// Render the `.rs` and `.md` of `spec` for host trait `host` (imported from `host_use`) and `since`.
#[must_use]
pub fn render(spec: &RuleSpec, host: &str, host_use: &str, since: &str) -> Rendered {
    let needs = if spec.needs.is_empty() {
        "Comments".to_owned()
    } else {
        spec.needs.join(", ")
    };
    let (applies, fence, file) = match &spec.applies {
        Applies::Universal => (
            format!("universal(needs = [{needs}], min_fidelity = F1)"),
            "rust".to_owned(),
            "src/lib.rs".to_owned(),
        ),
        Applies::Languages(l) => (
            format!(
                "languages({}; needs = [{needs}], min_fidelity = F1)",
                l.join(", ")
            ),
            l[0].to_ascii_lowercase(),
            "src/example.txt".to_owned(),
        ),
    };
    let (scope, imports, body) = match spec.scope {
        Scope::File => (
            "File",
            "FileCx, FileRule, Out, rule",
            format!(
                "impl<P: ?Sized + {host}> FileRule<P> for {ty} {{\n    fn check(&self, _cx: &FileCx<'_, P>, _out: &mut Out<'_, Self>) {{\n        tracing::debug!(\"{id} evaluated\");\n    }}\n}}\n",
                ty = type_name(&spec.id),
                id = spec.id,
            ),
        ),
        Scope::Repo => (
            "Repo",
            "Out, RepoRule, rule",
            format!(
                "impl<P: ?Sized + {host}> RepoRule<P> for {ty} {{\n    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {{\n        tracing::debug!(\"{id} evaluated\");\n    }}\n}}\n",
                ty = type_name(&spec.id),
                id = spec.id,
            ),
        ),
    };
    let ty = type_name(&spec.id);
    let rs = format!(
        "//! {id}: TODO describe what this rule judges (the page `{lower}.md` is its documentation and corpus).\n\nuse gob_rules::{{{imports}}};\n\nuse {host_use};\n\n/// {id} {slug}: replace with a one-line statement of what the rule flags.\n#[derive(Debug, Clone, Copy, Default)]\n#[rule(\n    id = \"{id}\",\n    slug = \"{slug}\",\n    severity = Error,\n    polarity = Pplus,\n    must_measure = false,\n    scope = {scope},\n    fix = Manual,\n    applies = {applies},\n    host = {host},\n    version = 1,\n    since = \"{since}\",\n)]\npub struct {ty};\n\n{body}",
        id = spec.id,
        lower = spec.id.to_ascii_lowercase(),
        slug = spec.slug,
    )
    .replace("TODO describe", "describe");
    let md = format!(
        "<!-- mdtest: rule={id} -->\n# {id} {slug}\n\nOne sentence stating what this rule requires.\n\n## What it does\n\nFlags the code the rule is about.\n\n## Why it matters\n\nWhat goes wrong when the rule is ignored.\n\n## Remedy\n\nHow to fix a finding.\n\n## Examples\n\n### A violating case fires\n\n```{fence} expect=fire file={file}\nviolation\n```\n\n### A conforming case is clean\n\n```{fence} expect=clean file={file}\nconforming\n```\n",
        id = spec.id,
        slug = spec.slug,
    );
    Rendered { rs, md }
}

/// The `[workspace.package] version` of the workspace at `root`.
fn workspace_version(root: &Path) -> Result<String, NewRuleError> {
    let path = root.join("Cargo.toml");
    let text = std::fs::read_to_string(&path).map_err(io(&path))?;
    let table: toml::Table = text.parse().map_err(|_| NewRuleError::NoVersion)?;
    table
        .get("workspace")
        .and_then(|w| w.get("package"))
        .and_then(|p| p.get("version"))
        .and_then(|v| v.as_str())
        .map(str::to_owned)
        .ok_or(NewRuleError::NoVersion)
}

/// The crate directory under `crates/` whose manifest lists `family`.
fn owner_of(crates: &Path, family: &str) -> Result<PathBuf, NewRuleError> {
    let mut owners = Vec::new();
    for entry in std::fs::read_dir(crates).map_err(io(crates))? {
        let dir = entry.map_err(io(crates))?.path();
        if let Some((_, families)) = rules_index::owned_families(&dir)
            && families.iter().any(|f| f == family)
        {
            owners.push(dir);
        }
    }
    owners.sort();
    owners
        .into_iter()
        .next()
        .ok_or_else(|| NewRuleError::NoOwner(family.to_owned()))
}

/// The host trait and its `use` path read from the first existing rule of `rules_dir`.
fn infer_host(rules_dir: &Path, krate: &str) -> Result<(String, String), NewRuleError> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(rules_dir)
        .map_err(io(rules_dir))?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "rs") && !p.ends_with("mod.rs"))
        .collect();
    files.sort();
    for file in files {
        let text = std::fs::read_to_string(&file).map_err(io(&file))?;
        let host = text.lines().find_map(|l| {
            l.trim()
                .strip_prefix("host = ")
                .map(|h| h.trim_end_matches(',').to_owned())
        });
        let Some(host) = host else { continue };
        let suffix = format!("::{host};");
        let path = text
            .lines()
            .find_map(|l| {
                l.trim()
                    .strip_prefix("use ")
                    .filter(|u| u.ends_with(&suffix))
            })
            .map_or_else(
                || format!("crate::host::{host}"),
                |u| u.trim_end_matches(';').to_owned(),
            );
        tracing::debug!(%host, %path, "host trait inferred from {}", gob_path::Shown::of(&file));
        return Ok((host, path));
    }
    Err(NewRuleError::NoHost(krate.to_owned()))
}

/// Where a scaffold will write, resolved and checked before anything is created.
struct Plan {
    krate: String,
    rs: PathBuf,
    md: PathBuf,
    host: String,
    host_use: String,
}

/// Resolve the paths and host for `spec` in `crate_dir`, refusing existing files.
fn plan(spec: &RuleSpec, root: &Path, crate_dir: &Path) -> Result<Plan, NewRuleError> {
    validate(spec)?;
    let krate = crate_dir.file_name().map_or_else(
        || "crate".to_owned(),
        |n| gob_path::Shown::of(Path::new(n)).as_str().to_owned(),
    );
    let rules_dir = crate_dir.join("src").join("rules");
    if !rules_dir.join("mod.rs").is_file() {
        return Err(NewRuleError::NoRulesModule(krate));
    }
    let stem = spec.id.to_ascii_lowercase();
    let (rs, md) = (
        rules_dir.join(format!("{stem}.rs")),
        rules_dir.join(format!("{stem}.md")),
    );
    if let Some(p) = [&rs, &md].into_iter().find(|p| p.exists()) {
        let shown = gob_path::forward_slashes(p.strip_prefix(root).unwrap_or(p));
        return Err(NewRuleError::Exists(shown));
    }
    let (host, host_use) = match &spec.host {
        Some(h) => (h.clone(), format!("crate::host::{h}")),
        None => infer_host(&rules_dir, &krate)?,
    };
    Ok(Plan {
        krate,
        rs,
        md,
        host,
        host_use,
    })
}

/// Scaffold `spec` into `crate_dir`, regenerate its index and return the two paths written.
///
/// # Errors
/// [`NewRuleError`] when the spec is malformed, the files exist, the host cannot be inferred or
/// the index cannot be regenerated.
pub fn scaffold(
    spec: &RuleSpec,
    root: &Path,
    crate_dir: &Path,
) -> Result<[PathBuf; 2], NewRuleError> {
    let p = plan(spec, root, crate_dir)?;
    let rendered = render(spec, &p.host, &p.host_use, &workspace_version(root)?);
    write_all(&[(p.rs.clone(), rendered.rs), (p.md.clone(), rendered.md)])?;
    tracing::info!(id = %spec.id, crate = %p.krate, "rule files written");
    write_all(&index_update(crate_dir, root)?)?;
    Ok([p.rs, p.md])
}

/// Write each `(path, content)` pair to disk.
fn write_all(files: &[(PathBuf, String)]) -> Result<(), NewRuleError> {
    files
        .iter()
        .try_for_each(|(path, content)| std::fs::write(path, content).map_err(io(path)))
}

/// The regenerated rule index for `crate_dir` as a write list (empty when no index is owned).
fn index_update(crate_dir: &Path, root: &Path) -> Result<Vec<(PathBuf, String)>, NewRuleError> {
    let file = rules_index::index_file(crate_dir, root)?;
    Ok(file
        .into_iter()
        .map(|f| (root.join(&f.path), f.content))
        .collect())
}

/// The package name of the crate at `crate_dir`.
fn package_name(crate_dir: &Path) -> Result<String, NewRuleError> {
    let path = crate_dir.join("Cargo.toml");
    let text = std::fs::read_to_string(&path).map_err(io(&path))?;
    let table: toml::Table = text
        .parse()
        .map_err(|e: toml::de::Error| NewRuleError::Test(e.to_string()))?;
    table
        .get("package")
        .and_then(|p| p.get("name"))
        .and_then(|n| n.as_str())
        .map(str::to_owned)
        .ok_or_else(|| {
            NewRuleError::Test(format!(
                "{} has no package name",
                gob_path::Shown::of(&path)
            ))
        })
}

/// Run the crate's rule-index freshness test, which compiles the crate with the new rule bound.
fn run_test(root: &Path, package: &str) -> Result<(), NewRuleError> {
    let spec = Spec {
        program: Program::Cargo,
        args: ["test", "-p", package, "--lib", "rules_index_is_fresh"]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: TEST_TIMEOUT,
        capture: false,
    };
    tracing::info!(package, "running the scaffolded rule's test");
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| NewRuleError::Test(e.to_string()))?;
    match out.status {
        Outcome::Exited(0) => Ok(()),
        other => Err(NewRuleError::Test(format!("cargo test ended {other:?}"))),
    }
}

/// Scaffold `spec` in its owning crate under `root` and run that crate's test.
///
/// # Errors
/// [`NewRuleError`] from [`scaffold`] or when the test fails.
pub fn run(spec: &RuleSpec, root: &Path) -> Result<Vec<PathBuf>, NewRuleError> {
    validate(spec)?;
    let crates = root.join("crates");
    let dir = match &spec.krate {
        Some(k) => crates.join(k),
        None => owner_of(&crates, family(&spec.id).unwrap_or_default())?,
    };
    let written = scaffold(spec, root, &dir)?;
    run_test(root, &package_name(&dir)?)?;
    Ok(written.to_vec())
}

/// Removes the temporary crate copy and restores `Cargo.lock` when dropped.
struct ProofGuard {
    dir: PathBuf,
    lock: PathBuf,
    lock_text: Option<Vec<u8>>,
}

impl Drop for ProofGuard {
    fn drop(&mut self) {
        if let Err(e) = std::fs::remove_dir_all(&self.dir) {
            tracing::warn!(error = %e, "temporary rule crate not removed");
        }
        match &self.lock_text {
            Some(bytes) => {
                if let Err(e) = std::fs::write(&self.lock, bytes) {
                    tracing::warn!(error = %e, "Cargo.lock not restored");
                }
            }
            None => {
                if let Err(e) = std::fs::remove_file(&self.lock) {
                    tracing::warn!(error = %e, "could not remove the proof lock file");
                }
            }
        }
    }
}

/// The scaffold the CI step proves: one universal and one language rule, both scopes.
fn proof_specs() -> [RuleSpec; 2] {
    let base = RuleSpec {
        id: "SCOPE991".to_owned(),
        slug: "scaffold-universal".to_owned(),
        applies: Applies::Universal,
        scope: Scope::Repo,
        needs: Vec::new(),
        krate: None,
        host: None,
    };
    let lang = RuleSpec {
        id: "SCOPE992".to_owned(),
        slug: "scaffold-language".to_owned(),
        applies: Applies::Languages(vec!["Rust".to_owned(), "Python".to_owned()]),
        scope: Scope::File,
        ..base.clone()
    };
    [base, lang]
}

/// Remove `dir` and everything under it; a missing directory is already clean.
fn clear_dir(dir: &Path) -> Result<(), NewRuleError> {
    match std::fs::remove_dir_all(dir) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(io(dir)(e)),
        _ => Ok(()),
    }
}

/// The proof crate's manifest text with its package renamed to `proof_name`.
fn proof_manifest(source: &Path, proof_name: &str) -> Result<String, NewRuleError> {
    let manifest = std::fs::read_to_string(source.join("Cargo.toml")).map_err(io(source))?;
    Ok(manifest.replacen(
        &format!("name = \"{PROVE_CRATE}\""),
        &format!("name = \"{proof_name}\""),
        1,
    ))
}

/// Copy `PROVE_CRATE` under `root` to a renamed temporary member; returns the new package name.
fn copy_proof_crate(root: &Path) -> Result<String, NewRuleError> {
    let crates = root.join("crates");
    let (source, copy) = (crates.join(PROVE_CRATE), crates.join(PROVE_DIR));
    let proof_name = format!("{PROVE_CRATE}-newrule-proof");
    clear_dir(&copy)?;
    gob_fs::copy_tree(&source.join("src"), &copy.join("src")).map_err(io(&source))?;
    write_all(&[(
        copy.join("Cargo.toml"),
        proof_manifest(&source, &proof_name)?,
    )])?;
    Ok(proof_name)
}

/// Scaffold the proof rules into the staged copy.
fn scaffold_proof(root: &Path) -> Result<(), NewRuleError> {
    let copy = root.join("crates").join(PROVE_DIR);
    proof_specs()
        .iter()
        .try_for_each(|spec| scaffold(spec, root, &copy).map(drop))?;
    tracing::info!("scaffold written into the temporary copy");
    Ok(())
}

/// Stage the proof crate and scaffold the proof rules into it; returns the new package name.
fn stage_proof(root: &Path) -> Result<String, NewRuleError> {
    copy_proof_crate(root).and_then(|name| scaffold_proof(root).map(|()| name))
}

/// A guard that restores the tree when dropped, taking the `Cargo.lock` snapshot now.
fn proof_guard(root: &Path) -> ProofGuard {
    let lock = root.join("Cargo.lock");
    ProofGuard {
        dir: root.join("crates").join(PROVE_DIR),
        lock_text: std::fs::read(&lock).ok(),
        lock,
    }
}

/// [`prove`] with the compile-and-test step injected, restoring the tree afterwards.
fn prove_with(
    root: &Path,
    test: impl FnOnce(&Path, &str) -> Result<(), NewRuleError>,
) -> Result<(), NewRuleError> {
    let _guard = proof_guard(root);
    let name = stage_proof(root)?;
    test(root, &name)
}

/// Prove the scaffold: copy `PROVE_CRATE` to a temporary workspace member, scaffold a universal and
/// a language rule into it, then compile and test it. The real tree is left byte-identical.
///
/// # Errors
/// [`NewRuleError`] when the copy, the scaffold or the compile and test fails.
pub fn prove(root: &Path) -> Result<(), NewRuleError> {
    prove_with(root, run_test)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec(applies: Applies, scope: Scope) -> RuleSpec {
        RuleSpec {
            id: "COV007".to_owned(),
            slug: "untested-thing".to_owned(),
            applies,
            scope,
            needs: vec!["TestItems".to_owned(), "Visibility".to_owned()],
            krate: None,
            host: None,
        }
    }

    // frob:tests crates/gob-dev/src/new_rule.rs::validate
    #[test]
    fn validate_rejects_a_bad_id_slug_or_name() {
        let ok = spec(Applies::Universal, Scope::Repo);
        assert!(validate(&ok).is_ok());
        let bad_id = RuleSpec {
            id: "cov7".to_owned(),
            ..ok.clone()
        };
        assert!(matches!(validate(&bad_id), Err(NewRuleError::BadId(_))));
        let bad_slug = RuleSpec {
            slug: "Not_Kebab".to_owned(),
            ..ok.clone()
        };
        assert!(matches!(validate(&bad_slug), Err(NewRuleError::BadSlug(_))));
        let bad_need = RuleSpec {
            needs: vec!["not a name".to_owned()],
            ..ok
        };
        assert!(matches!(validate(&bad_need), Err(NewRuleError::BadName(_))));
    }

    // frob:tests crates/gob-dev/src/new_rule.rs::render
    #[test]
    fn render_universal_repo_names_every_required_field_and_page_section() {
        let r = render(
            &spec(Applies::Universal, Scope::Repo),
            "CovHost",
            "crate::host::CovHost",
            "0.1.0",
        );
        assert!(r.rs.contains("applies = universal(needs = [TestItems, Visibility]"));
        assert!(r.rs.contains("impl<P: ?Sized + CovHost> RepoRule<P> for Cov007"));
        assert!(r.rs.contains("since = \"0.1.0\""));
        assert!(r.md.contains("<!-- mdtest: rule=COV007 -->\n# COV007 untested-thing"));
        for section in ["What it does", "Why it matters", "Remedy", "Examples"] {
            assert!(r.md.contains(&format!("## {section}")));
        }
        assert!(r.md.contains("expect=fire") && r.md.contains("expect=clean"));
    }

    // frob:tests crates/gob-dev/src/new_rule.rs::render
    #[test]
    fn render_language_file_lists_the_languages() {
        let r = render(
            &spec(
                Applies::Languages(vec!["Rust".to_owned(), "Python".to_owned()]),
                Scope::File,
            ),
            "H",
            "crate::host::H",
            "0.1.0",
        );
        assert!(r.rs.contains("applies = languages(Rust, Python; needs ="));
        assert!(r.rs.contains("FileRule<P> for Cov007"));
        assert!(r.md.contains("```rust expect=fire"));
    }

    // frob:tests crates/gob-dev/src/new_rule.rs::scaffold
    #[test]
    fn scaffold_writes_two_files_and_refuses_to_overwrite() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        std::fs::write(
            root.join("Cargo.toml"),
            "[workspace]\n[workspace.package]\nversion = \"1.2.3\"\n",
        )
        .unwrap();
        let rules = root.join("crates/demo/src/rules");
        std::fs::create_dir_all(&rules).unwrap();
        std::fs::write(rules.join("mod.rs"), "").unwrap();
        std::fs::write(
            rules.join("old001.rs"),
            "use crate::host::DemoHost;\n#[rule(\n    id = \"OLD001\",\n    scope = File,\n    host = DemoHost,\n)]\npub struct Old001;\n",
        )
        .unwrap();
        let dir = root.join("crates/demo");
        let s = spec(Applies::Universal, Scope::File);
        let [rs, md] = scaffold(&s, root, &dir).unwrap();
        assert!(
            std::fs::read_to_string(rs)
                .unwrap()
                .contains("use crate::host::DemoHost;")
        );
        assert!(md.is_file());
        assert!(matches!(
            scaffold(&s, root, &dir),
            Err(NewRuleError::Exists(_))
        ));
    }

    // frob:tests crates/gob-dev/src/new_rule.rs::prove
    #[test]
    fn prove_scaffolds_both_kinds_then_restores_the_tree() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        std::fs::write(
            root.join("Cargo.toml"),
            "[workspace]\n[workspace.package]\nversion = \"1.2.3\"\n",
        )
        .unwrap();
        let krate = root.join("crates").join(PROVE_CRATE);
        let rules = krate.join("src/rules");
        std::fs::create_dir_all(&rules).unwrap();
        std::fs::write(
            krate.join("Cargo.toml"),
            format!("[package]\nname = \"{PROVE_CRATE}\"\n"),
        )
        .unwrap();
        std::fs::write(rules.join("mod.rs"), "").unwrap();
        std::fs::write(
            rules.join("old001.rs"),
            "use crate::host::DemoHost;\n#[rule(\n    id = \"OLD001\",\n    scope = File,\n    host = DemoHost,\n)]\npub struct Old001;\n",
        )
        .unwrap();
        let seen = std::cell::Cell::new(false);
        prove_with(root, |r, name| {
            let copy = r.join("crates").join(PROVE_DIR).join("src/rules");
            assert_eq!(name, format!("{PROVE_CRATE}-newrule-proof"));
            assert!(copy.join("scope991.rs").is_file() && copy.join("scope992.md").is_file());
            seen.set(true);
            Ok(())
        })
        .unwrap();
        assert!(seen.get());
        assert!(!root.join("crates").join(PROVE_DIR).exists());
    }
}
