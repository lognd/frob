+++
id = "01M5BN07YM5RQW5M72NDG2H04F"
title = "tests: language fidelity F4 vs F3 failures on base (doctor_languages, e2e_init_loop)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T03:17:11Z"
updated = "2026-10-20T03:17:11Z"
+++

cli::doctor_languages_prints_fidelity_precisions_and_f0_extensions and e2e_init_loop::loop_on_main/trunk/orphan fail asserting F3 but get F4; unrelated to ~VHZ1FDQ.
