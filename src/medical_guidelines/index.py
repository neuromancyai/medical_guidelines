from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel


class Entry(BaseModel):
    id: str
    name: str
    path: Path


type Index = Mapping[str, Entry]
