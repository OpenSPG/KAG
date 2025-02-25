import os

have_sql_lite = True
try:
    import sqlite3
except:
    have_sql_lite = False
import threading
import pickle
import base64


# 初始化数据库
def init_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS kv_store\n                 (key TEXT PRIMARY KEY, value TEXT)"""
    )
    conn.commit()
    conn.close()


class KVStore:
    def __init__(self, db_name=None):
        if db_name is None:
            db_name = "/tmp/llm_cache"
        if not have_sql_lite:
            self.disable = True
            return
        self.db_name = db_name
        if not os.path.exists(db_name):
            init_db(db_name=db_name)
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.c = self.conn.cursor()
        self.rlock = threading.RLock()
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()

        self.disable = False

    def __del__(self):
        if self.disable:
            return
        self.conn.close()

    def set_value(self, key, value):
        if self.disable:
            return
        serialized_data = pickle.dumps(value)
        encoded_data = base64.b64encode(serialized_data).decode("utf-8")
        with self.write_lock:
            with self.rlock:
                self.c.execute(
                    "REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                    (key, encoded_data),
                )
                self.conn.commit()

    def get_value(self, key):
        if self.disable:
            return None
        with self.read_lock:
            with self.rlock:
                self.c.execute("SELECT value FROM kv_store WHERE key=?", (key,))
                result = self.c.fetchone()
                if result:
                    base64_str = result[0]
                    decoded_data = base64.b64decode(base64_str)
                    original_data = pickle.loads(decoded_data)
                    return original_data
                else:
                    return None

    def delete(self ,key):
        if self.disable:
            return None
        with self.write_lock:
            with self.rlock:
                self.c.execute("DELETE FROM kv_store WHERE key=?", (key,))
                self.conn.commit()
                return True