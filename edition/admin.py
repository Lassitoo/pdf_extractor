from django.contrib import admin
from .models import PDFDocument

@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'filename', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['title', 'pdf_file']
    readonly_fields = ['uploaded_at']
    
    def filename(self, obj):
        return obj.filename
    filename.short_description = 'Nom du fichier'
