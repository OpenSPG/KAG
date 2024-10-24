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

from kag.common.vectorizer.vectorizer import Vectorizer


class TestVectorizer(unittest.TestCase):
    """Vectorizer unit test"""

    def _get_local_vectorizer(self):
        path = base64.b64decode("fi8uY2FjaGUvdmVjdG9yaXplci9CQUFJL2JnZS1iYXNlLXpoLXYxLjU=").decode("utf-8")
        host = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9CQUFJLWJnZS1iYXNlLXpoLXYxLjUudGFyLmd6").decode("utf-8")
        model = base64.b64decode("YWxwcy9odWFpZG9uZy54aGQvRG9jdW1lbnRzL21vZGVscy9CQUFJLWJnZS1iYXNlLXpoLXYxLjUudGFyLmd6").decode("utf-8")
        config = {
            "vectorizer": "kag.common.vectorizer.LocalVectorizer",
            "path": path,
            "url": "https://%s/inference/%s" % (host, model),
        }
        vectorizer = Vectorizer.from_config(config)
        return vectorizer


    def _get_vectorizer(self, *, local=False):
        if local:
            vectorizer = self._get_local_vectorizer()
        else:
            vectorizer = self._get_maya_vectorizer()
        return vectorizer

    def setUp(self):
        self.vectorizer = self._get_vectorizer(local=False)

    def tearDown(self):
        pass

    def testVectorize(self):
        texts = ["How old are you?", "What is your age?"]
        vecs = self.vectorizer.vectorize(texts)
        similarity = sum(x * y for x, y in zip(*vecs))
        print("similarity: %g" % similarity)
        self.assertTrue(similarity >= 0.75)


if __name__ == "__main__":
    unittest.main()
