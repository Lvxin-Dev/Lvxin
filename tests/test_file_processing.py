import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from dotenv import load_dotenv

# It's good practice to add the project root to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load test environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env.test'))

from services.file_processing import analyze_folder, process_pdf, process_image

class TestFileProcessing(unittest.TestCase):

    @patch('services.file_processing.PdfReader')
    @patch('services.file_processing.ocr_pdf')
    def test_process_pdf_direct_extraction(self, mock_ocr_pdf, mock_pdf_reader):
        # Arrange
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is a standard PDF with plenty of text content."
        mock_pdf_reader.return_value.pages = [mock_page]
        
        # Act
        num_pages, text = process_pdf("dummy.pdf")
        
        # Assert
        mock_ocr_pdf.assert_not_called()
        self.assertEqual(text, "This is a standard PDF with plenty of text content.")

    @patch('services.file_processing.PdfReader')
    @patch('services.file_processing.ocr_pdf')
    def test_process_pdf_fallback_to_ocr(self, mock_ocr_pdf, mock_pdf_reader):
        # Arrange
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf_reader.return_value.pages = [mock_page]
        mock_ocr_pdf.return_value = "这是OCR文本"
        
        # Act
        num_pages, text = process_pdf("dummy.pdf")
        
        # Assert
        mock_ocr_pdf.assert_called_once_with("dummy.pdf")
        self.assertEqual(text, "这是OCR文本")

    @patch('services.file_processing.ocr_image')
    def test_process_image(self, mock_ocr_image):
        # Arrange
        mock_ocr_image.return_value = "来自图像的文本"
        
        # Act
        num_pages, text = process_image("dummy.png")
        
        # Assert
        mock_ocr_image.assert_called_once_with("dummy.png")
        self.assertEqual(text, "来自图像的文本")
        self.assertEqual(num_pages, 1)

    @patch('os.walk')
    @patch('services.file_processing.process_pdf')
    @patch('services.file_processing.process_image')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_analyze_folder(self, mock_makedirs, mock_file_open, mock_process_image, mock_process_pdf, mock_os_walk):
        # Arrange
        mock_os_walk.return_value = [
            ('/fake_dir', [], ['test.pdf', 'test.png']),
        ]
        mock_process_pdf.return_value = (1, "pdf text")
        mock_process_image.return_value = (1, "image text")

        # Act
        analyze_folder('/fake_dir')

        # Assert
        # Check if directories are created
        mock_makedirs.assert_called_once_with('/fake_dir/ocr_results', exist_ok=True)
        
        # Check that PDF processing was called and an output file was written
        mock_process_pdf.assert_called_with('/fake_dir/test.pdf')
        mock_file_open.assert_any_call('/fake_dir/ocr_results/test.txt', 'w', encoding='utf-8')
        
        # Check that image processing was called and an output file was written
        mock_process_image.assert_called_with('/fake_dir/test.png')
        mock_file_open.assert_any_call('/fake_dir/ocr_results/test.txt', 'w', encoding='utf-8')

if __name__ == '__main__':
    unittest.main() 