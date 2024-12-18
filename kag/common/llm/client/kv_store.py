import os
import sqlite3
import threading

# 初始化数据库
def init_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS kv_store\n                 (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()

class KVStore:
    def __init__(self, db_name):
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
        self.conn.close()

    def set_value(self, key, value):
        if self.disable:
            return
        with self.write_lock:
            with self.rlock:
                self.c.execute("REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, value))
                self.conn.commit()

    def get_value(self, key):
        if self.disable:
            return None
        with self.read_lock:
            with self.rlock:
                self.c.execute("SELECT value FROM kv_store WHERE key=?", (key,))
                result = self.c.fetchone()
                if result:
                    return result[0]
                else:
                    return None

