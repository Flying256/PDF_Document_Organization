from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


MATH_PATTERN = re.compile(r"(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)")


def escape_preserving_math(text: str) -> str:
    parts = []
    last = 0
    for match in MATH_PATTERN.finditer(text):
        parts.append(tex_escape(text[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(tex_escape(text[last:]))
    return "".join(parts)


def inline_markup(text: str) -> str:
    text = escape_preserving_math(text.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
    return text


def close_list(out: list[str], list_mode: str | None) -> str | None:
    if list_mode:
        out.append(rf"\end{{{list_mode}}}")
    return None


def markdown_to_latex(markdown: str) -> str:
    out: list[str] = []
    paragraph: list[str] = []
    list_mode: str | None = None
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(inline_markup(" ".join(paragraph)))
            out.append("")
            paragraph = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            flush_paragraph()
            list_mode = close_list(out, list_mode)
            out.append(r"\end{verbatim}" if in_code else r"\begin{verbatim}")
            in_code = not in_code
            continue

        if in_code:
            out.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            list_mode = close_list(out, list_mode)
            out.append("")
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            list_mode = close_list(out, list_mode)
            level = len(heading.group(1))
            title = inline_markup(heading.group(2))
            command = {1: "section", 2: "subsection", 3: "subsubsection"}.get(level, "paragraph")
            out.append(rf"\{command}{{{title}}}")
            continue

        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            desired = "itemize" if bullet else "enumerate"
            if list_mode != desired:
                list_mode = close_list(out, list_mode)
                out.append(rf"\begin{{{desired}}}")
                list_mode = desired
            out.append(rf"\item {inline_markup((bullet or numbered).group(1))}")
            continue

        if re.match(r"^\s*\|.*\|\s*$", line):
            flush_paragraph()
            list_mode = close_list(out, list_mode)
            out.append(r"\begin{verbatim}")
            out.append(line)
            out.append(r"\end{verbatim}")
            continue

        list_mode = close_list(out, list_mode)
        paragraph.append(line.strip())

    flush_paragraph()
    close_list(out, list_mode)
    if in_code:
        out.append(r"\end{verbatim}")
    return "\n".join(out)


def build_tex(markdown: str, title: str, source: str | None) -> str:
    source_line = rf"\large 来源：{tex_escape(source)}" if source else ""
    body = markdown_to_latex(markdown)
    return rf"""\documentclass[UTF8,11pt]{{ctexart}}
\usepackage[a4paper,margin=2.05cm]{{geometry}}
\usepackage{{amsmath,amssymb,mathtools}}
\usepackage{{booktabs,longtable,array}}
\usepackage{{enumitem}}
\usepackage{{hyperref}}
\hypersetup{{colorlinks=false,pdfborder={{0 0 0}}}}
\setlist{{leftmargin=2.2em,itemsep=0.25em,topsep=0.25em}}
\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0.25em}}
\emergencystretch=3em
\sloppy
\title{{\Huge {tex_escape(title)}}}
\author{{}}
\date{{}}

\begin{{document}}
\maketitle
\thispagestyle{{empty}}
\begin{{center}}
{source_line}
\end{{center}}
\newpage
\tableofcontents
\newpage

{body}

\end{{document}}
"""


def compile_tex(tex_path: Path, compiler: str) -> Path:
    pdf_path = tex_path.with_suffix(".pdf")
    if compiler == "none":
        return pdf_path
    exe = shutil.which("tectonic")
    if not exe:
        raise SystemExit("tectonic not found on PATH. Use the bundled LaTeX plugin compile_latex.py.")
    subprocess.run([exe, "-X", "compile", "--outdir", str(tex_path.parent), "--outfmt", "pdf", str(tex_path)], check=True)
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown notes to ctexart LaTeX/PDF.")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--title", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--basename", default=None)
    parser.add_argument("--compiler", choices=["none", "tectonic"], default="none")
    args = parser.parse_args()

    md_path = args.markdown.resolve()
    out_dir = (args.out_dir or md_path.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    basename = args.basename or md_path.stem
    title = args.title or md_path.stem
    tex_path = out_dir / f"{basename}.tex"

    markdown = md_path.read_text(encoding="utf-8")
    tex_path.write_text(build_tex(markdown, title, args.source), encoding="utf-8")
    print(f"wrote {tex_path}")
    if args.compiler != "none":
        print(f"compiled {compile_tex(tex_path, args.compiler)}")


if __name__ == "__main__":
    main()
