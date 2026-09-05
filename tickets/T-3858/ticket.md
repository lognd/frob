---
id: T-3858
title: 'frob:waive is silently inert in files with no registered grammar: the suppression
  mechanism fails without telling anyone'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'owner decision: option (a), lexical scan authorised for no-grammar files
    only, with the automatic-warn scope judged per directive presence'
  actor: logan
  at: '2026-09-05'
  old_length: 4592
  new_length: 7678
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as logand.app-v2 FROBLEMS F-041. A `frob:waive` written in a file whose
extension has no registered grammar is never extracted, so the waiver does
nothing -- and the user is told nothing about it.

REPORTER'S CASE: `# frob:waive REF002 reason="..."` inside a `.caddy` snippet has
no effect. REF001/REF002 keep firing. Their workaround was a
`[[refs.entrypoint]]` config entry, i.e. abandoning the waiver entirely.

WHY THIS PARTICULAR FAILURE IS WORSE THAN A MISSED FINDING. The waiver is the
SUPPRESSION mechanism. When a detector misses something, the user learns nothing
false. Here the user takes a deliberate action -- writes a reasoned waiver --
and frob accepts the file without complaint while the waiver is inert. The
finding then keeps firing, so the visible symptom is "frob ignores my waiver",
which reads as a broken tool rather than an unsupported file type. Trust in the
waiver mechanism is the thing being spent.

WHAT FROB ALREADY KNOWS, MEASURED 2026-09-05. It is not blind to the situation:

    src/frob/lang/__init__.py:581
        _log.warning(
            "no grammar registered for extension %r (path=%s, site=%s); pass "
            "expect_heterogeneous=True at the call site if this is routine ..."
        )

So the unparseable file IS noticed. Three reasons that warning does not reach
the user as the fact they need:
  1. It says "no grammar registered", not "a frob: directive in this file will
     be ignored". Nothing connects it to waivers.
  2. It fires once per (extension, site) per run and drops to DEBUG afterwards
     (`_unsupported_ext_warned`).
  3. A call site passing `expect_heterogeneous=True` gets DEBUG only, always --
     permanently silent for that path.
So frob has the fact and does not spend it on the one message that matters.

THE DESIGN TENSION, STATE IT RATHER THAN STEPPING AROUND IT. The standing
directive is that checks parse and compare SYMBOLS, never substrings. But for a
file with NO registered grammar there is no token stream to compare against, so
a directive scan there is necessarily lexical. That is not a violation of the
directive's intent: a `frob:` directive is a FIXED LITERAL PREFIX inside a
comment, not a code construct being inferred. Say this explicitly in the fix so
it is not mistaken later for the lexical shortcut the rule forbids.

Note the ordering trap: option (b) below ("warn that the waiver was ignored")
REQUIRES option (a) ("detect the directive at all"). You cannot know a file
carries a waiver without scanning it. Do not adopt (b) alone believing it is
the cheaper half.

OPTIONS:
  (a) Scan files with no registered grammar for `frob:` directive lines
      lexically, and honour them. Most useful; needs a stated rule for what
      counts as a comment in an unknown format (the reporter's case is `#`,
      but `//`, `;` and `--` are all common in config files).
  (b) Do not honour them, but emit a LOUD, waiver-specific finding: "frob:waive
      at <path>:<line> is ignored: no grammar for <ext>". Requires (a)'s scan.
  (c) Config-declared extension mapping -- let a repo say `.caddy` uses
      `#` comments, or map it to an existing grammar. Explicit, no guessing,
      but it is one more thing to know about.
I lean (a) with (b) as the fallback for anything still unrecognised, but make
the call and give reasoning. A silent inert waiver must not survive any of them.

CHECK WHETHER OTHER DIRECTIVES SHARE THIS FATE. `frob:waive` is the reported
one, but `frob:ticket`, `frob:tests`, `frob:doc`, `frob:debt`, `frob:todo` and
the rest presumably all go unextracted in the same files. If so the blast radius
is larger than waivers -- a `frob:debt` in an unparseable file is untracked debt
that no gate will ever surface. Enumerate and report; that finding may outrank
this one.

MUST-FIRE FIXTURES:
  - a frob:waive in a no-grammar file either takes effect, or produces a finding
    saying it was ignored -- never silence
  - a frob:debt in a no-grammar file is likewise not silently lost
MUST-STAY-QUIET FIXTURES:
  - a no-grammar file with no directives produces no new noise (this matters:
    most unparseable files are ordinary assets and must not start warning)
  - directive handling in every currently-supported language is unchanged

ACCEPTANCE
- The (a)/(b)/(c) choice made with reasoning, including the comment-syntax rule
  for unknown formats.
- The other-directives enumeration reported.
- The lexical-scan justification stated explicitly against the token-not-lexical
  directive, so it is not mistaken for a violation of it later.
- All fixtures committed.



OWNER DECISION 2026-09-05, superseding the (a)/(b)/(c) choice above: "No grammar
should AUTOMATICALLY warn, but I think lexical ONLY IN NO-GRAMMAR situations is
okay. Make your best judgement."

So: OPTION (a) IS CHOSEN. Lexically scan files with no registered grammar for
`frob:` directives and honour them. The lexical scan is authorised ONLY for the
no-grammar case -- a file WITH a registered grammar must keep going through its
grammar, always. Do not let this decision leak into parsed languages; the
token-not-lexical directive still governs everywhere a token stream exists.

The reasoning that makes this consistent rather than an exception: where there
is no grammar there is no token stream to compare against, so lexical is not a
shortcut past a better method -- it is the only method. And a `frob:` directive
is a fixed literal prefix inside a comment, not a code construct being inferred.
Record that argument in the code so a later reader does not "fix" it.

ON "AUTOMATICALLY WARN", and this is the judgement call the owner delegated.
Warning on every no-grammar file would drown the signal: most unparseable files
in a real repo are ordinary assets -- images, lock files, binaries, vendored
blobs -- and a warning per file per run would be noise nobody reads, which is
how the current once-per-(ext,site) dedup came to exist in the first place.

So make the warning UNCONDITIONAL AND LOUD for the case that is actually
actionable, and leave the rest quiet:

  1. A no-grammar file that CONTAINS a `frob:` directive: always report, every
     run, never deduped, never demoted to DEBUG, and NOT silenceable by
     `expect_heterogeneous=True`. This is the case where silence costs the user
     a waiver they think is working. If the directive can be honoured by the
     lexical scan, honour it and say nothing; if it cannot be honoured (an
     unrecognised comment syntax, say), that is a FINDING naming the file, the
     line and the directive.
  2. A no-grammar file with NO directives: keep today's behaviour. It is a
     parse-coverage fact, not a correctness problem, and it is already logged.

That split is the whole point: the existing message is deduped and silenceable
because it answers "was this file parsed?", which is routine. The new one
answers "is a directive you wrote being ignored?", which never is.

CONSEQUENCE FOR expect_heterogeneous: today that flag makes the no-grammar
notice DEBUG-only and permanently silent for that call site. That must not
suppress case 1. Check every call site passing it and confirm none of them is on
a path where user-authored directives live.

The comment-syntax question stands and is now the main design work: decide which
leading markers count as a comment in an unknown format. `#` is the reporter's
case; `//`, `;`, `--` and `%` are all common in config and data files. Prefer
recognising a known set and reporting an unhonourable directive (case 1's
finding) over guessing broadly -- a wrong guess silently honours a directive
that was never a directive, which is a worse failure than not honouring it.
