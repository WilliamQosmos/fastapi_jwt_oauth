import uuid
from typing import Annotated

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

convention = {
    "ix": "ix__%(column_0_label)s",
    "uq": "uq__%(table_name)s__%(column_0_name)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}
meta = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = meta


intpk = Annotated[int, mapped_column(primary_key=True, index=True, autoincrement=True)]
uuidpk = Annotated[UUID, mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)]
str100 = Annotated[str, 100]
