import asyncio
import json
import os

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def main():
    client = redis.from_url(REDIS_URL, decode_responses=True)

    while True:
        item = await client.blpop("reminder:queue", timeout=5)
        if not item:
            continue

        payload = json.loads(item[1])
        print("notification job:", payload, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
