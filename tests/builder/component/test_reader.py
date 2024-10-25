import unittest
from unittest import TestCase, mock
import os

from kag.builder.component.reader.txt_reader import TXTReader
from kag.builder.component.reader.docx_reader import DocxReader
from kag.builder.component.reader.json_reader import JSONReader
from kag.builder.component.reader.csv_reader import CSVReader
from kag.builder.component.reader.pdf_reader import PDFReader
from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.builder.component.reader.yuque_reader import YuqueReader
from unittest.mock import patch, mock_open, MagicMock
from kag.builder.model.chunk import Chunk, ChunkTypeEnum

dir_path = os.path.dirname(__file__)

class TestTXTReader(TestCase):
    def setUp(self):
        self.reader = TXTReader()

    def test_invoke_with_mock_file(self):
        file_path = "test_file.txt"
        with mock.patch(
            "kag.builder.component.reader.txt_reader.os.path.exists",
            return_value=True,
        ):
            with mock.patch(
                "kag.builder.component.reader.txt_reader.open",
                new_callable=mock.mock_open,
                read_data="file content",
            ):
                chunks = self.reader.invoke(file_path)
                self.assertEqual(len(chunks), 1)
                self.assertIsInstance(chunks[0], Chunk)
                self.assertEqual(chunks[0].id, Chunk.generate_hash_id(file_path))
                self.assertEqual(chunks[0].content, "file content")

    def test_invoke_with_mock_text(self):
        text = "input text"
        chunks = self.reader.invoke(text)
        self.assertEqual(len(chunks), 1)
        self.assertIsInstance(chunks[0], Chunk)
        self.assertEqual(chunks[0].content, text)

    def test_invoke_with_empty_input(self):
        with self.assertRaises(ValueError):
            self.reader.invoke("")

    def test_invoke_with_exist_file(self):
        file_path = os.path.join(dir_path, "../data/test_txt.txt")
        with open(file_path) as f:
            content = f.read()
        chunks = self.reader.invoke(file_path)
        self.assertEqual(len(chunks), 1)
        self.assertIsInstance(chunks[0], Chunk)
        self.assertEqual(chunks[0].id, Chunk.generate_hash_id(file_path))
        self.assertEqual(chunks[0].content, content)


class TestDocxReader(TestCase):
    def setUp(self):
        self.reader = DocxReader()

    def test_input_types(self):
        self.assertEqual(self.reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.reader.output_types, Chunk)

    @patch("kag.builder.component.reader.docx_reader.Document")
    def test_extract_text_from_docx(self, mock_document):
        # Mock the Document object to return a fake paragraph
        mock_paragraph = MagicMock()
        mock_paragraph.para.text = "Test paragraph"
        mock_document.return_value.paragraphs = [mock_paragraph]

        text = self.reader._extract_text_from_docx(mock_document)

        # Assert the expected result
        self.assertEqual(text, "")

    def test_invoke(self):
        # Invoke the method under test
        chunks = self.reader.invoke(os.path.join(os.path.dirname(dir_path),"data/test_docx.docx"))
        # Assert the expected result
        self.assertEqual(len(chunks), 1)
        self.assertIsInstance(chunks[0], Chunk)
        self.assertNotEqual(chunks[0].content, "")
        self.assertEqual(chunks[0].name, "test_docx")

    @patch("kag.builder.component.reader.docx_reader.Document")
    def test_invoke_raises_io_error(self, mock_document):
        # Set up the mock document to raise an OSError
        mock_document.side_effect = OSError("Test error")

        # Invoke the method under test and assert the expected exception
        with self.assertRaises(IOError):
            self.reader.invoke("test_docx.docx")


class TestJSONReader(TestCase):
    def setUp(self):
        self.reader = JSONReader()

    def test_input_types(self):
        self.assertEqual(self.reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.reader.output_types, Chunk)

    @patch(
        "kag.builder.component.reader.json_reader.open",
        new_callable=mock_open,
        read_data='{"key": "value"}',
    )
    def test_read_from_file_success(self, mock_file):
        file_path = "dummy.json"
        content = self.reader._read_from_file(file_path)
        self.assertEqual(content, {"key": "value"})
        mock_file.assert_called_once_with(file_path, "r")

    @patch(
        "kag.builder.component.reader.json_reader.open", new_callable=mock_open
    )
    def test_read_from_file_not_found(self, mock_file):
        mock_file.side_effect = FileNotFoundError
        with self.assertRaises(ValueError):
            self.reader._read_from_file("non_existent.json")

    def test_parse_json_string_success(self):
        json_string = '{"key": "value"}'
        content = self.reader._parse_json_string(json_string)
        self.assertEqual(content, {"key": "value"})

    def test_parse_json_string_failure(self):
        json_string = "invalid json"
        with self.assertRaises(ValueError):
            self.reader._parse_json_string(json_string)

    def test_invoke_with_file(self):
        json_file_path = os.path.join(dir_path, "../data/test_json.json")
        chunks = self.reader.invoke(json_file_path, name_col="title", content_col = "text")

        # Check output
        self.assertEqual(len(chunks), 24)
        self.assertEqual(chunks[0].name, "Thomas C. Sudhof")
        self.assertEqual(
            chunks[0].content,
            "Introduction\nThomas Christian Sudhof (German pronunciation: ['to:mas 'zy:t,ho:f] i; born December 22, 1955), ForMemRS, is a German-American biochemist known for his study of synaptic transmission. Currently, he is a professor in the school of medicine in the department of molecular and cellular physiology, and by courtesy in neurology, and in psychiatry and behavioral sciences at Stanford University.",
        )

    def test_invoke_with_json_string(self):
        json_string = '[{"title": "Test", "text": "Test content"}]'
        chunks = self.reader.invoke(json_string,name_col = "title",content_col = "text")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].name, "Test")
        self.assertEqual(chunks[0].content, "Test content")

    def test_invoke_non_dict_input(self):
        with self.assertRaises(ValueError):
            self.reader.invoke("invalid input")

    def test_invoke_missing_columns(self):
        json_string = '[{"title": "test_json", "text": "Test content"}]'
        chunks = self.reader.invoke(json_string,name_column="title",content_col = "text")

        self.assertEqual(len(chunks), 1)
        self.assertNotEqual(
            chunks[0].name, ""
        ) 
        self.assertEqual(chunks[0].content, "Test content")


class TestCSVReader(unittest.TestCase):
    def setUp(self):
        self.csv_reader = CSVReader()

    def test_input_types(self):
        self.assertEqual(self.csv_reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.csv_reader.output_types, Chunk)

    def test_invoke(self):
        file_path = os.path.join(dir_path, "../data/test_csv.csv")
        chunks = self.csv_reader.invoke(file_path, id_col='id', name_col='title', content_col='text')

        self.assertEqual(len(chunks), 24)


class TestMarkDownReader(unittest.TestCase):
    def setUp(self):
        self.reader = MarkDownReader(cut_depth=1)

    def test_init(self):
        self.assertEqual(self.reader.cut_depth, 1)

    def test_input_types(self):
        self.assertEqual(self.reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.reader.output_types, Chunk)

    def test_invoke(self):
        file_path = os.path.join(dir_path, "../data/test_markdown.md")
        chunks = self.reader.invoke(file_path)
        self.assertTrue(isinstance(chunks[0], Chunk))
        self.assertEqual(chunks[0].name, "test_markdown#0")

    def test_to_text(self):
        pass

    def test_extract_table(self):
        pass


class TestPDFReader(unittest.TestCase):
    def setUp(self):
        self.reader = PDFReader()

    def test_input_types(self):
        self.assertEqual(self.reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.reader.output_types, Chunk)

    def test_process_single_page(self):
        page = "Header\nContent 1\nContent 2\nFooter"
        watermark = "Header"
        expected = ["Content 1", "Content 2"]
        result = self.reader._process_single_page(
            page, watermark, remove_header=True, remove_footnote=True
        )
        self.assertEqual(result, expected)

    def test_invoke(self):

        file_path = os.path.join(dir_path, "../data/test_pdf.pdf")
        chunks = self.reader.invoke(file_path)

        self.assertIsInstance(chunks[0], Chunk)
        self.assertEqual(chunks[0].name, "test_pdf")
        self.assertEqual(chunks[0].type, ChunkTypeEnum.Text)

    def test_invoke_non_pdf(self):
        with self.assertRaises(ValueError):
            self.reader.invoke("../data/test_txt.txt")


class TestYuqueReader(unittest.TestCase):
    def setUp(self):
        self.token = "1yPz1LbE20FmXvemCDVwjlSHpAp18qtEu7wcjCfv"
        self.reader = YuqueReader(self.token)

    def test_init(self):
        self.assertEqual(self.reader.token, self.token)
        self.assertIsInstance(self.reader.markdown_reader, MarkDownReader)

    def test_input_types(self):
        self.assertEqual(self.reader.input_types, str)

    def test_output_types(self):
        self.assertEqual(self.reader.output_types, Chunk)

    @patch("kag.builder.component.reader.yuque_reader.requests.get")
    def test_get_yuque_api_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"id": "test_id", "title": "test_title", "body": "test_content"}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        data = YuqueReader.get_yuque_api_data(self.token, "test_url")
        self.assertEqual(data["id"], "test_id")
        self.assertEqual(data["title"], "test_title")
        self.assertEqual(data["body"], "test_content")

    def test_invoke(self):
        # Assuming 'solve_content' method of MarkDownReader returns a list of Chunk objects
        # Here we mock the behavior to return a dummy Chunk object

        chunks = self.reader.invoke(
            "https://yuque-api.antfin-inc.com/api/v2/repos/ob46m2/it70c2/docs/bnp80qitsy5vqoa5"
        )
        self.assertIsInstance(chunks, list)
        self.assertIsInstance(chunks[0], Chunk)
        self.assertEqual(chunks[0].content[:6], "1、建设目标")
        self.assertEqual(chunks[0].type, ChunkTypeEnum.Text)



if __name__ == "__main__":
    unittest.main()
