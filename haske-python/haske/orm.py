# haske/orm.py
"""
Object-Relational Mapping (ORM) utilities for Haske framework.

This module provides database abstraction with async support and
Rust-accelerated query preparation for improved performance.
"""

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Import Rust query preparation functions if available
try:
    from _haske_core import prepare_query, prepare_queries
    HAS_RUST_ORM = True
except ImportError:
    HAS_RUST_ORM = False

class Database:
    """
    Database connection and query management.
    
    Provides async database operations with connection pooling and
    Rust-accelerated query preparation.
    
    Attributes:
        engine: SQLAlchemy async engine
        async_session: Async session factory
        _prepared_queries: Cache of prepared queries
    """
    
    def __init__(self, url: str, **kwargs):
        """
        Initialize database connection.
        
        Args:
            url: Database connection URL
            **kwargs: Additional SQLAlchemy engine options
        """
        self.engine = create_async_engine(url, future=True, echo=False, **kwargs)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self._prepared_queries = {}

    async def fetch_all(self, sql: str, params: dict = None) -> List[Any]:
        """
        Execute query and return all results.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            List[Any]: List of result rows
            
        Example:
            >>> users = await db.fetch_all("SELECT * FROM users WHERE active = :active", {"active": True})
        """
        params = params or {}
        
        if HAS_RUST_ORM:
            query, positional = prepare_query(sql, params)
        else:
            # Fallback Python implementation
            query = sql
            positional = params
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result.fetchall()

    async def fetch_one(self, sql: str, params: dict = None) -> Optional[Any]:
        """
        Execute query and return first result.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            Optional[Any]: First result row or None
            
        Example:
            >>> user = await db.fetch_one("SELECT * FROM users WHERE id = :id", {"id": user_id})
        """
        params = params or {}
        
        if HAS_RUST_ORM:
            query, positional = prepare_query(sql, params)
        else:
            # Fallback Python implementation
            query = sql
            positional = params
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result.first()

    async def execute(self, sql: str, params: dict = None) -> Any:
        """
        Execute query and return result.
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            Any: Execution result
            
        Example:
            >>> result = await db.execute("INSERT INTO users (name) VALUES (:name)", {"name": "John"})
        """
        params = params or {}
        
        if HAS_RUST_ORM:
            query, positional = prepare_query(sql, params)
        else:
            # Fallback Python implementation
            query = sql
            positional = params
        
        async with self.async_session() as session:
            result = await session.execute(text(query), positional)
            return result

    async def execute_many(self, queries: List[str], params_list: List[dict] = None) -> List[Any]:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of SQL query strings
            params_list: List of parameter dictionaries
            
        Returns:
            List[Any]: List of execution results
            
        Raises:
            ValueError: If number of queries doesn't match number of parameter sets
            
        Example:
            >>> results = await db.execute_many(
            ...     ["INSERT INTO users (name) VALUES (:name)", "INSERT INTO logs (message) VALUES (:message)"],
            ...     [{"name": "John"}, {"message": "User created"}]
            ... )
        """
        params_list = params_list or [{}] * len(queries)
        
        if len(queries) != len(params_list):
            raise ValueError("Number of queries must match number of parameter sets")
        
        # Prepare all queries
        prepared_queries = []
        for sql, params in zip(queries, params_list):
            if HAS_RUST_ORM:
                query, positional = prepare_query(sql, params)
            else:
                # Fallback Python implementation
                query = sql
                positional = params
            
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
        """
        Prepare a query for repeated execution.
        
        Args:
            sql: SQL query string
            name: Optional name for the prepared query
            
        Returns:
            str: Query name for execution
            
        Example:
            >>> query_name = db.prepare("SELECT * FROM users WHERE id = :id")
            >>> user = await db.execute_prepared(query_name, {"id": user_id})
        """
        if name is None:
            # Generate name from SQL hash
            import hashlib
            name = f"query_{hashlib.md5(sql.encode()).hexdigest()[:8]}"
        
        self._prepared_queries[name] = sql
        return name

    async def execute_prepared(self, name: str, params: dict = None) -> Any:
        """
        Execute a prepared query.
        
        Args:
            name: Prepared query name
            params: Query parameters
            
        Returns:
            Any: Execution result
            
        Raises:
            ValueError: If prepared query not found
            
        Example:
            >>> user = await db.execute_prepared("get_user_by_id", {"id": user_id})
        """
        if name not in self._prepared_queries:
            raise ValueError(f"Prepared query '{name}' not found")
        
        sql = self._prepared_queries[name]
        return await self.execute(sql, params)

    async def health_check(self) -> bool:
        """
        Check database connection health.
        
        Returns:
            bool: True if connection is healthy, False otherwise
            
        Example:
            >>> healthy = await db.health_check()
        """
        try:
            async with self.async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False

class Model:
    """
    Base model class for ORM.
    
    Provides common database operations for model classes.
    Subclasses should define table structure using SQLAlchemy.
    """
    
    @classmethod
    async def get(cls, id: Any):
        """
        Get model by ID.
        
        Args:
            id: Model identifier
            
        Returns:
            Optional[Model]: Model instance or None if not found
        """
        # Implementation depends on your ORM setup
        pass
    
    @classmethod
    async def all(cls):
        """
        Get all models.
        
        Returns:
            List[Model]: List of all model instances
        """
        # Implementation depends on your ORM setup
        pass
    
    async def save(self):
        """
        Save model to database.
        
        Returns:
            None: Saves the model instance
        """
        # Implementation depends on your ORM setup
        pass
    
    async def delete(self):
        """
        Delete model from database.
        
        Returns:
            None: Deletes the model instance
        """
        # Implementation depends on your ORM setup
        pass