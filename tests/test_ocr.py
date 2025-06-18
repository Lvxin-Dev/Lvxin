import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.ocr_service import ocr_pdf

def test_ocr_on_pdf(pdf_path):
    """
    Tests OCR on a PDF file using the existing ocr_service.

    Args:
        pdf_path (str): The path to the PDF file.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: The file '{pdf_path}' does not exist.")
        return

    print(f"Starting OCR process for: {pdf_path}")
    
    extracted_text = ocr_pdf(pdf_path, lang='chi_sim')
    
    print("\n--- OCR Process Finished ---")
    if extracted_text:
        print("Extracted Text:")
        print(extracted_text)
    else:
        print("No text was extracted. Please check the file and OCR service.")

if __name__ == '__main__':
    # --- Instructions for the user ---
    # 1. Make sure you have Tesseract-OCR and Poppler installed as per README.md.
    # 2. Replace 'path/to/your/pdf_with_images.pdf' with the actual path to your PDF file.
    
    pdf_file_path = '/home/momo/Downloads/Lvxin/png2pdf.pdf'
    
    test_ocr_on_pdf(pdf_file_path)
