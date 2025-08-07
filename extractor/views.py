from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from .models import PDFDocument
from .utils import extract_pdf_content, convert_pdf_to_word
import os
import json
from datetime import datetime

def upload_pdf(request):
    """Vue principale pour l'upload et l'affichage"""
    return render(request, 'extractor/index.html')

@require_http_methods(["POST"])
def process_pdf(request):
    """API endpoint pour traiter le PDF en AJAX"""
    if 'pdf_file' not in request.FILES:
        return JsonResponse({
            'success': False, 
            'error': 'Aucun fichier PDF fourni'
        }, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validation du type de fichier
    if not pdf_file.name.lower().endswith('.pdf'):
        return JsonResponse({
            'success': False, 
            'error': 'Le fichier doit être un PDF'
        }, status=400)
    
    try:
        # Créer le document avec métadonnées
        document = PDFDocument.objects.create(
            file=pdf_file,
            original_filename=pdf_file.name,
            file_size=pdf_file.size
        )
        
        # Chemin vers le fichier PDF
        pdf_path = document.file.path
        
        # Dossier de sortie pour les images
        output_folder = os.path.join('media', 'extracted_images', str(document.id))
        
        # Extraction du contenu
        extraction_results = extract_pdf_content(pdf_path, output_folder)
        
        # Sauvegarder les résultats dans le modèle
        document.extraction_results = extraction_results
        document.extraction_completed = True
        document.extraction_date = datetime.now()
        document.save()
        
        # Préparer la réponse avec URLs relatives pour les images
        response_data = extraction_results.copy()
        
        # Convertir les chemins d'images en URLs accessibles
        for image in response_data.get('images', []):
            # Convertir le chemin absolu en URL relative
            relative_path = image['path'].replace(os.getcwd() + '/', '')
            image['url'] = '/' + relative_path.replace('\\', '/')
        
        # Ajouter les URLs aux pages aussi
        for page in response_data.get('pages', []):
            if 'images' in page:
                for image in page['images']:
                    relative_path = image['path'].replace(os.getcwd() + '/', '')
                    image['url'] = '/' + relative_path.replace('\\', '/')
        
        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'results': response_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors du traitement du PDF: {str(e)}'
        }, status=500)

def get_document_results(request, document_id):
    """API endpoint pour récupérer les résultats d'un document"""
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        if not document.extraction_completed:
            return JsonResponse({
                'success': False,
                'error': 'L\'extraction n\'est pas encore terminée'
            }, status=404)
        
        response_data = document.extraction_results.copy()
        
        # Convertir les chemins d'images en URLs accessibles
        for image in response_data.get('images', []):
            relative_path = image['path'].replace(os.getcwd() + '/', '')
            image['url'] = '/' + relative_path.replace('\\', '/')
        
        for page in response_data.get('pages', []):
            if 'images' in page:
                for image in page['images']:
                    relative_path = image['path'].replace(os.getcwd() + '/', '')
                    image['url'] = '/' + relative_path.replace('\\', '/')
        
        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'results': response_data
        })
        
    except PDFDocument.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document non trouvé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def convert_to_word(request, document_id):
    """API endpoint pour convertir un PDF déjà traité en document Word"""
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        if not document.extraction_completed:
            return JsonResponse({
                'success': False,
                'error': 'L\'extraction du PDF n\'est pas encore terminée'
            }, status=400)
        
        # Chemin vers le fichier PDF
        pdf_path = document.file.path
        
        # Dossier de sortie pour le document Word
        output_folder = os.path.join('media', 'converted_documents', str(document.id))
        
        # Conversion PDF vers Word
        conversion_results = convert_pdf_to_word(pdf_path, output_folder)
        
        if not conversion_results.get('success'):
            return JsonResponse({
                'success': False,
                'error': conversion_results.get('error', 'Erreur inconnue lors de la conversion')
            }, status=500)
        
        # Convertir le chemin absolu en URL relative pour le téléchargement
        word_path = conversion_results['word_path']
        relative_path = word_path.replace(os.getcwd() + '/', '')
        download_url = '/' + relative_path.replace('\\', '/')
        
        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'word_filename': conversion_results['word_filename'],
            'download_url': download_url,
            'file_size': conversion_results['file_size'],
            'pages_converted': conversion_results['pages_converted'],
            'tables_converted': conversion_results['tables_converted'],
            'images_converted': conversion_results['images_converted'],
            'conversion_date': conversion_results['conversion_date']
        })
        
    except PDFDocument.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document non trouvé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la conversion: {str(e)}'
        }, status=500)
