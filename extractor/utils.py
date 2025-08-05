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


def clean_and_validate_table(table, page, table_settings, page_num, table_idx, method):
    """
    Nettoie, normalise et valide un tableau extrait par pdfplumber ou autre.
    Retourne None si le tableau n'est pas pertinent.
    """
    cleaned_table = []
    max_cols = 0

    # Nettoyage des lignes et cellules
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

    # Normalisation du nombre de colonnes
    normalized_table = []
    for row in cleaned_table:
        while len(row) < max_cols:
            row.append("")
        if len(row) > max_cols:
            row = row[:max_cols]
        normalized_table.append(row)

    # Validation : au moins 2 lignes et 2 colonnes
    if len(normalized_table) < 2 or max_cols < 2:
        return None

    # Validation : au moins 30% de cellules non vides
    non_empty_cells = sum(1 for row in normalized_table for cell in row if cell.strip())
    total_cells = len(normalized_table) * max_cols
    if non_empty_cells < (total_cells * 0.3):
        return None

    # Détection des bordures
    has_borders = detect_table_borders(page, table_settings)

    # Détection d'en-têtes
    has_headers = False
    if len(normalized_table) > 1:
        first_row = normalized_table[0]
        first_row_chars = sum(len(cell) for cell in first_row)
        avg_chars_other_rows = sum(sum(len(cell) for cell in row) for row in normalized_table[1:]) / (
                    len(normalized_table) - 1)
        if first_row_chars > avg_chars_other_rows * 0.7:
            has_headers = True

    # Conversion en CSV
    try:
        if has_headers and len(normalized_table) > 1:
            df = pd.DataFrame(normalized_table[1:], columns=normalized_table[0])
            csv_data = df.to_csv(index=False)
        else:
            df = pd.DataFrame(normalized_table)
            csv_data = df.to_csv(index=False, header=False)
    except Exception as e:
        csv_data = None

    return {
        "table_id": f"page_{page_num}_table_{table_idx + 1}",
        "page": page_num,
        "data": normalized_table,
        "rows": len(normalized_table),
        "columns": max_cols,
        "has_borders": has_borders,
        "has_headers": has_headers,
        "extraction_method": f"pdfplumber_{method}",
        "csv_data": csv_data
    }


def extract_pdf_content(pdf_path, output_img_folder):
    """
    Extraction complète du contenu PDF avec préservation de la position
    et détection améliorée des images et tableaux
    """
    result = {
        "text": "",
        "positioned_text": [],
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
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            if text.strip():
                                page_text += text
                                positioned_chars.append({
                                    "text": text,
                                    "bbox": span["bbox"],
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

            # Extraction des images avec PyMuPDF
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_pil = Image.open(io.BytesIO(image_bytes))
                    image_filename = f"pymupdf_p{page_num + 1}_{img_index + 1}.{image_ext}"
                    image_path = os.path.join(output_img_folder, image_filename)
                    image_pil.save(image_path)
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
                objects = []
                for obj_index in range(page.count_objects()):
                    obj = page.get_object(obj_index)
                    if obj.get_type() == pdfium.FPDF_PAGEOBJ_IMAGE:
                        objects.append((obj_index, obj))
                for img_idx, (obj_index, obj) in enumerate(objects):
                    try:
                        bitmap = obj.get_bitmap()
                        if bitmap:
                            width = bitmap.get_width()
                            height = bitmap.get_height()
                            stride = bitmap.get_stride()
                            buffer = bitmap.get_buffer()
                            image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", stride)
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
                                image_filename = f"pdfium_p{page_num + 1}_{img_idx + 1}.png"
                                image_path = os.path.join(output_img_folder, image_filename)
                                image.save(image_path, "PNG")
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
                                if page_num < len(result["pages"]):
                                    result["pages"][page_num]["images"].append(image_data)
                    except Exception as e:
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
                error_data = {
                    "error": f"Erreur extraction images pypdfium2 page {page_num + 1}: {str(e)}",
                    "page": page_num + 1,
                    "method": "pypdfium2"
                }
                if "extraction_errors" not in result:
                    result["extraction_errors"] = []
                result["extraction_errors"].append(error_data)
    except Exception as e:
        error_data = {
            "error": f"Erreur ouverture PDF pypdfium2 pour extraction images: {str(e)}"
        }
        if "extraction_errors" not in result:
            result["extraction_errors"] = []
        result["extraction_errors"].append(error_data)

    # Extraction des tableaux avec pdfplumber (robuste)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Stratégies : lignes, texte, hybride
                strategies = [
                    ("lines", {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 5,
                               "join_tolerance": 5}),
                    ("text", {"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 10,
                              "join_tolerance": 10}),
                    ("hybrid", {"vertical_strategy": "lines", "horizontal_strategy": "text", "snap_tolerance": 8,
                                "join_tolerance": 8}),
                ]
                tables_found = []
                for method, settings in strategies:
                    try:
                        tables = page.extract_tables(settings)
                        if tables:
                            for table in tables:
                                tables_found.append((method, table, settings))
                    except Exception:
                        continue
                for table_idx, (method, table, settings) in enumerate(tables_found):
                    table_data = clean_and_validate_table(table, page, settings, page_num, table_idx, method)
                    if table_data:
                        result["tables"].append(table_data)
                        if page_num - 1 < len(result["pages"]):
                            result["pages"][page_num - 1]["tables"].append(table_data)
    except Exception as e:
        error_data = {
            "error": f"Erreur extraction tableaux avec pdfplumber: {str(e)}"
        }
        if "extraction_errors" not in result:
            result["extraction_errors"] = []
        result["extraction_errors"].append(error_data)

    # Extraction complémentaire de tableaux avec PyMuPDF (alignement des blocs texte)
    try:
        pdf_doc = fitz.open(pdf_path)
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            text_dict = page.get_text("dict")
            text_blocks = []
            for block in text_dict["blocks"]:
                if "lines" in block:
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
            if text_blocks:
                detected_tables = detect_tables_from_text_blocks(text_blocks, page_num + 1)
                for table_data in detected_tables:
                    already = False
                    for existing in result["tables"]:
                        if (existing["page"] == table_data["page"] and
                                existing["rows"] == table_data["rows"] and
                                existing["columns"] == table_data["columns"] and
                                existing["data"] and table_data["data"] and
                                existing["data"][0] == table_data["data"][0]):
                            already = True
                            break
                    if not already:
                        result["tables"].append(table_data)
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


def detect_table_borders(page, table_settings):
    """
    Détecte si un tableau a des bordures naturelles en analysant les lignes dans le PDF
    """
    try:
        vertical_strategy = table_settings.get("vertical_strategy", "")
        horizontal_strategy = table_settings.get("horizontal_strategy", "")
        if vertical_strategy == "lines" and horizontal_strategy == "lines":
            lines = page.lines
            if lines and len(lines) > 4:
                horizontal_lines = [line for line in lines if
                                    abs(line['x1'] - line['x0']) > abs(line['y1'] - line['y0'])]
                vertical_lines = [line for line in lines if abs(line['y1'] - line['y0']) > abs(line['x1'] - line['x0'])]
                if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
                    return True
        if vertical_strategy == "text" or horizontal_strategy == "text":
            return False
        if vertical_strategy == "lines" or horizontal_strategy == "lines":
            lines = page.lines
            if lines and len(lines) >= 3:
                return True
        return False
    except Exception:
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
            text_dict = page.get_text("dict")
            for block_num, block in enumerate(text_dict["blocks"]):
                if "lines" in block:
                    for line_num, line in enumerate(block["lines"]):
                        for span_num, span in enumerate(line["spans"]):
                            chars = page.get_text("rawdict")
                            for char_data in chars["blocks"]:
                                if "lines" in char_data:
                                    for line_data in char_data["lines"]:
                                        for span_data in line_data["spans"]:
                                            if span_data["bbox"] == span["bbox"]:
                                                text = span_data["text"]
                                                for i, char in enumerate(text):
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


def detect_tables_from_text_blocks(text_blocks, page_num):
    """
    Détecte les tableaux basés sur l'alignement et la position des blocs de texte
    """
    if not text_blocks or len(text_blocks) < 4:
        return []
    text_blocks.sort(key=lambda b: (round(b["y0"], 1), round(b["x0"], 1)))
    lines = []
    current_line = []
    current_y = None
    y_tolerance = 5
    for block in text_blocks:
        if current_y is None or abs(block["y0"] - current_y) <= y_tolerance:
            current_line.append(block)
            current_y = block["y0"] if current_y is None else current_y
        else:
            if len(current_line) >= 2:
                lines.append(sorted(current_line, key=lambda b: b["x0"]))
            current_line = [block]
            current_y = block["y0"]
    if len(current_line) >= 2:
        lines.append(sorted(current_line, key=lambda b: b["x0"]))
    if len(lines) < 2:
        return []
    detected_tables = []
    if len(lines) >= 2:
        col_counts = {}
        for line in lines:
            count = len(line)
            col_counts[count] = col_counts.get(count, 0) + 1
        most_common_cols = max([k for k in col_counts.keys() if k >= 2], default=0)
        if most_common_cols >= 2:
            table_lines = []
            for line in lines:
                if abs(len(line) - most_common_cols) <= 1:
                    if len(line) < most_common_cols:
                        while len(line) < most_common_cols:
                            line.append({"text": "", "x0": line[-1]["x1"], "y0": line[-1]["y0"],
                                         "x1": line[-1]["x1"], "y1": line[-1]["y1"],
                                         "font_size": line[-1]["font_size"]})
                    elif len(line) > most_common_cols:
                        line = line[:most_common_cols]
                    table_lines.append(line)
            if len(table_lines) >= 2:
                column_positions = []
                for col_idx in range(most_common_cols):
                    positions = []
                    for line in table_lines:
                        if col_idx < len(line):
                            positions.append(line[col_idx]["x0"])
                    if positions:
                        avg_pos = sum(positions) / len(positions)
                        max_deviation = max(abs(pos - avg_pos) for pos in positions)
                        if max_deviation <= 20:
                            column_positions.append(avg_pos)
                if len(column_positions) >= 2:
                    table_data = []
                    for line in table_lines:
                        row = []
                        for col_idx in range(most_common_cols):
                            if col_idx < len(line):
                                row.append(line[col_idx]["text"])
                            else:
                                row.append("")
                        table_data.append(row)
                    non_empty_cells = sum(1 for row in table_data for cell in row if cell.strip())
                    total_cells = len(table_data) * most_common_cols
                    if non_empty_cells >= (total_cells * 0.4):
                        has_headers = False
                        if len(table_data) > 1:
                            first_row_chars = sum(len(cell) for cell in table_data[0])
                            if len(table_data) > 1:
                                avg_other_rows = sum(sum(len(cell) for cell in row) for row in table_data[1:]) / (
                                            len(table_data) - 1)
                                if first_row_chars > avg_other_rows * 0.7:
                                    has_headers = True
                        table_info = {
                            "table_id": f"page_{page_num}_pymupdf_table_{len(detected_tables) + 1}",
                            "page": page_num,
                            "data": table_data,
                            "rows": len(table_data),
                            "columns": most_common_cols,
                            "has_headers": has_headers,
                            "has_borders": False,
                            "extraction_method": "PyMuPDF_position"
                        }
                        try:
                            if has_headers and len(table_data) > 1:
                                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                                table_info["csv_data"] = df.to_csv(index=False)
                            else:
                                df = pd.DataFrame(table_data)
                                table_info["csv_data"] = df.to_csv(index=False, header=False)
                        except Exception as e:
                            table_info["conversion_error"] = str(e)
                        detected_tables.append(table_info)
    return detected_tables