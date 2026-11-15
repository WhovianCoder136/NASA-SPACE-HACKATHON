/**
 * ASTRA-MED Single Page Application
 * Core screens, controllers, event bindings, and interactive telemetry views.
 */

// Active authenticated astronaut session
let activeUser = API.getStoredUser() || {
  id: 1,
  astronaut_id: 'ASTRA-001',
  name: 'CDR Sarah Chen, MD',
  role: 'Mission Commander & Flight Medical Officer',
  mission_id: 'ASTRA-1',
  is_medical_officer: true,
};

// Global selected crew member ID (defaults to activeUser id)
let currentCrewId = activeUser.id || 1;

// Selected files for medical report uploads
let selectedCheckupFiles = [];

const routeTitles = {
  '/dashboard': 'Mission Dashboard',
  '/crew': 'Astronaut Roster',
  '/cardiovascular': 'Cardiovascular Telemetry',
  '/immune': 'Immune Biomarkers',
  '/metabolic': 'Metabolic Health',
  '/radiation': 'Radiation Dosimetry',
  '/sleep': 'Sleep & Circadian Rhythms',
  '/neuromuscular': 'Neuromuscular Assessment',
  '/sans': 'SANS Neuro-Ocular Axis',
  '/health-checkup': 'Health Checkup Intake',
  '/health-records': 'Medical Dossier & Records',
  '/insights': 'Clinical Insights Centre',
  '/action-cards': 'Clinical Protocols & Action Cards',
  '/medical-comms': 'Earth Medical Comms',
  '/alerts': 'Active Physiological Alerts',
  '/baselines': 'Physiological Baselines',
  '/biosamples': 'BioSample Inventory',
  '/ground-review': 'Ground Telemedicine Review',
};

window.updateHeaderBreadcrumb = () => {
  const rawHash = (window.location.hash.slice(1) || '/dashboard').split('?')[0];
  const cleanPath = rawHash.startsWith('/') ? rawHash : `/${rawHash}`;
  const title = routeTitles[cleanPath] || 'Mission Operations';
  const el = document.getElementById('header-breadcrumb');
  if (el) el.textContent = title;
};

window.addEventListener('hashchange', () => window.updateHeaderBreadcrumb());
window.addEventListener('DOMContentLoaded', () => {
  window.updateSessionBadge();
  window.updateHeaderBreadcrumb();
});

window.updateSessionBadge = () => {
  const nameEl = document.getElementById('session-astronaut-name');
  const idEl = document.getElementById('session-astronaut-id');
  const avatarEl = document.getElementById('session-avatar');
  const hNameEl = document.getElementById('header-user-name');
  const hRoleEl = document.getElementById('header-user-role');
  const hAvatarEl = document.getElementById('header-user-avatar');

  if (activeUser) {
    const initials = (activeUser.name || 'SC')
      .replace(/CDR|PLT|MS|DR|MD|,/g, '')
      .trim()
      .split(/\s+/)
      .map((n) => n[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'SC';

    if (nameEl) nameEl.textContent = activeUser.name;
    if (idEl) idEl.textContent = `${activeUser.astronaut_id} (${activeUser.is_medical_officer ? 'Medical Officer' : 'Astronaut'})`;
    if (avatarEl) avatarEl.textContent = initials;
    if (hNameEl) hNameEl.textContent = activeUser.name;
    if (hRoleEl) hRoleEl.textContent = activeUser.is_medical_officer ? 'Flight Surgeon' : 'Astronaut';
    if (hAvatarEl) hAvatarEl.textContent = initials;
  }
};

window.showAuthModal = () => {
  const modalHtml = `
    <div class="modal-header">
      <h2>Astronaut Identity & Authentication</h2>
      <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
    </div>
    <div style="margin-bottom: 1rem; font-size: 0.85rem; color: var(--text-secondary);">
      Select an authenticated flight crew account or enter credentials. Medical officers possess authorization to submit checkups on behalf of other astronauts.
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.5rem;">
      <div class="card clickable" onclick="window.switchDemoUser('chen')" style="padding: 0.75rem; border: 1px solid ${activeUser.astronaut_id === 'ASTRA-001' ? 'var(--teal)' : 'var(--border-color)'};">
        <strong style="color: var(--teal);">CDR Sarah Chen, MD</strong>
        <div style="font-size: 0.75rem; color: var(--text-muted);">ASTRA-001 | Flight Medical Officer</div>
        <span class="badge badge-green" style="margin-top: 0.5rem; display: inline-block;">Medical Officer Clearance</span>
      </div>
      <div class="card clickable" onclick="window.switchDemoUser('vance')" style="padding: 0.75rem; border: 1px solid ${activeUser.astronaut_id === 'ASTRA-002' ? 'var(--teal)' : 'var(--border-color)'};">
        <strong style="color: #38bdf8;">PLT Marcus Vance</strong>
        <div style="font-size: 0.75rem; color: var(--text-muted);">ASTRA-002 | Pilot / Engineer</div>
        <span class="badge badge-teal" style="margin-top: 0.5rem; display: inline-block;">Crew Astronaut</span>
      </div>
    </div>
    <form onsubmit="window.submitCustomLogin(event)">
      <div class="form-group">
        <label>Username or Astronaut ID</label>
        <input type="text" id="login-user" class="form-input" placeholder="e.g. chen or ASTRA-001" required>
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" id="login-pass" class="form-input" value="password123" required>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick="Components.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-teal">Log In & Authenticate</button>
      </div>
    </form>
  `;
  Components.openModal(modalHtml);
};

window.switchDemoUser = async (username) => {
  try {
    const res = await API.login(username, 'password123');
    activeUser = {
      id: res.astronaut_id === 'ASTRA-001' ? 1 : 2,
      astronaut_id: res.astronaut_id,
      name: res.name,
      role: res.role,
      mission_id: 'ASTRA-1',
      is_medical_officer: res.is_medical_officer,
    };
    currentCrewId = activeUser.id;
    window.updateSessionBadge();
    Components.closeModal();
    Router.handleRouteChange();
  } catch (err) {
    alert(`Login failed: ${err.message}`);
  }
};

window.submitCustomLogin = async (e) => {
  e.preventDefault();
  const u = document.getElementById('login-user').value;
  const p = document.getElementById('login-pass').value;
  try {
    const res = await API.login(u, p);
    activeUser = {
      id: res.astronaut_id === 'ASTRA-001' ? 1 : 2,
      astronaut_id: res.astronaut_id,
      name: res.name,
      role: res.role,
      mission_id: 'ASTRA-1',
      is_medical_officer: res.is_medical_officer,
    };
    currentCrewId = activeUser.id;
    window.updateSessionBadge();
    Components.closeModal();
    Router.handleRouteChange();
  } catch (err) {
    alert(`Authentication failed: ${err.message}`);
  }
};

// ── Global Helper Functions ─────────────────────────────────────────────
window.acknowledgeAlert = async (alertId) => {
  try {
    await API.acknowledgeAlert(alertId);
    if (Router.currentRoute === '/alerts' || Router.currentRoute === '/dashboard' || Router.currentRoute === '/insights') {
      Router.handleRouteChange();
    }
  } catch (e) {
    alert(`Failed to acknowledge alert: ${e.message}`);
  }
};

window.acknowledgeInsight = async (insightId) => {
  try {
    await API.acknowledgeInsight(insightId);
    Router.handleRouteChange();
  } catch (e) {
    alert(`Failed to acknowledge insight: ${e.message}`);
  }
};

window.acknowledgeAction = async (actionId) => {
  try {
    await API.acknowledgeAction(actionId, 'Completed in flight');
    Router.handleRouteChange();
  } catch (e) {
    alert(`Failed to acknowledge action: ${e.message}`);
  }
};

window.syncMedicalReport = async (reportId) => {
  try {
    await API.syncMedicalReport(reportId);
    Router.handleRouteChange();
  } catch (e) {
    alert(`Failed to sync medical report: ${e.message}`);
  }
};

window.openCreateReportModal = () => {
  const modalHtml = `
    <div class="modal-header">
      <h2>Draft Medical Encounter Report</h2>
      <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
    </div>
    <form onsubmit="window.submitCreateReport(event)">
      <div class="form-group">
        <label>Report Title</label>
        <input type="text" id="rep-title" class="form-input" placeholder="e.g. Flight Day 142 Telemetry Review" required>
      </div>
      <div class="form-group">
        <label>Clinical Health Domain</label>
        <select id="rep-domain" class="form-select">
          <option value="general">General Autonomous Flight Health</option>
          <option value="cardiovascular">Cardiovascular & GAR</option>
          <option value="immune">Immune & Hostile Closed Environment</option>
          <option value="metabolic">Metabolic & Chemistry</option>
          <option value="radiation">Radiation Exposure</option>
          <option value="sleep">Sleep & Circadian Rhythm</option>
          <option value="neuromuscular">Sensorimotor & Gait</option>
          <option value="sans">SANS & Neuro-Ocular</option>
        </select>
      </div>
      <div class="form-group">
        <label>Clinical Summary & Findings (Objective Observation)</label>
        <textarea id="rep-summary" class="form-textarea" rows="4" placeholder="Detail observed deviations, applied pre-approved action cards, and astronaut status..." required></textarea>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick="Components.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-teal">Queue for Earth Transmission</button>
      </div>
    </form>
  `;
  Components.openModal(modalHtml);
};

window.submitCreateReport = async (e) => {
  e.preventDefault();
  const title = document.getElementById('rep-title').value;
  const domain = document.getElementById('rep-domain').value;
  const summary = document.getElementById('rep-summary').value;
  try {
    await API.createMedicalReport({
      crew_id: currentCrewId,
      title,
      domain,
      summary,
      requires_physician_review: true,
      future_phase_updates: {},
    });
    Components.closeModal();
    Router.handleRouteChange();
  } catch (err) {
    alert(`Error creating report: ${err.message}`);
  }
};

window.openSurgeonReviewModal = (reportId) => {
  const modalHtml = `
    <div class="modal-header">
      <h2>Simulate Earth Flight Surgeon Review</h2>
      <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
    </div>
    <form onsubmit="window.submitSurgeonReview(event, '${reportId}')">
      <div class="form-group">
        <label>Flight Surgeon Name & Designation</label>
        <input type="text" id="surg-name" class="form-input" value="Dr. Robert Mercer, MD (Houston Ground Surgeon)" required>
      </div>
      <div class="form-group">
        <label>Clinical Decision</label>
        <select id="surg-decision" class="form-select">
          <option value="approved">Approved — Concur with Onboard Action Cards</option>
          <option value="amended">Amended Protocol Guidance</option>
          <option value="escalated">Escalated Monitoring Required</option>
        </select>
      </div>
      <div class="form-group">
        <label>Physician Review Instructions</label>
        <textarea id="surg-comments" class="form-textarea" rows="3" required>Concur with observed physiological baseline deviation countermeasure. Maintain hydration loading and schedule 24-hour repeat standing test.</textarea>
      </div>
      <div class="form-group">
        <label>Approved Future Mission Phase Adaptations (JSON)</label>
        <textarea id="surg-updates" class="form-textarea" rows="2">{"gravity_transition_phase": "TRANSITION_STABILIZED", "daily_exercise_vo2max_target": 80}</textarea>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick="Components.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Transmit Review to Spacecraft</button>
      </div>
    </form>
  `;
  Components.openModal(modalHtml);
};

window.submitSurgeonReview = async (e, reportId) => {
  e.preventDefault();
  const name = document.getElementById('surg-name').value;
  const decision = document.getElementById('surg-decision').value;
  const comments = document.getElementById('surg-comments').value;
  let updates = {};
  try {
    updates = JSON.parse(document.getElementById('surg-updates').value || '{}');
  } catch (_) {
    updates = {};
  }

  try {
    await API.reviewMedicalReport(reportId, {
      physician_name: name,
      decision,
      comments,
      future_phase_updates: updates,
    });
    Components.closeModal();
    Router.handleRouteChange();
  } catch (err) {
    alert(`Error saving review: ${err.message}`);
  }
};

window.toggleBaselineFreeze = async (crewId, metricName, shouldFreeze) => {
  try {
    if (shouldFreeze) {
      await API.freezeBaseline(crewId, metricName);
    } else {
      await API.unfreezeBaseline(crewId, metricName);
    }
    Router.handleRouteChange();
  } catch (e) {
    alert(`Failed to toggle baseline freeze: ${e.message}`);
  }
};

window.syncEncounter = async (encounterId) => {
  try {
    await API.syncEncounter(encounterId);
    Router.handleRouteChange();
  } catch (e) {
    alert(`Sync failed: ${e.message}`);
  }
};

// ── Helper to build crew selector dropdown ──────────────────────────────
async function buildCrewSelector(selectedId, onChangeFnName = 'onCrewChange') {
  const crewList = await API.getCrew();
  if (crewList.length > 0 && !currentCrewId) {
    currentCrewId = crewList[0].id;
  }
  const options = crewList.map((c) => `
    <option value="${c.id}" ${c.id === Number(selectedId || currentCrewId) ? 'selected' : ''}>
      ${c.name} (${c.role})
    </option>
  `).join('');

  return `
    <div class="crew-selector-bar">
      <label for="crew-select">Active Crew Subject:</label>
      <select id="crew-select" class="form-select" onchange="${onChangeFnName}(this.value)">
        ${options}
      </select>
    </div>
  `;
}

window.onCrewChange = (newId) => {
  currentCrewId = Number(newId);
  Router.handleRouteChange();
};

// ═════════════════════════════════════════════════════════════════════════
// 0A. DEDICATED HEALTH CHECKUP & MEDICAL RECORDS INTAKE SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/health-checkup', async () => {
  window.updateSessionBadge();
  selectedCheckupFiles = [];

  // Fetch astronaut profile and previous checkups
  const targetAstronautId = activeUser ? activeUser.astronaut_id : 'ASTRA-001';
  const [history, crewList, latest] = await Promise.all([
    API.getHealthCheckups(targetAstronautId).catch(() => []),
    API.getCrew().catch(() => []),
    API.getMyLatestCheckup().catch(() => null),
  ]);

  const prevDate = latest ? latest.checkup_date : (history.length > 0 ? history[0].checkup_date : 'None logged');
  const totalCount = history.length;
  const offlineQueue = API.getOfflineQueue();

  // Role-based target selector
  const isOfficer = activeUser && activeUser.is_medical_officer;
  let targetSelectorHtml = `
    <div class="form-group" style="margin-bottom: 0;">
      <label>Astronaut Subject ID</label>
      <input type="text" id="chk-target-id" class="form-input" value="${targetAstronautId}" readonly style="background: rgba(15,23,42,0.8); color: var(--teal); font-weight: 600;">
      <span style="font-size: 0.75rem; color: var(--text-muted);">Locked to authenticated session account (${activeUser ? activeUser.name : 'Astronaut'}).</span>
    </div>
  `;

  if (isOfficer && crewList.length > 0) {
    const opts = crewList.map((c) => {
      const aId = c.astronaut_id || `ASTRA-${c.id < 10 ? '00' + c.id : '0' + c.id}`;
      return `<option value="${aId}" ${aId === targetAstronautId ? 'selected' : ''}>${c.name} (${aId}) — ${c.role}</option>`;
    }).join('');

    targetSelectorHtml = `
      <div class="form-group" style="margin-bottom: 0;">
        <label>Astronaut Subject (Medical Officer Proxy Mode)</label>
        <select id="chk-target-id" class="form-select" onchange="window.onProxyTargetChange(this.value)">
          ${opts}
        </select>
        <span style="font-size: 0.75rem; color: var(--teal);">★ Flight Medical Officer clearance active: authorized to enter data for any flight crew member.</span>
      </div>
    `;
  }

  const todayStr = new Date().toISOString().split('T')[0];
  const timeStr = new Date().toTimeString().slice(0, 5);

  const html = `
    <div class="screen-container">
      <!-- Section 2: Header & Session Identity Display -->
      <div class="screen-header" style="align-items: flex-start;">
        <div>
          <h2>Health Checkup & Medical Records Intake</h2>
          <p class="text-secondary">Comprehensive multi-hazard physiological assessment, point-of-care lab intake, and diagnostic report upload.</p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <a href="#/health-records" class="btn btn-outline">📂 View Health History (${totalCount})</a>
          ${offlineQueue.length > 0 ? `
            <button class="btn btn-amber btn-sm" onclick="window.syncOfflineQueue()">Sync Offline Buffer (${offlineQueue.length})</button>
          ` : ''}
        </div>
      </div>

      <!-- Identity & Previous Checkup Status Banner -->
      <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-bottom: 1.5rem;">
        ${Components.renderStatCard('Astronaut ID', activeUser.astronaut_id, '', activeUser.name, 'GREEN')}
        ${Components.renderStatCard('Mission Program', activeUser.mission_id || 'ASTRA-1', '', 'Deep Space Mars Transit')}
        ${Components.renderStatCard('Previous Checkup', prevDate, '', totalCount > 0 ? `${totalCount} previous records on file` : 'Initial checkup')}
        ${Components.renderStatCard('Offline Buffer', offlineQueue.length, 'Records', offlineQueue.length > 0 ? 'Pending Earth / Server Sync' : 'All records synchronized', offlineQueue.length > 0 ? 'AMBER' : 'GREEN')}
      </div>

      <!-- Offline / Online Link Indicator -->
      <div id="checkup-connection-alert" class="mission-bar" style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <span style="font-size: 1.25rem;">🩺</span>
          <div>
            <strong>AUTONOMOUS FLIGHT CHECKUP INTAKE ACTIVE</strong>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              Data is validated against your individual nominal baseline. In case of network disconnection, records are safely preserved in your spacecraft local buffer.
            </div>
          </div>
        </div>
        <span class="badge badge-green">LOCAL ENGINE READY</span>
      </div>

      <!-- Section 3: Structured Health Checkup Form -->
      <form id="health-checkup-form" onsubmit="window.submitRecentCheckup(event)">
        
        <!-- A. Checkup Metadata Box -->
        <div class="card" style="margin-bottom: 1.5rem;">
          <h3 style="margin-bottom: 1rem; color: var(--teal); display: flex; align-items: center; gap: 0.5rem;">
            <span>📋</span> A. Checkup Information
          </h3>
          <div class="two-column-layout" style="gap: 1rem;">
            <div>
              ${targetSelectorHtml}
              <div class="form-row" style="margin-top: 1rem;">
                <div class="form-group">
                  <label>Checkup Date *</label>
                  <input type="date" id="chk-date" class="form-input" value="${todayStr}" required>
                </div>
                <div class="form-group">
                  <label>Checkup Time</label>
                  <input type="time" id="chk-time" class="form-input" value="${timeStr}">
                </div>
              </div>
            </div>
            <div>
              <div class="form-group">
                <label>Checkup Type *</label>
                <select id="chk-type" class="form-select" onchange="window.highlightCheckupSections(this.value)" required>
                  <option value="Routine health checkup">Routine health checkup (Comprehensive)</option>
                  <option value="Cardiovascular assessment">Cardiovascular assessment</option>
                  <option value="Blood test">Blood test (CBC & Biomarkers)</option>
                  <option value="Immune assessment">Immune assessment</option>
                  <option value="Metabolic assessment">Metabolic assessment (CMP)</option>
                  <option value="Radiation assessment">Radiation assessment & Dosimetry</option>
                  <option value="Neuromuscular assessment">Neuromuscular assessment & Gait</option>
                  <option value="Vision and ocular assessment">Vision and ocular assessment (SANS)</option>
                  <option value="Other">Other Specialized Evaluation</option>
                </select>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>Testing Location / Medical Bay</label>
                  <input type="text" id="chk-location" class="form-input" value="Mars Transit Hab — Clinical Station">
                </div>
                <div class="form-group">
                  <label>Medical Officer Name (Optional)</label>
                  <input type="text" id="chk-officer" class="form-input" placeholder="e.g. CDR Sarah Chen, MD">
                </div>
              </div>
            </div>
          </div>
          <div class="form-group" style="margin-top: 0.5rem;">
            <label>General Clinical Notes / Astronaut Observations</label>
            <textarea id="chk-notes" class="form-textarea" rows="2" placeholder="Record qualitative physical symptoms, subjective fatigue, exercise tolerance, or checkup context..."></textarea>
          </div>
        </div>

        <!-- Section Navigation Tabs for Available Health Domains -->
        <div style="background: rgba(30, 41, 59, 0.4); padding: 0.5rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid var(--border-color);">
          <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; font-weight: 600;">
            Select Health Assessment Modules to Enter (Enter only what is available from your actual checkup):
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button type="button" class="btn btn-xs btn-teal" onclick="window.toggleSectionBox('sec-basic')">Vitals (Basic)</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-cardio')">Cardiovascular</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-blood')">Blood & Immune</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-metabolic')">Metabolic Panel</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-radiation')">Radiation</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-sleep')">Sleep & Circadian</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-neuromuscular')">Neuromuscular</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-sans')">SANS & Ocular</button>
            <button type="button" class="btn btn-xs btn-outline" onclick="window.toggleSectionBox('sec-upload')">📁 Upload Files</button>
          </div>
        </div>

        <!-- B. Basic Physiological Measurements -->
        <div id="sec-basic" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
            <span>❤️ B. Basic Physiological Measurements</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">All fields optional unless part of your scheduled checkup</span>
          </h3>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">
            Non-Diagnostic Notice: Entered values are objective physiological observations evaluated against your personal baseline and will not be autonomously diagnosed.
          </p>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Heart Rate (BPM)</label>
              <input type="number" step="1" id="m-hr" class="form-input" placeholder="e.g. 74" min="25" max="250">
            </div>
            <div class="form-group">
              <label>Systolic Blood Pressure (mmHg)</label>
              <input type="number" step="1" id="m-bpsys" class="form-input" placeholder="e.g. 118" min="40" max="300">
            </div>
            <div class="form-group">
              <label>Diastolic Blood Pressure (mmHg)</label>
              <input type="number" step="1" id="m-bpdia" class="form-input" placeholder="e.g. 76" min="30" max="200">
            </div>
            <div class="form-group">
              <label>Body Temperature (°C)</label>
              <input type="number" step="0.1" id="m-temp" class="form-input" placeholder="e.g. 36.6" min="30" max="45">
            </div>
            <div class="form-group">
              <label>Respiratory Rate (breaths/min)</label>
              <input type="number" step="1" id="m-resp" class="form-input" placeholder="e.g. 14" min="4" max="60">
            </div>
            <div class="form-group">
              <label>Oxygen Saturation (SpO2 %)</label>
              <input type="number" step="0.1" id="m-spo2" class="form-input" placeholder="e.g. 98.5" min="50" max="100">
            </div>
            <div class="form-group">
              <label>Body Weight (kg)</label>
              <input type="number" step="0.1" id="m-weight" class="form-input" placeholder="e.g. 72.5" min="30" max="200">
            </div>
            <div class="form-group">
              <label>Standing Height (cm)</label>
              <input type="number" step="0.5" id="m-height" class="form-input" placeholder="e.g. 178" min="100" max="250">
            </div>
          </div>
        </div>

        <!-- C. Cardiovascular Data -->
        <div id="sec-cardio" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">🫀 C. Cardiovascular Data (GAR & Hemodynamics)</h3>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">Supports resting hemodynamics, beat-to-beat ECG intervals, and orthostatic tolerance testing.</p>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Resting Heart Rate (BPM)</label>
              <input type="number" step="1" id="m-rhr" class="form-input" placeholder="e.g. 68">
            </div>
            <div class="form-group">
              <label>HRV RMSSD (ms)</label>
              <input type="number" step="0.1" id="m-hrv" class="form-input" placeholder="e.g. 42.5">
            </div>
            <div class="form-group">
              <label>Postural State During Assessment</label>
              <select id="m-cardio-posture" class="form-select">
                <option value="supine">Supine (Microgravity rest)</option>
                <option value="seated">Seated transition</option>
                <option value="standing">Upright standing challenge</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Cardiovascular Assessment Notes</label>
            <input type="text" id="m-cardio-notes" class="form-input" placeholder="e.g. Nominal sinus rhythm; orthostatic challenge test completed without presyncope.">
          </div>
        </div>

        <!-- D. Blood and Immune Data -->
        <div id="sec-blood" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">🩸 D. Blood & Immune Laboratory Data</h3>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">Enter CBC and immune biomarkers (NASA OSD-575 reference panel).</p>
          <div class="form-grid-3">
            <div class="form-group">
              <label>WBC Count (x10³/μL)</label>
              <input type="number" step="0.1" id="m-wbc" class="form-input" placeholder="e.g. 6.5">
            </div>
            <div class="form-group">
              <label>Neutrophil Count (%)</label>
              <input type="number" step="0.1" id="m-neut" class="form-input" placeholder="e.g. 62.0">
            </div>
            <div class="form-group">
              <label>Lymphocyte Count (%)</label>
              <input type="number" step="0.1" id="m-lymph" class="form-input" placeholder="e.g. 29.5">
            </div>
            <div class="form-group">
              <label>Monocyte Count (%)</label>
              <input type="number" step="0.1" id="m-mono" class="form-input" placeholder="e.g. 6.0">
            </div>
            <div class="form-group">
              <label>Eosinophil Count (%)</label>
              <input type="number" step="0.1" id="m-eos" class="form-input" placeholder="e.g. 2.0">
            </div>
            <div class="form-group">
              <label>Basophil Count (%)</label>
              <input type="number" step="0.1" id="m-baso" class="form-input" placeholder="e.g. 0.5">
            </div>
            <div class="form-group">
              <label>Hemoglobin (g/dL)</label>
              <input type="number" step="0.1" id="m-hb" class="form-input" placeholder="e.g. 15.2">
            </div>
            <div class="form-group">
              <label>Platelet Count (x10³/μL)</label>
              <input type="number" step="1" id="m-plt" class="form-input" placeholder="e.g. 245">
            </div>
            <div class="form-group">
              <label>IL-6 Cytokine (pg/mL)</label>
              <input type="number" step="0.1" id="m-il6" class="form-input" placeholder="e.g. 1.8">
            </div>
            <div class="form-group">
              <label>TNF-α Cytokine (pg/mL)</label>
              <input type="number" step="0.1" id="m-tnf" class="form-input" placeholder="e.g. 3.2">
            </div>
          </div>
        </div>

        <!-- E. Metabolic Data -->
        <div id="sec-metabolic" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">⚗️ E. Metabolic & Chemistry Data (CMP)</h3>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">Renal clearance, electrolyte balance, and bone mineral markers.</p>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Fasting Glucose (mg/dL)</label>
              <input type="number" step="1" id="m-glu" class="form-input" placeholder="e.g. 92">
            </div>
            <div class="form-group">
              <label>Serum Sodium (mEq/L)</label>
              <input type="number" step="1" id="m-na" class="form-input" placeholder="e.g. 140">
            </div>
            <div class="form-group">
              <label>Serum Potassium (mEq/L)</label>
              <input type="number" step="0.1" id="m-k" class="form-input" placeholder="e.g. 4.2">
            </div>
            <div class="form-group">
              <label>Serum Calcium (mg/dL)</label>
              <input type="number" step="0.1" id="m-ca" class="form-input" placeholder="e.g. 9.4">
            </div>
            <div class="form-group">
              <label>Serum Creatinine (mg/dL)</label>
              <input type="number" step="0.01" id="m-cr" class="form-input" placeholder="e.g. 0.92">
            </div>
            <div class="form-group">
              <label>Blood Urea Nitrogen (mg/dL)</label>
              <input type="number" step="1" id="m-bun" class="form-input" placeholder="e.g. 14">
            </div>
          </div>
        </div>

        <!-- F. Radiation Data -->
        <div id="sec-radiation" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">☢️ F. Radiation Dosimetry Data</h3>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Daily Exposure Rate (mSv/day)</label>
              <input type="number" step="0.01" id="m-rad-rate" class="form-input" placeholder="e.g. 1.42">
            </div>
            <div class="form-group">
              <label>Cumulative Mission Dose (mSv)</label>
              <input type="number" step="0.1" id="m-rad-cum" class="form-input" placeholder="e.g. 168.4">
            </div>
            <div class="form-group">
              <label>γ-H2AX Foci (foci/cell)</label>
              <input type="number" step="0.1" id="m-rad-h2ax" class="form-input" placeholder="e.g. 1.2">
            </div>
          </div>
        </div>

        <!-- G. Sleep and Circadian Data -->
        <div id="sec-sleep" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">🌙 G. Sleep & Circadian Data</h3>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Sleep Duration (hours)</label>
              <input type="number" step="0.1" id="m-slp-dur" class="form-input" placeholder="e.g. 7.4">
            </div>
            <div class="form-group">
              <label>Sleep Quality Score (1 - 100)</label>
              <input type="number" step="1" id="m-slp-qual" class="form-input" placeholder="e.g. 88">
            </div>
            <div class="form-group">
              <label>REM Sleep (%)</label>
              <input type="number" step="0.1" id="m-slp-rem" class="form-input" placeholder="e.g. 22.0">
            </div>
            <div class="form-group">
              <label>Deep Sleep (%)</label>
              <input type="number" step="0.1" id="m-slp-deep" class="form-input" placeholder="e.g. 18.0">
            </div>
            <div class="form-group">
              <label>Awakenings / Interruptions</label>
              <input type="number" step="1" id="m-slp-wake" class="form-input" placeholder="e.g. 1">
            </div>
            <div class="form-group">
              <label>Circadian Phase Drift (hours)</label>
              <input type="number" step="0.1" id="m-slp-drift" class="form-input" placeholder="e.g. 0.2">
            </div>
          </div>
        </div>

        <!-- H. Neuromuscular Data -->
        <div id="sec-neuromuscular" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">💪 H. Neuromuscular & Sensorimotor Data</h3>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Dynamic Gait Symmetry (%)</label>
              <input type="number" step="0.1" id="m-neu-sym" class="form-input" placeholder="e.g. 96.2">
            </div>
            <div class="form-group">
              <label>Postural Sway Velocity (cm/s)</label>
              <input type="number" step="0.1" id="m-neu-sway" class="form-input" placeholder="e.g. 1.8">
            </div>
            <div class="form-group">
              <label>PVT Median Reaction Time (ms)</label>
              <input type="number" step="1" id="m-neu-rt" class="form-input" placeholder="e.g. 242">
            </div>
          </div>
        </div>

        <!-- I. SANS / Ocular Data -->
        <div id="sec-sans" class="card checkup-section-card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem;">👁️ I. SANS & Neuro-Ocular Data</h3>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Optic Nerve Sheath Diameter (mm)</label>
              <input type="number" step="0.1" id="m-sans-onsd" class="form-input" placeholder="e.g. 5.1">
            </div>
            <div class="form-group">
              <label>RNFL Thickness (μm)</label>
              <input type="number" step="1" id="m-sans-rnfl" class="form-input" placeholder="e.g. 104">
            </div>
            <div class="form-group">
              <label>Intraocular Pressure (mmHg)</label>
              <input type="number" step="0.1" id="m-sans-iop" class="form-input" placeholder="e.g. 15.2">
            </div>
          </div>
        </div>

        <!-- Section 4: Supporting Medical Report Upload System -->
        <div id="sec-upload" class="card" style="margin-bottom: 1.5rem;">
          <h3 style="color: var(--teal); margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
            <span>📁 Supporting Medical Reports & Diagnostic Files</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">PDF, DICOM, Images, ECG Waveforms</span>
          </h3>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">
            Upload existing health checkup reports or sensor logs. The system stores original documents with SHA-256 integrity validation and parses text for human review.
          </p>
          ${Components.renderMedicalFileUploadZone('checkup-dropzone', 'checkup-files-input')}
        </div>

        <!-- Form Submission Actions -->
        <div class="form-actions" style="display: flex; justify-content: flex-end; gap: 1rem; align-items: center;">
          <button type="reset" class="btn btn-secondary" onclick="window.resetCheckupForm()">Clear Form</button>
          <button type="submit" id="submit-checkup-btn" class="btn btn-teal btn-lg" style="padding: 0.75rem 2rem; font-size: 1rem;">
            Submit Health Checkup & Update Baseline &rarr;
          </button>
        </div>
      </form>

      <!-- Confirmation Screen Overlay / Container -->
      <div id="checkup-confirmation-container" class="hidden" style="margin-top: 1.5rem;"></div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

// ── Form Helper Functions ───────────────────────────────────────────────

window.toggleSectionBox = (secId) => {
  const el = document.getElementById(secId);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.style.borderColor = 'var(--teal)';
    setTimeout(() => { el.style.borderColor = ''; }, 1200);
  }
};

window.highlightCheckupSections = (checkupType) => {
  // Highlight relevant section based on selected checkup type
  const typeMap = {
    'Cardiovascular assessment': 'sec-cardio',
    'Blood test': 'sec-blood',
    'Immune assessment': 'sec-blood',
    'Metabolic assessment': 'sec-metabolic',
    'Radiation assessment': 'sec-radiation',
    'Neuromuscular assessment': 'sec-neuromuscular',
    'Vision and ocular assessment': 'sec-sans',
  };
  const targetId = typeMap[checkupType] || 'sec-basic';
  window.toggleSectionBox(targetId);
};

window.onProxyTargetChange = (newTargetAstronautId) => {
  console.log(`[Proxy] Target astronaut changed to ${newTargetAstronautId}`);
};

window.handleCheckupFileSelect = (event) => {
  const files = Array.from(event.target.files || []);
  const listContainer = document.getElementById('selected-files-list');

  for (const f of files) {
    // Validate size (100MB)
    if (f.size > 100 * 1024 * 1024) {
      alert(`File '${f.name}' exceeds the 100 MB limit.`);
      continue;
    }
    // Prevent duplicate additions
    if (!selectedCheckupFiles.some((x) => x.name === f.name && x.size === f.size)) {
      selectedCheckupFiles.push(f);
    }
  }

  window.renderSelectedFilesList();
};

window.renderSelectedFilesList = () => {
  const listContainer = document.getElementById('selected-files-list');
  if (!listContainer) return;

  if (selectedCheckupFiles.length === 0) {
    listContainer.innerHTML = '';
    return;
  }

  const itemsHtml = selectedCheckupFiles.map((f, idx) => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; background: rgba(30, 41, 59, 0.6); border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 0.35rem; font-size: 0.85rem;">
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span>📎</span>
        <strong>${f.name}</strong>
        <span class="text-muted">(${(f.size / 1024).toFixed(1)} KB)</span>
      </div>
      <button type="button" class="btn btn-outline btn-xs" style="color: var(--red); border-color: var(--red);" onclick="window.removeSelectedFile(${idx})">&times; Remove</button>
    </div>
  `).join('');

  listContainer.innerHTML = `
    <div style="font-weight: 600; font-size: 0.8rem; color: var(--teal); margin-bottom: 0.25rem;">
      Files Staged for Upload (${selectedCheckupFiles.length}):
    </div>
    ${itemsHtml}
  `;
};

window.removeSelectedFile = (idx) => {
  selectedCheckupFiles.splice(idx, 1);
  window.renderSelectedFilesList();
};

window.resetCheckupForm = () => {
  selectedCheckupFiles = [];
  window.renderSelectedFilesList();
};

// ── Submit Checkup Handler ──────────────────────────────────────────────

window.submitRecentCheckup = async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById('submit-checkup-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Submitting & Routing to ML Engines...';
  }

  const astronautId = document.getElementById('chk-target-id').value;
  const checkupDate = document.getElementById('chk-date').value;
  const checkupTime = document.getElementById('chk-time').value;
  const location = document.getElementById('chk-location').value;
  const officer = document.getElementById('chk-officer').value;
  const checkupType = document.getElementById('chk-type').value;
  const notes = document.getElementById('chk-notes').value;

  // Gather discrete measurements
  const measurements = [];
  const addM = (dom, metric, elId, unit, ref) => {
    const el = document.getElementById(elId);
    if (el && el.value !== '' && !isNaN(parseFloat(el.value))) {
      measurements.push({
        domain: dom,
        metric_name: metric,
        value: parseFloat(el.value),
        unit: unit,
        reference_range: ref || null,
        data_source: 'manual_entry',
      });
    }
  };

  // Basic
  addM('basic', 'heart_rate', 'm-hr', 'bpm', '60 - 100');
  addM('basic', 'bp_systolic', 'm-bpsys', 'mmHg', '90 - 120');
  addM('basic', 'bp_diastolic', 'm-bpdia', 'mmHg', '60 - 80');
  addM('basic', 'temperature', 'm-temp', '°C', '36.1 - 37.2');
  addM('basic', 'respiratory_rate', 'm-resp', 'breaths/min', '12 - 20');
  addM('basic', 'spo2', 'm-spo2', '%', '95 - 100');
  addM('basic', 'weight', 'm-weight', 'kg');
  addM('basic', 'height', 'm-height', 'cm');

  // Cardio
  addM('cardiovascular', 'resting_heart_rate', 'm-rhr', 'bpm', '55 - 75');
  addM('cardiovascular', 'hrv_rmssd', 'm-hrv', 'ms', '30 - 80');

  // Blood & Immune
  addM('immune', 'wbc_count', 'm-wbc', 'x10³/μL', '4.5 - 11.0');
  addM('immune', 'neutrophil_pct', 'm-neut', '%', '40 - 70');
  addM('immune', 'lymphocyte_pct', 'm-lymph', '%', '20 - 45');
  addM('immune', 'monocyte_pct', 'm-mono', '%', '2 - 8');
  addM('immune', 'eosinophil_pct', 'm-eos', '%', '1 - 4');
  addM('immune', 'basophil_pct', 'm-baso', '%', '0.5 - 1.0');
  addM('immune', 'hemoglobin', 'm-hb', 'g/dL', '13.8 - 17.2');
  addM('immune', 'platelets', 'm-plt', 'x10³/μL', '150 - 450');
  addM('immune', 'il6', 'm-il6', 'pg/mL', '< 5.0');
  addM('immune', 'tnf_alpha', 'm-tnf', 'pg/mL', '< 8.0');

  // Metabolic
  addM('metabolic', 'glucose', 'm-glu', 'mg/dL', '70 - 100');
  addM('metabolic', 'sodium', 'm-na', 'mEq/L', '135 - 145');
  addM('metabolic', 'potassium', 'm-k', 'mEq/L', '3.5 - 5.0');
  addM('metabolic', 'calcium', 'm-ca', 'mg/dL', '8.5 - 10.5');
  addM('metabolic', 'creatinine', 'm-cr', 'mg/dL', '0.7 - 1.3');
  addM('metabolic', 'bun', 'm-bun', 'mg/dL', '7 - 20');

  // Radiation
  addM('radiation', 'radiation_dose_rate', 'm-rad-rate', 'mSv/day', '< 1.5');
  addM('radiation', 'cumulative_dose_msv', 'm-rad-cum', 'mSv', '< 600');
  addM('radiation', 'gamma_h2ax', 'm-rad-h2ax', 'foci/cell', '< 1.5');

  // Sleep
  addM('sleep', 'sleep_duration_hours', 'm-slp-dur', 'hours', '7.0 - 8.5');
  addM('sleep', 'sleep_quality_score', 'm-slp-qual', 'score', '80 - 100');
  addM('sleep', 'rem_pct', 'm-slp-rem', '%', '20 - 25');
  addM('sleep', 'deep_sleep_pct', 'm-slp-deep', '%', '15 - 20');
  addM('sleep', 'awakenings', 'm-slp-wake', 'count', '0 - 2');
  addM('sleep', 'circadian_phase_shift_h', 'm-slp-drift', 'hours', '< 1.0');

  // Neuromuscular
  addM('neuromuscular', 'gait_symmetry', 'm-neu-sym', '%', '95 - 100');
  addM('neuromuscular', 'sway_velocity', 'm-neu-sway', 'cm/s', '< 2.2');
  addM('neuromuscular', 'reaction_time_ms', 'm-neu-rt', 'ms', '< 260');

  // SANS
  addM('sans', 'optic_disc_diameter', 'm-sans-onsd', 'mm', '< 5.8');
  addM('sans', 'rnfl_thickness', 'm-sans-rnfl', 'μm', '90 - 110');
  addM('sans', 'iop', 'm-sans-iop', 'mmHg', '12 - 20');

  const idempotencyKey = `IDEMP-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
  const checkupPayload = {
    astronaut_id: astronautId,
    checkup_date: checkupDate,
    checkup_time: checkupTime,
    location: location,
    medical_officer: officer,
    checkup_type: checkupType,
    notes: notes,
    idempotency_key: idempotencyKey,
    measurements: measurements,
  };

  try {
    // 1. Submit checkup to FastAPI
    const confirmation = await API.submitHealthCheckup(checkupPayload);

    // 2. Upload any staged files
    let uploadedCount = 0;
    if (selectedCheckupFiles.length > 0) {
      const formData = new FormData();
      for (const file of selectedCheckupFiles) {
        formData.append('files', file);
      }
      formData.append('health_module', checkupType.toLowerCase());
      const uploadRes = await API.uploadCheckupFiles(confirmation.checkup_id, formData);
      uploadedCount = uploadRes.length;
    }

    // 3. Display Section 9 Confirmation Screen
    window.renderCheckupConfirmation({
      ...confirmation,
      files_uploaded: uploadedCount,
    });
  } catch (err) {
    console.error('Submission failed, buffering locally:', err);
    // Offline fallback per Section 12
    API.saveOfflineCheckup(checkupPayload);
    alert(`Server submission failed (${err.message}). Checkup has been safely stored in your local spacecraft offline buffer and will be synchronized when connectivity resumes.`);
    Router.navigate('/health-records');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Health Checkup & Update Baseline &rarr;';
    }
  }
};

window.renderCheckupConfirmation = (conf) => {
  const formEl = document.getElementById('health-checkup-form');
  if (formEl) formEl.classList.add('hidden');

  const confContainer = document.getElementById('checkup-confirmation-container');
  if (!confContainer) return;
  confContainer.classList.remove('hidden');

  const modulesProcessedHtml = (conf.modules_processed || []).map((m) => `
    <span class="badge badge-green" style="margin-right: 0.5rem; margin-bottom: 0.5rem;">✓ ${m.toUpperCase()}</span>
  `).join('') || '<span class="text-muted">No ML models triggered</span>';

  const warningsHtml = (conf.validation_warnings || []).map((w) => `
    <div style="font-size: 0.85rem; color: var(--amber); margin-bottom: 0.25rem;">▲ ${w}</div>
  `).join('') || '<div class="text-muted" style="font-size: 0.85rem;">All measurements passed clinical validity boundaries.</div>';

  confContainer.innerHTML = `
    <div class="card" style="border: 1px solid var(--teal); background: linear-gradient(135deg, rgba(20, 184, 166, 0.08), rgba(15, 23, 42, 0.9)); padding: 2rem;">
      <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
        <span style="font-size: 2.5rem;">✅</span>
        <div>
          <h2 style="margin: 0; color: var(--teal);">${conf.status}</h2>
          <div style="color: var(--text-secondary); font-size: 0.9rem;">
            Checkup ID: <code>${conf.checkup_id}</code> | Subject: <strong>${conf.astronaut_id}</strong> | Date: <strong>${conf.checkup_date}</strong>
          </div>
        </div>
      </div>

      <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 1.5rem;">
        ${Components.renderStatCard('Measurements Saved', conf.measurements_saved, 'Data Points', 'Stored in database', 'GREEN')}
        ${Components.renderStatCard('Reports Uploaded', conf.files_uploaded, 'Files', 'SHA-256 hashed')}
        ${Components.renderStatCard('ML Modules Routed', conf.modules_processed.length, 'Engines', 'Analytical evaluation run')}
      </div>

      <div class="card" style="margin-bottom: 1rem; background: rgba(15, 23, 42, 0.5);">
        <strong style="color: var(--teal); font-size: 0.9rem;">Analytical Health Engines Evaluated:</strong>
        <div style="margin-top: 0.5rem; display: flex; flex-wrap: wrap;">
          ${modulesProcessedHtml}
        </div>
      </div>

      <div class="card" style="margin-bottom: 1.5rem; background: rgba(15, 23, 42, 0.5);">
        <strong style="color: var(--amber); font-size: 0.9rem;">Validation Findings:</strong>
        <div style="margin-top: 0.5rem;">${warningsHtml}</div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 1rem;">
        <button class="btn btn-secondary" onclick="Router.handleRouteChange()">+ Log Another Checkup</button>
        <div style="display: flex; gap: 0.5rem;">
          <a href="#/insights" class="btn btn-primary">Review Generated Observations &rarr;</a>
          <button class="btn btn-teal" onclick="window.viewCheckupDetail('${conf.checkup_id}')">View Submitted Record Dossier</button>
        </div>
      </div>
    </div>
  `;
};

// ═════════════════════════════════════════════════════════════════════════
// 0B. ASTRONAUT HEALTH RECORDS HISTORY SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/health-records', async () => {
  window.updateSessionBadge();
  const targetAstronautId = activeUser ? activeUser.astronaut_id : 'ASTRA-001';

  const [records, offlineQueue] = await Promise.all([
    API.getHealthCheckups(targetAstronautId).catch(() => []),
    Promise.resolve(API.getOfflineQueue()),
  ]);

  const rows = records.length === 0
    ? `<tr><td colspan="7" class="text-center text-muted">No health checkup records logged yet for astronaut ${targetAstronautId}.</td></tr>`
    : records.map((r) => `
      <tr>
        <td><strong>${r.checkup_id}</strong></td>
        <td>${r.checkup_date} ${r.checkup_time || ''}</td>
        <td><span class="badge badge-teal">${r.checkup_type}</span></td>
        <td><strong>${r.measurements.length}</strong> measurements</td>
        <td><strong>${r.files.length}</strong> files</td>
        <td>
          <span class="badge ${r.is_amendment ? 'badge-amber' : 'badge-green'}">
            ${r.submission_status.toUpperCase()}
          </span>
        </td>
        <td>
          <button class="btn btn-xs btn-teal" onclick="window.viewCheckupDetail('${r.checkup_id}')">Open Dossier</button>
          <button class="btn btn-xs btn-outline" onclick="window.openAmendModal('${r.checkup_id}')">Amend</button>
        </td>
      </tr>
    `).join('');

  const offlineRows = offlineQueue.map((item, idx) => `
    <tr style="background: rgba(245, 158, 11, 0.05);">
      <td><strong>${item.idempotency_key}</strong></td>
      <td>${item.checkup_date}</td>
      <td>${item.checkup_type}</td>
      <td>${item.measurements.length} measurements</td>
      <td><span class="badge badge-amber">LOCAL BUFFER PENDING SYNC</span></td>
      <td>
        <button class="btn btn-xs btn-amber" onclick="window.syncSingleOfflineItem(${idx})">Sync Now</button>
      </td>
    </tr>
  `).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Astronaut Health Records & Checkup History</h2>
          <p class="text-secondary">Historical clinical record dossiers, discrete measurements, and uploaded diagnostic artifacts.</p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <a href="#/health-checkup" class="btn btn-teal">+ New Health Checkup</a>
          ${offlineQueue.length > 0 ? `
            <button class="btn btn-amber btn-sm" onclick="window.syncOfflineQueue()">Sync All Offline (${offlineQueue.length})</button>
          ` : ''}
        </div>
      </div>

      <div class="card" style="margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h3>Checkup History for ${activeUser.name} (<code>${targetAstronautId}</code>)</h3>
          <span class="text-muted" style="font-size: 0.85rem;">Total Checkup Records: <strong>${records.length}</strong></span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Checkup ID</th>
              <th>Date & Time</th>
              <th>Checkup Type</th>
              <th>Biometrics</th>
              <th>Reports</th>
              <th>Audit Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>

      ${offlineQueue.length > 0 ? `
        <div class="card" style="border-color: var(--amber);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <h3 style="color: var(--amber);">Local Offline Submission Buffer (${offlineQueue.length} Pending)</h3>
            <button class="btn btn-outline btn-xs" onclick="API.clearOfflineQueue(); Router.handleRouteChange();">Clear Buffer</button>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Idempotency Key</th>
                <th>Date</th>
                <th>Type</th>
                <th>Measurements</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${offlineRows}
            </tbody>
          </table>
        </div>
      ` : ''}
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.viewCheckupDetail = async (checkupId) => {
  try {
    const detail = await API.getHealthCheckupDetail(checkupId);
    Components.openModal(Components.renderCheckupDetailModal(detail));
  } catch (err) {
    alert(`Could not load checkup detail: ${err.message}`);
  }
};

window.openAmendModal = (checkupId) => {
  const modalHtml = `
    <div class="modal-header">
      <h2>Submit Clinical Record Amendment</h2>
      <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
    </div>
    <form onsubmit="window.submitCheckupAmendment(event, '${checkupId}')">
      <div class="form-group">
        <label>Target Checkup ID</label>
        <input type="text" class="form-input" value="${checkupId}" readonly>
      </div>
      <div class="form-group">
        <label>Reason for Amendment *</label>
        <input type="text" id="amend-reason" class="form-input" placeholder="e.g. Corrected sensor calibration reading" required>
      </div>
      <div class="form-group">
        <label>Additional Notes / Corrective Observations</label>
        <textarea id="amend-notes" class="form-textarea" rows="3" placeholder="Enter updated clinical context..."></textarea>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick="Components.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-teal">Log Auditable Amendment</button>
      </div>
    </form>
  `;
  Components.openModal(modalHtml);
};

window.submitCheckupAmendment = async (e, checkupId) => {
  e.preventDefault();
  const reason = document.getElementById('amend-reason').value;
  const notes = document.getElementById('amend-notes').value;
  try {
    await API.updateHealthCheckup(checkupId, {
      amendment_reason: reason,
      notes: notes,
      submission_status: 'amended',
    });
    Components.closeModal();
    alert('Amendment registered successfully in flight record.');
    Router.handleRouteChange();
  } catch (err) {
    alert(`Failed to save amendment: ${err.message}`);
  }
};

window.syncOfflineQueue = async () => {
  try {
    const res = await API.syncOfflineCheckups();
    alert(`Sync completed: ${res.synced} checkups sent to server, ${res.failed} failed.`);
    Router.handleRouteChange();
  } catch (err) {
    alert(`Sync error: ${err.message}`);
  }
};

window.syncSingleOfflineItem = async (idx) => {
  const queue = API.getOfflineQueue();
  if (queue[idx]) {
    try {
      await API.submitHealthCheckup(queue[idx]);
      queue.splice(idx, 1);
      localStorage.setItem('astra_offline_checkups', JSON.stringify(queue));
      alert('Offline record successfully uploaded to spacecraft database.');
      Router.handleRouteChange();
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    }
  }
};
Router.register('/dashboard', async () => {
  const [stats, activeAlerts, mlModules, queueDepth, crewList] = await Promise.all([
    API.getAlertStats(),
    API.getActiveAlerts(),
    API.mlHealth(),
    API.getQueueDepth(),
    API.getCrew(),
  ]);

  const activeCount = stats.active_unacknowledged || 0;
  const redCount = stats.by_severity ? stats.by_severity.RED : 0;
  const amberCount = stats.by_severity ? stats.by_severity.AMBER : 0;

  let alertFeedHtml = '';
  if (activeAlerts.length === 0) {
    alertFeedHtml = Components.renderEmptyState('Nominal Flight Status — All astronaut baselines within physiological boundaries.');
  } else {
    alertFeedHtml = activeAlerts.slice(0, 5).map((a) => Components.renderAlertCard(a)).join('');
  }

  const mlCardsHtml = mlModules.map((m) => Components.renderModuleHealthCard(m)).join('');

  const html = `
    <div class="dashboard-view">
      <!-- Mission Status Bar -->
      <div class="mission-bar">
        <div class="mission-info">
          <h2>MISSION: ASTRA-1 / MARS TRANSIT</h2>
          <span class="mission-sub">MET: Day 142 | Earth Comms Delay: ~20.0 min (One-way) | Mode: Autonomous Offline</span>
        </div>
        <div class="system-tag badge-green">FLIGHT SYSTEM HEALTHY</div>
      </div>

      <!-- Stat Cards Row -->
      <div class="stats-grid">
        ${Components.renderStatCard('Active Crew', crewList.length, 'Astronauts', 'All telemetry active')}
        ${Components.renderStatCard('Critical (RED) Alerts', redCount, '', 'Immediate action required', redCount > 0 ? 'RED' : 'GREEN')}
        ${Components.renderStatCard('Advisory (AMBER) Alerts', amberCount, '', 'Action card protocol active', amberCount > 0 ? 'AMBER' : 'GREEN')}
        ${Components.renderStatCard('Earth Store & Forward', queueDepth.pending_encounters, 'Pkgs', 'Queued for ground sync')}
      </div>

      <!-- Quick Action Banners -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
        <div class="card" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: linear-gradient(135deg, rgba(20, 184, 166, 0.1), rgba(15, 23, 42, 0.8)); border-color: rgba(20, 184, 166, 0.4);">
          <div>
            <h4 style="margin: 0; color: var(--teal); font-size: 1rem;">💡 Health Insight Centre</h4>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: var(--text-secondary);">Review synthesized physiological observations & pre-approved actions</p>
          </div>
          <a href="#/insights" class="btn btn-teal btn-sm">Open Insights &rarr;</a>
        </div>
        <div class="card" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(15, 23, 42, 0.8)); border-color: rgba(56, 189, 248, 0.4);">
          <div>
            <h4 style="margin: 0; color: #38bdf8; font-size: 1rem;">📡 Medical Comms & Telemedicine</h4>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: var(--text-secondary);">Asynchronous store-and-forward queue & flight surgeon reviews</p>
          </div>
          <a href="#/medical-comms" class="btn btn-primary btn-sm">Open Comms &rarr;</a>
        </div>
      </div>

      <!-- Active Alerts Section -->
      <div class="dashboard-section">
        <div class="section-header">
          <h3>Active Physiological Alerts (${activeAlerts.length})</h3>
          <a href="#/alerts" class="link-teal">View All Alerts &rarr;</a>
        </div>
        <div class="alert-feed">
          ${alertFeedHtml}
        </div>
      </div>

      <!-- ML Modules Matrix -->
      <div class="dashboard-section">
        <div class="section-header">
          <h3>ML Analytical Engines (7 Modules)</h3>
          <span class="text-muted">Consistent Input/Output Interface Active</span>
        </div>
        <div class="modules-grid">
          ${mlCardsHtml}
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

// ═════════════════════════════════════════════════════════════════════════
// 1B. INSIGHT CENTRE (Central Intelligence Engine)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/insights', async (params) => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const filterSev = params.get('severity') || '';

  const [insights, actionsData, astronautOverview] = await Promise.all([
    API.getInsights({ crew_id: currentCrewId, severity: filterSev || undefined }),
    API.getActions({ crew_id: currentCrewId }),
    API.getAstronautOverview(currentCrewId),
  ]);

  const cardsHtml = insights.length === 0
    ? Components.renderEmptyState('Nominal physiological baseline alignment. No acute deviations detected for this crew member.')
    : insights.map((i) => Components.renderInsightCard(i)).join('');

  const tasks = actionsData.tasks || [];
  const pendingTasks = tasks.filter((t) => t.status === 'pending');
  const ackedTasks = tasks.filter((t) => t.status !== 'pending');

  const tasksListHtml = tasks.length === 0
    ? '<span class="text-muted">No operational support actions pending.</span>'
    : tasks.map((t) => `
      <div class="action-task-item" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; margin-bottom: 0.5rem; background: rgba(15, 23, 42, 0.4);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <strong style="color: var(--teal); font-size: 0.9rem;">${t.title}</strong>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${t.source} | <code>${t.action_id}</code></div>
          </div>
          <span class="badge ${t.status === 'acknowledged' ? 'badge-green' : 'badge-amber'}">${t.status.toUpperCase()}</span>
        </div>
        <p style="font-size: 0.85rem; margin: 0.5rem 0; color: var(--text-secondary);">${t.description}</p>
        ${t.status === 'pending' ? `
          <button class="btn btn-teal btn-xs" onclick="window.acknowledgeAction('${t.action_id}')">Acknowledge Execution</button>
        ` : `<span style="font-size: 0.8rem; color: var(--teal);">✓ Completed at ${new Date(t.acknowledged_at || t.created_at).toLocaleTimeString()}</span>`}
      </div>
    `).join('');

  const libraryHtml = (actionsData.library || []).slice(0, 4).map((a) => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">
      <div>
        <div style="font-size: 0.85rem; font-weight: 600;">${a.title}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${a.action_id}</div>
      </div>
      <button class="btn btn-outline btn-xs" onclick="window.assignActionToCrew('${a.action_id}')">+ Assign</button>
    </div>
  `).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Autonomous Health Insight Centre</h2>
          <p class="text-secondary">Multi-domain physiological synthesis, personal baseline deviations, and pre-approved action recommendations.</p>
        </div>
      </div>

      ${crewSelector}

      <!-- Top Summary Metrics -->
      <div class="stats-grid">
        ${Components.renderStatCard('Total Observations', insights.length, 'Findings', 'Logged flight observations')}
        ${Components.renderStatCard('Baseline Deviations', astronautOverview.active_alerts_count, '', 'Deviations from personal nominal', astronautOverview.active_alerts_count > 0 ? 'AMBER' : 'GREEN')}
        ${Components.renderStatCard('Pending Actions', pendingTasks.length, 'Tasks', 'Action card protocols active', pendingTasks.length > 0 ? 'AMBER' : 'GREEN')}
        ${Components.renderStatCard('Autonomous Policy', 'STRICT', '', 'No autonomous disease diagnosis', 'GREEN')}
      </div>

      <!-- Main Layout: Insights Feed + Action Engine -->
      <div class="two-column-layout" style="grid-template-columns: 1.6fr 1fr; gap: 1.5rem; margin-top: 1.5rem;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h3>Physiological Observations Feed</h3>
            <div class="filter-bar" style="margin: 0;">
              <select class="form-select" onchange="window.filterInsights(this.value)">
                <option value="">All Severities</option>
                <option value="critical" ${filterSev === 'critical' ? 'selected' : ''}>Critical Reviews</option>
                <option value="warning" ${filterSev === 'warning' ? 'selected' : ''}>Warnings</option>
                <option value="monitor" ${filterSev === 'monitor' ? 'selected' : ''}>Routine Monitoring</option>
              </select>
            </div>
          </div>
          <div class="alert-feed">
            ${cardsHtml}
          </div>
        </div>

        <div>
          <div class="card" style="margin-bottom: 1rem;">
            <h3>Assigned Support Tasks (${pendingTasks.length} Pending)</h3>
            <div style="margin-top: 0.75rem;">
              ${tasksListHtml}
            </div>
          </div>

          <div class="card">
            <h3>Pre-Approved Action Library</h3>
            <p class="text-secondary" style="font-size: 0.8rem; margin-bottom: 0.5rem;">Flight surgeon pre-authorized protocols executable without real-time Earth clearance.</p>
            <div>
              ${libraryHtml}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.filterInsights = (val) => {
  Router.navigate(`/insights${val ? '?severity=' + val : ''}`);
};

window.assignActionToCrew = async (actionId) => {
  try {
    await API.assignAction(currentCrewId, actionId, 'Dispatched from Insight Centre');
    Router.handleRouteChange();
  } catch (err) {
    alert(`Could not assign action: ${err.message}`);
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 1C. MEDICAL COMMUNICATION & DELAYED TELEMEDICINE CENTRE
// ═════════════════════════════════════════════════════════════════════════
Router.register('/medical-comms', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const [reports, syncStatus, queue] = await Promise.all([
    API.getMedicalReports({ crew_id: currentCrewId }),
    API.getSyncStatus(),
    API.getSyncQueue(),
  ]);

  const queuedReports = reports.filter((r) => r.status === 'queued_for_sync');
  const transmittedReports = reports.filter((r) => r.status === 'transmitted');
  const reviewedReports = reports.filter((r) => r.status === 'reviewed');

  const queuedHtml = queuedReports.length === 0
    ? '<span class="text-muted">No outbound reports awaiting downlink window.</span>'
    : queuedReports.map((r) => Components.renderMedicalReportCard(r)).join('');

  const transmittedHtml = transmittedReports.length === 0
    ? '<span class="text-muted">No reports currently in transmission transit.</span>'
    : transmittedReports.map((r) => Components.renderMedicalReportCard(r)).join('');

  const reviewedHtml = reviewedReports.length === 0
    ? '<span class="text-muted">No physician review packages received yet.</span>'
    : reviewedReports.map((r) => Components.renderMedicalReportCard(r)).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Medical Communication Centre (Delayed Telemedicine)</h2>
          <p class="text-secondary">Asynchronous store-and-forward telemetry, Earth downlink buffer, and validated flight surgeon mission phase updates.</p>
        </div>
        <button class="btn btn-teal" onclick="window.openCreateReportModal()">+ Draft Medical Report</button>
      </div>

      ${crewSelector}

      <!-- Deep Space Comms Latency Indicator -->
      <div class="mission-bar" style="background: rgba(30, 41, 59, 0.7); border: 1px solid var(--border-color); margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 1rem;">
          <span style="font-size: 1.5rem;">📡</span>
          <div>
            <strong style="color: var(--teal);">DEEP SPACE STORE-AND-FORWARD NETWORK LINK: ACTIVE</strong>
            <div style="font-size: 0.85rem; color: var(--text-secondary);">One-Way Light Speed Delay: ~20.0 min (Mars Transit) | Buffering: AES-256-GCM / SHA-256 Audit Trail</div>
          </div>
        </div>
        <div style="text-align: right;">
          <span class="badge badge-teal">LOCAL BUFFER HEALTHY</span>
        </div>
      </div>

      <!-- Comms Stat Cards -->
      <div class="stats-grid">
        ${Components.renderStatCard('Outbound Queued', queuedReports.length, 'Reports', 'Buffered locally')}
        ${Components.renderStatCard('Transmitted to Earth', transmittedReports.length, 'Reports', 'Downlinked to Houston')}
        ${Components.renderStatCard('Physician Reviews', reviewedReports.length, 'Decisions', 'Flight surgeon signed', reviewedReports.length > 0 ? 'GREEN' : '')}
        ${Components.renderStatCard('Raw Encounter Buffers', queue.encounters.length, 'Packages', 'Telemetry SHA-256 hashed')}
      </div>

      <!-- Three-Section Communication Flow -->
      <div style="margin-top: 1.5rem;">
        <div class="card" style="margin-bottom: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <h3>1. Outbound Reports Waiting to be Sent (${queuedReports.length})</h3>
            ${queuedReports.length > 0 ? `
              <button class="btn btn-teal btn-xs" onclick="window.syncAllPendingReports()">Simulate Bulk Downlink Transmission</button>
            ` : ''}
          </div>
          <div>${queuedHtml}</div>
        </div>

        <div class="card" style="margin-bottom: 1.5rem;">
          <h3>2. Successfully Synchronized Reports (Downlinked to Ground Flight Surgeon) (${transmittedReports.length})</h3>
          <div>${transmittedHtml}</div>
        </div>

        <div class="card">
          <h3>3. Ground Flight Surgeon Review & Approved Future Mission Phase Adaptations (${reviewedReports.length})</h3>
          <p class="text-secondary" style="font-size: 0.85rem; margin-bottom: 0.75rem;">Official medical director approvals authorizing progression through Gravity Adaptation phases.</p>
          <div>${reviewedHtml}</div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.syncAllPendingReports = async () => {
  try {
    const reps = await API.getMedicalReports({ status: 'queued_for_sync' });
    for (const r of reps) {
      await API.syncMedicalReport(r.report_id);
    }
    Router.handleRouteChange();
  } catch (err) {
    alert(`Sync failed: ${err.message}`);
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 2. CREW MANAGEMENT SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/crew', async () => {
  const crewList = await API.getCrew();

  const crewCardsHtml = await Promise.all(
    crewList.map(async (member) => {
      const details = await API.getCrewMember(member.id);
      const vitalsList = details.latest_vitals || [];
      const vitalsRows = vitalsList.map((v) => `
        <div class="vital-pill">
          <span class="vital-name">${v.metric_name}:</span>
          <span class="vital-val">${v.value} ${v.unit}</span>
        </div>
      `).join('') || '<span class="text-muted">No telemetry logged yet</span>';

      return `
        <div class="crew-card">
          <div class="crew-header">
            <div class="crew-avatar">👨‍🚀</div>
            <div>
              <h3>${member.name}</h3>
              <span class="crew-role">${member.role}</span>
            </div>
            <span class="badge ${member.status === 'active' ? 'badge-green' : 'badge-amber'}">${member.status.toUpperCase()}</span>
          </div>
          <div class="crew-meta">
            <span><strong>Active Baselines:</strong> ${details.active_baselines_count}</span>
          </div>
          <div class="crew-vitals">
            <h4>Latest Physiological Telemetry:</h4>
            <div class="vitals-pill-grid">${vitalsRows}</div>
          </div>
        </div>
      `;
    })
  );

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Mission Crew Members</h2>
          <p class="text-secondary">Monitored astronauts with personalized baseline tracking.</p>
        </div>
        <button class="btn btn-teal" onclick="window.showAddCrewModal()">+ Register Crew Member</button>
      </div>

      <div class="crew-grid">
        ${crewCardsHtml.join('')}
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.showAddCrewModal = () => {
  const formHtml = `
    <div class="modal-header">
      <h2>Register New Crew Member</h2>
      <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
    </div>
    <form id="add-crew-form" onsubmit="window.submitNewCrew(event)">
      <div class="form-group">
        <label>Full Name & Rank</label>
        <input type="text" id="crew-name" class="form-input" placeholder="e.g. MS-1 Dr. Emily Hayes" required>
      </div>
      <div class="form-group">
        <label>Mission Role</label>
        <input type="text" id="crew-role" class="form-input" placeholder="e.g. Flight Medical Officer" required>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick="Components.closeModal()">Cancel</button>
        <button type="submit" class="btn btn-teal">Add Astronaut</button>
      </div>
    </form>
  `;
  Components.openModal(formHtml);
};

window.submitNewCrew = async (e) => {
  e.preventDefault();
  const name = document.getElementById('crew-name').value;
  const role = document.getElementById('crew-role').value;
  try {
    await API.createCrew({ name, role, status: 'active' });
    Components.closeModal();
    Router.handleRouteChange();
  } catch (err) {
    alert(`Failed to add crew: ${err.message}`);
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 3. CARDIOVASCULAR & GRAVITY ADAPTATION (GAR) SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/cardiovascular', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const [vitals, baselines, mlHealth] = await Promise.all([
    API.getLatestVitals(currentCrewId),
    API.getBaselines(currentCrewId),
    API.mlModuleHealth('cardiovascular'),
  ]);

  const hr = vitals.find((v) => v.metric_name === 'heart_rate')?.value || '--';
  const bpSys = vitals.find((v) => v.metric_name === 'bp_systolic')?.value || '--';
  const bpDia = vitals.find((v) => v.metric_name === 'bp_diastolic')?.value || '--';
  const hrv = vitals.find((v) => v.metric_name === 'hrv_rmssd')?.value || '--';

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 4: Gravity Adaptation & Rehabilitation (GAR) — Cardiovascular</h2>
          <p class="text-secondary">Hemodynamic tracking, orthostatic tolerance, continuous arterial BP, and beat-to-beat ECG analysis.</p>
        </div>
      </div>

      ${crewSelector}

      <div class="stats-grid">
        ${Components.renderStatCard('Heart Rate', hr, 'bpm', 'Continuous wearable')}
        ${Components.renderStatCard('Blood Pressure', `${bpSys}/${bpDia}`, 'mmHg', 'Continuous Finapres')}
        ${Components.renderStatCard('HRV RMSSD', hrv, 'ms', 'Autonomic tone marker')}
        ${Components.renderStatCard('Module Predictor', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Historical Physiological Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Systolic Blood Pressure & Orthostatic Baseline (MET 130 - 142)', [
          { met: 130, val: 118 }, { met: 132, val: 120 }, { met: 134, val: 117 },
          { met: 136, val: 119 }, { met: 138, val: 122 }, { met: 140, val: 124 },
          { met: 142, val: typeof bpSys === 'number' ? bpSys : 121 }
        ], 120.0, 5.0, 'mmHg')}
      </div>

      <div class="two-column-layout">
        <!-- Interactive Telemetry Ingest Box -->
        <div class="card">
          <h3>Record Orthostatic Vital Reading</h3>
          <form onsubmit="window.submitCardioVitals(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Systolic BP (mmHg)</label>
                <input type="number" id="cardio-sys" class="form-input" value="118" required>
              </div>
              <div class="form-group">
                <label>Diastolic BP (mmHg)</label>
                <input type="number" id="cardio-dia" class="form-input" value="76" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Heart Rate (bpm)</label>
                <input type="number" id="cardio-hr" class="form-input" value="72" required>
              </div>
              <div class="form-group">
                <label>Postural State</label>
                <select id="cardio-posture" class="form-select">
                  <option value="supine">Supine (Nominal Microgravity)</option>
                  <option value="seated">Seated Transition</option>
                  <option value="standing">Standing (Orthostatic Challenge)</option>
                </select>
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Log Vitals & Check Baseline</button>
          </form>
          <div id="cardio-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Module Inference Box -->
        <div class="card">
          <h3>Cardiovascular ML Inference (PTB-XL Module)</h3>
          <p class="text-secondary">Drop-in inference engine testing beat-level morphological features.</p>
          <button class="btn btn-primary" onclick="window.runCardioML()">Execute ML Inference</button>
          <div id="cardio-ml-result" class="ml-output-box">
            <span class="text-muted">Click above to execute model inference.</span>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.submitCardioVitals = async (e) => {
  e.preventDefault();
  const sys = parseFloat(document.getElementById('cardio-sys').value);
  const dia = parseFloat(document.getElementById('cardio-dia').value);
  const hr = parseFloat(document.getElementById('cardio-hr').value);
  const resBox = document.getElementById('cardio-result-box');

  try {
    const met = Date.now() / 3600000;
    const r1 = await API.ingestVital({
      crew_id: currentCrewId,
      metric_name: 'bp_systolic',
      value: sys,
      unit: 'mmHg',
      timestamp_met: met,
      hazard: 'hazard_4_gravity_fields',
    });
    const r2 = await API.ingestVital({
      crew_id: currentCrewId,
      metric_name: 'heart_rate',
      value: hr,
      unit: 'bpm',
      timestamp_met: met,
      hazard: 'hazard_4_gravity_fields',
    });

    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Telemetry ingested. Deviation z-score: BP ${r1.deviation.z_score}, HR ${r2.deviation.z_score}.
        ${r1.alert_triggered ? `<span class="badge badge-amber">ALERT TRIGGERED: ${r1.action_card_id}</span>` : '<span class="badge badge-green">BASELINE NOMINAL</span>'}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runCardioML = async () => {
  const box = document.getElementById('cardio-ml-result');
  box.innerHTML = 'Running PTB-XL cardiovascular predictor...';
  try {
    const result = await API.mlPredict('cardiovascular', {
      crew_id: currentCrewId,
      input_data: {
        bp_systolic: 125,
        bp_diastolic: 80,
        hr: 75,
        ecg_features: { qrs_duration_ms: 92, qt_interval_ms: 395 },
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Risk Assessment:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Risk Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Inference failed: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 4. IMMUNE SYSTEM & CLOSED ENVIRONMENTS (OSD-575)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/immune', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('immune');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 5: Hostile/Closed Environments — Immune Vigilance</h2>
          <p class="text-secondary">WBC differential, lymphocyte suppression, inflammatory cytokines (IL-6, TNF-α), and latent virus reactivation.</p>
        </div>
      </div>

      ${crewSelector}

      <div class="stats-grid">
        ${Components.renderStatCard('Immune Status', 'NOMINAL', '', 'Adaptive reserve stable', 'GREEN')}
        ${Components.renderStatCard('Viral Reactivation', 'NEGATIVE', '', 'EBV / VZV / HSV-1')}
        ${Components.renderStatCard('Inflammatory Index', '1.1 σ', '', 'Normal baseline range')}
        ${Components.renderStatCard('Predictor (OSD-575)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Total WBC Count Trajectory (MET 130 - 142)', [
          { met: 130, val: 6.8 }, { met: 132, val: 6.5 }, { met: 134, val: 6.9 },
          { met: 136, val: 6.3 }, { met: 138, val: 6.6 }, { met: 140, val: 6.4 },
          { met: 142, val: 6.7 }
        ], 6.5, 0.8, 'x10³/μL')}
      </div>

      <div class="two-column-layout">
        <!-- Measurement Ingest Form -->
        <div class="card">
          <h3>Log Immune Panel Biomarkers</h3>
          <form onsubmit="window.submitImmuneMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>WBC Count (x10³/μL)</label>
                <input type="number" step="0.1" id="imm-wbc" class="form-input" value="6.5" required>
              </div>
              <div class="form-group">
                <label>Lymphocytes (%)</label>
                <input type="number" step="0.1" id="imm-lymph" class="form-input" value="29.0" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>IL-6 Cytokine (pg/mL)</label>
                <input type="number" step="0.1" id="imm-il6" class="form-input" value="1.8" required>
              </div>
              <div class="form-group">
                <label>TNF-α (pg/mL)</label>
                <input type="number" step="0.1" id="imm-tnf" class="form-input" value="3.2" required>
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Log Biomarkers & Check Baseline</button>
          </form>
          <div id="imm-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Prediction Box -->
        <div class="card">
          <h3>Immune ML Prediction (NASA OSD-575 Model)</h3>
          <p class="text-secondary">Evaluates cytokine balance and immune suppression risk.</p>
          <button class="btn btn-primary" onclick="window.runImmuneML()">Execute Immune Predictor</button>
          <div id="immune-ml-result" class="ml-output-box">
            <span class="text-muted">Click above to analyze immune profile.</span>
          </div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('app').innerHTML = html;
});

window.submitImmuneMeasurements = async (e) => {
  e.preventDefault();
  const wbc = parseFloat(document.getElementById('imm-wbc').value);
  const il6 = parseFloat(document.getElementById('imm-il6').value);
  const resBox = document.getElementById('imm-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'immune',
      metric_name: 'wbc_count',
      value: wbc,
      unit: 'x10³/μL',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested WBC metric. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runImmuneML = async () => {
  const box = document.getElementById('immune-ml-result');
  box.innerHTML = 'Evaluating immune panel against OSD-575 astronaut norm...';
  try {
    const result = await API.mlPredict('immune', {
      crew_id: currentCrewId,
      input_data: {
        wbc_count: parseFloat(document.getElementById('imm-wbc')?.value || 6.8),
        lymphocyte_pct: parseFloat(document.getElementById('imm-lymph')?.value || 29.5),
        neutrophil_pct: 62.0,
        il6: parseFloat(document.getElementById('imm-il6')?.value || 2.1),
        tnf_alpha: parseFloat(document.getElementById('imm-tnf')?.value || 3.5),
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Status:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Composite Risk Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 5. METABOLIC & CMP SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/metabolic', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('metabolic');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Metabolic & Renal Chemistry (OSD-575 CMP)</h2>
          <p class="text-secondary">Electrolyte shifts, glucose metabolism, renal filtration, and bone demineralization calcium markers.</p>
        </div>
      </div>
      ${crewSelector}
      <div class="stats-grid">
        ${Components.renderStatCard('Serum Calcium', '9.4', 'mg/dL', 'Bone remodeling balance')}
        ${Components.renderStatCard('Creatinine', '0.92', 'mg/dL', 'Renal clearance normal')}
        ${Components.renderStatCard('Sodium/Potassium', '140 / 4.2', 'mEq/L', 'Osmotic balance')}
        ${Components.renderStatCard('Predictor (CMP)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Fasting Blood Glucose Trajectory (MET 130 - 142)', [
          { met: 130, val: 92 }, { met: 132, val: 94 }, { met: 134, val: 91 },
          { met: 136, val: 96 }, { met: 138, val: 93 }, { met: 140, val: 95 },
          { met: 142, val: 94 }
        ], 93.0, 6.0, 'mg/dL')}
      </div>

      <div class="two-column-layout">
        <!-- Measurement Form -->
        <div class="card">
          <h3>Log Metabolic & Chemistry Panel</h3>
          <form onsubmit="window.submitMetabolicMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Serum Glucose (mg/dL)</label>
                <input type="number" step="1" id="met-glu" class="form-input" value="95" required>
              </div>
              <div class="form-group">
                <label>Serum Calcium (mg/dL)</label>
                <input type="number" step="0.1" id="met-cal" class="form-input" value="9.4" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Creatinine (mg/dL)</label>
                <input type="number" step="0.01" id="met-cr" class="form-input" value="0.92" required>
              </div>
              <div class="form-group">
                <label>Serum Potassium (mEq/L)</label>
                <input type="number" step="0.1" id="met-pot" class="form-input" value="4.2" required>
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Log Chemistry & Check Baseline</button>
          </form>
          <div id="met-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Inference Box -->
        <div class="card">
          <h3>Metabolic Panel ML Inference</h3>
          <p class="text-secondary">Assesses renal clearance, osmotic shifts, and calcium mobilization.</p>
          <button class="btn btn-primary" onclick="window.runMetabolicML()">Run Metabolic Assessment</button>
          <div id="met-ml-result" class="ml-output-box"><span class="text-muted">Click to run.</span></div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('app').innerHTML = html;
});

window.submitMetabolicMeasurements = async (e) => {
  e.preventDefault();
  const glu = parseFloat(document.getElementById('met-glu').value);
  const resBox = document.getElementById('met-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'metabolic',
      metric_name: 'glucose',
      value: glu,
      unit: 'mg/dL',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested glucose. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runMetabolicML = async () => {
  const box = document.getElementById('met-ml-result');
  box.innerHTML = 'Computing metabolic risk index...';
  try {
    const result = await API.mlPredict('metabolic', {
      crew_id: currentCrewId,
      input_data: {
        glucose: parseFloat(document.getElementById('met-glu')?.value || 95),
        bun: 14,
        creatinine: parseFloat(document.getElementById('met-cr')?.value || 0.95),
        sodium: 141,
        potassium: parseFloat(document.getElementById('met-pot')?.value || 4.1),
        calcium: parseFloat(document.getElementById('met-cal')?.value || 9.3),
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Status:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 6. RADIATION HEALTH (OSD-157)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/radiation', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('radiation');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 1: Space Radiation Health (OSD-157)</h2>
          <p class="text-secondary">Cumulative GCR & SPE dose tracking, DNA double-strand break repair (γ-H2AX), and gene-expression stress signatures.</p>
        </div>
      </div>
      ${crewSelector}
      <div class="stats-grid">
        ${Components.renderStatCard('Cumulative Mission Dose', '168.4', 'mSv', 'Limit: 600 mSv', 'GREEN')}
        ${Components.renderStatCard('Current Dose Rate', '1.42', 'mSv/day', 'Nominal GCR background')}
        ${Components.renderStatCard('γ-H2AX Foci Index', '1.2', 'foci/cell', 'DNA repair kinetics active')}
        ${Components.renderStatCard('Predictor (OSD-157)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Galactic Cosmic Ray (GCR) Daily Dose Rate (MET 130 - 142)', [
          { met: 130, val: 1.38 }, { met: 132, val: 1.41 }, { met: 134, val: 1.40 },
          { met: 136, val: 1.45 }, { met: 138, val: 1.42 }, { met: 140, val: 1.44 },
          { met: 142, val: 1.42 }
        ], 1.40, 0.15, 'mSv/day')}
      </div>

      <div class="two-column-layout">
        <!-- Measurement Ingest Form -->
        <div class="card">
          <h3>Log Radiation Dosimetry & Biomarkers</h3>
          <form onsubmit="window.submitRadiationMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Daily Dose Rate (mSv/day)</label>
                <input type="number" step="0.01" id="rad-rate" class="form-input" value="1.42" required>
              </div>
              <div class="form-group">
                <label>Cumulative Mission Dose (mSv)</label>
                <input type="number" step="0.1" id="rad-cum" class="form-input" value="168.4" required>
              </div>
            </div>
            <div class="form-group">
              <label>γ-H2AX DNA Repair Foci (foci/cell)</label>
              <input type="number" step="0.1" id="rad-h2ax" class="form-input" value="1.2" required>
            </div>
            <button type="submit" class="btn btn-teal">Log Dosimetry & Check Baseline</button>
          </form>
          <div id="rad-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Inference Box -->
        <div class="card">
          <h3>Radiation Risk Predictor (OSD-157)</h3>
          <p class="text-secondary">Assesses double-strand break repair kinetics and deep-space biological stress.</p>
          <button class="btn btn-primary" onclick="window.runRadML()">Run Radiation Risk Assessment</button>
          <div id="rad-ml-result" class="ml-output-box"><span class="text-muted">Click to run.</span></div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('app').innerHTML = html;
});

window.submitRadiationMeasurements = async (e) => {
  e.preventDefault();
  const rate = parseFloat(document.getElementById('rad-rate').value);
  const resBox = document.getElementById('rad-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'radiation',
      metric_name: 'radiation_dose_rate',
      value: rate,
      unit: 'mSv/day',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested dosimetry. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runRadML = async () => {
  const box = document.getElementById('rad-ml-result');
  box.innerHTML = 'Evaluating radiation dosimetry against OSD-157 DNA markers...';
  try {
    const result = await API.mlPredict('radiation', {
      crew_id: currentCrewId,
      input_data: {
        cumulative_dose_msv: parseFloat(document.getElementById('rad-cum')?.value || 168.4),
        dose_rate: parseFloat(document.getElementById('rad-rate')?.value || 1.42),
        gamma_h2ax: parseFloat(document.getElementById('rad-h2ax')?.value || 1.2),
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Exposure Risk:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Composite Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 6B. SLEEP & CIRCADIAN RHYTHM SCREEN (Hazard 2: Isolation & Confinement)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/sleep', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('sleep');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 2: Isolation & Confinement — Sleep & Circadian Vigilance</h2>
          <p class="text-secondary">Actigraphy duration, sleep architecture (REM / N3 Deep), circadian phase shift, and psychomotor vigilance (PVT).</p>
        </div>
      </div>

      ${crewSelector}

      <div class="stats-grid">
        ${Components.renderStatCard('Total Sleep Time', '7.4', 'hours', 'Objective actigraphy', 'GREEN')}
        ${Components.renderStatCard('Sleep Efficiency', '91.8', '%', 'Nominal target > 85%')}
        ${Components.renderStatCard('Circadian Phase Shift', '0.3', 'hours', 'Entrained to 24h cabin cycle')}
        ${Components.renderStatCard('Predictor (Sleep)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Nightly Sleep Duration Trajectory (MET 130 - 142)', [
          { met: 130, val: 7.2 }, { met: 132, val: 7.5 }, { met: 134, val: 6.8 },
          { met: 136, val: 7.1 }, { met: 138, val: 7.6 }, { met: 140, val: 7.3 },
          { met: 142, val: 7.4 }
        ], 7.5, 0.8, 'hours')}
      </div>

      <div class="two-column-layout">
        <!-- Sleep Log Intake Form -->
        <div class="card">
          <h3>Log Daily Sleep & Circadian Architecture</h3>
          <form onsubmit="window.submitSleepMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Sleep Duration (hours)</label>
                <input type="number" step="0.1" id="slp-dur" class="form-input" value="7.4" required>
              </div>
              <div class="form-group">
                <label>REM Sleep (%)</label>
                <input type="number" step="0.1" id="slp-rem" class="form-input" value="22.5" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Deep Sleep / N3 (%)</label>
                <input type="number" step="0.1" id="slp-deep" class="form-input" value="18.0" required>
              </div>
              <div class="form-group">
                <label>Awakenings Count</label>
                <input type="number" step="1" id="slp-awake" class="form-input" value="1" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Circadian Phase Drift (hours)</label>
                <input type="number" step="0.1" id="slp-drift" class="form-input" value="0.3" required>
              </div>
              <div class="form-group">
                <label>PVT Lapses (>500ms)</label>
                <input type="number" step="1" id="slp-pvt" class="form-input" value="0" required>
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Log Sleep Session & Check Baseline</button>
          </form>
          <div id="slp-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Inference Box -->
        <div class="card">
          <h3>Sleep & Circadian Rhythm Evaluator</h3>
          <p class="text-secondary">Assesses cumulative fatigue, circadian desynchrony, and cognitive degradation risk.</p>
          <button class="btn btn-primary" onclick="window.runSleepML()">Execute Sleep Assessment</button>
          <div id="slp-ml-result" class="ml-output-box"><span class="text-muted">Click to run.</span></div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.submitSleepMeasurements = async (e) => {
  e.preventDefault();
  const dur = parseFloat(document.getElementById('slp-dur').value);
  const resBox = document.getElementById('slp-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'sleep',
      metric_name: 'sleep_duration_hours',
      value: dur,
      unit: 'hours',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested sleep duration. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runSleepML = async () => {
  const box = document.getElementById('slp-ml-result');
  box.innerHTML = 'Computing sleep architecture and circadian alignment...';
  try {
    const result = await API.mlPredict('sleep', {
      crew_id: currentCrewId,
      input_data: {
        sleep_duration_hours: parseFloat(document.getElementById('slp-dur')?.value || 7.4),
        rem_pct: parseFloat(document.getElementById('slp-rem')?.value || 22.5),
        deep_sleep_pct: parseFloat(document.getElementById('slp-deep')?.value || 18.0),
        awakenings: parseInt(document.getElementById('slp-awake')?.value || 1),
        circadian_phase_shift_h: parseFloat(document.getElementById('slp-drift')?.value || 0.3),
        pvt_lapses: parseInt(document.getElementById('slp-pvt')?.value || 0),
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Status:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Fatigue Risk Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 7. NEUROMUSCULAR & SENSORIMOTOR GAIT
// ═════════════════════════════════════════════════════════════════════════
Router.register('/neuromuscular', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('neuromuscular');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 4: Sensorimotor & Neuromuscular Acclimatization</h2>
          <p class="text-secondary">Postural sway velocity, dynamic gait symmetry index, and psychomotor vigilance (PVT) response latency.</p>
        </div>
      </div>
      ${crewSelector}
      <div class="stats-grid">
        ${Components.renderStatCard('Gait Symmetry', '96.2', '%', 'Bilateral stance balance', 'GREEN')}
        ${Components.renderStatCard('Postural Sway Velocity', '1.8', 'cm/s', 'Center-of-pressure stability')}
        ${Components.renderStatCard('PVT Median RT', '242', 'ms', 'Zero lapses (>500ms)')}
        ${Components.renderStatCard('Predictor (Gait)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Dynamic Gait Symmetry Trajectory (MET 130 - 142)', [
          { met: 130, val: 96.0 }, { met: 132, val: 95.8 }, { met: 134, val: 96.5 },
          { met: 136, val: 95.2 }, { met: 138, val: 96.1 }, { met: 140, val: 96.8 },
          { met: 142, val: 96.2 }
        ], 96.0, 1.5, '%')}
      </div>

      <div class="two-column-layout">
        <!-- Measurement Ingest Form -->
        <div class="card">
          <h3>Log Sensorimotor & Gait Kinematics</h3>
          <form onsubmit="window.submitNeuromuscularMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Gait Symmetry Index (%)</label>
                <input type="number" step="0.1" id="neu-sym" class="form-input" value="96.2" required>
              </div>
              <div class="form-group">
                <label>Postural Sway Velocity (cm/s)</label>
                <input type="number" step="0.1" id="neu-sway" class="form-input" value="1.8" required>
              </div>
            </div>
            <div class="form-group">
              <label>Psychomotor Reaction Time (ms)</label>
              <input type="number" step="1" id="neu-rt" class="form-input" value="242" required>
            </div>
            <button type="submit" class="btn btn-teal">Log Kinematics & Check Baseline</button>
          </form>
          <div id="neu-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Prediction Box -->
        <div class="card">
          <h3>Multimodal Gait & Postural Sway Inference</h3>
          <p class="text-secondary">Analyzes sensorimotor adaptation and postural ataxia in altered gravity fields.</p>
          <button class="btn btn-primary" onclick="window.runNeuromuscularML()">Execute Sensorimotor Assessment</button>
          <div id="neu-ml-result" class="ml-output-box"><span class="text-muted">Click to evaluate gait.</span></div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('app').innerHTML = html;
});

window.submitNeuromuscularMeasurements = async (e) => {
  e.preventDefault();
  const sym = parseFloat(document.getElementById('neu-sym').value);
  const resBox = document.getElementById('neu-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'neuromuscular',
      metric_name: 'gait_symmetry_pct',
      value: sym,
      unit: '%',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested gait kinematics. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runNeuromuscularML = async () => {
  const box = document.getElementById('neu-ml-result');
  box.innerHTML = 'Analyzing sensorimotor kinematics...';
  try {
    const result = await API.mlPredict('neuromuscular', {
      crew_id: currentCrewId,
      input_data: {
        gait_symmetry: (parseFloat(document.getElementById('neu-sym')?.value || 96.2)) / 100,
        stride_length: 0.72,
        sway_velocity: parseFloat(document.getElementById('neu-sway')?.value || 1.8),
        reaction_time_ms: parseInt(document.getElementById('neu-rt')?.value || 242),
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>Status:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Risk Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 8. SANS (SPACEFLIGHT-ASSOCIATED NEURO-OCULAR SYNDROME)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/sans', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const mlHealth = await API.mlModuleHealth('sans');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 4: SANS (Optic Nerve & Cephalad Fluid Shift)</h2>
          <p class="text-secondary">Optic Nerve Sheath Diameter (ONSD) ultrasound, Retinal Nerve Fiber Layer (RNFL) thickness, and IOP tracking.</p>
        </div>
      </div>
      ${crewSelector}
      <div class="stats-grid">
        ${Components.renderStatCard('ONSD (Optic Sheath)', '5.1', 'mm', 'Nominal threshold < 5.8 mm', 'GREEN')}
        ${Components.renderStatCard('RNFL Thickness', '104', 'μm', 'Baseline reference stability')}
        ${Components.renderStatCard('Intraocular Pressure', '15.2', 'mmHg', 'Normal range 12 - 20 mmHg')}
        ${Components.renderStatCard('Predictor (SANS)', mlHealth.status.toUpperCase(), '', mlHealth.version, mlHealth.status === 'live' ? 'GREEN' : 'AMBER')}
      </div>

      <!-- Trend Chart -->
      <div style="margin: 1.5rem 0;">
        ${Components.renderInteractiveTrendChart('Optic Nerve Sheath Diameter (ONSD) Ultrasound (MET 130 - 142)', [
          { met: 130, val: 4.9 }, { met: 132, val: 5.0 }, { met: 134, val: 5.1 },
          { met: 136, val: 5.2 }, { met: 138, val: 5.0 }, { met: 140, val: 5.1 },
          { met: 142, val: 5.1 }
        ], 5.0, 0.3, 'mm')}
      </div>

      <div class="two-column-layout">
        <!-- Measurement Ingest Form -->
        <div class="card">
          <h3>Log Ocular Ultrasound & Tonometry</h3>
          <form onsubmit="window.submitSANSMeasurements(event)">
            <div class="form-row">
              <div class="form-group">
                <label>Optic Sheath Diameter (mm)</label>
                <input type="number" step="0.1" id="sans-onsd" class="form-input" value="5.1" required>
              </div>
              <div class="form-group">
                <label>RNFL Thickness (μm)</label>
                <input type="number" step="1" id="sans-rnfl" class="form-input" value="104" required>
              </div>
            </div>
            <div class="form-group">
              <label>Intraocular Pressure (mmHg)</label>
              <input type="number" step="0.1" id="sans-iop" class="form-input" value="15.2" required>
            </div>
            <button type="submit" class="btn btn-teal">Log Ocular Telemetry & Check Baseline</button>
          </form>
          <div id="sans-result-box" class="result-box hidden"></div>
        </div>

        <!-- ML Inference Box -->
        <div class="card">
          <h3>Optic Ultrasound & MRI SANS Predictor</h3>
          <p class="text-secondary">Assesses cephalad venous congestion and papilledema risk.</p>
          <button class="btn btn-primary" onclick="window.runSANSML()">Execute SANS Predictor</button>
          <div id="sans-ml-result" class="ml-output-box"><span class="text-muted">Click to evaluate.</span></div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('app').innerHTML = html;
});

window.submitSANSMeasurements = async (e) => {
  e.preventDefault();
  const onsd = parseFloat(document.getElementById('sans-onsd').value);
  const resBox = document.getElementById('sans-result-box');
  try {
    const res = await API.ingestMeasurement({
      crew_id: currentCrewId,
      domain: 'sans',
      metric_name: 'optic_sheath_diameter',
      value: onsd,
      unit: 'mm',
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested ONSD. Observation: ${res.observation}
      </div>
    `;
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.runSANSML = async () => {
  const box = document.getElementById('sans-ml-result');
  box.innerHTML = 'Analyzing neuro-ocular biometric parameters...';
  try {
    const result = await API.mlPredict('sans', {
      crew_id: currentCrewId,
      input_data: {
        optic_disc_diameter: parseFloat(document.getElementById('sans-onsd')?.value || 5.1),
        rnfl_thickness: parseFloat(document.getElementById('sans-rnfl')?.value || 104),
        iop: parseFloat(document.getElementById('sans-iop')?.value || 15.2),
        choroidal_folds: false,
      },
    });
    box.innerHTML = `
      <div class="ml-result-card">
        <div><strong>SANS Risk Tier:</strong> ${result.risk_label}</div>
        <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
        <div><strong>Risk Score:</strong> ${(result.risk_score * 100).toFixed(1)}/100</div>
        ${result.observation ? `<div style="margin-top: 0.5rem; color: var(--teal); font-size: 0.85rem;"><strong>Insight Engine:</strong> ${result.observation}</div>` : ''}
        <pre class="json-dump">${JSON.stringify(result.details, null, 2)}</pre>
      </div>
    `;
  } catch (err) {
    box.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 9. ALERTS MANAGEMENT SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/alerts', async (params) => {
  const severityFilter = params.get('severity') || '';
  const hazardFilter = params.get('hazard') || '';

  const alerts = await API.getAlerts({
    severity: severityFilter || undefined,
    hazard: hazardFilter || undefined,
  });

  const alertCardsHtml = alerts.length === 0
    ? Components.renderEmptyState('No clinical alerts match the selected criteria.')
    : alerts.map((a) => Components.renderAlertCard(a)).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Clinical Alerts & Objective Deviations</h2>
          <p class="text-secondary">Tri-tier clinical classification (GREEN, AMBER, RED) strictly free of unsupported disease diagnoses.</p>
        </div>
      </div>

      <div class="filter-bar">
        <label>Filter Severity:</label>
        <select class="form-select" onchange="window.filterAlerts('severity', this.value)">
          <option value="">All Tiers</option>
          <option value="GREEN" ${severityFilter === 'GREEN' ? 'selected' : ''}>GREEN (Nominal)</option>
          <option value="AMBER" ${severityFilter === 'AMBER' ? 'selected' : ''}>AMBER (Countermeasure)</option>
          <option value="RED" ${severityFilter === 'RED' ? 'selected' : ''}>RED (Emergency Stabilization)</option>
        </select>

        <label>Filter Hazard:</label>
        <select class="form-select" onchange="window.filterAlerts('hazard', this.value)">
          <option value="">All Hazards</option>
          <option value="hazard_1_space_radiation" ${hazardFilter === 'hazard_1_space_radiation' ? 'selected' : ''}>Radiation</option>
          <option value="hazard_2_isolation_and_confinement" ${hazardFilter === 'hazard_2_isolation_and_confinement' ? 'selected' : ''}>Isolation</option>
          <option value="hazard_4_gravity_fields" ${hazardFilter === 'hazard_4_gravity_fields' ? 'selected' : ''}>Gravity (GAR)</option>
          <option value="hazard_5_hostile_closed_environments" ${hazardFilter === 'hazard_5_hostile_closed_environments' ? 'selected' : ''}>Immune</option>
          <option value="biosample_intelligence_engine" ${hazardFilter === 'biosample_intelligence_engine' ? 'selected' : ''}>BioSample Engine</option>
        </select>
      </div>

      <div class="alert-feed">
        ${alertCardsHtml}
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.filterAlerts = (key, val) => {
  const currentParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  if (val) {
    currentParams.set(key, val);
  } else {
    currentParams.delete(key);
  }
  Router.navigate(`/alerts?${currentParams.toString()}`);
};

// ═════════════════════════════════════════════════════════════════════════
// 10. ACTION CARDS REPOSITORY SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/action-cards', async () => {
  const cards = await API.getActionCards();

  const cardsHtml = cards.map((card) => `
    <div class="action-card-item">
      <div class="action-card-header">
        <span class="card-id">${card.card_id} (v${card.version})</span>
        ${Components.renderSeverityBadge(card.severity)}
      </div>
      <h3 class="card-title">${card.title}</h3>
      <p class="card-desc">${card.plain_language_summary}</p>
      <div class="card-footer">
        <button class="btn btn-teal btn-sm" onclick="window.viewActionCard('${card.card_id}')">Open Full Protocol &rarr;</button>
      </div>
    </div>
  `).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Pre-Authorized Medical Action Cards (BRIDGE Stage)</h2>
          <p class="text-secondary">Immutable, flight-surgeon approved operational procedures executable without real-time Earth support.</p>
        </div>
      </div>

      <div class="action-cards-grid">
        ${cardsHtml}
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

// ═════════════════════════════════════════════════════════════════════════
// 11. PERSONAL BASELINES SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/baselines', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);
  const baselines = await API.getBaselines(currentCrewId);

  const rows = baselines.length === 0
    ? `<tr><td colspan="6" class="text-center text-muted">No baselines established yet for this crew member. Log vitals to initialize.</td></tr>`
    : baselines.map((b) => `
      <tr>
        <td><strong>${b.metric_name}</strong></td>
        <td>${b.mean.toFixed(2)}</td>
        <td>± ${b.std.toFixed(2)}</td>
        <td>${b.n_samples}</td>
        <td>
          <span class="badge ${b.frozen ? 'badge-amber' : 'badge-green'}">
            ${b.frozen ? '❄ FROZEN' : 'ACTIVE'}
          </span>
        </td>
        <td>
          <button class="btn btn-xs ${b.frozen ? 'btn-teal' : 'btn-secondary'}" onclick="window.toggleBaselineFreeze(${b.crew_id}, '${b.metric_name}', ${!b.frozen})">
            ${b.frozen ? 'Unfreeze' : 'Freeze'}
          </button>
        </td>
      </tr>
    `).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Personal Baselines Engine</h2>
          <p class="text-secondary">Individual astronaut rolling nominal statistics. Automatically frozen during acute deviations (Constraint #7).</p>
        </div>
      </div>

      ${crewSelector}

      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Nominal Mean</th>
              <th>Std Dev (σ)</th>
              <th>Sample Count</th>
              <th>Anomaly Lock</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

// ═════════════════════════════════════════════════════════════════════════
// 12. BIOSAMPLE INTELLIGENCE ENGINE (LABORATORY INTAKE)
// ═════════════════════════════════════════════════════════════════════════
Router.register('/biosamples', async () => {
  const crewSelector = await buildCrewSelector(currentCrewId);

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Shared BioSample Intelligence Engine</h2>
          <p class="text-secondary">Point-of-care specimen analysis. Ingests raw blood, urine, and saliva instrument measurements without Earth sample return.</p>
        </div>
      </div>

      ${crewSelector}

      <!-- Specimen Tabs -->
      <div class="tabs-nav">
        <button class="tab-btn active" onclick="window.switchBioTab('blood')">🩸 Blood (CBC & Cytokines)</button>
        <button class="tab-btn" onclick="window.switchBioTab('urine')">🧪 Urine (Renal & Solutes)</button>
        <button class="tab-btn" onclick="window.switchBioTab('saliva')">💧 Saliva (Stress & Viral Markers)</button>
      </div>

      <!-- Blood Tab Panel -->
      <div id="tab-blood" class="tab-panel active">
        <div class="card">
          <h3>Blood Panel Instrument Intake</h3>
          <form onsubmit="window.submitBloodSample(event)">
            <div class="form-grid-3">
              <div class="form-group">
                <label>Total WBC (x10³/μL)</label>
                <input type="number" step="0.1" id="blood-wbc" class="form-input" value="6.5" required>
              </div>
              <div class="form-group">
                <label>Lymphocytes (%)</label>
                <input type="number" step="0.1" id="blood-lymph" class="form-input" value="31.0" required>
              </div>
              <div class="form-group">
                <label>Neutrophils (%)</label>
                <input type="number" step="0.1" id="blood-neut" class="form-input" value="61.5" required>
              </div>
              <div class="form-group">
                <label>Platelets (x10³/μL)</label>
                <input type="number" step="1" id="blood-plt" class="form-input" value="240" required>
              </div>
              <div class="form-group">
                <label>IL-6 Cytokine (pg/mL)</label>
                <input type="number" step="0.1" id="blood-il6" class="form-input" value="1.8">
              </div>
              <div class="form-group">
                <label>TNF-α Cytokine (pg/mL)</label>
                <input type="number" step="0.1" id="blood-tnf" class="form-input" value="3.2">
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Run Quality Control & Ingest Blood Panel</button>
          </form>
          <div id="blood-results" class="result-box hidden"></div>
        </div>
      </div>

      <!-- Urine Tab Panel -->
      <div id="tab-urine" class="tab-panel hidden">
        <div class="card">
          <h3>Urine Chemistry Instrument Intake</h3>
          <form onsubmit="window.submitUrineSample(event)">
            <div class="form-grid-3">
              <div class="form-group">
                <label>Specific Gravity (1.005 - 1.035)</label>
                <input type="number" step="0.001" id="urine-sg" class="form-input" value="1.018" required>
              </div>
              <div class="form-group">
                <label>pH (4.5 - 8.0)</label>
                <input type="number" step="0.1" id="urine-ph" class="form-input" value="6.2" required>
              </div>
              <div class="form-group">
                <label>Creatinine (mg/dL)</label>
                <input type="number" step="1" id="urine-cr" class="form-input" value="120" required>
              </div>
              <div class="form-group">
                <label>Calcium (mg/dL)</label>
                <input type="number" step="0.1" id="urine-ca" class="form-input" value="15.0">
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Run Quality Control & Ingest Urinalysis</button>
          </form>
          <div id="urine-results" class="result-box hidden"></div>
        </div>
      </div>

      <!-- Saliva Tab Panel -->
      <div id="tab-saliva" class="tab-panel hidden">
        <div class="card">
          <h3>Saliva Stress & Viral DNA Intake</h3>
          <form onsubmit="window.submitSalivaSample(event)">
            <div class="form-grid-3">
              <div class="form-group">
                <label>Salivary Free Cortisol (μg/dL)</label>
                <input type="number" step="0.01" id="saliva-cortisol" class="form-input" value="0.45" required>
              </div>
              <div class="form-group">
                <label>EBV DNA (copies/mL)</label>
                <input type="number" step="1" id="saliva-ebv" class="form-input" value="0">
              </div>
              <div class="form-group">
                <label>VZV DNA (copies/mL)</label>
                <input type="number" step="1" id="saliva-vzv" class="form-input" value="0">
              </div>
            </div>
            <button type="submit" class="btn btn-teal">Run Quality Control & Ingest Saliva Assay</button>
          </form>
          <div id="saliva-results" class="result-box hidden"></div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.switchBioTab = (tabName) => {
  document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));

  const activeBtn = event.target;
  const activePanel = document.getElementById(`tab-${tabName}`);
  if (activeBtn) activeBtn.classList.add('active');
  if (activePanel) activePanel.classList.remove('hidden');
};

window.submitBloodSample = async (e) => {
  e.preventDefault();
  const resBox = document.getElementById('blood-results');
  try {
    const res = await API.ingestBlood({
      crew_id: currentCrewId,
      timestamp_met: Date.now() / 3600000,
      wbc_count_k_ul: parseFloat(document.getElementById('blood-wbc').value),
      lymphocyte_pct: parseFloat(document.getElementById('blood-lymph').value),
      neutrophil_pct: parseFloat(document.getElementById('blood-neut').value),
      platelets_k_ul: parseFloat(document.getElementById('blood-plt').value),
      il6_pg_ml: parseFloat(document.getElementById('blood-il6').value),
      tnf_alpha_pg_ml: parseFloat(document.getElementById('blood-tnf').value),
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested ${res.processed_analytes} blood biomarkers. Quality control passed.
      </div>
    `;
  } catch (err) {
    alert(`Blood ingest failed: ${err.message}`);
  }
};

window.submitUrineSample = async (e) => {
  e.preventDefault();
  const resBox = document.getElementById('urine-results');
  try {
    const res = await API.ingestUrine({
      crew_id: currentCrewId,
      timestamp_met: Date.now() / 3600000,
      specific_gravity: parseFloat(document.getElementById('urine-sg').value),
      ph: parseFloat(document.getElementById('urine-ph').value),
      creatinine_mg_dl: parseFloat(document.getElementById('urine-cr').value),
      calcium_mg_dl: parseFloat(document.getElementById('urine-ca').value),
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested ${res.processed_analytes} urine parameters. Quality control passed.
      </div>
    `;
  } catch (err) {
    alert(`Urine ingest failed: ${err.message}`);
  }
};

window.submitSalivaSample = async (e) => {
  e.preventDefault();
  const resBox = document.getElementById('saliva-results');
  try {
    const res = await API.ingestSaliva({
      crew_id: currentCrewId,
      timestamp_met: Date.now() / 3600000,
      cortisol_ug_dl: parseFloat(document.getElementById('saliva-cortisol').value),
      ebv_dna_copies_ml: parseFloat(document.getElementById('saliva-ebv').value),
      vzv_dna_copies_ml: parseFloat(document.getElementById('saliva-vzv').value),
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ingested ${res.processed_analytes} saliva parameters. Quality control passed.
      </div>
    `;
  } catch (err) {
    alert(`Saliva ingest failed: ${err.message}`);
  }
};

// ═════════════════════════════════════════════════════════════════════════
// 13. GROUND REVIEW & DELAYED TELEMEDICINE SCREEN
// ═════════════════════════════════════════════════════════════════════════
Router.register('/ground-review', async () => {
  const [queue, depth] = await Promise.all([
    API.getGroundQueue(),
    API.getQueueDepth(),
  ]);

  const queueRows = queue.length === 0
    ? `<tr><td colspan="6" class="text-center text-muted">Store-and-forward transmission queue is empty.</td></tr>`
    : queue.map((enc) => `
      <tr>
        <td><strong>${enc.encounter_uuid}</strong></td>
        <td>Crew #${enc.crew_id}</td>
        <td>Alert #${enc.alert_id}</td>
        <td><code class="checksum">${enc.checksum ? enc.checksum.slice(0, 12) + '...' : '--'}</code></td>
        <td><span class="badge ${enc.ground_synced ? 'badge-green' : 'badge-amber'}">${enc.ground_synced ? 'SYNCED' : 'QUEUED'}</span></td>
        <td>
          ${!enc.ground_synced ? `
            <button class="btn btn-xs btn-teal" onclick="window.syncEncounter(${enc.id})">Simulate Downlink</button>
          ` : '<span class="text-muted">Downlinked</span>'}
        </td>
      </tr>
    `).join('');

  const html = `
    <div class="screen-container">
      <div class="screen-header">
        <div>
          <h2>Hazard 3: Distance from Earth — Ground Review & Telemedicine</h2>
          <p class="text-secondary">Asynchronous Store-and-Forward Encounter Packages buffer telemetry during 20-min light latency windows.</p>
        </div>
      </div>

      <div class="stats-grid">
        ${Components.renderStatCard('Pending Encounters', depth.pending_encounters, 'Packages', 'Awaiting Earth downlink window')}
        ${Components.renderStatCard('One-Way Light Delay', '20.0', 'min', 'Speed-of-light Mars latency')}
        ${Components.renderStatCard('Cryptographic Integrity', 'SHA-256', '', 'Audit tamper-evident logging')}
      </div>

      <div class="card">
        <h3>Outbound Store-and-Forward Encounter Queue</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Encounter UUID</th>
              <th>Subject</th>
              <th>Linked Alert</th>
              <th>SHA-256 Checksum</th>
              <th>Link Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${queueRows}
          </tbody>
        </table>
      </div>

      <!-- Ground Physician Review Form -->
      <div class="card">
        <h3>Simulate Inbound Earth Flight Surgeon Review</h3>
        <p class="text-secondary">Mission control medical evaluation sent asynchronously to the spacecraft.</p>
        <form onsubmit="window.submitPhysicianReview(event)">
          <div class="form-row">
            <div class="form-group">
              <label>Target Encounter Package ID</label>
              <input type="number" id="review-enc-id" class="form-input" placeholder="e.g. 1" required>
            </div>
            <div class="form-group">
              <label>Ground Flight Surgeon Name</label>
              <input type="text" id="review-surgeon" class="form-input" value="Dr. Robert Mercer, MD (NASA Flight Surgeon)" required>
            </div>
          </div>
          <div class="form-group">
            <label>Clinical Review Findings & Instructions</label>
            <textarea id="review-text" class="form-textarea" rows="3" required>Concur with onboard autonomous action card execution. Maintain hydration and schedule repeat baseline check in 24 hours.</textarea>
          </div>
          <button type="submit" class="btn btn-primary">Transmit Ground Review to Spacecraft</button>
        </form>
        <div id="review-result-box" class="result-box hidden"></div>
      </div>
    </div>
  `;

  document.getElementById('app').innerHTML = html;
});

window.submitPhysicianReview = async (e) => {
  e.preventDefault();
  const encId = parseInt(document.getElementById('review-enc-id').value);
  const surgeon = document.getElementById('review-surgeon').value;
  const text = document.getElementById('review-text').value;
  const resBox = document.getElementById('review-result-box');

  try {
    const review = await API.submitReview({
      encounter_id: encId,
      reviewer: surgeon,
      review_text: text,
      recommendations: ['Maintain hydration', 'Follow CARD-CVD-AMBER-01'],
      approved_updates: {},
      received_met: Date.now() / 3600000,
    });
    resBox.classList.remove('hidden');
    resBox.innerHTML = `
      <div class="success-banner">
        ✓ Ground review received from ${review.reviewer} and logged in mission record.
      </div>
    `;
  } catch (err) {
    alert(`Review submission failed: ${err.message}`);
  }
};

// ── Application Initialization ──────────────────────────────────────────
Router.init();
