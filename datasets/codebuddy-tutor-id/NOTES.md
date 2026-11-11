# NOTES — CodeBuddy Tutor ID build

Working notes for how the 120-row set was assembled from the 55-row seed. Kept for provenance and review.

## 1. Starting point

- Started from `data/seed_v1.json` (55 already-migrated examples: 15 `syntax_error`, 15 `runtime_error`, 10 `logic_error`, 10 `code_quality`, 5 `ocr_correction`).
- Seed `instruction`, `code`, and `hint` were **not** rewritten during the initial build. The only initial-build seed edits are the factual corrections in section 2, and they touch `feedback` only. (One later exception: `syn_001` was rewritten during the review pass — see section 6.)
- Schema and field order were preserved exactly: `id, kategori, sub_kategori, bahasa_pemrograman, tingkat, instruction, code, hint, feedback, corrected_code`.

## 2. Factual fixes applied to the seed (feedback only)

1. **qual_007** — `f'{92.5:.0f}'` / `format(92.5, '.0f')` prints **`92`, not `93`**. Python uses round-half-to-even (banker's rounding), so `92.5` rounds down to the even value `92`. The example comment `# tanpa desimal: 93` was corrected to `92`, with a short note explaining the rounding rule.
2. **qual_001** — the format spec `:,.0f` produces **`90,000` (comma separator), not `90.000`**. Python's `,` thousands separator is a comma by default; the output comment `Rp 90.000` was corrected to `Rp 90,000`, with a note that `:,` uses a comma.
3. **ocr_001** — the original bullet was circular: *"'l' salah baca sebagai 'l'"*. Rewritten to say the loop variable should be **`i`**, and that handwritten **`i` is misread as `l`**.
4. **ocr_004** — the student `print(“Halo,” nama)` is also **missing the comma** between the two `print` arguments. The gold `corrected_code` already adds it (`print('Halo,', nama)`), but the feedback did not mention it; a sentence about the missing comma was added.
5. **syn_010** — the claim that `input` was *"dikalikan dengan string"* (multiplied by a string) is wrong. `int(input'...')` is a **`SyntaxError`**: a name (`input`) is directly followed by a string literal, which Python does not allow; `input(...)` needs parentheses. Wording corrected.
6. **qual_010** — the claim *"15 baris → 5 baris"* was inaccurate. Recount of the actual strings: the student if-elif program is **17 lines** and the dictionary version is **11 lines**. The feedback now states `17 baris → 11 baris`. (Line counts were computed programmatically from the exact `code` / `corrected_code` strings, not estimated.)

All other seed content is unchanged.

## 3. New examples (65 added → 120 total)

New ids were chosen so they do not collide with the seed. Each new example is original, beginner-level (*pemula*), Python-only, and targets a sub-category that was thin or missing in the seed. No seed bug was cloned with only renamed variables.

Target mix reached exactly: syntax 25, runtime 25, logic 25, quality 25, OCR 20.

- **syntax_error (+10):** `syn_016`–`syn_025`
  - new sub-categories: `missing_comma`, `python2_print`, `keyword_as_identifier`, `unmatched_bracket`, `unexpected_indent`, `typo_keyword` (new token), `quote_in_string`, `fstring_error`, `missing_colon` (for-loop), `return_outside_function`.
- **runtime_error (+10):** `run_016`–`run_025`
  - fills previously-missing exceptions: `ValueError` (bad `int()` conversion, and unpacking), `TypeError` (`len()` on int, int not subscriptable, int not callable), `ModuleNotFoundError`, `IndexError` (string index), `UnboundLocalError`, `FileNotFoundError`, `ValueError` (math domain / `sqrt` of negative).
- **logic_error (+15):** `log_011`–`log_025`
  - `integer_division`, `operator_precedence`, `logic_operator` (`or` vs `and`), `wrong_initialization` (min and max seeded with 0), `type_comparison` (int vs str), `truthiness` (`or 'iya'`), `wrong_formula` (percent as `*20`, circle area `r*2`), `wrong_accumulator` (append value vs square), `counter_logic` (`=1` vs `+=1`), `swapped_logic` (odd/even labels), `off_by_one` (string slice), `misplaced_statement` (average inside loop), `premature_return` ("all pass" returns on first pass).
- **code_quality (+15):** `qual_011`–`qual_025`
  - `guard_clause`, `boolean_comparison` (`== True`), `use_enumerate`, `membership_in`, `builtin_function` (`sum`), `string_join`, `flatten_nested_if`, `ternary_expression`, `avoid_global`, `pep8_spacing`, `extract_variable` (DRY), `dict_get_default`, `use_any_all`, `early_continue`, `number_formatting` (`:.2f`).
- **ocr_correction (+15):** `ocr_006`–`ocr_020`
  - distinct confusable-character mechanisms: `rn`↔`m` (`import`), `cl`↔`d` (`def`), `vv`↔`w` (`while`), `9`↔`g` (`range`), `5`↔`S` (name), `8`↔`B` (numbers), `(`↔`{`, `.`↔`,` (decimal→tuple), merged tokens (`defhitung`), `3`↔`E` (`else`), `0`↔`o` (`for`), `1`↔`l` (name), split token (`pri nt`), `l`↔`i` (`if`), bracket mismatch (`]`↔`)`).

## 4. Split

- 90 train / 30 test, stratified by `kategori`, no `id` overlap.
- Per-category test counts: syntax 7, runtime 6, logic 6, quality 6, OCR 5 (= 30).
- The test set mixes seed and new rows and spans varied sub-categories on purpose. Test ids:
  - syntax: `syn_003, syn_008, syn_011, syn_017, syn_019, syn_021, syn_024`
  - runtime: `run_005, run_009, run_013, run_016, run_020, run_022`
  - logic: `log_002, log_006, log_011, log_014, log_018, log_021`
  - quality: `qual_003, qual_007, qual_013, qual_016, qual_019, qual_024`
  - OCR: `ocr_003, ocr_008, ocr_013, ocr_016, ocr_019`

## 5. Judgment calls

- **`feedback` vs `corrected_code` alignment.** Where `feedback` lists several valid fixes, `corrected_code` holds exactly one beginner-friendly primary fix; the alternatives stay in `feedback`. This matches the seed's existing convention.
- **Outputs described in `feedback` are read-verified, not executed.** Per the build constraints, no student code or gold code was run. `corrected_code` was validated with `ast.parse` (syntax only). Printed outputs / return values quoted in `feedback` were checked by hand.
- **`ocr_013` (`.`↔`,`) and `run_017` ("too many values to unpack")** describe runtime consequences (`19,99` becomes a tuple; unpacking mismatch raises `ValueError`) without executing anything; these were reasoned through, not run.
- **OCR examples are synthetic.** They model plausible OCR confusions of handwritten/photographed code rather than the output of any particular OCR engine.
- **A few new `code` snippets intentionally don't parse** (that is the bug being taught). Only `corrected_code` is guaranteed to be syntactically valid.

## 6. Review-pass fixes (applied after first review)

Content-only fixes; the 120-row set, the 25/25/25/25/20 mix, the 90/30 split membership, and the schema/key order are all unchanged. Edits were mirrored across `data/seed_v1.json` (for the seed row), `data/all.json`, and the matching split file so the three stay consistent.

1. **ocr_013** — `19.99 * 0.1` does **not** print `1.999`; it prints `1.9989999999999999` (binary floating point). The feedback's output comment was corrected to the real value `1.9989999999999999`. (An earlier draft suggested `round(pajak, 2)` would give `1.99`; that is wrong — `round(19.99 * 0.1, 2)` is `2.0` because the third decimal is `8`, so the tidy-rounding aside was dropped. The row's lesson is the OCR comma/period confusion, not formatting.) The `code` / `corrected_code` were left as-is.
2. **syn_001** — the old student `code` (`prin('Halo Dunia')`) is valid syntax and only raises `NameError` at runtime, which contradicted its `syntax_error` / `typo_keyword` label. To keep the 25/25/25/25/20 mix, the row was **not** relabelled; instead the example was rewritten to a genuine keyword-typo `SyntaxError`: `iff nilai >= 75:` (typo of `if`). `instruction`, `hint`, `feedback`, and `corrected_code` were updated to match. `id`, `kategori` (`syntax_error`), and `sub_kategori` (`typo_keyword`) are unchanged. After the edit, `ast.parse` on the student `code` fails and `corrected_code` parses.
3. **qual_025** — the feedback now states that `int(harga * 100) / 100` also **changes the result** (it truncates 19.9876 → 19.98), whereas `:.2f` rounds to 19.99 — not merely a tidier display.
4. **log_013** — added a line noting that `0 <= nilai <= 100` (used in `corrected_code`) means exactly the same as `nilai >= 0 and nilai <= 100`, so the hint/feedback ("use `and`") and the gold code are consistent.
5. **qual_011** — the `instruction` previously said the code was "bersarang terlalu dalam" (deeply nested), but the snippet is a flat if/else. Rewritten to match the actual lesson: an unnecessary `else` after `return` (guard clause).
6. **README.md** — citation year changed from 2025 to 2026.
7. Removed the untracked duplicate `seed_v1.json` from the repo root; the canonical copy remains at `data/seed_v1.json`.

## 7. For reviewer attention

- Confirm the tutor voice and difficulty of the 65 new rows match the seed to your liking (tone, analogy use, length).
- Spot-check the recomputed numbers in the two formatting fixes (qual_001, qual_007) and the line recount (qual_010) against your own reading.
- Confirm the test-split selection (which specific rows are held out) suits your evaluation plan; it is easy to re-stratify if you want different coverage.
