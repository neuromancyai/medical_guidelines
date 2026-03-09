import base64
import logging
import subprocess
import sys

from collections.abc import Generator
from difflib import SequenceMatcher
from pathlib import Path

import anthropic
import pymupdf


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

_DEFAULT_ENCODING = "utf-8"
_MODEL = "claude-opus-4-6"
_PROMPT = (
    "Convert this PDF page to Markdown. "
    "Reproduce all text content faithfully. "
    "Use proper Markdown formatting for headings, lists, tables, etc. "
    "Do not add any commentary — output ONLY the Markdown content. "
    "Convert all diagrams into valid Mermaid diagramming language notation."
)

_CONTEXT_PAGES = 3
_CONFLICT_MARKERS = ("<<<<<<< ", "=======\n", ">>>>>>> ")


class OcrError(Exception):
    def __init__(self, first: str, second: str) -> None:
        self.first = first
        self.second = second


def merge_conflict(first: str, second: str) -> str:
    first_lines = first.splitlines(keepends=True)
    second_lines = second.splitlines(keepends=True)
    result: list[str] = []

    for tag, i1, i2, j1, j2 in SequenceMatcher(None, first_lines, second_lines).get_opcodes():
        if tag == "equal":
            result.extend(first_lines[i1:i2])
        else:
            result.append(f"{_CONFLICT_MARKERS[0]}first_shot\n")
            result.extend(first_lines[i1:i2])
            if result[-1][-1] != "\n":
                result.append("\n")
            result.append(_CONFLICT_MARKERS[1])
            result.extend(second_lines[j1:j2])
            if result[-1][-1] != "\n":
                result.append("\n")
            result.append(f"{_CONFLICT_MARKERS[2]}second_shot\n")

    return "".join(result)


def has_conflict_markers(text: str) -> bool:
    return any(marker in text for marker in _CONFLICT_MARKERS)


def resolve_conflict(conflict_path: Path) -> str | None:
    subprocess.run(["code", "--wait", str(conflict_path)], check=True, shell=True)
    resolved = conflict_path.read_text(encoding=_DEFAULT_ENCODING)

    if has_conflict_markers(resolved):
        conflict_path.unlink()
        return None

    conflict_path.unlink()
    return resolved


def get_pages(document: pymupdf.Document) -> Generator[pymupdf.Document]:
    for i in range(len(document)):
        with pymupdf.open() as page:
            page.insert_pdf(document, from_page=i, to_page=i)
            yield page


def pdf_to_markdown(
    client: anthropic.Anthropic,
    path: Path,
    previous_pages: list[str] | None = None,
    example: str | None = None,
) -> str:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    prompt = _PROMPT
    if example:
        prompt += (
            "\n\nHere is an example of the desired Markdown output "
            "for reference on formatting, terminology, and style:\n\n"
            + example
        )
    if previous_pages:
        context = "\n\n---\n\n".join(previous_pages)
        prompt += (
            f"\n\nHere is the Markdown output of the previous {len(previous_pages)} "
            "page(s) for consistency in formatting, terminology, and style:\n\n"
            + context
        )

    message = client.messages.create(
        model=_MODEL,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": data
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
    )

    return message.content[0].text


def process_page(
    client: anthropic.Anthropic,
    input_path: Path,
    previous_pages: list[str] | None = None,
    example: str | None = None,
) -> str:
    first_shot = pdf_to_markdown(client, input_path, previous_pages, example)
    second_shot = pdf_to_markdown(client, input_path, previous_pages, example)

    if first_shot != second_shot:
        raise OcrError(first_shot, second_shot)

    return first_shot


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: python {sys.argv[0]} <input_path> [example_md_path]")
        return

    input_path = Path(sys.argv[1]).resolve()

    if not input_path.is_file() or input_path.suffix.lower() != ".pdf":
        logger.error("File not found or not a PDF: %s", input_path)
        return

    example: str | None = None
    if len(sys.argv) == 3:
        example_path = Path(sys.argv[2]).resolve()
        if not example_path.is_file() or example_path.suffix.lower() != ".md":
            logger.error("Example file not found or not a Markdown file: %s", example_path)
            return
        example = example_path.read_text(encoding=_DEFAULT_ENCODING)

    page_paths: list[Path] = []

    with pymupdf.open(input_path) as document:
        for i, page in enumerate(get_pages(document)):
            page_path = input_path.with_name(
                f"{input_path.stem}_page_{i + 1}.pdf"
            )
            page_paths.append(page_path)

            if not page_path.exists():
                page.save(str(page_path))

    client = anthropic.Anthropic()
    recent_pages: list[str] = []

    for page_path in page_paths:
        md_path = page_path.with_suffix(".md")

        if md_path.exists():
            md_content = md_path.read_text(encoding=_DEFAULT_ENCODING)
        else:
            context = recent_pages[-_CONTEXT_PAGES:] or None

            while True:
                try:
                    md_content = process_page(client, page_path, context, example)
                    break
                except OcrError as e:
                    conflict_path = page_path.with_suffix(".md.conflict")
                    conflict_path.write_text(
                        merge_conflict(e.first, e.second),
                        encoding=_DEFAULT_ENCODING
                    )
                    md_content = resolve_conflict(conflict_path)
                    if md_content is not None:
                        break

            md_path.write_text(md_content, encoding=_DEFAULT_ENCODING)

        recent_pages.append(md_content)

    output_path = input_path.with_suffix(".md")
    parts: list[str] = []

    for page_path in page_paths:
        md_path = page_path.with_suffix(".md")
        parts.append(md_path.read_text(encoding=_DEFAULT_ENCODING))

    output_path.write_text("\n\n".join(parts), encoding=_DEFAULT_ENCODING)

    for page_path in page_paths:
        page_path.unlink()
        page_path.with_suffix(".md").unlink()


if __name__ == "__main__":
    main()
