"""Minimal in-memory async Mongo stand-in for unit tests.

Supports only the subset of Motor operations the billing/auth code paths use
(find_one, insert_one, update_one with $set/upsert, find().to_list). No real
Mongo, no network, and — critically for the billing tests — no Stripe. Filters
support plain equality plus the few operators our code passes ($in/$nin/$gte).
"""
import copy
import re


class _Result:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _match(doc, flt):
        for k, v in flt.items():
            if k == "$or":
                if not any(FakeCollection._match(doc, sub) for sub in v):
                    return False
            elif isinstance(v, dict):
                if "$regex" in v:
                    if not re.search(v["$regex"], str(doc.get(k) or "")):
                        return False
                elif "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        return False
                elif "$nin" in v:
                    if doc.get(k) in v["$nin"]:
                        return False
                elif "$ne" in v:
                    if doc.get(k) == v["$ne"]:
                        return False
                elif "$gte" in v:
                    dv = doc.get(k)
                    if dv is None or dv < v["$gte"]:
                        return False
                elif "$lt" in v:
                    dv = doc.get(k)
                    if dv is None or dv >= v["$lt"]:
                        return False
                else:
                    if doc.get(k) != v:
                        return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, flt, projection=None):
        for d in self.docs:
            if self._match(d, flt):
                return copy.deepcopy(d)
        return None

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))
        return _Result(inserted_id=doc.get("id"))

    async def insert_many(self, docs):
        ids = []
        for d in docs:
            self.docs.append(copy.deepcopy(d))
            ids.append(d.get("id"))
        return _Result(inserted_ids=ids)

    async def delete_many(self, flt):
        keep = [d for d in self.docs if not self._match(d, flt)]
        removed = len(self.docs) - len(keep)
        self.docs = keep
        return _Result(deleted_count=removed)

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update, upsert=False):
        setv = update.get("$set", {})
        for d in self.docs:
            if self._match(d, flt):
                d.update(copy.deepcopy(setv))
                return _Result(matched_count=1, modified_count=1, upserted_id=None)
        if upsert:
            newdoc = {k: v for k, v in flt.items() if not isinstance(v, dict)}
            newdoc.update(copy.deepcopy(setv))
            self.docs.append(newdoc)
            return _Result(matched_count=0, modified_count=0, upserted_id=1)
        return _Result(matched_count=0, modified_count=0, upserted_id=None)

    async def distinct(self, field, flt=None):
        flt = flt or {}
        seen = []
        for d in self.docs:
            if self._match(d, flt):
                val = d.get(field)
                if val not in seen:
                    seen.append(val)
        return seen

    async def bulk_write(self, ops, ordered=True):
        """Support UpdateOne(filter, {'$set': ...}, upsert=True) — the shape
        security_master._upsert uses."""
        upserted = modified = 0
        for op in ops:
            flt = getattr(op, "_filter", None)
            doc = getattr(op, "_doc", None)
            upsert = getattr(op, "_upsert", False)
            if flt is None:  # pymongo UpdateOne stores as _doc/_filter in newer versions
                continue
            setv = (doc or {}).get("$set", {})
            matched = False
            for d in self.docs:
                if self._match(d, flt):
                    d.update(copy.deepcopy(setv))
                    modified += 1
                    matched = True
                    break
            if not matched and upsert:
                newdoc = {k: v for k, v in flt.items() if not isinstance(v, dict)}
                newdoc.update(copy.deepcopy(setv))
                self.docs.append(newdoc)
                upserted += 1
        return _Result(upserted_count=upserted, modified_count=modified)

    def find(self, flt, projection=None):
        items = [copy.deepcopy(d) for d in self.docs if self._match(d, flt)]
        if projection:
            excluded = [k for k, val in projection.items() if val == 0]
            if excluded:
                for d in items:
                    for k in excluded:
                        d.pop(k, None)

        class _Cursor:
            def __init__(self, rows):
                self._rows = rows

            def sort(self, key, direction=1):
                self._rows.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=direction < 0)
                return self

            def skip(self, n):
                self._rows = self._rows[n:] if n else self._rows
                return self

            def limit(self, n):
                self._rows = self._rows[:n] if n else self._rows
                return self

            async def to_list(self, n):
                return self._rows[: n if n else None]

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._rows):
                    raise StopAsyncIteration
                row = self._rows[self._i]
                self._i += 1
                return row

        return _Cursor(items)


class FakeDB:
    def __init__(self):
        self._colls = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._colls.setdefault(name, FakeCollection())

    def __getitem__(self, name):
        return self._colls.setdefault(name, FakeCollection())
