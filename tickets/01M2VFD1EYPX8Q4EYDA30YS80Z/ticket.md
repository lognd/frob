+++
id = "01M2VFD1EYPX8Q4EYDA30YS80Z"
title = "WIRE001 cannot resolve cross-file callers through .claude/hooks/ sys.path imports"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:00Z"
aliases = ["T-4574"]
labels = ["milestone:0.535.0", "v1-cluster:E1"]
scope = ["src/frob/gates/_wire.py"]
+++

Found while working T-3851: .claude/hooks/_shellscan.py::strip_and_blank_prefixed_segments is called by .claude/hooks/frob-suggest.py::_handle_bash (from _shellscan import strip_and_blank_prefixed_segments as _strip_and_blank, after sys.path.insert(0, str(Path(__file__).resolve().parent))) in the SAME diff, yet WIRE001 reports it as having 'no caller outside its own tests'. Pre-existing cross-file symbols in _shellscan.py (POS, strip_quoted) are never checked by WIRE001 because they are not NEW in any diff, so this blind spot has never been exercised before. Root cause suspected: WIRE001's call-graph resolver does not trace calls through .claude/hooks/**'s dynamic sys.path.insert + bare-module-name import pattern. Waived on T-3851 with a note; this ticket tracks fixing or explicitly documenting the resolver gap.
