from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel


class SearchHit(BaseModel):
    id: str
    name: str
    score: float


async def search(
    client: AsyncElasticsearch,
    index: str,
    query: str,
    size: int = 10
) -> list[SearchHit]:
    response = await client.search(
        index=index,
        query={
            "multi_match": {
                "query": query,
                "fields": ["name^3", "content"]
            }
        },
        size=size,
    )

    return [
        SearchHit(
            id=hit["_id"],
            name=hit["_source"]["name"],
            score=hit["_score"]
        )
        for hit in response["hits"]["hits"]
    ]
