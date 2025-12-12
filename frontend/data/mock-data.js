// Mock Products Data
const mockProducts = [
  {
    id: 1,
    name: 'Blue Wireless Headphones',
    price: 89.99,
    originalPrice: 129.99,
    image: 'https://via.placeholder.com/300x300?text=Headphones+Blue',
    stock: 15,
    colors: ['Blue', 'Black', 'Silver'],
    sizes: ['One Size'],
    rating: 4.5,
    reviews: 127,
    description: 'Premium quality wireless headphones with noise cancellation'
  },
  {
    id: 2,
    name: 'Classic Watch',
    price: 199.99,
    originalPrice: 249.99,
    image: 'https://via.placeholder.com/300x300?text=Watch+Classic',
    stock: 8,
    colors: ['Silver', 'Gold', 'Rose Gold'],
    sizes: ['One Size'],
    rating: 4.8,
    reviews: 89,
    description: 'Elegant analog watch for everyday wear'
  },
  {
    id: 3,
    name: 'Canvas Backpack',
    price: 59.99,
    originalPrice: 79.99,
    image: 'https://via.placeholder.com/300x300?text=Backpack+Canvas',
    stock: 20,
    colors: ['Black', 'Navy', 'Khaki', 'Red'],
    sizes: ['One Size'],
    rating: 4.6,
    reviews: 156,
    description: 'Durable canvas backpack with multiple compartments'
  },
  {
    id: 4,
    name: 'Running Shoes',
    price: 119.99,
    originalPrice: 159.99,
    image: 'https://via.placeholder.com/300x300?text=Shoes+Running',
    stock: 12,
    colors: ['Black', 'White', 'Red', 'Gray'],
    sizes: ['6', '7', '8', '9', '10', '11', '12', '13'],
    rating: 4.7,
    reviews: 203,
    description: 'Comfortable running shoes with responsive cushioning'
  },
  {
    id: 5,
    name: 'Smartphone Stand',
    price: 24.99,
    originalPrice: 34.99,
    image: 'https://via.placeholder.com/300x300?text=Phone+Stand',
    stock: 35,
    colors: ['Black', 'Silver'],
    sizes: ['One Size'],
    rating: 4.4,
    reviews: 78,
    description: 'Adjustable smartphone stand for any device'
  },
  {
    id: 6,
    name: 'Leather Wallet',
    price: 79.99,
    originalPrice: 99.99,
    image: 'https://via.placeholder.com/300x300?text=Wallet+Leather',
    stock: 18,
    colors: ['Brown', 'Black', 'Tan'],
    sizes: ['One Size'],
    rating: 4.6,
    reviews: 112,
    description: 'Genuine leather wallet with RFID protection'
  },
  {
    id: 7,
    name: 'USB-C Cable',
    price: 14.99,
    originalPrice: 19.99,
    image: 'https://via.placeholder.com/300x300?text=Cable+USB-C',
    stock: 50,
    colors: ['Black', 'White'],
    sizes: ['3ft', '6ft', '10ft'],
    rating: 4.3,
    reviews: 234,
    description: 'Fast charging USB-C cable, supports 100W'
  },
  {
    id: 8,
    name: 'Portable Speaker',
    price: 69.99,
    originalPrice: 99.99,
    image: 'https://via.placeholder.com/300x300?text=Speaker+Portable',
    stock: 10,
    colors: ['Black', 'Blue', 'Red'],
    sizes: ['One Size'],
    rating: 4.5,
    reviews: 145,
    description: 'Waterproof portable Bluetooth speaker with 12-hour battery'
  },
  {
    id: 9,
    name: 'Screen Protector',
    price: 9.99,
    originalPrice: 14.99,
    image: 'https://via.placeholder.com/300x300?text=Screen+Protector',
    stock: 100,
    colors: ['Clear'],
    sizes: ['iPhone 14', 'iPhone 14 Pro', 'Samsung S23', 'Android'],
    rating: 4.2,
    reviews: 567,
    description: 'Tempered glass screen protector with easy installation'
  },
  {
    id: 10,
    name: 'Phone Case',
    price: 19.99,
    originalPrice: 29.99,
    image: 'https://via.placeholder.com/300x300?text=Case+Phone',
    stock: 42,
    colors: ['Black', 'Clear', 'Blue', 'Pink'],
    sizes: ['iPhone 14', 'iPhone 14 Pro', 'Samsung S23'],
    rating: 4.4,
    reviews: 189,
    description: 'Protective phone case with shockproof design'
  }
];

// Mock Users Data
const mockUsers = [
  {
    id: 1,
    email: 'john@example.com',
    password: 'hashedPassword123',
    name: 'John Doe',
    loyaltyPoints: 450,
    createdAt: new Date('2023-01-15')
  },
  {
    id: 2,
    email: 'jane@example.com',
    password: 'hashedPassword456',
    name: 'Jane Smith',
    loyaltyPoints: 820,
    createdAt: new Date('2023-02-20')
  },
  {
    id: 3,
    email: 'bob@example.com',
    password: 'hashedPassword789',
    name: 'Bob Johnson',
    loyaltyPoints: 150,
    createdAt: new Date('2023-03-10')
  }
];

// Mock Chat Responses
const mockChatResponses = [
  "That's a great choice! Let me show you some similar products.",
  "Perfect! I've added that to your cart. Would you like to see related items?",
  "Thanks for your interest! This item is very popular. Can I help with anything else?",
  "Excellent selection! You're saving 30% off the original price.",
  "I think you'll love this product. Many customers have given it 5-star reviews!",
  "Would you like to hear about our loyalty rewards program?",
  "This product is perfect for you based on your interests.",
  "Great taste! This is one of our best sellers.",
  "You've got excellent items in your cart. Ready to checkout?",
  "Let me know if you'd like me to apply a discount code to your order."
];

// Mock Chat History
const mockChatHistory = [
  {
    id: 1,
    sender: 'agent',
    content: 'Hello! Welcome to our store. How can I help you today?',
    timestamp: new Date(Date.now() - 5 * 60000),
    type: 'text'
  },
  {
    id: 2,
    sender: 'user',
    content: 'Hi! I\'m looking for some new headphones.',
    timestamp: new Date(Date.now() - 4 * 60000),
    type: 'text'
  },
  {
    id: 3,
    sender: 'agent',
    content: 'Great! Let me show you our best-selling headphones with excellent reviews.',
    timestamp: new Date(Date.now() - 3.5 * 60000),
    type: 'text'
  }
];

// Helper function to get random mock response
function getRandomMockResponse() {
  return mockChatResponses[Math.floor(Math.random() * mockChatResponses.length)];
}
