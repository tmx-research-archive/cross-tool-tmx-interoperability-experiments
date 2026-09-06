# Diagnostics: H0 canonical → memoQ

Pre: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/0_Canonical TMX/GA_R1.tmx`

Post: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/1_H0&C0/memoQ/T1/GA_memoQ_T1.tmx`

## Judgement

- Level: **moderate first-pass transformation**
- Rationale: content-layer mean=99.17; metadata/identifier-layer mean=83.13; detected: language_code_case_normalised, tool_specific_props_added, header_values_changed, duplicate_text_fingerprints_detected_matching_may_need_manual_check

## Matching

- Strategy used: `hybrid`
- tuid overlap ratio: `0.99`
- matched TU count: `99`
- match method counts: `{'tuid': 99}`
- low-confidence matched TUs: `0`
- confidence: `high`

## Detected transformations

- language_code_case_normalised
- tool_specific_props_added
- header_values_changed
- duplicate_text_fingerprints_detected_matching_may_need_manual_check

## Axis scores

- A1_tu_count_retention: 99.00
- A2_text_retention: 100.00
- A2b_pure_text_retention: 100.00
- A3_inline_tag_count_retention: N/A
- A3b_tag_introduction_ratio: N/A
- A4_inline_tag_type_retention: N/A
- A4b_inline_tag_type_multiset_retention: N/A
- A5_bpt_ept_pairing_retention: N/A
- A6_dom_nesting_retention: N/A
- A6b_dom_nesting_introduction_ratio: 0.00
- A7_attribute_key_retention: N/A
- A8_attribute_value_retention: N/A
- A9a_header_field_presence_retention: 100.00
- A9b_header_value_retention: 16.67
- A10a_prop_type_retention: 100.00
- A10a_strict_prop_type_retention_per_tu: 100.00
- A10b_prop_value_retention: 100.00
- A11a_language_strict_retention: 0.00
- A11b_language_case_normalised_retention: 98.51
- A12_tuid_retention: 99.00

## Notes

A7/A8 attribute retention is position-sensitive within matched TUs. If a tool inserts or re-tokenises tags, inspect the per-TU CSV before treating low attribute scores as pure loss.
