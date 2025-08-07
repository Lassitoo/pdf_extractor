from django.urls import path
from . import views

app_name = 'edition'

urlpatterns = [
    path('', views.list_pdfs, name='list_pdfs'),
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('view/<int:document_id>/', views.view_pdf, name='view_pdf'),
    path('save-annotations/<int:document_id>/', views.save_pdf_annotations, name='save_annotations'),
]