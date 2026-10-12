# Lint evidence study: what should frob, grimble and crunk lint for? (design of the study)

Owner request 2026-10-08: mine PR interactions and refactoring commits on the top ~1000
repositories to see which mistakes are commonly made; mine talks, videos, blogs (via
transcripts) from creators such as Logan Smith who demonstrably worked on real projects and
know what they are doing. EXTENSIVE. Output feeds the rule catalogue (rules.md, neatness.md,
cohesion.md, crunk.md) with evidence weights.

## Questions
Q1. Which mistakes do reviewers flag most often, by language and domain, and how severe are they
    (blocking change request vs nit)?
Q2. Which refactorings do maintainers perform, and what motivated them (the smell they removed)?
Q3. Which mistakes escape review and get fixed or reverted later (bug-fix and revert commits)?
Q4. What do credible practitioners say to lint for, where do they agree, where do they disagree?
Q5. For each candidate: is it mechanically detectable, at which tier (syntax, U with Bounds,
    types, effects, render, human), and does an existing frob/grimble/crunk rule cover it?

## Strand A: repository mining (agent: miner)
- Universe: about 1000 repositories, stars-ranked per primary language with floors so every
  language frob targets is represented (Rust, Python, TypeScript/JavaScript incl. React, C#
  incl. Unity projects, Go, Java/Kotlin, C/C++, Ruby, PHP, Swift), plus curated well-reviewed
  projects (rust-lang, CPython, TypeScript, Roslyn, Kubernetes, React, Django, LLVM, Chromium
  mirrors where PRs exist). Exclude archived, forks, awesome-lists, tutorials, mirrors without PRs.
  Record the selection query and date; the denominator is printed in every table.
- Data per repository (GitHub GraphQL, authenticated gh; respect rate limits, resumable, cached):
  last 24 months of merged and closed PRs (cap per repo, e.g. 200 most-commented), their review
  threads (inline comments with file path, diff hunk, resolution state, author association),
  review states (CHANGES_REQUESTED vs COMMENTED vs APPROVED), PR titles/bodies/labels; commits
  whose message signals refactoring, revert, or fix (conventional-commit types, "refactor",
  "revert", "fix", "cleanup", "simplify", "extract", "rename"), with diff stats and touched paths.
- Prefer existing curated datasets where they fit and cite them (e.g. Microsoft CodeReviewer
  dataset, RefactoringMiner oracle and tool for Java, ManySStuBs4J, BugsInPy, Defects4J,
  PyDriller for commit mining); public GH Archive files if BigQuery is unavailable.
- Storage: SQLite plus raw JSON cache under the mining repository's data/ (git-ignored).
  No usernames in any published note; aggregate only.
- Classification: a codebook seeded from the literature (Mantyla and Lassenius 2009 code review
  defect taxonomy; Beller et al. 2014 "Modern code reviews in open-source projects: which problems
  do they fix?"; Bacchelli and Bird 2013; Silva, Tsantalis and Valente 2016 "Why we refactor?";
  AlOmar et al. on refactoring motivations; Sadowski et al. 2018 "Modern code review at Google")
  and extended by open coding. Stratified sample (by language, review state, repository) of at
  least 4000 review comments and 1500 refactoring/fix commits labelled by careful reading, with a
  second independent labelling of 10 percent and agreement reported (Cohen's kappa); the rest
  extrapolated by a local classifier or embedding clustering with stated error. Frequencies
  carry confidence intervals.
- Every category maps to: example comments (paraphrased, linked), languages, severity proxy,
  detectability tier, existing rule id or "new candidate".

## Strand B: practitioner corpus (agents: creators-systems, creators-web, creators-games)
- Credibility gate (applied BEFORE reading their advice, recorded with evidence links):
  shipped or maintained real software of non-trivial size (commits to known projects, a product
  with users, a named role on a team that shipped), and depth (talks at peer-reviewed or
  curated venues, books, widely used libraries). Exclude pure commentators with no verifiable
  work. Record why each person passed or failed. Logan Smith (@_noisecode) is the seed; verify
  him the same way.
- Sources: YouTube talks and videos (transcripts via yt-dlp auto-captions or
  youtube-transcript-api), conference talks (CppCon, C++Now, RustConf, PyCon, JSConf, React Conf,
  GDC, Strange Loop, GOTO, NDC, QCon), blogs, books, style guides of respected organisations
  (Google style guides, Rust API guidelines, PEP 8 and PEP 20, Effective series).
- Extraction: atomic advice items with source, timestamp or section, quote-or-paraphrase,
  the mistake it targets, the claimed reason, the evidence offered (anecdote, data, experience),
  and language scope. Normalise into a shared advice taxonomy aligned with Strand A's codebook.
- Consensus: per advice item, credible sources for, against, and conditional; contested items
  are kept with both sides.

## Synthesis (coordinator)
A ranked candidate catalogue: evidence score = mined frequency x severity x practitioner
consensus, filtered by detectability. Diff against the existing catalogue
(notes/research/lint-requirements.md, neatness.md, cohesion.md draft, crunk.md draft).
New candidates become tickets with their evidence attached.

## Shared rules for every agent in this study
- ASCII only. Every factual claim cites a source fetched in this session (URL, author, date).
  Unfetched = [unsourced]. Print denominators and coverage (an honesty block first).
- Research only inside frob-v2: never modify ~/projects/frob-v2. The miner's code lives
  in its own repository ~/projects/goblin-mining (uv, Python 3.12, pydantic, logging
  module logger, TODO.md for todos, .gitignore with data/).
- Budget the GitHub API (5000 points per hour): resumable, cached, back off on secondary limits.
- Publishable outputs avoid personal data: no usernames or emails; link PRs, aggregate counts.

## Synthesis method as used (appended 2026-10-12, from lint-catalogue-2026-10-08 section 1)

Recorded so a rerun with new mining data is mechanical.

- Score per row: E = M x s x C x A; E_det = E x delta; build rank = E_det x P / cost.
- M (mined score, Strand A): M = r x (1 + 2B - N) + 0.5 f + 0.25 m, with r the post-stratified
  percent share of human thread-opening comments on non-AI PRs, B and N the blocking and nit
  shares of those comments, f the share of fix commits mapping to the candidate (denominator 600)
  and m the share of genuine refactorings mapping to it (denominator 491). Correction applied:
  a quarter of R-DESIGN-STRUCTURE goes to C23.
- s: share of a mined candidate used by a row when one candidate feeds several rows [J].
- C (consensus, Strand B) in [0.25, 2.5]: q = min(1, w / w_ref) with w = flag + 0.5 cond - 1.5
  oppose, voices weighted PASS 1.0, PASS-W 0.5, organisations 1.0, unvetted 0, and w_ref = 15
  (CS), 5 (CG), 8 (CW). C = 1 + q, plus 0.25 per further corpus with q >= 0.3 (cap +0.5), plus
  0.25 when a cited source carries measured data. No coverage: C = 1.0. Contested: C = 0.5
  (Advisory or off only). Opposed-dominant: C = 0.25.
- A (agentic modifier): 1.1 when the category's share on AI-authored PRs is at least 1.4 times
  its human share, else 1.0.
- delta (detectable fraction), P (precision prior: 0.95-1.0 compiler or formatter facts, 0.8-0.9
  bound linters and declared structure, 0.6-0.7 heuristics with Bounds, 0.3-0.5 noisy shapes)
  and cost (story points) are judgement [J]; P enters the rank only.
- Discounts: AI-reviewer comments and human comments on AI PRs carry weight 0 in M (the latter
  enter only through A); practitioner opinion cannot create a signal (C multiplies M); domain
  packs use the parent category's stratum share times a specificity share [J].
- Rerun: change inputs (MR, CS, CG, CW tables or a [J] value), recompute the table, and
  reorder; the top three rows should be stable under halving any one [J] value.
