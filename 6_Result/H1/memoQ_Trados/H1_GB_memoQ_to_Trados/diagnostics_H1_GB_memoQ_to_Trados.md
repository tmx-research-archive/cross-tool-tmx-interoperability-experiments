# Diagnostics: H1 memoQ → Trados

Pre: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/1_H0&C0/memoQ/T1/GB_memoQ_T1_Trados-compatible.tmx`

Post: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/2_H1/memoQ_to_Trados/GB_memoQ_to_Trados_H1.tmx`

## Judgement

- Level: **poor interoperability**
- Rationale: content-layer mean=71.55; structure-layer mean=100.0; metadata/identifier-layer mean=23.33; detected: tuid_overlap_low_matching_fell_back_to_text_or_position, tuid_removed_or_reassigned, language_code_case_normalised, tool_specific_props_added, pre_existing_props_removed_or_replaced, header_values_changed

## Matching

- Strategy used: `hybrid`
- tuid overlap ratio: `0.0`
- matched TU count: `99`
- match method counts: `{'alignment_text_fingerprint': 99}`
- low-confidence matched TUs: `0`
- confidence: `high`

## Detected transformations

- tuid_overlap_low_matching_fell_back_to_text_or_position
- tuid_removed_or_reassigned
- language_code_case_normalised
- tool_specific_props_added
- pre_existing_props_removed_or_replaced
- header_values_changed

## Axis scores

- A1_tu_count_retention: 100.00
- A2_text_retention: 15.15
- A2b_pure_text_retention: 100.00
- A3_inline_tag_count_retention: 100.00
- A3b_tag_introduction_ratio: 0.00
- A4_inline_tag_type_retention: 100.00
- A4b_inline_tag_type_multiset_retention: 100.00
- A5_bpt_ept_pairing_retention: 100.00
- A6_dom_nesting_retention: N/A
- A6b_dom_nesting_introduction_ratio: 0.00
- A7_attribute_key_retention: 100.00
- A8_attribute_value_retention: 100.00
- A9a_header_field_presence_retention: 100.00
- A9b_header_value_retention: 16.67
- A10a_prop_type_retention: 0.00
- A10a_strict_prop_type_retention_per_tu: 0.00
- A10b_prop_value_retention: 0.00
- A11a_language_strict_retention: 0.00
- A11b_language_case_normalised_retention: 99.50
- A12_tuid_retention: 0.00

## Notes

A7/A8 attribute retention is position-sensitive within matched TUs. If a tool inserts or re-tokenises tags, inspect the per-TU CSV before treating low attribute scores as pure loss.
