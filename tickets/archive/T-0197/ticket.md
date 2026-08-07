---
id: T-0197
title: 'candidate prefilters: DECKARD characteristic vectors + Oreo metric ratios
  + NiCad size ratio'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_prefilter.py::TestCharacteristicVector::test_identical_streams_have_identical_vectors
- tests/test_dup_prefilter.py::TestCharacteristicVector::test_placeholder_count_position_does_not_matter_only_bucket_count
- tests/test_dup_prefilter.py::TestCharacteristicVector::test_empty_stream_is_empty_vector
- tests/test_dup_prefilter.py::TestCosineSimilarity::test_identical_vectors_are_similarity_one
- tests/test_dup_prefilter.py::TestCosineSimilarity::test_disjoint_vectors_are_similarity_zero
- tests/test_dup_prefilter.py::TestCosineSimilarity::test_both_empty_is_similarity_one
- tests/test_dup_prefilter.py::TestCosineSimilarity::test_one_empty_is_similarity_zero
- tests/test_dup_prefilter.py::TestNicadSizeRatio::test_similar_sizes_pass
- tests/test_dup_prefilter.py::TestNicadSizeRatio::test_wildly_different_sizes_rejected
- tests/test_dup_prefilter.py::TestNicadSizeRatio::test_missing_size_passes_through
- tests/test_dup_prefilter.py::TestOreoMetricRatio::test_similar_branch_counts_pass
- tests/test_dup_prefilter.py::TestOreoMetricRatio::test_both_zero_branch_count_passes
- tests/test_dup_prefilter.py::TestOreoMetricRatio::test_wildly_different_branch_counts_rejected
- tests/test_dup_prefilter.py::TestDeckardVector::test_similar_shape_passes
- tests/test_dup_prefilter.py::TestDeckardVector::test_disjoint_shape_rejected
- tests/test_dup_prefilter.py::TestDeckardVector::test_missing_vector_passes_through
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_smart]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_rungs]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_region]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_inline]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_prefilter_never_exceeds_unfiltered_verification_count[dup_smart]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_prefilter_never_exceeds_unfiltered_verification_count[dup_rungs]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_prefilter_never_exceeds_unfiltered_verification_count[dup_region]
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_prefilter_never_exceeds_unfiltered_verification_count[dup_inline]
designated_repro_test: null
threat: null
component: null
---
Survey items 2/4/6 (non-ML halves): three additive candidate-pruning stages before APTED/WL verification; prefilters only prune pairs, never add false positives -- test that enabling them never changes the verified-clone set on fixtures, only the pair count examined.