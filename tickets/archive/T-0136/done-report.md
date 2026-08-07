## Done report

Building on T-0132's string-valued attr tokens, the secret construct
(issued_by/audience/lifetime/revoke) and the on-deploy node block
(canary stages, endorsed_by chain, rollback within) parse from .strata
source and elaborate through the landed elaborate_secret (T-0082) and
DeployContract/CanaryStage (T-0083) machinery with no duplicated
validation; malformed blocks (missing lifetime, missing rollback) fail
closed with line/col diagnostics. Existing litmus goldens
byte-identical; new design/litmus/deploy_secret.strata litmus
exercises both constructs end-to-end. Reviewer APPROVED (contingent on
T-0132's trail, completed at merge). Verified on main: 378 strata
tests green after make core, 6 new rust tests in the crate.
