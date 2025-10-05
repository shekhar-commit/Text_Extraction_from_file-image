import cv2
import pytesseract
import numpy as np

# Update this path if your Tesseract is installed elsewhere
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image):
    """
    Advanced preprocessing to improve OCR accuracy:
    - Convert to grayscale
    - Apply bilateral filter to reduce noise while keeping edges sharp
    - Adaptive thresholding for better binarization
    - Morphological operations to clean text regions
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 2)
    kernel = np.ones((1, 1), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return morph

def extract_text_from_image(path):
    image = cv2.imread(path)
    if image is None:
        return ""

    processed = preprocess_image(image)
    text = pytesseract.image_to_string(processed, lang='eng')

    # Clean up extracted text
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned_text = ' '.join(lines)
    return cleaned_text