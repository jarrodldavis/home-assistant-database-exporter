"""Custom Upsert class for handling insert or update operations."""

from collections.abc import Sequence
from typing import Any, Self, TypeVar, Union

from sqlalchemy import Insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql._typing import _DMLColumnKeyMapping, _DMLTableArgument
from sqlalchemy.sql.compiler import Compiled
from sqlalchemy.sql.expression import ClauseElement, Executable
from sqlalchemy.sql.roles import DDLConstraintColumnRole
from sqlalchemy.sql.schema import Column as ColumnObject

InsertT = TypeVar("InsertT", bound="Insert")

type Column = Union[ColumnObject[Any], str, DDLConstraintColumnRole]
type ValueArg = Union[_DMLColumnKeyMapping[Any], Sequence[Any]]


class Upsert(Executable, ClauseElement):
    """Custom Upsert class for handling insert or update operations."""

    inherit_cache = False
    _inline = False

    def __init__(self, table: _DMLTableArgument) -> None:
        """Initialize the Upsert statement."""
        self.table = table
        self.values_args: list[ValueArg] | tuple[ValueArg, ...] = []
        self.values_kwargs: dict[str, Any] = {}
        self.conflict_columns: list[Column] | tuple[Column, ...] = []
        self.update_columns: list[str] = []

    def values(
        self,
        *args: _DMLColumnKeyMapping[Any] | Sequence[Any],
        **kwargs: Any,
    ) -> Self:
        """Set the values to be inserted or updated."""
        self.values_args = args
        self.values_kwargs = kwargs
        return self

    def on_conflict(self, *columns: Column) -> Self:
        """Define the columns that can conflict."""
        self.conflict_columns = columns
        return self

    def update(self, *columns: Column) -> Self:
        """Define the columns to update on conflict."""
        self.update_columns = [_extract_column_name(col) for col in columns]
        return self


def upsert(table: _DMLTableArgument) -> Upsert:
    """Construct an Upsert object."""
    return Upsert(table)


def _extract_column_name(col: Column) -> str:
    if isinstance(col, ColumnObject):
        return col.name
    if isinstance(col, DDLConstraintColumnRole):
        raise TypeError("DDLConstraintColumnRole cannot be used directly in upsert().")
    return col


def _visit_upsert(element: Upsert, compiler: Compiled, **kw):
    dialect = compiler.dialect.name
    raise NotImplementedError(f"The dialect '{dialect}' does not support upserts.")


def _visit_upsert_postgresql(el: Upsert, compiler: Compiled, **kw):
    stmt = pg_insert(el.table).values(*el.values_args, **el.values_kwargs)
    cols = el.conflict_columns
    updates = {key: stmt.excluded[key] for key in el.update_columns}
    stmt = stmt.on_conflict_do_update(index_elements=cols, set_=updates)
    return compiler.process(stmt)


def _visit_upsert_mysql(el: Upsert, compiler: Compiled, **kw):
    stmt = mysql_insert(el.table).values(*el.values_args, **el.values_kwargs)
    updates = {key: stmt.inserted[key] for key in el.update_columns}
    stmt = stmt.on_duplicate_key_update(**updates)
    return compiler.process(stmt)


def _visit_upsert_sqlite(el: Upsert, compiler: Compiled, **kw):
    stmt = sqlite_insert(el.table).values(*el.values_args, **el.values_kwargs)
    cols = el.conflict_columns
    updates = {key: stmt.excluded[key] for key in el.update_columns}
    stmt = stmt.on_conflict_do_update(index_elements=cols, set_=updates)
    return compiler.process(stmt)


compiles(Upsert)(_visit_upsert)
compiles(Upsert, "postgresql")(_visit_upsert_postgresql)
compiles(Upsert, "mysql")(_visit_upsert_mysql)
compiles(Upsert, "sqlite")(_visit_upsert_sqlite)
