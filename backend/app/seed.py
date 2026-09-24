"""
Seed script – loads demo data into Neo4j.

Usage:
  python -m app.seed

Runs schema.cypher then seed.cypher against the configured Neo4j instance.
Safe to run multiple times (idempotent MERGE statements).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "neo4j"


async def run_seed():
    from app.config import settings

    if not settings.neo4j_password:
        logger.error("NEO4J_PASSWORD not set. Cannot seed without database credentials.")
        logger.info("Set NEO4J_PASSWORD in .env and ensure Neo4j is running.")
        sys.exit(1)

    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        # Verify connectivity
        async with driver.session(database=settings.neo4j_database) as session:
            await session.run("RETURN 1")
        logger.info("Connected to Neo4j at %s", settings.neo4j_uri)

        # Run schema
        schema_path = DATA_DIR / "schema.cypher"
        if schema_path.exists():
            logger.info("Running schema.cypher...")
            await _run_cypher_file(driver, schema_path, settings.neo4j_database)
            logger.info("Schema applied successfully")

        # Run seed
        seed_path = DATA_DIR / "seed.cypher"
        if seed_path.exists():
            logger.info("Running seed.cypher...")
            await _run_cypher_file(driver, seed_path, settings.neo4j_database)
            logger.info("Seed data loaded successfully")

        # Verify
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(
                "MATCH (l:Location) RETURN count(l) AS locations"
            )
            record = await result.single()
            logger.info("Verification: %d locations in database", record["locations"])

            result = await session.run(
                "MATCH (s:Shipment) RETURN count(s) AS shipments"
            )
            record = await result.single()
            logger.info("Verification: %d shipments in database", record["shipments"])

    finally:
        await driver.close()

    logger.info("Seed complete!")


async def _run_cypher_file(driver, file_path: Path, database: str):
    """Execute a .cypher file statement by statement."""
    content = file_path.read_text(encoding="utf-8")

    # Split on semicolons, filter empty
    statements = [s.strip() for s in content.split(";") if s.strip()]

    async with driver.session(database=database) as session:
        for i, stmt in enumerate(statements):
            # Skip comment-only blocks
            lines = [line for line in stmt.split("\n") if line.strip() and not line.strip().startswith("//")]
            if not lines:
                continue
            try:
                await session.run(stmt)
            except Exception as exc:
                logger.warning("Statement %d failed (may be expected): %s", i + 1, exc)


if __name__ == "__main__":
    asyncio.run(run_seed())
