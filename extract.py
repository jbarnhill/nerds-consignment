import os
from PIL import Image
import pytesseract

# Configuration
SOURCE_DIR = "albany_silver"
OUTPUT_FILE = "extracted_text.txt"

# Ensure Tesseract is installed and accessible
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Update path if needed

def extract_text_from_image(image_path):
    """Extract text from an image using Tesseract OCR."""
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        return text.strip()
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def main():
    # Ensure the source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: {SOURCE_DIR} directory not found.")
        return

    # Process all JPG/PNG images
    for filename in os.listdir(SOURCE_DIR):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        image_path = os.path.join(SOURCE_DIR, filename)
        text = extract_text_from_image(image_path)

        if text:
            print(f"Extracted text from {filename}:\n{text}\n{'-'*40}")
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"File: {filename}\n{text}\n{'-'*40}\n")

if __name__ == "__main__":
    main()