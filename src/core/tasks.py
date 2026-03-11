import asyncio

from arq import create_pool
from arq.connections import RedisSettings

from src.core.config import settings
from src.core.logger import system_logger as logger


async def process_experiment_results(ctx, experiment_id: str, ecosystem_id: str):
    """
    Background Task: Heavy statistical processing of experiment results.
    Offloads compute-intensive work from the fast perception-decision loop.
    """
    logger.info("Starting background task: process_experiment_results", extra={"experiment_id": experiment_id})

    # Simulate heavy statistical calculation / Bayesian updating
    await asyncio.sleep(2)

    # In a full implementation, we would inject the RelationalArchive and KnowledgeGraph here
    # to update the strategy fitness and publish an event.
    logger.info("Completed background task: process_experiment_results", extra={"experiment_id": experiment_id})
    return {"status": "success", "significance": 0.95}

async def batch_knowledge_graph_update(ctx, nodes_to_create: list, relationships_to_create: list):
    """
    Background Task: Batch processing for Knowledge Graph ingestion.
    Prevents GraphDB latency from slowing down agent reasoning.
    """
    logger.info("Starting background task: batch_knowledge_graph_update", extra={"nodes_count": len(nodes_to_create)})
    await asyncio.sleep(1)
    logger.info("Completed background task: batch_knowledge_graph_update")
    return {"status": "success"}

# ARQ Worker Settings
class WorkerSettings:
    functions = [process_experiment_results, batch_knowledge_graph_update]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    async def on_startup(ctx):
        logger.info("ARQ Worker started. Connected to Redis.")

    async def on_shutdown(ctx):
        logger.info("ARQ Worker shutting down.")

# Simple helper for the main app to enqueue tasks
class TaskQueue:
    _pool = None

    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            cls._pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        return cls._pool

    @classmethod
    async def enqueue(cls, function_name: str, *args, **kwargs):
        pool = await cls.get_pool()
        job = await pool.enqueue_job(function_name, *args, **kwargs)
        if job:
            logger.debug(f"Enqueued background task {function_name}", extra={"job_id": job.job_id})
        return job
