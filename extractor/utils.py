import pdfplumber
import pypdfium2 as pdfium
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import pandas as pd
import json
from datetime import datetime
import hashlib

def extract_pdf_content(pdf_path, output_img_folder):
    """
    Extraction complète du contenu PDF avec préservation de la position
    et détection améliorée des images
    """
    result = {
        "text": "",
        "positioned_text": [],  # Nouveau: texte avec coordonnées
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
    
    # Extraction avec PyMuPDF pour images et contenu positionnel
    try:
        pdf_doc = fitz.open(pdf_path)
        result["metadata"]["total_pages"] = len(pdf_doc)
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            page_data = {
                "page_number": page_num + 1,
                "text": "",
                "positioned_text": [],
                "tables": [],
                "images": [],
                "bbox": [0, 0, page.rect.width, page.rect.height],
                "rotation": page.rotation
            }
            
            # Extraction du texte avec positions (PyMuPDF)
            text_dict = page.get_text("dict")
            positioned_chars = []
            page_text = ""
            
            for block in text_dict["blocks"]:
                if "lines" in block:  # Block de texte
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            if text.strip():
                                page_text += text
                                
                                # Informations de position pour chaque span
                                positioned_chars.append({
                                    "text": text,
                                    "bbox": span["bbox"],  # [x0, y0, x1, y1]
                                    "font": span["font"],
                                    "size": span["size"],
                                    "flags": span["flags"],
                                    "color": span["color"]
                                })
                        page_text += "\n"
            
            page_data["text"] = page_text
            page_data["positioned_text"] = positioned_chars
            result["positioned_text"].extend(positioned_chars)
            result["text"] += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            # Extraction des images avec PyMuPDF (méthode principale)
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    # Récupérer les données de l'image
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Créer l'image PIL
                    image_pil = Image.open(io.BytesIO(image_bytes))
                    
                    # Nom de fichier unique
                    image_filename = f"pymupdf_p{page_num + 1}_{img_index + 1}.{image_ext}"
                    image_path = os.path.join(output_img_folder, image_filename)
                    
                    # Sauvegarder l'image
                    image_pil.save(image_path)
                    
                    # Métadonnées de l'image
                    image_data = {
                        "image_id": f"page_{page_num + 1}_image_{img_index + 1}",
                        "filename": image_filename,
                        "path": image_path,
                        "page": page_num + 1,
                        "format": image_ext,
                        "width": image_pil.width,
                        "height": image_pil.height,
                        "size_bytes": os.path.getsize(image_path),
                        "mode": image_pil.mode,
                        "extraction_method": "PyMuPDF"
                    }
                    
                    result["images"].append(image_data)
                    page_data["images"].append(image_data)
                    
                except Exception as e:
                    # Log de l'erreur sans arrêter le processus
                    error_data = {
                        "error": f"Erreur extraction image PyMuPDF page {page_num + 1}, index {img_index}: {str(e)}",
                        "page": page_num + 1,
                        "image_index": img_index,
                        "method": "PyMuPDF"
                    }
                    if "extraction_errors" not in result:
                        result["extraction_errors"] = []
                    result["extraction_errors"].append(error_data)
            
            result["pages"].append(page_data)
        
        pdf_doc.close()
        
    except Exception as e:
        error_data = {
            "error": f"Erreur ouverture PDF avec PyMuPDF: {str(e)}"
        }
        if "extraction_errors" not in result:
            result["extraction_errors"] = []
        result["extraction_errors"].append(error_data)
    
    # Extraction complémentaire avec pypdfium2 pour images manquées
    try:
        pdf_doc_pdfium = pdfium.PdfDocument(pdf_path)
        
        for page_num in range(len(pdf_doc_pdfium)):
            page = pdf_doc_pdfium[page_num]
            
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
                            
                            # Vérifier si cette image n'a pas déjà été extraite par PyMuPDF
                            image_hash = hashlib.md5(image.tobytes()).hexdigest()
                            existing_hashes = []
                            for existing_img in result["images"]:
                                if existing_img.get("page") == page_num + 1:
                                    try:
                                        existing_pil = Image.open(existing_img["path"])
                                        existing_hash = hashlib.md5(existing_pil.tobytes()).hexdigest()
                                        existing_hashes.append(existing_hash)
                                    except:
                                        pass
                            
                            if image_hash not in existing_hashes:
                                # Nom de fichier unique
                                image_filename = f"pdfium_p{page_num + 1}_{img_idx + 1}.png"
                                image_path = os.path.join(output_img_folder, image_filename)
                                
                                # Sauvegarder l'image
                                image.save(image_path, "PNG")
                                
                                # Métadonnées de l'image
                                image_data = {
                                    "image_id": f"page_{page_num + 1}_pdfium_image_{img_idx + 1}",
                                    "filename": image_filename,
                                    "path": image_path,
                                    "page": page_num + 1,
                                    "format": "png",
                                    "width": width,
                                    "height": height,
                                    "size_bytes": os.path.getsize(image_path),
                                    "mode": image.mode if hasattr(image, 'mode') else 'RGBA',
                                    "extraction_method": "pypdfium2"
                                }
                                
                                result["images"].append(image_data)
                                
                                # Ajouter l'image aux données de la page correspondante
                                if page_num < len(result["pages"]):
                                    result["pages"][page_num]["images"].append(image_data)
                            
                    except Exception as e:
                        # Log de l'erreur sans arrêter le processus
                        error_data = {
                            "error": f"Erreur extraction image pypdfium2 page {page_num + 1}, index {img_idx}: {str(e)}",
                            "page": page_num + 1,
                            "image_index": img_idx,
                            "method": "pypdfium2"
                        }
                        if "extraction_errors" not in result:
                            result["extraction_errors"] = []
                        result["extraction_errors"].append(error_data)
                        
            except Exception as e:
                # Erreur pour toute la page
                error_data = {
                    "error": f"Erreur extraction images pypdfium2 page {page_num + 1}: {str(e)}",
                    "page": page_num + 1,
                    "method": "pypdfium2"
                }
                if "extraction_errors" not in result:
                    result["extraction_errors"] = []
                result["extraction_errors"].append(error_data)
    
    except Exception as e:
        # Erreur lors de l'ouverture du PDF pour les images
        error_data = {
            "error": f"Erreur ouverture PDF pypdfium2 pour extraction images: {str(e)}"
        }
        if "extraction_errors" not in result:
            result["extraction_errors"] = []
        result["extraction_errors"].append(error_data)
    
    # Extraction des tableaux avec pdfplumber (amélioration de la détection)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extraction des tableaux avec paramètres personnalisés
                table_settings = {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "explicit_vertical_lines": [],
                    "explicit_horizontal_lines": [],
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_vertical": 3,
                    "min_words_horizontal": 1,
                    "intersection_tolerance": 3,
                    "text_tolerance": 3,
                    "text_x_tolerance": 3,
                    "text_y_tolerance": 3
                }
                
                # Essayer différentes stratégies de détection
                tables_found = []
                
                # Stratégie 1: Lignes strictes
                tables = page.extract_tables(table_settings)
                if tables:
                    tables_found.extend(tables)
                
                # Stratégie 2: Texte seulement (pour tableaux sans bordures)
                table_settings["vertical_strategy"] = "text"
                table_settings["horizontal_strategy"] = "text"
                tables_text = page.extract_tables(table_settings)
                if tables_text:
                    for table in tables_text:
                        # Éviter les doublons
                        if table not in tables_found:
                            tables_found.append(table)
                
                # Traiter les tableaux trouvés
                for table_idx, table in enumerate(tables_found):
                    if table and len(table) > 0:
                        # Nettoyer les cellules vides et None
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [cell.strip() if cell and cell.strip() else "" for cell in row]
                            if any(cleaned_row):  # Garder seulement les lignes non vides
                                cleaned_table.append(cleaned_row)
                        
                        if cleaned_table and len(cleaned_table) > 1:  # Au moins 2 lignes
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
                            
                            result["tables"].append(table_data)
                            
                            # Ajouter aux données de la page correspondante
                            if page_num - 1 < len(result["pages"]):
                                result["pages"][page_num - 1]["tables"].append(table_data)
                
    except Exception as e:
        error_data = {
            "error": f"Erreur extraction tableaux avec pdfplumber: {str(e)}"
        }
        if "extraction_errors" not in result:
            result["extraction_errors"] = []
        result["extraction_errors"].append(error_data)
    
    # Ajouter des statistiques finales
    result["metadata"]["total_images"] = len(result["images"])
    result["metadata"]["total_tables"] = len(result["tables"])
    result["metadata"]["total_text_length"] = len(result["text"])
    result["metadata"]["total_positioned_elements"] = len(result["positioned_text"])
    
    return result

def extract_text_with_layout(pdf_path):
    """
    Extraction de texte avec préservation complète du layout
    Retourne les coordonnées exactes de chaque caractère/mot
    """
    layout_data = []
    
    try:
        pdf_doc = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            
            # Extraction avec détails maximum
            text_dict = page.get_text("dict")
            
            for block_num, block in enumerate(text_dict["blocks"]):
                if "lines" in block:  # Block de texte
                    for line_num, line in enumerate(block["lines"]):
                        for span_num, span in enumerate(line["spans"]):
                            # Extraire chaque caractère avec sa position
                            chars = page.get_text("rawdict")
                            
                            for char_data in chars["blocks"]:
                                if "lines" in char_data:
                                    for line_data in char_data["lines"]:
                                        for span_data in line_data["spans"]:
                                            if span_data["bbox"] == span["bbox"]:
                                                # Caractères individuels
                                                text = span_data["text"]
                                                for i, char in enumerate(text):
                                                    # Estimation de la position du caractère
                                                    char_width = (span["bbox"][2] - span["bbox"][0]) / len(text)
                                                    char_x = span["bbox"][0] + (i * char_width)
                                                    
                                                    layout_data.append({
                                                        "page": page_num + 1,
                                                        "block": block_num,
                                                        "line": line_num,
                                                        "span": span_num,
                                                        "char": char,
                                                        "char_index": i,
                                                        "x": char_x,
                                                        "y": span["bbox"][1],
                                                        "width": char_width,
                                                        "height": span["bbox"][3] - span["bbox"][1],
                                                        "font": span["font"],
                                                        "size": span["size"],
                                                        "color": span["color"]
                                                    })
        
        pdf_doc.close()
        
    except Exception as e:
        print(f"Erreur extraction layout: {e}")
    
    return layout_data
