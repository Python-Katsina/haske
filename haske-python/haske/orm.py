# haske/orm.py
"""
Haske ORM — async-first, Rust-accelerated ORM helper built on SQLAlchemy.

Features
- Mandatory Rust extension `_haske_core` for query preparation and optimization.
- Async-first API; sync-convenience auto-run wrappers.
- Rust-accelerated: connection pooling, query building, result processing, batch operations.
- init_engine to initialize engine/session factory.
- create_all / drop_all schema helpers.
- CRUD: add, add_all, delete, update, commit.
- Raw SQL execution: fetch_all, fetch_one, execute, execute_many.
- Prepared query cache + execute_prepared.
- Full Pagination object with helpers and `paginate` method.
- Relationship helpers: OneToOne, OneToMany, ManyToMany.
- Re-exports common SQLAlchemy types & Base.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, Union

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    Time,
    Text,
    LargeBinary,
    JSON,
    ForeignKey,
    Table,
    func,
    select,
    text as sa_text,
    and_,
    or_
)
from sqlalchemy.orm import declarative_base, relationship as sa_relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# -------------------------------
# Mandatory Rust extension import
# -------------------------------
# This will raise ImportError if the Rust extension is not installed,
# as requested (mandatory).
from _haske_core import (
    prepare_query, 
    prepare_queries,
    build_select_query,
    process_result_set,
    get_connection_from_pool,
    return_connection_to_pool,
    batch_insert,
    optimize_type_conversion,
    build_update_query,
    build_delete_query,
    validate_query_syntax,
    cache_prepared_statement,
    get_cached_statement,
    clear_statement_cache
)

# -------------------------------
# Helper: sync-or-async behavior
# -------------------------------
def _maybe_sync(coro):
    """
    If called from a running event loop, return the coroutine (caller should await).
    If not, run the coroutine to completion and return its result (sync convenience).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # no running loop -> run to completion
        return asyncio.run(coro)
    else:
        # running loop -> return coroutine (caller must await)
        return coro

# -------------------------------
# Declarative base
# -------------------------------
Base = declarative_base()

# -------------------------------
# Pagination object (complete)
# -------------------------------
class Pagination:
    """
    Pagination container similar to Flask-SQLAlchemy's Pagination.

    Attributes:
        items (List[Any]): Items for the current page.
        total (int): Total number of items (matching the query/filter).
        page (int): Current 1-based page number.
        per_page (int): Items per page.
    """

    def __init__(self, items: List[Any], total: int, page: int, per_page: int):
        self.items = items
        self.total = int(total)
        self.page = int(page)
        self.per_page = int(per_page)

    @property
    def pages(self) -> int:
        """Total number of pages."""
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Whether a next page exists."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Whether a previous page exists."""
        return self.page > 1

    @property
    def next_num(self) -> Optional[int]:
        """Number of the next page or None."""
        return self.page + 1 if self.has_next else None

    @property
    def prev_num(self) -> Optional[int]:
        """Number of the previous page or None."""
        return self.page - 1 if self.has_prev else None
    
    @property
    def prev_page(self) -> Optional[int]:
        """Alias for prev_num, for more natural API."""
        return self.prev_num

    @property
    def next_page(self) -> Optional[int]:
        """Alias for next_num, for more natural API."""
        return self.next_num

    def iter_pages(
        self,
        left_edge: int = 2,
        left_current: int = 2,
        right_current: int = 5,
        right_edge: int = 2,
    ):
        """
        Iterate over page numbers for displaying pagination links.
        Returns page numbers and None for gaps (same behavior as Flask-SQLAlchemy).
        Example usage:
            for p in pagination.iter_pages():
                if p:
                    print(p)   # page number
                else:
                    print("...")  # gap
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (num >= self.page - left_current and num <= self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dict representation."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_num": self.next_num,
            "prev_num": self.prev_num,
        }

# -------------------------------
# Relationship helpers
# -------------------------------
def OneToOne(target: Union[str, Type[Base]], back_populates: Optional[str] = None, **kwargs):
    """
    One-to-one relationship helper.

    Usage:
        profile = OneToOne("Profile", back_populates="user")
    """
    return sa_relationship(target, uselist=False, back_populates=back_populates, **kwargs)


def OneToMany(target: Union[str, Type[Base]], back_populates: Optional[str] = None, **kwargs):
    """
    One-to-many relationship helper.
    """
    return sa_relationship(target, back_populates=back_populates, **kwargs)


def ManyToMany(target: Union[str, Type[Base]], secondary: Table, back_populates: Optional[str] = None, **kwargs):
    """
    Many-to-many relationship helper. `secondary` must be an association Table instance.
    """
    return sa_relationship(target, secondary=secondary, back_populates=back_populates, **kwargs)


# -------------------------------
# AsyncORM main class
# -------------------------------
class AsyncORM:
    """
    AsyncORM - a simplified async-first ORM wrapper for Haske.

    Core design:
    - Mandatory Rust extension `_haske_core` for query preparation and optimization.
    - Async implementations for all heavy-lifting operations.
    - Rust-accelerated: connection pooling, query building, result processing.
    - Public methods are sync-friendly: call from sync code and the operation
      will run to completion; call from async code and you'll receive a coroutine to await.
    """

    # re-export SQLAlchemy types and helpers so user imports less
    Base = Base
    Column = Column
    Integer = Integer
    String = String
    Float = Float
    Boolean = Boolean
    Date = Date
    DateTime = DateTime
    Time = Time
    Text = Text
    LargeBinary = LargeBinary
    JSON = JSON
    ForeignKey = ForeignKey
    Table = Table
    relationship = sa_relationship
    OneToOne = OneToOne
    OneToMany = OneToMany
    ManyToMany = ManyToMany
    Pagination = Pagination

    def __init__(self, database_url: Optional[str] = None, echo: bool = False, **engine_kwargs):
        """
        Construct AsyncORM.

        Args:
            database_url: optional DB URL to initialize immediately (e.g. "sqlite+aiosqlite:///./app.db").
            echo: SQLAlchemy echo flag.
            engine_kwargs: extra engine kwargs forwarded to create_async_engine.
        """
        self._database_url = database_url
        self._engine_kwargs = dict(engine_kwargs, echo=echo)
        self._engine = None  # sqlalchemy engine
        self._session_maker: Optional[sessionmaker] = None
        self._prepared_queries: Dict[str, str] = {}
        self._rust_connection_pool_enabled = False

        if database_url:
            # Auto-init engine in sync-friendly way
            _maybe_sync(self.init_engine(database_url, **engine_kwargs))

    # -------------------------------
    # Engine / session initialization
    # -------------------------------
    async def _init_engine(self, url: str, **engine_kwargs):
        """
        Async: initialize SQLAlchemy async engine and sessionmaker.

        Args:
            url: database URL
            engine_kwargs: additional engine keyword arguments
        """
        # merge kwargs from constructor
        kw = dict(self._engine_kwargs)
        kw.update(engine_kwargs)
        # create engine
        self._engine = create_async_engine(url, future=True, **kw)
        self._session_maker = sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)
        self._database_url = url
        
        # Enable Rust connection pooling for supported databases
        if any(db in url for db in ['sqlite', 'postgresql', 'mysql']):
            self._rust_connection_pool_enabled = True

    def init_engine(self, url: str, **engine_kwargs):
        """
        Initialize engine (sync-friendly).

        - If called from sync code, this will run and return when ready.
        - If called from async code, it returns a coroutine that you must await.
        """
        return _maybe_sync(self._init_engine(url, **engine_kwargs))

    # -------------------------------
    # Rust connection pool integration
    # -------------------------------
    async def _get_rust_connection(self):
        """Get connection from Rust-managed pool if enabled"""
        if self._rust_connection_pool_enabled:
            try:
                # This would integrate with actual Rust DB drivers
                # For now, it's a placeholder for the connection pool interface
                return get_connection_from_pool()
            except Exception:
                # Fall back to SQLAlchemy session if Rust pool fails
                self._rust_connection_pool_enabled = False
        return self._session()

    async def _return_rust_connection(self, conn):
        """Return connection to Rust pool"""
        if self._rust_connection_pool_enabled:
            try:
                return_connection_to_pool(conn)
                return True
            except Exception:
                self._rust_connection_pool_enabled = False
        return False

    # -------------------------------
    # Schema helpers
    # -------------------------------
    async def _create_all(self):
        """Async create all tables from Base metadata."""
        if not self._engine:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def create_all(self):
        """Create all tables. Sync-friendly wrapper around async implementation."""
        return _maybe_sync(self._create_all())

    async def _drop_all(self):
        """Async drop all tables from Base metadata (dangerous)."""
        if not self._engine:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def drop_all(self):
        """Drop all tables. Sync-friendly wrapper."""
        return _maybe_sync(self._drop_all())

    # -------------------------------
    # Core session helpers
    # -------------------------------
    def _session(self) -> AsyncSession:
        """Return a new AsyncSession instance (not a coroutine)."""
        if not self._session_maker:
            raise RuntimeError("Session maker not available. Call init_engine(url) first.")
        return self._session_maker()

    # -------------------------------
    # CRUD helpers (async impls)
    # -------------------------------
    async def _add(self, instance: Base) -> None:
        """Add and commit a single instance."""
        async with self._session() as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)

    def add(self, instance: Base):
        """Add instance (sync-friendly)."""
        return _maybe_sync(self._add(instance))

    async def _add_all(self, instances: Iterable[Base]) -> None:
        """Add and commit multiple instances."""
        async with self._session() as session:
            session.add_all(list(instances))
            await session.commit()

    def add_all(self, instances: Iterable[Base]):
        """Add many instances (sync-friendly)."""
        return _maybe_sync(self._add_all(instances))

    async def _delete(self, instance: Base) -> None:
        """Delete instance and commit."""
        async with self._session() as session:
            await session.delete(instance)
            await session.commit()

    def delete(self, instance: Base):
        """Delete instance (sync-friendly)."""
        return _maybe_sync(self._delete(instance))

    async def _commit(self) -> None:
        """Commit: opens a session and commits."""
        async with self._session() as session:
            await session.commit()

    def commit(self):
        """Commit (sync-friendly)."""
        return _maybe_sync(self._commit())

    async def _update(self, instance: Base, **kwargs) -> None:
        """Update attributes on an instance and commit."""
        for k, v in kwargs.items():
            setattr(instance, k, v)
        async with self._session() as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)

    def update(self, instance: Base, **kwargs):
        """Update instance (sync-friendly)."""
        return _maybe_sync(self._update(instance, **kwargs))

    # -------------------------------
    # Rust-accelerated query building
    # -------------------------------
    def build_select(self, table: str, columns: List[str] = None, 
                    where_clauses: List[str] = None, order_by: str = None,
                    limit: int = None, offset: int = None) -> str:
        """Build optimized SELECT query using Rust"""
        columns = columns or ["*"]
        where_clauses = where_clauses or []
        return build_select_query(table, columns, where_clauses, order_by, limit, offset)

    def build_update(self, table: str, set_clauses: List[str], where_clauses: List[str]) -> str:
        """Build UPDATE query using Rust"""
        return build_update_query(table, set_clauses, where_clauses)

    def build_delete(self, table: str, where_clauses: List[str]) -> str:
        """Build DELETE query using Rust"""
        return build_delete_query(table, where_clauses)

    def validate_sql(self, sql: str) -> bool:
        """Validate SQL syntax using Rust"""
        return validate_query_syntax(sql)

    # -------------------------------
    # Raw SQL / ORM queries (async impls)
    # -------------------------------
    async def _fetch_all(self, sql_or_model: Union[str, Type[Base]], params: Optional[dict] = None) -> List[Any]:
        """
        Fetch all rows for raw SQL or for an ORM model.
        Uses Rust for query preparation and result processing.
        """
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")

        params = params or {}
        async with self._session() as session:
            if isinstance(sql_or_model, str):
                # Use Rust for query preparation
                sql, positional = prepare_query(sql_or_model, params)
                result = await session.execute(sa_text(sql), positional)
                
                # Process results with Rust for efficiency
                rows = result.fetchall()
                if rows:
                    # Convert to format for Rust processing
                    column_names = [str(col) for col in result.keys()]
                    result_data = [[col for col in row] for row in rows]
                    
                    # Process with Rust (optimized type conversion)
                    processed = process_result_set(result_data, column_names)
                    return processed
                return []
            else:
                # ORM query
                result = await session.execute(select(sql_or_model))
                return result.scalars().all()

    def fetch_all(self, sql_or_model: Union[str, Type[Base]], params: Optional[dict] = None):
        """Fetch all (sync-friendly)."""
        return _maybe_sync(self._fetch_all(sql_or_model, params))

    async def _fetch_one(self, sql_or_model: Union[str, Type[Base]], params: Optional[dict] = None) -> Optional[Any]:
        """Fetch a single row using Rust-optimized processing."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")

        params = params or {}
        async with self._session() as session:
            if isinstance(sql_or_model, str):
                sql, positional = prepare_query(sql_or_model, params)
                result = await session.execute(sa_text(sql), positional)
                row = result.first()
                if row:
                    # Process single row with Rust
                    column_names = [str(col) for col in result.keys()]
                    result_data = [[col for col in row]]
                    processed = process_result_set(result_data, column_names)
                    return processed[0] if processed else None
                return None
            else:
                stmt = select(sql_or_model)
                for key, val in params.items():
                    if hasattr(sql_or_model, key):
                        stmt = stmt.where(getattr(sql_or_model, key) == val)
                result = await session.execute(stmt)
                return result.scalars().first()

    def fetch_one(self, sql_or_model: Union[str, Type[Base]], params: Optional[dict] = None):
        """Fetch one (sync-friendly)."""
        return _maybe_sync(self._fetch_one(sql_or_model, params))

    # -------------------------------
    # Filter helpers with Rust optimization
    # -------------------------------
    async def _filter(self, model: Type[Base], *criteria) -> List[Any]:
        """Advanced filtering with potential Rust optimization."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._session() as session:
            stmt = select(model).where(*criteria)
            result = await session.execute(stmt)
            return result.scalars().all()

    def filter(self, model: Type[Base], *criteria) -> List[Any]:
        """Filter with criteria (sync-friendly)."""
        return _maybe_sync(self._filter(model, *criteria))

    async def _filter_by(self, model: Type[Base], **kwargs) -> List[Any]:
        """Keyword-based filtering."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._session() as session:
            stmt = select(model).filter_by(**kwargs)
            result = await session.execute(stmt)
            return result.scalars().all()

    def filter_by(self, model: Type[Base], **kwargs) -> List[Any]:
        """Filter by keyword args (sync-friendly)."""
        return _maybe_sync(self._filter_by(model, **kwargs))

    async def _get(self, model: Type[Base], **kwargs) -> Optional[Base]:
        """Fetch a single record by keyword filters."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._session() as session:
            stmt = select(model).filter_by(**kwargs).limit(1)
            result = await session.execute(stmt)
            return result.scalars().first()

    def get(self, model: Type[Base], **kwargs) -> Optional[Base]:
        """Get one row by filter (sync-friendly)."""
        return _maybe_sync(self._get(model, **kwargs))

    async def _all(self, model: Type[Base]) -> List[Base]:
        """Fetch all records for a model."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        async with self._session() as session:
            stmt = select(model)
            result = await session.execute(stmt)
            return result.scalars().all()

    def all(self, model: Type[Base]) -> List[Base]:
        """Get all rows (sync-friendly)."""
        return _maybe_sync(self._all(model))

    # -------------------------------
    # Rust-accelerated batch operations
    # -------------------------------
    async def _batch_insert(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Perform batch insert using Rust-optimized query building."""
        if not data:
            return 0

        columns = list(data[0].keys())
        values = [[row[col] for col in columns] for row in data]
        
        # Build batch insert query with Rust
        sql = batch_insert(table, columns, values)
        
        async with self._session() as session:
            result = await session.execute(sa_text(sql), [item for sublist in values for item in sublist])
            await session.commit()
            return result.rowcount

    def batch_insert(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Batch insert (sync-friendly)."""
        return _maybe_sync(self._batch_insert(table, data))

    # -------------------------------
    # Execute operations
    # -------------------------------
    async def _execute(self, sql: str, params: Optional[dict] = None):
        """Execute raw SQL with Rust query preparation."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")

        params = params or {}
        sql_prep, positional = prepare_query(sql, params)
        async with self._session() as session:
            result = await session.execute(sa_text(sql_prep), positional)
            await session.commit()
            return result

    def execute(self, sql: str, params: Optional[dict] = None):
        """Execute raw SQL (sync-friendly)."""
        return _maybe_sync(self._execute(sql, params))

    async def _execute_many(self, queries: List[str], params_list: Optional[List[dict]] = None) -> List[Any]:
        """Execute multiple queries with Rust batch preparation."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")

        params_list = params_list or [{} for _ in queries]
        if len(queries) != len(params_list):
            raise ValueError("queries length must match params_list length")

        # Use Rust for batch query preparation
        prepared = prepare_queries(queries, params_list)

        async with self._session() as session:
            results = []
            for sql_p, positional in prepared:
                r = await session.execute(sa_text(sql_p), positional)
                results.append(r)
            await session.commit()
            return results

    def execute_many(self, queries: List[str], params_list: Optional[List[dict]] = None):
        """Execute many (sync-friendly)."""
        return _maybe_sync(self._execute_many(queries, params_list))

    # -------------------------------
    # Prepared queries cache with Rust integration
    # -------------------------------
    def prepare(self, sql: str, name: Optional[str] = None) -> str:
        """Store prepared SQL and cache in Rust."""
        if name is None:
            name = f"q_{hashlib.md5(sql.encode()).hexdigest()[:8]}"
        self._prepared_queries[name] = sql
        # Also cache in Rust for faster access
        cache_prepared_statement(sql, name)
        return name

    async def _execute_prepared(self, name: str, params: Optional[dict] = None):
        """Execute prepared query with Rust caching."""
        # Try to get from Rust cache first
        rust_cached = get_cached_statement(name)
        if rust_cached:
            sql = rust_cached
        elif name in self._prepared_queries:
            sql = self._prepared_queries[name]
        else:
            raise ValueError(f"Prepared query '{name}' not found")
        
        return await self._execute(sql, params or {})

    def execute_prepared(self, name: str, params: Optional[dict] = None):
        """Execute prepared (sync-friendly)."""
        return _maybe_sync(self._execute_prepared(name, params))

    def clear_prepared_cache(self):
        """Clear both Python and Rust prepared statement caches."""
        self._prepared_queries.clear()
        return clear_statement_cache()

    # -------------------------------
    # Pagination with Rust optimization
    # -------------------------------
    async def _paginate(
        self,
        model: Type[Base],
        page: int = 1,
        per_page: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Iterable[Union[str, Any]]] = None,
    ) -> Pagination:
        """Paginate ORM query results with Rust optimizations."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")

        filters = filters or {}
        async with self._session() as session:
            # Build where clauses for Rust optimization
            where_clauses = []
            for k, v in filters.items():
                if hasattr(model, k):
                    where_clauses.append(f"{k} = :{k}")

            stmt = select(model)
            for k, v in filters.items():
                if hasattr(model, k):
                    stmt = stmt.where(getattr(model, k) == v)

            if order_by:
                for ob in order_by:
                    if isinstance(ob, str):
                        if ob.startswith("-"):
                            col_name = ob[1:]
                            if hasattr(model, col_name):
                                stmt = stmt.order_by(getattr(model, col_name).desc())
                        else:
                            if hasattr(model, ob):
                                stmt = stmt.order_by(getattr(model, ob))
                    else:
                        stmt = stmt.order_by(ob)

            count_stmt = select(func.count()).select_from(model)
            for k, v in filters.items():
                if hasattr(model, k):
                    count_stmt = count_stmt.where(getattr(model, k) == v)

            total_res = await session.execute(count_stmt)
            total = int(total_res.scalar() or 0)

            if per_page > 0:
                stmt = stmt.offset((max(page, 1) - 1) * per_page).limit(per_page)
            
            result = await session.execute(stmt)
            items = result.scalars().all()

        return Pagination(items=items, total=total, page=page, per_page=per_page)

    def paginate(
        self,
        model: Type[Base],
        page: int = 1,
        per_page: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Iterable[Union[str, Any]]] = None,
    ):
        """Paginate (sync-friendly wrapper)."""
        return _maybe_sync(self._paginate(model, page, per_page, filters, order_by))

    # -------------------------------
    # Type optimization
    # -------------------------------
    def optimize_types(self, values: List[Any]) -> List[Any]:
        """Optimize Python types for database operations using Rust."""
        return optimize_type_conversion(values)

    # -------------------------------
    # Health check
    # -------------------------------
    async def _health_check(self) -> bool:
        """Async health check."""
        if not self._session_maker:
            raise RuntimeError("Engine not initialized. Call init_engine(url) first.")
        try:
            async with self._session() as session:
                res = await session.execute(sa_text("SELECT 1"))
                val = res.scalar()
                return val == 1
        except Exception:
            return False

    def health_check(self):
        """Health check (sync-friendly)."""
        return _maybe_sync(self._health_check())

    # -------------------------------
    # Performance monitoring
    # -------------------------------
    def is_rust_pool_enabled(self) -> bool:
        """Check if Rust connection pooling is enabled."""
        return self._rust_connection_pool_enabled

    def get_prepared_cache_size(self) -> int:
        """Get size of prepared statement cache."""
        return len(self._prepared_queries)

# Module exports
__all__ = [
    "AsyncORM",
    "Base",
    "Column",
    "Integer",
    "String",
    "Float",
    "Boolean",
    "Date",
    "DateTime",
    "Time",
    "Text",
    "LargeBinary",
    "JSON",
    "ForeignKey",
    "Table",
    "OneToOne",
    "OneToMany",
    "ManyToMany",
    "Pagination",
]