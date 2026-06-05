"""Drop and recreate destinations table with new schema, then seed with import."""
import asyncio
import os

from database import engine, init_db

DB_PATH = os.path.join(os.path.dirname(__file__), "nomad.db")


async def migrate():
    print("Dropping old destinations table...")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: sync_conn.execute(
            __import__("sqlalchemy").text("DROP TABLE IF EXISTS destinations")
        ))
    print("Creating new schema...")
    await init_db()
    print("Migration complete. Run import_cities.py next.")


if __name__ == "__main__":
    asyncio.run(migrate())
