import re

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import aiohttp

from bs4 import BeautifulSoup
from pydantic import BaseModel
from yarl import URL

from .utility import doi_to_file_name, download_file


_BASE_URL = URL("https://www.esge.com/")
_PAGE_API_URL = _BASE_URL / "api" / "live" / "pages"
_DOI_PATTERN = re.compile(r"10\.\d{4,9}\/[-._;()/a-zA-Z0-9]+")
_MALFORMED_DOIS = {
    "DOI https://doi.org/0.1055/a-2292-2494": "10.1055/a-2292-2494"
}


class Entry(BaseModel):
    name: str
    doi: str
    url: URL


type Index = list[Entry]
type _Node = dict[str, Any]


def _find_nodes(
    root: _Node,
    predicate: Callable[[_Node], bool]
) -> Iterable[_Node]:
    candidates = [root]

    while candidates:
        candidate = candidates.pop()

        if predicate(candidate):
            yield candidate

        candidates.extend(candidate.get("children", []))


def _find_nodes_by_title(root: _Node, title: str) -> Iterable[_Node]:
    return _find_nodes(root, lambda x: x.get("title") == title)


def _extract_doi(text: str) -> str:
    if text in _MALFORMED_DOIS:
        return _MALFORMED_DOIS[text]

    match = _DOI_PATTERN.search(text)

    if not match:
        raise ValueError(f"Couldn't extract DOI from '{text}'")

    return match.group()


async def download_index(session: aiohttp.ClientSession) -> Index:
    index = []
    details = []

    async with session.get(_PAGE_API_URL / "guidelines") as response:
        data = await response.json()

    for node in _find_nodes_by_title(data["content"], "copy list"):
        html = node["properties"]["text"]
        soup = BeautifulSoup(html, "html.parser")

        for anchor in soup.find_all("a"):
            href = anchor["href"]
            name = anchor.get_text().strip()

            if "://" in href:
                detail_url = _PAGE_API_URL / URL(href).path[1:]
            else:
                detail_url = _PAGE_API_URL / href[1:]

            details.append((detail_url, name))

    for detail_url, name in details:
        async with session.get(detail_url) as response:
            data = await response.json()

        content = data["content"]
        button_node = next(
            _find_nodes_by_title(content, "View full guideline")
        )

        doi_node = next(_find_nodes_by_title(content, "Link + Copyright"))
        html = doi_node["properties"]["text"]
        soup = BeautifulSoup(html, "html.parser")
        target_name = button_node["properties"]["targetName"][1:]

        if "://" in target_name:
            entry_url = URL(button_node["properties"]["targetName"])
        else:
            entry_url = \
                _BASE_URL / button_node["properties"]["targetName"][1:]

        entry_doi = \
            _extract_doi(list(soup.find("h6").children)[0].get_text())

        entry = Entry(
            name=name,
            url=entry_url,
            doi=entry_doi
        )

        index.append(entry)

    return index


async def download_guidelines(
    index: Index,
    root: Path,
    session: aiohttp.ClientSession
) -> None:
    root.mkdir(parents=True, exist_ok=True)

    for entry in index:
        file = (root / doi_to_file_name(entry.doi)).with_suffix(".pdf")

        await download_file(entry.url, file, session)
