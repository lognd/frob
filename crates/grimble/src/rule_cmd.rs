//! `rule test`, `rule check`, `rule catalog`, `rule fmt` and `rule new`: thin verbs over `gob_plan::verbs`.

// frob:ticket 01M3ZX7FCFBJSWMTZGCQMW7215

use std::fmt::Write as _;
use std::path::Path;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_path::Shown;
use gob_plan::verbs::catalog::{CatalogResult, lookup};
use gob_plan::verbs::check::{FileCheck, RuleCost, check_source};
use gob_plan::verbs::fmt::{Formatted, format_text};
use gob_plan::verbs::test::{FileTest, test_file};
use gob_plan::verbs::{Diag, discover_rules};
use schemars::JsonSchema;
use serde::Serialize;

/// The rule files to act on: the named paths, else every `.grl` file under the workspace root.
fn rule_files(
    ctx: &Context,
    paths: &[String],
) -> Result<(std::path::PathBuf, Vec<String>), CliError> {
    if paths.is_empty() {
        let root = gob_product::workspace::locate_root(crate::PRODUCT, &ctx.cwd);
        let found = discover_rules(&root, &root)
            .map_err(|e| CliError::internal(format!("cannot search for .grl files: {e}")))?;
        Ok((root, found))
    } else {
        let mut v = paths.to_vec();
        v.sort();
        v.dedup();
        Ok((ctx.cwd.clone(), v))
    }
}

fn read_rule(base: &Path, path: &str) -> Result<String, CliError> {
    std::fs::read_to_string(base.join(path))
        .map_err(|e| CliError::Usage(format!("cannot read rule file {path}: {e}")))
}

/// The optional positional rule file list shared by the rule verbs.
#[derive(Debug, Clone, clap::Args)]
struct PathsArg {
    #[arg(
        num_args = 0..,
        value_name = "PATH",
        help = "Rule files; default every .grl file under the workspace root"
    )]
    paths: Vec<String>,
}

fn gate<T: Serialize>(message: String, data: &T) -> CliError {
    match serde_json::to_value(data) {
        Ok(value) => CliError::Gate {
            message,
            data: value,
            warnings: Vec::new(),
        },
        Err(e) => CliError::internal(e),
    }
}

fn diag_lines(path: &str, diags: &[Diag]) -> Vec<String> {
    diags
        .iter()
        .map(|d| {
            format!(
                "{path}:{}:{}: {} {} {}",
                d.line, d.col, d.severity, d.code, d.message
            )
        })
        .collect()
}

/// Run the examples of rule files; exits 1 when any example fails.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule test",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct RuleTest {
    paths: Vec<String>,
}

/// Output of `rule test`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RuleTestData {
    /// One entry per rule file, in path order.
    pub files: Vec<FileTest>,
    /// Examples that passed.
    pub passed: usize,
    /// Examples that failed or could not run, plus files that did not compile.
    pub failed: usize,
}

/// `RuleTest` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RuleTestArgs {
    #[command(flatten)]
    paths: PathsArg,
}

impl Command for RuleTest {
    type Data = RuleTestData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<RuleTestArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RuleTestArgs>(m)?;
        Ok(Self {
            paths: a.paths.paths,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RuleTestData> {
        let (base, paths) = rule_files(ctx, &self.paths)?;
        let (mut files, mut rows) = (Vec::new(), Vec::new());
        let (mut passed, mut failed) = (0, 0);
        for path in paths {
            let result = test_file(&path, &read_rule(&base, &path)?);
            rows.extend(diag_lines(&path, &result.diagnostics));
            for e in &result.examples {
                rows.push(e.text());
                rows.extend(e.diff.lines().map(|l| format!("    {l}")));
                if e.status == "ok" {
                    passed += 1;
                } else {
                    failed += 1;
                }
            }
            if result.diagnostics.iter().any(|d| d.severity == "error") {
                failed += 1;
            }
            files.push(result);
        }
        let data = RuleTestData {
            files,
            passed,
            failed,
        };
        if failed > 0 {
            let message = format!("{failed} example(s) failed\n{}", rows.join("\n"));
            return Err(gate(message, &data));
        }
        Ok(Payload::new(data).with_rendered(rows))
    }
}

/// Compile rule files and print each rule's cost class and prefilter; exits 1 on a compile error.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule check",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct RuleCheck {
    paths: Vec<String>,
}

/// Output of `rule check`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RuleCheckData {
    /// One entry per rule file, in path order.
    pub files: Vec<FileCheck>,
}

/// `RuleCheck` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RuleCheckArgs {
    #[command(flatten)]
    paths: PathsArg,
}

impl Command for RuleCheck {
    type Data = RuleCheckData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<RuleCheckArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RuleCheckArgs>(m)?;
        Ok(Self {
            paths: a.paths.paths,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RuleCheckData> {
        let (base, paths) = rule_files(ctx, &self.paths)?;
        let (mut files, mut rows) = (Vec::new(), Vec::new());
        for path in paths {
            let result = check_source(&path, &read_rule(&base, &path)?);
            rows.extend(diag_lines(&path, &result.diagnostics));
            rows.extend(result.rules.iter().map(RuleCost::text));
            files.push(result);
        }
        let data = RuleCheckData { files };
        if data.files.iter().any(|f| !f.ok()) {
            return Err(gate(
                format!("rule files do not compile\n{}", rows.join("\n")),
                &data,
            ));
        }
        Ok(Payload::new(data).with_rendered(rows))
    }
}

/// Print a catalog word (kind, verb or flag), or list them all; an unknown word gets a suggestion.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule catalog",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, usage, internal)
)]
pub struct RuleCatalog {
    word: Option<String>,
}

/// `RuleCatalog` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct CatalogArgs {
    #[arg(value_name = "WORD", help = "The word to look up; default list all")]
    word: Option<String>,
}

impl Command for RuleCatalog {
    type Data = CatalogResult;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<CatalogArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<CatalogArgs>(m)?;
        Ok(Self { word: a.word })
    }

    fn run(&self, _ctx: &Context) -> Outcome<CatalogResult> {
        let result = lookup(self.word.as_deref());
        if result.entries.is_empty() {
            let word = self.word.as_deref().unwrap_or_default();
            let message = match &result.did_you_mean {
                Some(near) => format!("unknown catalog word `{word}`; did you mean `{near}`?"),
                None => format!("unknown catalog word `{word}`"),
            };
            return Err(gate(message, &result));
        }
        let rows = result
            .entries
            .iter()
            .map(|e| {
                let mut row = format!("{:<5} {:<14} {}", e.class, e.word, e.summary);
                for f in &e.fields {
                    let _ = write!(
                        row,
                        "
        .{} ({}) e.g. {}",
                        f.name, f.ty, f.example
                    );
                }
                row
            })
            .collect();
        Ok(Payload::new(result).with_rendered(rows))
    }
}

/// Rewrite rule files to the canonical layout; `--check` only reports and exits 1 on a difference.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule fmt",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct RuleFmt {
    check: bool,
    paths: Vec<String>,
}

/// Output of `rule fmt`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RuleFmtData {
    /// True under `--check` (nothing was written).
    pub check: bool,
    /// Files examined.
    pub files: usize,
    /// Files whose text is not canonical (rewritten unless `--check`).
    pub rewritten: Vec<String>,
    /// Files fmt could not format, with the reason.
    pub skipped: Vec<String>,
}

/// `RuleFmt` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct FmtArgs {
    #[arg(
        long,
        help = "Report non-canonical files and exit 1 instead of rewriting them"
    )]
    check: bool,
    #[command(flatten)]
    paths: PathsArg,
}

impl Command for RuleFmt {
    type Data = RuleFmtData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<FmtArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<FmtArgs>(m)?;
        Ok(Self {
            check: a.check,
            paths: a.paths.paths,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RuleFmtData> {
        let (base, paths) = rule_files(ctx, &self.paths)?;
        let mut data = RuleFmtData {
            check: self.check,
            files: paths.len(),
            rewritten: Vec::new(),
            skipped: Vec::new(),
        };
        for path in &paths {
            match format_text(path, &read_rule(&base, path)?) {
                Formatted::Unchanged => {}
                Formatted::Skipped(why) => data.skipped.push(format!("{path}: {why}")),
                Formatted::Changed(text) => {
                    data.rewritten.push(path.clone());
                    if !self.check {
                        std::fs::write(base.join(path), text)
                            .map_err(|e| CliError::internal(format!("cannot write {path}: {e}")))?;
                        tracing::info!(%path, "rule file formatted");
                    }
                }
            }
        }
        if self.check && (!data.rewritten.is_empty() || !data.skipped.is_empty()) {
            let message = format!(
                "{} file(s) not canonical, {} file(s) not formattable: {}",
                data.rewritten.len(),
                data.skipped.len(),
                data.rewritten
                    .iter()
                    .chain(&data.skipped)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            return Err(gate(message, &data));
        }
        let skipped = data.skipped.clone();
        let already = data.rewritten.is_empty();
        let mut payload = Payload::new(data).with_already(already);
        payload.warnings = skipped;
        Ok(payload)
    }
}

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W

/// Scaffold `rules/ID.grl` from the code at `FILE:LINE`; `--print` shows it without writing.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule new",
    product = "grimble",
    exits(ok, refused, usage, internal)
)]
pub struct RuleNew {
    id: String,
    location: String,
    print: bool,
}

/// Output of `rule new`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RuleNewData {
    /// Where the rule file is (or would be, under `--print`), relative to the workspace root.
    pub path: String,
    /// True when the file was written.
    pub written: bool,
    /// The code line the rule was built from.
    pub from: String,
    /// The snippet the rule looks for.
    pub snippet: String,
    /// The scaffolded text.
    pub text: String,
}

/// `RuleNew` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct NewArgs {
    #[arg(required = true, value_name = "ID", help = "Rule id, such as NOPE001")]
    id: String,
    #[arg(
        long = "from",
        required = true,
        value_name = "FILE:LINE",
        help = "The code to build the rule from"
    )]
    location: String,
    #[arg(long, help = "Show the scaffold without writing rules/ID.grl")]
    print: bool,
}

impl Command for RuleNew {
    type Data = RuleNewData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<NewArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<NewArgs>(m)?;
        Ok(Self {
            id: a.id,
            location: a.location,
            print: a.print,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RuleNewData> {
        let usage = |e: gob_plan::verbs::new::NewError| CliError::Usage(e.to_string());
        let (file, line) = gob_plan::verbs::new::parse_location(&self.location).map_err(usage)?;
        let source = std::fs::read_to_string(ctx.cwd.join(file))
            .map_err(|e| CliError::Usage(format!("cannot read {file}: {e}")))?;
        let rule = gob_plan::verbs::new::scaffold(&self.id, file, line, &source).map_err(usage)?;
        let root = gob_product::workspace::locate_root(crate::PRODUCT, &ctx.cwd);
        let target = root.join(&rule.path);
        if !self.print {
            if target.exists() {
                return Err(CliError::Usage(format!("{} already exists", rule.path)));
            }
            if let Some(dir) = target.parent() {
                std::fs::create_dir_all(dir).map_err(|e| {
                    CliError::internal(format!("cannot create {}: {e}", Shown::of(dir)))
                })?;
            }
            std::fs::write(&target, &rule.text)
                .map_err(|e| CliError::internal(format!("cannot write {}: {e}", rule.path)))?;
            tracing::info!(path = %rule.path, "rule scaffolded");
        }
        Ok(Payload::new(RuleNewData {
            path: rule.path,
            written: !self.print,
            from: rule.from,
            snippet: rule.snippet,
            text: rule.text,
        }))
    }
}

// frob:ticket 01M4PT1A52YR3QV6PYSGNC7N38

/// Trace rule `ID` at `FILE:LINE`: the candidates there and the first clause that fails.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule why",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct RuleWhy {
    id: String,
    location: String,
}

/// `RuleWhy` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct WhyArgs {
    #[arg(required = true, value_name = "ID", help = "Rule id, such as NOPE001")]
    id: String,
    #[arg(
        required = true,
        value_name = "FILE:LINE",
        help = "The source location to trace the rule at"
    )]
    location: String,
}

impl Command for RuleWhy {
    type Data = gob_plan::why::Why;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<WhyArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<WhyArgs>(m)?;
        Ok(Self {
            id: a.id,
            location: a.location,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<gob_plan::why::Why> {
        let (file, line) = gob_plan::verbs::new::parse_location(&self.location)
            .map_err(|e| CliError::Usage(e.to_string()))?;
        let line = u32::try_from(line)
            .map_err(|_| CliError::Usage(format!("line {line} is out of range")))?;
        let lang = file.rsplit_once('.').map_or("", |(_, ext)| ext);
        let text = std::fs::read_to_string(ctx.cwd.join(file))
            .map_err(|e| CliError::Usage(format!("cannot read {file}: {e}")))?;
        let (base, paths) = rule_files(ctx, &[])?;
        for path in paths {
            let src = read_rule(&base, &path)?;
            match gob_plan::verbs::why::why_source(&path, &src, &self.id, lang, &text, line) {
                Err(gob_plan::verbs::why::WhyVerbError::NoRule(_)) => {}
                Err(e) => return Err(CliError::Usage(format!("{path}: {e}"))),
                Ok(why) => {
                    tracing::debug!(rule = %self.id, %path, line, "rule why traced");
                    let rows = why.lines();
                    return Ok(Payload::new(why).with_rendered(rows));
                }
            }
        }
        Err(CliError::Usage(format!(
            "no rule `{}` in any .grl file under the workspace root",
            self.id
        )))
    }
}
