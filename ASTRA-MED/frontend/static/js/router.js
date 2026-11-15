/**
 * ASTRA-MED Hash-Based SPA Router
 * Zero dependencies, works 100% offline.
 */

const Router = {
  routes: {},
  currentRoute: null,

  register(path, handler) {
    this.routes[path] = handler;
  },

  navigate(path) {
    window.location.hash = path.startsWith('#') ? path : `#${path}`;
  },

  async handleRouteChange() {
    const rawHash = window.location.hash.slice(1) || '/dashboard';
    const cleanPath = rawHash.startsWith('/') ? rawHash : `/${rawHash}`;

    // Extract path and query
    const [pathPart, queryPart] = cleanPath.split('?');
    const routeKey = pathPart || '/dashboard';

    // Update active nav link
    const baseRoute = routeKey.replace(/^\//, '');
    document.querySelectorAll('.nav-link').forEach((link) => {
      const target = link.getAttribute('data-route');
      if (target === baseRoute || (baseRoute === '' && target === 'dashboard')) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    const handler = this.routes[routeKey] || this.routes['/dashboard'];
    if (handler) {
      this.currentRoute = routeKey;
      const appEl = document.getElementById('app');
      if (appEl) {
        appEl.innerHTML = '<div class="loading-spinner">Loading telemetry...</div>';
        try {
          await handler(queryPart ? new URLSearchParams(queryPart) : new URLSearchParams());
        } catch (err) {
          console.error(`[Router Error] Route ${routeKey}:`, err);
          appEl.innerHTML = `
            <div class="error-container">
              <h2>Error Loading Screen</h2>
              <p>${err.message}</p>
              <button class="btn btn-teal" onclick="Router.navigate('/dashboard')">Return to Dashboard</button>
            </div>
          `;
        }
      }
    }
  },

  init() {
    window.addEventListener('hashchange', () => this.handleRouteChange());
    window.addEventListener('DOMContentLoaded', () => {
      // Close modal on escape
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') Components.closeModal();
      });

      // Mobile sidebar toggle
      const toggle = document.getElementById('sidebar-toggle');
      const sidebar = document.getElementById('sidebar');
      if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
          sidebar.classList.toggle('open');
        });
      }

      this.handleRouteChange();
    });
  },
};

window.Router = Router;
