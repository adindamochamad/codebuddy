---
license: apache-2.0
language:
- id
tags:
- code
- python
- education
- indonesian
- tutoring
task_categories:
- text-generation
pretty_name: CodeBuddy Tutor ID
size_categories:
- n<1K
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.jsonl
  - split: test
    path: data/test.jsonl
---

# CodeBuddy Tutor ID

**Ringkasan (Bahasa Indonesia):** Dataset kecil berisi 120 contoh kode Python tingkat pemula (SMP/SMA) beserta *hint* dan penjelasan tutor dalam Bahasa Indonesia. Setiap contoh berisi satu program siswa yang bermasalah (atau bisa diperbaiki), petunjuk singkat yang mengarahkan tanpa memberi jawaban jadi, penjelasan lengkap gaya tutor, dan kode perbaikannya. Dataset ini dikurasi secara manual untuk mengevaluasi (dan secara opsional melatih ringan) asisten koding berbahasa Indonesia. Lisensi Apache-2.0.

---

## Dataset summary (English)

CodeBuddy Tutor ID is a small, hand-curated dataset of **120 beginner Python examples** paired with Indonesian-language tutoring. It is built for evaluating how well a model acts as a patient coding tutor for Indonesian students (roughly junior/senior high school, *pemula* level), and can optionally be used for light supervised fine-tuning.

Each row contains:
- a student program that is broken or improvable,
- a short **hint** that points at the problem and nudges the learner without handing over the full solution,
- a full **feedback** explanation in a warm tutor voice (diagnosis → explanation → fix → optional tip), and
- the **corrected_code** (the gold Python program).

The examples are original and written for this dataset. They are not scraped from tutorials and are not derived from other Hub datasets.

## Intended use

- **Primary:** evaluating Indonesian coding-tutor behavior — clarity of diagnosis, quality of hints, correctness of fixes, and tone.
- **Secondary:** optional light instruction tuning (SFT) for small Indonesian coding-tutor models.
- **Out of scope:** general-purpose code generation benchmarks, non-Python languages, advanced/competitive programming, and any use that assumes production-grade coverage.

## Languages

- Explanations, hints, and instructions: **Bahasa Indonesia**.
- Code: **Python** only.

## Schema

Every row has these fields, in this exact order:

| field | description |
|---|---|
| `id` | unique id, prefixed by category (`syn_`, `run_`, `log_`, `qual_`, `ocr_`) |
| `kategori` | one of `syntax_error`, `runtime_error`, `logic_error`, `code_quality`, `ocr_correction` |
| `sub_kategori` | finer-grained label (e.g. `missing_colon`, `IndexError`, `off_by_one`) |
| `bahasa_pemrograman` | always `"python"` |
| `tingkat` | always `"pemula"` |
| `instruction` | task prompt in Bahasa Indonesia (unique per row) |
| `code` | the student program (whitespace preserved; may contain errors) |
| `hint` | 2–5 short Indonesian sentences; nudges without giving the full solution |
| `feedback` | full tutor explanation (may include a `Kode yang benar:` block) |
| `corrected_code` | the gold Python program only (no markdown fences, no labels) |

Notes:
- `code` intentionally contains broken programs for the error categories, so it will not always parse. **Do not execute `code`** — a few examples (e.g. infinite loops) are unsafe to run. Every `corrected_code` has been checked for valid syntax with `ast.parse` (parse only, never executed).
- `hint` never contains the full corrected program or a ready-to-copy solution.

## Categories

The five categories, with the beginner mistakes they cover:

- **syntax_error** — typos in keywords, missing colons/parentheses/commas, indentation, quote problems, Python-2-style `print`, using a keyword as a variable name, etc.
- **runtime_error** — `NameError`, `TypeError`, `IndexError`, `KeyError`, `ValueError`, `ZeroDivisionError`, `AttributeError`, `RecursionError`, `UnboundLocalError`, `ModuleNotFoundError`, `FileNotFoundError`.
- **logic_error** — wrong operators/conditions, off-by-one, integer division, operator precedence, bad accumulator/initialization, swapped branches, premature return, wrong formulas.
- **code_quality** — naming, magic numbers, duplication, decomposition, comments, list comprehensions, f-strings, error handling, `enumerate`, `in`/`join`, guard clauses, ternaries, `any`/`all`, avoiding globals, PEP 8 spacing.
- **ocr_correction** — reconstructing Python from noisy OCR of handwritten/photographed code: confusable characters (`rn`↔`m`, `cl`↔`d`, `vv`↔`w`, `0`↔`o`, `1`↔`l`, `5`↔`S`, `8`↔`B`, `9`↔`g`, `3`↔`E`), smart quotes, `:`↔`;`, bracket mismatches, lost or inserted spaces, lost indentation, and comma/period confusion.

## Splits

| split | file | rows | syntax | runtime | logic | quality | ocr |
|---|---|---:|---:|---:|---:|---:|---:|
| train | `data/train.jsonl` | 90 | 18 | 19 | 19 | 19 | 15 |
| test | `data/test.jsonl` | 30 | 7 | 6 | 6 | 6 | 5 |
| **all** | `data/all.json` | **120** | **25** | **25** | **25** | **25** | **20** |

The split is stratified by `kategori` with no `id` overlap. The test split deliberately mixes original seed rows and newer examples, and spans a diverse set of sub-categories, so it is not just leftover rows of one kind.

### Files

- `data/all.json` — all 120 rows as a pretty-printed JSON array (`ensure_ascii=False`, 2-space indent).
- `data/train.jsonl`, `data/test.jsonl` — the final split, one JSON object per line.
- `data/seed_v1.json` — the original 55 curated examples (migrated schema) that this set grew from, kept for provenance. See `NOTES.md`.

## Provenance

The dataset started from 55 hand-written seed examples (15 syntax, 15 runtime, 10 logic, 10 quality, 5 OCR). 65 new original examples were added to reach 120 with a balanced mix, filling in thin or missing sub-categories. A small number of factual corrections were applied to the seed explanations; these are listed in `NOTES.md`.

## Limitations

- **Python only**, and only **beginner** (*pemula*) level — no other languages, no intermediate/advanced material.
- **Small and curated**, not a scrape: 120 rows cannot represent the full space of beginner mistakes, and category/sub-category coverage is uneven.
- Explanations reflect **one tutor's voice and pedagogical choices**; where several valid fixes exist, one beginner-friendly fix is chosen as `corrected_code` and alternatives are mentioned in `feedback`.
- `corrected_code` is checked for **syntax** only (`ast.parse`); it has **not** been executed, so runtime behavior and printed outputs described in `feedback` are author-verified by reading, not by running.
- OCR examples are **synthetic reconstructions** of plausible OCR errors, not outputs of a specific OCR engine on real scans.
- Not a safety or security benchmark, and not suitable as a production correctness oracle.

## Author & license

- **Author:** Adinda Panca Mochamad
- **License:** Apache-2.0

## Links

- Project / source code: https://github.com/adindamochamad/codebuddy
- Demo (Hugging Face Space): https://huggingface.co/spaces/adindamochamad/codebuddy
- Dataset: https://huggingface.co/datasets/adindamochamad/codebuddy-tutor-id

## Citation

```
@misc{codebuddy_tutor_id,
  title  = {CodeBuddy Tutor ID: An Indonesian beginner Python coding-tutor dataset},
  author = {Mochamad, Adinda Panca},
  year   = {2026},
  note   = {Apache-2.0}
}
```
