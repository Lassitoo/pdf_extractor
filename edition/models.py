from django.db import models
from django.contrib.auth.models import User
import os

def pdf_upload_path(instance, filename):
    """Générer le chemin d'upload pour les PDFs"""
    return f'pdfs/edition/{filename}'

class PDFDocument(models.Model):
    title = models.CharField(max_length=255, verbose_name="Titre")
    pdf_file = models.FileField(upload_to=pdf_upload_path, verbose_name="Fichier PDF")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'upload")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Uploadé par")
    
    class Meta:
        verbose_name = "Document PDF"
        verbose_name_plural = "Documents PDF"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title
    
    @property
    def filename(self):
        return os.path.basename(self.pdf_file.name)
