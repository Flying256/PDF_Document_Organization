#!/usr/bin/env python3
"""Extract PDF text page by page for custom note generation."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    text = text.replace("\x0c", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def pdfinfo_page_count(pdf_path: Path) -> int | None:
    exe = shutil.which("pdfinfo")
    if not exe:
        return None
    proc = subprocess.run([exe, str(pdf_path)], text=True, capture_output=True)
    if proc.returncode != 0:
        return None
    match = re.search(r"^Pages:\s+(\d+)\s*$", proc.stdout, flags=re.M)
    return int(match.group(1)) if match else None


def pypdf_page_count(pdf_path: Path) -> int | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    return len(PdfReader(str(pdf_path)).pages)


def get_page_count(pdf_path: Path) -> int:
    count = pdfinfo_page_count(pdf_path) or pypdf_page_count(pdf_path)
    if not count:
        raise SystemExit("Could not determine page count. Install poppler pdfinfo or pypdf.")
    return count


def extract_page_pdftotext(pdf_path: Path, page: int) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not found")
    proc = subprocess.run(
        [exe, "-layout", "-enc", "UTF-8", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"pdftotext failed on page {page}")
    return clean_text(proc.stdout)


def extract_pages_pdftotext(pdf_path: Path, page_count: int) -> list[dict[str, object]]:
    pages = []
    for page in range(1, page_count + 1):
        text = extract_page_pdftotext(pdf_path, page)
        pages.append({"page": page, "text": text, "char_count": len(text), "method": "pdftotext"})
        print(f"page {page}/{page_count}: {len(text)} chars", flush=True)
    return pages


def extract_pages_pypdf(pdf_path: Path) -> list[dict[str, object]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf is not installed") from exc

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        pages.append({"page": index, "text": text, "char_count": len(text), "method": "pypdf"})
        print(f"page {index}/{len(reader.pages)}: {len(text)} chars", flush=True)
    return pages


def write_outputs(pdf_path: Path, out_dir: Path, basename: str, pages: list[dict[str, object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{basename}.pages.json"
    txt_path = out_dir / f"{basename}.pages.txt"

    payload = {
        "source": str(pdf_path),
        "page_count": len(pages),
        "total_chars": sum(int(p["char_count"]) for p in pages),
        "low_text_pages": [p["page"] for p in pages if int(p["char_count"]) < 80],
        "pages": pages,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    chunks = []
    for p in pages:
        chunks.append(f"=== Page {p['page']} ===\n{p['text']}\n")
    txt_path.write_text("\n".join(chunks), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {txt_path}")
    if payload["low_text_pages"]:
        print("low_text_pages=" + ",".join(map(str, payload["low_text_pages"])))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from a PDF page by page.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--basename", default=None)
    parser.add_argument("--method", choices=["auto", "pdftotext", "pypdf"], default="auto")
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    out_dir = (args.out_dir or pdf_path.parent).resolve()
    basename = args.basename or pdf_path.stem

    try:
        if args.method in {"auto", "pdftotext"}:
            pages = extract_pages_pdftotext(pdf_path, get_page_count(pdf_path))
        else:
            pages = extract_pages_pypdf(pdf_path)
    except Exception as exc:
        if args.method != "auto":
            raise SystemExit(str(exc)) from exc
        print(f"pdftotext unavailable or failed: {exc}; falling back to pypdf", file=sys.stderr)
        pages = extract_pages_pypdf(pdf_path)

    write_outputs(pdf_path, out_dir, basename, pages)


if __name__ == "__main__":
    main()
