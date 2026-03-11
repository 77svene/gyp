import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
import asyncpg
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class RelationalArchive:
    """
    Persistent Knowledge Substrate Integration using PostgreSQL.
    Maintains the Strategy Genome Library and Experiment Archive with full provenance.
    """
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("POSTGRES_URL", "postgresql://user:password@localhost:5432/autonomous_marketing")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)
            logger.info("Connected to Relational Archive (PostgreSQL)")
            await self._initialize_schema()
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def close(self):
        """Close connection pool to PostgreSQL."""
        if self.pool:
            await self.pool.close()

    async def _initialize_schema(self):
        """Create necessary tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # Table for the Strategy Genome Library
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    strategy_id UUID PRIMARY KEY,
                    ecosystem_id VARCHAR(255) NOT NULL,
                    genome JSONB NOT NULL,
                    fitness_score FLOAT DEFAULT 0.0,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    parent_ids UUID[] DEFAULT ARRAY[]::UUID[]
                )
            """)

            # Table for the Experiment Archive
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id UUID PRIMARY KEY,
                    strategy_id UUID REFERENCES strategies(strategy_id),
                    ecosystem_id VARCHAR(255) NOT NULL,
                    design_parameters JSONB NOT NULL,
                    observed_outcomes JSONB,
                    statistical_significance FLOAT,
                    status VARCHAR(50) DEFAULT 'running',
                    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    end_time TIMESTAMP WITH TIME ZONE,
                    conclusion TEXT
                )
            """)

            # Table for System Audit Logs (Provenance tracking)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    event_type VARCHAR(255) NOT NULL,
                    payload JSONB NOT NULL,
                    source_agent_id VARCHAR(255)
                )
            """)

            logger.info("Database schema initialized.")

    async def save_strategy(self, strategy_id: str, ecosystem_id: str, genome: Dict[str, Any], fitness_score: float = 0.0, parent_ids: List[str] = None):
        """Persist a strategy genome."""
        parents = parent_ids or []
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO strategies (strategy_id, ecosystem_id, genome, fitness_score, parent_ids)
                VALUES ($1::uuid, $2, $3::jsonb, $4, $5::uuid[])
                ON CONFLICT (strategy_id) DO UPDATE SET
                    genome = EXCLUDED.genome,
                    fitness_score = EXCLUDED.fitness_score,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """, strategy_id, ecosystem_id, json.dumps(genome), fitness_score, parents)

    async def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a strategy genome by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM strategies WHERE strategy_id = $1::uuid
            """, strategy_id)
            if row:
                return dict(row)
            return None

    async def log_experiment_result(self, experiment_id: str, strategy_id: str, ecosystem_id: str, parameters: Dict[str, Any], outcomes: Dict[str, Any], significance: float):
        """Log the result of an experiment into the archive."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO experiments (experiment_id, strategy_id, ecosystem_id, design_parameters, observed_outcomes, statistical_significance, status, end_time)
                VALUES ($1::uuid, $2::uuid, $3, $4::jsonb, $5::jsonb, $6, 'completed', NOW())
                ON CONFLICT (experiment_id) DO UPDATE SET
                    observed_outcomes = EXCLUDED.observed_outcomes,
                    statistical_significance = EXCLUDED.statistical_significance,
                    status = EXCLUDED.status,
                    end_time = EXCLUDED.end_time
            """, experiment_id, strategy_id, ecosystem_id, json.dumps(parameters), json.dumps(outcomes), significance)

    async def record_audit_event(self, event_type: str, payload: Dict[str, Any], source_agent_id: str = None):
        """Record a system-level audit event for provenance and governance."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_logs (event_type, payload, source_agent_id)
                VALUES ($1, $2::jsonb, $3)
            """, event_type, json.dumps(payload), source_agent_id)
