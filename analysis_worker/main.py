import asyncio
import os

import aiofiles
import asyncpg
import orjson
from loguru import logger
from redis.asyncio import Redis

REDIS_URL = os.environ["QUEUE_URL"]
QUEUE_NAME = os.environ["QUEUE_NAME"]
DB_URL = os.environ["DB_URL"]

# Create DB Connection here


async def handle_msg(conn: asyncpg.Connection, request_id: str, raw_image: str) -> None:
    input_file = f"{request_id}-input.jpg"
    output_file = f"./{request_id}-output.txt"

    # Write to input file
    async with aiofiles.open(input_file, mode="w") as f:
        await f.write(raw_image)

    # Call engine
    process = await asyncio.create_subprocess_exec(
        "./overflowengine", "--input", "images/healthy.jpg", "--output", output_file
    )
    stdout, stderr = await process.communicate()

    logger.debug(f"Stdout is {stdout}")
    logger.debug(f"Stderr is {stderr}")

    status_code = process.returncode

    result_status: str
    if status_code != 0:
        # error
        result_status = "failed"
        logger.error(
            f"Encountered an issue when running overflowengine '{status_code}'"
        )
    else:
        async with aiofiles.open(output_file, mode="r") as f:
            result_status = (await f.read()).strip()

    print(result_status)

    query = rf"UPDATE analysis_job SET result = '{result_status}', updated_at = CURRENT_TIMESTAMP WHERE id = '{request_id}';"

    await conn.execute(query)


tasks = set()


async def main():
    logger.info("Starting analysis worker...")
    redis = await Redis.from_url(REDIS_URL)
    conn = await asyncpg.connect(DB_URL)

    try:
        while True:
            msg = await redis.lpop(QUEUE_NAME)
            if msg is None:
                await asyncio.sleep(1)
                continue

            data = orjson.loads(msg)

            request_id = data["request_id"]
            raw_image = data["raw_image"]

            tasks.add(asyncio.create_task(handle_msg(conn, request_id, raw_image)))

    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
