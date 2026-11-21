import os
import unittest

from cervix_sim.store import MemoryStore, MongoStore


class StoreContract:
    def make(self):
        raise NotImplementedError

    def test_insert_get_find_update_upsert_count(self):
        s = self.make()
        a = s.insert("c", {"k": 1, "t": "b"})
        s.insert("c", {"k": 1, "t": "a"})
        s.insert("c", {"k": 2, "t": "c"})
        self.assertEqual(s.get("c", a["_id"])["k"], 1)
        self.assertIsNone(s.get("c", "no-existe"))
        self.assertEqual([d["t"] for d in s.find("c", {"k": 1}, sort="t")], ["a", "b"])
        self.assertTrue(s.update("c", a["_id"], {"k": 9}))
        self.assertEqual(s.get("c", a["_id"])["k"], 9)
        self.assertFalse(s.update("c", "no-existe", {"k": 1}))
        s.upsert("c", {"_id": "fijo", "v": 1})
        s.upsert("c", {"_id": "fijo", "v": 2})
        self.assertEqual(s.get("c", "fijo")["v"], 2)
        self.assertEqual(s.count("c"), 4)

    def test_los_documentos_devueltos_son_copias(self):
        s = self.make()
        d = s.insert("c", {"lista": [1]})
        d["lista"].append(2)
        self.assertEqual(s.get("c", d["_id"])["lista"], [1])


class MemoryStoreTests(StoreContract, unittest.TestCase):
    def make(self):
        return MemoryStore()


@unittest.skipUnless(os.environ.get("MONGODB_URI"), "Define MONGODB_URI para probar MongoStore")
class MongoStoreTests(StoreContract, unittest.TestCase):
    def make(self):
        import uuid
        return MongoStore(os.environ["MONGODB_URI"], "cervix_sim_test_" + uuid.uuid4().hex[:8])


if __name__ == "__main__":
    unittest.main()
