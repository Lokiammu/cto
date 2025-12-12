// Main App Module - Orchestrates all functionality

const APP = {
  init() {
    // Initialize auth first to check if user is logged in
    AUTH.init();

    // Check if user is authenticated
    if (!AUTH.isAuthenticated()) {
      this.switchPage('signup');
    } else {
      this.switchPage('chat');
    }

    // Setup navigation
    this.setupNavigation();

    // Initialize cart
    CART.init();

    // Initialize chat and products based on current page
    this.setupPageModules();
  },

  setupNavigation() {
    // Handle page navigation links
    document.querySelectorAll('[data-page]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        this.switchPage(page);
      });
    });
  },

  switchPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
      page.classList.remove('active');
    });

    // Show selected page
    const page = document.getElementById(`${pageName}-page`);
    if (page) {
      page.classList.add('active');

      // Initialize page-specific modules
      if (pageName === 'chat') {
        if (!CHAT.messagesContainer) {
          CHAT.init();
        }
      } else if (pageName === 'products') {
        if (!PRODUCTS.productsGrid) {
          PRODUCTS.init();
        }
      }
    }
  },

  setupPageModules() {
    // Initialize CHAT if user is authenticated and on chat page
    if (AUTH.isAuthenticated()) {
      CHAT.init();
      PRODUCTS.init();
    }
  },

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
};

// Cart Module - Handles shopping cart
const CART = {
  sidebar: null,
  cartItems: null,
  cartToggle: null,
  cartBadge: null,
  isOpen: false,

  init() {
    this.sidebar = document.getElementById('cart-sidebar');
    this.cartItems = document.getElementById('cart-items');
    this.cartToggle = document.querySelectorAll('.cart-toggle');
    this.cartBadge = document.querySelectorAll('.cart-badge');

    this.setupEventListeners();
    this.updateCart();
  },

  setupEventListeners() {
    // Toggle cart
    this.cartToggle.forEach(btn => {
      btn.addEventListener('click', () => this.toggleCart());
    });

    // Close cart
    document.getElementById('cart-close').addEventListener('click', () => this.toggleCart());

    // Close on overlay click
    this.sidebar.addEventListener('click', (e) => {
      if (e.target === this.sidebar) {
        this.toggleCart();
      }
    });

    // Checkout
    document.getElementById('checkout-btn').addEventListener('click', () => this.checkout());
  },

  toggleCart() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.sidebar.classList.add('open');
    } else {
      this.sidebar.classList.remove('open');
    }
  },

  async updateCart() {
    try {
      const cart = await API.getCart();
      this.renderCart(cart);
      this.updateCartCount(cart.length);
      this.updateCartTotal(cart);
    } catch (error) {
      console.error('Failed to update cart:', error);
    }
  },

  renderCart(cart) {
    const cartItemsContainer = document.getElementById('cart-items');
    cartItemsContainer.innerHTML = '';

    if (cart.length === 0) {
      cartItemsContainer.innerHTML = `
        <div class="cart-empty">
          <div class="cart-empty-icon">🛒</div>
          <p>Your cart is empty</p>
        </div>
      `;
      return;
    }

    cart.forEach(item => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'cart-item';
      itemDiv.innerHTML = `
        <img src="${item.image}" alt="${item.name}" class="cart-item-image">
        <div class="cart-item-details">
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-price">$${item.price.toFixed(2)}</div>
          <div class="quantity-selector">
            <button class="quantity-btn" data-action="decrease" data-product-id="${item.productId}">−</button>
            <span class="quantity-value">${item.quantity}</span>
            <button class="quantity-btn" data-action="increase" data-product-id="${item.productId}">+</button>
          </div>
          <button class="cart-remove" data-product-id="${item.productId}">Remove</button>
        </div>
      `;

      // Quantity controls
      itemDiv.querySelector('[data-action="decrease"]').addEventListener('click', async () => {
        await API.updateCartItem(item.productId, item.quantity - 1);
        this.updateCart();
      });

      itemDiv.querySelector('[data-action="increase"]').addEventListener('click', async () => {
        await API.updateCartItem(item.productId, item.quantity + 1);
        this.updateCart();
      });

      itemDiv.querySelector('.cart-remove').addEventListener('click', async () => {
        await API.updateCartItem(item.productId, 0);
        this.updateCart();
      });

      cartItemsContainer.appendChild(itemDiv);
    });
  },

  updateCartCount(count) {
    this.cartBadge.forEach(badge => {
      badge.textContent = count;
      if (count === 0) {
        badge.style.display = 'none';
      } else {
        badge.style.display = 'flex';
      }
    });
  },

  updateCartTotal(cart) {
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    // Get loyalty discount
    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    const loyaltyDiscount = currentUser ? (currentUser.loyaltyPoints / 100) : 0;

    const total = Math.max(0, subtotal - loyaltyDiscount);

    document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('loyalty-discount').textContent = `-$${loyaltyDiscount.toFixed(2)}`;
    document.getElementById('total').textContent = `$${total.toFixed(2)}`;
  },

  async checkout() {
    try {
      const cart = await API.getCart();

      if (cart.length === 0) {
        APP.showNotification('Cart is empty', 'error');
        return;
      }

      const currentUser = JSON.parse(localStorage.getItem('currentUser'));
      const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      const loyaltyDiscount = currentUser ? (currentUser.loyaltyPoints / 100) : 0;

      const order = await API.checkout(cart, loyaltyDiscount);

      APP.showNotification('Order placed successfully!', 'success');
      this.updateCart();
      this.toggleCart();

      // Show order confirmation
      setTimeout(() => {
        alert(`Order #${order.id}\nTotal: $${order.total.toFixed(2)}\n\nThank you for your purchase!`);
      }, 500);
    } catch (error) {
      APP.showNotification('Checkout failed: ' + error.message, 'error');
    }
  }
};

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    APP.init();
  });
} else {
  APP.init();
}
