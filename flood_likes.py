import asyncio
import httpx

URL = "http://127.0.0.1:8000/graphql"  # если запустили на 8001 — временно укажите 8001
COURSE_ID = "api-design"
BURST = 50


async def get_likes(client: httpx.AsyncClient) -> int:
    res = await client.post(
        URL,
        json={"query": f'{{ course(id: "{COURSE_ID}") {{ likes }} }}'},
    )
    res.raise_for_status()
    return res.json()["data"]["course"]["likes"]


async def send_like(client: httpx.AsyncClient, sem: asyncio.Semaphore) -> None:
    async with sem:
        res = await client.post(
            URL,
            json={
                "query": f'mutation {{ likeCourse(id: "{COURSE_ID}") {{ course {{ likes }} }} }}'
            },
        )
        res.raise_for_status()


async def main() -> None:
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=30.0) as client:
        before = await get_likes(client)
        await asyncio.gather(*(send_like(client, sem) for _ in range(BURST)))
        after = await get_likes(client)
        print(f"Before: {before}, sent: {BURST}, after: {after} (diff: +{after - before})")


if __name__ == "__main__":
    asyncio.run(main())