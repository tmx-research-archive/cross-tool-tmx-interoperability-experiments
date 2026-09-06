# Route diagnostics: H2 memoQ → Trados → memoQ

## Route judgement

{
  "level": "round-trip preliminary",
  "step_levels": [
    "unstable route segment",
    "unstable route segment"
  ],
  "worst_step_index_1_based": 1,
  "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
  "end_to_end_level": "unstable route segment"
}

## Stepwise results

### Step 1: memoQ → Trados

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=100.0; metadata/identifier-layer mean=23.33; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

### Step 2: Trados → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=86.67; metadata/identifier-layer mean=54.17; detected: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

## End-to-end: memoQ → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=71.72; structure-layer mean=100.0; metadata/identifier-layer mean=66.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, tool_specific_props_added, pre_existing_props_removed_or_replaced
