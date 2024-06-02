#%%
import os
import base64
import requests
from PIL import Image
import fitz  # PyMuPDF
import json
import argparse
import shutil

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
    base64_image = encode_image(image_path)
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": 'Extract the company name and amount charged from this invoice image. Return in JSON format as exactly {"company_name": "...", "amount": "..."}. Do not include any ```json``` tags, just return the exact JSON dictionary.'
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

def extract_info_from_pdf(pdf_path, temp_image_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap()
    pix.save(temp_image_path)
    info = extract_info_from_image(temp_image_path)
    os.remove(temp_image_path)
    return info

def rename_and_convert_to_pdf(file_path, new_filename):
    if file_path.lower().endswith(('png', 'jpg', 'jpeg')):
        image = Image.open(file_path)
        image.save(new_filename, "PDF")
    elif file_path.lower().endswith('pdf'):
        doc = fitz.open(file_path)
        if not os.path.exists(new_filename):
            doc.save(new_filename)

def process_invoices(folder_path):
    temp_image_path = os.path.join(folder_path, "temp_image.jpg")
    raw_folder = os.path.join(folder_path, "raw")
    processed_folder = os.path.join(folder_path, "processed")
    os.makedirs(raw_folder, exist_ok=True)
    os.makedirs(processed_folder, exist_ok=True)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.lower().endswith(('png', 'jpg', 'jpeg')):
            info = extract_info_from_image(file_path)
            info = json.loads(info)
        elif filename.lower().endswith('pdf'):
            info = extract_info_from_pdf(file_path, temp_image_path)
            info = json.loads(info)
        else:
            continue
        try:
            company_name = info["company_name"]
            amount = info["amount"]
            new_filename = f"{company_name} -- {amount.replace(' ', '').replace('.', '_')}.pdf"
            new_file_path = os.path.join(processed_folder, new_filename)
            rename_and_convert_to_pdf(file_path, new_file_path)
            shutil.move(file_path, os.path.join(raw_folder, filename))
        except Exception as e:
            print(f"Failed to extract information from {filename}")
            raise

#%%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a folder of invoice images and PDFs.')
    parser.add_argument('folder_path', type=str, help='The path to the folder containing the invoices.')
    args = parser.parse_args()

    process_invoices(args.folder_path)
# %%