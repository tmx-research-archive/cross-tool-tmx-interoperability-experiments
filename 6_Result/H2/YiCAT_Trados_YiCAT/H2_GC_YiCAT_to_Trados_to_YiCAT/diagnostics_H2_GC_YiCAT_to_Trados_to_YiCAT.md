# Route diagnostics: H2 YiCAT → Trados → YiCAT

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

### Step 1: YiCAT → Trados

- Level: **unstable route segment**
- Rationale: content-layer mean=91.29; structure-layer mean=94.73; metadata/identifier-layer mean=58.33; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, tool_specific_props_added, inline_tags_compressed_or_deleted, header_values_changed, header_fields_added; matching confidence=medium; inspect per-TU CSV if needed
- Matching: hybrid, confidence=medium, methods={'alignment_text_fingerprint': 86}, low-confidence=0
- Transformations: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, tool_specific_props_added, inline_tags_compressed_or_deleted, header_values_changed, header_fields_added

### Step 2: Trados → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=100.0; structure-layer mean=87.9; metadata/identifier-layer mean=29.17; detected: pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost
- Matching: hybrid, confidence=high, methods={'alignment_text_fingerprint': 86}, low-confidence=0
- Transformations: pre_existing_props_removed_or_replaced, header_values_changed, header_fields_lost

## End-to-end: YiCAT → YiCAT

- Level: **unstable route segment**
- Rationale: content-layer mean=91.29; structure-layer mean=94.81; metadata/identifier-layer mean=66.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, inline_tags_compressed_or_deleted; matching confidence=medium; inspect per-TU CSV if needed
