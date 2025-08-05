document.addEventListener('DOMContentLoaded', function() {
    // Éléments du DOM
    const uploadSection = document.getElementById('upload-section');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('pdf-file');
    const fileInputWrapper = document.querySelector('.file-input-wrapper');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const resultsSection = document.getElementById('results-section');
    const errorAlert = document.getElementById('error-alert');
    
    let selectedFile = null;

    // Gestion du drag & drop
    uploadSection.addEventListener('dragover', handleDragOver);
    uploadSection.addEventListener('dragleave', handleDragLeave);
    uploadSection.addEventListener('drop', handleDrop);

    // Gestion du changement de fichier
    fileInput.addEventListener('change', handleFileSelect);

    // Gestion du formulaire
    uploadForm.addEventListener('submit', handleFormSubmit);

    function handleDragOver(e) {
        e.preventDefault();
        uploadSection.classList.add('dragover');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        uploadSection.classList.remove('dragover');
    }

    function handleDrop(e) {
        e.preventDefault();
        uploadSection.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                fileInput.files = files;
                handleFileSelect({ target: { files: [file] } });
            } else {
                showError('Veuillez sélectionner un fichier PDF.');
            }
        }
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            selectedFile = file;
            updateFileInfo(file);
            uploadBtn.classList.add('show');
        }
    }

    function updateFileInfo(file) {
        const fileInfo = document.querySelector('.file-info');
        const sizeKB = Math.round(file.size / 1024);
        fileInfo.innerHTML = `
            <strong>Fichier sélectionné:</strong> ${file.name}<br>
            <strong>Taille:</strong> ${sizeKB} KB
        `;
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        
        if (!selectedFile) {
            showError('Veuillez sélectionner un fichier PDF.');
            return;
        }

        uploadPDF();
    }

    function uploadPDF() {
        const formData = new FormData();
        formData.append('pdf_file', selectedFile);

        // Afficher le chargement
        uploadSection.style.display = 'none';
        loading.style.display = 'block';
        hideError();

        // Envoyer la requête AJAX
        fetch('/process/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            
            if (data.success) {
                displayResults(data.results);
                uploadSection.style.display = 'block';
                resetForm();
            } else {
                showError(data.error || 'Une erreur est survenue lors du traitement du PDF.');
                uploadSection.style.display = 'block';
            }
        })
        .catch(error => {
            loading.style.display = 'none';
            uploadSection.style.display = 'block';
            showError('Erreur de connexion. Veuillez réessayer.');
            console.error('Error:', error);
        });
    }

    function displayResults(results) {
        // Afficher la section des résultats
        resultsSection.style.display = 'block';
        resultsSection.classList.add('show');

        // Mettre à jour les statistiques
        updateResultsStats(results);

        // Initialiser les onglets
        initializeTabs();

        // Afficher le contenu de chaque onglet
        displayTextContent(results.text);
        displayTablesContent(results.tables);
        displayImagesContent(results.images);

        // Scroll vers les résultats
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    function updateResultsStats(results) {
        const metadata = results.metadata || {};
        const statsHTML = `
            <div class="stat-item">
                <span>📄</span>
                <span>${metadata.total_pages || 0} pages</span>
            </div>
            <div class="stat-item">
                <span>📝</span>
                <span>${metadata.total_text_length || 0} caractères</span>
            </div>
            <div class="stat-item">
                <span>📊</span>
                <span>${metadata.total_tables || 0} tableaux</span>
            </div>
            <div class="stat-item">
                <span>🖼️</span>
                <span>${metadata.total_images || 0} images</span>
            </div>
        `;
        document.querySelector('.results-stats').innerHTML = statsHTML;
    }

    function initializeTabs() {
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Désactiver tous les onglets
                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(tc => tc.classList.remove('active'));

                // Activer l'onglet cliqué
                tab.classList.add('active');
                const targetContent = document.getElementById(tab.dataset.tab);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });

        // Activer le premier onglet par défaut
        if (tabs.length > 0) {
            tabs[0].click();
        }
    }

    function displayTextContent(text) {
        const textContainer = document.getElementById('text-content');
        if (text && text.trim()) {
            textContainer.innerHTML = `<div class="text-content">${escapeHtml(text)}</div>`;
        } else {
            textContainer.innerHTML = '<div class="alert alert-warning">Aucun texte extrait de ce PDF.</div>';
        }
    }

    function displayTablesContent(tables) {
        const tablesContainer = document.getElementById('tables-content');
        
        if (!tables || tables.length === 0) {
            tablesContainer.innerHTML = '<div class="alert alert-warning">Aucun tableau trouvé dans ce PDF.</div>';
            return;
        }

        const tablesHTML = tables.map(table => {
            const tableHTML = generateTableHTML(table);
            return `
                <div class="table-container">
                    <div class="table-header">
                        <div>
                            <div class="table-title">${table.table_id}</div>
                            <div class="table-meta">
                                Page ${table.page} • ${table.rows} lignes × ${table.columns} colonnes
                            </div>
                        </div>
                    </div>
                    <div class="table-wrapper">
                        ${tableHTML}
                    </div>
                </div>
            `;
        }).join('');

        tablesContainer.innerHTML = `<div class="tables-section">${tablesHTML}</div>`;
    }

    function generateTableHTML(table) {
        if (!table.data || table.data.length === 0) {
            return '<div class="alert alert-warning">Données de tableau vides</div>';
        }

        const rows = table.data;
        const hasHeaders = table.has_headers;
        
        let tableHTML = '<table class="extracted-table">';
        
        if (hasHeaders && rows.length > 0) {
            tableHTML += '<thead><tr>';
            rows[0].forEach(cell => {
                tableHTML += `<th>${escapeHtml(cell || '')}</th>`;
            });
            tableHTML += '</tr></thead>';
            
            if (rows.length > 1) {
                tableHTML += '<tbody>';
                rows.slice(1).forEach(row => {
                    tableHTML += '<tr>';
                    row.forEach(cell => {
                        tableHTML += `<td>${escapeHtml(cell || '')}</td>`;
                    });
                    tableHTML += '</tr>';
                });
                tableHTML += '</tbody>';
            }
        } else {
            tableHTML += '<tbody>';
            rows.forEach(row => {
                tableHTML += '<tr>';
                row.forEach(cell => {
                    tableHTML += `<td>${escapeHtml(cell || '')}</td>`;
                });
                tableHTML += '</tr>';
            });
            tableHTML += '</tbody>';
        }
        
        tableHTML += '</table>';
        return tableHTML;
    }

    function displayImagesContent(images) {
        const imagesContainer = document.getElementById('images-content');
        
        if (!images || images.length === 0) {
            imagesContainer.innerHTML = '<div class="alert alert-warning">Aucune image trouvée dans ce PDF.</div>';
            return;
        }

        const imagesHTML = images.map(image => {
            const sizeKB = Math.round(image.size_bytes / 1024);
            return `
                <div class="image-container">
                    <div class="image-header">
                        <div class="image-title">
                            ${image.filename}
                            <span class="page-badge">Page ${image.page}</span>
                        </div>
                        <div class="image-meta">
                            <span>${image.width} × ${image.height}px</span>
                            <span>${image.format.toUpperCase()}</span>
                            <span>${sizeKB} KB</span>
                        </div>
                    </div>
                    <div class="image-wrapper">
                        <img src="${image.url}" alt="${image.filename}" class="extracted-image" loading="lazy">
                    </div>
                </div>
            `;
        }).join('');

        imagesContainer.innerHTML = `<div class="images-section">${imagesHTML}</div>`;
    }

    function resetForm() {
        selectedFile = null;
        fileInput.value = '';
        uploadBtn.classList.remove('show');
        document.querySelector('.file-info').innerHTML = 'Format PDF uniquement, taille maximale 10MB';
    }

    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
        setTimeout(() => {
            errorAlert.style.display = 'none';
        }, 5000);
    }

    function hideError() {
        errorAlert.style.display = 'none';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});