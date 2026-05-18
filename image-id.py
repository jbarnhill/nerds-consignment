import csv
import os
import re
import time
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ==========================================
# STEP 1: DEFINE STRUCTURAL OUTPUT SCHEMA
# ==========================================
class ComicBookDetails(BaseModel):
    publisher: str = Field(description="The publisher of the comic book (e.g., Marvel, DC, Gold Key, Dell, Charlton).")
    title: str = Field(description="The exact title of the comic book series.")
    issue_number: str = Field(description="The issue number as a string (e.g., '15', '38', or 'One-Shot').")
    publish_year: int = Field(description="The 4-digit publication year. If uncertain, provide your closest estimate.")
    is_key_issue: bool = Field(description="True if this is a known key issue, milestone number, or major character debut.")
    key_details: str = Field(description="Brief details on why it is a key issue, or 'None' if it is a common issue.")

# ==========================================
# STEP 2: IMAGE PRE-PROCESSING ENGINE
# ==========================================
def preprocess_image(image_path: Path, target_width: int = 1330) -> Path:
    """
    Resizes the input image to optimize token usage and forces a standard
    comic book aspect ratio (1.42) to optimize OCR accuracy.
    """
    print(f"Processing image geometry for: {image_path.name}")
    target_height = int(target_width * 1.4285)
    output_path = image_path.parent / f"opt_{image_path.stem}.jpg"
    
    with Image.open(image_path) as img:
        resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        resized_img.save(output_path, "JPEG", quality=80)
        
    return output_path

# ==========================================
# STEP 3: MULTIMODAL INFERENCE ENGINE
# ==========================================
def analyze_comic_cover(client: genai.Client, image_path: Path) -> ComicBookDetails:
    """
    Sends the pre-processed image to Gemini 2.5 Flash to extract catalog data
    coerced strictly into the Pydantic schema.
    """
    print(f"Running visual and text taxonomy identification for: {image_path.name}")
    
    system_instruction = (
        "You are an expert comic book cataloging assistant. Your job is to extract "
        "precise visual data from cover images. Analyze layouts, corner price boxes, "
        "indicia hints, art styles, logos, text, and issue numbers."
    )
    
    prompt = (
        "Analyze this comic book cover image. Inspect the visual indicators and fields "
        "to accurately populate the required database tracking fields."
    )
    
    with Image.open(image_path) as img:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=ComicBookDetails,
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt],
            config=config
        )
        
        return ComicBookDetails.model_validate_json(response.text)

# ==========================================
# STEP 4: FILE SANITIZATION & RENAMING HELPER
# ==========================================
def generate_safe_new_name(directory: Path, data: ComicBookDetails, original_suffix: str) -> Path:
    """
    Creates a clean, file-system safe name string based on metadata:
    Format: publisher-title-issue-publish_year.jpg
    """
    # Combine the string fields using simple hyphens
    raw_name = f"{data.publisher}-{data.title}-{data.issue_number}-{data.publish_year}"
    
    # Replace spaces with underscores or clean dashes, and drop illegal punctuation
    clean_name = raw_name.replace(" ", "_")
    clean_name = re.sub(r'[\\/*?:"<>|]', "", clean_name) # Strip out OS reserved tokens
    
    base_target = directory / f"{clean_name}{original_suffix}"
    
    # Check for collision and raise an error to alert user instead of silently appending v2
    if base_target.exists():
        raise FileExistsError(f"Potential duplicate detected: '{base_target.name}' already exists.")
        
    return base_target

# ==========================================
# STEP 5: PIPELINE ORCHESTRATION & STORAGE
# ==========================================
def run_inventory_pipeline(input_directory: str, output_csv_path: str):
    """
    Iterates through a folder of images, processes them, runs inference,
    logs metadata to a CSV file, and renames the file source.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is missing. Set it before running the script.")
        
    client = genai.Client()
    dir_path = Path(input_directory)
    csv_file = Path(output_csv_path)
    
    # Load previously processed files to avoid re-processing if CSV exists
    processed_files = set()
    if csv_file.exists():
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers and "New_File" in headers:
                new_file_idx = headers.index("New_File")
                for row in reader:
                    if len(row) > new_file_idx:
                        processed_files.add(row[new_file_idx])
                        
    def is_already_processed(filename: str) -> bool:
        if filename in processed_files:
            return True
        # Heuristic: Processed files have no spaces and at least 3 hyphens (e.g. publisher-title-issue-year)
        if " " not in filename and filename.count("-") >= 3:
            return True
        return False
    
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    # Filter files dynamically, avoiding optimization buffers, output tracks, and processed files
    image_files = [
        f for f in dir_path.iterdir() 
        if f.suffix.lower() in valid_extensions 
        and not f.name.startswith("opt_")
        and not is_already_processed(f.name)
    ]
    
    if not image_files:
        print(f"No valid source images found in directory: {input_directory}")
        return

    print(f"Found {len(image_files)} image files to index and rename. Opening CSV pipeline...\n")
    
    headers = ["Original_File", "New_File", "Publisher", "Title", "Issue_Number", "Publish_Year", "Is_Key", "Key_Details"]
    write_headers = not csv_file.exists()
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_headers:
            writer.writerow(headers)
            
        for img_file in image_files:
            temp_optimized_image = None
            try:
                # 1. Pre-process current image frame geometry
                temp_optimized_image = preprocess_image(img_file)
                
                # 2. Extract text and visual attributes from binary payload
                comic_data = analyze_comic_cover(client, temp_optimized_image)
                
                # 3. Calculate safe new file path identity string
                new_file_path = generate_safe_new_name(dir_path, comic_data, img_file.suffix)
                
                # 4. Write data record properties to tracking matrix
                writer.writerow([
                    img_file.name,
                    new_file_path.name,
                    comic_data.publisher,
                    comic_data.title,
                    comic_data.issue_number,
                    comic_data.publish_year,
                    comic_data.is_key_issue,
                    comic_data.key_details
                ])
                
                # 5. Commit change step directly to storage drive
                img_file.rename(new_file_path)
                print(f"SUCCESS: Renamed '{img_file.name}' -> '{new_file_path.name}'")
                print(f"Logged record: {comic_data.title} #{comic_data.issue_number}\n")
                
            except Exception as e:
                print(f"ERROR executing pipeline on file {img_file.name}: {e}\n")
                
            finally:
                # Clear optimized temporary target
                if temp_optimized_image and temp_optimized_image.exists():
                    temp_optimized_image.unlink()
            
            # Pause briefly to prevent overwhelming the API / hitting rate limits
            time.sleep(3)

if __name__ == "__main__":
    TARGET_IMAGE_FOLDER = "./albany_silver" 
    OUTPUT_CSV = "./comic_inventory.csv"
    
    run_inventory_pipeline(TARGET_IMAGE_FOLDER, OUTPUT_CSV)
    print("Inventory scanning and batch renaming task finished.")