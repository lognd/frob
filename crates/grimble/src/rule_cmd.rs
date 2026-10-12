//! `rule test`, `rule check`, `rule catalog`, `rule fmt` and `rule new`: thin verbs over `gob_plan::verbs`.

// frob:ticket 01M3ZX7FCFBJSWMTZGCQMW7215

use std::fmt::Write as _;
use std::path::Path;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
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

fn paths_arg(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
    cmd.arg(
        Arg::new("paths")
            .num_args(0..)
            .value_name("PATH")
            .help("Rule files; default every .grl file under the workspace root"),
    )
}

fn paths_of(m: &ArgMatches) -> Vec<String> {
    m.get_many::<String>("paths")
        .map(|v| v.cloned().collect())
        .unwrap_or_default()
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

impl Command for RuleTest {
    type Data = RuleTestData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        paths_arg(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self { paths: paths_of(m) })
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

impl Command for RuleCheck {
    type Data = RuleCheckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        paths_arg(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self { paths: paths_of(m) })
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

impl Command for RuleCatalog {
    type Data = CatalogResult;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("word")
                .value_name("WORD")
                .help("The word to look up; default list all"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            word: m.get_one::<String>("word").cloned(),
        })
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

impl Command for RuleFmt {
    type Data = RuleFmtData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        paths_arg(
            cmd.arg(
                Arg::new("check")
                    .long("check")
                    .action(ArgAction::SetTrue)
                    .help("Report non-canonical files and exit 1 instead of rewriting them"),
            ),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            check: m.get_flag("check"),
            paths: paths_of(m),
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

impl Command for RuleNew {
    type Data = RuleNewData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("id")
                .required(true)
                .value_name("ID")
                .help("Rule id, such as NOPE001"),
        )
        .arg(
            Arg::new("location")
                .long("from")
                .required(true)
                .value_name("FILE:LINE")
                .help("The code to build the rule from"),
        )
        .arg(
            Arg::new("print")
                .long("print")
                .action(ArgAction::SetTrue)
                .help("Show the scaffold without writing rules/ID.grl"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let get = |k: &str| m.get_one::<String>(k).cloned().unwrap_or_default();
        Ok(Self {
            id: get("id"),
            location: get("location"),
            print: m.get_flag("print"),
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
                    CliError::internal(format!("cannot create {}: {e}", dir.display()))
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
