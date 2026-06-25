import json

from django.db import models


class PgVectorField(models.Field):
    """
    Store embeddings as pgvector in PostgreSQL and JSON text in local SQLite.

    The Postgres `vector` type is provided by the database extension, so this
    field avoids requiring the Python pgvector package just to import models.
    """

    description = "PostgreSQL pgvector column with a SQLite text fallback"

    def __init__(self, *args, dimensions=384, **kwargs):
        self.dimensions = dimensions
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return f"vector({self.dimensions})"
        return "text"

    def from_db_value(self, value, expression, connection):
        return self._to_python(value)

    def to_python(self, value):
        return self._to_python(value)

    def get_prep_value(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        return "[" + ",".join(self._format_number(item) for item in value) + "]"

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["dimensions"] = self.dimensions
        return name, path, args, kwargs

    def _to_python(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, (list, tuple)):
            return [float(item) for item in value]
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            try:
                return [float(item) for item in json.loads(cleaned)]
            except (TypeError, ValueError, json.JSONDecodeError):
                cleaned = cleaned.strip("[]{}()")
                if not cleaned:
                    return None
                return [
                    float(item.strip()) for item in cleaned.split(",") if item.strip()
                ]
        return value

    def _format_number(self, value):
        number = float(value)
        return f"{number:.8f}".rstrip("0").rstrip(".") or "0"
