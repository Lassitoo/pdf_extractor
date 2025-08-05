from django.db import models
import json

class PDFDocument(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Résultats d'extraction stockés en JSON
    extraction_results = models.JSONField(null=True, blank=True)
    extraction_completed = models.BooleanField(default=False)
    extraction_date = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées du fichier
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"PDF Document {self.id} - {self.original_filename or self.file.name}"
    
    @property
    def has_text(self):
        if not self.extraction_results:
            return False
        return bool(self.extraction_results.get('text', '').strip())
    
    @property
    def has_tables(self):
        if not self.extraction_results:
            return False
        return len(self.extraction_results.get('tables', [])) > 0
    
    @property
    def has_images(self):
        if not self.extraction_results:
            return False
        return len(self.extraction_results.get('images', [])) > 0
    
    @property
    def total_pages(self):
        if not self.extraction_results:
            return 0
        return self.extraction_results.get('metadata', {}).get('total_pages', 0)
    
    def get_page_data(self, page_number):
        """Retourne les données d'une page spécifique"""
        if not self.extraction_results:
            return None
        pages = self.extraction_results.get('pages', [])
        for page in pages:
            if page.get('page_number') == page_number:
                return page
        return None
