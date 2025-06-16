import os
import re
from PyPDF2 import PdfReader
from docx import Document
import textract

def count_chinese_chars(text: str) -> int:
    """Count Chinese characters in a string."""
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def process_pdf(file_path: str) -> tuple[int, int]:
    """Process a PDF file to count pages and Chinese characters."""
    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        chinese_chars = count_chinese_chars(text)
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        return 0, 0

def process_docx(file_path: str) -> tuple[int, int]:
    """Process a DOCX file to count pages and Chinese characters."""
    try:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        chinese_chars = count_chinese_chars(text)
        # DOCX doesn't have a direct page count, so we estimate by section breaks or just count as 1
        num_pages = 1
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing DOCX {file_path}: {e}")
        return 0, 0

def process_doc(file_path: str) -> tuple[int, int]:
    """Process a DOC file to count pages and Chinese characters."""
    try:
        text = textract.process(file_path).decode('utf-8')
        chinese_chars = count_chinese_chars(text)
        num_pages = 1  # No direct way to get page count from DOC, so we estimate as 1
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing DOC {file_path}: {e}")
        return 0, 0

def analyze_folder(folder_path: str) -> tuple[int, int, int, int]:
    """Analyze all supported files in a folder for stats."""
    total_files = 0
    total_pages = 0
    total_chinese_chars = 0

    for root, _, files in os.walk(folder_path):
        for file in files:
            ext = file.lower().split('.')[-1]
            file_path = os.path.join(root, file)
            pages, chars = 0, 0
            
            if ext == 'pdf':
                pages, chars = process_pdf(file_path)
            elif ext == 'docx':
                pages, chars = process_docx(file_path)
            elif ext == 'doc':
                pages, chars = process_doc(file_path)
            
            if pages > 0:
                total_files += 1
                total_pages += pages
                total_chinese_chars += chars

    total_cost = total_chinese_chars * 3
    
    print(f"Total files: {total_files}")
    print(f"Total pages: {total_pages}")
    print(f"Total Chinese characters: {total_chinese_chars}")
    print(f"Total cost: {total_cost}")
    
    return total_files, total_pages, total_chinese_chars, total_cost 