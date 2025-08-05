import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
import io
import os
import pandas as pd
import json
from datetime import datetime

def extract_pdf_content(pdf_path, output_img_folder):
    result = {
        "text": "",
        "tables": [],
        "images": [],
        "metadata": {
            "total_pages": 0,
            "extraction_date": datetime.now().isoformat(),
            "file_size": os.path.getsize(pdf_path)
        },
        "pages": []
    }

    # Créer le dossier de sortie pour les images
    os.makedirs(output_img_folder, exist_ok=True)
    
    # Extraction avec pdfplumber pour texte et tableaux
    with pdfplumber.open(pdf_path) as pdf:
        result["metadata"]["total_pages"] = len(pdf.pages)
        
        for page_num, page in enumerate(pdf.pages, 1):
            page_data = {
                "page_number": page_num,
                "text": "",
                "tables": [],
                "bbox": page.bbox,
                "rotation": page.rotation
            }
            
            # Extraction du texte
            page_text = page.extract_text() or ''
            page_data["text"] = page_text
            result["text"] += f"\n--- Page {page_num} ---\n{page_text}\n"
            
            # Extraction des tableaux avec plus de détails
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                if table and len(table) > 0:
                    # Nettoyer les cellules vides et None
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [cell.strip() if cell and cell.strip() else "" for cell in row]
                        if any(cleaned_row):  # Garder seulement les lignes non vides
                            cleaned_table.append(cleaned_row)
                    
                    if cleaned_table:
                        table_data = {
                            "table_id": f"page_{page_num}_table_{table_idx + 1}",
                            "page": page_num,
                            "data": cleaned_table,
                            "rows": len(cleaned_table),
                            "columns": len(cleaned_table[0]) if cleaned_table else 0
                        }
                        
                        # Tentative de conversion en DataFrame pour analyse
                        try:
                            if len(cleaned_table) > 1:  # Au moins une ligne d'en-tête + données
                                df = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
                                table_data["csv_data"] = df.to_csv(index=False)
                                table_data["has_headers"] = True
                            else:
                                table_data["has_headers"] = False
                        except Exception as e:
                            table_data["conversion_error"] = str(e)
                            table_data["has_headers"] = False
                        
                        page_data["tables"].append(table_data)
                        result["tables"].append(table_data)
            
            result["pages"].append(page_data)

    # Extraction des images avec pypdfium2
    try:
        pdf_doc = pdfium.PdfDocument(pdf_path)
        image_counter = 0
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            
            try:
                # Obtenir les objets images de la page
                objects = []
                for obj_index in range(page.count_objects()):
                    obj = page.get_object(obj_index)
                    if obj.get_type() == pdfium.FPDF_PAGEOBJ_IMAGE:
                        objects.append((obj_index, obj))
                
                for img_idx, (obj_index, obj) in enumerate(objects):
                    try:
                        # Extraire l'image
                        bitmap = obj.get_bitmap()
                        if bitmap:
                            # Convertir en PIL Image
                            width = bitmap.get_width()
                            height = bitmap.get_height()
                            stride = bitmap.get_stride()
                            
                            # Obtenir les données de pixels
                            buffer = bitmap.get_buffer()
                            
                            # Créer l'image PIL
                            image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", stride)
                            
                            # Nom de fichier unique
                            image_filename = f"image_p{page_num + 1}_{img_idx + 1}.png"
                            image_path = os.path.join(output_img_folder, image_filename)
                            
                            # Sauvegarder l'image
                            image.save(image_path, "PNG")
                            image_counter += 1
                            
                            # Métadonnées de l'image
                            image_data = {
                                "image_id": f"page_{page_num + 1}_image_{img_idx + 1}",
                                "filename": image_filename,
                                "path": image_path,
                                "page": page_num + 1,
                                "format": "png",
                                "width": width,
                                "height": height,
                                "size_bytes": os.path.getsize(image_path),
                                "mode": image.mode if hasattr(image, 'mode') else 'RGBA'
                            }
                            
                            result["images"].append(image_data)
                            
                            # Ajouter l'image aux données de la page correspondante
                            if page_num < len(result["pages"]):
                                if "images" not in result["pages"][page_num]:
                                    result["pages"][page_num]["images"] = []
                                result["pages"][page_num]["images"].append(image_data)
                            
                    except Exception as e:
                        # Log de l'erreur sans arrêter le processus
                        error_data = {
                            "error": f"Erreur extraction image page {page_num + 1}, index {img_idx}: {str(e)}",
                            "page": page_num + 1,
                            "image_index": img_idx
                        }
                        if "extraction_errors" not in result:
                            result["extraction_errors"] = []
                        result["extraction_errors"].append(error_data)
                        
            except Exception as e:
                # Erreur pour toute la page
                error_data = {
                    "error": f"Erreur extraction images page {page_num + 1}: {str(e)}",
                    "page": page_num + 1
                }
                if "extraction_errors" not in result:
                    result["extraction_errors"] = []
                result["extraction_errors"].append(error_data)
    
    except Exception as e:
        # Erreur lors de l'ouverture du PDF pour les images
        error_data = {
            "error": f"Erreur ouverture PDF pour extraction images: {str(e)}"
        }
        result["extraction_errors"] = [error_data]
    
    # Ajouter des statistiques finales
    result["metadata"]["total_images"] = len(result["images"])
    result["metadata"]["total_tables"] = len(result["tables"])
    result["metadata"]["total_text_length"] = len(result["text"])
    
    return result
