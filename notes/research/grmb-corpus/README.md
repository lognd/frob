# grmb planning corpus (rev 2)

Deliverable of ticket ~T5VVDBY (acceptance 2). Hand-written mockups for
`docs/design/grmb-planning.md` rev 2. Nothing here has been run through a
parser: no rev 2 grammar is implemented. Every file carries its EXPECTED
FINDINGS (what the rules in the design predict) and its NOT EXPRESSIBLE
notes. The first job of P0/P1 is to check these predictions.

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

[GAPS.md](GAPS.md) lists what the grammar could not express, for R2, plus
the syntax these mockups had to ASSUME because planning.md does not define
it.
