import unittest
import os
from kag.common.vectorizer import Vectorizer


class TestOllamaVectorizer(unittest.TestCase):
    def setUp(self):
        self.file_path = os.path.dirname(__file__)

    def test_ollama_vectorizer(self):
        config_path = os.path.join(self.file_path, "config/ollama_vectorizer.yaml")
        vectorizer = Vectorizer.from_config(config_path)
        res = vectorizer.vectorize("你好")
        print(res)
        assert res is not None


if __name__ == "__main__":
    unittest.main()
