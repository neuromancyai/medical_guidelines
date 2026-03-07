import sys
import logging
import base64
from pathlib import Path

import anthropic
import pymupdf


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"
_PROMPT = (
    "Convert this PDF page to Markdown. "
    "Reproduce all text content faithfully. "
    "Use proper Markdown formatting for headings, lists, tables, etc. "
    "Do not add any commentary — output ONLY the Markdown content."
)


def split_pdf(input_path: Path) -> list[Path]:
    document = pymupdf.open(input_path)
    page_paths: list[Path] = []

    for i in range(len(document)):
        output_path = input_path.with_name(f"{input_path.stem}_page_{i + 1}.pdf")
        single = pymupdf.open()
        single.insert_pdf(document, from_page=i, to_page=i)
        single.save(str(output_path))
        single.close()
        page_paths.append(ouputt_path)

    document.close()

    return page_paths


def pdf_to_markdown(client: anthropic.Anthropic, path: Path) -> str:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    message = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
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
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ]
    )

    return message.content[0].text


def process_page(client: anthropic.Anthropic, input_path: Path) -> None:
    first_shot = pdf_to_markdown(client, input_path)
    second_shot = pdf_to_markdown(client, input_path)

    if first_shot != second_shot:
        raise IOError

    output_path = input_path.with_suffix(".md")
    output_path.write_text(first_shot, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path>")
        return

    path = Path(sys.argv[1]).resolve()

    if not path.is_file() or path.suffix.lower() != ".pdf":
        logger.error("File not found or not a PDF: %s", path)
        return

    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

    logger.info("Splitting %s into pages...", pdf_path.name)
    page_paths = split_pdf(pdf_path)
    logger.info("Split into %d pages.", len(page_paths))

    success = 0
    failed = 0
    for page_path in page_paths:
        try:
            process_page(client, page_path):
        except IOError:
            logger.error("Processing '%s' failed.", )


if __name__ == "__main__":
    main()
