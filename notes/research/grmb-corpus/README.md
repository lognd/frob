# grmb design corpus

The one home of worked .grmb examples (docs/design/grmb-spec.md keeps a
single example in 18.2). Written under ticket ~T5VVDBY and respelled to
the cycle 1 grammar of ticket ~MHGA5VN (`:` outcome types, `=>` arms,
list waypoint chains with `=>` outcome maps, default retry targets, `///`
labels, `bound` claims for budgets). Nothing here has been run through a
parser: the shipped P1 parser predates cycle 1. Every file carries its
EXPECTED FINDINGS (what the rules of the spec predict) and its NOT
EXPRESSIBLE notes. The first job of P0/P1 is to check these predictions.

Domain files are whole models: one braced `system` at the top level makes
the file's planning items its members (grmb-spec 11.2). Stress files are
FRAGMENTS: read each as if it began `grimble = "2"; module m; system s;`
and declared every actor, goal and step it names, except the names a
fixture is about (f13 and f15 test unresolved names). EXPECTED blocks
list what fires on the text as written; IF EDITED lines say what an edit
would change. The P1 exit checks the lists one way (grmb-spec 18.3).

## Domain mockup sets (synthesis 6.1), `domains/`

| File | Domain |
|---|---|
| d01_web_shop.grmb | web shop |
| d02_firmware.grmb | firmware |
| d03_saga.grmb | distributed saga |
| d04_pubsub.grmb | event-driven pub-sub |
| d05_cli_tool.grmb | CLI developer tool (frob dogfood) |
| d06_mobile_sync.grmb | mobile offline sync |
| d07_unity_game.grmb | Unity game loop |
| d08_batch_pipeline.grmb | batch data pipeline |
| d09_multitenant_saas.grmb | multi-tenant SaaS roles |
| d10_regulated_device.grmb | regulated medical/automotive |
| d11_llm_agent.grmb | LLM/agent workflow |

## Stress fixtures (synthesis 6.2), `stress/`

Files f01..f16 map one to one onto the sixteen stress cases (f10 is split
into f10a goals-only and f10b impls-only). f05, f06 and f07 are partly or
wholly inexpressible by design and exist to record the gap.

## Gaps

What the grammar cannot express is the open-questions list of
docs/design/grmb-spec.md section 19 (gap ids G1-G11 are cited from the
files; G3 was closed by D153). The former GAPS.md and its list of guessed
syntax were folded into that list and into the cycle 1 decisions
D150-D165.
