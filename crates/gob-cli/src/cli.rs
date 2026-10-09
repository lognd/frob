//! The clap root: global flags, verb registration, dispatch and exit codes.

use std::ffi::OsString;
use std::path::{Path, PathBuf};

use clap::error::{ContextKind, ContextValue, ErrorKind};
use clap::{Arg, ArgAction, ArgMatches};
use gob_diagnostics::{ColorChoice, ExitCode, is_tty};

use crate::command::{Command, Registered};
use crate::context::{ColorMode, Context, FormatChoice};
use crate::error::CliError;
use crate::render::{self, Execution};
use crate::schema_cmd::SchemaCmd;
use crate::serve::ServeCmd;

/// A product's command-line root: global flags plus its registered verbs.
pub struct Cli {
    pub(crate) product: &'static str,
    pub(crate) version: &'static str,
    pub(crate) verbs: Vec<Registered>,
    // frob:ticket 01M40FXV09GYGBH9YZZANDZXZ4
    guard: Option<Guard>,
}

/// A product's precondition check, run after parsing and before a verb: `(verb path, context)`.
pub type Guard = fn(&str, &Context) -> Result<(), CliError>;

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
            guard: None,
        }
        .register::<SchemaCmd>()
        .register::<ServeCmd>()
    }

    /// Run `guard` before every verb (not `--schema`); an `Err` stops the verb and is rendered.
    #[must_use]
    pub fn with_guard(mut self, guard: Guard) -> Self {
        self.guard = Some(guard);
        self
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
        if let Some(cwd) = &exec.serve_cwd {
            tracing::info!(product = self.product, cwd = %cwd.display(), "serve: MCP over stdio");
            let stdin = std::io::stdin();
            let mut stdout = std::io::stdout();
            return match self.serve_mcp(stdin.lock(), &mut stdout, cwd) {
                Ok(()) => 0,
                Err(e) => {
                    tracing::error!(error = %e, "serve: transport failed");
                    ExitCode::Internal.code()
                }
            };
        }
        render::emit(&exec);
        exec.exit
    }

    // frob:ticket 01M40YQZF4422S88TN6992AN0Q
    /// Every verb path with the long flags it accepts (its own plus the global ones).
    ///
    /// Lets tests and doc checks verify that a quoted `product verb --flag` exists.
    pub fn verb_flags(
        &self,
    ) -> std::collections::BTreeMap<String, std::collections::BTreeSet<String>> {
        let root = self.build(false);
        let globals: std::collections::BTreeSet<String> = root
            .get_arguments()
            .filter_map(|a| a.get_long().map(str::to_owned))
            .chain(["schema", "help", "version"].map(str::to_owned))
            .collect();
        let mut out = std::collections::BTreeMap::new();
        let mut stack: Vec<(String, &clap::Command)> = vec![(String::new(), &root)];
        while let Some((path, cmd)) = stack.pop() {
            let subs: Vec<_> = cmd.get_subcommands().collect();
            if subs.is_empty() {
                let mut flags = globals.clone();
                flags.extend(
                    cmd.get_arguments()
                        .filter_map(|a| a.get_long().map(str::to_owned)),
                );
                out.insert(path, flags);
                continue;
            }
            for sub in subs {
                let next = if path.is_empty() {
                    sub.get_name().to_owned()
                } else {
                    format!("{path} {}", sub.get_name())
                };
                stack.push((next, sub));
            }
        }
        tracing::debug!(verbs = out.len(), "verb flag table built");
        out
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
                .help("Output format: json, text, md (markdown; refused on verbs without a markdown view), or auto (json when stdout is not a terminal)"),
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

    /// Build the clap tree: global flags, one nested subcommand per verb-path word.
    ///
    /// `relaxed` drops every verb argument's `required`, so `--schema` can be
    /// answered without the verb's positionals.
    pub(crate) fn build(&self, relaxed: bool) -> clap::Command {
        let mut root = clap::Command::new(self.product)
            .version(self.version)
            .bin_name(self.product)
            .infer_long_args(false)
            .infer_subcommands(false)
            .subcommand_required(true)
            .arg_required_else_help(true)
            .args(Self::global_args());
        let mut tree = Node::default();
        for v in &self.verbs {
            tree.insert(v.meta.verb, v);
        }
        for (name, node) in tree.children {
            root = root.subcommand(node.command(name, relaxed));
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
        let relaxed = wants_schema(&full);
        let matches = match self.build(relaxed).try_get_matches_from(&full) {
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
        if path == ServeCmd::VERB && !leaf.get_flag("schema") {
            tracing::debug!(cwd = %ctx.cwd.display(), "serve requested");
            return Execution::serving(ctx.cwd.clone());
        }
        if leaf.get_flag("schema") {
            let text = serde_json::to_string_pretty(&(verb.schema)()).unwrap_or_default();
            return Execution::out(format!("{text}\n"));
        }
        if ctx.markdown() && !verb.meta.markdown {
            let supported = crate::meta::markdown_verbs(self.product);
            tracing::debug!(verb = %path, "--format md refused: no markdown view");
            let err = CliError::Usage(format!(
                "`{path}` has no markdown view; --format md is supported by: {}",
                if supported.is_empty() {
                    "no verb".to_owned()
                } else {
                    supported.join(", ")
                }
            ));
            return render::failure(Some(&dotted), &err, false);
        }
        let span = tracing::info_span!("cli.verb", verb = %dotted);
        let _enter = span.enter();
        if let Some(guard) = self.guard
            && let Err(err) = guard(&path, &ctx)
        {
            tracing::debug!(error = %err, "guard refused the verb");
            return render::failure(Some(&dotted), &err, ctx.json);
        }
        let mut exec = match (verb.run)(leaf, &ctx) {
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
        };
        if let Some(note) = verb.meta.deprecation_note(self.product) {
            tracing::debug!(verb = %path, "deprecated alias used");
            exec.stderr.insert_str(0, &format!("{note}\n"));
        }
        exec
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
            FormatChoice::Text | FormatChoice::Md => false,
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
            format: match (format, json) {
                (FormatChoice::Md, _) => FormatChoice::Md,
                (_, true) => FormatChoice::Json,
                (_, false) => FormatChoice::Text,
            },
            verbosity,
            quiet: leaf.get_flag("quiet"),
            dry_run,
            clock: std::sync::Arc::new(gob_time::SystemClock::pin()),
        })
    }

    /// Map a clap parse error: help/version succeed, everything else is usage.
    fn parse_failure(&self, e: &clap::Error, argv: &[OsString]) -> Execution {
        if matches!(e.kind(), ErrorKind::DisplayHelp | ErrorKind::DisplayVersion) {
            return Execution::out(e.to_string());
        }
        let (message, remedy) = usage_parts(e, self.product);
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

/// Strings held by a clap context entry, whether it carries one value or a list.
fn context_strings(e: &clap::Error, kind: ContextKind) -> Vec<String> {
    match e.get(kind) {
        Some(ContextValue::Strings(s)) => s.clone(),
        Some(ContextValue::String(s)) => vec![s.clone()],
        Some(ContextValue::StyledStr(s)) => vec![s.to_string()],
        _ => Vec::new(),
    }
}

/// Quote each name as `'name'` and join with commas.
fn quoted(names: &[String]) -> String {
    names
        .iter()
        .map(|n| format!("'{n}'"))
        .collect::<Vec<_>>()
        .join(", ")
}

/// Build the one-line usage message and its remedy from clap's structured error, not its rendering.
fn usage_parts(e: &clap::Error, product: &str) -> (String, Option<String>) {
    let arg = context_strings(e, ContextKind::InvalidArg);
    let value = context_strings(e, ContextKind::InvalidValue);
    let valid = context_strings(e, ContextKind::ValidValue);
    let sub = context_strings(e, ContextKind::InvalidSubcommand);
    let message = match e.kind() {
        ErrorKind::MissingRequiredArgument if !arg.is_empty() => {
            format!("missing required arguments: {}", arg.join(", "))
        }
        ErrorKind::MissingSubcommand | ErrorKind::DisplayHelpOnMissingArgumentOrSubcommand => {
            "a subcommand is required".to_owned()
        }
        ErrorKind::InvalidSubcommand if !sub.is_empty() => {
            format!("unrecognized subcommand {}", quoted(&sub))
        }
        ErrorKind::UnknownArgument if !arg.is_empty() => {
            format!("unexpected argument {} found", quoted(&arg))
        }
        ErrorKind::InvalidValue | ErrorKind::ValueValidation
            if !arg.is_empty() && !value.is_empty() =>
        {
            let mut m = format!("invalid value {} for '{}'", quoted(&value), arg.join(" "));
            if !valid.is_empty() {
                m = format!("{m}; valid values: {}", valid.join(", "));
            }
            m
        }
        _ => rendered_summary(e),
    };
    // A suggested verb is itself the remedy: the exact command to run instead.
    let subs = context_strings(e, ContextKind::SuggestedSubcommand);
    if let Some(s) = subs.first() {
        return (message, Some(format!("{product} {s}")));
    }
    let mut hints = Vec::new();
    let args = context_strings(e, ContextKind::SuggestedArg);
    if let Some(s) = args.first() {
        hints.push(format!("did you mean `{s}`?"));
    }
    let vals = context_strings(e, ContextKind::SuggestedValue);
    if let Some(s) = vals.first() {
        hints.push(format!("did you mean `{s}`?"));
    }
    let mut usage = context_strings(e, ContextKind::Usage);
    if usage.is_empty() {
        usage = e
            .to_string()
            .lines()
            .filter(|l| l.starts_with("Usage:"))
            .map(str::to_owned)
            .collect();
    }
    if let Some(u) = usage.first() {
        let line = u.trim().strip_prefix("Usage:").unwrap_or(u.trim()).trim();
        let first = line.lines().next().unwrap_or(line).trim();
        hints.push(format!("usage: {first}"));
    }
    let subcommands = context_strings(e, ContextKind::ValidSubcommand);
    if !subcommands.is_empty() {
        hints.push(format!("subcommands: {}", subcommands.join(", ")));
    }
    let remedy = (!hints.is_empty()).then(|| hints.join("; "));
    (message, remedy)
}

/// Fallback for error kinds without a structured form: the first paragraph of clap's text, on one line.
fn rendered_summary(e: &clap::Error) -> String {
    let full = e.to_string();
    let para: Vec<&str> = full
        .lines()
        .take_while(|l| !l.trim().is_empty())
        .map(str::trim)
        .collect();
    let joined = para.join(" ");
    joined.strip_prefix("error: ").unwrap_or(&joined).to_owned()
}

/// One word of the verb-path trie; a node is a verb (leaf) or a group of deeper words.
#[derive(Default)]
struct Node<'a> {
    verb: Option<&'a Registered>,
    children: Vec<(&'static str, Node<'a>)>,
}

impl<'a> Node<'a> {
    /// Add `v` under its space-separated path, keeping first-seen order.
    fn insert(&mut self, path: &'static str, v: &'a Registered) {
        let mut node = self;
        for word in path.split(' ') {
            let at = if let Some(i) = node.children.iter().position(|(w, _)| *w == word) {
                i
            } else {
                node.children.push((word, Node::default()));
                node.children.len() - 1
            };
            node = &mut node.children[at].1;
        }
        node.verb = Some(v);
    }

    /// The clap command for this word: a leaf when it is only a verb, else a group.
    fn command(self, name: &'static str, relaxed: bool) -> clap::Command {
        if self.children.is_empty() {
            let v = self
                .verb
                .unwrap_or_else(|| unreachable!("a leaf node holds a verb"));
            return leaf_command(name, v, relaxed);
        }
        let mut group = clap::Command::new(name)
            .about(format!("{name} commands"))
            .subcommand_required(true)
            .arg_required_else_help(true);
        for (child, node) in self.children {
            group = group.subcommand(node.command(child, relaxed));
        }
        group
    }
}

/// True when argv asks for a schema (a `--schema` before any `--` terminator).
fn wants_schema(argv: &[OsString]) -> bool {
    argv.iter()
        .skip(1)
        .take_while(|a| *a != "--")
        .any(|a| a == "--schema")
}

/// A leaf subcommand with the verb's flags and (if it opts in) `--dry-run`.
fn leaf_command(name: &'static str, v: &Registered, relaxed: bool) -> clap::Command {
    let mut cmd = clap::Command::new(name)
        .about(v.meta.summary)
        .hide(v.meta.deprecated_form().is_some());
    if v.meta.dry_run {
        cmd = cmd.arg(
            Arg::new("dry_run")
                .long("dry-run")
                .action(ArgAction::SetTrue)
                .help("Report what would change without changing it"),
        );
    }
    let cmd = (v.configure)(cmd);
    if relaxed {
        tracing::debug!(verb = v.meta.verb, "--schema: verb arguments made optional");
        return cmd.mut_args(|a| a.required(false));
    }
    cmd
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
