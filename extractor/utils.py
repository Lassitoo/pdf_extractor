import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import io
import os

def extract_pdf_content(pdf_path, output_img_folder):
    result = {
        "text": "",
        "tables": [],
        "images": [],
    }

    # Texte + Tableaux
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            result["text"] += page.extract_text() or ''
            tables = page.extract_tables()
            for table in tables:
                result["tables"].append(table)

    # Images
    os.makedirs(output_img_folder, exist_ok=True)
    pdf_doc = fitz.open(pdf_path)
    for i, page in enumerate(pdf_doc):
        images = page.get_images(full=True)
        for j, img in enumerate(images):
            xref = img[0]
            base_image = pdf_doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            image_path = os.path.join(output_img_folder, f"image_{i}_{j}.{image_ext}")
            image.save(image_path)
            result["images"].append(image_path)

    return result
