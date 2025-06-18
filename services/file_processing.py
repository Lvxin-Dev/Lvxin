import os
import re
from PyPDF2 import PdfReader
from docx import Document
import textract
from services.ocr_service import ocr_pdf, ocr_image

def count_chinese_chars(text: str) -> int:
    """Count Chinese characters in a string."""
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def process_pdf(file_path: str) -> tuple[int, str]:
    """Process a PDF file to extract text. Falls back to OCR if needed."""
    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        text = ""
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text
        
        # If text is minimal, it might be a scanned PDF, so we use OCR.
        if len(text.strip()) < 100: # Threshold to trigger OCR
            print(f"Falling back to OCR for {file_path}")
            text = ocr_pdf(file_path)
            
        return num_pages, text
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        # Fallback to OCR on any exception with PyPDF2
        print(f"Falling back to OCR for {file_path}")
        text = ocr_pdf(file_path)
        return 0, text # Page count is unknown here

def process_docx(file_path: str) -> tuple[int, str]:
    """Process a DOCX file to extract text."""
    try:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        # DOCX doesn't have a direct page count, so we estimate by section breaks or just count as 1
        num_pages = 1
        return num_pages, text
    except Exception as e:
        print(f"Error processing DOCX {file_path}: {e}")
        return 0, ""

def process_doc(file_path: str) -> tuple[int, str]:
    """Process a DOC file to extract text."""
    try:
        text = textract.process(file_path).decode('utf-8')
        num_pages = 1  # No direct way to get page count from DOC, so we estimate as 1
        return num_pages, text
    except Exception as e:
        print(f"Error processing DOC {file_path}: {e}")
        return 0, ""

def process_image(file_path: str) -> tuple[int, str]:
    """Process an image file using OCR to extract text."""
    try:
        text = ocr_image(file_path)
        return 1, text # An image is considered a single page
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")
        return 0, ""

def analyze_folder(folder_path: str) -> tuple[int, int, int, int]:
    """Analyze all supported files in a folder for stats."""
    total_files = 0
    total_pages = 0
    total_chinese_chars = 0
    output_dir = os.path.join(folder_path, "ocr_results")
    os.makedirs(output_dir, exist_ok=True)

    for root, _, files in os.walk(folder_path):
        # Avoid processing files in the output directory
        if root == output_dir:
            continue

        for file in files:
            ext = file.lower().split('.')[-1]
            file_path = os.path.join(root, file)
            pages, text = 0, ""
            
            if ext == 'pdf':
                pages, text = process_pdf(file_path)
            elif ext == 'docx':
                pages, text = process_docx(file_path)
            elif ext == 'doc':
                pages, text = process_doc(file_path)
            elif ext in ['png', 'jpg', 'jpeg', 'tiff']:
                pages, text = process_image(file_path)

            if pages > 0:
                total_files += 1
                total_pages += pages
                chars = count_chinese_chars(text)
                total_chinese_chars += chars
                
                # Save extracted text to a file
                output_filename = os.path.join(output_dir, f"{os.path.splitext(file)[0]}.txt")
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(text)

    total_cost = total_chinese_chars * 3
    
    print(f"Total files: {total_files}")
    print(f"Total pages: {total_pages}")
    print(f"Total Chinese characters: {total_chinese_chars}")
    print(f"Total cost: {total_cost}")
    
    return total_files, total_pages, total_chinese_chars, total_cost 