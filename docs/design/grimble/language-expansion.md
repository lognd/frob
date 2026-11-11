# Language expansion: ranked target set and per-language semantics

Status: draft
Owner: grimble
Decisions: none
Audience: contributor

Provenance: research deliverable of ticket ~49P22KK (alias T-1598,
cluster D2). It is the evidence base that later per-language adapter
batches read BEFORE writing any adapter: which languages, in what order,
with what grammar, what comment syntax carries a directive, and what
"public symbol" means in each. Nothing here changes code.

Research date: 2026-11-07. Sources were fetched on that date with
`curl`; every ranking number below is copied from the fetched page and
its URL is in section 9. Claims that were NOT fetched are labelled
`(unverified)` where they appear and are collected in section 8. The
rankings date quickly; a later batch that leans on a number should
re-fetch the page named in section 9.

## 1. What this document decides

1. The target set (section 3) and the weighting that produced it
   (section 2).
2. The grammar situation per target (section 4).
3. The comment forms that can carry a `frob:` directive, including the
   awkward ones (section 5).
4. The intended "public symbol" rule per language (section 6), stated
   before any adapter exists so adapter authors implement a rule rather
   than invent one.
5. The batch order (section 7), with the five languages the owner named
   (C#, Java, CUDA, Zig, Bash) first.

## 2. Method and where the rankings disagree

Five rankings were requested. What was actually obtained:

| Source | Obtained | Notes |
|---|---|---|
| TIOBE Index, November 2026 | top 50 table, full text | search-engine hit counts; rewards old languages with many pages |
| RedMonk, January 2026 run (published 2026-04-14) | top 20 plus the "watch" languages named in prose | GitHub pull requests plus Stack Overflow tags; RedMonk itself says the Stack Overflow axis and the 2025 H2 pull-request axis are both distorted this run |
| Stack Overflow Developer Survey 2025 | full "most used languages" list (all respondents, professional, learning) | self-reported use among respondents; 2026 edition fetched but its page exposes only the top 10 |
| Stack Overflow Developer Survey 2026 | top 10 only | JavaScript 62.0, SQL 58.4, HTML/CSS 58.2, Python 58.0, Bash/Shell 51.3, TypeScript 43.8, Java 27.6, C# 27.1, PowerShell 24.6, C++ 24.3 |
| GitHub Octoverse 2025 | contributor-growth table (top 5 rows) and prose | growth, not size; rank 1 is the largest absolute contributor gain, not the largest language |
| IEEE Spectrum Top Programming Languages 2025 | prose only | the ranking itself is an interactive widget that did not come through as text; only the narrative (Python first in both the "Spectrum" and "Jobs" rankings, JavaScript fell from third to sixth, SQL called out in Jobs) was read. No per-language IEEE numbers are used below |

The 2026 Octoverse landing page (octoverse.github.com) loaded but
carried no language data in the fetched HTML, so Octoverse 2025 is the
data point used. IEEE's 2026 URL returned 404 (not yet published or a
different slug); 2025 is the latest read.

### 2.1 Disagreements worth knowing

- TypeScript: TIOBE rank 41 (0.26 percent), RedMonk 6, Stack Overflow
  2025 6th (43.6 percent), Octoverse 2025 first by contributor gain
  (about 1.05 million, plus 66.63 percent) and GitHub states TypeScript
  overtook Python and JavaScript as the most used language in August
  2025. TIOBE counts search pages and undercounts it badly.
- Shell: absent from TIOBE's top 50, 14th at RedMonk, 5th in Stack
  Overflow (48.7 percent in 2025, 51.3 percent in 2026) and Octoverse
  calls shell scripts "the fastest riser" (+324 percent in the AI
  projects cohort it analysed). Its true weight for a repo that needs
  obligation tracking is high because every repo has CI and build
  scripts.
- Visual Basic, Delphi, Fortran, MATLAB, Scratch, COBOL, ABAP, SAS,
  PL/SQL and Ada all sit in TIOBE's top 30, but have no or negligible
  presence in RedMonk's top 20, and a few percent or less in Stack
  Overflow (Delphi 2.5, MATLAB 3.9, Fortran 1.4, Ada 1.4, COBOL 1.0
  percent in 2025). TIOBE overweights them relative to what a frob
  user is likely to run.
- R: TIOBE 7 (2.27 percent) but Stack Overflow 2025 4.9 percent and
  RedMonk 13. Statistical users exist; the frob-user overlap is small.
- Kotlin: TIOBE 33, RedMonk 14, Stack Overflow 15 (10.8 percent).
- Rust: TIOBE 11, Stack Overflow 14 (14.8 percent), RedMonk 20 (and
  RedMonk notes Dart passed it this run).
- Zig: Stack Overflow 2025 33rd (2.1 percent); RedMonk 82, but RedMonk
  notes that on GitHub alone it is 58 while the Stack Overflow axis is
  83, so the Stack Overflow decline understates it. Not in TIOBE's top
  50.
- CUDA: appears in none of the fetched rankings as its own row (it is
  counted as C++ or CUDA is not tracked). Its inclusion rests on the
  owner's request and on GPU/ML repos, not on a ranking.
- COBOL: TIOBE 24 (0.67 percent), Stack Overflow 1.0 percent; Octoverse
  2025 notes COBOL appeared with nearly 3,000 active developers,
  "likely driven by" AI-assisted tutorial repositories, i.e. not
  production mainframe code. Ranked low here.

### 2.2 Weighting

Rank is by a judgement, not a formula, in three passes:

1. Count of independent sources placing the language in the top 20
   (TIOBE, RedMonk, Stack Overflow 2025, Octoverse 2025 notable).
2. A frob-relevance adjustment: up for languages that sit in repos with
   CI, build files and public APIs worth obligation-tracking (shell,
   PowerShell, build and infra languages, GPU kernels); down for
   languages dominated by single-file analysis, notebooks, spreadsheets
   or legacy-only estates (VBA, MATLAB, COBOL, ABAP, SAS, Scratch,
   LabVIEW, Ladder Logic).
3. A cost adjustment (section 4): a language with no usable grammar is
   not dropped but is placed after those with one, because the cost
   differs by an order of magnitude.

Languages already carried by this repo are ranked too, for context, and
marked `supported`.

## 3. Ranked target list

Columns: **T** TIOBE Nov 2026 rank; **RM** RedMonk Jan 2026 rank (ties
share a number; "-" outside the top 20 shown; Zig quoted from prose);
**SO** Stack Overflow 2025 all-respondent rank and percent; **Tier** is
section 7's batch (S = supported already, 1 to 5 = batch). A dash means
the fetched page did not list it (TIOBE: not in the top 50 table I
read, which is not proof it is lower than 50).

| # | Language | T | RM | SO 2025 | Other | Tier |
|---|---|---|---|---|---|---|
| 1 | Python | 1 | 2 | 4 (57.9) | Octoverse #2 growth | S |
| 2 | TypeScript | 41 | 6 | 6 (43.6) | Octoverse #1 growth, GitHub #1 by usage Aug 2025 | S |
| 3 | JavaScript | 6 | 1 | 1 (66.0) | Octoverse #3 growth | S |
| 4 | Java | 3 | 3 | 7 (29.4) | Octoverse #4 growth | S (adapter), 1 (gap audit) |
| 5 | C# | 5 | 4 (tie) | 8 (27.8) | Octoverse #5 growth | S (adapter), 1 (gap audit) |
| 6 | C++ | 4 | 7 (tie) | 9 (23.5) | Octoverse: C++ >7,800 AI repos, +11 percent | S |
| 7 | C | 2 | 10 | 11 (22.0) | | S |
| 8 | Bash / Shell | - | 14 (tie) | 5 (48.7) | Octoverse: shell +324 percent | S (adapter), 1 (gap audit) |
| 9 | Go | 10 | 12 | 13 (16.4) | | S |
| 10 | Rust | 11 | 20 | 14 (14.8) | | S |
| 11 | SQL | 8 | - | 3 (58.6) | dialect problem, section 4 | 3 |
| 12 | PowerShell | - | 17 | 10 (23.2) | | 2 |
| 13 | PHP | 12 | 4 (tie) | 12 (18.9) | | 2 |
| 14 | Kotlin | 33 | 14 (tie) | 15 (10.8) | | 2 |
| 15 | Swift | 18 | 11 | 20 (5.4) | | 2 |
| 16 | Ruby | 30 | 9 | 18 (6.4) | | 2 |
| 17 | CUDA | - | - | - | owner request; GPU/ML repos | 1 |
| 18 | Zig | - | 82 (GitHub-only 58) | 33 (2.1) | owner request; RedMonk "watching" set | 1 |
| 19 | Scala | 38 | 14 (tie) | 29 (2.6) | | 3 |
| 20 | Dart | 20 | 18 (tie) | 19 (5.9) | | 3 |
| 21 | Lua | 32 | - | 16 (9.2) | Luau (Roblox) is Octoverse fastest-growing small language: >3,600 devs, >194 percent | 3 |
| 22 | Objective-C | 29 | 18 (tie) | - | RedMonk expects it to leave the top 20 | 4 |
| 23 | R | 7 | 13 | 21 (4.9) | | 4 |
| 24 | Terraform / HCL | - | - | - | infra; not in any fetched ranking | 2 |
| 25 | Dockerfile | - | - | - | infra; not in any fetched ranking | 2 |
| 26 | Makefile / CMake | - | - | - | build; not in any fetched ranking | 2 |
| 27 | Groovy (also Gradle) | - | - | 22 (4.8) | build scripts | 3 |
| 28 | Elixir | - | - | 28 (2.7) | | 4 |
| 29 | Haskell | 39 | - | - | | 4 |
| 30 | F# | - | - | 37 (1.3) | | 4 |
| 31 | OCaml | 34 | - | 38 (1.2) | | 4 |
| 32 | Julia | 23 | - | - | | 4 |
| 33 | Perl | 15 | - | 26 (3.8) | | 4 |
| 34 | Visual Basic .NET | 9 (listed "Visual Basic") | - | 23 (4.4) | | 4 (grammar is weak) |
| 35 | GDScript | - | - | 27 (3.3) | Godot | 4 |
| 36 | Fortran | 13 | - | 35 (1.4) | | 5 |
| 37 | Ada | 28 | - | 36 (1.4) | | 5 |
| 38 | Delphi / Object Pascal | 19 | - | 30 (2.5) | | 5 |
| 39 | Erlang | - | - | 34 (1.5) | | 5 |
| 40 | Nix | - | - | - | infra | 5 |
| 41 | Solidity | 49 | - | - | | 5 |
| 42 | Assembly | 17 | - | 17 (7.1) | no single syntax, section 5 | 5 |
| 43 | MATLAB | 16 | - | 25 (3.9) | | 5 |
| 44 | COBOL | 24 | - | 41 (1.0) | Octoverse: about 3,000 devs, tutorial-driven | 5 |

Explicitly out of scope for this round, all of which appear in a
fetched ranking: VBA (SO 24th, 4.2 percent; no grammar in the pack),
Scratch (TIOBE 14, visual), VBScript and Classic Visual Basic (TIOBE 21
and 22, legacy), ABAP (TIOBE 25, no grammar), SAS (TIOBE 26, grammar
exists but proprietary estate), PL/SQL (TIOBE 27, folded into SQL),
Ladder Logic (TIOBE 37, graphical), LabVIEW (TIOBE 48, graphical), GML,
Xojo, FoxPro, XSLT, Mojo (SO 0.4 percent), Gleam, Prolog, Lisp
family, Clojure (TIOBE 50), D, Nim, Odin, Crystal, V. Each can be added
by the same recipe; none earns a slot against the 44 above.

## 4. Tree-sitter grammar availability and maturity

### 4.1 What this repository actually uses

The ticket text says the repo "already depends on tree-sitter-language-pack".
It does not. Grep of every `Cargo.toml` finds no such dependency.
Grammars are individual pinned crates in `crates/gob-languages`, each
behind a feature (`rust markdown toml python csharp go java c cpp
typescript tsx javascript jsx css scss html yaml shell`, with `tree-sitter`
pinned `=0.27.0`). `Cargo.toml` at the workspace root carries
`[profile.dev.package.tree-sitter-*]` overrides for the same set. The
pinning rule is documented in `crates/gob-languages/Cargo.toml` ("the pin is part of the cache
identity"). That convention, one exact-pinned crate per language behind a
feature, is what a new language follows. Using the language pack
instead would change the cache identity model and is a separate
decision, not assumed here.

Which targets are already wired (main branch, this worktree):
Python, JavaScript, TypeScript, TSX, JSX, C, C++, C#, Java, Go, Rust,
Shell (grammar `tree-sitter-bash =0.25.1`), CSS, SCSS, HTML, YAML, TOML,
Markdown. Symbol adapters exist in `gob-symbols` for C#, Java, Go, C and
C++ (shared), Python, Rust, TypeScript family, Shell, CSS, HTML, YAML,
Markdown (`crates/gob-symbols/src/*.rs`).

Zig and CUDA: ticket ~233F9ZV (worktree `/home/logan/projects/frob-wt/233F9ZV`,
NOT landed) adds `Language::Zig` and `Language::Cuda`, features `zig`
and `cuda`, with `tree-sitter-zig =1.1.2` and `tree-sitter-cuda =0.21.2`,
comment discovery for both, and in `gob-symbols/src/lang.rs` maps both to
`Lang::OpaqueText` ("no gob_caps::Lang row yet: symbols treat Zig and
CUDA as text with no adapter"). So at this writing they parse and their
comments are found, but no public-symbol extraction exists. That is the
real starting point for batch 1.

### 4.2 Availability table

"Pack" = listed in the tree-sitter-language-pack README (371 languages,
repo `xberg-io/tree-sitter-language-pack`, crate v1.25.0 updated
2026-11-06) with the upstream grammar repository shown. "Crate" = a
standalone grammar crate on crates.io, with version and last-update
date from the crates.io API. The pack list proves a grammar exists; it
does not prove quality. Maturity here is only what could be
measured: recency of the last crates.io release and, for the repo's own
adapters, that they are used. Anything about parse completeness,
error-recovery or corpus coverage is `(unverified)` and each adapter
ticket must test the grammar on a real corpus of the language before
committing to it.

| Language | In repo now | Pack (upstream) | crates.io crate | Class |
|---|---|---|---|---|
| Python, JS, TS, TSX, C, C++, C#, Java, Go, Rust, Bash, CSS, HTML, YAML | yes | yes | in `gob-languages` | wired |
| SQL | no | yes (`Goldziher/tree-sitter-sql`; also tsql, bigquery variants) | `tree-sitter-sequel` 0.3.11, 2025-10-01 | crate; dialect risk |
| PowerShell | no | yes (`airbus-cert/tree-sitter-powershell`) | `tree-sitter-powershell` 0.26.6, 2026-10-28 | crate |
| PHP | no | yes (`tree-sitter/tree-sitter-php`) | `tree-sitter-php` 0.25.1, 2026-10-06 | crate |
| Kotlin | no | yes (`fwcd/tree-sitter-kotlin`) | `tree-sitter-kotlin` 0.3.8, 2024-08-03; `tree-sitter-kotlin-ng` 1.1.0, 2025-01-09 | crate; two competing grammars |
| Swift | no | yes (`alex-pinkus/tree-sitter-swift`) | `tree-sitter-swift` 0.7.4, 2026-10-04 | crate |
| Ruby | no | yes (`tree-sitter/tree-sitter-ruby`) | `tree-sitter-ruby` 0.23.1, 2024-11-11 | crate |
| CUDA | in ~233F9ZV | yes (`tree-sitter-grammars/tree-sitter-cuda`) | `tree-sitter-cuda` 0.21.2, 2026-09-15 | crate (pending landing) |
| Zig | in ~233F9ZV | yes (`tree-sitter-grammars/tree-sitter-zig`) | `tree-sitter-zig` 1.1.2, 2024-12-22 | crate (pending landing) |
| Scala | no | yes (`tree-sitter/tree-sitter-scala`) | `tree-sitter-scala` 0.26.9, 2026-11-07 | crate |
| Dart | no | yes (`UserNobody14/tree-sitter-dart`) | `tree-sitter-dart` 0.3.0, 2026-10-25 | crate |
| Lua | no | yes (`MunifTanjim/tree-sitter-lua`) | `tree-sitter-lua` 0.5.0, 2026-02-26 | crate |
| Objective-C | no | yes (`tree-sitter-grammars/tree-sitter-objc`) | `tree-sitter-objc` 3.0.2, 2024-12-16 | crate |
| R | no | yes (`r-lib/tree-sitter-r`) | `tree-sitter-r` 1.3.0, 2026-06-19 | crate |
| Terraform / HCL | no | yes (`MichaHoffmann/tree-sitter-hcl`; also `tree-sitter-grammars/tree-sitter-hcl` as "terraform") | `tree-sitter-hcl` 1.1.0, 2025-05-16 | crate |
| Dockerfile | no | yes (`xberg-io/tree-sitter-dockerfile`) | `tree-sitter-dockerfile` 0.2.0, 2024-05-09 | crate; stale |
| Makefile | no | yes (`alemuller/tree-sitter-make`) | not queried | pack only until checked |
| CMake | no | yes (`uyha/tree-sitter-cmake`) | not queried | pack only until checked |
| Groovy | no | yes (`Decodetalkers/tree-sitter-groovy`) | `tree-sitter-groovy` 0.1.2, 2024-11-19 | crate; 0.1 |
| Elixir | no | yes (`elixir-lang/tree-sitter-elixir`) | `tree-sitter-elixir` 0.3.5, 2026-03-02 | crate |
| Haskell | no | yes (`tree-sitter/tree-sitter-haskell`) | `tree-sitter-haskell` 0.24.1, 2026-09-30 | crate |
| F# | no | yes (`ionide/tree-sitter-fsharp`) | not queried | pack only until checked |
| OCaml | no | yes (`tree-sitter/tree-sitter-ocaml`) | `tree-sitter-ocaml` 0.26.0, 2026-09-13 | crate |
| Julia | no | yes (`tree-sitter/tree-sitter-julia`) | `tree-sitter-julia` 0.23.1, 2024-11-11 | crate |
| Perl | no | yes (`tree-sitter-perl/tree-sitter-perl`) | `tree-sitter-perl` 1.1.2, 2025-12-27 | crate |
| Visual Basic .NET | no | yes, as "vb" (`CodeAnt-AI/tree-sitter-vb-dotnet`) | not queried | pack only; unproven (unverified) |
| GDScript | no | yes (`PrestonKnopp/tree-sitter-gdscript`) | not queried | pack only until checked |
| Fortran | no | yes (`stadelmanma/tree-sitter-fortran`) | `tree-sitter-fortran` 0.6.0, 2026-04-24 | crate |
| Ada | no | yes (`briot/tree-sitter-ada`) | `tree-sitter-ada` 0.9.2, 2026-10-28 | crate |
| Delphi / Pascal | no | yes, as "pascal" (`Isopod/tree-sitter-pascal`) | `tree-sitter-pascal` 0.10.2, 2025-12-23 | crate; Delphi dialect coverage (unverified) |
| Erlang | no | yes (`WhatsApp/tree-sitter-erlang`) | `tree-sitter-erlang` 0.21.0, 2026-10-07 | crate |
| Nix | no | yes (`nix-community/tree-sitter-nix`) | not queried | pack only until checked |
| Solidity | no | yes (`JoranHonig/tree-sitter-solidity`) | not queried | pack only until checked |
| Assembly | no | only per-assembler grammars: `asm` (`rush-rs/tree-sitter-asm`), `nasm`, `x86asm` | `tree-sitter-asm` 0.24.0, 2025-02-06 | fragmented |
| MATLAB | no | yes (`acristoffers/tree-sitter-matlab`) | `tree-sitter-matlab` 1.3.3, 2026-11-06 | crate |
| COBOL | no | yes (`nolanlwin/tree-sitter-cobol`) | `tree-sitter-cobol` 0.1.0, 2025-08-22 (617 downloads) | crate; barely used |

Classes used above: **wired** (already a feature here), **crate** (a
standalone crate exists, so the add is a feature plus pin), **pack
only** (a grammar exists in the pack's sources, but no standalone crate
was confirmed; the adapter needs a vendored or git dependency, and the
repo's pinning model must be extended), **none** (no usable grammar).

### 4.3 Targets with no usable grammar

No row in section 3 is entirely without a grammar, but the cost
differs and these need a decision before their batch:

- **Assembly**: no single grammar; the dialect (NASM, GAS, MASM, ARM) is
  not knowable from the extension `.s`/`.asm`. Plan for text-only
  (`OpaqueText`) with comment scanning for the arch family per file. No
  symbols beyond labels.
- **Visual Basic .NET, COBOL, Dockerfile**: a grammar exists, but the
  fetched evidence for quality is weak (VB grammar upstream owner, COBOL
  crate has 617 downloads, Dockerfile last release 2024-05-09).
  Mark each as `OpaqueText` plus lexical directive scanning (the
  existing lexical no-grammar path) until a corpus test justifies promoting it.
- **VBA, ABAP, Ladder Logic, LabVIEW**: out of scope, see section 3.

The lexical fallback is what makes the no-grammar group tractable:
directives are honoured (PARSE002) or reported when the comment syntax
is unrecognised (PARSE001), but they are "matched lexically and still
invisible to structural gates". That is cost-low, value-low, and is the
default for any pack-only or doubtful grammar.

## 5. Comment syntax for the directive DSL

A directive is `frob:<verb> ...` in a comment. Per
`docs/design/shared/code-model.md` it must start a comment line (text
before it on the same comment line makes it prose) and binds to the
next item or the enclosing section. That requires, per language: (a) a
form that can occupy a whole line by itself, (b) a way to know the
comment is a real comment and not a string, heredoc or doc literal, and
(c) a rule for where the binding anchor is.

Notation: `L` line comment opener, `B` block form, `N` yes if block
comments nest. "Directive form" is the form adapters should recognise;
block forms are accepted only where noted. All entries are from the
language specifications as known to the author and were NOT re-fetched
this pass (unverified); the existing C-family, Python, shell and Rust
entries match `crates/gob-languages/src/comments.rs`, which was read.

### 5.1 Plain cases

| Language | L | B | N | Directive form | Awkward notes |
|---|---|---|---|---|---|
| Java, C#, C, C++, CUDA, Go, JS, TS, Kotlin, Swift, Scala, Dart, Rust, PHP, Objective-C, Groovy, Solidity, Zig, Gleam | `//` | `/* */` (not Zig, not Gleam) | Rust, Kotlin, Swift, Scala, Dart: yes (unverified). Java, C#, C, C++, CUDA, Go, JS, TS, PHP, Groovy, Solidity, Objective-C: no | `//` line | Zig has no block comment at all; Gleam too. `///` and `//!` (Zig, Rust, Gleam `///` `////`) are doc comments: a directive on them is allowed only if the adapter treats doc lines as comments (code-model.md rule for `///`). Non-nesting block: a `*/` inside quoted text ends it, so a scanner must be string-aware (the existing `csharp_plain` and `web_plain` do this). |
| PHP (extra) | `//` and `#` | `/* */` | no | `//` | `#[` starts an attribute in PHP 8, not a comment; `#` followed by `[` must not be scanned as a directive start. Also `?>` ends a `//` comment mid-line. Inline HTML outside `<?php` is not code. |
| Python, Ruby, R, Perl, Elixir, GDScript, Julia, Nim-style hash | `#` | Ruby `=begin`/`=end`; Perl POD `=pod`..`=cut`; Julia `#= =#` (nests) | Julia yes | `#` | Python: docstrings are string literals, not comments; a directive in a docstring is not a directive. Significant indentation: the directive line must sit at the indent of the symbol it binds to, and a `#` line never changes indentation parse, so a directive between a decorator and the def is legal but binds to the def. Ruby's `=begin` must start at column 0. Perl `#` also appears in regex `/x` and `qw()`; a heredoc body can contain `#` that is text. |
| Lua | `--` | `--[[ ]]` and `--[==[ ]==]` (level-matched) | only by differing `=` count | `--` | `--[[` opens a block even when intended as a line comment; the scanner must test for `[` `=`* `[` immediately after `--`. |
| Haskell | `--` | `{- -}` | yes | `--` | `--` followed by an operator character (`-->`, `--|`) is an operator, not a comment; `{-# ... #-}` is a pragma, not a comment. |
| OCaml | none | `(* *)` | yes | `(* ... *)` single line | no line comment, so a directive must be a one-line block comment; strings inside comments are lexed, so an unbalanced `"` inside breaks nesting. |
| F# | `//` | `(* *)` | yes | `//` | `(*)` is the multiplication operator in parentheses, not a comment start. |
| Erlang | `%` | none | - | `%` | `%%` and `%%%` conventionally document modules; any count is the same comment. |
| Ada | `--` | none | - | `--` | none. |
| Fortran | `!` (free form) | none | - | `!` | Fixed form: `C`, `c`, `*`, or `!` in column 1; `!` inside a character literal is text. Both forms occur in the wild; treat `.f`/`.F` as fixed and `.f90` and later as free (unverified). |
| COBOL | `*>` (free form) | none | - | `*>` | Fixed form: `*` in column 7; columns 1-6 and 73-80 are not code. No block comment. A directive in fixed form must have `*` at column 7, which constrains the adapter. |
| MATLAB | `%` | `%{` ... `%}` each alone on a line | yes | `%` | `%{` is only a block if alone on its line. `...` begins a continuation that comments out the remainder of the line. |
| SQL | `--` | `/* */` | PostgreSQL yes, most others no | `--` | MySQL requires a space after `--`; `/*! ... */` and `/*+ ... */` are executable hint comments, not prose; dialect is not known from `.sql`. Stored-procedure bodies delimited by `$$` contain code, so comment scanning must not stop at `$$`. |
| PowerShell | `#` | `<# #>` | no | `#` | `<# ... #>` is also help text (comment-based help); here-strings `@" "@` hold `#` text; `#requires` is a statement-like comment. |
| Bash / shell | `#` | none | - | `#` | `#` starts a comment only at the start of a word (`$#`, `${#x}`, `a#b` are not); here-document bodies contain `#` text; `#!` on line 1 is the interpreter line, not a directive. Already handled by `hash_comment_starts`. |
| Dockerfile | `#` | none | - | `#` at line start only | a `#` after an instruction is part of the argument, not a comment. Leading `# syntax=` and `# escape=` are parser directives, not prose. |
| Makefile | `#` | none | - | `#` | A trailing backslash continues a comment onto the next line; a `#` inside a recipe line is passed to the shell, where it is a shell comment. |
| CMake | `#` | `#[[ ]]` and `#[=[ ]=]` | no | `#` | bracket-comment rules like Lua. |
| Terraform / HCL | `#` and `//` | `/* */` | no | `#` or `//` | none beyond string interpolation `"${...}"`. |
| Nix | `#` | `/* */` | no | `#` | `''` multi-line strings contain `#` text. |
| Visual Basic .NET | `'` and `REM` | none | - | `'` | The `''' ` triple form is the XML doc comment. A trailing `_` continues the line. No block comment. |
| Delphi / Pascal | `//` | `{ }` and `(* *)` | no (mixing is allowed) | `//` | `{$...}` and `(*$...*)` are compiler directives that look like comments. |
| Assembly | `;` (NASM, MASM) | `/* */` (GAS) | no | arch dependent | GAS uses `#`, `@`, `//` or `;` depending on target; a `;` can also be a statement separator; nothing is knowable from the extension. |
| Clojure and Lisp family | `;` | `#\| \|#` (Common Lisp, Scheme) | yes | `;` | `#_` discards the next form and `(comment ...)` is real code evaluated to nil; neither is a comment for the scanner. |

### 5.2 Languages with no line comment, or a block that cannot nest

- **No line comment**: OCaml (block only), plus none of the others in
  the list; COBOL fixed form uses a column marker instead of an opener.
  Directive form must be a block comment containing one line.
- **Block does not nest**: Java, C#, C, C++, CUDA, Go, JS, TS, PHP, Groovy,
  Solidity, Objective-C, PowerShell, Delphi, SQL (most dialects), HCL.
  `/* frob:ticket X */` is safe only if the text does not contain `*/`.
- **No block comment at all**: Zig, Gleam, Erlang, Ada, Fortran, COBOL,
  Python, shell, Bash, Make, Dockerfile, R, Elixir. A multi-line
  directive must repeat the line opener on every line.
- **Significant indentation constrains placement**: Python, GDScript,
  Nim, Haskell (layout), F# (offside), Elixir (not significant but
  conventionally aligned), Makefile (tab-prefixed recipes), YAML
  (already handled). Rule: the directive sits on its own line, at the
  indentation of the item it binds to, immediately before it.
- **Comment indistinguishable from other syntax** (parser must decide):
  PHP `#[`, Haskell `-->`, F# `(*)`, Perl `#` in regex, shell `$#`,
  MySQL `--` without trailing space, Lua `--[[`, SQL hint comments.

## 6. What "public symbol" means, per language

The model is the one in `docs/design/shared/code-model.md`: a symbol
carries an `ATTR_VISIBILITY` of `public` or `private` (plus whatever
the existing adapters emit). This section states the intended mapping so
an adapter author does not choose one. "Surface" means what an
obligation gate (`frob:tests`, docstring coverage) treats as public.

Existing rules, read from the adapters in this worktree, which stay
unchanged unless a gap is noted:

- **Rust**: `pub` is public; `pub(crate)`/`pub(super)`/`pub(in ...)`
  are NOT public surface (restricted); private otherwise (unverified for
  the exact adapter edge cases; the Rust adapter was not read for this
  document).
- **Go** (`go.rs`): leading upper-case letter is public, else private.
- **C and C++** (`c.rs`): `static` is private, everything else public.
  Header/implementation split is not modelled: a definition in `.c`
  and its declaration in `.h` are two symbols. Intended rule: a
  declaration in a header is the public symbol; the matching
  definition binds to it (one obligation, not two); a definition with
  no header declaration and not `static` is public-by-linkage but
  flagged `unpublished`; `static` and anonymous-namespace members are
  private. This is a design statement, not what `c.rs` does today.
- **Java** (`java.rs`): `public` or `protected` is public, else
  private. Package-private is therefore private, which matches
  intent: it is not API outside the package. Nested types inherit
  nothing (a `public` member of a non-public class is not reachable;
  intended rule: public only if every enclosing type is public or
  protected (unverified in the adapter)).
- **C#** (`csharp.rs`): `public` (and members of interfaces and enums)
  is public; `internal`, `private`, `protected internal` handling per
  `visibility_of`: `internal` is not public. Types default to
  `internal`, members of classes default to `private`. Intended rule is
  the same as the adapter's; `protected` is treated as public surface
  only for an unsealed `public` type (unverified in the adapter).
- **Python**: no enforced visibility; convention is a leading
  underscore is private and `__all__`, when present, overrides.
- **TypeScript and JavaScript**: `export` is public; a class member is
  public unless `private`/`#name`; `@internal` JSDoc is a hint only.
- **Shell** (`shell.rs`): functions have no visibility; see below.

Intended rules for languages with no adapter yet:

| Language | Public means | Private means | Notes |
|---|---|---|---|
| Zig | `pub` declarations (`pub fn`, `pub const`, `pub var`, `pub usingnamespace`); a `pub` field in a container is absent: fields are always accessible | non-`pub` top-level declarations | `export fn` is the C ABI surface and is ALSO public. `test "name"` blocks are not symbols. The file is itself a struct; `@import` of a file exposes only `pub`. |
| CUDA | as C++ (below) plus kernels: `__global__` functions are public entry points (launchable); `__device__` functions are public only when declared in a header or `extern` | `static`, anonymous namespaces, and `__device__` functions not in a header | `__host__ __device__` is one symbol, not two. `.cuh` is a header. |
| Bash / shell | every function defined at file top level is public: shell has no visibility | none | Convention: a leading underscore (`_helper`) is private (unverified, convention not enforced). Only functions and exported variables (`export X`) are symbols; plain variables are not. A file meant to be `source`d vs executed has the same surface; the rule treats `main` as the entry, not a symbol requiring tests. |
| PowerShell | functions and cmdlets are public unless the module has an `Export-ModuleMember` or a manifest `FunctionsToExport`, in which case only those are public | non-exported module functions; `private:` scope | |
| Kotlin | default is public; `internal` is NOT public; `private`, `protected` not public | `private`, `internal`, `protected` (top-level) | Matches C# `internal` choice. Companion members belong to the class's rule. |
| Swift | `public` and `open` are public; `internal` (the default), `fileprivate`, `private` are not | everything else | Default is internal, so absent modifier means private. |
| Scala | public unless `private` or `protected`; `private[pkg]` is not public | | `object` members are static-like. |
| PHP | `public` members and all top-level functions/classes (PHP has no file visibility) | `private`, `protected` | |
| Ruby | methods are public by default; after a `private` keyword line (or `private :name`) they are private | `private`, `protected` | The `private` keyword is a method call, state changes mid-class; the adapter must track it in order. `module_function` makes copies. |
| Dart | a name beginning with `_` is library-private; all else public | leading `_` | Privacy is per library (file), not per class. |
| Lua | functions assigned into the returned module table (`M.f`, `return { f = f }`) are public; `local function` is private | `local` | Convention-based. Whole-file tables returned by `require`. |
| Objective-C | declared in the `@interface` in a header is public; methods only in the `@implementation` or a class extension are private | | Same header/implementation problem as C. |
| R | package: names in `NAMESPACE` via `export()` are public; a name starting with `.` is private by convention | | `NAMESPACE` is a separate file; the adapter needs it. Script-only R has no public surface. |
| SQL | schema objects (`CREATE FUNCTION/PROCEDURE/VIEW/TABLE`) are public unless in a non-default private schema | | Dialect decides; one rule is not honest. Treat object definitions as the symbols and visibility as `public` for all. |
| Terraform / HCL | `variable` and `output` blocks are the module's public interface; `resource`, `data`, `locals` are private | | |
| Dockerfile | no symbols; stages (`FROM x AS name`) and `ARG`/`ENV` are the only nameable things; treat as public | | |
| Makefile / CMake | targets are public; a target whose name begins with `.` or `_` is private; CMake `function()`/`macro()` are public | | |
| Groovy | default is public; Gradle `build.gradle` is script code with no surface | `private`, `protected` | |
| Elixir | `def` is public; `defp` is private; `defmacro` public, `defmacrop` private | `defp`, `defmacrop` | `@moduledoc false` hides docs only. |
| Haskell | with an export list, only the listed names; without one, everything top-level is exported | names not in the list | Export lists are per module and include re-exports. |
| OCaml | names in the `.mli` are public; without an `.mli`, everything top-level is public | names absent from the `.mli` | Same header/implementation shape as C. |
| F# | public by default; `private`, `internal` restrict; an `.fsi` signature file restricts as `.mli` does | `private`, `internal`, absent from `.fsi` | |
| Julia | names in `export` are public; since Julia 1.11, `public` declares non-exported public names (unverified for version) | everything else | |
| Perl | package subs not beginning with `_` and, if `@EXPORT`/`@EXPORT_OK` present, those; `my` subs private | `_`-prefixed | Convention-based. |
| Visual Basic .NET | `Public` is public; `Friend`/`Private`/`Protected` not | | Defaults mirror C#: types default Friend. |
| GDScript | everything public; a leading `_` is private by convention | `_`-prefixed | |
| Fortran | in a `module`, public by default unless `private` statement or attribute; with `public ::` list, only listed | per module | |
| Ada | declarations in the package specification (`.ads`) are public until a `private` part; the body (`.adb`) is private | spec after `private`, body | Header/implementation split like C. |
| Delphi / Pascal | declarations in the `interface` section are public; `implementation` section is private; class members `public`/`published` are public | | |
| Erlang | functions in `-export([...])` are public | all others | |
| Nix | no visibility; attributes of the returned set are public; `let` bindings private | `let` | |
| Solidity | `public` and `external` functions and state variables are public; `internal` and `private` are not | | Interface and library members follow the same keywords. |
| Assembly | labels declared `.globl`/`global`/`PUBLIC` are public; others private | | Directive spelling per assembler. |
| MATLAB | all functions in a file visible; only the first function in a `.m` file is callable from outside, the rest are local; `classdef` blocks have `Access` attributes | local functions, `Access=private` | |
| COBOL | a program is public by its `PROGRAM-ID`; paragraphs and sections are private to it (CALL targets are the surface) | | The "public symbol" notion is weakest here. |

For every row: the rule is the first design cut. It is checked against
each language's specification and a corpus when the adapter is built,
not before; the right-hand columns were not re-verified against
language specifications in this pass (unverified).

## 7. Recommended batch order

Constraint: the owner named C#, Java, CUDA, Zig and Bash first. State
as of this writing: C#, Java and Bash have grammars and symbol adapters
on main; CUDA and Zig have grammars in the unlanded ~233F9ZV and no
adapters at all. So batch 1 is a mix of "finish what exists" and "build
what is missing".

| Batch | Languages | Why | Work |
|---|---|---|---|
| 1 | C#, Java, Bash (audit) ; Zig, CUDA (build) | owner request; the first three already ship adapters | Audit C#, Java and Bash against section 6 and 5 (record the gaps rather than silently change behaviour); land ~233F9ZV; write Zig and CUDA symbol adapters (`Lang::Zig`, `Lang::Cuda` rows replacing `OpaqueText`); write the C/C++ header-to-implementation binding rule since CUDA depends on it and it is a gap in `c.rs` today |
| 2 | PowerShell, PHP, Kotlin, Swift, Ruby, Terraform/HCL, Dockerfile, Makefile and CMake | highest cross-ranking presence among unsupported languages (PowerShell SO 10th; PHP, Kotlin, Swift, Ruby in RedMonk's top 20) plus the infra files every repo has | Standalone crates exist for all except Make and CMake (confirm). Kotlin needs a choice between `tree-sitter-kotlin` and `tree-sitter-kotlin-ng` |
| 3 | SQL, Scala, Dart, Lua, Groovy | next tier in at least two rankings | SQL gets one adapter with explicit dialect awareness or a deliberate "objects only" scope |
| 4 | Objective-C, R, Elixir, Haskell, F#, OCaml, Julia, Perl, VB.NET, GDScript | present in at least one ranking but weaker or with weaker grammars | Each needs a corpus test before commit; VB.NET and F# may stay `OpaqueText` |
| 5 | Fortran, Ada, Delphi, Erlang, Nix, Solidity, Assembly, MATLAB, COBOL | legacy or niche estates; some overweighted by TIOBE | Assembly and COBOL are lexical-only unless a customer asks |

Each batch is a set of independent tickets, one per language, so they
parallelise (language adapters touch disjoint files). Shared edits
(`Language` enum, `gob-caps::Lang` rows, grammar pins, the symbol
coverage allowlist) serialize and should land first as a scaffold
ticket per batch, or each language ticket must rebase around them.

The adapter checklist per language, so batches stay uniform: add the
feature and exact-pinned crate; extend `Language` and `detect`; extend
`comment_spans` (section 5); add the `Lang` row and adapter (section 6);
add a corpus test in the language's real idiom; add the language to
`docs/design/grimble/output-atoms.md` if it has an output surface.

## 8. What was not verified

- IEEE Spectrum 2025 per-language ranks: the page's ranking is an
  interactive widget; only prose was read. IEEE 2026 was not published
  at the URL tried.
- GitHub Octoverse 2025: only the five-row growth table and prose; the
  full language leaderboard (and any Octoverse 2026 data) was not read.
  The 2026 Octoverse landing page returned no language data.
- Stack Overflow 2026: top 10 only; the full 2025 list is used for
  breadth.
- TIOBE: only the top 50 table was parsed; "-" means "not in the top 50
  I read".
- Grammar quality: only recency of the last crates.io release was
  measured. Whether a grammar parses real code, recovers from errors, or
  ships an up-to-date node-types is unmeasured; the adapter ticket owns
  that test. Makefile, CMake, F#, VB.NET, GDScript, Nix and Solidity
  were not queried on crates.io.
- Section 5 comment syntax and section 6 visibility rules for languages
  without an adapter in this repo are the author's knowledge of the
  language specifications, not a fetched text. They are the first draft
  for adapter authors to confirm, not a citation. The Java, C#, Go, C
  and shell remarks come from reading the adapters in this tree;
  Rust, Python and TypeScript adapters were not read in detail.
- The pack README states 371 languages and ABI 14; it does not state
  parse quality per language.
- No source examines how many `frob` users run each language; the
  relevance adjustment in 2.2 is judgement.

## 9. Sources (all fetched 2026-11-07)

1. TIOBE Programming Community index for November 2026:
   https://www.tiobe.com/tiobe-index/ (top 50 table, all TIOBE ranks above).
2. RedMonk Programming Language Rankings, January 2026 (published
   2026-04-14): https://redmonk.com/sogrady/2026/04/14/language-rankings-1-26/
   and the category listing https://redmonk.com/sogrady/category/programming-languages/.
3. Stack Overflow Developer Survey 2025, Technology:
   https://survey.stackoverflow.co/2025/technology (programming,
   scripting and markup languages: all respondents, professional
   developers, learning to code).
4. Stack Overflow Developer Survey 2026, Technology:
   https://survey.stackoverflow.co/2026/technology (top 10).
5. GitHub Octoverse 2025, "A new developer joins GitHub every second as AI
   leads TypeScript to #1" (2025-10-28, updated 2026-02-28):
   https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
6. IEEE Spectrum, "The Top Programming Languages 2025" (2025-09-23):
   https://spectrum.ieee.org/top-programming-languages-2025 (prose only).
7. tree-sitter-language-pack README (371 languages, upstream repository
   per language): https://github.com/xberg-io/tree-sitter-language-pack,
   read from the kreuzberg-dev path
   https://raw.githubusercontent.com/kreuzberg-dev/tree-sitter-language-pack/main/README.md
   (the crates.io metadata gives the xberg-io path as the current
   repository).
8. crates.io API, one query per `tree-sitter-*` crate named in
   section 4.2: https://crates.io/api/v1/crates/<name>.
9. In-repo: `crates/gob-languages/Cargo.toml`, `language.rs`,
   `comments.rs`, `hash.rs`; `crates/gob-symbols/src/{lang,csharp,java,go,c,shell}.rs`;
   and, for the unlanded Zig/CUDA state, worktree
   `/home/logan/projects/frob-wt/233F9ZV` (branch `ticket/233F9ZV`).
