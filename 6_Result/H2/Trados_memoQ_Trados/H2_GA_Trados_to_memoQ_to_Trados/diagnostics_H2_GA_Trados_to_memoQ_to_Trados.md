# Route diagnostics: H2 Trados → memoQ → Trados

## Route judgement

{
  "level": "round-trip preliminary",
  "step_levels": [
    "partially stable route segment",
    "partially stable route segment"
  ],
  "worst_step_index_1_based": 1,
  "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
  "end_to_end_level": "stable route segment"
}

## Stepwise results

### Step 1: Trados → memoQ

- Level: **partially stable route segment**
- Rationale: content-layer mean=99.83; metadata/identifier-layer mean=54.17; detected: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

### Step 2: memoQ → Trados

- Level: **partially stable route segment**
- Rationale: content-layer mean=99.83; metadata/identifier-layer mean=38.54; detected: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

## End-to-end: Trados → Trados

- Level: **stable route segment**
- Rationale: content-layer mean=100.0; metadata/identifier-layer mean=93.75
