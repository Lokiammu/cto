// Auth Module - Handles authentication and user management

const AUTH = {
  currentUser: null,
  token: null,

  init() {
    this.restoreSession();
    this.setupEventListeners();
  },

  setupEventListeners() {
    const signupForm = document.getElementById('signup-form');
    const signinForm = document.getElementById('signin-form');
    const passwordInput = document.getElementById('signup-password');

    if (signupForm) {
      signupForm.addEventListener('submit', (e) => this.handleSignup(e));
    }

    if (signinForm) {
      signinForm.addEventListener('submit', (e) => this.handleSignin(e));
    }

    if (passwordInput) {
      passwordInput.addEventListener('input', (e) => this.updatePasswordRequirements(e.target.value));
    }

    // Logout buttons
    document.querySelectorAll('.btn-logout').forEach(btn => {
      btn.addEventListener('click', () => this.logout());
    });
  },

  async handleSignup(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const name = formData.get('name');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirm = formData.get('confirm');

    // Clear previous errors
    form.querySelectorAll('.form-error').forEach(error => {
      error.classList.remove('show');
      error.textContent = '';
    });

    let isValid = true;

    // Validate name
    if (!name.trim()) {
      this.setFormError(form, 'signup-name', 'Please enter your name');
      isValid = false;
    }

    // Validate email
    if (!API.validateEmail(email)) {
      this.setFormError(form, 'signup-email', 'Please enter a valid email');
      isValid = false;
    }

    // Validate password requirements
    const passwordValidation = API.validatePassword(password);
    if (!passwordValidation.isValid) {
      this.setFormError(form, 'signup-password', 'Password must be at least 8 characters');
      isValid = false;
    }

    // Check if passwords match
    if (password !== confirm) {
      this.setFormError(form, 'signup-confirm', 'Passwords do not match');
      isValid = false;
    }

    if (!isValid) {
      return;
    }

    try {
      const result = await API.signup(email, password, name);
      this.setCurrentUser(result.user);
      this.token = result.token;

      APP.showNotification('Account created successfully!', 'success');
      APP.switchPage('chat');
    } catch (error) {
      if (error.message.includes('already registered')) {
        this.setFormError(form, 'signup-email', error.message);
      } else {
        APP.showNotification(error.message, 'error');
      }
    }
  },

  async handleSignin(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const email = formData.get('email');
    const password = formData.get('password');

    // Clear previous errors
    form.querySelectorAll('.form-error').forEach(error => {
      error.classList.remove('show');
      error.textContent = '';
    });

    let isValid = true;

    // Validate email
    if (!API.validateEmail(email)) {
      this.setFormError(form, 'signin-email', 'Please enter a valid email');
      isValid = false;
    }

    // Validate password
    if (!password) {
      this.setFormError(form, 'signin-password', 'Please enter your password');
      isValid = false;
    }

    if (!isValid) {
      return;
    }

    try {
      const result = await API.signin(email, password);
      this.setCurrentUser(result.user);
      this.token = result.token;

      APP.showNotification('Signed in successfully!', 'success');
      APP.switchPage('chat');
    } catch (error) {
      APP.showNotification(error.message, 'error');
    }
  },

  updatePasswordRequirements(password) {
    const requirements = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      number: /\d/.test(password)
    };

    document.querySelectorAll('.password-requirement').forEach(req => {
      const requirement = req.dataset.requirement;
      const isValid = requirements[requirement];

      if (isValid) {
        req.classList.remove('invalid');
        req.classList.add('valid');
      } else {
        req.classList.remove('valid');
        req.classList.add('invalid');
      }
    });
  },

  setFormError(form, fieldId, message) {
    const field = form.querySelector(`#${fieldId}`);
    if (field) {
      field.classList.add('error');
      const errorElement = field.nextElementSibling;
      if (errorElement && errorElement.classList.contains('form-error')) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
      }
    }
  },

  setCurrentUser(user) {
    this.currentUser = user;
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.updateUserUI();
  },

  updateUserUI() {
    if (!this.currentUser) return;

    const initials = this.currentUser.name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);

    document.querySelectorAll('[id^="user-avatar"]').forEach(avatar => {
      avatar.textContent = initials;
    });

    document.querySelectorAll('[id^="user-name"]').forEach(name => {
      name.textContent = this.currentUser.name;
    });
  },

  restoreSession() {
    const user = localStorage.getItem('currentUser');
    const token = localStorage.getItem('token');

    if (user && token) {
      this.currentUser = JSON.parse(user);
      this.token = token;
      this.updateUserUI();
      return true;
    }

    return false;
  },

  logout() {
    if (confirm('Are you sure you want to logout?')) {
      this.currentUser = null;
      this.token = null;
      localStorage.removeItem('currentUser');
      localStorage.removeItem('token');
      localStorage.removeItem('chatHistory');
      localStorage.removeItem('cart');

      APP.switchPage('signin');
      APP.showNotification('Logged out successfully', 'info');
    }
  },

  isAuthenticated() {
    return !!this.currentUser && !!this.token;
  },

  getToken() {
    return this.token;
  }
};
