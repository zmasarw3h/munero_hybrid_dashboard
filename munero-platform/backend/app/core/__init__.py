"""Core module initialization"""
from .config import settings, DB_TABLES, SCHEMA_FOREIGN_KEYS, TERMINOLOGY_MAPPING, SQL_GENERATION_RULES

__all__ = [
    "settings",
    "DB_TABLES",
    "SCHEMA_FOREIGN_KEYS",
    "TERMINOLOGY_MAPPING",
    "SQL_GENERATION_RULES"
]
