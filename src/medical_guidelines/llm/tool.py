import aiofiles

from anthropic import beta_async_tool
from anthropic.lib.tools._beta_functions import BetaAsyncFunctionTool
from anthropic.types.beta import BetaRequestDocumentBlockParam

from ..index import Index


def create_load_tool(
    index: Index,
    encoding: str = "utf-8"
) -> BetaAsyncFunctionTool:
    @beta_async_tool
    async def load_medical_guideline(
        id: str,
    ) -> list[BetaRequestDocumentBlockParam]:
        """Load a medical guideline document by its ID. Returns the full
        text content of the guideline. Use information from your system
        prompt to determine which guideline ID to load.
        """

        entry = index.get(id)

        if entry is None:
            raise ValueError(f"No guideline with ID '{id}'")

        async with aiofiles.open(
            entry.path,
            "r",
            encoding=encoding
        ) as stream:
            data = await stream.read()

        return [
            {
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": data
                },
                "title": entry.name,
                "citations": {"enabled": True}
            }
        ]

    return load_medical_guideline
