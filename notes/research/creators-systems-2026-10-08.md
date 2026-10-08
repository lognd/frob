# creators-systems: practitioner corpus for lint evidence (general design, Rust, C++, C, Go, Python, C#/.NET, Java/Kotlin, architecture, testing)

Date 2026-10-08. Agent creators-systems, Strand B of lint-evidence-study.md. Research only; no repository modified. ASCII only.

## 0. Honesty block

- Candidates vetted: 99 (Logan Smith plus 98). Verdicts: 69 PASS, 27 PASS-W (passes with weight 0.5, never sole support), 3 FAIL. The 3 FAILs are deliberate contrast cases I added (anonymous or self-reported-only YouTubers); every person on the owner's list passed or passed-weighted once evidence was found. 7 people first failed only because my first lookup found nothing; a second search recovered them (Josuttis, Evans, Meszaros, Newman, Nygard, Milewski, Romeo). The gate therefore excludes little among already-famous names; it is a weighting device, not a filter. Evidence marked 'via search' was read in a WebSearch result page, not opened.
- Sources: 459 source units processed (375 web documents, 84 talk transcripts). Status: {'full': 379, 'skimmed': 55, 'unreadable': 14, 'irrelevant': 7, 'duplicate': 1, 'mismatch': 3}. 433 read in full or skimmed; 411 yielded at least one item. 14 Google Testing Blog and EWD files were unreadable scrapes (12 recovered through the blog's Atom feed in a second pass of 85 posts). Skimmed means a partial read, stated per source in items/*.sources.tsv (C++ Core Guidelines: index plus Reason lines of about 470 rules; Google C++ guide: formatting tail skimmed; Clippy index: lint lists; Zig reference: style section; Liskov-Wing: abstract, intro, conclusion).
- Talks: transcripts are YouTube auto-captions (yt-dlp, youtube-transcript-api); about 22 talk searches were throttled or matched wrong videos and were dropped; wrong-speaker matches are flagged in the items (Landwerth, Rousos, Static Void podcast hosts carry weight 0). Transcripts live only in the scratch area, not in any repo.
- Items: 2483 atomic advice items (2456 from sources read this session, 27 re-keyed from the earlier neatness.md note and flagged secondary). Extraction and stance relabelling were done by Sonnet sub-agents under a fixed brief; I read roughly 150 item lines in context (contested topics, data-backed items) but did not re-verify items against their sources. Stance labels from extraction were unreliable (negative phrasing was tagged 'against'), so every item was relabelled against a rule statement (flag / oppose / cond / off): flag 1478, cond 260, oppose 78, off 635 (misassigned, excluded). Consensus weights count each voice once per stance; Google voices (style guides, Abseil, Testing Blog, Winters, Wright) are collapsed to one voice.
- Coverage bias: language scope of items: any 914, C++ 701, Go 205, Python 193, C# 174, Rust 123, Java 96, C 46, Kotlin 46. C++ is over-represented; Rust and Java under-represented. Evidence types: argument 1027, authority 658, convention 448, war story 282, data 68. Only 68 items cite data; most 'consensus' is shared opinion among experts, not measurement.
- Not done: no code was run; frob-v2 rule coverage is from grep of crates (implemented ids found as literals: NEAT001, NEAT002, NEAT013, NEAT031, CYCLE001, TODO001, TODO002) and docs/design, notes/research/neatness.md, staged cohesion.md (designed only). Beller et al. numbers cite the PDF fetched from repository.tudelft.nl; Mantyla and Lassenius from aaltodoc PDF. External-tool coverage claims are limited to the Clippy index and the earlier note's verified list.
- Full data: items in creators/items/*.jsonl, relabels in creators/relabel/out_*.jsonl, per-item table in creators/items-all.jsonl, consensus in creators/consensus2.json (all under the scratchpad).

## 1. Credibility gate (step 1)

Criteria: shipped or maintained real software of non-trivial size, plus depth (curated-venue talks, books, widely used libraries). Verdicts: PASS = both; PASS-W = one criterion thin or unverifiable here (weight 0.5); FAIL = no verifiable work or identity.

### 1.1 Logan Smith (@_noisecode), re-verified

- Found: LinkedIn profile 'Logan Smith - Software Engineer at Manticore Games Inc.' (https://www.linkedin.com/in/logan-smith-94772552/): Principal Software Engineer (search snippet), 'decade of professional experience', recommendations about foundational Unreal Engine and C++ systems, and the page lists his videos on proc macros, C++ constructors and Verse. Manticore Games shipped Core, an Unreal-based creation platform in Early Access since 2021, Epic Games an investor (https://en.wikipedia.org/wiki/Core_(video_game)). His own video descriptions say 'in my current codebase at [employer]' we have an optional_ref template, and he thanks an 'occasional colleague'.
- Not found: any public repository (GitHub user noisecode has 0 repos), any commit to a named project, any curated-venue talk or book. The identity link between the YouTube channel and the LinkedIn profile rests on the LinkedIn page naming the videos; I could not confirm it from an independent source.
- Verdict PASS-W. His claims are used as corroboration only; the channel is a good synthesis of Parent, Van Eerd and Martin, whom the corpus reads directly.

### 1.2 Vetting table


| # | Person | Domain | Verdict | Items/sources used | Evidence (links fetched this session; 'via search' = seen in a search-result page, not opened) | Why |
|---|---|---|---|---|---|---|
| 1 | Alex Kladov (matklad) | Rust | PASS | 79/24 | https://github.com/rust-lang/rust-analyzer (5441 commits, rank 3); TigerBeetle | rust-analyzer lead. |
| 2 | Alexis King | Haskell/Racket | PASS | 16/3 | https://github.com/racket/racket (110 commits, rank 25), hasura/graphql-engine (63, rank 41), ghc/ghc (25) | Racket CS and GHC contributor; Parse, don't validate. |
| 3 | Andrei Alexandrescu | C++/D | PASS | 15/2 | https://github.com/dlang/phobos (2072 commits, rank 1); folly/Facebook (https://en.wikipedia.org/wiki/Andrei_Alexandrescu); Modern C++ Design author | Language-library maintainer, Loki, Facebook. |
| 4 | Andrew Gallant (BurntSushi) | Rust | PASS | 7/2 | https://github.com/BurntSushi/ripgrep (68911 stars, 1574 commits, rank 1), rust-lang/regex (1143) | ripgrep and regex author. |
| 5 | Andrew Kelley | Zig | PASS | 11/3 | https://github.com/ziglang/zig (43304 stars, 13495 commits, rank 1) | Language creator. |
| 6 | Anthony Williams | C++ concurrency | PASS | 0/0 | https://github.com/boostorg/thread (358 commits, rank 2) | Boost.Thread maintainer. |
| 7 | Barbara Liskov | abstraction | PASS | 13/2 | CLU, Argus, Turing Award (https://en.wikipedia.org/wiki/Barbara_Liskov) | Built the language systems she theorised. |
| 8 | Bartosz Milewski | C++/Haskell | PASS | 0/0 | Development lead of the Microsoft Content Index (Windows file search) team, C++ in Action, Category Theory for Programmers (https://bartoszmilewski.com/about/ via search) | Shipped Windows component. |
| 9 | Ben Deane | C++/games | PASS | 20/2 | 23 years in games at EA and Blizzard then Quantlab; CppCon 2018, 2019, 2021, 2025 (https://cppcon2018.sched.com/speaker/ben_deane, https://github.com/elbeno/constexpr 88 commits) | Industry experience and repeated curated talks. |
| 10 | Bjarne Stroustrup | C++ | PASS | 0/0 | Creator of C++, https://github.com/isocpp/CppCoreGuidelines (151 commits, rank 4) | Language creator. |
| 11 | Bob Nystrom | Dart/games | PASS | 0/0 | https://github.com/dart-lang/sdk (1634 commits, rank 18), Crafting Interpreters (11097 stars), Game Programming Patterns | Dart team, EA game work. |
| 12 | Brandon Rhodes | Python | PASS | 24/3 | https://github.com/skyfielders/python-skyfield (2324 commits, rank 1), PyEphem (883) | Maintains widely used astronomy libraries. |
| 13 | Brett Cannon | Python | PASS | 0/0 | https://github.com/python/cpython (2249 commits, rank 12), microsoft/vscode-python (671) | Core developer. |
| 14 | Brian Goetz | Java | PASS | 21/3 | Java Language Architect, JSR-335 spec lead, Java Concurrency in Practice (https://dev.java/community/javaone-2026/speakers/brian-goetz/, https://www.infoq.com/profile/Brian-Goetz/) | Language architect; GitHub commits few because JDK work is in other trees. |
| 15 | Brian Kernighan | C/Unix | PASS | 0/0 | https://en.wikipedia.org/wiki/Brian_Kernighan (Unix, AWK, K&R) | Elements of Programming Style. |
| 16 | Bryan Cantrill | systems | PASS | 9/4 | DTrace co-creator, illumos (120 commits), https://github.com/oxidecomputer/hubris (94 commits), Oxide CTO (https://en.wikipedia.org/wiki/Bryan_Cantrill) | Systems engineer; opinionated. |
| 17 | Caitlin Sadowski | code review/static analysis | PASS | 0/0 | Tricorder at Google; 12 years Google; papers in ICSE/CACM (https://cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/, https://dblp.org/pid/17/2324.html) | Primary source for review and analyzer deployment. |
| 18 | Casey Muratori | games/C++ | PASS | 29/5 | Bink Video and Granny 3D at RAD Game Tools, Bink in over 15000 games (https://en.wikipedia.org/wiki/Casey_Muratori); https://github.com/cmuratori/meow_hash (117 commits) | Shipped middleware at scale. Opinionated; advice marked as game/perf scoped. |
| 19 | Chandler Carruth | C++/LLVM | PASS | 9/1 | https://github.com/llvm/llvm-project (3974 commits, rank 17), https://github.com/carbon-language/carbon-lang (487 commits, rank 4); Google | Major LLVM committer and Carbon lead. |
| 20 | Dan Luu | systems/empirics | PASS | 15/6 | Centaur Technology 2005-2013, Google (TPU), Microsoft, Twitter staff (https://qconsf.com/sf2016/sf2016/users/dan-luu.html, https://danluu.com/cache-incidents/) | Verified career; blog is empirical. |
| 21 | Dave Abrahams | C++/Swift | PASS | 14/2 | Boost founder, C++ committee (https://en.wikipedia.org/wiki/David_Abrahams_(computer_programmer)); boostorg/python (1270 commits, rank 1); Swift stdlib | Library designer. |
| 22 | Dave Cheney | Go | PASS | 49/14 | https://github.com/pkg/errors (8254 stars, 104 commits, rank 1), practical-go | Widely used library, Go project contributor. |
| 23 | David Fowler | ASP.NET | PASS | 22/2 | https://github.com/dotnet/aspnetcore (1446 commits, rank 9); AspNetCoreDiagnosticScenarios | Distinguished engineer on ASP.NET Core. |
| 24 | David Parnas | modularity | PASS | 4/1 | https://en.wikipedia.org/wiki/David_Parnas (information hiding, A-7E avionics) | Real avionics software work; 1972 paper. |
| 25 | David Tolnay | Rust | PASS | 3/2 | https://github.com/serde-rs/serde (10868 stars, 2685 commits, rank 1), anyhow (898), thiserror | Author of the Rust ecosystem's most used crates. |
| 26 | Edsger Dijkstra | foundations | PASS | 9/3 | THE multiprogramming system, ALGOL 60 compiler (https://en.wikipedia.org/wiki/Edsger_W._Dijkstra); EWD archive https://www.cs.utexas.edu/~EWD/ | Primary-era source; claims dated, scoped. |
| 27 | Eric Lippert | C# | PASS | 12/4 | Principal developer on the C# compiler team and language design team, 16 years at Microsoft, Coverity architect (https://ericlippert.com/about-eric-lippert/, https://www.silicon.co.uk/workspace/microsoft-coverity-101559) | Compiler team member. |
| 28 | Eric Niebler | C++ | PASS | 0/0 | https://github.com/ericniebler/range-v3 (4376 stars, 1277 commits, rank 1) | Ranges author. |
| 29 | Fedor Pikus | C++/perf | PASS | 0/0 | Chief scientist Mentor Graphics, technical fellow Siemens Calibre, Google, 25+ patents, CppCon instructor (https://www.oreilly.com/pub/au/7031, https://blogs.sw.siemens.com/calibre/2024/11/07/dr-fedor-pikus-cultivates-engineering-talent-in-armenia/) | Industrial EDA codebase. |
| 30 | Gary Bernhardt | testing/boundaries | PASS | 18/2 | https://github.com/garybernhardt/selecta (271 commits, rank 1), Execute Program product, Destroy All Software (https://www.destroyallsoftware.com/) | Ships a product; Boundaries talk is the source. |
| 31 | Guido van Rossum | Python | PASS | 4/1 | https://github.com/python/cpython (11275 commits, rank 1) | Language creator. |
| 32 | Herb Sutter | C++ | PASS | 31/4 | ISO C++ convener, Microsoft (https://en.wikipedia.org/wiki/Herb_Sutter); https://github.com/hsutter/cppfront (6010 stars, 996 commits, rank 1) | Standards leadership plus maintained compiler front end. |
| 33 | Hynek Schlawack | Python | PASS | 27/7 | https://github.com/python-attrs/attrs (5853 stars, 1417 commits, rank 1), structlog (1595) | Maintainer of attrs, which inspired dataclasses. |
| 34 | Hyrum Wright | large-scale refactoring | PASS | 617/135 | Senior staff engineer Google, leads Code Health, Hyrum's Law, SWE at Google editor (https://www.hyrumwright.org/cv.html, https://abseil.io/resources/swe-book/html/ch01.html) | Automated large-scale change at Google. |
| 35 | Ian Lance Taylor | Go | PASS | 0/0 | https://github.com/golang/go (2878 commits, rank 4) | Go compiler and gccgo. |
| 36 | Jason Turner | C++ | PASS | 70/7 | https://github.com/ChaiScript/ChaiScript (1793 commits, rank 1), cppbestpractices (244, rank 1); C++ Weekly since 2016, CppCon/C++Now speaker (https://www.oreilly.com/pub/au/6951) | Maintainer plus curated talks. |
| 37 | John Ousterhout | systems/design | PASS | 27/2 | Tcl and Tk, Sprite, RAMCloud (https://github.com/PlatformLab/RAMCloud), Raft; Stanford professor, founded Electric Cloud (https://en.wikipedia.org/wiki/John_Ousterhout) | Verified systems: Tcl/Tk (wiki), RAMCloud and LogCabin (Raft) repos; see 'APOSD' book. |
| 38 | Jon Gjengset | Rust | PASS | 0/0 | https://github.com/mit-pdos/noria (2767 commits, rank 1), Rust for Rustaceans, Crust of Rust | Research system author plus Rust teaching. |
| 39 | Jon Kalb | C++ | PASS | 0/0 | Wrote C++ for Amazon, Apple, Intuit, Microsoft, Netscape, Sun, Yahoo; chair of C++Now and CppCon, Boost Steering Committee chair (https://www.oreilly.com/pub/au/6473, https://cppalliance.org/people/jon.html) | Shipped across employers, runs the curated venues. |
| 40 | Jon Skeet | C#/API | PASS | 0/0 | https://github.com/nodatime/nodatime (3005 stars, 3633 commits, rank 1), googleapis/google-cloud-dotnet (516) | Library author; C# in Depth. |
| 41 | Jonathan Blow | games/C++ | PASS | 3/1 | Braid (2008), The Witness (2016) (https://en.wikipedia.org/wiki/Jonathan_Blow) | Shipped games; language-design talks are opinion, scoped to games. |
| 42 | Jonathan Boccara | C++ | PASS | 10/2 | https://github.com/joboccara/NamedType (827 stars, 80 commits), pipes (261); Fluent C++ blog | Maintains strong-type library. |
| 43 | Joshua Bloch | Java API design | PASS | 23/1 | Java Collections Framework, Effective Java (https://en.wikipedia.org/wiki/Joshua_Bloch) | Library author at Sun and Google. |
| 44 | Kent Beck | testing/XP | PASS | 15/4 | https://github.com/junit-team/junit5 ; https://en.wikipedia.org/wiki/Kent_Beck (XP, JUnit, TDD) | Creator of XP, JUnit; Facebook years. |
| 45 | Klaus Iglberger | C++ design | PASS | 16/2 | Blaze math library lead designer, C++ Software Design author, CppCon Software Design track organiser (https://isocpp.org/blog/2021/07/cppcon-2020-breaking-dependencies-the-solid-principles-klaus-iglberger, https://cppcon.org/kc_interview_2022_iglberger/) | Library plus curated talks. |
| 46 | Lukasz Langa | Python | PASS | 17/3 | https://github.com/psf/black (41874 stars, 372 commits, rank 1), CPython (291) | Black author, CPython release manager. |
| 47 | Mads Torgersen | C# | PASS | 3/1 | https://github.com/dotnet/csharplang (856 commits, rank 1); C# lead designer | Language design lead. |
| 48 | Manish Goregaokar | Rust | PASS | 0/0 | https://github.com/servo/servo (1429 commits, rank 9), rust-clippy (868, rank 6) | Clippy and Servo. |
| 49 | Mara Bos | Rust | PASS | 0/0 | https://github.com/rust-lang/rust (1421 commits, rank 43); library team lead; Rust Atomics and Locks (https://marabos.nl/atomics/) | Std library maintainer. |
| 50 | Mark Seemann | C#/testing | PASS | 12/3 | https://github.com/AutoFixture/AutoFixture (3540 stars, 713 commits, rank 1); blog https://blog.ploeh.dk/ | Maintainer plus books. |
| 51 | Martin Thompson | perf/messaging | PASS | 0/0 | https://github.com/real-logic/aeron (8900 stars, 10091 commits, rank 1) | Aeron author. |
| 52 | Matt Godbolt | C++/tools | PASS | 0/0 | https://github.com/compiler-explorer/compiler-explorer (19109 stars, 3126 commits, rank 1) | Created and maintains Compiler Explorer, millions of users. |
| 53 | Mike Acton | games/DoD | PASS | 9/1 | Engine Director Insomniac Games, CppCon 2014 keynote, VP DOTS Unity (https://cppcon.org/third-keynote-2014/, https://www.linkedin.com/in/mikeacton/ via search) | Shipped console games; keynote at curated venue. |
| 54 | Niko Matsakis | Rust | PASS | 0/0 | https://github.com/rust-lang/rust (4349 commits, rank 12), chalk (1247, rank 1) | Rust lang team co-lead; borrow checker design. |
| 55 | Peter Bourgon | Go | PASS | 17/2 | https://github.com/go-kit/kit (27424 stars, 744 commits, rank 1) | Go kit author. |
| 56 | Raymond Chen | Windows/API | PASS | 0/0 | Microsoft Windows engineer; The Old New Thing blog since 2003 and book 2007 (https://devblogs.microsoft.com/oldnewthing/author/oldnewthing/) | Three decades on Windows compat; blog is the evidence. |
| 57 | Raymond Hettinger | Python | PASS | 29/3 | https://github.com/python/cpython (4579 commits, rank 7) | Core developer; collections, itertools. |
| 58 | Rich Hickey | Clojure/design | PASS | 45/6 | https://github.com/clojure/clojure (10969 stars, 1870 commits, rank 1); https://en.wikipedia.org/wiki/Rich_Hickey | Created Clojure, Datomic. |
| 59 | Rob Pike | Go | PASS | 25/7 | https://github.com/golang/go (2993 commits, rank 3), Plan 9, UTF-8 (https://en.wikipedia.org/wiki/Rob_Pike) | Go co-creator. |
| 60 | Roman Elizarov | Kotlin | PASS | 5/1 | https://github.com/Kotlin/kotlinx.coroutines (13821 stars, 1036 commits, rank 1) | Kotlin coroutines lead. |
| 61 | Russ Cox | Go | PASS | 4/1 | https://github.com/golang/go (7578 commits, rank 1), https://github.com/google/re2 (152 commits) | Go tech lead, RE2. |
| 62 | Sean Parent | C++ | PASS | 41/8 | GH sean-parent/stlab: https://github.com/stlab/libraries (682 stars, 201 commits, contributor rank 2); Adobe since 1993 on Photoshop, then Software Technology Lab (https://cppcast.com/sean-parent/); Better Code series (https://sean-parent.stlab.cc/presentations/2017-01-25-better-code/2017-01-25-better-code.pdf) | Long shipped Photoshop work plus maintained library plus curated-venue talks. |
| 63 | Stephan T. Lavavej | C++ | PASS | 11/1 | https://github.com/microsoft/STL (11163 stars, 634 commits, rank 1) | MSVC STL maintainer. |
| 64 | Stephen Toub | C#/perf | PASS | 10/3 | https://github.com/dotnet/runtime (10438 commits, rank 2) | Core runtime committer. |
| 65 | Steve Klabnik | Rust | PASS | 0/0 | https://github.com/rust-lang/book (624 commits, rank 3), rust-lang/rust (1798, rank 31) | Rust book maintainer, core contributor. |
| 66 | Tim Peters | Python | PASS | 4/1 | https://github.com/python/cpython (2496 commits, rank 11); Zen of Python, Timsort (https://en.wikipedia.org/wiki/Tim_Peters_(software_engineer)) | Core developer. |
| 67 | Titus Winters | C++/Abseil | PASS | 617/135 | Founded Abseil (https://abseil.io/blog/20170926-welcome-to-abseil, https://github.com/abseil/abseil-cpp 18158 stars), lead author SWE at Google, C++ library design subcommittee chair | Maintained library plus book. |
| 68 | Tony Van Eerd | C++ | PASS | 19/5 | Worked at Inscriber, Adobe, BlackBerry, Christie Digital; C++ committee member; CppCon 2017/2019/2020 talks (https://cppcon2020.sched.com/speaker/tvaneerd); GH https://github.com/tvaneerd/cpp17_in_TTs (rank 1, 136 commits) | Shipped products across employers, committee, repeated curated-venue talks. |
| 69 | Vittorio Romeo | C++ | PASS | 0/0 | 9+ years Bloomberg C++ infrastructure, maintains SFML, co-author Embracing Modern C++ Safely, CppCon 2019 and 2025 keynote (https://romeo.training/, https://cppcon2019.sched.com/speaker/vittorio_romeo via search) | Maintained library plus curated talks. |
| 70 | Arthur O'Dwyer | C++ | PASS-W | 0/0 | https://github.com/llvm/llvm-project (356 commits, rank 231); blog https://quuxplusone.github.io/blog/ | Contributor and prolific blogger; no large product; weighted. |
| 71 | Eric Evans | DDD | PASS-W | 0/0 | Worked on Java and Smalltalk projects in finance, shipping, insurance, manufacturing; Domain Language founder; DDD Blue Book (https://www.domainlanguage.com/, https://nofluffjuststuff.com/conference/speaker/eric_evans via search) | Projects unnamed; no public repos; weighted. |
| 72 | Gerard Meszaros | test patterns | PASS-W | 0/0 | Wrote a Smalltalk unit-test framework in 1996, ClearStream Consulting chief scientist, xUnit Test Patterns (http://xunitpatterns.com/gerardmeszaros.html via search) | Consultant; no public repos; weighted. |
| 73 | Hillel Wayne | formal methods | PASS-W | 13/3 | Consultant (NASA, Meta, Siemens clients), Practical TLA+ (Springer), https://github.com/hwayne/lets-prove-leftpad; QCon London speaker (https://qconlondon.com/speakers/hillelwayne) | Consultant and author; no large shipped codebase; weighted. |
| 74 | Howard Hinnant | C++ | PASS-W | 0/0 | https://github.com/HowardHinnant/date (3434 stars, 522 commits, rank 1) became std::chrono calendar | libc++ and move semantics authorship not fetched; weighted. |
| 75 | Jeff Atwood | community/craft | PASS-W | 20/3 | https://en.wikipedia.org/wiki/Jeff_Atwood (Stack Overflow, Discourse) | Founder; advice mostly craft essays; weighted. |
| 76 | Joel Spolsky | management/craft | PASS-W | 9/3 | https://en.wikipedia.org/wiki/Joel_Spolsky (Fog Creek, Stack Overflow co-founder) | Founder of shipped products; advice mostly process; weighted. |
| 77 | Julia Evans | debugging/tools | PASS-W | 0/0 | https://github.com/rbspy/rbspy (2573 stars, 106 commits, rank 2) | One notable tool plus widely used teaching zines; weighted. |
| 78 | Kate Gregory | C++ teaching | PASS-W | 49/3 | Consultant who writes C# and C++, Microsoft Regional Director, Visual C++ MVP, over a dozen books, CppCon keynote 2018 (https://cppcon.org/plenary2018-2/, https://devblogs.microsoft.com/cppblog/in-the-community-meet-kate-gregory/) | Depth strong; no named shipped product or public repo found, so weighted. |
| 79 | Kevlin Henney | patterns/C++/Java | PASS-W | 18/2 | Co-author of two Pattern-Oriented Software Architecture volumes, editor of 97 Things, IEEE Software advisory board (https://www.oreilly.com/pub/au/3907, https://en.wikipedia.org/wiki/Kevlin_Henney) | Consultant; no verifiable repos; weighted. |
| 80 | Logan Smith (@_noisecode) | Rust/C++/game | PASS-W | 20/20 | LinkedIn page (https://www.linkedin.com/in/logan-smith-94772552/) lists Principal Software Engineer, Manticore Games, 'decade of professional experience', recommendations on Unreal Engine/C++ foundations; his own video descriptions mention 'my current codebase at [employer]'; Manticore shipped Core (https://en.wikipedia.org/wiki/Core_(video_game)) | Employer and role found; link between the LinkedIn Logan Smith and the YouTube channel rests on that page naming his videos (WebFetch summary) and the channel text, not on a GitHub profile. No public repos (GitHub user 'noisecode' has 0 repos), no curated-venue talk found, no named commits. Seed source, weight 0.5 on his own claims; corroborate. |
| 81 | Martin Fowler | refactoring/architecture | PASS-W | 73/23 | Thoughtworks chief scientist (https://en.wikipedia.org/wiki/Martin_Fowler_(software_engineer)); Refactoring catalogue | Depth is exceptional; own shipped code is not verifiable in this session, so weighted. |
| 82 | Michael Feathers | legacy code/testing | PASS-W | 16/1 | Object Mentor, Obtiva Chief Scientist, R7K (https://www.informit.com/authors/bio/16F6A5B2-9838-4BEC-88DB-263B29A7B74C); GOTO talks (https://gotocon.com/amsterdam-2013/speaker/Michael+Feathers) | Consultant of 20 years; no public repos; weighted. |
| 83 | Michael Nygard | architecture | PASS-W | 0/0 | 15+ years delivering systems to US government, banking, retail; Release It! (https://pragprog.com/titles/mnee2/release-it-second-edition/ via search) | Systems unnamed; weighted. |
| 84 | Nicolai Josuttis | C++ | PASS-W | 0/0 | Active C++ Standards Committee member 20+ years, Library Working Group; The C++ Standard Library, C++ Templates co-author (https://cpponline.uk/speaker/nicolai-josuttis/ via search; https://www.josuttis.com/tmplbook/tmplbook.html) | Standards work verified; no code repos found; weighted. |
| 85 | Robert C. Martin | OO/clean code | PASS-W | 43/7 | https://github.com/unclebob/fitnesse (67 commits, rank 10); Object Mentor; https://en.wikipedia.org/wiki/Robert_C._Martin | Shipped FitNesse; strongest rules are contested by Ousterhout; keep both sides. |
| 86 | Sam Newman | architecture | PASS-W | 0/0 | ThoughtWorks consultant embedded at Yahoo and Google 2007 teaching testable code; Building Microservices (https://samnewman.io/about/, https://www.thoughtworks.com/profiles/s/sam-newman via search) | Consultant; weighted. |
| 87 | Sandi Metz | Ruby OO design | PASS-W | 26/4 | https://en.wikipedia.org/wiki/Sandi_Metz (POODR author, workshops) | Teacher; no verifiable repos; weighted. |
| 88 | Scott Meyers | C++ | PASS-W | 0/0 | https://en.wikipedia.org/wiki/Scott_Meyers; retired 2015 (https://www.aristeia.com/, https://scottmeyers.blogspot.com/2015/12/good-to-go.html via search) | Books and training cited by every style guide; no verifiable shipped code, so depth only, weight 0.5, never sole support. |
| 89 | Scott Wlaschin | F#/DDD | PASS-W | 35/8 | Developer, architect, F# Software Foundation board, Domain Modeling Made Functional (https://www.goodreads.com/en/book/show/34921689, https://github.com/swlaschin/DomainModelingMadeFunctional 15 commits) | No named shipped product found; weighted. |
| 90 | Steve McConnell | construction | PASS-W | 0/0 | https://en.wikipedia.org/wiki/Steve_McConnell (Code Complete, Rapid Development) | Book depth very high; career details not fetched this session; weighted. |
| 91 | ThePrimeagen (Michael Paulson) | JS/Rust commentary | PASS-W | 0/0 | 10 years at Netflix, lead developer of Falcor (https://lexfridman.com/theprimeagen-transcript/ via search) | Shipped at Netflix; content is mostly commentary; weighted, no transcripts read. |
| 92 | Tsoding | C/recreational | PASS-W | 0/0 | https://github.com/tsoding/musializer (1481 stars), 308 repos, 14628 followers | Many real hobby projects; no curated-venue talks; weighted, none read. |
| 93 | Vladimir Khorikov | C#/testing | PASS-W | 8/1 | https://github.com/vkhorikov/CSharpFunctionalExtensions (2831 stars, 483 commits, rank 1) | Library maintainer; Unit Testing book not fetched; weighted. |
| 94 | Ward Cunningham | wiki/patterns | PASS-W | 2/1 | https://en.wikipedia.org/wiki/Ward_Cunningham (wiki, Fit, technical debt metaphor) | Originator; few current public repos; weighted. |
| 95 | without.boats | Rust | PASS-W | 0/0 | https://github.com/rust-lang/rust (54 commits, rank 440) | Designed async/await and Pin; few commits, depth is via RFCs and blog, not fetched in this step; weighted. |
| 96 | Yaron Minsky | OCaml/finance | PASS-W | 15/2 | Jane Street (https://github.com/janestreet/base, https://github.com/ocaml/dune 5 commits); Real World OCaml co-author | Role at Jane Street verifiable from GitHub company field only; depth not yet read; weighted. |
| 97 | ArjanCodes (Arjan Egges) | Python design videos | FAIL | 0/0 | Self-reported startups and 20 years teaching (https://arjancodes.com/about/ via search) | No named shipped software or repositories found; self-reported only. |
| 98 | CodeAesthetic (YouTube) | design videos | FAIL | 0/0 | Creator is anonymous (https://www.patreon.com/codeaesthetic/about via search); GitHub 'codeAesthetic' is an unrelated user with 4 followers | No verifiable work, no verifiable identity. Example of the exclusion rule; popular 'never nest' video not used as an authority. |
| 99 | mCoding (James Murphy) | Python/C++ videos | FAIL | 0/0 | Self-reported quant developer, consultancy owner (https://mcoding.io/ via search); GitHub mCodingLLC 18 repos 359 followers | Employer and projects not named; self-reported only. |


## 2. Sources (step 2)

Primary sources by kind: Google, LLVM, Chromium, Linux, Uber, Rust, Go, .NET, Kotlin and Python style guides; C++ Core Guidelines; Rust API Guidelines; Software Engineering at Google chapters 8-22; Google Engineering Practices; Google Testing Blog (85 posts); Abseil tips (32); Fowler bliki and catalog; Beck, Hickey, Parnas, Dijkstra, Liskov-Wing; blogs by matklad, BurntSushi, dtolnay, Cheney, Hynek, Lippert, Toub, D. Fowler, Seemann, Luu, Wayne, Wlaschin, King, Spolsky, Atwood, Metz, Martin, Muratori; 84 conference talks (CppCon, C++Now, GoingNative, NDC, GOTO, PyCon, RailsConf, Strange Loop, GopherCon, KotlinConf and others). Full list in section 8.

## 3. Taxonomy (step 3)

Codes follow Mantyla and Lassenius 2009 (TSE 35; PDF from aaltodoc.aalto.fi): findings split into evolvability (documentation, visual representation, structure with organization and solution approach) and functional defects (interface, logic, resource, check, timing, support, larger). Their data: 75 percent of review-found defects affect evolvability, not visible function; evolvability classification repeatability kappa 0.79. Beller et al. 2014 (MSR; PDF from repository.tudelft.nl) reused the scheme on over 1,400 changes in two OSS projects (ConQAT, GROMACS) and found the same 75:25 maintainability-to-functional ratio. Codes used: EVO.DOC.NAME, EVO.DOC.COMMENT, EVO.DOC.LANG, EVO.VIS, EVO.STR.ORG, EVO.STR.SOL, FUN.RES, FUN.CHK, FUN.INT, FUN.LOG, FUN.TIM, FUN.SUP, plus extensions EVO.STR.ARCH, FUN.PERF, TEST, SEC. The practitioner corpus is dominated by EVO.* and FUN.INT/TEST advice, which matches the 75:25 pattern in what reviewers actually flag.

## 4. Consensus (step 3)

Method: each item was assigned to one of 120 normalised items (from 729 raw slugs; 45 items stayed unassigned in a tail), relabelled flag / oppose / cond against that item's rule statement, and weighted by distinct credible voice (PASS 1.0, PASS-W 0.5, organisations 1.0, unvetted 0). Score = flag + 0.5 cond - 1.5 oppose. 'contested*' marks cases I judged contested from reading both sides even though the relabel found few explicit opposing items (agents tagged one side as flag in 'contested' groups). Statuses: consensus-for 99, contested 16 (8 computed, 8 manual), thin 4, conditional 1 (computed over the 120).

### 4.1 Top 30 consensus items


| Rank | Id | Item | Tier | Weighted for/cond/oppose | frob-v2 today |
|---|---|---|---|---|---|
| 1 | ADV001 | hidden-global-state | structural | 14.0/2.5/0.0 | DESIGN note NEAT012 hidden-state-read (scope graph) |
| 2 | ADV002 | naming-convention | syntax | 15.0/2.0/0.5 | NONE in v2 (language adapters + bound tools; clippy/ruff N rules) |
| 3 | ADV003 | perf-algorithmic | types | 12.0/4.0/0.0 | NONE (clippy perf group via BIND; quadratic needs types/effects) |
| 4 | ADV004 | primitive-obsession | types | 15.5/3.0/2.0 | DESIGN note NEAT022/NEAT023 (strong types); needs types |
| 5 | ADV005 | deep-inheritance | structural | 12.5/2.5/0.0 | NONE (design family ARCH could carry inheritance depth) |
| 6 | ADV006 | weakest-param-type | types | 12.0/2.0/0.0 | DESIGN note NEAT020/NEAT021 |
| 7 | ADV008 | cleanup-on-all-paths | structural | 12.0/3.0/1.0 | NONE (needs resource vocabulary; Unresolved-by-default) |
| 8 | ADV010 | assertions | human | 11.0/2.0/0.0 | NONE (contested) |
| 9 | ADV011 | nesting-depth | syntax | 12.0/2.5/1.0 | DESIGN NEAT004 |
| 10 | ADV012 | api-compat | structural | 12.0/2.5/1.0 | DESIGN DEPR/REL/VERSION (unbumped API), SYS006 contract skew |
| 11 | ADV013 | missing-public-doc | syntax | 11.0/1.5/0.0 | DESIGN DOC001 public items documented; COV |
| 12 | ADV014 | immutability | syntax | 10.5/5.0/1.0 | DESIGN note NEAT036 unnecessary-mutation (language-level) |
| 13 | ADV015 | swallowed-error | structural | 10.5/2.0/0.0 | NONE (error-handling family absent in rules.md; EXC is waiver family) |
| 14 | ADV016 | bool-flag-param | syntax | 9.5/4.0/0.0 | DESIGN NEAT003 boolean-flag-parameter |
| 15 | ADV017 | format-rules | syntax | 10.0/3.0/0.0 | NONE (bind formatter) |
| 16 | ADV018 | copy-paste-dup | structural | 10.5/0.0/0.0 | DESIGN DUP clone rungs R1-R5 (rules.md) |
| 17 | ADV019 | casts | syntax | 9.5/2.0/0.0 | DESIGN note NEAT042 powerful-cast |
| 18 | ADV020 | encapsulation | syntax | 8.5/4.0/0.0 | NONE |
| 19 | ADV021 | raw-owning-pointer | types | 9.5/1.5/0.0 | DESIGN note NEAT043 raw-owning-pointer |
| 20 | ADV022 | premature-abstraction | human | 10.5/4.0/1.5 | NONE (heuristic: single-implementor interface, one-call-site helper => structural?) |
| 21 | ADV023 | public-surface | structural | 12.0/2.5/2.0 | DESIGN SYS009 SYS-SURFACE, COV undocumented public symbol |
| 22 | ADV024 | reinvent-stdlib | structural | 9.5/1.0/0.0 | NONE (needs idiom vocabulary; NEAT006 covers only loops) |
| 23 | ADV025 | task-leak | effects | 10.0/0.0/0.0 | NONE |
| 24 | ADV026 | autoformat-no-bikeshed | syntax | 9.5/4.0/1.0 | NONE as rule; belongs to bound formatter (BIND); policy: do not lint layout |
| 25 | ADV027 | unclear-name | human | 11.5/0.0/1.0 | NONE (partial syntax: single-letter, abbreviations vocabulary) |
| 26 | ADV028 | leaky-abstraction | human | 9.5/1.0/0.0 | NONE |
| 27 | ADV029 | name-lies-about-effect | effects | 9.0/1.0/0.0 | DESIGN NEAT016 name-effect-mismatch |
| 28 | ADV030 | comment-restates-code | human | 9.0/1.0/0.0 | NONE (weak syntax heuristic: comment tokens equal identifier tokens) |
| 29 | ADV031 | error-lacks-context | human | 9.5/0.0/0.0 | NONE |
| 30 | ADV032 | positional-params-confusable | types | 9.5/0.0/0.0 | DESIGN note NEAT022 swappable-primitive-parameters (needs types) |


### 4.2 Contested items, both sides (top 10, then the rest of the table)

Sides cite src (slug or video id) and location. Table of all 16 is in 4.3.

1. Function size (ADV-fn-size). Small: Martin (aposd-vs-cc Method Length; 7EmboKQH8lM 00:56) 2-4 lines rarely over 20; Fowler (fowler-funclen) half a dozen lines is a smell but intent, not length, is the criterion; Feathers (4cVZvoFGJTU 00:12) 5-10 lines; Metz (metz-rules) five lines; Parent (W2tWOdzgXHA 00:30); Van Eerd (QTLn3goa3A8 00:22); TigerStyle hard limit 70 lines. Deep modules: Ousterhout (bmSAYlu0NcY 00:18-00:20; aposd-vs-cc) tiny methods give shallow entangled modules, hundreds-of-lines methods are fine if clean; Go Code Review Comments and Google (about 40 lines, no hard limit); rust-analyzer style (matklad-style) avoid single-use helpers; Google Testing Blog hackable-projects post warns that length 20 or complexity 30 limits feel overbearing; Wayne (WELBnE33dpY 00:00) cites mixed evidence: small functions easier to read and change, harder to debug. Lint implication: NEAT001 stays advisory, high default; never claim evidence for a low limit.
2. Duplication vs wrong abstraction. Tolerate: Metz (8bZh5LMaSmE 00:14; metz-wrong), Cheney (cheney-pkgnames), Hynek (hynek-subclass), Bloch (aAb7hSCtvGw 00:18, SPI needs three implementations), Google tests DAMP not DRY (gtb tests-damp post). Remove at once: Martin (7EmboKQH8lM), Minsky (Effective ML talk), Fowler/Beck 'no duplication' (fowler-beck). Lint: exact-clone rungs only; no sub-three-occurrence rule; n=1 vs n=2 is a profile.
3. Comments. Comment interfaces and the why, missing comments cost 10-100x more than stale ones: Ousterhout (aposd-vs-cc Comments); Cheney, TigerStyle, Google agree on why-comments. Comments are a failure to express in code: Martin (aposd-vs-cc); Pike's C notes (pike-style) minimise comments. Lint: existence of public docs (DOC001) is safe; comment-ratio rules are not.
4. Test doubles. Prefer real objects and state tests: Fowler (fowler-mocks, fowler-unittest), Google (swe-ch11/12/13, gtb avoiding-mocks post), Khorikov (4j-_71crnN4), matklad (matklad-howtotest, no mocks, layer-rooted integrated tests). Mock-heavy small units: Bourgon (bourgon-bp) 80-90 percent unit tests with small interfaces; Fowler grants mockist design pressure (fowler-mocks Design Style). Lint: counting doubles per test is advisory at most; 'do not mock types you do not own' (Google, ADV dont-mock) is types-tier.
5. Coverage thresholds. Pointer, not target: Fowler (fowler-coverage), Bernhardt (RAxiiRPHS9k 00:28), Google (gtb coverage best practices: tiers 60/75/90 but avoid mandates; mutation testing, about 70 percent of real bugs coupled to a mutant). Every line tested: Martin (7EmboKQH8lM 01:46); Turner (turner-tools). Directly relevant to the TEST floors in frob design: prefer changed-line coverage in review (gtb measuring-coverage: about 10 percent lift) over global gates.
6. Exceptions vs status values. No exceptions: Google, LLVM, Chromium (practical reasons), Abseil tip 76. Exceptions: Core Guidelines E.2, I.10, NR.3; Turner; Sutter; Lavavej. Alexandrescu (Wa4mt3GXpK0 00:10) measured exceptions about 50x slower on a hot parse path. Ousterhout and Wlaschin: define errors away / Result values. Lint: a per-language policy knob, not a rule; all camps agree on 'swallowed error' (ADV015).
7. Name length. Short names in small scopes: Cheney (cheney-practical 2.2), Pike (pike-style), Go Code Review Comments, Core Guidelines NL.7, Linux. No abbreviations, long boring names: TigerStyle (tigerstyle Naming), rust-analyzer (matklad-style). Wayne cites a controlled study with no fault-finding difference between full words and abbreviations (WELBnE33dpY 00:10). Lint: scope-proportional only, advisory.
8. Pass by value vs const reference. Parent (W2tWOdzgXHA 01:06) and Abrahams (QthAU-t3PQ4): sink by value. Sutter (xnqTKD8uD64 01:10) measured pessimisation in setters; Winters (xTdeZ4MxbKo 00:26): default const&. Lint: do not lint; at most NEAT021-style weakest-type advice.
9. Raw loops. Parent (W2tWOdzgXHA 00:02): no raw loops. Sutter (xnqTKD8uD64 00:08) and Gregory accept range-for; Boccara (2olsGf6JIkU 00:06) says for_each is not the general replacement. Lint: NEAT006 only for loops whose body matches a known algorithm shape.
10. Static types as defect prevention. Luu (luu-pl) finds the empirical evidence weak; Wayne agrees; King, Wlaschin, Minsky argue on design grounds that types carry invariants. Lint: frame types-tier rules as design hygiene, not as proven bug reduction.

Also contested, in 4.3: DI containers and injection (Feathers, Seemann, Rhodes vs Hettinger), premature optimisation (Carruth, Parent, TigerBeetle argue performance is designed in), opaque vs matchable error types (Cheney vs Uber), header forward declarations (Google vs Chromium/LLVM), auto/var use, test pyramid shape, single-exit vs early return (Henney, Deane, Atwood vs Spolsky cleanup and Linux goto), panic in production (TigerStyle, BurntSushi vs Uber and Go), logging.

Conflict with the owner's global rule 'log everything worth logging': Chromium (chromium-cpp) says remove logging before check-in and Linux (linux-style) says quiet unless something is wrong; Cheney (cheney-logging) wants only two levels. Not a lint conflict; record it when writing a logging rule.

### 4.3 All contested items


| Id | Item | Auto/manual | Weighted for/cond/oppose | Opposing voices |
|---|---|---|---|---|
| ADV101 | fn-size: Function length and size limits (contested: tiny functions vs deep modules) | contested | 6.0/4.0/3.5 | Google, Hillel Wayne, John Ousterhout, matklad |
| ADV050 | premature-optimization: Optimising before measuring | contested | 11.0/0.0/3.0 | Chandler Carruth, Sean Parent, TigerBeetle |
| ADV087 | opaque-error-type: Opaque error types; matching on strings | contested | 6.5/3.0/3.0 | Dave Cheney, David Tolnay, matklad |
| ADV104 | coverage-as-goal: Coverage as a target; mutation testing signal | contested | 5.5/1.5/2.5 | Google, Jason Turner, Robert C. Martin |
| ADV052 | comment-explains-why: comment everything on interfaces vs comments are failure | contested* | 8.5/2.0/2.0 | C++ Core Guidelines, Google |
| ADV048 | exceptions-policy: exceptions vs status/result values | contested* | 8.5/2.5/2.0 | C++ Core Guidelines, Jason Turner |
| ADV097 | header-hygiene: Header and linkage hygiene (C/C++) | contested | 5.0/2.0/2.0 | Google, Rob Pike |
| ADV119 | auto-usage: auto/var type deduction usage (contested) | contested | 1.0/4.0/2.0 | C++ Core Guidelines, Herb Sutter |
| ADV112 | test-pyramid: Test pyramid balance and test sizing | contested | 3.0/2.0/1.5 | Google, Martin Fowler |
| ADV007 | raw-loop-vs-algorithm: no raw loops vs range-for is fine | contested* | 11.5/5.0/1.0 | Rob Pike |
| ADV063 | pass-by-value-vs-ref: sink by value vs const ref default | contested* | 5.0/4.0/1.0 | Herb Sutter |
| ADV009 | inject-dependencies: inject everywhere vs restructure to pure core | contested* | 11.5/4.0/1.0 | Brandon Rhodes |
| ADV114 | c-arrays-pointers: C arrays and pointer arithmetic | contested | 2.0/2.0/1.0 | Rob Pike |
| ADV043 | short-names-scope: scope-proportional short names vs no abbreviations | contested* | 5.0/7.0/0.5 | Hillel Wayne |
| ADV055 | mock-overuse: real objects/state vs mock-heavy unit tests | contested* | 6.0/2.5/0.5 | Martin Fowler |
| ADV120 | dup-vs-wrong-abstraction: remove duplication at once vs tolerate until abstraction clear | contested* | 0.0/0.0/3.5 | Dave Cheney, Hynek Schlawack, Joshua Bloch, Sandi Metz |


## 5. Lint candidates and detectability (step 4)

Tier meaning: syntax = one-file AST/tokens; structural = whole-program facts over the universal model (calls, imports, def-use, duplicates) with may/must bounds; types = needs type/trait resolution; effects = needs purity/IO/panic/async effect facts; human = judgment. 'Today' = frob-v2 status: IMPL (id found as a literal in crates), DESIGN (in docs/design, notes/research/neatness.md or staged cohesion.md, no code), NONE.

### 5.1 Ranked candidates (consensus-for, detectable, with evidence)

| Rank | Candidate | Tier | Today | Evidence weight | Note |
|---|---|---|---|---|---|
| 1 | Swallowed error, catch-all handler, TODO inside error handler (ADV015, ADV049) | structural / syntax | NONE (no error-handling family in rules.md) | Only family with real data: Yuan et al. OSDI 2014 as cited by Luu (luu-postmortem), TigerStyle and Wayne: 92 percent of catastrophic failures from mishandled non-fatal errors, about 25 percent ignored errors, 8 percent overbroad catch, 2 percent TODO in handler | New family; P+ on empty catch/ignored result with vocabulary; FP risk low when scoped to explicit discard |
| 2 | Hidden global state / ambient calls (ADV001, ADV091) | structural | NEAT012 DESIGN, NEAT013 IMPL | 18 voices, 0 opposed | Highest agreement of any item; ship NEAT012 next |
| 3 | Nesting depth with guard-clause remedy (ADV011) | syntax | NEAT004 DESIGN | 17 voices; Atwood cites correlation with errors | Cheap, language-neutral |
| 4 | Boolean flag and confusable positional parameters (ADV016, ADV032) | syntax / types | NEAT003, NEAT022 DESIGN | 13 and 10 voices | Syntax finds literals at call sites |
| 5 | Resource cleanup on all paths (ADV008) | structural | NONE | 16 voices; Linux goto vs RAII is a language split | Needs resource vocabulary; Unresolved by default |
| 6 | Public surface wider than needed; API compat / Hyrum (ADV023, ADV012) | structural | SYS009, DEPR/REL DESIGN | 17 and 14 voices; Wright's law | Fits frob graph strengths |
| 7 | Command-query / out-parameters / mutated args (ADV036) | effects | NEAT018/019 DESIGN (019 off by default) | 12 voices; remove_if conflict with CQS (earlier note) | Keep out-param (NEAT018) on, CQS off |
| 8 | Functional core vs shell, name lies about effect (ADV040, ADV029) | effects | COH002, NEAT016 DESIGN | 11 and 12 voices | Needs effects capability |
| 9 | Test hygiene: logic in tests, no assertion, sleep/clock in tests (ADV096, ADV082, ADV060) | syntax / effects | NONE (TEST001 covers bindings only) | Google flakiness data: flake rate rises with test size (0.5 percent small, 14 percent large; gtb where-do-our-flaky-tests) | New; cheap syntax rules |
| 10 | Copy-paste duplication (ADV018) | structural | DUP R1-R5 DESIGN | 13 voices, 0 opposed on exact clones | Only exact/near clones; see contested 2 |
| 11 | Dead code, stale comments (ADV076, ADV099) | structural | DEAD, DRIFT DESIGN | 5 and 6 voices | |
| 12 | Raw owning pointer, casts, two-phase init, wildcard match (ADV021, ADV019, ADV033, ADV070) | types / syntax | NEAT043, 042, 027, 041 DESIGN | 10-11 voices each | Mostly C++/Rust; bind clippy/clang-tidy where they exist |
| 13 | Generic names (util/common/base), stuttering names, public mutable fields (ADV041, ADV093, ADV020) | syntax | NONE | 9-11 voices | Very cheap, new |
| 14 | Async blocking, lock across await, task leak (ADV066, ADV073, ADV025) | effects | NONE | 4-10 voices; Rousos data: thread-pool exhaustion | C#/Go/Rust adapters |
| 15 | Dependency hygiene (ADV051) | structural | VET DESIGN | 10 voices | Already planned |

### 5.2 Meta-advice for how frob should run lints (cluster lint-adoption, from Google's Tricorder paper chapter and Testing Blog)

Only deploy checks with low false-positive rates and count perceived false positives (swe-ch20 Usability); show findings on changed lines and in review, not whole-program scores (swe-ch20; gtb mutation-testing: tuning cut the not-useful rate from 80 to about 15 percent); attach autofixes; project-level not per-user configuration; track a per-rule not-useful rate and disable rules with high rates (swe-ch20 Feedback Channels); scope suppressions narrowly with a reason (Google Python 2.1, Turner); a compiler-warnings-as-errors baseline from day one (Turner, LLVM, TigerStyle); do not hard-limit length/complexity (gtb hackable-projects). All of this matches frob's baseline, ratchet and EXC design; the new idea is a measured per-rule not-useful rate.

### 5.3 Do not lint (taste, contested, or tool-owned)

Layout and ordering (ADV017, ADV026, ADV068, ADV056): bind a formatter and say so (Google swe-ch08: automate; Black: line length 88 measured). Language policies with real splits: exceptions vs status, auto/var, forward declarations, brace init, default args vs overloads, unsigned counts, pass by value vs const ref, short vs long names. Judgment items (tier human): unclear name, leaky abstraction, premature abstraction, error context, comment-explains-why, SRP.

### 5.4 Already in frob-v2 per this evidence

NEAT001 (fn size: contested, keep advisory), NEAT002, NEAT013, NEAT031 (dispatcher; supported by open-closed-conditionals, 3 voices), CYCLE001 (3 voices), TODO001/002 (5 voices, plus Luu's data on TODO in error handlers). Designed and well supported: NEAT003, 004, 012, 016, 021, 022, 041-044, DOC001, DUP, SYS009, COH001/002. COH003 (levels) and COH004 (vocabularies) have weak support (5 voices, no data; human-tier).



## 6. Advice catalogue (120 normalised items; ADV ids ordered by score)

Atomic items (2,483) with source, location, paraphrase, mistake, reason, evidence type, language, stance, tax, tier, label are in items-all.jsonl next to this file's creators/ folder.

| Id | Normalised item (rule statement) | Tax | Tier | frob-v2 today | Weighted voices: flag / cond / oppose | On-topic items | Languages | Consensus |
|---|---|---|---|---|---|---|---|---|
| ADV001 | hidden-global-state: Flag reads/writes of global or singleton state; make dependencies explicit. | EVO.STR.ARCH | structural | DESIGN note NEAT012 hidden-state-read (scope graph) | 14.0 / 2.5 / 0.0 | 29 | any:11, cpp:7, go:6, csharp:3, python:2 | consensus-for |
| ADV002 | naming-convention: Flag names violating the language's naming conventions. | EVO.DOC.NAME | syntax | NONE in v2 (language adapters + bound tools; clippy/ruff N rules) | 15.0 / 2.0 / 0.5 | 52 | csharp:9, any:8, cpp:7, rust:7, go:7 | consensus-for |
| ADV003 | perf-algorithmic: Flag accidental quadratic behaviour, allocation in loops, per-item calls that could be batched. | FUN.PERF | types | NONE (clippy perf group via BIND; quadratic needs types/effects) | 12.0 / 4.0 / 0.0 | 20 | cpp:7, any:7, python:3, rust:1, go:1 | consensus-for |
| ADV004 | primitive-obsession: Flag primitives used for ids/units/domain values; use strong types. | EVO.DOC.LANG | types | DESIGN note NEAT022/NEAT023 (strong types); needs types | 15.5 / 3.0 / 2.0 | 33 | any:19, cpp:8, python:2, rust:1, other:1 | consensus-for |
| ADV005 | deep-inheritance: Flag implementation inheritance, deep hierarchies and gratuitous virtuals; prefer composition. | EVO.STR.ARCH | structural | NONE (design family ARCH could carry inheritance depth) | 12.5 / 2.5 / 0.0 | 29 | cpp:15, any:9, python:3, csharp:2, other:1 | consensus-for |
| ADV006 | weakest-param-type: Flag parameters demanding stronger types than needed. | FUN.INT | types | DESIGN note NEAT020/NEAT021 | 12.0 / 2.0 / 0.0 | 22 | rust:6, cpp:5, go:4, any:3, python:3 | consensus-for |
| ADV007 | raw-loop-vs-algorithm: Flag hand-written loops where a named algorithm/iterator pipeline exists (opposite: loops are fine/clearer). | EVO.STR.SOL | syntax | DESIGN NEAT006 raw-loop (Pn, bound tools: clippy needless_range_loop etc.) | 11.5 / 5.0 / 1.0 | 25 | cpp:13, python:6, any:5, rust:1, go:1 | contested* |
| ADV008 | cleanup-on-all-paths: Flag resource cleanup that does not run on all paths; use RAII/defer/using. | FUN.RES | structural | NONE (needs resource vocabulary; Unresolved-by-default) | 12.0 / 3.0 / 1.0 | 27 | cpp:12, python:4, any:3, c:2, go:2 | consensus-for |
| ADV009 | inject-dependencies: Inject dependencies and wrap external APIs (DI containers contested). | EVO.STR.ARCH | effects | DESIGN note NEAT014-018 injected-dependency-missing | 11.5 / 4.0 / 1.0 | 26 | any:13, python:4, java:4, csharp:3, cpp:2 | contested* |
| ADV010 | assertions: Assert invariants / fail fast (contested whether in production). | FUN.CHK | human | NONE (contested) | 11.0 / 2.0 / 0.0 | 20 | cpp:8, any:4, c:3, other:3, rust:1 | consensus-for |
| ADV011 | nesting-depth: Flag deep nesting; prefer guard clauses and early returns. | EVO.STR.ORG | syntax | DESIGN NEAT004 | 12.0 / 2.5 / 1.0 | 24 | any:11, cpp:4, go:4, python:3, rust:2 | consensus-for |
| ADV012 | api-compat: Flag breaking API changes; treat observable behaviour as contract (Hyrum's law). | FUN.INT | structural | DESIGN DEPR/REL/VERSION (unbumped API), SYS006 contract skew | 12.0 / 2.5 / 1.0 | 25 | any:9, cpp:5, csharp:5, rust:3, go:2 | consensus-for |
| ADV013 | missing-public-doc: Flag public API without documentation, or doc comments not in the required form. | EVO.DOC.COMMENT | syntax | DESIGN DOC001 public items documented; COV | 11.0 / 1.5 / 0.0 | 30 | any:10, python:9, rust:3, go:3, cpp:2 | consensus-for |
| ADV014 | immutability: Flag mutable-by-default data; prefer const/immutable. | EVO.DOC.LANG | syntax | DESIGN note NEAT036 unnecessary-mutation (language-level) | 10.5 / 5.0 / 1.0 | 30 | cpp:18, any:7, csharp:2, other:1, kotlin:1 | consensus-for |
| ADV015 | swallowed-error: Flag errors that are silently ignored. | FUN.CHK | structural | NONE (error-handling family absent in rules.md; EXC is waiver family) | 10.5 / 2.0 / 0.0 | 17 | any:5, cpp:4, go:2, c:2, python:2 | consensus-for |
| ADV016 | bool-flag-param: Flag boolean flag parameters (use enums, separate functions or options). | FUN.INT | syntax | DESIGN NEAT003 boolean-flag-parameter | 9.5 / 4.0 / 0.0 | 18 | cpp:6, rust:4, csharp:3, any:3, python:2 | consensus-for |
| ADV017 | format-rules: Enforce specific layout rules (indentation, blank lines, braces, trailing commas). | EVO.VIS | syntax | NONE (bind formatter) | 10.0 / 3.0 / 0.0 | 38 | python:13, cpp:9, c:5, any:4, java:3 | consensus-for |
| ADV018 | copy-paste-dup: Flag copy-pasted code and duplicated state. | EVO.STR.ORG | structural | DESIGN DUP clone rungs R1-R5 (rules.md) | 10.5 / 0.0 / 0.0 | 17 | any:12, cpp:5, go:1 | consensus-for |
| ADV019 | casts: Flag C-style casts and unchecked downcasts. | FUN.CHK | syntax | DESIGN note NEAT042 powerful-cast | 9.5 / 2.0 / 0.0 | 14 | cpp:10, other:1, go:1, java:1, ts:1 | consensus-for |
| ADV020 | encapsulation: Flag public mutable fields and trivial accessor boilerplate (contested for accessors). | EVO.DOC.LANG | syntax | NONE | 8.5 / 4.0 / 0.0 | 18 | cpp:6, python:4, any:3, csharp:3, rust:2 | consensus-for |
| ADV021 | raw-owning-pointer: Flag raw owning pointers and manual new/delete; prefer owning types. | FUN.RES | types | DESIGN note NEAT043 raw-owning-pointer | 9.5 / 1.5 / 0.0 | 31 | cpp:31 | consensus-for |
| ADV022 | premature-abstraction: Flag speculative generality, premature abstraction and clever metaprogramming (YAGNI). | EVO.STR.SOL | human | NONE (heuristic: single-implementor interface, one-call-site helper => structural?) | 10.5 / 4.0 / 1.5 | 35 | any:25, cpp:3, go:3, csharp:3, python:1 | consensus-for |
| ADV023 | public-surface: Flag public API surface wider than needed. | EVO.STR.ARCH | structural | DESIGN SYS009 SYS-SURFACE, COV undocumented public symbol | 12.0 / 2.5 / 2.0 | 23 | any:10, cpp:4, rust:3, csharp:2, other:1 | consensus-for |
| ADV024 | reinvent-stdlib: Flag hand-rolled code duplicating the standard library or an established idiom. | EVO.STR.SOL | structural | NONE (needs idiom vocabulary; NEAT006 covers only loops) | 9.5 / 1.0 / 0.0 | 22 | cpp:10, python:6, any:3, c:1, go:1 | consensus-for |
| ADV025 | task-leak: Flag goroutine/task leaks and ignoring cancellation; prefer structured concurrency. | FUN.TIM | effects | NONE | 10.0 / 0.0 / 0.0 | 17 | go:8, cpp:5, kotlin:2, any:1, csharp:1 | consensus-for |
| ADV026 | autoformat-no-bikeshed: Use an automatic formatter and do not review layout by hand. | EVO.VIS | syntax | NONE as rule; belongs to bound formatter (BIND); policy: do not lint layout | 9.5 / 4.0 / 1.0 | 30 | any:17, python:5, cpp:2, rust:2, go:2 | consensus-for |
| ADV027 | unclear-name: Flag unclear, ambiguous, misleading or inconsistently chosen names. | EVO.DOC.NAME | human | NONE (partial syntax: single-letter, abbreviations vocabulary) | 11.5 / 0.0 / 1.0 | 25 | any:18, cpp:4, c:1, python:1, csharp:1 | consensus-for |
| ADV028 | leaky-abstraction: Flag leaky abstractions and APIs easy to misuse. | EVO.STR.ARCH | human | NONE | 9.5 / 1.0 / 0.0 | 15 | any:11, cpp:2, other:1, rust:1, java:1 | consensus-for |
| ADV029 | name-lies-about-effect: Flag names that promise less than the function does (e.g. get that mutates, find that does work). | EVO.DOC.NAME | effects | DESIGN NEAT016 name-effect-mismatch | 9.0 / 1.0 / 0.0 | 14 | any:5, cpp:2, python:2, other:2, rust:1 | consensus-for |
| ADV030 | comment-restates-code: Flag comments that merely restate the code. | EVO.DOC.COMMENT | human | NONE (weak syntax heuristic: comment tokens equal identifier tokens) | 9.0 / 1.0 / 0.0 | 19 | any:8, c:2, cpp:2, go:2, python:2 | consensus-for |
| ADV031 | error-lacks-context: Flag errors without context, and log-and-return handling. | FUN.CHK | human | NONE | 9.5 / 0.0 / 0.0 | 17 | go:10, python:3, any:2, cpp:1, rust:1 | consensus-for |
| ADV032 | positional-params-confusable: Flag adjacent parameters of the same primitive type that callers can swap, or long positional literals. | FUN.INT | types | DESIGN note NEAT022 swappable-primitive-parameters (needs types) | 9.5 / 0.0 / 0.0 | 11 | any:4, go:3, cpp:2, other:1, kotlin:1 | consensus-for |
| ADV033 | two-phase-init: Flag two-phase initialisation, invalid default states and work in constructors. | FUN.INT | syntax | DESIGN note NEAT027 half-built-object | 8.5 / 1.5 / 0.0 | 21 | cpp:11, csharp:4, go:3, any:2, rust:1 | consensus-for |
| ADV034 | illegal-states: Flag types that permit illegal states (flags plus data, sentinel values, unions); make illegal states unrepresentable. | FUN.CHK | types | DESIGN note NEAT023 precondition-outside-type, NEAT024 | 8.0 / 2.0 / 0.0 | 19 | any:11, cpp:3, python:2, java:2, other:1 | consensus-for |
| ADV035 | rule-of-zero: Flag special-member-function mistakes (rule of zero/five, moves, virtual dtors). | FUN.RES | types | NONE (clang-tidy cppcoreguidelines-special-member-functions) | 8.5 / 1.0 / 0.0 | 20 | cpp:20 | consensus-for |
| ADV036 | command-query: Flag queries with side effects, output parameters and mutated arguments. | FUN.INT | effects | DESIGN NEAT019 (off by default), NEAT018 out-parameter | 9.5 / 2.0 / 1.0 | 18 | cpp:9, any:7, csharp:2, rust:1 | consensus-for |
| ADV037 | options-defaults: Flag option/default/overload design problems. | FUN.INT | syntax | NONE (bool/option params partly NEAT003) | 9.0 / 3.0 / 1.0 | 22 | cpp:6, csharp:6, any:4, go:2, rust:1 | consensus-for |
| ADV038 | shared-mutable: Flag shared mutable state without synchronisation and raw sync primitives. | FUN.TIM | effects | DESIGN note NEAT044 raw-sync-primitive | 7.5 / 2.0 / 0.0 | 15 | cpp:6, any:3, go:3, python:1, csharp:1 | consensus-for |
| ADV039 | low-cohesion-module: Flag types/modules doing several unrelated jobs (god types, SRP violations). | EVO.STR.ORG | structural | DESIGN COH001 (slices), rules.md LCOM in ARCH/LARGE | 9.0 / 2.0 / 1.0 | 19 | any:14, python:2, go:1, kotlin:1, csharp:1 | consensus-for |
| ADV040 | functional-core: Keep a pure core and push IO to a shell. | EVO.STR.ARCH | effects | DESIGN COH002 / NEAT014-017 (effects capability) | 8.0 / 0.5 / 0.0 | 22 | any:14, python:6, cpp:2, rust:1 | consensus-for |
| ADV041 | generic-name-util-common: Flag generic names such as util, common, base, manager, helper. | EVO.DOC.NAME | syntax | NONE (file/module name vocabulary; cheap) | 8.0 / 0.0 / 0.0 | 16 | any:5, go:5, cpp:3, csharp:2, other:1 | consensus-for |
| ADV042 | layering: Flag layering violations and wrong dependency direction. | EVO.STR.ARCH | structural | DESIGN ARCH (rules.md), INV forbidden import | 7.0 / 2.0 / 0.0 | 16 | any:13, cpp:2, go:1 | consensus-for |
| ADV043 | short-names-scope: Contested: short names for small scopes versus no abbreviations at all. | EVO.DOC.NAME | syntax | NONE (contested; profile knob if ever) | 5.0 / 7.0 / 0.5 | 19 | any:6, cpp:4, c:3, go:3, java:2 | contested* |
| ADV044 | uninitialized-member: Flag uninitialised members and ambiguous initialisation syntax. | FUN.RES | syntax | NONE (compiler warnings / clang-tidy) | 6.0 / 3.0 / 0.0 | 16 | cpp:15, rust:1 | consensus-for |
| ADV045 | panic-in-library: Flag panic/exit/fatal in library code. | FUN.CHK | structural | DESIGN note NEAT013 callee vocabulary (exit/abort) partly; PF-14 | 6.0 / 3.0 / 0.0 | 12 | go:5, rust:3, any:3, c:1 | consensus-for |
| ADV046 | test-behavior: Test behaviour not implementation; flag change-detector tests. | TEST | human | NONE | 6.0 / 2.0 / 0.0 | 24 | any:20, java:3, cpp:2, go:1, ts:1 | consensus-for |
| ADV047 | wildcard-import: Flag wildcard imports and using-directives. | EVO.STR.ARCH | syntax | DESIGN note NEAT041 enum-glob-in-match (enum variant globs only) | 5.5 / 3.0 / 0.0 | 15 | cpp:7, rust:2, go:2, other:2, python:1 | consensus-for |
| ADV048 | exceptions-policy: Contested: exceptions versus return codes; exceptions for control flow. | FUN.CHK | human | NONE (contested; language-policy choice) | 8.5 / 2.5 / 2.0 | 18 | cpp:10, any:4, csharp:3, go:1 | contested* |
| ADV049 | catch-all-handler: Flag catch-all handlers and overly broad try bodies. | FUN.CHK | syntax | NONE | 6.0 / 1.5 / 0.0 | 10 | csharp:4, python:3, any:2, cpp:1 | consensus-for |
| ADV050 | premature-optimization: Flag optimisation without measurement. | FUN.PERF | human | NONE | 11.0 / 0.0 / 3.0 | 18 | any:9, cpp:6, java:2, rust:1 | contested |
| ADV051 | dependency-hygiene: Dependency hygiene (minimal, pinned, vetted). | FUN.SUP | structural | DESIGN VET (dependency vetting), PACK drift locks | 6.5 / 3.0 / 1.0 | 16 | any:9, cpp:2, rust:2, go:2, python:1 | consensus-for |
| ADV052 | comment-explains-why: Comments should explain why, not what; public API needs comments (opposite: comments are a failure to express intent in code). | EVO.DOC.COMMENT | human | DESIGN DOC001 only checks existence; NARR for ticket narrative | 8.5 / 2.0 / 2.0 | 22 | any:15, cpp:4, c:1, go:1, python:1 | contested* |
| ADV053 | complexity: Flag high cyclomatic or cognitive complexity and convoluted conditional expressions. | EVO.STR.ORG | syntax | DESIGN NEAT005 cognitive-complexity | 8.0 / 1.5 / 1.5 | 16 | any:7, cpp:4, go:2, c:1, rust:1 | consensus-for |
| ADV054 | cpp-modern-idioms: Flag legacy C++ idioms with modern replacements (endl, NULL, typedef...). | FUN.PERF | syntax | NONE (clang-tidy modernize-*) | 6.0 / 1.0 / 0.0 | 21 | cpp:20, c:1 | consensus-for |
| ADV055 | mock-overuse: Flag over-mocking; prefer state and real objects. | TEST | structural | NONE (could count test-double constructs per test) | 6.0 / 2.5 / 0.5 | 27 | any:22, java:5, python:3, other:1 | contested* |
| ADV056 | import-order: Flag imports/includes not in the required order or grouping. | EVO.VIS | syntax | NONE (bind formatter/linter) | 6.0 / 1.0 / 0.0 | 11 | cpp:5, python:5, rust:1 | consensus-for |
| ADV057 | null-as-value: Flag null/None used as a normal value or error signal; flag nullable APIs. | FUN.CHK | types | NONE (language features; tool-bound) | 7.5 / 1.0 / 1.0 | 19 | csharp:7, any:5, cpp:3, go:2, java:1 | consensus-for |
| ADV058 | go-misc: Go-specific misc rules. | FUN.TIM | syntax | NONE (bind golangci) | 5.0 / 3.0 / 0.0 | 10 | go:10 | consensus-for |
| ADV059 | fn-params-count: Flag functions with more than about 4-6 parameters. | EVO.STR.ORG | syntax | IMPL NEAT002 | 5.5 / 1.5 / 0.0 | 12 | any:7, cpp:2, rust:2, go:1 | consensus-for |
| ADV060 | flaky-test: Flag flaky/non-deterministic tests (sleeps, order dependence, shared state). | TEST | effects | NONE (sleep/clock/random in tests: callee vocabulary like NEAT013 scoped to tests); DESIGN TIME003 test date literal | 5.5 / 1.0 / 0.0 | 26 | any:19, cpp:4, go:1, python:1, ts:1 | consensus-for |
| ADV061 | lint-adoption: How to run lints: low false positives, new code only, autofix, suppression hygiene. | FUN.SUP | human | DESIGN ratchet, baseline, quarantine (rules.md section 6) cover new-code-only and suppression hygiene | 5.0 / 2.0 / 0.0 | 18 | any:12, cpp:4, python:1, csharp:1 | consensus-for |
| ADV062 | logging: Logging policy. | FUN.PERF | human | NONE (contrast: owner global rule says log everything; Chromium/Linux disagree) | 6.0 / 0.0 / 0.0 | 7 | go:2, any:2, cpp:1, c:1, python:1 | consensus-for |
| ADV063 | pass-by-value-vs-ref: Contested: when to pass by value versus reference. | FUN.INT | types | NONE (contested) | 5.0 / 4.0 / 1.0 | 12 | cpp:11, go:1 | contested* |
| ADV064 | thin-framework-hook: Flag framework hooks/dispatchers that contain logic instead of delegating. | EVO.STR.ARCH | structural | DESIGN NEAT030 thin-hook, NEAT031 dispatch (IMPL NEAT031) | 5.5 / 0.0 / 0.0 | 7 | any:4, go:1, python:1, java:1, kotlin:1 | consensus-for |
| ADV065 | boy-scout-prefactor: Separate refactoring from behaviour change; tidy as you go. | EVO.STR.ORG | human | DESIGN PM/commit discipline (pm-enforcement.md); mixed-change detection is structural on diffs | 4.5 / 1.5 / 0.0 | 11 | any:11 | consensus-for |
| ADV066 | async-blocking: Flag blocking on async code, async void and Task misuse. | FUN.TIM | effects | NONE (bind Roslyn analyzers VSTHRD/ASP0xxx [unsourced]) | 4.0 / 2.0 / 0.0 | 24 | csharp:21, cpp:2, any:1 | consensus-for |
| ADV067 | untracked-todo: Flag TODO/FIXME comments with no owner or ticket. | EVO.DOC.COMMENT | syntax | IMPL TODO001/TODO002 | 4.5 / 1.0 / 0.0 | 9 | any:7, cpp:1, java:1 | consensus-for |
| ADV068 | line-length: Enforce a maximum line length (the number is contested). | EVO.VIS | syntax | NONE (bind formatter) | 7.0 / 2.0 / 2.0 | 16 | python:5, any:4, go:3, cpp:2, java:1 | consensus-for |
| ADV069 | implicit-conversion-ops: Flag implicit conversions and surprising operator overloads. | FUN.INT | syntax | NONE | 4.0 / 2.0 / 0.0 | 10 | cpp:8, rust:1, csharp:1 | consensus-for |
| ADV070 | wildcard-match: Flag default/wildcard arms on matches over closed enums, and implicit fallthrough. | FUN.LOG | syntax | DESIGN note NEAT041 enum-glob-in-match; clippy wildcard_enum_match_arm exists in index | 6.0 / 1.0 / 1.0 | 12 | cpp:4, java:4, rust:3, other:2 | consensus-for |
| ADV071 | numeric-conversions: Flag lossy, mixed-sign or implicit numeric conversions. | FUN.LOG | types | NONE (bind clippy cast_* / clang-tidy) | 5.0 / 0.0 / 0.0 | 7 | cpp:6, csharp:1 | consensus-for |
| ADV072 | macro-use: Flag macros where inline/template/constexpr works. | EVO.STR.SOL | syntax | NONE | 5.0 / 0.0 / 0.0 | 6 | cpp:3, c:3 | consensus-for |
| ADV073 | lock-across-await: Flag locks held across IO/await. | FUN.TIM | effects | NONE | 4.0 / 1.0 / 0.0 | 9 | cpp:6, rust:2, any:1 | consensus-for |
| ADV074 | magic-number: Flag magic numbers and hard-coded values. | EVO.DOC.NAME | syntax | DESIGN NEAT009 magic-value (bound tool only) | 4.5 / 0.0 / 0.0 | 8 | any:5, cpp:3, csharp:1 | consensus-for |
| ADV075 | option-vs-sentinel: Contested: use Option/optional versus sentinel values or out-of-band signals. | FUN.CHK | types | DESIGN note NEAT024 option-with-many-none-paths | 4.5 / 3.0 / 1.0 | 13 | any:5, cpp:4, go:1, java:1, python:1 | consensus-for |
| ADV076 | dead-code: Flag dead code, unused parameters, commented-out code and stale flags. | EVO.STR.ORG | structural | DESIGN DEAD (rules.md family; no code) | 4.5 / 0.0 / 0.0 | 10 | any:5, cpp:4, python:2 | consensus-for |
| ADV077 | c-unsafe-apis: Flag unsafe C idioms (varargs, memset on objects, NUL assumptions, goto). | SEC | syntax | DESIGN SEC family partially; NONE specific | 4.0 / 1.0 / 0.0 | 8 | cpp:7, c:1 | consensus-for |
| ADV078 | template-restraint: Flag template metaprogramming beyond need. | FUN.PERF | human | NONE | 4.0 / 1.0 / 0.0 | 6 | cpp:5, rust:1 | consensus-for |
| ADV079 | member-ordering: Flag members or parameters not in the conventional order. | EVO.VIS | syntax | NONE | 6.0 / 0.0 / 1.0 | 13 | cpp:5, kotlin:3, rust:2, java:2, go:1 | consensus-for |
| ADV080 | function-vs-class: Flag classes that should be free functions (static-only classes, doer objects). | EVO.STR.SOL | syntax | NONE | 6.0 / 0.0 / 1.0 | 8 | python:3, cpp:2, rust:2, any:1 | consensus-for |
| ADV081 | lambda-capture: Flag risky lambda capture/shape. | FUN.RES | syntax | NONE | 4.0 / 1.0 / 0.0 | 6 | cpp:4, python:1, csharp:1 | consensus-for |
| ADV082 | test-assertions: Flag weak or noisy assertions in tests. | TEST | syntax | NONE (test without assertion is cheap syntax) | 4.0 / 1.0 / 0.0 | 15 | any:8, go:4, cpp:2, java:2, kotlin:1 | consensus-for |
| ADV083 | stringly-typed: Flag strings used where a type/enum belongs. | EVO.DOC.LANG | types | NONE | 4.0 / 1.0 / 0.0 | 5 | any:2, go:1, csharp:1, java:1 | consensus-for |
| ADV084 | py-idioms: Python-specific footguns. | EVO.STR.SOL | syntax | NONE (bind ruff B/PLW rules per prior note) | 3.0 / 3.0 / 0.0 | 13 | python:13 | consensus-for |
| ADV085 | dont-mock-types-you-dont-own: Flag mocking types you do not own. | TEST | types | NONE | 3.5 / 2.0 / 0.0 | 6 | python:3, any:3, java:2 | consensus-for |
| ADV086 | parse-dont-validate: Flag repeated validation of raw data instead of parsing once into a type at the boundary. | FUN.CHK | types | DESIGN note NEAT025 validate-returns-nothing | 4.5 / 1.5 / 1.0 | 15 | any:10, rust:2, csharp:2, java:1 | consensus-for |
| ADV087 | opaque-error-type: Flag opaque/stringly error types that callers cannot match. | FUN.CHK | types | NONE | 6.5 / 3.0 / 3.0 | 14 | rust:6, go:6, cpp:2 | contested |
| ADV088 | test-naming: Test naming and one scenario per test. | TEST | syntax | NONE | 2.5 / 2.0 / 0.0 | 9 | any:5, go:2, kotlin:2, cpp:1, java:1 | consensus-for |
| ADV089 | variable-scope: Flag wide variable scope and shadowing. | EVO.STR.ORG | syntax | NONE | 5.0 / 0.0 / 1.0 | 11 | cpp:6, go:3, any:1, java:1 | consensus-for |
| ADV090 | circular-dependency: Flag circular dependencies. | EVO.STR.ARCH | structural | IMPL CYCLE001 | 3.0 / 1.0 / 0.0 | 4 | python:2, cpp:1, any:1 | consensus-for |
| ADV091 | ambient-calls: Flag ambient time/rng/env/fs calls from deep code. | FUN.INT | syntax | IMPL NEAT013 ambient-source-call | 3.5 / 0.0 / 0.0 | 4 | any:2, other:1, go:1 | consensus-for |
| ADV092 | go-interface-pollution: Flag Go interfaces defined by producers or too early. | FUN.INT | structural | NONE (Go adapter vocabulary; revive/staticcheck) | 3.0 / 1.0 / 0.0 | 4 | go:4 | consensus-for |
| ADV093 | stuttering-names: Flag names that repeat the package/type name. | EVO.DOC.NAME | syntax | NONE | 3.0 / 1.0 / 0.0 | 5 | go:3, other:1, rust:1 | consensus-for |
| ADV094 | fakes-over-mocks: Prefer fakes (with conformance tests) to mocks. | TEST | human | NONE | 3.0 / 1.0 / 0.0 | 15 | any:12, java:3, python:2 | consensus-for |
| ADV095 | mixed-abstraction-levels: Flag functions that mix abstraction levels (high-level steps next to low-level detail). | EVO.STR.ORG | structural | DESIGN NEAT008 note / COH003 (needs layer map; advisory) | 3.5 / 0.0 / 0.0 | 6 | any:5, python:1, java:1, go:1 | consensus-for |
| ADV096 | logic-in-tests: Flag logic in tests; prefer DAMP, local setup. | TEST | syntax | NONE (control-flow statements inside test bodies is cheap syntax) | 2.5 / 1.0 / 0.0 | 20 | any:16, cpp:3, java:3, python:2, rust:1 | consensus-for |
| ADV097 | header-hygiene: Flag header/include/linkage hygiene problems in C/C++. | EVO.STR.ARCH | syntax | NONE (C/C++ only; bind clang-tidy/IWYU) | 5.0 / 2.0 / 2.0 | 20 | cpp:19, c:1 | contested |
| ADV098 | type-in-name: Flag names that encode the type or unit (Hungarian notation). | EVO.DOC.NAME | syntax | NONE | 4.0 / 1.0 / 1.0 | 7 | any:2, go:1, python:1, java:1, kotlin:1 | consensus-for |
| ADV099 | stale-comment: Flag comments and docs that disagree with the code. | EVO.DOC.COMMENT | structural | DESIGN DRIFT/AFFECT/DOC families (doc-consistency.md) | 4.5 / 0.0 / 1.0 | 8 | any:8 | consensus-for |
| ADV100 | liskov-substitution: Flag subtypes that break the base type's contract. | EVO.STR.SOL | human | NONE | 3.0 / 0.0 / 0.0 | 3 | python:1, java:1, any:1 | consensus-for |
| ADV101 | fn-size: Flag functions longer than a size limit; keep functions short (opposite view: long functions are fine if the module is deep and the body is straight-line). | EVO.STR.ORG | syntax | IMPL NEAT001 (statement count) | 6.0 / 4.0 / 3.5 | 25 | any:16, cpp:4, rust:2, c:1, python:1 | contested |
| ADV102 | repo-layout: Repository/package layout conventions. | EVO.STR.ARCH | human | NONE (profile/doc) | 2.0 / 1.5 / 0.0 | 4 | rust:1, go:1, python:1, any:1 | consensus-for |
| ADV103 | dangling-refs: Flag references/views/temporaries that can dangle. | FUN.RES | types | NONE (compiler/borrowck/sanitizers) | 2.0 / 1.0 / 0.0 | 9 | cpp:9 | consensus-for |
| ADV104 | coverage-as-goal: Flag coverage percentage used as a goal or gate (opposite: coverage thresholds are useful). | TEST | structural | DESIGN TEST floors / COV (note: floors are exactly the contested practice) | 5.5 / 1.5 / 2.5 | 14 | any:12, go:2 | contested |
| ADV105 | rust-idioms: Rust-specific idioms. | FUN.INT | types | NONE (bind clippy) | 2.0 / 1.0 / 0.0 | 5 | rust:5 | consensus-for |
| ADV106 | property-tests: Property/fuzz/characterisation tests. | TEST | human | DESIGN INV property test required | 2.5 / 0.0 / 0.0 | 4 | any:4 | consensus-for |
| ADV107 | shallow-module: Flag shallow modules and pass-through methods that add no abstraction. | EVO.STR.ORG | structural | NONE (could be a COH/ARCH metric: interface size vs body size) | 2.0 / 1.0 / 0.0 | 7 | any:7 | consensus-for |
| ADV108 | namespace-depth: Flag deep namespace nesting. | EVO.STR.ARCH | syntax | NONE | 2.0 / 0.0 / 0.0 | 4 | cpp:3, csharp:1 | consensus-for |
| ADV109 | smart-ptr-params: Flag smart pointers passed or dereferenced where a reference suffices. | FUN.INT | types | NONE | 2.0 / 0.0 / 0.0 | 4 | cpp:4 | consensus-for |
| ADV110 | long-file: Flag very long files, or more than one major type per file. | EVO.STR.ARCH | syntax | DESIGN LARGE (rules.md family; no code) | 1.0 / 2.0 / 0.0 | 4 | go:1, java:1, csharp:1, kotlin:1 | conditional |
| ADV111 | module-public-api: Only a module's public API may be used across boundaries. | EVO.STR.ARCH | structural | DESIGN SYS009 SYS-SURFACE / INV forbidden import | 2.0 / 0.0 / 0.0 | 3 | python:2, any:1 | consensus-for |
| ADV112 | test-pyramid: Balance test sizes (many small, few large). | TEST | structural | DESIGN TEST family (bindings, floors), frob-tests | 3.0 / 2.0 / 1.5 | 25 | any:24, ts:1 | contested |
| ADV113 | open-closed-conditionals: Flag type/tag switches that belong in dispatch (open-closed). | EVO.STR.ARCH | syntax | DESIGN NEAT031 dispatch-site-owns-logic (IMPL) | 1.5 / 0.5 / 0.0 | 4 | any:4, csharp:1, java:1 | consensus-for |
| ADV114 | c-arrays-pointers: Flag C arrays and pointer arithmetic where containers/spans/indices exist. | FUN.CHK | syntax | NONE | 2.0 / 2.0 / 1.0 | 8 | cpp:5, any:1, c:1, other:1 | contested |
| ADV115 | demeter-chains: Flag long call chains reaching through objects (Law of Demeter). | EVO.STR.ORG | syntax | NONE | 1.5 / 0.0 / 0.0 | 2 | csharp:1, any:1 | thin |
| ADV116 | section-comments-in-fn: Flag comments that label phases inside one function body (extract functions instead). | EVO.DOC.COMMENT | syntax | DESIGN NEAT007 | 1.5 / 0.0 / 0.0 | 2 | any:2 | thin |
| ADV117 | security-misc: Security-flavoured idioms. | SEC | syntax | DESIGN SEC family | 1.0 / 0.0 / 0.0 | 1 | go:1 | thin |
| ADV118 | reserve-capacity: Flag reserve/capacity calls that defeat growth strategy or are misused. | FUN.PERF | types | DESIGN note NEAT045 reserve-in-reusable-api | 0.5 / 0.0 / 0.0 | 1 | cpp:1, rust:1 | thin |
| ADV119 | auto-usage: Contested: when auto/var is allowed. | EVO.DOC.LANG | syntax | NONE (contested; no rule) | 1.0 / 4.0 / 2.0 | 8 | cpp:5, csharp:2, java:1 | contested |
| ADV120 | dup-vs-wrong-abstraction: Contested: remove duplication at once (DRY) versus tolerate duplication until the right abstraction is clear. | EVO.STR.SOL | human | DESIGN (DUP profile choice n=1 vs n=2; neatness 6.0 conflict note) | 0.0 / 0.0 / 3.5 | 5 | any:3, go:1, python:1 | contested* |

## 7. (see section 1.2 for the vetting table)

## 8. Source list (459 units)

| Id | Kind | Author or channel | Title or URL | Status | Items |
|---|---|---|---|---|---|
| S001 | talk | 25msr | GoingNative 2013 C++ Seasoning <https://youtu.be/W2tWOdzgXHA> | full | 15 |
| S002 | talk | CppCon | CppCon 2015: Sean Parent "Better Code: Data Structures" <https://youtu.be/sWgDk-o-6ZE> | full | 7 |
| S003 | talk | CppNow | Sean Parent: Better Code: Concurrency <https://youtu.be/32f6JrQPV8c> | skimmed | 7 |
| S004 | talk | NDC Conferences | Better Code: Concurrency - Sean Parent <https://youtu.be/zULU6Hhp42w> | skimmed | 5 |
| S005 | talk | 25msr | GoingNative 2013 Inheritance Is The Base Class of Evil <https://youtu.be/-ss9XGsENPE> | full | 4 |
| S006 | talk | CppCon | CppCon 2017: Tony Van Eerd "Postmodern C++" <https://youtu.be/QTLn3goa3A8> | full | 7 |
| S007 | talk | CppCon | CppCon 2019: Tony Van Eerd Objects vs Values: Value Oriented Programming in an Object Oriented World <https://youtu.be/2JGH_SWURrI> | full | 9 |
| S008 | talk | CppCon | CppCon 2019: Kate Gregory "Naming is Hard: Let's Do Better" <https://youtu.be/MBRoCdtZOYg> | full | 19 |
| S009 | talk | CppCon | CppCon 2015: Kate Gregory "Stop Teaching C" <https://youtu.be/YnWhqhNdYyk> | full | 9 |
| S010 | talk | ACCU Conference | Simplicity: not just for beginners -  Kate Gregory [ACCU 2018] <https://youtu.be/O50qTuM5OT0> | full | 21 |
| S011 | talk | CppCon | CppCon 2014: Herb Sutter "Back to the Basics! Essentials of Modern C++ Style" <https://youtu.be/xnqTKD8uD64> | full | 13 |
| S012 | talk | CppCon | CppCon 2014: Chandler Carruth "Efficiency with Algorithms, Performance with Data Structures" <https://youtu.be/fHNmRkzxHWs> | full | 9 |
| S013 | talk | CPP_Medium_Rare | C++ and Beyond 2012 - Andrei Alexandrescu: Systematic Error Handling <https://youtu.be/Wa4mt3GXpK0> | skimmed | 9 |
| S014 | talk | CppCon | CppCon 2018: Andrei Alexandrescu "Expect the expected" <https://youtu.be/PH4WBuE1BHI> | full | 6 |
| S015 | talk | CppCon | CppCon 2018: Ben Deane "Easy to Use, Hard to Misuse: Declarative Style in C++" <https://youtu.be/I52uPJSoAT4> | full | 9 |
| S016 | talk | Code Blacksmith | Exception Safety - Learn Modern C++ <https://youtu.be/X4TNDFlXzOo> | full | 2 |
| S017 | talk | Casey Muratori | Designing and Evaluating Reusable Components - 2004 <https://youtu.be/ZQ5_u8Lgvyk> | full | 9 |
| S018 | talk | Better Software Conference | Casey Muratori - The Big OOPs: Anatomy of a Thirty-five-year Mistake - BSC 2025 <https://youtu.be/wo84LFzx5nI> | skimmed | 6 |
| S019 | talk | Molly Rocket | Where Does Bad Code Come From? <https://youtu.be/7YpFGkG-u1w> | full | 3 |
| S020 | talk | DevGAMM | Preventing the Collapse of Civilization / Jonathan Blow (Thekla, Inc) <https://youtu.be/ZSRHeXYDLko> | skimmed | 3 |
| S021 | talk | CppCon | CppCon 2014: Mike Acton "Data-Oriented Design and C++" <https://youtu.be/rX0ItVEVjHc> | skimmed | 9 |
| S022 | talk | C++ Russia -     Cpp | Titus Winters - Designing for the long term: Invariants, knobs, extensions, and Hyrum's Law <https://youtu.be/Wx9nzYTUd-c> | full | 9 |
| S023 | talk | CppCon | CppCon 2018: Titus Winters "Modern C++ Design (part 1 of 2)" <https://youtu.be/xTdeZ4MxbKo> | full | 9 |
| S024 | talk | CppCon | CppCon 2016: Jason Turner "Practical Performance Practices" <https://youtu.be/uzF4u9KgUWI> | full | 12 |
| S025 | talk | CppCon | API Structure and Technique: Learnings from C++ Code Review - Ben Deane - CppCon 2025 <https://youtu.be/dLsZ3t_kG1U> | full | 11 |
| S026 | talk | DevTernity Conference |   Seven Ineffective Coding Habits of Many Programmers (Kevlin Henney) <https://youtu.be/SUIUZ09mnwM> | full | 12 |
| S027 | talk | ACCU Conference | Procedural Programming: It's Back? It Never Went Away - Kevlin Henney [ACCU 2018] <https://youtu.be/mrY6xrWp3Gs> | skimmed | 6 |
| S028 | talk | CppCon | Breaking Dependencies: The SOLID Principles - Klaus Iglberger - CppCon 2020 <https://youtu.be/Ntraj80qN2k> | full | 8 |
| S029 | talk | CppCon | Back to Basics: Designing Classes (part 1 of 2) - Klaus Iglberger - CppCon 2021 <https://youtu.be/motLOioLJfg> | full | 8 |
| S030 | talk | CppCon | CppCon 2018: Jonathan Boccara "105 STL Algorithms in Less Than an Hour" <https://youtu.be/2olsGf6JIkU> | full | 7 |
| S031 | talk | aghuttun | Don't Help the Compiler <https://youtu.be/AKtHxKJRwp4> | full | 11 |
| S032 | talk | Sudeep | WWDC 2015 - Protocol-Oriented Programming in Swift (HD) <https://youtu.be/FlNlyH9uRdI> | full | 7 |
| S033 | talk | CppCon | Value Semantics: Safety, Independence, Projection, & Future of Programming - Dave Abrahams CppCon 22 <https://youtu.be/QthAU-t3PQ4> | full | 7 |
| S034 | web | Abseil | https://abseil.io/tips/1 | full | 4 |
| S035 | web | Abseil | https://abseil.io/tips/108 | full | 3 |
| S036 | web | Abseil | https://abseil.io/tips/11 | full | 3 |
| S037 | web | Abseil | https://abseil.io/tips/116 | full | 4 |
| S038 | web | Abseil | https://abseil.io/tips/117 | full | 2 |
| S039 | web | Abseil | https://abseil.io/tips/119 | full | 3 |
| S040 | web | Abseil | https://abseil.io/tips/122 | full | 4 |
| S041 | web | Abseil | https://abseil.io/tips/124 | full | 2 |
| S042 | web | Abseil | https://abseil.io/tips/126 | full | 2 |
| S043 | web | Abseil | https://abseil.io/tips/130 | full | 3 |
| S044 | web | Abseil | https://abseil.io/tips/131 | full | 3 |
| S045 | web | Abseil | https://abseil.io/tips/134 | full | 2 |
| S046 | web | Abseil | https://abseil.io/tips/135 | full | 3 |
| S047 | web | Abseil | https://abseil.io/tips/140 | full | 6 |
| S048 | web | Abseil | https://abseil.io/tips/141 | full | 3 |
| S049 | web | Abseil | https://abseil.io/tips/147 | full | 2 |
| S050 | web | Abseil | https://abseil.io/tips/153 | full | 2 |
| S051 | web | Abseil | https://abseil.io/tips/163 | full | 2 |
| S052 | web | Abseil | https://abseil.io/tips/171 | full | 1 |
| S053 | web | Abseil | https://abseil.io/tips/181 | full | 4 |
| S054 | web | Abseil | https://abseil.io/tips/3 | full | 1 |
| S055 | web | Abseil | https://abseil.io/tips/36 | full | 1 |
| S056 | web | Abseil | https://abseil.io/tips/42 | full | 2 |
| S057 | web | Abseil | https://abseil.io/tips/49 | full | 3 |
| S058 | web | Abseil | https://abseil.io/tips/5 | full | 2 |
| S059 | web | Abseil | https://abseil.io/tips/55 | full | 1 |
| S060 | web | Abseil | https://abseil.io/tips/59 | full | 1 |
| S061 | web | Abseil | https://abseil.io/tips/61 | full | 2 |
| S062 | web | Abseil | https://abseil.io/tips/76 | full | 3 |
| S063 | web | Abseil | https://abseil.io/tips/88 | full | 2 |
| S064 | web | Abseil | https://abseil.io/tips/93 | full | 3 |
| S065 | web | Abseil | https://abseil.io/tips/94 | full | 2 |
| S066 | web | Acton | https://www.slideshare.net/slideshow/three-big-lies-typical-design-failures-in-game-programming-gdc2010/3637436 | unreadable | 0 |
| S067 | web | Boccara | https://www.fluentcpp.com/2016/12/08/strong-types-for-strong-interfaces/ | full | 3 |
| S068 | web | Chromium | https://raw.githubusercontent.com/chromium/chromium/main/styleguide/c++/c++.md | full | 20 |
| S069 | web | Chromium | https://raw.githubusercontent.com/chromium/chromium/main/styleguide/c++/c++-dos-and-donts.md | full | 16 |
| S070 | web | Stroustrup/Sutter | https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines | skimmed | 197 |
| S071 | web | Google | https://google.github.io/styleguide/cppguide.html | skimmed | 92 |
| S072 | web | Linux | https://www.kernel.org/doc/html/latest/process/coding-style.html | full | 32 |
| S073 | web | LLVM | https://llvm.org/docs/CodingStandards.html | full | 44 |
| S074 | web | Muratori | https://caseymuratori.com/blog_0016 | full | 5 |
| S075 | web | Muratori | https://caseymuratori.com/blog_0024 | full | 0 |
| S076 | web | Muratori | https://caseymuratori.com/blog_0015 | full | 6 |
| S077 | web | Sutter | https://herbsutter.com/2013/06/05/gotw-91-solution-smart-pointer-parameters/ | full | 6 |
| S078 | web | Sutter | https://herbsutter.com/elements-of-modern-c-style/ | full | 8 |
| S079 | web | Sutter | http://www.gotw.ca/publications/mill18.htm | full | 4 |
| S080 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/09-Considering_Correctness.md | full | 1 |
| S081 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/05-Considering_Maintainability.md | full | 5 |
| S082 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/08-Considering_Performance.md | full | 15 |
| S083 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/04-Considering_Safety.md | full | 8 |
| S084 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/03-Style.md | full | 21 |
| S085 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/00-Table_of_Contents.md | full | 0 |
| S086 | web | Turner | https://raw.githubusercontent.com/cpp-best-practices/cppbestpractices/master/02-Use_the_Tools_Available.md | full | 8 |
| S087 | talk | The Go Programming Language | Gopherfest 2015 / Go Proverbs with Rob Pike <https://youtu.be/PAAkCSZUG1c> | full | 6 |
| S088 | talk | dotconferences | dotGo 2015 - Rob Pike - Simplicity is Complicated <https://youtu.be/rFejpH_tAHM> | full | 2 |
| S089 | talk | Stanford | Another Go at Language Design <https://youtu.be/7VcArS4Wpqk> | skimmed | 3 |
| S090 | talk | Russ Cox | Go 2 Drafts Announcement <https://youtu.be/6wIP3rO6On8> | irrelevant | 0 |
| S091 | talk | Singapore Gophers | Opening keynote: Clear is better than clever - GopherCon SG 2019 <https://youtu.be/NwEuRO_w8HE> | full | 5 |
| S092 | talk | GopherCon UK | Golang UK Conference 2016 - Dave Cheney - SOLID Go Design <https://youtu.be/zzAdEt3xZ1M> | full | 1 |
| S093 | talk | InfoQ | Rust's Journey to Async/Await <https://youtu.be/lJ3NC-R3gSI> | skimmed | 0 |
| S094 | talk | Bryan Cantrill | Platform as a Reflection of Values <https://youtu.be/Xhx970_JKX4> | skimmed | 1 |
| S095 | talk | Oxide Computer Company | The Complexity of Simplicity <https://youtu.be/Cum5uN2634o> | skimmed | 3 |
| S096 | talk | ChimiChanga | Andrew Kelley: A Practical Guide to Applying Data Oriented Design (DoD) <https://youtu.be/IroPQ150F6c> | skimmed | 5 |
| S097 | talk | ChariotSolutions | The Road to Zig 1.0 - Andrew Kelley <https://youtu.be/Gv2I7qTux7g> | skimmed | 3 |
| S098 | talk | GOTO Conferences | Debugging Under Fire: Keep your Head when Systems have Lost their Mind  Bryan Cantrill  GOTO 2017 <https://youtu.be/30jNsCVLpAE> | skimmed | 4 |
| S099 | web | Bourgon | https://peter.bourgon.org/go-best-practices-2016/ | full | 8 |
| S100 | web | Bourgon | https://peter.bourgon.org/go-for-industrial-programming/ | full | 9 |
| S101 | web | BurntSushi | https://blog.burntsushi.net/rust-error-handling/ | skimmed | 4 |
| S102 | web | BurntSushi | https://blog.burntsushi.net/ripgrep/ | skimmed | 3 |
| S103 | web | Cantrill | https://bcantrill.dtrace.org/2018/09/28/the-relative-performance-of-c-and-rust/ | full | 1 |
| S104 | web | Cheney | https://dave.cheney.net/2016/08/20/solid-go-design | full | 5 |
| S105 | web | Cheney | https://dave.cheney.net/2017/01/26/context-is-for-cancelation | full | 1 |
| S106 | web | Cheney | https://dave.cheney.net/2012/01/18/why-go-gets-exceptions-right | full | 1 |
| S107 | web | Cheney | https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully | full | 5 |
| S108 | web | Cheney | https://dave.cheney.net/2015/11/05/lets-talk-about-logging | full | 3 |
| S109 | web | Cheney | https://dave.cheney.net/2019/01/27/eliminate-error-handling-by-eliminating-errors | full | 1 |
| S110 | web | Cheney | https://dave.cheney.net/2019/09/24/be-wary-of-functions-which-take-several-parameters-of-the-same-type | full | 1 |
| S111 | web | Cheney | https://dave.cheney.net/2014/10/17/functional-options-for-friendly-apis | full | 2 |
| S112 | web | Cheney | https://dave.cheney.net/2018/07/12/slices-from-the-ground-up | irrelevant | 0 |
| S113 | web | Cheney | https://dave.cheney.net/2017/01/23/the-package-level-logger-anti-pattern | full | 1 |
| S114 | web | Cheney | https://dave.cheney.net/2019/01/08/avoid-package-names-like-base-util-or-common | full | 2 |
| S115 | web | Cheney | https://dave.cheney.net/practical-go/presentations/qcon-china.html | full | 19 |
| S116 | web | Cheney | https://dave.cheney.net/2016/08/20/solid-go-design | full | 0 |
| S117 | web | Cheney | https://dave.cheney.net/2019/05/07/prefer-table-driven-tests | skimmed | 2 |
| S118 | web | Cox | https://research.swtch.com/deps | skimmed | 4 |
| S119 | web | dtolnay | https://raw.githubusercontent.com/dtolnay/anyhow/master/README.md | full | 2 |
| S120 | web | dtolnay | https://raw.githubusercontent.com/dtolnay/thiserror/master/README.md | full | 1 |
| S121 | web | Go | https://go.dev/doc/effective_go | skimmed | 7 |
| S122 | web | Go | https://go.dev/blog/go1.13-errors | full | 2 |
| S123 | web | Pike | https://go.dev/blog/errors-are-values | full | 1 |
| S124 | web | Go | https://go.dev/blog/package-names | full | 2 |
| S125 | web | Pike | https://go-proverbs.github.io/ | full | 4 |
| S126 | web | Go | https://go.dev/wiki/CodeReviewComments | full | 21 |
| S127 | web | Google | https://google.github.io/styleguide/go/best-practices | full | 22 |
| S128 | web | Google | https://google.github.io/styleguide/go/decisions | full | 30 |
| S129 | web | Google | https://google.github.io/styleguide/go/guide | full | 9 |
| S130 | web | Kelley | https://ziglang.org/learn/why_zig_rust_d_cpp/ | full | 3 |
| S131 | web | Kelley | https://ziglang.org/documentation/master/ | skimmed | 6 |
| S132 | web | matklad | https://matklad.github.io/2024/09/03/the-fundamental-law-of-dependencies.html | full | 1 |
| S133 | web | matklad | https://matklad.github.io/2024/09/06/fix-one-level-deeper.html | full | 2 |
| S134 | web | matklad | https://matklad.github.io/2024/10/06/ousterhouts-dichotomy.html | full | 1 |
| S135 | web | matklad | https://matklad.github.io/2024/10/08/two-tips.html | full | 0 |
| S136 | web | matklad | https://matklad.github.io/2024/12/30/what-is-dependency.html | full | 1 |
| S137 | web | matklad | https://matklad.github.io/2025/04/15/underusing-snapshot-testing.html | full | 2 |
| S138 | web | matklad | https://matklad.github.io/2025/05/14/scalar-select-aniti-pattern.html | full | 1 |
| S139 | web | matklad | https://matklad.github.io/2025/08/16/reserve-first.html | full | 2 |
| S140 | web | matklad | https://matklad.github.io/2025/08/23/retry-loop-retry.html | full | 1 |
| S141 | web | matklad | https://matklad.github.io/2025/09/04/look-for-bugs.html | full | 2 |
| S142 | web | matklad | https://matklad.github.io/2025/11/06/error-codes-for-control-flow.html | full | 2 |
| S143 | web | matklad | https://matklad.github.io/2025/11/09/error-ABI.html | full | 1 |
| S144 | web | matklad | https://matklad.github.io/2025/12/06/mechanical-habits.html | full | 4 |
| S145 | web | matklad | https://matklad.github.io/2025/12/23/zig-newtype-index-pattern.html | full | 3 |
| S146 | web | matklad | https://matklad.github.io/2026/02/11/programming-aphorisms.html | full | 2 |
| S147 | web | matklad | https://matklad.github.io/2026/05/12/software-architecture.html | full | 1 |
| S148 | web | matklad | https://matklad.github.io/2026/05/14/catch-flakes-on-main.html | full | 1 |
| S149 | web | matklad | https://matklad.github.io/2026/05/18/always-be-blaming.html | full | 1 |
| S150 | web | matklad | https://matklad.github.io/2026/09/19/finding-bugs.html | full | 2 |
| S151 | web | matklad | https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html | full | 2 |
| S152 | web | matklad | https://matklad.github.io/2023/12/10/nsfw.html | full | 2 |
| S153 | web | matklad | https://matklad.github.io/2021/05/31/how-to-test.html | full | 9 |
| S154 | web | matklad | https://matklad.github.io/2020/10/15/study-of-std-io-error.html | full | 4 |
| S155 | web | matklad | https://matklad.github.io/2021/09/05/Rust100k.html | full | 0 |
| S156 | web | matklad | https://raw.githubusercontent.com/rust-lang/rust-analyzer/master/docs/book/src/contributing/style.md | full | 30 |
| S157 | web | matklad | https://matklad.github.io/2021/08/22/large-rust-workspaces.html | full | 2 |
| S158 | web | Oxide | https://rfd.shared.oxide.computer/rfd/0001 | irrelevant | 0 |
| S159 | web | Pike | https://commandcenter.blogspot.com/2012/06/less-is-exponentially-more.html | full | 2 |
| S160 | web | Pike | https://www.lysator.liu.se/c/pikestyle.html | full | 0 |
| S161 | web | Pike | https://doc.cat-v.org/bell_labs/pikestyle | full | 7 |
| S162 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/checklist.html | full | 0 |
| S163 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/debuggability.html | full | 1 |
| S164 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/dependability.html | full | 2 |
| S165 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/documentation.html | full | 5 |
| S166 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/flexibility.html | full | 4 |
| S167 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/future-proofing.html | full | 4 |
| S168 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/interoperability.html | full | 7 |
| S169 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/macros.html | full | 1 |
| S170 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/naming.html | full | 7 |
| S171 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/predictability.html | full | 7 |
| S172 | web | Rust API WG | https://rust-lang.github.io/api-guidelines/type-safety.html | full | 4 |
| S173 | web | Klabnik | https://doc.rust-lang.org/book/ch09-00-error-handling.html | full | 0 |
| S174 | web | Rust | https://rust-lang.github.io/rust-clippy/master/index.html | skimmed | 18 |
| S175 | web | Rust | https://doc.rust-lang.org/nightly/style-guide/ | full | 4 |
| S176 | web | TigerBeetle | https://raw.githubusercontent.com/tigerbeetle/tigerbeetle/main/docs/TIGER_STYLE.md | full | 24 |
| S177 | web | Uber | https://raw.githubusercontent.com/uber-go/guide/master/style.md | full | 34 |
| S178 | web | Google | https://developer.android.com/kotlin/style-guide | full | 12 |
| S179 | web | Langa | https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html | full | 9 |
| S180 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions | full | 14 |
| S181 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/abstract-class | full | 2 |
| S182 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/arrays | full | 1 |
| S183 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/base-classes-for-implementing-abstractions | full | 1 |
| S184 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/capitalization-conventions | full | 2 |
| S185 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/choosing-between-class-and-struct | full | 1 |
| S186 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/common-design-patterns | full | 0 |
| S187 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/constructor | full | 5 |
| S188 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/designing-for-extensibility | full | 1 |
| S189 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/enum | full | 4 |
| S190 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/exception-throwing | full | 6 |
| S191 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/extension-methods | full | 2 |
| S192 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/field | full | 3 |
| S193 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/interface | full | 4 |
| S194 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/member-overloading | full | 3 |
| S195 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/names-of-classes-structs-and-interfaces | full | 3 |
| S196 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/names-of-type-members | full | 3 |
| S197 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/nested-types | full | 1 |
| S198 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/operator-overloads | full | 3 |
| S199 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/parameter-design | full | 7 |
| S200 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/property | full | 4 |
| S201 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/struct | full | 1 |
| S202 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/using-standard-exception-types | full | 4 |
| S203 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/ | full | 1 |
| S204 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions | full | 10 |
| S205 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/exceptions | full | 0 |
| S206 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/naming-guidelines | full | 1 |
| S207 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/type | full | 1 |
| S208 | web | Microsoft | https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/usage-guidelines | full | 0 |
| S209 | web | D. Fowler | https://raw.githubusercontent.com/davidfowl/AspNetCoreDiagnosticScenarios/master/AsyncGuidance.md | full | 16 |
| S210 | web | D. Fowler | https://raw.githubusercontent.com/davidfowl/AspNetCoreDiagnosticScenarios/master/AspNetCoreGuidance.md | full | 6 |
| S211 | web | D. Fowler | https://raw.githubusercontent.com/davidfowl/DotNetCodingPatterns/main/README.md | irrelevant | 0 |
| S212 | web | D. Fowler | https://raw.githubusercontent.com/davidfowl/DotNetCodingPatterns/master/README.md | irrelevant | 0 |
| S213 | web | Goetz | https://www.infoq.com/articles/data-oriented-programming-java/ | full | 11 |
| S214 | web | Google | https://google.github.io/styleguide/csharp-style.html | full | 18 |
| S215 | web | Google | https://google.github.io/styleguide/javaguide.html | full | 27 |
| S216 | web | Google | https://google.github.io/styleguide/pyguide.html | full | 53 |
| S217 | web | Hynek | https://hynek.me/articles/serialization/ | full | 2 |
| S218 | web | Hynek | https://hynek.me/articles/hasattr/ | full | 2 |
| S219 | web | Hynek | https://hynek.me/articles/python-app-deps-2018/ | full | 3 |
| S220 | web | Hynek | https://hynek.me/articles/what-to-mock-in-5-mins/ | full | 5 |
| S221 | web | Hynek | https://hynek.me/articles/semver-will-not-save-you/ | full | 4 |
| S222 | web | Hynek | https://hynek.me/articles/hasattr/ | duplicate | 0 |
| S223 | web | Hynek | https://hynek.me/articles/python-subclassing-redux/ | full | 9 |
| S224 | web | Hynek | https://hynek.me/articles/testing-packaging/ | full | 2 |
| S225 | web | JetBrains | https://kotlinlang.org/docs/coding-conventions.html | full | 22 |
| S226 | web | JetBrains | https://kotlinlang.org/docs/idioms.html | full | 4 |
| S227 | web | Lippert | https://learn.microsoft.com/en-us/archive/blogs/ericlippert/immutability-in-c-part-one-kinds-of-immutability | full | 5 |
| S228 | web | Lippert | https://learn.microsoft.com/en-us/archive/blogs/ericlippert/locks-and-exceptions-do-not-mix | full | 3 |
| S229 | web | Lippert | https://ericlippert.com/2009/11/12/closing-over-the-loop-variable-considered-harmful-part-one/ | full | 1 |
| S230 | web | Lippert | https://ericlippert.com/2008/09/10/vexing-exceptions/ | full | 3 |
| S231 | web | Torgersen | https://devblogs.microsoft.com/dotnet/embracing-nullable-reference-types/ | full | 3 |
| S232 | web | Peters | https://peps.python.org/pep-0020/ | full | 4 |
| S233 | web | Python | https://peps.python.org/pep-0257/ | full | 6 |
| S234 | web | Python | https://peps.python.org/pep-0008/ | full | 38 |
| S235 | web | Rhodes | https://rhodesmill.org/brandon/slides/2014-07-pyohio/clean-architecture/ | full | 9 |
| S236 | web | Seemann | https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/ | full | 4 |
| S237 | web | Seemann | https://blog.ploeh.dk/2016/03/18/functional-architecture-is-ports-and-adapters/ | skimmed | 4 |
| S238 | web | Seemann | https://blog.ploeh.dk/2017/02/02/dependency-rejection/ | skimmed | 4 |
| S239 | web | Toub | https://devblogs.microsoft.com/dotnet/how-async-await-really-works/ | skimmed | 3 |
| S240 | web | Toub | https://devblogs.microsoft.com/dotnet/configureawait-faq/ | skimmed | 5 |
| S241 | web | Toub | https://devblogs.microsoft.com/dotnet/understanding-the-whys-whats-and-whens-of-valuetask/ | full | 2 |
| S242 | talk | Google TechTalks | How To Design A Good API and Why it Matters <https://youtu.be/aAb7hSCtvGw> | full | 23 |
| S243 | talk | ChariotSolutions | Java Futures, Early 2019 Edition - Brian Goetz <https://youtu.be/BL6ba2dtprw> | skimmed | 7 |
| S244 | talk | ClojureTV | Brian Goetz - Stewardship: the Sobering Parts <https://youtu.be/2y5Pv4yN0b0> | skimmed | 3 |
| S245 | talk | SciForce | Transforming Code Into Beautiful, Idiomatic Python / Raymond Hettinger / PyCon US 2013 <https://youtu.be/anrOzOapJ2E> | full | 15 |
| S246 | talk | PyCon 2015 | Raymond Hettinger - Beyond PEP 8 -- Best practices for beautiful intelligible code - PyCon 2015 <https://youtu.be/wf-BqAjZb8M> | mismatch | 10 |
| S247 | talk | PyCon 2015 | Raymond Hettinger - Super considered super! - PyCon 2015 <https://youtu.be/EiOglTERPEo> | full | 4 |
| S248 | talk | Next Day Video | The Clean Architecture in Python <https://youtu.be/DJtef410XaM> | full | 7 |
| S249 | talk | PyWaw Summit | Brandon Rhodes: Hoist Your I/O - PyWaw Summit 2015 <https://youtu.be/PBQN62oUnN8> | full | 8 |
| S250 | talk | PyCon 2019 | ukasz Langa - Life Is Better Painted Black, or: How to Stop Worrying and Embrace Auto-Formatting <https://youtu.be/esZLCuWs_2Y> | full | 6 |
| S251 | talk | Python Typing Summit | Thoughts on Python Typing - Guido van Rossum - PyCon US 2026 Typing Summit <https://youtu.be/_SRFZODQtxw> | full | 4 |
| S252 | talk | DevExpress | DevExpress Interviews - Mads Torgersen <https://youtu.be/0SOeDxjyFfY> | mismatch | 0 |
| S253 | talk | Immo Landwerth (terrajobst) | Episode 25: Using nullable reference types <https://youtu.be/SlHnM3aQfW0> | skimmed | 7 |
| S254 | talk | dotnet | Diagnosing thread pool exhaustion issues in .NET Core apps <https://youtu.be/isK8Cel3HP0> | mismatch | 2 |
| S255 | talk | Eximia - Excelencia Tecnologica  | Unit testing principles, patterns and practices (ft. Vlad Khorikov) <https://youtu.be/4j-_71crnN4> | full | 8 |
| S256 | talk | JetBrains | KotlinConf 2017 - Deep Dive into Coroutines on JVM by Roman Elizarov <https://youtu.be/YrrUCSi72E8> | full | 5 |
| S257 | talk | GOTO Conferences | Tidy First? A Daily Exercise in Empirical Design  Kent Beck  GOTO 2024 <https://youtu.be/Saaz6D1azlU> | full | 6 |
| S258 | talk | Kent Beck | Test Desiderata 8/12: Tests Should Be Isolated (from each other) <https://youtu.be/HApI2cspQus> | full | 2 |
| S259 | talk | heise conferences | Martin Fowler @ OOP2014 "Workflows of Refactoring" <https://youtu.be/vqEg37e4Mkw> | full | 3 |
| S260 | talk | Etsy Eng (Etsy Engineering) | Martin Fowler - Software Design in the 21st Century <https://youtu.be/6wDoopbtEqk> | full | 10 |
| S261 | talk | Grant Ammons | Michael Feathers - the deep synergy between testability and good design <https://youtu.be/4cVZvoFGJTU> | full | 16 |
| S262 | talk | Confreaks | RailsConf 2014 - All the Little Things by Sandi Metz <https://youtu.be/8bZh5LMaSmE> | full | 12 |
| S263 | talk | Confreaks | RailsConf 2015 - Nothing is Something <https://youtu.be/OMPfEXIlTVE> | full | 8 |
| S264 | talk | Confreaks | Ruby Conf 12 - Boundaries by Gary Bernhardt <https://youtu.be/yTkzNHF6rMs> | full | 8 |
| S265 | talk | Next Day Video | Fast Test, Slow Test <https://youtu.be/RAxiiRPHS9k> | full | 10 |
| S266 | talk | Strange Loop Conference | "Simple Made Easy" - Rich Hickey (2011) <https://youtu.be/SxdOUGdseq4> | full | 13 |
| S267 | talk | InfoQ | The Value of Values with Rich Hickey <https://youtu.be/-6BsiVyC1kM> | full | 5 |
| S268 | talk | ClojureTV | Maybe Not - Rich Hickey <https://youtu.be/YR5WdGrpoug> | full | 6 |
| S269 | talk | Talks at Google | A Philosophy of Software Design / John Ousterhout / Talks at Google <https://youtu.be/bmSAYlu0NcY> | full | 15 |
| S270 | talk | Jess Chadwick | Static Void Podcast:  Design Patterns <https://youtu.be/R_ZqlcKLAII> | skimmed | 8 |
| S271 | talk | jasonofthel33t | Effective ML by Yaron Minsky <https://youtu.be/DM2hEBwEWPc> | full | 10 |
| S272 | talk | NDC Conferences | Domain Modeling Made Functional - Scott Wlaschin <https://youtu.be/Up7LcbGZFuo> | full | 10 |
| S273 | talk | NDC Conferences | Functional Design Patterns - Scott Wlaschin <https://youtu.be/srQt1NAHYC0> | full | 9 |
| S274 | talk | TechTrain | Scott Wlaschin - Railway oriented programming <https://youtu.be/fYo3LN9Vf_M> | full | 6 |
| S275 | talk | GOTO Conferences | Intro to Empirical Software Engineering: What We Know We Don't Know  Hillel Wayne  GOTO 2019 <https://youtu.be/WELBnE33dpY> | full | 7 |
| S276 | talk | Strange Loop Conference | Strange Loop Chat with Hillel Wayne about TLA+ <https://youtu.be/B5iRABcC5-Q> | full | 2 |
| S277 | talk | NC State | The Power of Abstraction <https://youtu.be/GDVAHA0oyJU> | full | 10 |
| S278 | talk | Ward Cunningham | Debt Metaphor <https://youtu.be/pqeJFYwnkjE> | full | 2 |
| S279 | talk | UnityCoin | Clean Code - Uncle Bob / Lesson 1 <https://youtu.be/7EmboKQH8lM> | full | 16 |
| S280 | talk | Confreaks | Ruby Midwest 2011 - Keynote: Architecture the Lost Years by Robert Martin <https://youtu.be/WpkDN78P884> | full | 8 |
| S281 | web | Ousterhout | https://web.stanford.edu/~ouster/cgi-bin/aposd.php | irrelevant | 0 |
| S282 | web | Fowler | https://martinfowler.com/bliki/FunctionLength.html | full | 4 |
| S283 | web | Fowler | https://martinfowler.com/bliki/BeckDesignRules.html | full | 4 |
| S284 | web | Fowler | https://martinfowler.com/bliki/CodeSmell.html | full | 2 |
| S285 | web | Ousterhout | https://raw.githubusercontent.com/johnousterhout/aposd-vs-clean-code/main/README.md | full(read | 22 |
| S286 | web | Atwood | https://blog.codinghorror.com/flattening-arrow-code/ | full | 4 |
| S287 | web | Atwood | https://blog.codinghorror.com/the-best-code-is-no-code-at-all/ | full | 2 |
| S288 | web | Atwood | https://blog.codinghorror.com/code-smells/ | full | 14 |
| S289 | web | Beck | https://testdesiderata.com/ | full | 3 |
| S290 | web | Beck | https://tidyfirst.substack.com/p/canon-tdd | full | 4 |
| S291 | web | Google | https://google.github.io/eng-practices/review/reviewer/standard.html | full | 2 |
| S292 | web | Google | https://google.github.io/eng-practices/review/reviewer/looking-for.html | full | 13 |
| S293 | web | Google | https://google.github.io/eng-practices/review/reviewer/comments.html | full | 1 |
| S294 | web | Google | https://google.github.io/eng-practices/review/developer/cl-descriptions.html | full | 2 |
| S295 | web | Google | https://google.github.io/eng-practices/review/reviewer/pushback.html | full | 1 |
| S296 | web | Google | https://google.github.io/eng-practices/review/developer/small-cls.html | full | 4 |
| S297 | web | Wright | https://www.hyrumslaw.com/ | full | 2 |
| S298 | web | Fowler | https://martinfowler.com/bliki/PublishedInterface.html | full | 1 |
| S299 | web | Fowler | https://martinfowler.com/bliki/TestDouble.html | full | 1 |
| S300 | web | Fowler | https://martinfowler.com/bliki/TestCoverage.html | full | 2 |
| S301 | web | Fowler | https://martinfowler.com/bliki/SelfTestingCode.html | full | 1 |
| S302 | web | Fowler | https://refactoring.com/catalog/ | full | 4 |
| S303 | web | Fowler | https://martinfowler.com/bliki/AnemicDomainModel.html | full | 2 |
| S304 | web | Fowler | https://martinfowler.com/bliki/BoundedContext.html | full | 1 |
| S305 | web | Fowler | https://martinfowler.com/bliki/DesignStaminaHypothesis.html | full | 1 |
| S306 | web | Fowler | https://martinfowler.com/bliki/PresentationDomainDataLayering.html | full | 3 |
| S307 | web | Fowler | https://martinfowler.com/bliki/MonolithFirst.html | full | 2 |
| S308 | web | Fowler | https://martinfowler.com/bliki/OpportunisticRefactoring.html | full | 1 |
| S309 | web | Fowler | https://martinfowler.com/bliki/TechnicalDebt.html | full | 1 |
| S310 | web | Fowler | https://martinfowler.com/bliki/TestPyramid.html | full | 3 |
| S311 | web | Fowler | https://martinfowler.com/bliki/UnitTest.html | full | 2 |
| S312 | web | Fowler | https://martinfowler.com/bliki/Yagni.html | full | 4 |
| S313 | web | Fowler | https://martinfowler.com/articles/nonDeterminism.html | full | 9 |
| S314 | web | Fowler | https://martinfowler.com/articles/injection.html | skimmed | 6 |
| S315 | web | Fowler | https://martinfowler.com/articles/mocksArentStubs.html | full | 6 |
| S316 | web | Google Testing Blog | https://testing.googleblog.com/2020/08/code-coverage-best-practices.html | unreadable | 0 |
| S317 | web | Google Testing Blog | https://testing.googleblog.com/2008/07/breaking-law-of-demeter-is-like-looking.html | unreadable | 0 |
| S318 | web | Google Testing Blog | https://testing.googleblog.com/2013/06/testing-on-toilet-fake-your-way-to.html | unreadable | 0 |
| S319 | web | Google Testing Blog | https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html | unreadable | 0 |
| S320 | web | Google Testing Blog | https://testing.googleblog.com/2014/07/testing-on-toilet-dont-put-logic-in.html | unreadable | 0 |
| S321 | web | Google Testing Blog | https://testing.googleblog.com/2023/09/use-abstraction-to-improve-function.html | unreadable | 0 |
| S322 | web | Google Testing Blog | https://testing.googleblog.com/2017/06/code-health-reduce-nesting-reduce.html | unreadable | 0 |
| S323 | web | Google Testing Blog | https://testing.googleblog.com/2015/01/testing-on-toilet-prefer-testing-public.html | unreadable | 0 |
| S324 | web | Google Testing Blog | https://testing.googleblog.com/2008/11/clean-code-talks-dependency-injection.html | unreadable | 0 |
| S325 | web | Google Testing Blog | https://testing.googleblog.com/2008/08/by-miko-hevery-so-you-join-new-project.html | unreadable | 0 |
| S326 | web | Google Testing Blog | https://testing.googleblog.com/2008/02/in-movie-amadeus-austrian-emperor.html | unreadable | 0 |
| S327 | web | Google Testing Blog | https://testing.googleblog.com/2008/12/static-methods-are-death-to-testability.html | unreadable | 0 |
| S328 | web | Dijkstra | https://www.cs.utexas.edu/~EWD/transcriptions/EWD02xx/EWD215.html | full | 2 |
| S329 | web | The following manuscript | Copyright Notice | unreadable | 0 |
| S330 | web | Dijkstra | https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD340.html | skimmed | 5 |
| S331 | web | Dijkstra | https://www.cs.utexas.edu/~EWD/transcriptions/EWD10xx/EWD1036.html | skimmed | 2 |
| S332 | web | Hickey | https://raw.githubusercontent.com/matthiasn/talk-transcripts/master/Hickey_Rich/SimpleMadeEasy.md | full | 10 |
| S333 | web | Hickey | https://raw.githubusercontent.com/matthiasn/talk-transcripts/master/Hickey_Rich/HammockDrivenDev.md | skimmed | 0 |
| S334 | web | Hickey | https://raw.githubusercontent.com/matthiasn/talk-transcripts/master/Hickey_Rich/MaybeNot.md | skimmed | 6 |
| S335 | web | Hickey | https://raw.githubusercontent.com/matthiasn/talk-transcripts/master/Hickey_Rich/ValueOfValues.md | skimmed | 5 |
| S336 | web | King | https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/ | full | 9 |
| S337 | web | King | https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/ | full | 3 |
| S338 | web | King | https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/ | full | 4 |
| S339 | web | Wlaschin | https://fsharpforfunandprofit.com/posts/designing-with-types-intro/ | full | 2 |
| S340 | web | Wlaschin | https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/ | full | 4 |
| S341 | web | Wlaschin | https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/ | full | 2 |
| S342 | web | Wlaschin | https://fsharpforfunandprofit.com/posts/designing-with-types-more-semantic-types/ | full | 1 |
| S343 | web | Wlaschin | https://fsharpforfunandprofit.com/rop/ | skimmed | 1 |
| S344 | web | Metz | https://thoughtbot.com/blog/sandi-metz-rules-for-developers | full | 4 |
| S345 | web | Metz | https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction | full | 2 |
| S346 | web | Martin | https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html | full | 3 |
| S347 | web | Martin | https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html | skimmed | 2 |
| S348 | web | Martin | https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html | full | 4 |
| S349 | web | Techniques                        Editor | Programming                       R. Morris | full | 4 |
| S350 | web | Spolsky | https://www.joelonsoftware.com/2005/05/11/making-wrong-code-look-wrong/ | full | 6 |
| S351 | web | Spolsky | https://www.joelonsoftware.com/2002/11/11/the-law-of-leaky-abstractions/ | full | 1 |
| S352 | web | Spolsky | https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/ | full | 2 |
| S353 | web | Luu | https://danluu.com/testing/ | full | 4 |
| S354 | web | Luu | https://danluu.com/wat/ | skimmed | 1 |
| S355 | web | Luu | https://danluu.com/postmortem-lessons/ | full | 4 |
| S356 | web | Luu | https://danluu.com/file-consistency/ | skimmed | 2 |
| S357 | web | Luu | https://danluu.com/everything-is-broken/ | skimmed | 2 |
| S358 | web | Luu | https://danluu.com/boring-languages/ | irrelevant | 0 |
| S359 | web | Luu | https://danluu.com/empirical-pl/ | skimmed | 2 |
| S360 | web | Wayne | https://www.hillelwayne.com/post/contracts/ | full | 4 |
| S361 | web | Wayne | https://www.hillelwayne.com/post/this-is-how-science-happens/ | skimmed | 0 |
| S362 | web | Wayne | https://www.hillelwayne.com/post/why-dont-people-use-formal-methods/ | skimmed | 0 |
| S363 | web | Google | https://abseil.io/resources/swe-book/html/ch08.html | skimmed | 13 |
| S364 | web | Google | https://abseil.io/resources/swe-book/html/ch09.html | skimmed | 4 |
| S365 | web | Google | https://abseil.io/resources/swe-book/html/ch10.html | skimmed | 4 |
| S366 | web | Google | https://abseil.io/resources/swe-book/html/ch11.html | skimmed | 8 |
| S367 | web | Google | https://abseil.io/resources/swe-book/html/ch12.html | full | 12 |
| S368 | web | Google | https://abseil.io/resources/swe-book/html/ch13.html | skimmed | 7 |
| S369 | web | Google | https://abseil.io/resources/swe-book/html/ch15.html | skimmed | 5 |
| S370 | web | Sadowski | https://abseil.io/resources/swe-book/html/ch20.html | skimmed | 8 |
| S371 | web | Google | https://abseil.io/resources/swe-book/html/ch14.html | skimmed | 3 |
| S372 | web | Wright | https://abseil.io/resources/swe-book/html/ch22.html | skimmed | 2 |
| S373 | web |  | A Behavioral                                          Notion                        of Subtyping | skimmed | 3 |
| S374 | web | Minsky | https://blog.janestreet.com/effective-ml-revisited/ | full | 5 |
| S375 | web | Google Testing Blog | https://testing.googleblog.com/2026/07/prefactoring-clear-way-for-your-new.html | full | 3 |
| S376 | web | Google Testing Blog | https://testing.googleblog.com/2026/06/choosing-values-for-robust-tests.html | full | 3 |
| S377 | web | Google Testing Blog | https://testing.googleblog.com/2024/12/tech-on-toilet-driving-software.html | full | 0 |
| S378 | web | Google Testing Blog | https://testing.googleblog.com/2024/10/smurf-beyond-test-pyramid.html | full | 1 |
| S379 | web | Google Testing Blog | https://testing.googleblog.com/2024/05/test-failures-should-be-actionable.html | full | 4 |
| S380 | web | Google Testing Blog | https://testing.googleblog.com/2024/04/how-i-learned-to-stop-writing-brittle.html | full | 3 |
| S381 | web | Google Testing Blog | https://testing.googleblog.com/2024/04/prefer-narrow-assertions-in-unit-tests.html | full | 2 |
| S382 | web | Google Testing Blog | https://testing.googleblog.com/2024/02/increase-test-fidelity-by-avoiding-mocks.html | full | 4 |
| S383 | web | Google Testing Blog | https://testing.googleblog.com/2023/11/clean-up-code-cruft.html | full | 2 |
| S384 | web | Google Testing Blog | https://testing.googleblog.com/2023/11/write-clean-code-to-reduce-cognitive.html | full | 5 |
| S385 | web | Google Testing Blog | https://testing.googleblog.com/2023/10/include-only-relevant-details-in-tests.html | full | 2 |
| S386 | web | Google Testing Blog | https://testing.googleblog.com/2023/10/improve-readability-with-positive.html | full | 3 |
| S387 | web | Google Testing Blog | https://testing.googleblog.com/2023/09/use-abstraction-to-improve-function.html | full | 1 |
| S388 | web | Google Testing Blog | https://testing.googleblog.com/2022/02/code-health-now-youre-thinking-with.html | full | 2 |
| S389 | web | Google Testing Blog | https://testing.googleblog.com/2021/06/how-much-testing-is-enough.html | full | 3 |
| S390 | web | Google Testing Blog | https://testing.googleblog.com/2021/04/mutation-testing.html | full | 5 |
| S391 | web | Google Testing Blog | https://testing.googleblog.com/2020/12/test-flakiness-one-of-main-challenges.html | full | 3 |
| S392 | web | Google Testing Blog | https://testing.googleblog.com/2020/12/testing-on-toilet-separation-of.html | full | 1 |
| S393 | web | Google Testing Blog | https://testing.googleblog.com/2020/11/fixing-test-hourglass.html | full | 2 |
| S394 | web | Google Testing Blog | https://testing.googleblog.com/2020/10/testing-on-toilet-testing-ui-logic.html | full | 1 |
| S395 | web | Google Testing Blog | https://testing.googleblog.com/2020/08/testing-on-toilet-avoid-hardcoding.html | full | 2 |
| S396 | web | Google Testing Blog | https://testing.googleblog.com/2020/08/code-coverage-best-practices.html | full | 5 |
| S397 | web | Google Testing Blog | https://testing.googleblog.com/2020/07/testing-on-toilet-dont-mock-types-you.html | full | 2 |
| S398 | web | Google Testing Blog | https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html | full | 1 |
| S399 | web | Google Testing Blog | https://testing.googleblog.com/2019/11/code-health-respectful-reviews-useful.html | full | 2 |
| S400 | web | Google Testing Blog | https://testing.googleblog.com/2019/07/truth-10-fluent-assertions-for-java-and.html | full | 1 |
| S401 | web | Google Testing Blog | https://testing.googleblog.com/2019/01/android-platform-testing-made-easy.html | full | 1 |
| S402 | web | Google Testing Blog | https://testing.googleblog.com/2018/11/testing-on-toilet-exercise-service-call.html | full | 2 |
| S403 | web | Google Testing Blog | https://testing.googleblog.com/2018/07/code-health-make-interfaces-hard-to.html | full | 4 |
| S404 | web | Google Testing Blog | https://testing.googleblog.com/2018/06/testing-on-toilet-only-verify-relevant.html | full | 1 |
| S405 | web | Google Testing Blog | https://testing.googleblog.com/2018/06/testing-on-toilet-keep-tests-focused.html | full | 1 |
| S406 | web | Google Testing Blog | https://testing.googleblog.com/2018/05/code-health-understanding-code-in-review.html | full | 2 |
| S407 | web | Google Testing Blog | https://testing.googleblog.com/2018/02/testing-on-toilet-cleanly-create-test.html | full | 3 |
| S408 | web | Google Testing Blog | https://testing.googleblog.com/2017/12/testing-on-toilet-only-verify-state.html | full | 2 |
| S409 | web | Google Testing Blog | https://testing.googleblog.com/2017/11/obsessed-with-primitives.html | full | 2 |
| S410 | web | Google Testing Blog | https://testing.googleblog.com/2017/10/code-health-identifiernamingpostforworl.html | full | 3 |
| S411 | web | Google Testing Blog | https://testing.googleblog.com/2017/09/code-health-providing-context-with.html | full | 2 |
| S412 | web | Google Testing Blog | https://testing.googleblog.com/2017/08/code-health-eliminate-yagni-smells.html | full | 4 |
| S413 | web | Google Testing Blog | https://testing.googleblog.com/2017/07/code-health-to-comment-or-not-to-comment.html | full | 5 |
| S414 | web | Google Testing Blog | https://testing.googleblog.com/2017/06/code-health-too-many-comments-on-your.html | full | 3 |
| S415 | web | Google Testing Blog | https://testing.googleblog.com/2017/06/code-health-reduce-nesting-reduce.html | full | 3 |
| S416 | web | Google Testing Blog | https://testing.googleblog.com/2017/04/where-do-our-flaky-tests-come-from.html | full | 3 |
| S417 | web | Google Testing Blog | https://testing.googleblog.com/2017/04/code-health-googles-internal-code.html | full | 1 |
| S418 | web | Google Testing Blog | https://testing.googleblog.com/2017/01/testing-on-toilet-keep-cause-and-effect.html | full | 2 |
| S419 | web | Google Testing Blog | https://testing.googleblog.com/2017/01/happy-10th-birthday-google-testing-blog.html | full | 0 |
| S420 | web | Google Testing Blog | https://testing.googleblog.com/2016/11/what-test-engineers-do-at-google.html | full | 2 |
| S421 | web | Google Testing Blog | https://testing.googleblog.com/2016/09/testing-on-toilet-what-makes-good-end.html | full | 2 |
| S422 | web | Google Testing Blog | https://testing.googleblog.com/2016/09/what-test-engineers-do-at-google.html | full | 0 |
| S423 | web | Google Testing Blog | https://testing.googleblog.com/2016/08/hackable-projects.html | full | 7 |
| S424 | web | Google Testing Blog | https://testing.googleblog.com/2016/06/the-inquiry-method-for-test-planning.html | full | 2 |
| S425 | web | Google Testing Blog | https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html | full | 1 |
| S426 | web | Google Testing Blog | https://testing.googleblog.com/2016/02/earlgrey-ios-functional-ui-testing.html | full | 0 |
| S427 | web | Google Testing Blog | https://testing.googleblog.com/2015/10/audio-testing-automatic-gain-control.html | full | 2 |
| S428 | web | Google Testing Blog | https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html | full | 3 |
| S429 | web | Google Testing Blog | https://testing.googleblog.com/2015/03/android-ui-automated-testing.html | full | 2 |
| S430 | web | Google Testing Blog | https://testing.googleblog.com/2015/02/the-first-annual-testing-on-toilet.html | full | 0 |
| S431 | web | Google Testing Blog | https://testing.googleblog.com/2015/01/testing-on-toilet-change-detector-tests.html | full | 1 |
| S432 | web | Google Testing Blog | https://testing.googleblog.com/2015/01/testing-on-toilet-prefer-testing-public.html | full | 1 |
| S433 | web | Google Testing Blog | https://testing.googleblog.com/2014/12/testing-on-toilet-truth-fluent.html | full | 1 |
| S434 | web | Google Testing Blog | https://testing.googleblog.com/2014/11/protractor-angular-testing-made-easy.html | full | 1 |
| S435 | web | Google Testing Blog | https://testing.googleblog.com/2014/10/testing-on-toilet-writing-descriptive.html | full | 1 |
| S436 | web | Google Testing Blog | https://testing.googleblog.com/2014/09/chrome-firefox-webrtc-interop-test-pt-2.html | full | 2 |
| S437 | web | Google Testing Blog | https://testing.googleblog.com/2014/08/chrome-firefox-webrtc-interop-test-pt-1.html | full | 2 |
| S438 | web | Google Testing Blog | https://testing.googleblog.com/2014/08/testing-on-toilet-web-testing-made.html | full | 1 |
| S439 | web | Google Testing Blog | https://testing.googleblog.com/2014/07/testing-on-toilet-dont-put-logic-in.html | full | 2 |
| S440 | web | Google Testing Blog | https://testing.googleblog.com/2014/07/measuring-coverage-at-google.html | full | 1 |
| S441 | web | Google Testing Blog | https://testing.googleblog.com/2014/05/testing-on-toilet-risk-driven-testing.html | full | 1 |
| S442 | web | Google Testing Blog | https://testing.googleblog.com/2014/05/testing-on-toilet-effective-testing.html | full | 2 |
| S443 | web | Google Testing Blog | https://testing.googleblog.com/2014/04/testing-on-toilet-test-behaviors-not.html | full | 1 |
| S444 | web | Google Testing Blog | https://testing.googleblog.com/2014/04/the-real-test-driven-development.html | full | 0 |
| S445 | web | Google Testing Blog | https://testing.googleblog.com/2014/03/testing-on-toilet-what-makes-good-test.html | full | 2 |
| S446 | web | Google Testing Blog | https://testing.googleblog.com/2014/03/whenhow-to-use-mockito-answer.html | full | 2 |
| S447 | web | Google Testing Blog | https://testing.googleblog.com/2014/01/the-google-test-and-development_21.html | full | 1 |
| S448 | web | Google Testing Blog | https://testing.googleblog.com/2014/01/the-google-test-and-development.html | full | 0 |
| S449 | web | Google Testing Blog | https://testing.googleblog.com/2013/12/the-google-test-and-development.html | full | 0 |
| S450 | web | Google Testing Blog | https://testing.googleblog.com/2013/11/webrtc-audio-quality-testing.html | full | 2 |
| S451 | web | Google Testing Blog | https://testing.googleblog.com/2013/08/how-google-team-tests-mobile-apps.html | full | 3 |
| S452 | web | Google Testing Blog | https://testing.googleblog.com/2013/08/testing-on-toilet-test-behavior-not.html | full | 1 |
| S453 | web | Google Testing Blog | https://testing.googleblog.com/2013/07/testing-on-toilet-know-your-test-doubles.html | full | 1 |
| S454 | web | Google Testing Blog | https://testing.googleblog.com/2013/06/testing-on-toilet-fake-your-way-to.html | full | 2 |
| S455 | web | Google Testing Blog | https://testing.googleblog.com/2013/05/testing-on-toilet-dont-overuse-mocks.html | full | 1 |
| S456 | web | Google Testing Blog | https://testing.googleblog.com/2013/04/two-new-videos-about-testing-at-google.html | full | 0 |
| S457 | web | Google Testing Blog | https://testing.googleblog.com/2013/03/testing-on-toilet-testing-state-vs.html | full | 1 |
| S458 | web | Google Testing Blog | https://testing.googleblog.com/2013/01/test-engineers-google.html | full | 0 |
| S459 | web | Google Testing Blog | https://testing.googleblog.com/2012/11/testacular-spectacular-test-runner-for.html | full | 1 |
