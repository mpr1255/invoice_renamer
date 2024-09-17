#%%
import warnings
from urllib3.exceptions import NotOpenSSLWarning
from tqdm import tqdm
import os
import base64
import requests
from PIL import Image
import fitz  # PyMuPDF
import json
import argparse
import shutil
import re
import pytesseract

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
api_key = os.getenv("OPENAI_API_KEY")

#%%
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_info_from_image(image_path):
    try:
        base64_image = encode_image(image_path)
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": 'Extract the company name and amount charged from this invoice image. Return in JSON format as exactly {"company_name": "...", "amount": "..."}. Do not include any ```json``` tags, just return the exact JSON dictionary. Some '
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error using OpenAI API: {str(e)}. Falling back to Tesseract.")
        return extract_info_with_tesseract(image_path)

def extract_info_with_tesseract(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        
        # Simple regex patterns to find company name and amount
        company_pattern = r'(?i)(?:company|business|from):\s*(.+)'
        amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        
        company_match = re.search(company_pattern, text)
        amount_match = re.search(amount_pattern, text)
        
        company_name = company_match.group(1) if company_match else ""
        amount = amount_match.group(1) if amount_match else ""
        
        return json.dumps({"company_name": company_name.strip(), "amount": amount.strip()})
    except Exception as e:
        print(f"Error extracting info with Tesseract: {str(e)}")
        return json.dumps({"company_name": "", "amount": ""})

def extract_info_from_pdf(pdf_path):
    temp_image_path = None
    try:
        doc = fitz.open(pdf_path)
        all_info = []
        for page in doc:
            pix = page.get_pixmap()
            temp_image_path = f"temp_image_{page.number}.jpg"
            pix.save(temp_image_path)
            info = extract_info_from_image(temp_image_path)
            all_info.append(json.loads(info))
            os.remove(temp_image_path)
            temp_image_path = None
        # Combine info from all pages, prioritizing non-empty values
        combined_info = {"company_name": "", "amount": ""}
        for info in all_info:
            if not combined_info["company_name"] and info["company_name"]:
                combined_info["company_name"] = info["company_name"]
            if not combined_info["amount"] and info["amount"]:
                combined_info["amount"] = info["amount"]
        return json.dumps(combined_info)
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {str(e)}")
        if temp_image_path:
            return extract_info_with_tesseract(temp_image_path)
        return json.dumps({"company_name": "", "amount": ""})
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)

def rename_and_convert_to_pdf(file_path, new_filename):
    if file_path.lower().endswith(('png', 'jpg', 'jpeg')):
        image = Image.open(file_path)
        image.save(new_filename, "PDF")
    elif file_path.lower().endswith('pdf'):
        doc = fitz.open(file_path)
        if not os.path.exists(new_filename):
            doc.save(new_filename)

def process_invoices(folder_path):
    raw_folder = os.path.join(folder_path, "raw")
    processed_folder = os.path.join(folder_path, "processed")
    os.makedirs(raw_folder, exist_ok=True)
    os.makedirs(processed_folder, exist_ok=True)

    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'pdf'))]
    errored_files = []

    for filename in tqdm(files, desc="Processing invoices"):
        file_path = os.path.join(folder_path, filename)
        try:
            if filename.lower().endswith(('png', 'jpg', 'jpeg')):
                info = extract_info_from_image(file_path)
            elif filename.lower().endswith('pdf'):
                info = extract_info_from_pdf(file_path)
            else:
                continue

            info = json.loads(info)
            company_name = info["company_name"].upper()
            amount = info["amount"]
            new_filename = f"{company_name} -- {amount.replace(' ', '').replace('.', '_')}.pdf"
            new_file_path = os.path.join(processed_folder, new_filename)
            rename_and_convert_to_pdf(file_path, new_file_path)
            shutil.move(file_path, os.path.join(raw_folder, filename))
        except Exception as e:
            print(f"\nError processing {filename}: {str(e)}")
            errored_files.append(file_path)

    if errored_files:
        print("\nThe following files encountered errors and need examination:")
        for file in errored_files:
            print(file)
    else:
        print("\nAll files processed successfully!")

#%%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a folder of invoice images and PDFs.')
    parser.add_argument('folder_path', type=str, help='The path to the folder containing the invoices.')
    args = parser.parse_args()
    process_invoices(args.folder_path)
# %%