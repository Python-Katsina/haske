import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from _haske_core import prepare_query, prepare_queries

class Database:
    def __init__(self, url: str, **kwargs):
        self.engine = create_async_engine(url, future=True, echo=False, **kwargs)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self._prepared_queries = {}

    async def fetch_all(self, sql: str, params: dict = None) -> List[Any]:
        """Execute query and return all results"""
        params = params or {}
        query, positional = prepare_query(sql, params)
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result.fetchall()

    async def fetch_one(self, sql: str, params: dict = None) -> Optional[Any]:
        """Execute query and return first result"""
        params = params or {}
        query, positional = prepare_query(sql, params)
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result.first()

    async def execute(self, sql: str, params: dict = None) -> Any:
        """Execute query and return result"""
        params = params or {}
        query, positional = prepare_query(sql, params)
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result

    async def execute_many(self, queries: List[str], params_list: List[dict] = None) -> List[Any]:
        """Execute multiple queries in a transaction"""
        params_list = params_list or [{}] * len(queries)
        
        if len(queries) != len(params_list):
            raise ValueError("Number of queries must match number of parameter sets")
        
        # Prepare all queries
        prepared_queries = []
        for sql, params in zip(queries, params_list):
            query, positional = prepare_query(sql, params)
            prepared_queries.append((query, positional))
        
        # Execute in transaction
        async with self.async_session() as session:
            results = []
            for query, positional in prepared_queries:
                result = await session.execute(text(query), positional)
                results.append(result)
            await session.commit()
            return results

    def prepare(self, sql: str, name: str = None) -> str:
        """Prepare a query for repeated execution"""
        if name is None:
            # Generate name from SQL hash
            import hashlib
            name = f"query_{hashlib.md5(sql.encode()).hexdigest()[:8]}"
        
        self._prepared_queries[name] = sql
        return name

    async def execute_prepared(self, name: str, params: dict = None) -> Any:
        """Execute a prepared query"""
        if name not in self._prepared_queries:
            raise ValueError(f"Prepared query '{name}' not found")
        
        sql = self._prepared_queries[name]
        return await self.execute(sql, params)

    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False

class Model:
    """Base model class for ORM"""
    
    @classmethod
    async def get(cls, id: Any):
        """Get model by ID"""
        # Implementation depends on your ORM setup
        pass
    
    @classmethod
    async def all(cls):
        """Get all models"""
        # Implementation depends on your ORM setup
        pass
    
    async def save(self):
        """Save model to database"""
        # Implementation depends on your ORM setup
        pass
    
    async def delete(self):
        """Delete model from database"""
        # Implementation depends on your ORM setup
        pass