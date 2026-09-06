# Route diagnostics: H2 YiCAT → Trados → YiCAT

## Route judgement

{
  "level": "round-trip preliminary",
  "step_levels": [
    "partially stable route segment",
    "partially stable route segment"
  ],
  "worst_step_index_1_based": 2,
  "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
  "end_to_end_level": "partially stable route segment"
}

## Stepwise results

### Step 1: YiCAT → Trados

- Level: **partially stable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=100.0; metadata/identifier-layer mean=58.33; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, tool_specific_props_added, header_values_changed, header_fields_added
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, tool_specific_props_added, header_values_changed, header_fields_added

### Step 2: Trados → YiCAT

- Level: **partially stable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=90.0; metadata/identifier-layer mean=29.17; detected: pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 99}, low-confidence=0
- Transformations: pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost

## End-to-end: YiCAT → YiCAT

- Level: **partially stable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=100.0; metadata/identifier-layer mean=66.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned
