//! The clap root: global flags, verb registration, dispatch and exit codes.

use std::ffi::OsString;
use std::path::{Path, PathBuf};

use clap::error::{ContextKind, ContextValue, ErrorKind};
use clap::{Arg, ArgAction, ArgMatches};
use gob_diagnostics::{ColorChoice, is_tty};

use crate::command::{Command, Registered};
use crate::context::{ColorMode, Context, FormatChoice};
use crate::error::CliError;
use crate::render::{self, Execution};
use crate::schema_cmd::SchemaCmd;

/// A product's command-line root: global flags plus its registered verbs.
pub struct Cli {
    product: &'static str,
    version: &'static str,
    verbs: Vec<Registered>,
}

impl std::fmt::Debug for Cli {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Cli")
            .field("product", &self.product)
            .field(
                "verbs",
                &self.verbs.iter().map(|v| v.meta.verb).collect::<Vec<_>>(),
            )
            .finish_non_exhaustive()
    }
}

impl Cli {
    /// A root for `product` with the built-in `schema` verb registered.
    pub fn new(product: &'static str, version: &'static str) -> Self {
        tracing::debug!(product, version, "cli root created");
        Self {
            product,
            version,
            verbs: Vec::new(),
        }
        .register::<SchemaCmd>()
    }

    /// Register verb `C` under the path declared in its metadata.
    #[must_use]
    pub fn register<C: Command>(mut self) -> Self {
        let verb = Registered::of::<C>();
        tracing::debug!(verb = verb.meta.verb, "verb registered");
        self.verbs.push(verb);
        self
    }

    /// Parse `args` (the program name is added for you), run, write the result, return the exit code.
    pub fn run<I, T>(&self, args: I) -> i32
    where
        I: IntoIterator<Item = T>,
        T: Into<OsString>,
    {
        let exec = self.execute(args, None, true);
        render::emit(&exec);
        exec.exit
    }

    /// Report a failure that happened before dispatch (exit 4) and return the code.
    pub fn fail_startup(&self, error: impl Into<Box<dyn std::error::Error + Send + Sync>>) -> i32 {
        let argv: Vec<OsString> = std::env::args_os().collect();
        let exec = render::failure(None, &CliError::internal(error), sniff_json(&argv));
        render::emit(&exec);
        exec.exit
    }

    fn global_args() -> Vec<Arg> {
        vec![
            Arg::new("format")
                .long("format")
                .value_name("FORMAT")
                .value_parser(clap::value_parser!(FormatChoice))
                .default_value("auto")
                .global(true)
                .help("Output format: json, text, or auto (json when stdout is not a terminal)"),
            Arg::new("json")
                .long("json")
                .action(ArgAction::SetTrue)
                .global(true)
                .help("Alias of --format json"),
            Arg::new("text")
                .long("text")
                .action(ArgAction::SetTrue)
                .global(true)
                .help("Alias of --format text"),
            Arg::new("quiet")
                .short('q')
                .long("quiet")
                .action(ArgAction::SetTrue)
                .global(true)
                .help("Suppress text output on success"),
            Arg::new("verbose")
                .short('v')
                .long("verbose")
                .action(ArgAction::Count)
                .global(true)
                .help("More logging on stderr (-v info, -vv debug, -vvv trace)"),
            Arg::new("color")
                .long("color")
                .value_name("WHEN")
                .value_parser(clap::value_parser!(ColorMode))
                .default_value("auto")
                .global(true)
                .help("Color text output: auto, always, never"),
            Arg::new("cwd")
                .long("cwd")
                .value_name("DIR")
                .value_parser(clap::value_parser!(PathBuf))
                .global(true)
                .help("Run as if started in DIR"),
            Arg::new("schema")
                .long("schema")
                .action(ArgAction::SetTrue)
                .global(true)
                .help("Print the JSON schema of the verb's data and exit"),
        ]
    }

    /// Build the clap tree: global flags, one subcommand per verb path.
    fn build(&self) -> clap::Command {
        let mut root = clap::Command::new(self.product)
            .version(self.version)
            .bin_name(self.product)
            .infer_long_args(false)
            .infer_subcommands(false)
            .subcommand_required(true)
            .arg_required_else_help(true)
            .args(Self::global_args());
        // Groups keep first-seen order; a verb path has one or two words.
        let mut groups: Vec<(&'static str, Vec<&Registered>)> = Vec::new();
        for v in &self.verbs {
            let head = v.meta.verb.split(' ').next().unwrap_or(v.meta.verb);
            match groups.iter_mut().find(|(g, _)| *g == head) {
                Some((_, members)) => members.push(v),
                None => groups.push((head, vec![v])),
            }
        }
        for (head, members) in groups {
            if let [single] = members.as_slice()
                && single.meta.verb == head
            {
                root = root.subcommand(leaf_command(head, single));
                continue;
            }
            let mut group = clap::Command::new(head)
                .about(format!("{head} commands"))
                .subcommand_required(true)
                .arg_required_else_help(true);
            for v in members {
                let tail = v.meta.verb.split_once(' ').map_or(v.meta.verb, |(_, t)| t);
                group = group.subcommand(leaf_command(tail, v));
            }
            root = root.subcommand(group);
        }
        root
    }

    /// The full pipeline without touching process streams.
    ///
    /// `default_cwd` replaces the process directory when `--cwd` is absent;
    /// `log` installs the global tracing subscriber (off for in-process tests).
    pub(crate) fn execute<I, T>(&self, args: I, default_cwd: Option<&Path>, log: bool) -> Execution
    where
        I: IntoIterator<Item = T>,
        T: Into<OsString>,
    {
        let mut full: Vec<OsString> = vec![OsString::from(self.product)];
        full.extend(args.into_iter().map(Into::into));
        let matches = match self.build().try_get_matches_from(&full) {
            Ok(m) => m,
            Err(e) => return self.parse_failure(&e, &full),
        };
        let (path, leaf) = leaf_of(&matches);
        let ctx = match self.context(leaf, default_cwd, log) {
            Ok(c) => c,
            Err(err) => return render::failure(None, &err, sniff_json(&full)),
        };
        let Some(verb) = self.verbs.iter().find(|v| v.meta.verb == path) else {
            let err = CliError::internal(format!("verb `{path}` parsed but not registered"));
            return render::failure(None, &err, ctx.json);
        };
        let dotted = path.replace(' ', ".");
        if leaf.get_flag("schema") {
            let text = serde_json::to_string_pretty(&(verb.schema)()).unwrap_or_default();
            return Execution::out(format!("{text}\n"));
        }
        let span = tracing::info_span!("cli.verb", verb = %dotted);
        let _enter = span.enter();
        match (verb.run)(leaf, &ctx) {
            Ok(erased) => {
                tracing::debug!(
                    findings = erased.findings.len(),
                    already = erased.already,
                    "verb ok"
                );
                render::success(&dotted, erased, ctx.json, ctx.quiet, ctx.color)
            }
            Err(err) => {
                tracing::debug!(error = %err, "verb failed");
                render::failure(Some(&dotted), &err, ctx.json)
            }
        }
    }

    /// Resolve global flags into a [`Context`] and install logging.
    fn context(
        &self,
        leaf: &ArgMatches,
        default_cwd: Option<&Path>,
        log: bool,
    ) -> Result<Context, CliError> {
        let format = match (leaf.get_flag("json"), leaf.get_flag("text")) {
            (true, true) => {
                return Err(CliError::Usage("--json and --text conflict".to_owned()));
            }
            (true, false) => FormatChoice::Json,
            (false, true) => FormatChoice::Text,
            (false, false) => leaf
                .get_one::<FormatChoice>("format")
                .copied()
                .unwrap_or(FormatChoice::Auto),
        };
        let json = match format {
            FormatChoice::Json => true,
            FormatChoice::Text => false,
            FormatChoice::Auto => !is_tty(&std::io::stdout()),
        };
        let color = match leaf
            .get_one::<ColorMode>("color")
            .copied()
            .unwrap_or(ColorMode::Auto)
        {
            ColorMode::Always => ColorChoice::Always,
            ColorMode::Never => ColorChoice::Never,
            ColorMode::Auto => {
                if is_tty(&std::io::stdout()) && std::env::var_os("NO_COLOR").is_none() {
                    ColorChoice::Always
                } else {
                    ColorChoice::Never
                }
            }
        };
        let verbosity = leaf.get_count("verbose");
        let cwd = resolve_cwd(leaf.get_one::<PathBuf>("cwd"), default_cwd)?;
        if log {
            match gob_log::init(self.product, verbosity, json) {
                Ok(()) => {}
                Err(gob_log::InitError::AlreadyInitialized(_)) => {
                    tracing::debug!("logging already initialised");
                }
                Err(e) => return Err(CliError::Usage(e.to_string())),
            }
        }
        let dry_run = leaf
            .try_get_one::<bool>("dry_run")
            .ok()
            .flatten()
            .copied()
            .unwrap_or(false);
        Ok(Context {
            cwd,
            color,
            json,
            verbosity,
            quiet: leaf.get_flag("quiet"),
            dry_run,
        })
    }

    /// Map a clap parse error: help/version succeed, everything else is usage.
    fn parse_failure(&self, e: &clap::Error, argv: &[OsString]) -> Execution {
        if matches!(e.kind(), ErrorKind::DisplayHelp | ErrorKind::DisplayVersion) {
            return Execution::out(e.to_string());
        }
        let full = e.to_string();
        let first = full.lines().next().unwrap_or_default();
        let message = first.strip_prefix("error: ").unwrap_or(first).to_owned();
        let remedy = match (
            e.get(ContextKind::SuggestedSubcommand),
            e.get(ContextKind::SuggestedArg),
        ) {
            (Some(ContextValue::Strings(s)), _) if !s.is_empty() => {
                Some(format!("{} {}", self.product, s[0]))
            }
            (_, Some(ContextValue::Strings(s))) if !s.is_empty() => Some(format!("use {}", s[0])),
            (_, Some(ContextValue::String(s))) => Some(format!("use {s}")),
            _ => None,
        };
        tracing::debug!(kind = ?e.kind(), "usage error");
        let mut err = gob_diagnostics::Refusal::new(
            "E-USAGE",
            gob_diagnostics::RefusalClass::UsageError,
            message,
        );
        if let Some(r) = remedy {
            err = err.with_remedy(r);
        }
        render::failure(None, &CliError::Refusal(err), sniff_json(argv))
    }
}

/// A leaf subcommand with the verb's flags and (if it opts in) `--dry-run`.
fn leaf_command(name: &'static str, v: &Registered) -> clap::Command {
    let mut cmd = clap::Command::new(name).about(v.meta.summary);
    if v.meta.dry_run {
        cmd = cmd.arg(
            Arg::new("dry_run")
                .long("dry-run")
                .action(ArgAction::SetTrue)
                .help("Report what would change without changing it"),
        );
    }
    (v.configure)(cmd)
}

/// Walk to the innermost subcommand; returns its space-joined path and matches.
fn leaf_of(matches: &ArgMatches) -> (String, &ArgMatches) {
    let mut names = Vec::new();
    let mut cur = matches;
    while let Some((name, sub)) = cur.subcommand() {
        names.push(name);
        cur = sub;
    }
    (names.join(" "), cur)
}

/// Absolute working directory from `--cwd`, the test default, or the process.
fn resolve_cwd(flag: Option<&PathBuf>, default_cwd: Option<&Path>) -> Result<PathBuf, CliError> {
    let process_dir = || std::env::current_dir().map_err(CliError::internal);
    let base = match default_cwd {
        Some(d) => d.to_path_buf(),
        None => process_dir()?,
    };
    let cwd = match flag {
        Some(p) if p.is_absolute() => p.clone(),
        Some(p) => base.join(p),
        None => base,
    };
    if cwd.is_dir() {
        Ok(cwd)
    } else {
        Err(CliError::Usage(format!(
            "--cwd {} is not a directory",
            cwd.display()
        )))
    }
}

/// Best-effort format choice from raw argv, for errors raised before parsing finishes.
fn sniff_json(argv: &[OsString]) -> bool {
    let mut json = None;
    let mut iter = argv.iter().filter_map(|a| a.to_str());
    while let Some(a) = iter.next() {
        match a {
            "--json" | "--format=json" => json = Some(true),
            "--text" | "--format=text" => json = Some(false),
            "--format" => match iter.next() {
                Some("json") => json = Some(true),
                Some("text") => json = Some(false),
                _ => {}
            },
            _ => {}
        }
    }
    json.unwrap_or_else(|| !is_tty(&std::io::stdout()))
}

/// Run `cli` in-process with `args` (the program name is added for you) as if started in `cwd`.
///
/// Returns `(exit code, stdout, stderr)` without touching the real streams or
/// installing a log subscriber; output defaults to JSON because the test
/// process's stdout is not a terminal.
pub fn run_for_test(cli: &Cli, args: &[&str], cwd: &Path) -> (i32, String, String) {
    let exec = cli.execute(args.iter().copied(), Some(cwd), false);
    (exec.exit, exec.stdout, exec.stderr)
}
