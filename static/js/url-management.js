// URL Management JavaScript

// Confirmation dialog for delete operations
function confirmDelete(urlName, url) {
    const message = `Are you sure you want to delete "${urlName}"?\n\nURL: ${url}\n\nThis action cannot be undone.`;
    return confirm(message);
}

// Form validation for edit form
function validateEditForm() {
    const nameInput = document.getElementById('name');
    const urlInput = document.getElementById('url');
    
    if (!nameInput.value.trim()) {
        alert('URL Name is required.');
        nameInput.focus();
        return false;
    }
    
    if (!urlInput.value.trim()) {
        alert('Finviz URL is required.');
        urlInput.focus();
        return false;
    }
    
    // Basic URL validation
    if (!urlInput.value.includes('finviz.com/screener.ashx')) {
        alert('Please enter a valid Finviz screener URL.');
        urlInput.focus();
        return false;
    }
    
    return true;
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add confirmation to delete links
    const deleteLinks = document.querySelectorAll('.btn-delete');
    deleteLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const urlName = this.getAttribute('data-url-name');
            const url = this.getAttribute('data-url');
            
            if (!confirmDelete(urlName, url)) {
                e.preventDefault();
            }
        });
    });
    
    // Add validation to edit form
    const editForm = document.querySelector('.edit-form');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            if (!validateEditForm()) {
                e.preventDefault();
            }
        });
    }
    
    // Add tooltip functionality
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = this.getAttribute('data-tooltip');
            if (tooltip) {
                this.title = tooltip;
            }
        });
    });
}); 