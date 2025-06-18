import cv2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

def preprocess_image(image_path):
    """
    Preprocesses an image for OCR by converting it to grayscale and applying thresholding.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Image not found or unable to read.")
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding for better text segmentation
        processed_image = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Save the processed image temporarily for OCR
        temp_image_path = "temp_processed_image.png"
        cv2.imwrite(temp_image_path, processed_image)
        return temp_image_path
    except Exception as e:
        print(f"Error during image preprocessing: {e}")
        return None

def ocr_image(image_path, lang='chi_sim'):
    """
    Performs OCR on a single image file.
    """
    try:
        preprocessed_image_path = preprocess_image(image_path)
        if not preprocessed_image_path:
            return "Error: Image preprocessing failed."

        text = pytesseract.image_to_string(Image.open(preprocessed_image_path), lang=lang)
        
        # Clean up the temporary processed image
        if os.path.exists(preprocessed_image_path):
            os.remove(preprocessed_image_path)
            
        return text
    except pytesseract.TesseractNotFoundError:
        return "Error: Tesseract is not installed or not in your PATH."
    except Exception as e:
        return f"An error occurred during OCR: {e}"

def ocr_pdf(pdf_path, lang='chi_sim'):
    """
    Performs OCR on a PDF file by converting its pages to images.
    """
    try:
        # Convert PDF to a list of images
        images = convert_from_path(pdf_path)
        full_text = ""
        
        for i, image in enumerate(images):
            # Save each page as a temporary image file
            page_image_path = f"temp_page_{i}.png"
            image.save(page_image_path, "PNG")
            
            # Perform OCR on the page image
            text = ocr_image(page_image_path, lang=lang)
            full_text += f"--- Page {i+1} ---\n{text}\n\n"
            
            # Clean up the temporary page image
            if os.path.exists(page_image_path):
                os.remove(page_image_path)
                
        return full_text
    except Exception as e:
        return f"An error occurred during PDF processing: {e}" 