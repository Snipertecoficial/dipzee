"""Minimal in-memory async Mongo stand-in for unit tests.

Supports only the subset of Motor operations the billing/auth code paths use
(find_one, insert_one, update_one with $set/upsert, find().to_list). No real
Mongo, no network, and — critically for the billing tests — no Stripe. Filters
support plain equality plus the few operators our code passes ($in/$nin/$gte).
"""
import copy


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
            if isinstance(v, dict):
                if "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        return False
                elif "$nin" in v:
                    if doc.get(k) in v["$nin"]:
                        return False
                elif "$gte" in v:
                    dv = doc.get(k)
                    if dv is None or dv < v["$gte"]:
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

    def find(self, flt):
        items = [copy.deepcopy(d) for d in self.docs if self._match(d, flt)]

        class _Cursor:
            def __init__(self, rows):
                self._rows = rows

            async def to_list(self, n):
                return self._rows[: n if n else None]

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
