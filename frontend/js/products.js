// Products Module - Handles product display and management

const PRODUCTS = {
  productsGrid: null,
  searchInput: null,
  sortSelect: null,
  allProducts: [],
  selectedProduct: null,
  selectedColor: null,
  selectedSize: null,

  init() {
    this.productsGrid = document.getElementById('products-grid');
    this.searchInput = document.getElementById('search-input');
    this.sortSelect = document.getElementById('sort-select');

    this.setupEventListeners();
    this.loadAndDisplayProducts();
  },

  setupEventListeners() {
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this.filterAndSort({ search: e.target.value });
      });
    }

    if (this.sortSelect) {
      this.sortSelect.addEventListener('change', (e) => {
        this.filterAndSort({ sort: e.target.value });
      });
    }

    // Modal close buttons
    document.getElementById('modal-close').addEventListener('click', () => {
      this.closeProductModal();
    });

    document.getElementById('modal-cancel').addEventListener('click', () => {
      this.closeProductModal();
    });

    // Modal add to cart
    document.getElementById('modal-add-to-cart').addEventListener('click', () => {
      this.addToCartFromModal();
    });

    // Close modal on overlay click
    document.getElementById('product-modal').addEventListener('click', (e) => {
      if (e.target.id === 'product-modal') {
        this.closeProductModal();
      }
    });
  },

  async loadAndDisplayProducts() {
    try {
      this.allProducts = await API.getProducts();
      this.displayProducts(this.allProducts);
    } catch (error) {
      console.error('Failed to load products:', error);
      APP.showNotification('Failed to load products', 'error');
    }
  },

  async filterAndSort(filters = {}) {
    try {
      this.allProducts = await API.getProducts(filters);
      this.displayProducts(this.allProducts);
    } catch (error) {
      console.error('Failed to filter products:', error);
    }
  },

  displayProducts(products) {
    this.productsGrid.innerHTML = '';

    if (products.length === 0) {
      this.productsGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No products found</p>';
      return;
    }

    products.forEach(product => {
      const card = this.createProductCard(product);
      this.productsGrid.appendChild(card);
    });
  },

  createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.dataset.productId = product.id;

    const inStock = product.stock > 0;
    const badgeText = inStock ? 'In Stock' : 'Out of Stock';
    const badgeClass = inStock ? '' : 'out-of-stock';

    const discount = Math.round((1 - product.price / product.originalPrice) * 100);

    card.innerHTML = `
      <div style="position: relative;">
        <img
          src="${product.image}"
          alt="${product.name}"
          class="product-image"
          loading="lazy"
        >
        <div class="product-badge ${badgeClass}">
          ${inStock ? `${discount}% OFF` : badgeText}
        </div>
      </div>
      <div class="product-info">
        <h3 class="product-name">${product.name}</h3>
        <div class="product-price">
          <span class="price-current">$${product.price.toFixed(2)}</span>
          <span class="price-original">$${product.originalPrice.toFixed(2)}</span>
        </div>
        <div class="product-rating">
          ★ ${product.rating} (${product.reviews})
        </div>
        <div class="product-actions">
          <button class="btn btn-sm btn-secondary" data-action="view-details">
            View
          </button>
          <button class="btn btn-sm btn-primary" data-action="quick-add">
            Quick Add
          </button>
        </div>
      </div>
    `;

    card.querySelector('[data-action="view-details"]').addEventListener('click', () => {
      this.showProductModal(product.id);
    });

    card.querySelector('[data-action="quick-add"]').addEventListener('click', async () => {
      if (product.stock > 0) {
        await this.addToCart(product.id, 1);
      } else {
        APP.showNotification('Out of stock', 'error');
      }
    });

    return card;
  },

  async showProductModal(productId) {
    try {
      this.selectedProduct = await API.getProductDetails(productId);
      this.selectedColor = null;
      this.selectedSize = null;

      const modal = document.getElementById('product-modal');

      // Set product details
      document.getElementById('modal-product-name').textContent = this.selectedProduct.name;
      document.getElementById('modal-product-image').src = this.selectedProduct.image;
      document.getElementById('modal-product-price').textContent = `$${this.selectedProduct.price.toFixed(2)}`;
      document.getElementById('modal-product-description').textContent = this.selectedProduct.description;

      // Stock status
      const stockSpan = document.getElementById('modal-product-stock');
      if (this.selectedProduct.stock > 0) {
        stockSpan.textContent = `${this.selectedProduct.stock} in stock`;
        stockSpan.style.color = 'var(--secondary)';
      } else {
        stockSpan.textContent = 'Out of Stock';
        stockSpan.style.color = 'var(--error)';
      }

      // Rating
      document.getElementById('modal-product-rating').textContent =
        `★ ${this.selectedProduct.rating} (${this.selectedProduct.reviews} reviews)`;

      // Colors
      const colorOptions = document.getElementById('color-options');
      colorOptions.innerHTML = '';
      this.selectedProduct.colors.forEach(color => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'color-option';
        btn.textContent = color;
        btn.style.backgroundColor = this.getColorValue(color);
        btn.style.color = this.getTextColorForBackground(color);

        btn.addEventListener('click', () => {
          document.querySelectorAll('.color-option').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          this.selectedColor = color;
        });

        colorOptions.appendChild(btn);
      });

      // Sizes
      const sizeOptions = document.getElementById('size-options');
      sizeOptions.innerHTML = '';
      this.selectedProduct.sizes.forEach(size => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'size-option';
        btn.textContent = size;

        btn.addEventListener('click', () => {
          document.querySelectorAll('.size-option').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          this.selectedSize = size;
        });

        sizeOptions.appendChild(btn);
      });

      // Reviews
      this.displayReviews();

      // Show modal
      modal.classList.add('active');
    } catch (error) {
      APP.showNotification('Failed to load product details', 'error');
    }
  },

  closeProductModal() {
    const modal = document.getElementById('product-modal');
    modal.classList.remove('active');
    this.selectedProduct = null;
    this.selectedColor = null;
    this.selectedSize = null;
  },

  displayReviews() {
    const reviewsContainer = document.getElementById('reviews-container');
    reviewsContainer.innerHTML = '';

    const sampleReviews = [
      { author: 'Sarah M.', rating: 5, text: 'Excellent quality and fast shipping!' },
      { author: 'John D.', rating: 4, text: 'Good product, exactly as described.' },
      { author: 'Emma L.', rating: 5, text: 'Love it! Will definitely buy again.' }
    ];

    sampleReviews.forEach(review => {
      const reviewDiv = document.createElement('div');
      reviewDiv.className = 'review-item';
      reviewDiv.innerHTML = `
        <div class="review-header">
          <span><strong>${review.author}</strong></span>
          <span class="review-rating">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</span>
        </div>
        <p class="review-text">${review.text}</p>
      `;
      reviewsContainer.appendChild(reviewDiv);
    });
  },

  async addToCartFromModal() {
    if (!this.selectedProduct) return;

    if (this.selectedProduct.stock <= 0) {
      APP.showNotification('Out of stock', 'error');
      return;
    }

    try {
      await this.addToCart(this.selectedProduct.id, 1);
      this.closeProductModal();
    } catch (error) {
      APP.showNotification('Failed to add to cart', 'error');
    }
  },

  async addToCart(productId, quantity) {
    try {
      await API.addToCart(productId, quantity);
      CART.updateCart();
      APP.showNotification(`Added to cart!`, 'success');
    } catch (error) {
      APP.showNotification('Failed to add to cart', 'error');
    }
  },

  getColorValue(colorName) {
    const colors = {
      'Blue': '#007AFF',
      'Black': '#000000',
      'White': '#FFFFFF',
      'Silver': '#C0C0C0',
      'Gold': '#FFD700',
      'Rose Gold': '#B76E79',
      'Red': '#FF3B30',
      'Green': '#34C759',
      'Navy': '#000080',
      'Khaki': '#F0E68C',
      'Brown': '#8B4513',
      'Tan': '#D2B48C',
      'Clear': '#F2F2F7'
    };
    return colors[colorName] || '#F2F2F7';
  },

  getTextColorForBackground(colorName) {
    const lightColors = ['White', 'Silver', 'Gold', 'Khaki', 'Clear', 'Tan'];
    return lightColors.includes(colorName) ? '#000000' : '#FFFFFF';
  }
};
