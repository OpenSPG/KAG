# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import base64
import unittest

from tabulate import tabulate
from kag.common.vectorizer.vectorizer import Vectorizer


class TestDifferentVectorizers(unittest.TestCase):
    """Different vectorizers unit test"""

    def _get_bge_zh_vectorizer(self):
        path = base64.b64decode("fi8uY2FjaGUvdmVjdG9yaXplci9CQUFJL2JnZS1iYXNlLXpoLXYxLjU=").decode("utf-8")
        host = base64.b64decode("YWxwcy1jb21tb24ub3NzLWNuLWhhbmd6aG91LXptZi5hbGl5dW5jcy5jb20=").decode("utf-8")
        model = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9CQUFJLWJnZS1iYXNlLXpoLXYxLjUudGFyLmd6").decode("utf-8")
        config = {
            "vectorizer": "kag.common.vectorizer.LocalVectorizer",
            "path": path,
            "url": "https://%s/%s" % (host, model),
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer

    def _get_contriever_vectorizer(self):
        path = base64.b64decode("fi8uY2FjaGUvdmVjdG9yaXplci9mYWNlYm9vay9jb250cmlldmVy").decode("utf-8")
        host = base64.b64decode("YWxwcy1jb21tb24ub3NzLWNuLWhhbmd6aG91LXptZi5hbGl5dW5jcy5jb20=").decode("utf-8")
        model = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9mYWNlYm9vay1jb250cmlldmVyLnRhci5neg==").decode("utf-8")
        config = {
            "vectorizer": "kag.common.vectorizer.ContrieverVectorizer",
            "path": path,
            "url": "https://%s/%s" % (host, model),
            "normalize": True,
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer

    def _get_openai_vectorizer(self):
        config = {
            "vectorizer": "kag.common.vectorizer.OpenAIVectorizer",
            "nn_name": "text-embedding-ada-002",
            "openai_api_key": "EMPTY",
            "openai_api_base": "http://127.0.0.1:38080/v1"
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer

    def _get_bge_en_vectorizer(self):
        path = base64.b64decode("fi8uY2FjaGUvdmVjdG9yaXplci9CQUFJL2JnZS1iYXNlLWVuLXYxLjU=").decode("utf-8")
        host = base64.b64decode("YWxwcy1jb21tb24ub3NzLWNuLWhhbmd6aG91LXptZi5hbGl5dW5jcy5jb20=").decode("utf-8")
        model = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9CQUFJLWJnZS1iYXNlLWVuLXYxLjUudGFyLmd6").decode("utf-8")
        config = {
            "vectorizer": "kag.common.vectorizer.LocalVectorizer",
            "path": path,
            "url": "https://%s/%s" % (host, model),
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer

    def _get_bge_m3_vectorizer(self):
        path = base64.b64decode("fi8uY2FjaGUvdmVjdG9yaXplci9CQUFJL2JnZS1tMw==").decode("utf-8")
        host = base64.b64decode("YWxwcy1jb21tb24ub3NzLWNuLWhhbmd6aG91LXptZi5hbGl5dW5jcy5jb20=").decode("utf-8")
        model = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9CQUFJLWJnZS1tMy50YXIuZ3o=").decode("utf-8")
        config = {
            "vectorizer": "kag.common.vectorizer.LocalBGEM3Vectorizer",
            "path": path,
            "url": "https://%s/%s" % (host, model),
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer

    def _get_vectorizers(self):
        vectorizers = (
            ("bge_zh", self._get_bge_zh_vectorizer()),
            ("contriever", self._get_contriever_vectorizer()),
            ("openai", self._get_openai_vectorizer()),
            ("bge_en", self._get_bge_en_vectorizer()),
            ("bge_m3", self._get_bge_m3_vectorizer()),
        )
        return vectorizers

    def setUp(self):
        self.vectorizers = self._get_vectorizers()

    def tearDown(self):
        pass

    def testVectorize(self):
        inputs = [
            "George Washington",
            "Father of the United States",
            "President Washington",
            "The American George",
            "Washington the Great",
        ]
        inputs2 = [
            "诸葛亮",
            "卧龙先生",
            "诸葛丞相",
            "武乡侯",
            "孔明先生",
        ]
        headers = ("#",) + tuple(name for name, _vectorizer in self.vectorizers)
        columns = []
        for _name, vectorizer in self.vectorizers:
            column = []
            vecs = vectorizer.vectorize(inputs)
            for vec in vecs:
                similarity = sum(x * y for x, y in zip(vecs[0], vec))
                column.append(similarity)
            columns.append(column)
        data = []
        for i in range(len(columns[0])):
            row = [i]
            for column in columns:
                row.append(column[i])
            data.append(row)
        string = tabulate(data, headers=headers)
        print(string)


if __name__ == "__main__":
    unittest.main()
