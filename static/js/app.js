/**
 * ERA - Event Resource & Administration System
 * SPA Engine: Home Landing -> Registration/Login -> Role Personal Dashboard & Profile
 */

// Initial Seed Data
const INITIAL_DATA = {
  activeRole: 'client',
  activeUser: { name: 'Alex Johnson', email: 'alex@example.com', phone: '+91 98765 43210', city: 'Mumbai', role: 'client' },

  events: [
    {
      id: 101,
      name: 'Global Tech & AI Summit 2026',
      category: 'Corporate',
      date: '2026-11-15',
      startTime: '09:00',
      endTime: '18:00',
      venue: 'Grand Crystal Ballroom',
      budget: 25000,
      spent: 18400,
      liveStatus: 'Upcoming',
      progress: 75,
      description: 'Annual Technology Innovation Conference featuring keynotes and panel discussions.'
    },
    {
      id: 102,
      name: 'Royal Wedding Gala',
      category: 'Wedding',
      date: '2026-12-05',
      startTime: '17:00',
      endTime: '23:30',
      venue: 'Emerald Garden Pavilion',
      budget: 40000,
      spent: 36500,
      liveStatus: 'In-Progress',
      progress: 90,
      description: 'Luxury wedding celebration with 250 guests and gourmet catering.'
    },
    {
      id: 103,
      name: 'Indie Rock Music Fest',
      category: 'Concert',
      date: '2027-01-20',
      startTime: '16:00',
      endTime: '23:00',
      venue: 'Skyline Horizon Arena',
      budget: 55000,
      spent: 12000,
      liveStatus: 'Upcoming',
      progress: 30,
      description: 'Outdoor live music festival with stage setups and food trucks.'
    }
  ],

  venues: [
    {
      id: 1,
      name: 'Grand Crystal Ballroom',
      type: 'Ballroom / Indoor',
      location: 'Downtown Financial District, Bldg 4',
      capacity: 500,
      availabilityStatus: 'Available',
      ownerName: 'Vanguard Properties',
      pricePerDay: 4500,
      licenseNumber: 'V-884920'
    },
    {
      id: 2,
      name: 'Emerald Garden Pavilion',
      type: 'Outdoor / Banquet',
      location: 'Green Valley Estates, Gate 2',
      capacity: 250,
      availabilityStatus: 'Booked',
      ownerName: 'Lush Green Spaces Ltd',
      pricePerDay: 3200,
      licenseNumber: 'V-449102'
    },
    {
      id: 3,
      name: 'Skyline Horizon Arena',
      type: 'Stadium / Arena',
      location: 'Westside Cultural Hub',
      capacity: 2500,
      availabilityStatus: 'Available',
      ownerName: 'City Arena Group',
      pricePerDay: 12000,
      licenseNumber: 'V-993104'
    }
  ],

  vendors: [
    { id: 1, businessName: 'Gourmet Catering Co.', serviceType: 'Catering & Beverages', pricing: '$35 - $80 / plate', rating: '4.9 ★', availability: 'Available', phone: '+91 98765 43210' },
    { id: 2, businessName: 'Sonic Boom Audio & FX', serviceType: 'Sound, Stage & Lighting', pricing: '$2,500 / day', rating: '4.8 ★', availability: 'Available', phone: '+91 98123 45678' },
    { id: 3, businessName: 'Floral & Decor Elegance', serviceType: 'Decoration & Styling', pricing: '$1,500 - $8,000 / event', rating: '4.7 ★', availability: 'Busy', phone: '+91 97654 32109' }
  ],

  expenses: [
    { id: 1, eventId: 101, category: 'Venue Rental', description: 'Grand Crystal Ballroom Deposit', allocated: 5000, spent: 4500, status: 'Paid' },
    { id: 2, eventId: 101, category: 'Catering', description: 'Gourmet Lunch & High Tea', allocated: 9000, spent: 8500, status: 'Paid' },
    { id: 3, eventId: 101, category: 'Audio/Visual', description: 'LED Stage Screen & Microphones', allocated: 4000, spent: 3400, status: 'Paid' },
    { id: 4, eventId: 101, category: 'Marketing', description: 'Social Media Ads', allocated: 3000, spent: 2000, status: 'Pending' }
  ],

  attendees: [
    { id: 1, eventId: 101, aName: 'Dr. Sarah Connor', email: 'sarah@techcorp.com', phone: '+91 91234 56789', status: 'Confirmed', ticketCode: 'TICK-ERA-991' },
    { id: 2, eventId: 101, aName: 'Mark Rayson', email: 'mark@designstudio.io', phone: '+91 92345 67890', status: 'Confirmed', ticketCode: 'TICK-ERA-992' }
  ],

  deliveries: [
    { id: 1, partnerId: 'DP-01', item: '40 High-End Stage Speakers', origin: 'Sonic Warehouse', destination: 'Skyline Horizon Arena', event: 'Indie Rock Music Fest', status: 'In-Transit' },
    { id: 2, partnerId: 'DP-02', item: '250 Banquet Chairs', origin: 'Gourmet Depot', destination: 'Emerald Garden Pavilion', event: 'Royal Wedding Gala', status: 'Delivered' }
  ],

  chatMessages: [
    { sender: 'Event Organizer', text: 'Hi! We have confirmed the catering timeline.', time: '10:30 AM', type: 'incoming' },
    { sender: 'Client', text: 'Great! Did they accommodate dietary requests?', time: '10:32 AM', type: 'outgoing' }
  ],

  stakeholders: [
    { id: 1, name: 'Alex Johnson', role: 'client', email: 'alex@client.com', phone: '9876543210', status: 'active' },
    { id: 2, name: 'Apex Event Managers', role: 'organizer', email: 'info@apexevents.com', phone: '9876543211', status: 'active' },
    { id: 3, name: 'Vanguard Properties', role: 'venue_owner', email: 'admin@vanguard.com', phone: '9876543212', status: 'active' },
    { id: 4, name: 'Gourmet Catering Co.', role: 'vendor', email: 'contact@gourmet.com', phone: '9876543213', status: 'active' },
    { id: 5, name: 'Dr. Sarah Connor', role: 'attendee', email: 'sarah@techcorp.com', phone: '9876543214', status: 'active' },
    { id: 6, name: 'LogiSpeed Express', role: 'delivery_partner', email: 'dispatch@logispeed.com', phone: '9876543215', status: 'active' },
    { id: 7, name: 'System Admin', role: 'admin', email: 'admin@era.org', phone: '9876543216', status: 'active' }
  ]
};

// Store Management
function getStore() {
  const saved = localStorage.getItem('era_store');
  if (saved) {
    try { return JSON.parse(saved); } catch (e) { console.error(e); }
  }
  localStorage.setItem('era_store', JSON.stringify(INITIAL_DATA));
  return INITIAL_DATA;
}

function saveStore(store) {
  localStorage.setItem('era_store', JSON.stringify(store));
}

let currentStore = getStore();
let currentDashboardSubView = 'dashboard';

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
  showHomePage();
});

// ROUTING
function showHomePage() {
  document.getElementById('page-home').style.display = 'block';
  document.getElementById('page-auth').style.display = 'none';
  document.getElementById('page-dashboard').style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showAuthPage(mode = 'register') {
  document.getElementById('page-home').style.display = 'none';
  document.getElementById('page-auth').style.display = 'block';
  document.getElementById('page-dashboard').style.display = 'none';
  toggleAuthMode(mode);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showDashboardPage() {
  document.getElementById('page-home').style.display = 'none';
  document.getElementById('page-auth').style.display = 'none';
  document.getElementById('page-dashboard').style.display = 'block';

  renderDashboardApp();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toggleAuthMode(mode) {
  const registerBox = document.getElementById('authRegisterBox');
  const loginBox = document.getElementById('authLoginBox');
  if (mode === 'login') {
    registerBox.style.display = 'none';
    loginBox.style.display = 'block';
  } else {
    registerBox.style.display = 'block';
    loginBox.style.display = 'none';
  }
}

function scrollToSection(id) {
  const target = document.getElementById(id);
  if (target) target.scrollIntoView({ behavior: 'smooth' });
}

// STRONG PASSWORD VALIDATION
function validatePassword(password) {
  const hasMinLen = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);

  return hasMinLen && hasUpper && hasLower && hasNumber && hasSpecial;
}

function checkPasswordStrength(password) {
  const updateRule = (id, isValid) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (isValid) {
      el.className = 'badge badge-success';
    } else {
      el.className = 'badge badge-warning';
    }
  };

  updateRule('rule-len', password.length >= 8);
  updateRule('rule-upper', /[A-Z]/.test(password));
  updateRule('rule-lower', /[a-z]/.test(password));
  updateRule('rule-num', /[0-9]/.test(password));
  updateRule('rule-spec', /[^A-Za-z0-9]/.test(password));
}

// AUTH HANDLERS
function handleRegistrationSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const identifier = document.getElementById('regIdentifier').value.trim();
  const city = document.getElementById('regCity').value.trim();
  const role = document.getElementById('regRole').value;
  const password = document.getElementById('regPassword').value;

  // Verify Strong Password
  if (!validatePassword(password)) {
    showToast('Password is not strong enough! Must be 8+ chars with uppercase, lowercase, number, and special character.', 'danger');
    return;
  }

  const isEmail = identifier.includes('@');
  currentStore.activeUser = {
    name: name,
    email: isEmail ? identifier : `${name.toLowerCase().replace(/\s+/g, '')}@example.com`,
    phone: isEmail ? '+91 98765 43210' : identifier,
    city: city,
    role: role
  };
  currentStore.activeRole = role;
  saveStore(currentStore);

  showToast(`Registration verified! Welcome to your ${getRoleName(role)} Dashboard.`, 'success');
  showDashboardPage();
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const identifier = document.getElementById('loginIdentifier').value.trim();
  const password = document.getElementById('loginPassword').value;
  const role = document.getElementById('loginRole').value;

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password, role })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.message || 'Login failed. Please check credentials.', 'danger');
      return;
    }

    currentStore.activeUser = data.user;
    currentStore.activeRole = data.user.role;
    saveStore(currentStore);

    showToast(data.message || `Logged in successfully as ${getRoleName(data.user.role)}.`, 'success');
    showDashboardPage();
  } catch (err) {
    showToast('Unable to connect to the authentication server.', 'danger');
  }
}

async function demoLogin(role) {
  // Demo password mapping for seeded users
  const demoUsers = {
    client: { email: 'client@era.com', pw: 'User@123' },
    organizer: { email: 'organizer@era.com', pw: 'User@123' },
    venue_owner: { email: 'venueowner@era.com', pw: 'User@123' },
    vendor: { email: 'vendor@era.com', pw: 'User@123' },
    attendee: { email: 'attendee@era.com', pw: 'User@123' },
    delivery_partner: { email: 'delivery@era.com', pw: 'User@123' },
    admin: { email: 'admin@era.com', pw: 'Admin@123' }
  };

  const cred = demoUsers[role];
  if (cred) {
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: cred.email, password: cred.pw, role: role })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        currentStore.activeUser = data.user;
        currentStore.activeRole = data.user.role;
        saveStore(currentStore);
        showToast(`Logged in as verified seed ${getRoleName(role)}.`, 'success');
        showDashboardPage();
        return;
      } else {
        showToast(data.message, 'warning');
      }
    } catch (e) {}
  }

  currentStore.activeRole = role;
  currentStore.activeUser = {
    name: `Demo ${getRoleName(role)}`,
    email: `${role}@era.org`,
    phone: '+91 98765 43210',
    city: 'Mumbai',
    role: role
  };
  saveStore(currentStore);
  showToast(`Accessing ${getRoleName(role)} Dashboard preview...`, 'info');
  showDashboardPage();
}

async function logoutUser() {
  try {
    await fetch('/api/logout', { method: 'POST' });
  } catch (e) {}
  showToast('Logged out successfully.', 'info');
  showHomePage();
}


// DASHBOARD & ROLE ENGINE
function getRoleName(role) {
  const roles = {
    client: 'Client',
    organizer: 'Event Organizer',
    venue_owner: 'Venue Owner',
    vendor: 'Vendor / Supplier',
    attendee: 'Attendee',
    delivery_partner: 'Delivery Partner',
    admin: 'System Admin'
  };
  return roles[role] || 'User';
}

function renderDashboardApp() {
  updateRoleHeaderUI();
  switchDashboardView(currentDashboardSubView);
}

function updateRoleHeaderUI() {
  const role = currentStore.activeRole;
  const user = currentStore.activeUser || { name: 'User' };

  document.getElementById('headerUserName').textContent = user.name || `${getRoleName(role)} Console`;
  document.getElementById('headerAvatar').textContent = getRoleInitials(user.name || role);

  // Dynamic Navigation Links
  const navContainer = document.getElementById('dynamicNavLinks');
  let links = [];

  if (role === 'client') {
    links = [
      { id: 'events', label: 'My Events & Requests', icon: '📋' },
      { id: 'venues', label: 'Browse Venues', icon: '🏛️' },
      { id: 'vendors', label: 'Find Vendors', icon: '🛠️' },
      { id: 'budget', label: 'Budget Tracker', icon: '💰' },
      { id: 'chat', label: 'Chat with Organizer', icon: '💬' }
    ];
  } else if (role === 'organizer') {
    links = [
      { id: 'events', label: 'All Events Console', icon: '📅' },
      { id: 'venues', label: 'Venue Manager', icon: '🏛️' },
      { id: 'vendors', label: 'Vendor Coordination', icon: '🧰' },
      { id: 'budget', label: 'Budget Allocator', icon: '📊' },
      { id: 'chat', label: 'Client Messages', icon: '💬' }
    ];
  } else if (role === 'venue_owner') {
    links = [
      { id: 'venues', label: 'My Venues & Capacity', icon: '🏛️' },
      { id: 'events', label: 'Venue Bookings', icon: '📅' }
    ];
  } else if (role === 'vendor') {
    links = [
      { id: 'vendors', label: 'Service Offerings', icon: '🧰' },
      { id: 'events', label: 'Service Requests', icon: '📩' }
    ];
  } else if (role === 'attendee') {
    links = [
      { id: 'attendees', label: 'My Tickets & Pass', icon: '🎟️' },
      { id: 'events', label: 'Public Events', icon: '🌟' }
    ];
  } else if (role === 'delivery_partner') {
    links = [
      { id: 'delivery', label: 'Logistics Dispatches', icon: '🚚' }
    ];
  } else if (role === 'admin') {
    links = [
      { id: 'admin', label: 'System Analytics', icon: '⚡' },
      { id: 'events', label: 'Event Records', icon: '📑' },
      { id: 'venues', label: 'Manage Venues', icon: '🏛️' },
      { id: 'vendors', label: 'Manage Suppliers', icon: '🧰' },
      { id: 'budget', label: 'Financial Overview', icon: '💵' }
    ];
  }

  navContainer.innerHTML = links.map(link => `
    <a class="nav-link ${currentDashboardSubView === link.id ? 'active' : ''}" data-view="${link.id}" onclick="switchDashboardView('${link.id}')">
      <span style="font-size:1rem;">${link.icon}</span>
      <span>${link.label}</span>
    </a>
  `).join('');
}

function getRoleInitials(str) {
  if (!str) return 'US';
  const parts = str.split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return str.substring(0, 2).toUpperCase();
}

// DASHBOARD SUB-VIEW SWITCHER
function switchDashboardView(viewId) {
  currentDashboardSubView = viewId;
  
  document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');

  const target = document.getElementById(`view-${viewId}`);
  if (target) {
    target.style.display = 'block';
  } else {
    document.getElementById('view-dashboard').style.display = 'block';
  }

  document.querySelectorAll('.nav-link').forEach(el => {
    if (el.getAttribute('data-view') === viewId) el.classList.add('active');
    else el.classList.remove('active');
  });

  if (viewId === 'dashboard') renderDashboardOverview();
  else if (viewId === 'profile') renderProfileView();
  else if (viewId === 'events') renderEventsView();
  else if (viewId === 'venues') renderVenuesView();
  else if (viewId === 'vendors') renderVendorsView();
  else if (viewId === 'budget') renderBudgetView();
  else if (viewId === 'attendees') renderAttendeesView();
  else if (viewId === 'delivery') renderDeliveryView();
  else if (viewId === 'chat') renderChatView();
  else if (viewId === 'admin') renderAdminView();
}

// 1. DASHBOARD OVERVIEW (Cleaned layout)
function renderDashboardOverview() {
  const role = currentStore.activeRole;
  const user = currentStore.activeUser || { name: 'User' };

  document.getElementById('dashboardWelcomeTitle').textContent = `${user.name}'s Dashboard`;
  document.getElementById('dashboardWelcomeSub').textContent = `Role: ${getRoleName(role)} | Location: ${user.city || 'Mumbai'}`;

  const totalEvents = currentStore.events.length;
  const activeVenues = currentStore.venues.filter(v => v.availabilityStatus === 'Available').length;
  const totalBudget = currentStore.events.reduce((sum, e) => sum + e.budget, 0);
  const totalSpent = currentStore.events.reduce((sum, e) => sum + e.spent, 0);

  document.getElementById('statCardsGrid').innerHTML = `
    <div class="stat-card">
      <div class="stat-icon indigo">📅</div>
      <div>
        <div class="stat-label">Total Events</div>
        <div class="stat-value">${totalEvents}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon cyan">🏛️</div>
      <div>
        <div class="stat-label">Available Venues</div>
        <div class="stat-value">${activeVenues} / ${currentStore.venues.length}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon emerald">💰</div>
      <div>
        <div class="stat-label">Total Budget Pool</div>
        <div class="stat-value">$${totalBudget.toLocaleString()}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon rose">💵</div>
      <div>
        <div class="stat-label">Total Spent</div>
        <div class="stat-value">$${totalSpent.toLocaleString()}</div>
      </div>
    </div>
  `;

  document.getElementById('dashboardEventsList').innerHTML = currentStore.events.map(ev => `
    <div style="padding:1rem; background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:var(--radius-md); margin-bottom:0.75rem; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <h4 style="font-size:1rem; font-weight:700;">${ev.name}</h4>
          <span class="badge ${ev.liveStatus === 'In-Progress' ? 'badge-warning' : 'badge-info'}">${ev.liveStatus}</span>
        </div>
        <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.25rem;">
          📅 ${ev.date} (${ev.startTime} - ${ev.endTime}) &bull; 📍 ${ev.venue}
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="openEventSummaryModal(${ev.id})">Brief PDF</button>
    </div>
  `).join('');
}

// 2. PROFILE SECTION VIEW & EDITING
function renderProfileView() {
  const user = currentStore.activeUser || { name: 'User', email: 'user@example.com', phone: '', city: 'Mumbai', role: currentStore.activeRole };

  document.getElementById('profileAvatarLarge').textContent = getRoleInitials(user.name);
  document.getElementById('profileDisplayName').textContent = user.name;
  document.getElementById('profileRoleBadge').textContent = getRoleName(currentStore.activeRole);
  document.getElementById('profileCityTag').textContent = `📍 ${user.city || 'Mumbai'}`;

  document.getElementById('profName').value = user.name || '';
  document.getElementById('profEmail').value = user.email || '';
  document.getElementById('profPhone').value = user.phone || '';
  document.getElementById('profCity').value = user.city || '';
  document.getElementById('profRoleDisplay').value = getRoleName(currentStore.activeRole);
}

function handleSaveProfile(e) {
  e.preventDefault();
  const name = document.getElementById('profName').value.trim();
  const email = document.getElementById('profEmail').value.trim();
  const phone = document.getElementById('profPhone').value.trim();
  const city = document.getElementById('profCity').value.trim();

  currentStore.activeUser.name = name;
  currentStore.activeUser.email = email;
  currentStore.activeUser.phone = phone;
  currentStore.activeUser.city = city;
  saveStore(currentStore);

  updateRoleHeaderUI();
  renderProfileView();
  showToast('Profile details successfully updated!', 'success');
}

// 3. EVENTS VIEW
function renderEventsView() {
  document.getElementById('eventsTableBody').innerHTML = currentStore.events.map(ev => `
    <tr>
      <td><strong>#${ev.id}</strong></td>
      <td>
        <div style="font-weight:700; color:var(--text-main);">${ev.name}</div>
        <div style="font-size:0.78rem; color:var(--text-dim);">${ev.category}</div>
      </td>
      <td>
        <div>${ev.date}</div>
        <div style="font-size:0.78rem; color:var(--text-dim);">${ev.startTime} - ${ev.endTime}</div>
      </td>
      <td>${ev.venue}</td>
      <td><span class="badge ${ev.liveStatus === 'In-Progress' ? 'badge-warning' : 'badge-info'}">${ev.liveStatus}</span></td>
      <td style="width:120px;">
        <div style="font-size:0.75rem; color:var(--text-dim);">${ev.progress}%</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:${ev.progress}%;"></div></div>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openEventSummaryModal(${ev.id})">Summary</button>
      </td>
    </tr>
  `).join('');
}

// 4. VENUES VIEW
function renderVenuesView() {
  document.getElementById('venuesGrid').innerHTML = currentStore.venues.map(v => `
    <div class="glass-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
        <h3 style="font-family:var(--font-display); font-size:1.1rem; font-weight:700;">${v.name}</h3>
        <span class="badge ${v.availabilityStatus === 'Available' ? 'badge-success' : 'badge-danger'}">${v.availabilityStatus}</span>
      </div>
      <div style="font-size:0.84rem; color:var(--text-muted); margin-bottom:1rem; display:flex; flex-direction:column; gap:0.4rem;">
        <div>📍 ${v.location}</div>
        <div>👥 Capacity: <strong>${v.capacity} Guests</strong></div>
        <div>💵 Rate: <strong>$${v.pricePerDay.toLocaleString()} / day</strong></div>
      </div>
      <button class="btn ${v.availabilityStatus === 'Available' ? 'btn-primary' : 'btn-secondary'} btn-sm" style="width:100%;" 
        ${v.availabilityStatus === 'Booked' ? 'disabled' : ''} onclick="bookVenue('${v.name}')">
        ${v.availabilityStatus === 'Available' ? 'Book Venue' : 'Currently Booked'}
      </button>
    </div>
  `).join('');
}

// 5. VENDORS VIEW
function renderVendorsView() {
  document.getElementById('vendorsGrid').innerHTML = currentStore.vendors.map(v => `
    <div class="glass-card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
        <h3 style="font-family:var(--font-display); font-size:1.1rem; font-weight:700;">${v.businessName}</h3>
        <span class="badge badge-info">${v.rating}</span>
      </div>
      <div style="font-size:0.84rem; color:var(--text-muted); margin-bottom:1rem; display:flex; flex-direction:column; gap:0.4rem;">
        <div>🛠️ Service: <strong>${v.serviceType}</strong></div>
        <div>💵 Pricing: ${v.pricing}</div>
        <div>📞 Phone: ${v.phone}</div>
      </div>
      <button class="btn btn-secondary btn-sm" style="width:100%;" onclick="requestVendorQuote('${v.businessName}')">Request Quote</button>
    </div>
  `).join('');
}

// 6. BUDGET VIEW
function renderBudgetView() {
  const totalAllocated = currentStore.expenses.reduce((s, x) => s + x.allocated, 0);
  const totalSpent = currentStore.expenses.reduce((s, x) => s + x.spent, 0);
  const totalRemaining = totalAllocated - totalSpent;

  document.getElementById('budgetStatGrid').innerHTML = `
    <div class="stat-card">
      <div class="stat-icon indigo">📊</div>
      <div>
        <div class="stat-label">Total Allocated</div>
        <div class="stat-value">$${totalAllocated.toLocaleString()}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon rose">💵</div>
      <div>
        <div class="stat-label">Total Spent</div>
        <div class="stat-value">$${totalSpent.toLocaleString()}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon emerald">💰</div>
      <div>
        <div class="stat-label">Remaining Balance</div>
        <div class="stat-value">$${totalRemaining.toLocaleString()}</div>
      </div>
    </div>
  `;

  document.getElementById('budgetExpensesTableBody').innerHTML = currentStore.expenses.map(x => `
    <tr>
      <td><strong>${x.category}</strong></td>
      <td>${x.description}</td>
      <td>$${x.allocated.toLocaleString()}</td>
      <td style="color:var(--color-danger);">$${x.spent.toLocaleString()}</td>
      <td style="color:var(--color-success);">$${(x.allocated - x.spent).toLocaleString()}</td>
      <td><span class="badge ${x.status === 'Paid' ? 'badge-success' : 'badge-warning'}">${x.status}</span></td>
    </tr>
  `).join('');
}

// 7. ATTENDEES VIEW
function renderAttendeesView() {
  document.getElementById('attendeeEventsGrid').innerHTML = currentStore.events.map(ev => `
    <div class="glass-card">
      <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem;">
        <span class="badge badge-info">${ev.category}</span>
        <span class="badge badge-success">RSVP Confirmed</span>
      </div>
      <h3 style="font-family:var(--font-display); font-size:1.15rem; font-weight:700; margin-bottom:0.4rem;">${ev.name}</h3>
      <div style="background:rgba(0,0,0,0.3); padding:0.75rem; border-radius:var(--radius-md); font-size:0.82rem; margin-bottom:1rem;">
        <div>📅 Date: ${ev.date} (${ev.startTime})</div>
        <div>📍 Venue: ${ev.venue}</div>
        <div>🎟️ Pass Code: <strong style="color:var(--color-primary-light);">TICK-ERA-${ev.id}88</strong></div>
      </div>
      <button class="btn btn-primary btn-sm" style="width:100%;" onclick="openEventSummaryModal(${ev.id})">Download Digital Pass</button>
    </div>
  `).join('');
}

// 8. DELIVERY VIEW
function renderDeliveryView() {
  document.getElementById('deliveryTableBody').innerHTML = currentStore.deliveries.map(d => `
    <tr>
      <td><strong>${d.partnerId}</strong></td>
      <td>${d.item}</td>
      <td>
        <div style="font-size:0.85rem;">From: ${d.origin}</div>
        <div style="font-size:0.85rem; color:var(--color-primary-light);">To: ${d.destination}</div>
      </td>
      <td>${d.event}</td>
      <td><span class="badge ${d.status === 'Delivered' ? 'badge-success' : d.status === 'In-Transit' ? 'badge-warning' : 'badge-info'}">${d.status}</span></td>
      <td>
        <select class="form-control" style="padding:0.3rem 0.5rem; font-size:0.8rem;" onchange="updateDeliveryStatus(${d.id}, this.value)">
          <option value="Pending" ${d.status === 'Pending' ? 'selected' : ''}>Pending</option>
          <option value="In-Transit" ${d.status === 'In-Transit' ? 'selected' : ''}>In-Transit</option>
          <option value="Delivered" ${d.status === 'Delivered' ? 'selected' : ''}>Delivered</option>
        </select>
      </td>
    </tr>
  `).join('');
}

// 9. CHAT VIEW
function renderChatView() {
  document.getElementById('chatContactsList').innerHTML = currentStore.stakeholders.filter(s => s.role !== currentStore.activeRole).map(s => `
    <div class="chat-contact" onclick="selectChatContact('${s.name}')">
      <div class="user-avatar" style="width:30px; height:30px; font-size:0.75rem;">${s.name.substring(0, 2).toUpperCase()}</div>
      <div>
        <div style="font-size:0.85rem; font-weight:600;">${s.name}</div>
        <div style="font-size:0.7rem; color:var(--text-dim);">${getRoleName(s.role)}</div>
      </div>
    </div>
  `).join('');

  renderChatMessages();
}

function renderChatMessages() {
  document.getElementById('chatMessagesBody').innerHTML = currentStore.chatMessages.map(msg => `
    <div class="message-bubble ${msg.type}">
      <div style="font-size:0.7rem; opacity:0.8; margin-bottom:0.2rem;">${msg.sender} &bull; ${msg.time}</div>
      <div>${msg.text}</div>
    </div>
  `).join('');

  const chatBody = document.getElementById('chatMessagesBody');
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;
}

function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  const newMsg = {
    sender: getRoleName(currentStore.activeRole),
    text: text,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    type: 'outgoing'
  };

  currentStore.chatMessages.push(newMsg);
  saveStore(currentStore);
  input.value = '';
  renderChatMessages();
}

function handleChatEnter(e) { if (e.key === 'Enter') sendChatMessage(); }
function selectChatContact(name) { document.getElementById('activeChatName').textContent = name; }

// 10. ADMIN VIEW
function renderAdminView() {
  document.getElementById('adminStatGrid').innerHTML = `
    <div class="stat-card">
      <div class="stat-icon indigo">👥</div>
      <div>
        <div class="stat-label">Total Stakeholders</div>
        <div class="stat-value">${currentStore.stakeholders.length}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon cyan">🏢</div>
      <div>
        <div class="stat-label">Registered Venues</div>
        <div class="stat-value">${currentStore.venues.length}</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon emerald">🧰</div>
      <div>
        <div class="stat-label">Registered Vendors</div>
        <div class="stat-value">${currentStore.vendors.length}</div>
      </div>
    </div>
  `;

  renderSVGChart();

  document.getElementById('adminUsersTableBody').innerHTML = currentStore.stakeholders.map(u => `
    <tr>
      <td><strong>#USR-${u.id}</strong></td>
      <td>${u.name}</td>
      <td><span class="badge badge-info">${getRoleName(u.role)}</span></td>
      <td>${u.email}</td>
      <td>${u.phone}</td>
      <td><span class="badge badge-success">${u.status}</span></td>
    </tr>
  `).join('');
}

function renderSVGChart() {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const values = [40, 55, 30, 70, 85, 90, 65, 110, 95, 130, 150, 180];
  const max = Math.max(...values);
  const chart = document.getElementById('svgAnalyticsChart');

  chart.innerHTML = months.map((m, i) => {
    const heightPercent = (values[i] / max) * 100;
    return `
      <div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:0.4rem; height:100%; justify-content:flex-end;">
        <div style="font-size:0.72rem; color:var(--color-primary-light); font-weight:700;">$${values[i]}k</div>
        <div style="width:100%; max-width:32px; height:${heightPercent}%; background:linear-gradient(180deg, var(--color-primary), var(--color-secondary)); border-radius:4px 4px 0 0;"></div>
        <div style="font-size:0.72rem; color:var(--text-dim);">${m}</div>
      </div>
    `;
  }).join('');
}

// GENERAL UTILITIES
function handleCreateEvent(e) {
  e.preventDefault();
  const name = document.getElementById('evName').value.trim();
  const category = document.getElementById('evCategory').value;
  const budget = parseFloat(document.getElementById('evBudget').value);
  const date = document.getElementById('evDate').value;
  const startTime = document.getElementById('evStartTime').value;
  const endTime = document.getElementById('evEndTime').value;
  const venue = document.getElementById('evVenue').value;
  const description = document.getElementById('evDescription').value;

  const newEvent = {
    id: Math.floor(100 + Math.random() * 900),
    name, category, budget, date, startTime, endTime, venue, description,
    spent: 0, liveStatus: 'Upcoming', progress: 10
  };

  currentStore.events.unshift(newEvent);
  saveStore(currentStore);
  closeCreateEventModal();
  showToast(`Event "${name}" created successfully!`, 'success');
  renderDashboardApp();
}

function bookVenue(venueName) { showToast(`Booking request submitted for "${venueName}". Pending owner approval.`, 'success'); }
function requestVendorQuote(vendorName) { showToast(`Quote request dispatched to "${vendorName}".`, 'info'); }

function updateDeliveryStatus(id, newStatus) {
  const delivery = currentStore.deliveries.find(d => d.id === id);
  if (delivery) {
    delivery.status = newStatus;
    saveStore(currentStore);
    showToast(`Delivery #${id} updated to ${newStatus}`, 'success');
  }
}

function openEventSummaryModal(eventId) {
  const ev = currentStore.events.find(e => e.id === eventId) || currentStore.events[0];
  document.getElementById('summaryModalTitle').textContent = `Official Event Brief (#${ev.id})`;

  document.getElementById('eventSummaryModalBody').innerHTML = `
    <div style="background:#fff; color:#0f172a; padding:1.75rem; border-radius:12px;">
      <div style="display:flex; justify-content:space-between; border-bottom:2px solid #e2e8f0; padding-bottom:0.75rem; margin-bottom:1rem;">
        <div>
          <h2 style="color:#4f46e5; margin:0; font-size:1.4rem;">ERA Event Document</h2>
          <p style="margin:0; color:#64748b; font-size:0.8rem;">Event Resource & Administration System</p>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:700; font-size:1rem;">${ev.name}</div>
          <div style="font-size:0.8rem; color:#64748b;">${ev.category}</div>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; background:#f8fafc; padding:0.85rem; border-radius:8px; font-size:0.88rem; margin-bottom:1rem;">
        <div><strong>Date:</strong> ${ev.date}</div>
        <div><strong>Time:</strong> ${ev.startTime} - ${ev.endTime}</div>
        <div><strong>Venue:</strong> ${ev.venue}</div>
        <div><strong>Status:</strong> ${ev.liveStatus}</div>
      </div>
      <p style="font-size:0.88rem; color:#475569;">${ev.description}</p>
    </div>
  `;

  document.getElementById('eventSummaryModal').classList.add('active');
}

function closeEventSummaryModal() { document.getElementById('eventSummaryModal').classList.remove('active'); }
function openCreateEventModal() { document.getElementById('createEventModal').classList.add('active'); }
function closeCreateEventModal() { document.getElementById('createEventModal').classList.remove('active'); }

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'danger' ? '❌' : 'ℹ️'}</span><div>${message}</div>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function exportCurrentViewReport() { showToast('Exporting report...', 'success'); openEventSummaryModal(currentStore.events[0].id); }
function handleGlobalSearch(e) { if (e.target.value.trim()) showToast(`Searching for "${e.target.value}"...`, 'info'); }
