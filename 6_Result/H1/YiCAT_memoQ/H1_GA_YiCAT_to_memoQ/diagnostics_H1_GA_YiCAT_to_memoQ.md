# Diagnostics: H1 YiCAT → memoQ

Pre: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/1_H0&C0/YiCAT/T1/GA_YiCAT_T1.tmx`

Post: `/Users/xxx/Documents/Codex/2026-07-21/referenced-chatgpt-conversation-this-is-untrusted/work/tu_matching_audit/experiment/Experiment/2_H1/YiCAT_to_memoQ/GA_YiCAT_to_memoQ_H1.tmx`

## Judgement

- Level: **partial interoperability**
- Rationale: content-layer mean=99.83; metadata/identifier-layer mean=75.0; detected: language_code_case_normalised, tool_specific_props_added, header_values_changed, header_fields_added

## Matching

- Strategy used: `hybrid`
- tuid overlap ratio: `1.0`
- matched TU count: `99`
- match method counts: `{'tuid': 99}`
- low-confidence matched TUs: `0`
- confidence: `high`

## Detected transformations

- language_code_case_normalised
- tool_specific_props_added
- header_values_changed
- header_fields_added

## Axis scores

- A1_tu_count_retention: 100.00
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
- A9b_header_value_retention: 25.00
- A10a_prop_type_retention: N/A
- A10a_strict_prop_type_retention_per_tu: N/A
- A10b_prop_value_retention: N/A
- A11a_language_strict_retention: 0.00
- A11b_language_case_normalised_retention: 99.50
- A12_tuid_retention: 100.00

## Notes

A7/A8 attribute retention is position-sensitive within matched TUs. If a tool inserts or re-tokenises tags, inspect the per-TU CSV before treating low attribute scores as pure loss.
