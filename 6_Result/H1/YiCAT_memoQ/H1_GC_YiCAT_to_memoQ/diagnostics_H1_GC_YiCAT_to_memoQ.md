# Diagnostics: H1 YiCAT → memoQ

Pre: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/1_H0&C0/YiCAT/T1/GC_YiCAT_T1.tmx`

Post: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/2_H1/YiCAT_to_memoQ/GC_YiCAT_to_memoQ_H1.tmx`

## Judgement

- Level: **poor interoperability**
- Rationale: content-layer mean=66.5; structure-layer mean=102.17; metadata/identifier-layer mean=41.67; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, inline_tags_expanded_or_reencoded, header_values_changed; matching confidence=medium; inspect per-TU CSV if needed

## Matching

- Strategy used: `hybrid`
- tuid overlap ratio: `0.0`
- matched TU count: `99`
- match method counts: `{'alignment_text_fingerprint': 6, 'sequence_similarity': 93}`
- low-confidence matched TUs: `1`
- confidence: `medium`

## Detected transformations

- tuid_overlap_low_matching_fell_back_to_text_or_position
- tuid_removed_or_reassigned
- language_code_case_normalised
- tool_specific_props_added
- inline_tags_expanded_or_reencoded
- header_values_changed
- header_fields_added

## Axis scores

- A1_tu_count_retention: 100.00
- A2_text_retention: 0.00
- A2b_pure_text_retention: 2.02
- A3_inline_tag_count_retention: 199.78
- A3b_tag_introduction_ratio: 99.78
- A4_inline_tag_type_retention: 35.22
- A4b_inline_tag_type_multiset_retention: 100.00
- A5_bpt_ept_pairing_retention: 201.10
- A6_dom_nesting_retention: N/A
- A6b_dom_nesting_introduction_ratio: 0.00
- A7_attribute_key_retention: 51.87
- A8_attribute_value_retention: 22.90
- A9a_header_field_presence_retention: 100.00
- A9b_header_value_retention: 25.00
- A10a_prop_type_retention: N/A
- A10a_strict_prop_type_retention_per_tu: N/A
- A10b_prop_value_retention: N/A
- A11a_language_strict_retention: 0.00
- A11b_language_case_normalised_retention: 99.50
- A12_tuid_retention: 0.00

## Notes

A7/A8 attribute retention is position-sensitive within matched TUs. If a tool inserts or re-tokenises tags, inspect the per-TU CSV before treating low attribute scores as pure loss.
