// API Module - Handles all API calls with mock responses

const API = {
  BASE_URL: 'http://localhost:3000/api',

  // Helper function to simulate API delay
  simulateDelay(ms = 1000) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  // Auth API calls
  async signup(email, password, name) {
    await this.simulateDelay(500);

    const users = JSON.parse(localStorage.getItem('users')) || mockUsers;
    
    // Check if email already exists
    if (users.some(u => u.email === email)) {
      throw new Error('Email already registered');
    }

    const newUser = {
      id: users.length + 1,
      email,
      password: this.hashPassword(password),
      name,
      loyaltyPoints: 0,
      createdAt: new Date()
    };

    users.push(newUser);
    localStorage.setItem('users', JSON.stringify(users));

    const token = this.generateToken(newUser);
    localStorage.setItem('token', token);
    localStorage.setItem('currentUser', JSON.stringify(newUser));

    return { token, user: newUser };
  },

  async signin(email, password) {
    await this.simulateDelay(500);

    const users = JSON.parse(localStorage.getItem('users')) || mockUsers;
    const user = users.find(u => u.email === email);

    if (!user) {
      throw new Error('User not found');
    }

    if (user.password !== this.hashPassword(password)) {
      throw new Error('Invalid password');
    }

    const token = this.generateToken(user);
    localStorage.setItem('token', token);
    localStorage.setItem('currentUser', JSON.stringify(user));

    return { token, user };
  },

  // Product API calls
  async getProducts(filters = {}) {
    await this.simulateDelay(300);

    let products = mockProducts;

    if (filters.search) {
      const search = filters.search.toLowerCase();
      products = products.filter(p =>
        p.name.toLowerCase().includes(search)
      );
    }

    if (filters.sort) {
      switch (filters.sort) {
        case 'price-low':
          products = [...products].sort((a, b) => a.price - b.price);
          break;
        case 'price-high':
          products = [...products].sort((a, b) => b.price - a.price);
          break;
        case 'rating':
          products = [...products].sort((a, b) => b.rating - a.rating);
          break;
        case 'newest':
          products = [...products].reverse();
          break;
      }
    }

    return products;
  },

  async getProductDetails(productId) {
    await this.simulateDelay(200);

    const product = mockProducts.find(p => p.id == productId);
    if (!product) {
      throw new Error('Product not found');
    }

    return product;
  },

  async checkInventory(productId, location = 'default') {
    await this.simulateDelay(200);

    const product = mockProducts.find(p => p.id == productId);
    if (!product) {
      throw new Error('Product not found');
    }

    return {
      available: product.stock > 0,
      quantity: product.stock,
      location
    };
  },

  // Chat API calls
  async sendChatMessage(sessionId, message) {
    await this.simulateDelay(2000 + Math.random() * 1000); // 2-3 second delay

    // Save message to localStorage
    const chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
    chatHistory.push({
      id: chatHistory.length + 1,
      sender: 'agent',
      content: getRandomMockResponse(),
      timestamp: new Date(),
      type: 'text'
    });
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

    return chatHistory[chatHistory.length - 1];
  },

  async getChatHistory(sessionId) {
    await this.simulateDelay(300);

    const chatHistory = JSON.parse(localStorage.getItem('chatHistory'));
    return chatHistory || mockChatHistory;
  },

  // Cart API calls
  async addToCart(productId, quantity) {
    await this.simulateDelay(300);

    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const existingItem = cart.find(item => item.productId == productId);

    if (existingItem) {
      existingItem.quantity += quantity;
    } else {
      const product = await this.getProductDetails(productId);
      cart.push({
        productId,
        quantity,
        price: product.price,
        name: product.name,
        image: product.image
      });
    }

    localStorage.setItem('cart', JSON.stringify(cart));
    return cart;
  },

  async updateCartItem(productId, quantity) {
    await this.simulateDelay(200);

    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const item = cart.find(i => i.productId == productId);

    if (!item) {
      throw new Error('Item not in cart');
    }

    if (quantity <= 0) {
      const index = cart.indexOf(item);
      cart.splice(index, 1);
    } else {
      item.quantity = quantity;
    }

    localStorage.setItem('cart', JSON.stringify(cart));
    return cart;
  },

  async getCart() {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    return cart;
  },

  async applyLoyaltyDiscount(userId) {
    await this.simulateDelay(200);

    const users = JSON.parse(localStorage.getItem('users')) || mockUsers;
    const user = users.find(u => u.id == userId);

    if (!user) {
      throw new Error('User not found');
    }

    // 1 loyalty point = $0.01 discount
    const discountAmount = user.loyaltyPoints / 100;
    return { discountAmount, loyaltyPoints: user.loyaltyPoints };
  },

  async checkout(cartItems, loyaltyDiscount = 0) {
    await this.simulateDelay(1000);

    const currentUser = JSON.parse(localStorage.getItem('currentUser'));
    if (!currentUser) {
      throw new Error('User not authenticated');
    }

    // Create order
    const order = {
      id: Math.random().toString(36).substr(2, 9),
      userId: currentUser.id,
      items: cartItems,
      subtotal: cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0),
      discount: loyaltyDiscount,
      total: cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0) - loyaltyDiscount,
      createdAt: new Date(),
      status: 'pending'
    };

    // Save order
    const orders = JSON.parse(localStorage.getItem('orders')) || [];
    orders.push(order);
    localStorage.setItem('orders', JSON.stringify(orders));

    // Clear cart
    localStorage.setItem('cart', JSON.stringify([]));

    return order;
  },

  // Helper functions
  hashPassword(password) {
    // Simple mock hash - in production, use proper hashing
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
      const char = password.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return 'hashed_' + Math.abs(hash).toString(36);
  },

  generateToken(user) {
    // Mock JWT token
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({
      id: user.id,
      email: user.email,
      iat: Date.now()
    }));
    const signature = 'mock_signature';
    return `${header}.${payload}.${signature}`;
  },

  validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  validatePassword(password) {
    return {
      isValid: password.length >= 8,
      hasLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasNumber: /\d/.test(password)
    };
  }
};
