There is some serious reworking that I want to do with this library. First, I think these subcommands need to
straight up be removed because they are never used:

* frob edit	Isolate, stage, and atomically commit changes to a single symbol
* frob dispatch	Decompose a task into parallel agent missions
* frob mission	Manage individual agent mission state
* frob todo	Lightweight task list stored in .frob/

Additionally, I think we need to remove `agents/` and `skills/` or at least REALLY rework them.

I want to make this a better utility, especially for documentation checking. Every function/class/etc. needs
to have a digest/hash in a `.frob/` folder, and every bit of documentation needs to be connected so that we
have a graph of WHAT DOCUMENTATION and WHAT OTHER CODE needs to be updated whenever something is touched,
without even needing to run a single test (like a static-type checker with documentation.) 

We also need to create a better way to hierarchically catalogue both TODOs (in a way that is statically-checkable)
and features (ESPECIALLY for WEB; and in a human/AI split thing where I can add desired features to a queue, you
can read all outstanding requests and then make a specific game-plan and repeat cycle; additionally, for UX and 
compatibility auditors to make requests and for subagents to record all of the features that they added, what
needs to be tested, and so forth), mark blockers, get a list of "do-able tickets". Because what ends up happening
is that we start getting into the nitty-gritty and we forget that we have a stack of things and we only end up
popping off the top half of the stack.

I also want a better way to guarantee system security and reliability statically, rather than just running simple
audit/fix cycles and praying.

I would prefer to have some sort of embedded language in comments or whatnot across TypeScript, Rust, C++, C, Python
to record what needs to be done and some way to statically check it so that NO MATTER WHAT it is impossible to "be
a lazy developer". Can you help me think through some potential features to add to this tool so that it is impossible
to not have a PERFECT codebase?
