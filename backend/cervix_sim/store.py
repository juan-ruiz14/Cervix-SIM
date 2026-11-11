"""Almacén de datos NoSQL (decisión D6).

Colecciones (entidades del modelo): usuarios, sesiones, decisiones, sugerencias,
metricas, sus y eventos. Los casos viven en el banco versionado (data/cases.json).

- MemoryStore: solo desarrollo y pruebas (los datos se pierden al reiniciar).
- MongoStore: MongoDB Atlas o local (requiere `pip install pymongo`).
Firebase Firestore queda como alternativa por implementar con la misma interfaz.
"""
from __future__ import annotations

import copy
import threading
import uuid
from typing import Dict, List, Optional


class Store:
    """Interfaz mínima. Todos los documentos tienen un campo `_id` (str)."""

    kind = "abstract"

    def insert(self, coll: str, doc: dict) -> dict: raise NotImplementedError
    def get(self, coll: str, _id: str) -> Optional[dict]: raise NotImplementedError
    def find(self, coll: str, filters: Optional[dict] = None, sort: Optional[str] = None) -> List[dict]: raise NotImplementedError
    def update(self, coll: str, _id: str, fields: dict) -> bool: raise NotImplementedError
    def upsert(self, coll: str, doc: dict) -> dict: raise NotImplementedError
    def count(self, coll: str) -> int: raise NotImplementedError


def _sorted(docs: List[dict], sort: Optional[str]) -> List[dict]:
    return sorted(docs, key=lambda d: d.get(sort, "")) if sort else docs


class MemoryStore(Store):
    kind = "memory"

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, dict]] = {}
        self._lock = threading.RLock()

    def insert(self, coll, doc):
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", uuid.uuid4().hex)
        with self._lock:
            bucket = self._data.setdefault(coll, {})
            if doc["_id"] in bucket:
                raise ValueError(f"_id duplicado en {coll}")
            bucket[doc["_id"]] = doc
        return copy.deepcopy(doc)

    def get(self, coll, _id):
        with self._lock:
            doc = self._data.get(coll, {}).get(_id)
            return copy.deepcopy(doc) if doc else None

    def find(self, coll, filters=None, sort=None):
        filters = filters or {}
        with self._lock:
            docs = [copy.deepcopy(d) for d in self._data.get(coll, {}).values()
                    if all(d.get(k) == v for k, v in filters.items())]
        return _sorted(docs, sort)

    def update(self, coll, _id, fields):
        with self._lock:
            doc = self._data.get(coll, {}).get(_id)
            if not doc:
                return False
            doc.update(copy.deepcopy(fields))
            return True

    def upsert(self, coll, doc):
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", uuid.uuid4().hex)
        with self._lock:
            self._data.setdefault(coll, {})[doc["_id"]] = doc
        return copy.deepcopy(doc)

    def count(self, coll):
        with self._lock:
            return len(self._data.get(coll, {}))


class MongoStore(Store):
    kind = "mongodb"

    def __init__(self, uri: str, db_name: str) -> None:
        try:
            from pymongo import MongoClient  # import diferido: dependencia opcional
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Para usar MongoDB instala: pip install -r requirements-mongo.txt") from exc
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._db = self._client[db_name]

    def insert(self, coll, doc):
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", uuid.uuid4().hex)
        self._db[coll].insert_one(doc)
        return doc

    def get(self, coll, _id):
        return self._db[coll].find_one({"_id": _id})

    def find(self, coll, filters=None, sort=None):
        return _sorted(list(self._db[coll].find(filters or {})), sort)

    def update(self, coll, _id, fields):
        return self._db[coll].update_one({"_id": _id}, {"$set": fields}).matched_count == 1

    def upsert(self, coll, doc):
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", uuid.uuid4().hex)
        self._db[coll].replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return doc

    def count(self, coll):
        return self._db[coll].count_documents({})


def build_store(settings) -> Store:
    if settings.mongodb_uri:
        return MongoStore(settings.mongodb_uri, settings.mongodb_db)
    return MemoryStore()
