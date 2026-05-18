import os
import time
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
# Make sure to set GEMINI_API_KEY in your environment or a .env file in this directory
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY environment variable not found. Script will likely fail.")
genai.configure(api_key=api_key)

# Configuration
SOURCE_DIR = 'albany_silver'

def identify_comic(image_path):
    print(f"Analyzing {image_path}...")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        img = Image.open(image_path)
        prompt = (
            "You are an expert comic book identifier. "
            "Analyze this image and identify the comic book's publisher, title, issue number, and publication date (Year). "
            "Return ONLY a single string in exactly this format: Publisher - Title - Issue - Year. "
            "For example: Marvel - The Amazing Spider-Man - 300 - 1988. "
            "If you cannot identify a field, omit it or make your best guess, but maintain the dashes. "
            "Do not include any other text, quotes, or markdown."
        )
        response = model.generate_content([prompt, img])
        result = response.text.strip()
        # Clean up possible formatting issues
        result = result.replace('\n', '')
        return result
    except Exception as e:
        print(f"Error analyzing {image_path}: {e}")
        return None

def main():
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: {SOURCE_DIR} directory not found.")
        return

    # Process all JPG/PNG files
    for filename in os.listdir(SOURCE_DIR):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
            
        # Skip if it already looks like it matches the pattern Publisher - Title - Issue - Date
        if filename.count('-') >= 2:
            print(f"Skipping {filename}, already looks formatted.")
            continue
            
        old_path = os.path.join(SOURCE_DIR, filename)
        new_name_base = identify_comic(old_path)
        
        if new_name_base:
            # Keep original extension, but lowercase it for consistency
            _, ext = os.path.splitext(filename)
            new_filename = f"{new_name_base}{ext.lower()}"
            
            # Sanitize filename (remove invalid characters for Windows)
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                new_filename = new_filename.replace(char, '')
            
            new_path = os.path.join(SOURCE_DIR, new_filename)
            
            # Ensure unique filename
            counter = 1
            while os.path.exists(new_path):
                name, e = os.path.splitext(new_filename)
                new_path = os.path.join(SOURCE_DIR, f"{name} ({counter}){e}")
                counter += 1
                
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {filename} -> {os.path.basename(new_path)}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")
                
            # Rate limiting for API (especially useful if on Gemini free tier)
            time.sleep(3)

if __name__ == "__main__":
    main()
