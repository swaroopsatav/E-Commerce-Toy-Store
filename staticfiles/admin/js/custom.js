// Custom JavaScript for admin interface

// Image preview functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle image uploads
    const imageInputs = document.querySelectorAll('input[type="file"][name$="-image"]');
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const preview = this.closest('.form-row').querySelector('.image-preview');
            if (preview) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    }
                    reader.readAsDataURL(file);
                }
            }
        });
    });

    // Category hierarchy display
    function updateCategoryHierarchy() {
        const categorySelects = document.querySelectorAll('select[name$="-parent"]');
        categorySelects.forEach(select => {
            const currentCategory = select.value;
            const options = select.querySelectorAll('option');
            options.forEach(option => {
                if (option.value === currentCategory) {
                    option.style.display = 'none';
                } else {
                    option.style.display = 'block';
                }
            });
        });
    }

    // Update category hierarchy on page load and select change
    updateCategoryHierarchy();
    document.querySelectorAll('select[name$="-parent"]').forEach(select => {
        select.addEventListener('change', updateCategoryHierarchy);
    });

    // Stock status update
    function updateStockStatus() {
        const stockInputs = document.querySelectorAll('input[name$="-stock"]');
        stockInputs.forEach(input => {
            const statusSpan = input.closest('.form-row').querySelector('.stock-status');
            if (statusSpan) {
                const stock = parseInt(input.value) || 0;
                if (stock > 10) {
                    statusSpan.innerHTML = '<span class="badge bg-success">In Stock</span>';
                } else if (stock > 0) {
                    statusSpan.innerHTML = '<span class="badge bg-warning">Low Stock</span>';
                } else {
                    statusSpan.innerHTML = '<span class="badge bg-danger">Out of Stock</span>';
                }
            }
        });
    }

    // Update stock status on page load and input change
    updateStockStatus();
    document.querySelectorAll('input[name$="-stock"]').forEach(input => {
        input.addEventListener('input', updateStockStatus);
    });

    // Category tree view
    function createCategoryTree(categories) {
        const treeContainer = document.querySelector('.category-tree');
        if (!treeContainer) return;

        function createNode(category) {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="parent-category">${category.name}</span>
                <ul class="category-tree">
                    ${category.subcategories.map(createNode).join('')}
                </ul>
            `;
            return li;
        }

        const ul = document.createElement('ul');
        ul.className = 'category-tree';
        ul.innerHTML = categories.map(createNode).join('');
        treeContainer.appendChild(ul);
    }

    // Fetch and display category tree
    fetch('/api/categories/tree/')
        .then(response => response.json())
        .then(data => createCategoryTree(data))
        .catch(error => console.error('Error loading category tree:', error));

    // Product image sorting
    const imageSortButtons = document.querySelectorAll('.image-sort-btn');
    imageSortButtons.forEach(button => {
        button.addEventListener('click', function() {
            const imageId = this.dataset.imageId;
            const direction = this.dataset.direction;
            fetch(`/api/products/images/${imageId}/move/${direction}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                // Update image order in UI
                updateImageOrder(data.images);
            })
            .catch(error => console.error('Error sorting images:', error));
        });
    });

    // Helper function to get cookie value
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

    // Helper function to update image order
    function updateImageOrder(images) {
        const imageContainer = document.querySelector('.image-container');
        if (!imageContainer) return;

        const imageElements = images.map(image => {
            const element = document.createElement('div');
            element.className = 'image-item';
            element.innerHTML = `
                <img src="${image.url}" alt="${image.alt_text}" class="image-preview">
                <div class="image-actions">
                    <button class="image-sort-btn" data-image-id="${image.id}" data-direction="up">
                        Move Up
                    </button>
                    <button class="image-sort-btn" data-image-id="${image.id}" data-direction="down">
                        Move Down
                    </button>
                </div>
            `;
            return element;
        });

        imageContainer.innerHTML = imageElements.join('');
    }
});
