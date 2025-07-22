"""
Database optimization service for improved performance
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of database queries for optimization"""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class QueryPerformance:
    """Query performance metrics"""

    query_hash: str
    query_type: QueryType
    execution_time: float
    timestamp: datetime
    table_name: Optional[str] = None
    rows_affected: Optional[int] = None
    cache_hit: bool = False


@dataclass
class IndexRecommendation:
    """Database index recommendation"""

    table_name: str
    columns: List[str]
    index_type: str  # "btree", "hash", "composite"
    estimated_improvement: float
    query_patterns: List[str]
    priority: int  # 1-5, 5 being highest priority


class DatabaseOptimizer:
    """Database optimization and monitoring service"""

    def __init__(self, db_path: str = "data/resume_optimization.db"):
        self.db_path = db_path
        self.query_log: List[QueryPerformance] = []
        self.connection_pool_size = 10
        self.connection_pool: List[aiosqlite.Connection] = []
        self.pool_lock = asyncio.Lock()
        self.performance_threshold = 0.1  # 100ms
        self.slow_queries: List[QueryPerformance] = []

        # Index tracking
        self.existing_indexes: Dict[str, List[str]] = {}
        self.index_recommendations: List[IndexRecommendation] = []

        # Query optimization patterns
        self.optimization_patterns = {
            "resume_data": {
                "common_filters": ["user_id", "created_at", "status"],
                "common_joins": ["user_id"],
                "recommended_indexes": [
                    ("user_id", "btree"),
                    ("created_at", "btree"),
                    ("user_id, created_at", "composite"),
                ],
            },
            "conversations": {
                "common_filters": ["session_id", "user_id", "timestamp"],
                "common_joins": ["session_id", "user_id"],
                "recommended_indexes": [
                    ("session_id", "btree"),
                    ("user_id", "btree"),
                    ("timestamp", "btree"),
                    ("session_id, timestamp", "composite"),
                ],
            },
            "job_analyses": {
                "common_filters": ["job_hash", "user_id", "created_at"],
                "common_joins": ["user_id"],
                "recommended_indexes": [
                    ("job_hash", "hash"),
                    ("user_id", "btree"),
                    ("created_at", "btree"),
                ],
            },
            "resume_versions": {
                "common_filters": ["resume_id", "user_id", "version_number"],
                "common_joins": ["resume_id", "user_id"],
                "recommended_indexes": [
                    ("resume_id", "btree"),
                    ("user_id", "btree"),
                    ("resume_id, version_number", "composite"),
                ],
            },
        }

    async def initialize(self):
        """Initialize the database optimizer"""
        await self._create_connection_pool()
        await self._analyze_existing_schema()
        await self._create_performance_tables()
        logger.info("Database optimizer initialized")

    async def shutdown(self):
        """Shutdown the database optimizer"""
        await self._close_connection_pool()
        logger.info("Database optimizer shutdown")

    async def _create_connection_pool(self):
        """Create a pool of database connections"""
        async with self.pool_lock:
            for _ in range(self.connection_pool_size):
                conn = await aiosqlite.connect(self.db_path)
                # Enable WAL mode for better concurrency
                await conn.execute("PRAGMA journal_mode=WAL")
                # Enable foreign key constraints
                await conn.execute("PRAGMA foreign_keys=ON")
                # Optimize SQLite settings
                await conn.execute("PRAGMA cache_size=10000")  # 10MB cache
                await conn.execute("PRAGMA temp_store=MEMORY")
                await conn.execute("PRAGMA synchronous=NORMAL")
                self.connection_pool.append(conn)

    async def _close_connection_pool(self):
        """Close all connections in the pool"""
        async with self.pool_lock:
            for conn in self.connection_pool:
                await conn.close()
            self.connection_pool.clear()

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        async with self.pool_lock:
            if self.connection_pool:
                conn = self.connection_pool.pop()
            else:
                # Create new connection if pool is empty
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA foreign_keys=ON")

        try:
            yield conn
        finally:
            async with self.pool_lock:
                if len(self.connection_pool) < self.connection_pool_size:
                    self.connection_pool.append(conn)
                else:
                    await conn.close()

    async def _create_performance_tables(self):
        """Create tables for performance monitoring"""
        async with self.get_connection() as conn:
            # Query performance log table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    table_name TEXT,
                    rows_affected INTEGER,
                    cache_hit BOOLEAN DEFAULT FALSE
                )
            """
            )

            # Index usage statistics
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS index_usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    index_name TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    last_used DATETIME,
                    avg_improvement REAL DEFAULT 0.0
                )
            """
            )

            await conn.commit()

    async def _analyze_existing_schema(self):
        """Analyze existing database schema"""
        async with self.get_connection() as conn:
            # Get all tables
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )
            tables = await cursor.fetchall()

            # Get indexes for each table
            for (table_name,) in tables:
                cursor = await conn.execute(f"PRAGMA index_list({table_name})")
                indexes = await cursor.fetchall()

                table_indexes = []
                for index_info in indexes:
                    index_name = index_info[1]
                    cursor = await conn.execute(f"PRAGMA index_info({index_name})")
                    columns = await cursor.fetchall()
                    column_names = [col[2] for col in columns]
                    table_indexes.append(f"{index_name}: {', '.join(column_names)}")

                self.existing_indexes[table_name] = table_indexes

    async def log_query_performance(
        self,
        query: str,
        execution_time: float,
        query_type: QueryType,
        table_name: Optional[str] = None,
        rows_affected: Optional[int] = None,
        cache_hit: bool = False,
    ):
        """Log query performance for analysis"""

        import hashlib

        query_hash = hashlib.md5(query.encode()).hexdigest()

        performance = QueryPerformance(
            query_hash=query_hash,
            query_type=query_type,
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
            table_name=table_name,
            rows_affected=rows_affected,
            cache_hit=cache_hit,
        )

        self.query_log.append(performance)

        # Track slow queries
        if execution_time > self.performance_threshold:
            self.slow_queries.append(performance)
            logger.warning(
                f"Slow query detected: {execution_time:.3f}s - {query[:100]}..."
            )

        # Store in database for persistent analysis
        await self._store_performance_data(performance)

    async def _store_performance_data(self, performance: QueryPerformance):
        """Store performance data in database"""
        async with self.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO query_performance 
                (query_hash, query_type, execution_time, timestamp, table_name, rows_affected, cache_hit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    performance.query_hash,
                    performance.query_type.value,
                    performance.execution_time,
                    performance.timestamp,
                    performance.table_name,
                    performance.rows_affected,
                    performance.cache_hit,
                ),
            )
            await conn.commit()

    async def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities"""

        if not self.query_log:
            return {"message": "No query data available for analysis"}

        # Analyze by table
        table_stats = {}
        query_type_stats = {}

        for perf in self.query_log:
            # Table statistics
            if perf.table_name:
                if perf.table_name not in table_stats:
                    table_stats[perf.table_name] = {
                        "query_count": 0,
                        "avg_execution_time": 0,
                        "total_time": 0,
                        "slow_queries": 0,
                    }

                stats = table_stats[perf.table_name]
                stats["query_count"] += 1
                stats["total_time"] += perf.execution_time
                stats["avg_execution_time"] = stats["total_time"] / stats["query_count"]

                if perf.execution_time > self.performance_threshold:
                    stats["slow_queries"] += 1

            # Query type statistics
            query_type = perf.query_type.value
            if query_type not in query_type_stats:
                query_type_stats[query_type] = {
                    "count": 0,
                    "avg_time": 0,
                    "total_time": 0,
                }

            stats = query_type_stats[query_type]
            stats["count"] += 1
            stats["total_time"] += perf.execution_time
            stats["avg_time"] = stats["total_time"] / stats["count"]

        return {
            "total_queries": len(self.query_log),
            "slow_queries": len(self.slow_queries),
            "table_statistics": table_stats,
            "query_type_statistics": query_type_stats,
            "performance_threshold": self.performance_threshold,
        }

    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Generate index recommendations based on query patterns"""

        recommendations = []

        # Analyze slow queries for index opportunities
        table_query_patterns = {}

        for perf in self.slow_queries:
            if perf.table_name:
                if perf.table_name not in table_query_patterns:
                    table_query_patterns[perf.table_name] = []
                table_query_patterns[perf.table_name].append(perf)

        # Generate recommendations for each table
        for table_name, patterns in table_query_patterns.items():
            if table_name in self.optimization_patterns:
                table_config = self.optimization_patterns[table_name]

                for columns, index_type in table_config["recommended_indexes"]:
                    # Check if index already exists
                    existing = self.existing_indexes.get(table_name, [])
                    index_exists = any(columns in idx for idx in existing)

                    if not index_exists:
                        # Calculate estimated improvement
                        relevant_queries = [
                            p for p in patterns if p.table_name == table_name
                        ]
                        avg_time = (
                            sum(p.execution_time for p in relevant_queries)
                            / len(relevant_queries)
                            if relevant_queries
                            else 0
                        )
                        estimated_improvement = min(
                            avg_time * 0.7, 0.9
                        )  # Assume up to 70% improvement

                        # Determine priority based on query frequency and performance impact
                        query_count = len(relevant_queries)
                        priority = min(
                            5, max(1, int(query_count / 10) + int(avg_time * 10))
                        )

                        recommendation = IndexRecommendation(
                            table_name=table_name,
                            columns=columns.split(", "),
                            index_type=index_type,
                            estimated_improvement=estimated_improvement,
                            query_patterns=[
                                f"Slow {p.query_type.value} queries"
                                for p in relevant_queries[:3]
                            ],
                            priority=priority,
                        )

                        recommendations.append(recommendation)

        # Sort by priority
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        self.index_recommendations = recommendations

        return recommendations

    async def apply_index_recommendations(
        self, recommendations: List[IndexRecommendation] = None
    ) -> Dict[str, Any]:
        """Apply index recommendations to the database"""

        if recommendations is None:
            recommendations = self.index_recommendations

        if not recommendations:
            return {"message": "No recommendations to apply"}

        applied = []
        failed = []

        async with self.get_connection() as conn:
            for rec in recommendations:
                try:
                    # Generate index name
                    index_name = f"idx_{rec.table_name}_{'_'.join(rec.columns)}"

                    # Create index SQL
                    columns_str = ", ".join(rec.columns)
                    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {rec.table_name} ({columns_str})"

                    # Execute index creation
                    start_time = datetime.utcnow()
                    await conn.execute(sql)
                    await conn.commit()
                    end_time = datetime.utcnow()

                    creation_time = (end_time - start_time).total_seconds()

                    applied.append(
                        {
                            "table": rec.table_name,
                            "columns": rec.columns,
                            "index_name": index_name,
                            "creation_time": creation_time,
                            "estimated_improvement": rec.estimated_improvement,
                        }
                    )

                    logger.info(
                        f"Created index {index_name} on {rec.table_name}({columns_str})"
                    )

                except Exception as e:
                    failed.append(
                        {
                            "table": rec.table_name,
                            "columns": rec.columns,
                            "error": str(e),
                        }
                    )
                    logger.error(f"Failed to create index on {rec.table_name}: {e}")

        return {
            "applied": applied,
            "failed": failed,
            "total_recommendations": len(recommendations),
        }

    async def optimize_database(self) -> Dict[str, Any]:
        """Perform comprehensive database optimization"""

        optimization_results = {
            "vacuum_result": None,
            "analyze_result": None,
            "index_recommendations": None,
            "applied_indexes": None,
            "performance_summary": None,
        }

        async with self.get_connection() as conn:
            # VACUUM to reclaim space and defragment
            try:
                start_time = datetime.utcnow()
                await conn.execute("VACUUM")
                end_time = datetime.utcnow()

                optimization_results["vacuum_result"] = {
                    "success": True,
                    "duration": (end_time - start_time).total_seconds(),
                }
                logger.info("Database VACUUM completed")

            except Exception as e:
                optimization_results["vacuum_result"] = {
                    "success": False,
                    "error": str(e),
                }
                logger.error(f"VACUUM failed: {e}")

            # ANALYZE to update query planner statistics
            try:
                start_time = datetime.utcnow()
                await conn.execute("ANALYZE")
                end_time = datetime.utcnow()

                optimization_results["analyze_result"] = {
                    "success": True,
                    "duration": (end_time - start_time).total_seconds(),
                }
                logger.info("Database ANALYZE completed")

            except Exception as e:
                optimization_results["analyze_result"] = {
                    "success": False,
                    "error": str(e),
                }
                logger.error(f"ANALYZE failed: {e}")

        # Generate and apply index recommendations
        try:
            recommendations = await self.generate_index_recommendations()
            optimization_results["index_recommendations"] = len(recommendations)

            if recommendations:
                applied_result = await self.apply_index_recommendations(recommendations)
                optimization_results["applied_indexes"] = applied_result

        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            optimization_results["applied_indexes"] = {"error": str(e)}

        # Get performance summary
        try:
            optimization_results["performance_summary"] = (
                await self.analyze_query_patterns()
            )
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            optimization_results["performance_summary"] = {"error": str(e)}

        return optimization_results

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""

        stats = {}

        async with self.get_connection() as conn:
            # Database size
            cursor = await conn.execute("PRAGMA page_count")
            page_count = (await cursor.fetchone())[0]
            cursor = await conn.execute("PRAGMA page_size")
            page_size = (await cursor.fetchone())[0]

            stats["database_size"] = {
                "pages": page_count,
                "page_size": page_size,
                "total_size_bytes": page_count * page_size,
                "total_size_mb": (page_count * page_size) / (1024 * 1024),
            }

            # Table statistics
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )
            tables = await cursor.fetchall()

            table_stats = {}
            for (table_name,) in tables:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = (await cursor.fetchone())[0]
                table_stats[table_name] = {"row_count": row_count}

            stats["table_statistics"] = table_stats

            # Index statistics
            stats["index_statistics"] = self.existing_indexes

            # Performance statistics
            stats["performance_statistics"] = {
                "total_queries_logged": len(self.query_log),
                "slow_queries": len(self.slow_queries),
                "performance_threshold": self.performance_threshold,
                "connection_pool_size": len(self.connection_pool),
            }

        return stats

    async def cleanup_old_performance_data(self, days: int = 30) -> int:
        """Clean up old performance data"""

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM query_performance 
                WHERE timestamp < ?
            """,
                (cutoff_date,),
            )

            deleted_count = cursor.rowcount
            await conn.commit()

            logger.info(f"Cleaned up {deleted_count} old performance records")
            return deleted_count


# Query execution wrapper with performance monitoring
class OptimizedQuery:
    """Wrapper for database queries with performance monitoring"""

    def __init__(self, optimizer: DatabaseOptimizer):
        self.optimizer = optimizer

    async def execute(
        self,
        query: str,
        params: Tuple = None,
        query_type: QueryType = QueryType.SELECT,
        table_name: Optional[str] = None,
    ) -> Any:
        """Execute query with performance monitoring"""

        start_time = datetime.utcnow()

        async with self.optimizer.get_connection() as conn:
            try:
                if params:
                    cursor = await conn.execute(query, params)
                else:
                    cursor = await conn.execute(query)

                if query_type == QueryType.SELECT:
                    result = await cursor.fetchall()
                    rows_affected = len(result)
                else:
                    result = cursor.rowcount
                    rows_affected = cursor.rowcount
                    await conn.commit()

                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()

                # Log performance
                await self.optimizer.log_query_performance(
                    query=query,
                    execution_time=execution_time,
                    query_type=query_type,
                    table_name=table_name,
                    rows_affected=rows_affected,
                )

                return result

            except Exception as e:
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()

                # Log failed query
                await self.optimizer.log_query_performance(
                    query=query,
                    execution_time=execution_time,
                    query_type=query_type,
                    table_name=table_name,
                    rows_affected=0,
                )

                logger.error(f"Query execution failed: {e}")
                raise


# Global database optimizer instance
_db_optimizer: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get the global database optimizer instance"""
    global _db_optimizer
    if _db_optimizer is None:
        _db_optimizer = DatabaseOptimizer()
    return _db_optimizer


async def initialize_database_optimizer(db_path: str = "data/resume_optimization.db"):
    """Initialize the global database optimizer"""
    global _db_optimizer
    _db_optimizer = DatabaseOptimizer(db_path)
    await _db_optimizer.initialize()


async def shutdown_database_optimizer():
    """Shutdown the global database optimizer"""
    global _db_optimizer
    if _db_optimizer:
        await _db_optimizer.shutdown()
        _db_optimizer = None
