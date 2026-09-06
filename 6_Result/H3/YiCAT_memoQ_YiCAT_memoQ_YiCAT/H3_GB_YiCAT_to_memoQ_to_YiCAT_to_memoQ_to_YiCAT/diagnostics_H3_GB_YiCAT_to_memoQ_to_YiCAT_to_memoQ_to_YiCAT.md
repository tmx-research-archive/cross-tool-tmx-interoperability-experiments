# Route diagnostics: H3 YiCAT → memoQ → YiCAT → memoQ → YiCAT

## Route judgement

{
  "level": "multi-hop preliminary",
  "step_levels": [
    "unstable route segment",
    "unstable route segment",
    "unstable route segment",
    "unstable route segment"
  ],
  "worst_step_index_1_based": 2,
  "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
  "end_to_end_level": "partially stable route segment"
}

## Stepwise results

### Step 1: YiCAT → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=110.0; metadata/identifier-layer mean=41.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, inline_tags_expanded_or_reencoded, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, inline_tags_expanded_or_reencoded, header_values_changed, header_fields_added

### Step 2: memoQ → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=64.0; metadata/identifier-layer mean=16.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost

### Step 3: YiCAT → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=75.0; metadata/identifier-layer mean=75.0; detected: language_code_case_normalised, tool_specific_props_added, header_values_changed, header_fields_added
- Matching: hybrid, confidence=high, methods={'tuid': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, header_values_changed, header_fields_added

### Step 4: memoQ → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=100.0; metadata/identifier-layer mean=16.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost

## End-to-end: YiCAT → YiCAT

- Level: **partially stable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=123.33; metadata/identifier-layer mean=66.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, inline_tags_expanded_or_reencoded
