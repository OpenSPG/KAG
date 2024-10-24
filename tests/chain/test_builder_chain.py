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

import unittest

from kag.builder.default_chain import BuilderChain


class TestBuilderClient(unittest.TestCase):
    """BuilderClient unit test stubs"""

    def setUp(self):
        self.chain = BuilderChain()

    def tearDown(self):
        pass

    def testExecute(self):
        """Test execute"""


if __name__ == "__main__":
    unittest.main()
