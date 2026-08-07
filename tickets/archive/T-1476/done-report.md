## Done report

Implemented step 2 of the T-1459 vet _capability split design (T-1420
LARGE001 residue): the python import/binding-aware resolution family
moved verbatim from src/frob/vet/_capability.py to a new sibling
src/frob/vet/_capability_python.py. 5513 -> 4670 lines; new file 867
lines. Public surface unchanged. `_needle_matches_resolved` relocated to
_capability_core.py as a genuinely shared cross-language helper.
