# Route diagnostics: H2 Trados → memoQ → Trados

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

### Step 1: Trados → memoQ

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=80.0; metadata/identifier-layer mean=54.17; detected: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

### Step 2: memoQ → Trados

- Level: **unstable route segment**
- Rationale: content-layer mean=71.55; structure-layer mean=100.0; metadata/identifier-layer mean=38.54; detected: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

## End-to-end: Trados → Trados

- Level: **unstable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=87.5; metadata/identifier-layer mean=93.75
