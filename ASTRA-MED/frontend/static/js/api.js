/**
 * ASTRA-MED Frontend API Client
 * Fully offline-first HTTP interface to FastAPI backend.
 */

const API = {
  BASE: '/api/v1',

  getToken() {
    return localStorage.getItem('astra_token') || '';
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('astra_token', token);
    } else {
      localStorage.removeItem('astra_token');
    }
  },

  async request(endpoint, options = {}) {
    const url = `${this.BASE}${endpoint}`;
    const headers = {
      'Accept': 'application/json',
      ...(options.headers || {}),
    };

    // If not sending FormData, default to application/json
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    // Auto-attach auth token
    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let errDetail = 'Network response was not ok';
        try {
          const errData = await response.json();
          errDetail = errData.detail || JSON.stringify(errData);
        } catch (_) {
          errDetail = response.statusText;
        }
        throw new Error(errDetail);
      }
      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${options.method || 'GET'} ${url}:`, err);
      throw err;
    }
  },

  get(path) {
    return this.request(path, { method: 'GET' });
  },

  post(path, data) {
    return this.request(path, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  put(path, data = {}) {
    return this.request(path, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // ── Crew ──
  getCrew() {
    return this.get('/crew');
  },
  getCrewMember(id) {
    return this.get(`/crew/${id}`);
  },
  createCrew(data) {
    return this.post('/crew', data);
  },

  // ── Vitals & Telemetry ──
  getVitals(crewId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/vitals/${crewId}${query ? '?' + query : ''}`);
  },
  getLatestVitals(crewId) {
    return this.get(`/vitals/${crewId}/latest`);
  },
  ingestVital(data) {
    return this.post('/vitals/ingest', data);
  },
  ingestBatch(data) {
    return this.post('/vitals/batch', data);
  },

  // ── Alerts ──
  getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/alerts${query ? '?' + query : ''}`);
  },
  getActiveAlerts(crewId = null) {
    const query = crewId ? `?crew_id=${crewId}` : '';
    return this.get(`/alerts/active${query}`);
  },
  acknowledgeAlert(id) {
    return this.put(`/alerts/${id}/acknowledge`);
  },
  getAlertStats() {
    return this.get('/alerts/stats');
  },

  // ── Action Cards ──
  getActionCards(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/action-cards${query ? '?' + query : ''}`);
  },
  getActionCard(id) {
    return this.get(`/action-cards/${id}`);
  },
  getActionCardForAlert(alertId) {
    return this.get(`/action-cards/for-alert/${alertId}`);
  },

  // ── Baselines ──
  getBaselines(crewId) {
    return this.get(`/baselines/${crewId}`);
  },
  freezeBaseline(crewId, metric) {
    return this.post(`/baselines/${crewId}/${encodeURIComponent(metric)}/freeze`);
  },
  unfreezeBaseline(crewId, metric) {
    return this.post(`/baselines/${crewId}/${encodeURIComponent(metric)}/unfreeze`);
  },

  // ── BioSamples ──
  ingestBlood(data) {
    return this.post('/biosample/blood', data);
  },
  ingestUrine(data) {
    return this.post('/biosample/urine', data);
  },
  ingestSaliva(data) {
    return this.post('/biosample/saliva', data);
  },

  // ── Ground Review & Asynchronous Queue ──
  getGroundQueue() {
    return this.get('/ground/queue');
  },
  getQueueDepth() {
    return this.get('/ground/queue/depth');
  },
  syncEncounter(id) {
    return this.post(`/ground/sync/${id}`);
  },
  submitReview(data) {
    return this.post('/ground/review', data);
  },
  getReviewsForEncounter(encounterId) {
    return this.get(`/ground/reviews/${encounterId}`);
  },

  // ── ML Inference ──
  mlPredict(moduleName, data) {
    return this.post(`/ml/${moduleName}/predict`, data);
  },
  mlHealth() {
    return this.get('/ml/health');
  },
  mlModuleHealth(moduleName) {
    return this.get(`/ml/${moduleName}/health`);
  },

  // ── System Status ──
  getStatus() {
    return this.get('/status');
  },
  getSystemHealth() {
    return this.get('/health');
  },

  // ── Insight Engine ──
  getInsights(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/insights${query ? '?' + query : ''}`);
  },
  getAstronautInsights(astronautId) {
    return this.get(`/insights/${astronautId}`);
  },
  acknowledgeInsight(insightId) {
    return this.put(`/insights/${insightId}/acknowledge`);
  },

  // ── Action Engine ──
  getActions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/actions${query ? '?' + query : ''}`);
  },
  assignAction(crewId, actionId, notes = '') {
    return this.post('/actions/assign', { crew_id: crewId, action_id: actionId, notes });
  },
  acknowledgeAction(actionId, notes = '') {
    return this.post(`/actions/${encodeURIComponent(actionId)}/acknowledge`, { notes });
  },

  // ── Medical Reports & Asynchronous Telemedicine ──
  getMedicalReports(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`/medical-reports${query ? '?' + query : ''}`);
  },
  getAstronautReports(astronautId) {
    return this.get(`/medical-reports/${astronautId}`);
  },
  createMedicalReport(data) {
    return this.post('/medical-reports', data);
  },
  syncMedicalReport(reportId) {
    return this.post(`/medical-reports/${reportId}/sync`);
  },
  reviewMedicalReport(reportId, data) {
    return this.post(`/medical-reports/${reportId}/review`, data);
  },

  // ── Unified Measurements & Astronauts ──
  getAstronauts() {
    return this.get('/astronauts');
  },
  getAstronautOverview(astronautId) {
    return this.get(`/astronauts/${astronautId}/overview`);
  },
  ingestMeasurement(data) {
    return this.post('/measurements', data);
  },
  // ── Authentication & Astronaut Identity ──
  async login(username, password) {
    const res = await this.post('/auth/login', { username, password });
    if (res.access_token) {
      this.setToken(res.access_token);
      localStorage.setItem('astra_user', JSON.stringify(res));
    }
    return res;
  },
  logout() {
    this.setToken('');
    localStorage.removeItem('astra_user');
  },
  getCurrentUser() {
    return this.get('/auth/me');
  },
  getStoredUser() {
    try {
      const u = localStorage.getItem('astra_user');
      return u ? JSON.parse(u) : null;
    } catch (_) {
      return null;
    }
  },

  // ── Health Checkups & Medical Records ──
  getHealthCheckups(astronautId) {
    return this.get(`/health-checkups/${astronautId}`);
  },
  getHealthCheckupDetail(checkupId) {
    return this.get(`/health-checkups/${checkupId}`);
  },
  submitHealthCheckup(data) {
    return this.post('/health-checkups', data);
  },
  updateHealthCheckup(checkupId, data) {
    return this.put(`/health-checkups/${checkupId}`, data);
  },
  addCheckupMeasurements(checkupId, measurements) {
    return this.post(`/health-checkups/${checkupId}/measurements`, measurements);
  },
  uploadCheckupFiles(checkupId, formData) {
    return this.request(`/health-checkups/${checkupId}/files`, {
      method: 'POST',
      body: formData,
    });
  },
  getMyHealthHistory() {
    return this.get('/astronauts/me/health-history');
  },
  getMyLatestCheckup() {
    return this.get('/astronauts/me/latest-checkup');
  },
  getMedicalFileStatus(fileId) {
    return this.get(`/medical-files/${fileId}/status`);
  },

  // ── Offline Submission Buffer / Queue ──
  getOfflineQueue() {
    try {
      return JSON.parse(localStorage.getItem('astra_offline_checkups') || '[]');
    } catch (_) {
      return [];
    }
  },
  saveOfflineCheckup(data) {
    const queue = this.getOfflineQueue();
    queue.push({
      ...data,
      saved_at: new Date().toISOString(),
      offline_status: 'pending_synchronization',
    });
    localStorage.setItem('astra_offline_checkups', JSON.stringify(queue));
    return queue.length;
  },
  clearOfflineQueue() {
    localStorage.removeItem('astra_offline_checkups');
  },
  async syncOfflineCheckups() {
    const queue = this.getOfflineQueue();
    if (queue.length === 0) return { synced: 0, failed: 0 };
    let synced = 0;
    let failed = 0;
    const remaining = [];
    for (const item of queue) {
      try {
        await this.submitHealthCheckup(item);
        synced++;
      } catch (err) {
        failed++;
        remaining.push(item);
      }
    }
    localStorage.setItem('astra_offline_checkups', JSON.stringify(remaining));
    return { synced, failed, remaining: remaining.length };
  },
};
