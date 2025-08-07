from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from .models import PDFDocument
import json
import os

# Create your views here.

def upload_pdf(request):
    """Vue pour uploader un PDF"""
    if request.method == 'POST':
        if 'pdf_file' not in request.FILES:
            messages.error(request, 'Aucun fichier sélectionné')
            return render(request, 'edition/upload.html')
        
        pdf_file = request.FILES['pdf_file']
        title = request.POST.get('title', pdf_file.name)
        
        # Vérifier que c'est bien un PDF
        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, 'Veuillez sélectionner un fichier PDF')
            return render(request, 'edition/upload.html')
        
        # Créer le document
        document = PDFDocument.objects.create(
            title=title,
            pdf_file=pdf_file,
            uploaded_by=request.user if request.user.is_authenticated else None
        )
        
        messages.success(request, 'PDF uploadé avec succès!')
        return redirect('edition:view_pdf', document_id=document.id)
    
    return render(request, 'edition/upload.html')

def view_pdf(request, document_id):
    """Vue pour afficher et éditer un PDF"""
    document = get_object_or_404(PDFDocument, id=document_id)
    return render(request, 'edition/view_pdf.html', {'document': document})

def list_pdfs(request):
    """Vue pour lister tous les PDFs"""
    documents = PDFDocument.objects.all()
    return render(request, 'edition/list_pdfs.html', {'documents': documents})

@csrf_exempt
def save_pdf_annotations(request, document_id):
    """Vue pour sauvegarder les annotations du PDF"""
    if request.method == 'POST':
        document = get_object_or_404(PDFDocument, id=document_id)
        try:
            data = json.loads(request.body)
            annotations = data.get('annotations', [])
            
            # Ici vous pouvez sauvegarder les annotations
            # Pour l'instant, on retourne juste une réponse de succès
            return JsonResponse({'status': 'success', 'message': 'Annotations sauvegardées'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Données invalides'})
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})
