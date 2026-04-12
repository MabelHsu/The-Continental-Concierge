"""
Seed Embeddings Generator
===========================
Generates embeddings for all lore_chunks using Vertex AI
text-embedding-005 and updates AlloyDB.

Run this after schema + seed data are loaded.

Usage:
    python db/seed_embeddings.py --project PROJECT_ID --region REGION
"""

import argparse
import asyncio

import asyncpg
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel


async def generate_and_store_embeddings(
    project_id: str,
    region: str,
    db_host: str,
    db_name: str = "continental",
    db_user: str = "continental_app",
    db_password: str = "",
):
    """Generate embeddings for all lore chunks and scene memories."""

    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=region)
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")

    # Connect to AlloyDB
    conn = await asyncpg.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
    )

    try:
        # ── Lore Chunks ──────────────────────────────────────
        print("Generating embeddings for lore_chunks...")

        rows = await conn.fetch(
            "SELECT id, title, content FROM lore_chunks WHERE embedding IS NULL"
        )
        print(f"  Found {len(rows)} chunks without embeddings.")

        for i, row in enumerate(rows):
            text = f"{row['title']}: {row['content']}"

            # Generate embedding via Vertex AI
            embeddings = model.get_embeddings([text])
            embedding_values = embeddings[0].values  # 768-dim vector

            # Store in AlloyDB
            await conn.execute(
                "UPDATE lore_chunks SET embedding = $1::vector(768) WHERE id = $2",
                str(embedding_values),
                row["id"],
            )

            print(f"  [{i + 1}/{len(rows)}] Embedded: {row['title']}")

        # ── Conversation Summaries ────────────────────────────
        print("\nGenerating embeddings for conversation_summaries...")

        rows = await conn.fetch(
            "SELECT id, summary FROM conversation_summaries WHERE embedding IS NULL"
        )
        print(f"  Found {len(rows)} summaries without embeddings.")

        for i, row in enumerate(rows):
            embeddings = model.get_embeddings([row["summary"]])
            await conn.execute(
                "UPDATE conversation_summaries SET embedding = $1::vector(768) WHERE id = $2",
                str(embeddings[0].values),
                row["id"],
            )
            print(f"  [{i + 1}/{len(rows)}] Embedded summary {row['id']}")

        # ── Scene Memories ────────────────────────────────────
        print("\nGenerating embeddings for scene_memories...")

        rows = await conn.fetch("SELECT id, scene_text FROM scene_memories WHERE embedding IS NULL")
        print(f"  Found {len(rows)} scenes without embeddings.")

        for i, row in enumerate(rows):
            # Truncate long scenes for embedding
            text = row["scene_text"][:2000]
            embeddings = model.get_embeddings([text])
            await conn.execute(
                "UPDATE scene_memories SET embedding = $1::vector(768) WHERE id = $2",
                str(embeddings[0].values),
                row["id"],
            )
            print(f"  [{i + 1}/{len(rows)}] Embedded scene {row['id']}")

        print("\nAll embeddings generated successfully.")

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for Continental lore")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--db-host", required=True, help="AlloyDB host IP")
    parser.add_argument("--db-password", required=True, help="DB password")

    args = parser.parse_args()

    asyncio.run(
        generate_and_store_embeddings(
            project_id=args.project,
            region=args.region,
            db_host=args.db_host,
            db_password=args.db_password,
        )
    )
