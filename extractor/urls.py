from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_pdf, name='upload_pdf'),
    path('process/', views.process_pdf, name='process_pdf'),
    path('results/<int:document_id>/', views.get_document_results, name='get_document_results'),
    path('convert-to-word/<int:document_id>/', views.convert_to_word, name='convert_to_word'),
]
