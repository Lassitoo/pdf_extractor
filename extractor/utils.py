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
    
                    # Extraction des tableaux avec pdfplumber (focus sur les tableaux avec bordures)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Paramètres optimisés pour détecter uniquement les tableaux avec bordures
                table_settings = {
                    "vertical_strategy": "lines",  # Uniquement basé sur les lignes
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,  # Plus strict pour les bordures
                    "join_tolerance": 3,
                    "edge_min_length": 15,  # Lignes plus longues pour éviter les faux positifs
                    "min_words_vertical": 2,
                    "min_words_horizontal": 1,
                    "intersection_tolerance": 3,
                    "text_tolerance": 3,
                    "text_x_tolerance": 3,
                    "text_y_tolerance": 3
                }
                
                # Extraire uniquement avec la stratégie basée sur les lignes
                tables_found = []
                try:
                    tables = page.extract_tables(table_settings)
                    if tables:
                        # Vérifier chaque tableau pour s'assurer qu'il a des bordures
                        for table_idx, table in enumerate(tables):
                            # Obtenir la bbox approximative du tableau
                            table_bbox = None
                            try:
                                # Essayer d'obtenir la bbox du tableau
                                table_finder = page.find_tables(table_settings)
                                if table_finder and table_idx < len(table_finder):
                                    table_bbox = table_finder[table_idx].bbox
                            except:
                                pass
                            
                            # Vérifier si le tableau a des bordures
                            has_borders = detect_table_borders(page, table_bbox)
                            
                            # Ne garder que les tableaux avec bordures
                            if has_borders:
                                tables_found.append(("lines_with_borders", table))
                except:
                    pass
                
                # Traiter et nettoyer les tableaux trouvés
                for table_idx, table_info in enumerate(tables_found):
                    # Extraire la méthode et le tableau
                    if isinstance(table_info, tuple):
                        method, table = table_info
                    else:
                        method = "lines"  # Par défaut
                        table = table_info
                        
                    if table and len(table) > 0:
                        # Nettoyer et valider le tableau
                        cleaned_table = []
                        max_cols = 0
                        
                        # Première passe : déterminer le nombre maximum de colonnes
                        for row in table:
                            if row:
                                clean_row = []
                                for cell in row:
                                    if cell is not None:
                                        cell_text = str(cell).strip()
                                        clean_row.append(cell_text)
                                    else:
                                        clean_row.append("")
                                if len(clean_row) > max_cols:
                                    max_cols = len(clean_row)
                                if any(cell for cell in clean_row if cell):  # Au moins une cellule non vide
                                    cleaned_table.append(clean_row)
                        
                        # Deuxième passe : normaliser toutes les lignes au même nombre de colonnes
                        normalized_table = []
                        for row in cleaned_table:
                            # Étendre ou tronquer la ligne pour avoir max_cols colonnes
                            while len(row) < max_cols:
                                row.append("")
                            if len(row) > max_cols:
                                row = row[:max_cols]
                            normalized_table.append(row)
                        
                        # Valider que c'est vraiment un tableau (au moins 2 lignes et 2 colonnes)
                        if len(normalized_table) >= 2 and max_cols >= 2:
                            # Vérifier qu'il y a assez de contenu
                            non_empty_cells = sum(1 for row in normalized_table for cell in row if cell.strip())
                            total_cells = len(normalized_table) * max_cols
                            
                            # Au moins 30% des cellules doivent avoir du contenu
                            if non_empty_cells >= (total_cells * 0.3):
                                # Puisqu'on a déjà filtré pour les bordures, marquer comme ayant des bordures
                                has_borders = True
                                
                                table_data = {
                                    "table_id": f"page_{page_num}_table_{table_idx + 1}",
                                    "page": page_num,
                                    "data": normalized_table,
                                    "rows": len(normalized_table),
                                    "columns": max_cols,
                                    "has_borders": has_borders,
                                    "extraction_method": f"pdfplumber_{method}"
                                }
                                
                                # Déterminer s'il y a des en-têtes (première ligne différente des autres)
                                has_headers = False
                                if len(normalized_table) > 1:
                                    first_row = normalized_table[0]
                                    # Heuristique : si la première ligne a plus de texte ou des mots plus longs
                                    first_row_chars = sum(len(cell) for cell in first_row)
                                    avg_chars_other_rows = sum(sum(len(cell) for cell in row) for row in normalized_table[1:]) / (len(normalized_table) - 1)
                                    
                                    if first_row_chars > avg_chars_other_rows * 0.8:
                                        has_headers = True
                                
                                table_data["has_headers"] = has_headers
                                
                                # Tentative de conversion en DataFrame
                                try:
                                    if has_headers and len(normalized_table) > 1:
                                        df = pd.DataFrame(normalized_table[1:], columns=normalized_table[0])
                                        table_data["csv_data"] = df.to_csv(index=False)
                                    else:
                                        df = pd.DataFrame(normalized_table)
                                        table_data["csv_data"] = df.to_csv(index=False, header=False)
                                except Exception as e:
                                    table_data["conversion_error"] = str(e)
                                
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
    
    # Extraction complémentaire de tableaux avec PyMuPDF (uniquement pour tableaux avec bordures visibles)
    try:
        pdf_doc = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            
            # Vérifier s'il y a des lignes sur cette page qui pourraient indiquer des tableaux
            page_dict = page.get_text("dict")
            
            # Obtenir les objets de dessin (lignes, rectangles) de la page
            drawings = page.get_drawings()
            
            # Filtrer pour ne garder que les lignes droites
            lines = []
            for drawing in drawings:
                for item in drawing.get("items", []):
                    if item.get("type") == "l":  # ligne
                        lines.append({
                            "x0": item["p1"][0],
                            "y0": item["p1"][1], 
                            "x1": item["p2"][0],
                            "y1": item["p2"][1]
                        })
            
            # Si on a suffisamment de lignes, essayer de détecter des tableaux
            if len(lines) >= 4:
                # Créer un objet page simulé pour la détection de bordures
                class MockPage:
                    def __init__(self, lines):
                        self.lines = lines
                
                mock_page = MockPage(lines)
                
                # Vérifier s'il y a des bordures de tableau sur cette page
                if detect_table_borders(mock_page):
                    # Obtenir les blocs de texte pour essayer de reconstruire le tableau
                    text_blocks = []
                    
                    for block in page_dict["blocks"]:
                        if "lines" in block:  # Block de texte
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    if span["text"].strip():
                                        text_blocks.append({
                                            "text": span["text"].strip(),
                                            "x0": span["bbox"][0],
                                            "y0": span["bbox"][1],
                                            "x1": span["bbox"][2],
                                            "y1": span["bbox"][3],
                                            "font_size": span["size"]
                                        })
                    
                    # Essayer de détecter des structures tabulaires uniquement s'il y a des bordures
                    if text_blocks:
                        detected_tables = detect_tables_from_text_blocks_with_borders(text_blocks, page_num + 1, lines)
                        
                        for table_data in detected_tables:
                            # Vérifier si ce tableau n'existe pas déjà (éviter les doublons)
                            existing_table_found = False
                            for existing_table in result["tables"]:
                                if (existing_table["page"] == table_data["page"] and 
                                    existing_table["rows"] == table_data["rows"] and
                                    existing_table["columns"] == table_data["columns"]):
                                    # Comparer quelques cellules pour voir si c'est le même tableau
                                    if len(existing_table["data"]) > 0 and len(table_data["data"]) > 0:
                                        if existing_table["data"][0] == table_data["data"][0]:
                                            existing_table_found = True
                                            break
                            
                            if not existing_table_found:
                                result["tables"].append(table_data)
                                
                                # Ajouter aux données de la page correspondante
                                if page_num < len(result["pages"]):
                                    result["pages"][page_num]["tables"].append(table_data)
        
        pdf_doc.close()
        
    except Exception as e:
        error_data = {
            "error": f"Erreur extraction tableaux avec PyMuPDF: {str(e)}"
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

def detect_table_borders(page, table_bbox=None):
    """
    Détecte si un tableau a des bordures naturelles en analysant les lignes dans le PDF
    """
    try:
        # Obtenir toutes les lignes de la page
        lines = page.lines
        if not lines or len(lines) < 4:
            return False
        
        # Si on a des coordonnées de tableau, vérifier uniquement dans cette zone
        if table_bbox:
            x0, y0, x1, y1 = table_bbox
            # Filtrer les lignes qui sont dans la zone du tableau (avec une petite marge)
            margin = 5
            relevant_lines = []
            for line in lines:
                line_x0, line_y0 = line['x0'], line['y0']
                line_x1, line_y1 = line['x1'], line['y1']
                
                # Vérifier si la ligne intersecte avec la zone du tableau
                if (line_x0 >= x0 - margin and line_x1 <= x1 + margin and 
                    line_y0 >= y0 - margin and line_y1 <= y1 + margin):
                    relevant_lines.append(line)
            
            lines = relevant_lines
        
        if len(lines) < 4:
            return False
        
        # Analyser les lignes pour voir si elles forment une grille
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            width = abs(line['x1'] - line['x0'])
            height = abs(line['y1'] - line['y0'])
            
            # Ligne horizontale si largeur > hauteur et largeur significative
            if width > height and width > 20:
                horizontal_lines.append(line)
            # Ligne verticale si hauteur > largeur et hauteur significative  
            elif height > width and height > 20:
                vertical_lines.append(line)
        
        # Vérifier qu'on a suffisamment de lignes pour former un tableau
        if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
            # Vérifier que les lignes forment vraiment une grille
            # Les lignes horizontales doivent être approximativement alignées
            horizontal_lines.sort(key=lambda l: l['y0'])
            vertical_lines.sort(key=lambda l: l['x0'])
            
            # Vérifier l'espacement régulier des lignes horizontales
            h_spacings = []
            for i in range(1, len(horizontal_lines)):
                spacing = abs(horizontal_lines[i]['y0'] - horizontal_lines[i-1]['y0'])
                if spacing > 5:  # Espacement minimum
                    h_spacings.append(spacing)
            
            # Vérifier l'espacement régulier des lignes verticales
            v_spacings = []
            for i in range(1, len(vertical_lines)):
                spacing = abs(vertical_lines[i]['x0'] - vertical_lines[i-1]['x0'])
                if spacing > 5:  # Espacement minimum
                    v_spacings.append(spacing)
            
            # Si on a des espacements réguliers, c'est probablement un vrai tableau
            if len(h_spacings) >= 1 and len(v_spacings) >= 1:
                return True
        
        return False
        
    except Exception:
        # En cas d'erreur, supposer qu'il n'y a pas de bordures
        return False

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

def detect_tables_from_text_blocks_with_borders(text_blocks, page_num, border_lines):
    """
    Détecte les tableaux basés sur l'alignement des blocs de texte ET la présence de bordures
    """
    if not text_blocks or len(text_blocks) < 4 or not border_lines:
        return []
    
    # Trier les blocs par position (y puis x)
    text_blocks.sort(key=lambda b: (round(b["y0"], 1), round(b["x0"], 1)))
    
    # Analyser les lignes de bordure pour identifier les zones de tableau
    horizontal_lines = []
    vertical_lines = []
    
    for line in border_lines:
        width = abs(line['x1'] - line['x0'])
        height = abs(line['y1'] - line['y0'])
        
        if width > height and width > 30:  # Ligne horizontale significative
            horizontal_lines.append(line)
        elif height > width and height > 30:  # Ligne verticale significative
            vertical_lines.append(line)
    
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return []  # Pas assez de bordures pour un tableau
    
    # Trier les lignes
    horizontal_lines.sort(key=lambda l: l['y0'])
    vertical_lines.sort(key=lambda l: l['x0'])
    
    # Définir la zone du tableau basée sur les bordures
    table_x0 = min(v['x0'] for v in vertical_lines)
    table_x1 = max(v['x0'] for v in vertical_lines)
    table_y0 = min(h['y0'] for h in horizontal_lines)
    table_y1 = max(h['y0'] for h in horizontal_lines)
    
    # Filtrer les blocs de texte qui sont dans la zone du tableau
    table_text_blocks = []
    margin = 5
    
    for block in text_blocks:
        if (table_x0 - margin <= block['x0'] <= table_x1 + margin and
            table_y0 - margin <= block['y0'] <= table_y1 + margin):
            table_text_blocks.append(block)
    
    if len(table_text_blocks) < 4:
        return []
    
    # Grouper les blocs par lignes (basé sur les lignes horizontales)
    table_rows = []
    
    for i in range(len(horizontal_lines) - 1):
        row_y0 = horizontal_lines[i]['y0']
        row_y1 = horizontal_lines[i + 1]['y0']
        
        # Trouver tous les blocs de texte dans cette ligne
        row_blocks = []
        for block in table_text_blocks:
            if row_y0 <= block['y0'] <= row_y1:
                row_blocks.append(block)
        
        if row_blocks:
            # Trier par position x
            row_blocks.sort(key=lambda b: b['x0'])
            table_rows.append(row_blocks)
    
    if len(table_rows) < 2:
        return []
    
    # Déterminer le nombre de colonnes basé sur les lignes verticales
    num_cols = len(vertical_lines) - 1
    if num_cols < 2:
        return []
    
    # Construire le tableau en assignant les blocs de texte aux cellules
    table_data = []
    
    for row_blocks in table_rows:
        row = [""] * num_cols
        
        for block in row_blocks:
            # Déterminer dans quelle colonne ce bloc appartient
            block_x = block['x0']
            col_index = 0
            
            for i in range(len(vertical_lines) - 1):
                if vertical_lines[i]['x0'] <= block_x < vertical_lines[i + 1]['x0']:
                    col_index = i
                    break
            
            if col_index < num_cols:
                if row[col_index]:  # Si la cellule a déjà du contenu, l'ajouter
                    row[col_index] += " " + block['text']
                else:
                    row[col_index] = block['text']
        
        # Ajouter la ligne seulement si elle a du contenu
        if any(cell.strip() for cell in row):
            table_data.append(row)
    
    if len(table_data) < 2:
        return []
    
    # Vérifier que le tableau a du contenu significatif
    non_empty_cells = sum(1 for row in table_data for cell in row if cell.strip())
    total_cells = len(table_data) * num_cols
    
    if non_empty_cells < (total_cells * 0.3):  # Au moins 30% de cellules non vides
        return []
    
    # Déterminer s'il y a des en-têtes
    has_headers = False
    if len(table_data) > 1:
        first_row_chars = sum(len(cell) for cell in table_data[0])
        if len(table_data) > 1:
            avg_other_rows = sum(sum(len(cell) for cell in row) for row in table_data[1:]) / (len(table_data) - 1)
            if first_row_chars > avg_other_rows * 0.7:
                has_headers = True
    
    table_info = {
        "table_id": f"page_{page_num}_pymupdf_bordered_table_1",
        "page": page_num,
        "data": table_data,
        "rows": len(table_data),
        "columns": num_cols,
        "has_headers": has_headers,
        "has_borders": True,  # Par définition, puisqu'on a détecté des bordures
        "extraction_method": "PyMuPDF_bordered"
    }
    
    # Générer CSV
    try:
        if has_headers and len(table_data) > 1:
            df = pd.DataFrame(table_data[1:], columns=table_data[0])
            table_info["csv_data"] = df.to_csv(index=False)
        else:
            df = pd.DataFrame(table_data)
            table_info["csv_data"] = df.to_csv(index=False, header=False)
    except Exception as e:
        table_info["conversion_error"] = str(e)
    
    return [table_info]
