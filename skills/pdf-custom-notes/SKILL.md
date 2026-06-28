---
name: pdf-custom-notes
description: Extract, organize, and summarize PDF documents into user-defined structured notes, study handouts, Markdown, LaTeX, DOCX-ready text, or compiled PDFs. Use when the user asks to整理/概括 PDF 文档, make detailed notes from PDFs, follow a provided example format, customize summary depth/content requirements, preserve formulas/page references, or turn PDF source material into polished notes.
---

# PDF Custom Notes

Use this skill to turn one or more PDFs into structured notes according to the user's requested format and depth. The output requirements are user-defined: mirror an example format when provided, otherwise ask or infer the desired structure before drafting.

## Workflow

1. Clarify the output contract when it is missing: target file type, language, depth, chapter/section structure, whether to include formulas, examples, definitions, comparisons, Q&A, glossary, page references, or exam-style summaries.
2. Inspect the PDF before summarizing. Use `pdfinfo` for page count and metadata; render sample pages when layout, formulas, tables, or scanned pages matter.
3. Extract text page by page with `scripts/extract_pdf_text.py`. Keep page markers so notes can cite source pages and formula/table problems can be checked.
4. Build notes from the extracted content using the user's requested format. Paraphrase and synthesize; do not copy long passages. Preserve important formulas, variables, assumptions, and algorithm steps. Mark uncertain OCR/extraction spots with source page numbers instead of guessing.
5. Generate the requested artifact. For PDF output, write Markdown or LaTeX, then use `scripts/notes_md_to_pdf.py` or a direct LaTeX file plus the bundled LaTeX compiler.
6. Verify the result: check page count and A4 sizing with `pdfinfo`, render representative pages with `pdftoppm`, and inspect title/TOC/content/final pages for broken Chinese text, missing formulas, or layout overflow.

## PDF Extraction

```bash
python /path/to/skill/scripts/extract_pdf_text.py \
  "/abs/source.pdf" \
  --out-dir "/abs/work-dir" \
  --basename "source_extracted"
```

This writes:

- `source_extracted.pages.json` with page-level text and extraction metadata.
- `source_extracted.pages.txt` with readable `=== Page N ===` markers.

If extraction is sparse or formulas are broken, render the relevant pages and use visual inspection. For scanned PDFs, use OCR first or tell the user OCR is required.

## Note Drafting Rules

- Treat the user's requested format as the source of truth. If the user says "按照刚刚的格式", inspect the previous artifact or ask for the example if it is not available.
- Keep page references for claims, formulas, tables, diagrams, or ambiguous extraction.
- Preserve formulas in LaTeX whenever possible. If a formula cannot be reliably reconstructed, write a placeholder such as `公式见原 PDF 第 N 页` rather than inventing it.
- Prefer dense, useful notes over slide-like summaries. Include definitions, intuition, conditions, derivations, algorithm steps, examples, and pitfalls when requested.
- Do not summarize every page uniformly when the user asks for exam notes or conceptual notes; reorganize around concepts while retaining source traceability.

## PDF Build

For Markdown notes:

```bash
python /path/to/skill/scripts/notes_md_to_pdf.py \
  "/abs/notes.md" \
  --title "资料标题" \
  --source "source.pdf" \
  --out-dir "/abs/output-dir" \
  --compiler none
```

Then compile the generated `.tex` with the bundled LaTeX plugin when `tectonic` is not on `PATH`:

```bash
python3 /Users/Zhuanz/.codex/plugins/cache/openai-bundled/latex/0.2.4/scripts/compile_latex.py \
  "/abs/output-dir/notes.tex" \
  --compiler tectonic \
  --json
```

For formula-heavy documents, it is acceptable to write the `.tex` directly instead of converting from Markdown.

## Verification Commands

```bash
pdfinfo "/abs/output.pdf"
pdftoppm -png -r 140 -f 1 -l 1 "/abs/output.pdf" "/tmp/pdf-check"
```

Sample at least the cover/TOC, early content, middle content, and final page. Report any remaining extraction uncertainty to the user.
