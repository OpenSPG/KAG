import unittest
import os
from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock

from kag.builder.component.splitter.length_splitter import LengthSplitter
from kag.builder.component.splitter.outline_splitter import OutlineSplitter
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.model.chunk import Chunk, ChunkTypeEnum
from kag.common.env import init_kag_config

init_kag_config(os.path.join(os.path.dirname(__file__),"test_config.cfg"))


class TestLengthSplitter(TestCase):

    def setUp(self):
        self.splitter = LengthSplitter()

    def test_split_sentence(self):
        sentence = "Hello World!This is a test. You and df aasd? sadq a asd !"
        self.splitter.split_sentence(sentence)
        self.assertEqual(len(self.splitter.split_sentence(sentence)), 4)
    
    @patch("kag.builder.component.splitter.length_splitter.LengthSplitter.slide_window_chunk")    
    def test_invoke(self, mock_slide_window_chunk):
        mock_slide_window_chunk.return_value = [Chunk(id = 1,name = "test",content = "Hello World!This is a test. You and df aasd? sadq a asd !")]
        res = self.splitter.invoke("test")
        self.assertEqual(len(res), 1)
        
class TestOutlineSplitter(TestCase):
    
    def setUp(self):
        self.length_splitter = LengthSplitter(split_length=8000)
        self.outline_splitter = OutlineSplitter()
        self.docx_reader = DocxReader()

    def test_invoke(self):
        docx_path = os.path.join(os.path.dirname(__file__),"../data/test_docx.docx")
        chunk = self.docx_reader.invoke(docx_path)
        chunks = self.length_splitter.invoke(chunk)
        chunks = self.outline_splitter.invoke(chunks)
        print(chunks)
    
        

if __name__ == "__main__":
    unittest.main()