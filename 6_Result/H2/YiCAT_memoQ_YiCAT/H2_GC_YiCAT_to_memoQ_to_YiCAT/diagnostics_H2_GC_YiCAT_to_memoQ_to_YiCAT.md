# Route diagnostics: H2 YiCAT → memoQ → YiCAT

## Route judgement

{
  "level": "round-trip preliminary",
  "step_levels": [
    "unstable route segment",
    "unstable route segment"
  ],
  "worst_step_index_1_based": 2,
  "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
  "end_to_end_level": "unstable route segment"
}

## Stepwise results

### Step 1: YiCAT → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=66.5; structure-layer mean=102.17; metadata/identifier-layer mean=41.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, inline_tags_expanded_or_reencoded, header_values_changed; matching confidence=medium; inspect per-TU CSV if needed
- Matching: hybrid, confidence=medium, methods={'alignment_text_fingerprint': 6, 'sequence_similarity': 93}, low-confidence=1
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, inline_tags_expanded_or_reencoded, header_values_changed, header_fields_added

### Step 2: memoQ → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=66.5; structure-layer mean=53.76; metadata/identifier-layer mean=16.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, inline_tags_compressed_or_deleted, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 94, 'sequence_similarity': 5}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, inline_tags_compressed_or_deleted, header_values_changed, header_fields_lost

## End-to-end: YiCAT → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=68.69; structure-layer mean=64.71; metadata/identifier-layer mean=66.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, inline_tags_expanded_or_reencoded; matching confidence=medium; inspect per-TU CSV if needed
