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
    let currentDocumentId = null;

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
                currentDocumentId = data.document_id;
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

        // Afficher le bouton de conversion
        showConvertButton();

        // Initialiser les onglets
        initializeTabs();

        // Afficher le contenu de chaque onglet
        displayTextContent(results.text);
        displayPositionedContent(results.positioned_text, results.pages);
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
                <span>📍</span>
                <span>${metadata.total_positioned_elements || 0} éléments positionnels</span>
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
            textContainer.innerHTML = `
                <div class="content-header">
                    <h3>Texte extrait (éditable)</h3>
                    <div class="content-actions">
                        <button class="btn-secondary" onclick="copyToClipboard('text-content-area')">📋 Copier</button>
                        <button class="btn-secondary" onclick="downloadText('text-content-area', 'extracted-text.txt')">💾 Télécharger</button>
                    </div>
                </div>
                <div class="text-content">
                    <textarea id="text-content-area" class="editable-text">${escapeHtml(text)}</textarea>
                </div>
            `;
        } else {
            textContainer.innerHTML = '<div class="alert alert-warning">Aucun texte extrait de ce PDF.</div>';
        }
    }

    function displayPositionedContent(positionedText, pages) {
        const positionedContainer = document.getElementById('positioned-content');
        
        if (!positionedText || positionedText.length === 0) {
            positionedContainer.innerHTML = '<div class="alert alert-warning">Aucun contenu positionnel trouvé dans ce PDF.</div>';
            return;
        }

        // Grouper le contenu par page
        const pageGroups = {};
        positionedText.forEach(item => {
            const pageNum = findPageForElement(item, pages);
            if (!pageGroups[pageNum]) {
                pageGroups[pageNum] = [];
            }
            pageGroups[pageNum].push(item);
        });

        let positionedHTML = `
            <div class="content-header">
                <h3>Contenu avec positions (éditable)</h3>
                <div class="content-actions">
                    <button class="btn-secondary" onclick="togglePositionView()">🎯 Basculer vue</button>
                    <button class="btn-secondary" onclick="exportPositionedData()">📊 Exporter données</button>
                </div>
            </div>
            <div class="positioned-content-wrapper">
        `;

        // Afficher chaque page
        Object.keys(pageGroups).sort((a, b) => a - b).forEach(pageNum => {
            const pageElements = pageGroups[pageNum];
            
            positionedHTML += `
                <div class="positioned-page" data-page="${pageNum}">
                    <div class="page-header">
                        <h4>Page ${pageNum}</h4>
                        <span class="element-count">${pageElements.length} éléments</span>
                    </div>
                    <div class="positioned-elements" id="positioned-view-${pageNum}">
            `;

            // Afficher les éléments avec leur position
            pageElements.forEach((element, index) => {
                const elementId = `pos-element-${pageNum}-${index}`;
                positionedHTML += `
                    <div class="positioned-element" 
                         data-element-id="${elementId}"
                         data-bbox="${JSON.stringify(element.bbox)}"
                         data-font="${element.font}"
                         data-size="${element.size}">
                        <div class="element-info">
                            <span class="position-info">x:${Math.round(element.bbox[0])}, y:${Math.round(element.bbox[1])}</span>
                            <span class="font-info">${element.font} ${element.size}pt</span>
                        </div>
                        <div class="element-text" contenteditable="true" 
                             onblur="updateElementText('${elementId}', this.textContent)">${escapeHtml(element.text)}</div>
                    </div>
                `;
            });

            positionedHTML += `
                    </div>
                </div>
            `;
        });

        positionedHTML += '</div>';
        positionedContainer.innerHTML = positionedHTML;
    }

    function findPageForElement(element, pages) {
        // Trouver la page correspondante basée sur les données disponibles
        if (element.page) return element.page;
        
        // Si pas de page directe, chercher dans les pages
        for (let i = 0; i < pages.length; i++) {
            const page = pages[i];
            if (page.positioned_text && page.positioned_text.includes(element)) {
                return i + 1;
            }
        }
        return 1; // Par défaut page 1
    }

    function displayTablesContent(tables) {
        const tablesContainer = document.getElementById('tables-content');
        
        if (!tables || tables.length === 0) {
            tablesContainer.innerHTML = '<div class="alert alert-warning">Aucun tableau trouvé dans ce PDF.</div>';
            return;
        }

        const tablesHTML = tables.map(table => {
            const tableHTML = generateTableHTML(table);
            const hasBorders = table.has_borders !== false;
            const borderIndicator = hasBorders ? "🔲 Avec bordures" : "📄 Sans bordures";
            
            return `
                <div class="table-container">
                    <div class="table-header">
                        <div>
                            <div class="table-title">${table.table_id} (éditable)</div>
                            <div class="table-meta">
                                Page ${table.page} • ${table.rows} lignes × ${table.columns} colonnes • ${borderIndicator}
                            </div>
                        </div>
                        <div class="content-actions">
                            <button class="btn-secondary" onclick="exportTableData('${table.table_id}')">📊 Exporter CSV</button>
                            <button class="btn-secondary" onclick="copyTableData('${table.table_id}')">📋 Copier</button>
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
        const hasBorders = table.has_borders !== false; // Par défaut, on assume qu'il y a des bordures
        
        // Classe CSS différente selon la présence de bordures
        const tableClass = hasBorders ? "extracted-table with-borders" : "extracted-table no-borders";
        
        let tableHTML = `<table class="${tableClass}" data-table-id="${table.table_id}" data-has-borders="${hasBorders}">`;
        
        if (hasHeaders && rows.length > 0) {
            tableHTML += '<thead><tr>';
            rows[0].forEach((cell, index) => {
                tableHTML += `<th contenteditable="true" data-row="0" data-col="${index}" onblur="updateTableCell('${table.table_id}', 0, ${index}, this.textContent)">${escapeHtml(cell || '')}</th>`;
            });
            tableHTML += '</tr></thead>';
            
            if (rows.length > 1) {
                tableHTML += '<tbody>';
                rows.slice(1).forEach((row, rowIndex) => {
                    tableHTML += '<tr>';
                    row.forEach((cell, colIndex) => {
                        tableHTML += `<td contenteditable="true" data-row="${rowIndex + 1}" data-col="${colIndex}" onblur="updateTableCell('${table.table_id}', ${rowIndex + 1}, ${colIndex}, this.textContent)">${escapeHtml(cell || '')}</td>`;
                    });
                    tableHTML += '</tr>';
                });
                tableHTML += '</tbody>';
            }
        } else {
            tableHTML += '<tbody>';
            rows.forEach((row, rowIndex) => {
                tableHTML += '<tr>';
                row.forEach((cell, colIndex) => {
                    tableHTML += `<td contenteditable="true" data-row="${rowIndex}" data-col="${colIndex}" onblur="updateTableCell('${table.table_id}', ${rowIndex}, ${colIndex}, this.textContent)">${escapeHtml(cell || '')}</td>`;
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

    // Fonctions utilitaires globales
    window.copyToClipboard = function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.select();
            document.execCommand('copy');
            showNotification('Contenu copié dans le presse-papiers!');
        }
    };

    window.downloadText = function(elementId, filename) {
        const element = document.getElementById(elementId);
        if (element) {
            const text = element.value || element.textContent;
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showNotification('Fichier téléchargé!');
        }
    };

    window.updateElementText = function(elementId, newText) {
        // Mettre à jour le texte d'un élément positionnel
        console.log(`Mise à jour de l'élément ${elementId}: ${newText}`);
        showNotification('Texte mis à jour!');
    };

    window.togglePositionView = function() {
        const wrapper = document.querySelector('.positioned-content-wrapper');
        if (wrapper) {
            wrapper.classList.toggle('visual-layout');
            const button = event.target;
            if (wrapper.classList.contains('visual-layout')) {
                button.textContent = '📝 Vue liste';
            } else {
                button.textContent = '🎯 Vue visuelle';
            }
        }
    };

    window.exportPositionedData = function() {
        const positionedElements = document.querySelectorAll('.positioned-element');
        const data = [];
        
        positionedElements.forEach(element => {
            const bbox = JSON.parse(element.dataset.bbox || '[]');
            const text = element.querySelector('.element-text').textContent;
            const font = element.dataset.font;
            const size = element.dataset.size;
            
            data.push({
                text: text,
                x: bbox[0],
                y: bbox[1],
                width: bbox[2] - bbox[0],
                height: bbox[3] - bbox[1],
                font: font,
                size: size
            });
        });
        
        const jsonData = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'positioned-data.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification('Données positionnelles exportées!');
    };

    window.updateTableCell = function(tableId, row, col, newValue) {
        // Mettre à jour une cellule de tableau
        console.log(`Mise à jour cellule ${tableId} [${row}, ${col}]: ${newValue}`);
        showNotification('Cellule mise à jour!');
    };

    window.exportTableData = function(tableId) {
        const table = document.querySelector(`table[data-table-id="${tableId}"]`);
        if (!table) return;

        const rows = [];
        const headerRows = table.querySelectorAll('thead tr');
        const bodyRows = table.querySelectorAll('tbody tr');

        // Collecter les en-têtes
        headerRows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('th')).map(cell => cell.textContent.trim());
            rows.push(cells);
        });

        // Collecter les données
        bodyRows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td')).map(cell => cell.textContent.trim());
            rows.push(cells);
        });

        // Convertir en CSV
        const csvContent = rows.map(row => 
            row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')
        ).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${tableId}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification('Tableau exporté en CSV!');
    };

    window.copyTableData = function(tableId) {
        const table = document.querySelector(`table[data-table-id="${tableId}"]`);
        if (!table) return;

        const rows = [];
        const headerRows = table.querySelectorAll('thead tr');
        const bodyRows = table.querySelectorAll('tbody tr');

        // Collecter toutes les lignes
        [...headerRows, ...bodyRows].forEach(row => {
            const cells = Array.from(row.querySelectorAll('th, td')).map(cell => cell.textContent.trim());
            rows.push(cells.join('\t'));
        });

        const textContent = rows.join('\n');
        
        // Copier dans le presse-papiers
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(textContent).then(() => {
                showNotification('Tableau copié dans le presse-papiers!');
            });
        } else {
            // Fallback pour les navigateurs plus anciens
            const textArea = document.createElement('textarea');
            textArea.value = textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('Tableau copié dans le presse-papiers!');
        }
    };

    function showNotification(message) {
        // Créer une notification temporaire
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 10000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 2000);
    }

    // Fonctions pour la conversion PDF vers Word
    function showConvertButton() {
        const convertBtn = document.getElementById('convert-to-word-btn');
        if (convertBtn && currentDocumentId) {
            convertBtn.style.display = 'inline-block';
            convertBtn.onclick = handleConvertToWord;
        }
    }

    function handleConvertToWord() {
        if (!currentDocumentId) {
            showError('Aucun document disponible pour la conversion');
            return;
        }

        const convertBtn = document.getElementById('convert-to-word-btn');
        const statusDiv = document.getElementById('conversion-status');
        
        // Afficher le statut de chargement
        convertBtn.disabled = true;
        convertBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Conversion...';
        statusDiv.style.display = 'block';
        statusDiv.className = 'conversion-status loading';
        statusDiv.textContent = 'Conversion en cours...';

        // Appel à l'API de conversion
        fetch(`/convert-to-word/${currentDocumentId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            convertBtn.disabled = false;
            convertBtn.innerHTML = '<i class="fas fa-file-word me-1"></i>Convertir en Word';

            if (data.success) {
                statusDiv.className = 'conversion-status success';
                statusDiv.innerHTML = `
                    <i class="fas fa-check-circle me-1"></i>
                    Conversion réussie ! 
                    <a href="${data.download_url}" download="${data.word_filename}" class="ms-2">
                        <i class="fas fa-download"></i> Télécharger le fichier Word
                    </a>
                `;
                
                // Afficher une notification de succès
                showNotification('Document converti avec succès en format Word !', 'success');
                
            } else {
                statusDiv.className = 'conversion-status error';
                statusDiv.innerHTML = `
                    <i class="fas fa-exclamation-circle me-1"></i>
                    Erreur: ${data.error}
                `;
                showError(data.error || 'Erreur lors de la conversion');
            }
        })
        .catch(error => {
            convertBtn.disabled = false;
            convertBtn.innerHTML = '<i class="fas fa-file-word me-1"></i>Convertir en Word';
            
            statusDiv.className = 'conversion-status error';
            statusDiv.innerHTML = `
                <i class="fas fa-exclamation-circle me-1"></i>
                Erreur de connexion lors de la conversion
            `;
            showError('Erreur de connexion lors de la conversion');
            console.error('Conversion error:', error);
        });
    }
});