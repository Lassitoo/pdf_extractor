# Extracteur PDF Intelligent

Une application Django moderne pour extraire le contenu des documents PDF (texte, tableaux et images) avec une interface utilisateur élégante et des fonctionnalités avancées.

## ✨ Fonctionnalités

- **Extraction complète** : Texte, tableaux et images de vos documents PDF
- **Interface moderne** : Upload par glisser-déposer avec affichage en temps réel
- **Traitement structuré** : Organisation du contenu par pages avec métadonnées détaillées
- **Tableaux intelligents** : Conversion automatique en CSV avec détection des en-têtes
- **Images haute qualité** : Extraction et sauvegarde au format PNG
- **API AJAX** : Traitement asynchrone sans rechargement de page
- **Responsive** : Interface adaptée à tous les appareils

## 🚀 Technologies

- **Backend** : Django 5.2.4
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Extraction PDF** : 
  - `pdfplumber` pour le texte et les tableaux
  - `pypdfium2` pour les images
- **Traitement d'images** : Pillow
- **Analyse de données** : Pandas
- **Base de données** : SQLite (par défaut)

## 📋 Prérequis

- Python 3.8+
- pip

## 🛠️ Installation

1. **Cloner le projet**
```bash
git clone <votre-repo>
cd pdf_extractor
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurer la base de données**
```bash
python manage.py migrate
```

4. **Lancer le serveur**
```bash
python manage.py runserver
```

5. **Accéder à l'application**
Ouvrez votre navigateur à l'adresse : `http://localhost:8000`

## 📁 Structure du projet

```
pdf_extractor/
├── extractor/                 # Application principale
│   ├── models.py             # Modèles de données
│   ├── views.py              # Vues et API endpoints
│   ├── utils.py              # Logique d'extraction PDF
│   ├── urls.py               # Configuration des URLs
│   └── templates/            # Templates HTML
├── static/                   # Fichiers statiques
│   ├── css/
│   │   └── style.css        # Styles modernes
│   └── js/
│       └── app.js           # JavaScript pour l'interface
├── media/                    # Fichiers uploadés et extraits
│   ├── pdfs/                # PDFs uploadés
│   └── extracted_images/    # Images extraites
├── requirements.txt          # Dépendances Python
└── manage.py                # Script de gestion Django
```

## 🎯 Utilisation

### Interface Web

1. **Upload** : Glissez-déposez un PDF ou cliquez pour le sélectionner
2. **Traitement** : L'extraction se lance automatiquement
3. **Résultats** : Naviguez entre les onglets pour voir :
   - **Texte** : Contenu textuel organisé par page
   - **Tableaux** : Tableaux structurés avec possibilité d'export CSV
   - **Images** : Galerie des images extraites avec métadonnées

### API Endpoints

#### POST `/process/`
Traite un fichier PDF et retourne les résultats d'extraction.

**Request:**
```javascript
FormData avec 'pdf_file'
```

**Response:**
```json
{
  "success": true,
  "document_id": 1,
  "results": {
    "text": "...",
    "tables": [...],
    "images": [...],
    "metadata": {...},
    "pages": [...]
  }
}
```

#### GET `/results/<int:document_id>/`
Récupère les résultats d'extraction d'un document.

## 📊 Format des données

### Métadonnées du document
```json
{
  "total_pages": 10,
  "extraction_date": "2024-01-15T10:30:00",
  "file_size": 1024000,
  "total_images": 5,
  "total_tables": 3,
  "total_text_length": 15000
}
```

### Structure des tableaux
```json
{
  "table_id": "page_1_table_1",
  "page": 1,
  "data": [["Header1", "Header2"], ["Cell1", "Cell2"]],
  "rows": 2,
  "columns": 2,
  "has_headers": true,
  "csv_data": "Header1,Header2\nCell1,Cell2"
}
```

### Informations des images
```json
{
  "image_id": "page_1_image_1",
  "filename": "image_p1_1.png",
  "path": "/media/extracted_images/1/image_p1_1.png",
  "page": 1,
  "format": "png",
  "width": 800,
  "height": 600,
  "size_bytes": 45000,
  "mode": "RGBA"
}
```

## 🎨 Personnalisation

### Styles CSS
Modifiez `static/css/style.css` pour personnaliser l'apparence :
- Variables CSS pour les couleurs
- Animations et transitions
- Responsive design

### Configuration Django
Ajustez `pdf_extractor/settings.py` pour :
- Changer la base de données
- Configurer les fichiers media
- Modifier les paramètres de sécurité

## 🔧 Développement

### Ajouter de nouvelles fonctionnalités

1. **Nouvelles méthodes d'extraction** : Modifiez `extractor/utils.py`
2. **API endpoints** : Ajoutez des vues dans `extractor/views.py`
3. **Interface utilisateur** : Étendez `static/js/app.js`

### Tests

```bash
python manage.py test
```

## 📝 Notes techniques

- **Gestion des erreurs** : Robuste avec logging des erreurs d'extraction
- **Performance** : Traitement asynchrone pour les gros fichiers
- **Sécurité** : Validation des types de fichiers et CSRF protection
- **Stockage** : Les résultats sont sauvegardés en base pour consultation ultérieure

## 🐛 Dépannage

### Erreurs communes

1. **Module non trouvé** : Vérifiez que toutes les dépendances sont installées
2. **Erreur de permission** : Assurez-vous que Django peut écrire dans `media/`
3. **PDF corrompu** : L'application gère gracieusement les fichiers défectueux

### Logs
Consultez les logs Django pour plus de détails sur les erreurs.

## 🤝 Contribution

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Commit vos changements
4. Push vers la branche
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [pdfplumber](https://github.com/jsvine/pdfplumber) pour l'extraction de texte et tableaux
- [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) pour l'extraction d'images
- [Django](https://www.djangoproject.com/) pour le framework web
- [Pillow](https://python-pillow.org/) pour le traitement d'images