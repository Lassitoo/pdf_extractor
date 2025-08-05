from django.shortcuts import render
from .models import PDFDocument
from .utils import extract_pdf_content
import os

def upload_pdf(request):
    if request.method == 'POST' and request.FILES['pdf_file']:
        pdf_file = request.FILES['pdf_file']
        document = PDFDocument.objects.create(file=pdf_file)
        pdf_path = document.file.path
        output_folder = os.path.join('media', 'extracted_images', str(document.id))
        content = extract_pdf_content(pdf_path, output_folder)
        return render(request, 'extractor/result.html', {
            'content': content,
            'document': document
        })
    return render(request, 'extractor/index.html')
