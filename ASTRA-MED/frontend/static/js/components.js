/**
 * ASTRA-MED Component Library
 * Reusable UI renderers for clinical dashboards, charts, alerts, and modals.
 */

const Components = {
  renderSeverityBadge(severity) {
    const sev = (severity || 'GREEN').toUpperCase();
    let badgeClass = 'badge-green';
    let icon = '●';
    if (sev === 'AMBER') {
      badgeClass = 'badge-amber';
      icon = '▲';
    } else if (sev === 'RED') {
      badgeClass = 'badge-red';
      icon = '■';
    }
    return `<span class="badge ${badgeClass}"><span class="badge-dot">${icon}</span> ${sev}</span>`;
  },

  renderStatCard(title, value, unit = '', subtitle = '', severity = '') {
    let sevBorder = '';
    if (severity === 'RED') sevBorder = 'border-red';
    else if (severity === 'AMBER') sevBorder = 'border-amber';
    else if (severity === 'GREEN') sevBorder = 'border-green';

    return `
      <div class="stat-card ${sevBorder}">
        <div class="stat-header">
          <span class="stat-title">${title}</span>
        </div>
        <div class="stat-body">
          <span class="stat-value">${value}</span>
          ${unit ? `<span class="stat-unit">${unit}</span>` : ''}
        </div>
        ${subtitle ? `<div class="stat-subtitle">${subtitle}</div>` : ''}
      </div>
    `;
  },

  renderAlertCard(alert, canAcknowledge = true) {
    const sev = (alert.severity || 'GREEN').toUpperCase();
    const borderClass = `alert-border-${sev.toLowerCase()}`;
    const badge = this.renderSeverityBadge(sev);

    return `
      <div class="alert-card ${borderClass}" data-alert-id="${alert.id}">
        <div class="alert-top">
          <div class="alert-tags">
            ${badge}
            <span class="hazard-tag">${(alert.hazard || '').replace(/_/g, ' ')}</span>
            <span class="met-tag">MET: ${typeof alert.timestamp_met === 'number' ? alert.timestamp_met.toFixed(1) : alert.timestamp_met}h</span>
          </div>
          ${!alert.acknowledged && canAcknowledge ? `
            <button class="btn btn-sm btn-outline ack-btn" onclick="window.acknowledgeAlert(${alert.id})">
              Acknowledge
            </button>
          ` : '<span class="ack-status">✓ Acknowledged</span>'}
        </div>
        <div class="alert-metric">
          <strong>${alert.metric_name}</strong>: ${alert.observed_value} 
          <span class="z-score">(z = ${typeof alert.z_score === 'number' ? alert.z_score.toFixed(2) : alert.z_score})</span>
        </div>
        <p class="alert-summary">${alert.summary_text}</p>
        ${alert.action_card_id ? `
          <div class="alert-action-footer">
            <button class="btn btn-sm btn-teal" onclick="window.viewActionCard('${alert.action_card_id}')">
              View Protocol: ${alert.action_card_id}
            </button>
          </div>
        ` : ''}
      </div>
    `;
  },

  renderModuleHealthCard(mod) {
    const isLive = mod.status === 'live';
    const statusText = isLive ? 'LIVE' : 'PLACEHOLDER';
    const badgeClass = isLive ? 'badge-green' : 'badge-amber';

    return `
      <div class="module-card">
        <div class="module-header">
          <span class="module-name">${mod.module.toUpperCase()}</span>
          <span class="badge ${badgeClass}">${statusText}</span>
        </div>
        <div class="module-meta">
          <span>Ver: ${mod.version}</span>
          <span>Status: ${isLive ? 'Model Online' : 'Drop-in Ready'}</span>
        </div>
      </div>
    `;
  },

  renderProgressBar(label, value, max = 100, unit = '%') {
    const pct = Math.min(Math.max((value / max) * 100, 0), 100);
    let barColor = 'var(--teal)';
    if (pct < 30) barColor = 'var(--red)';
    else if (pct < 70) barColor = 'var(--amber)';

    return `
      <div class="progress-container">
        <div class="progress-labels">
          <span class="progress-title">${label}</span>
          <span class="progress-value">${value.toFixed(1)}${unit}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${pct}%; background-color: ${barColor};"></div>
        </div>
      </div>
    `;
  },

  renderActionCardModal(card) {
    const instructionsList = (card.crew_instructions || [])
      .map((step, idx) => `
        <li class="instruction-item">
          <span class="step-num">${idx + 1}</span>
          <span class="step-text">${step}</span>
        </li>
      `).join('');

    const limits = Object.entries(card.safety_limits || {})
      .map(([k, v]) => `<div><strong>${k.replace(/_/g, ' ')}:</strong> ${v}</div>`)
      .join('');

    return `
      <div class="action-card-detail">
        <div class="modal-header">
          <h2>${card.title}</h2>
          <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
        </div>
        <div class="modal-meta">
          <span><strong>ID:</strong> ${card.card_id}</span>
          <span><strong>Version:</strong> ${card.version}</span>
          ${this.renderSeverityBadge(card.severity)}
        </div>
        <div class="modal-summary">
          <p>${card.plain_language_summary}</p>
        </div>
        <div class="modal-section">
          <h3>Crew Action Instructions</h3>
          <ol class="instructions-list">
            ${instructionsList}
          </ol>
        </div>
        ${limits ? `
          <div class="modal-section safety-box">
            <h3>Safety Boundaries</h3>
            <div class="safety-grid">${limits}</div>
          </div>
        ` : ''}
        ${card.de_escalation_criteria ? `
          <div class="modal-section de-escalation-box">
            <h3>De-escalation Criteria</h3>
            <p>${card.de_escalation_criteria}</p>
          </div>
        ` : ''}
      </div>
    `;
  },

  renderEmptyState(message) {
    return `
      <div class="empty-state">
        <div class="empty-icon">🛰️</div>
        <p class="empty-text">${message}</p>
      </div>
    `;
  },

  renderInsightCard(insight, canAcknowledge = true) {
    const sev = (insight.severity || 'monitor').toLowerCase();
    let sevBadge = '<span class="badge badge-teal">MONITOR</span>';
    let borderClass = 'alert-border-green';
    if (sev === 'warning') {
      sevBadge = '<span class="badge badge-amber">▲ WARNING</span>';
      borderClass = 'alert-border-amber';
    } else if (sev === 'critical') {
      sevBadge = '<span class="badge badge-red">■ CRITICAL REVIEW</span>';
      borderClass = 'alert-border-red';
    }

    const timeStr = insight.created_at ? new Date(insight.created_at).toLocaleTimeString() : 'Recent';

    return `
      <div class="alert-card ${borderClass}" data-insight-id="${insight.id}">
        <div class="alert-top">
          <div class="alert-tags">
            ${sevBadge}
            <span class="hazard-tag">${(insight.module || 'health').toUpperCase()}</span>
            <span class="met-tag">${timeStr}</span>
            ${insight.requires_medical_review ? '<span class="badge badge-red">Physician Review Flagged</span>' : ''}
          </div>
          ${!insight.acknowledged && canAcknowledge ? `
            <button class="btn btn-sm btn-outline ack-btn" onclick="window.acknowledgeInsight(${insight.id})">
              Acknowledge
            </button>
          ` : '<span class="ack-status">✓ Acknowledged</span>'}
        </div>
        <p class="alert-summary" style="font-size: 0.95rem; line-height: 1.5; margin: 0.75rem 0;">
          ${insight.observation}
        </p>
        <div class="insight-meta" style="font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 1rem; border-top: 1px solid var(--border-color); padding-top: 0.5rem;">
          <span>Subject: <strong>${insight.subject_id}</strong></span>
          <span>Deviation Detected: <strong>${insight.baseline_deviation_detected ? 'Yes' : 'No'}</strong></span>
          <span>Diagnosis: <strong style="color: var(--teal);">None (Autonomous Research Protocol)</strong></span>
        </div>
      </div>
    `;
  },

  renderMedicalReportCard(rep) {
    let statusBadge = '<span class="badge badge-amber">QUEUED FOR EARTH SYNC</span>';
    if (rep.status === 'transmitted') {
      statusBadge = '<span class="badge badge-teal">TRANSMITTED TO EARTH</span>';
    } else if (rep.status === 'reviewed') {
      statusBadge = '<span class="badge badge-green">PHYSICIAN REVIEW RECEIVED</span>';
    }

    const updates = rep.future_phase_updates && Object.keys(rep.future_phase_updates).length > 0
      ? `<div class="phase-updates-box" style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(0,255,200,0.05); border-left: 3px solid var(--teal); font-size: 0.85rem;">
          <strong>Approved Future Phase Adaptation:</strong>
          <pre style="margin: 0.25rem 0 0 0; font-family: monospace;">${JSON.stringify(rep.future_phase_updates, null, 2)}</pre>
        </div>`
      : '';

    const physicianComments = rep.physician_comments
      ? `<div class="physician-comments" style="margin: 0.75rem 0; padding: 0.5rem 0.75rem; background: rgba(56, 189, 248, 0.08); border-radius: 4px; font-size: 0.9rem;">
          <strong style="color: #38bdf8;">Ground Flight Surgeon Decision: ${rep.physician_decision || 'Reviewed'}</strong>
          <p style="margin: 0.25rem 0 0 0;">${rep.physician_comments}</p>
          ${updates}
        </div>`
      : '';

    return `
      <div class="card medical-report-card" style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
          <div>
            <h3 style="margin: 0 0 0.25rem 0;">${rep.title}</h3>
            <span class="text-muted" style="font-size: 0.85rem;">ID: <code>${rep.report_id}</code> | Domain: <strong>${(rep.domain || '').toUpperCase()}</strong></span>
          </div>
          <div>${statusBadge}</div>
        </div>
        <p style="font-size: 0.95rem; line-height: 1.5; color: var(--text-secondary); margin: 0.5rem 0;">${rep.summary}</p>
        ${physicianComments}
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 0.5rem; margin-top: 0.5rem; font-size: 0.8rem;">
          <span class="text-muted">Checksum: <code class="checksum">${rep.checksum ? rep.checksum.slice(0, 16) + '...' : '--'}</code></span>
          <div>
            ${rep.status === 'queued_for_sync' ? `
              <button class="btn btn-teal btn-xs" onclick="window.syncMedicalReport('${rep.report_id}')">Simulate 20-min Downlink</button>
            ` : ''}
            ${rep.status === 'transmitted' ? `
              <button class="btn btn-primary btn-xs" onclick="window.openSurgeonReviewModal('${rep.report_id}')">Simulate Physician Review</button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  },

  renderInteractiveTrendChart(title, dataPoints, baselineMean, baselineStd, unit = '') {
    if (!dataPoints || dataPoints.length === 0) {
      dataPoints = [
        { met: 130, val: baselineMean - 1.2 },
        { met: 133, val: baselineMean + 0.8 },
        { met: 136, val: baselineMean - 0.4 },
        { met: 139, val: baselineMean + 1.6 },
        { met: 142, val: baselineMean + 0.2 },
      ];
    }

    const width = 500;
    const height = 160;
    const padding = 35;

    const values = dataPoints.map((d) => d.val);
    const upper2sigma = baselineMean + 2 * baselineStd;
    const lower2sigma = baselineMean - 2 * baselineStd;

    const minVal = Math.min(...values, lower2sigma) * 0.95;
    const maxVal = Math.max(...values, upper2sigma) * 1.05;
    const range = maxVal - minVal || 1;

    const getY = (val) => height - padding - ((val - minVal) / range) * (height - 2 * padding);
    const getX = (idx) => padding + (idx / Math.max(dataPoints.length - 1, 1)) * (width - 2 * padding);

    const polyPoints = dataPoints.map((d, i) => `${getX(i).toFixed(1)},${getY(d.val).toFixed(1)}`).join(' ');

    const meanY = getY(baselineMean).toFixed(1);
    const upperY = getY(upper2sigma).toFixed(1);
    const lowerY = getY(lower2sigma).toFixed(1);

    const corridorHeight = Math.abs(lowerY - upperY);

    const dots = dataPoints.map((d, i) => `
      <circle cx="${getX(i).toFixed(1)}" cy="${getY(d.val).toFixed(1)}" r="4" fill="var(--teal)" stroke="#0b132b" stroke-width="2">
        <title>MET Day ${d.met}: ${d.val} ${unit}</title>
      </circle>
    `).join('');

    return `
      <div class="trend-chart-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <h4 style="margin: 0; font-size: 0.95rem;">${title}</h4>
          <span style="font-size: 0.8rem; color: var(--teal);">Baseline: ${baselineMean.toFixed(1)} ± ${baselineStd.toFixed(1)} ${unit}</span>
        </div>
        <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; background: rgba(15, 23, 42, 0.6); border-radius: 6px; border: 1px solid var(--border-color);">
          <!-- ±2σ Corridor -->
          <rect x="${padding}" y="${upperY}" width="${width - 2 * padding}" height="${corridorHeight}" fill="rgba(20, 184, 166, 0.08)" />
          
          <!-- Upper and Lower Limit Lines -->
          <line x1="${padding}" y1="${upperY}" x2="${width - padding}" y2="${upperY}" stroke="rgba(245, 158, 11, 0.4)" stroke-dasharray="4" stroke-width="1" />
          <line x1="${padding}" y1="${lowerY}" x2="${width - padding}" y2="${lowerY}" stroke="rgba(245, 158, 11, 0.4)" stroke-dasharray="4" stroke-width="1" />
          
          <!-- Baseline Center Mean Line -->
          <line x1="${padding}" y1="${meanY}" x2="${width - padding}" y2="${meanY}" stroke="rgba(20, 184, 166, 0.7)" stroke-width="1.5" />
          <text x="${width - padding + 4}" y="${meanY}" fill="var(--teal)" font-size="10" alignment-baseline="middle">μ</text>

          <!-- Telemetry Line -->
          <polyline fill="none" stroke="var(--teal)" stroke-width="2.5" points="${polyPoints}" />
          ${dots}

          <!-- Axis Labels -->
          <text x="${padding}" y="${height - 10}" fill="var(--text-muted)" font-size="9">MET Day ${dataPoints[0].met}</text>
          <text x="${width - padding}" y="${height - 10}" fill="var(--text-muted)" font-size="9" text-anchor="end">MET Day ${dataPoints[dataPoints.length - 1].met}</text>
        </svg>
      </div>
    `;
  },

  renderSimpleSVGSparkline(values, width = 200, height = 40, color = 'var(--teal)') {
    if (!values || values.length < 2) return '';
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const points = values.map((val, i) => {
      const x = (i / (values.length - 1)) * (width - 10) + 5;
      const y = height - 5 - ((val - min) / range) * (height - 10);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    return `
      <svg width="${width}" height="${height}" class="sparkline" viewBox="0 0 ${width} ${height}">
        <polyline fill="none" stroke="${color}" stroke-width="2" points="${points}" />
      </svg>
    `;
  },

  renderMedicalFileUploadZone(zoneId = 'checkup-dropzone', inputId = 'checkup-file-input', allowedText = 'PDF, JPG, PNG, TIFF, DICOM, CSV, JSON, NPY, WAV') {
    return `
      <div class="upload-dropzone" id="${zoneId}" onclick="document.getElementById('${inputId}').click()">
        <input type="file" id="${inputId}" multiple style="display: none;" onchange="window.handleCheckupFileSelect(event)">
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📄</div>
        <div style="font-weight: 600; font-size: 1rem; color: var(--teal); margin-bottom: 0.25rem;">
          Click to Browse or Drag & Drop Medical Files
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0 0 0.5rem 0;">
          Supported formats: <strong>${allowedText}</strong> (Max 100 MB per file)
        </p>
        <div style="font-size: 0.75rem; color: var(--text-secondary); background: rgba(20, 184, 166, 0.05); padding: 0.25rem 0.75rem; border-radius: 4px; display: inline-block;">
          Original files are preserved securely in local storage; SHA-256 checksums are logged for clinical audit.
        </div>
      </div>
      <div id="selected-files-list" class="selected-files-container" style="margin-top: 0.75rem;"></div>
    `;
  },

  renderCheckupDetailModal(checkup) {
    const measurementsRows = (checkup.measurements || []).map((m) => `
      <tr>
        <td><strong style="color: var(--teal);">${m.domain.toUpperCase()}</strong></td>
        <td>${m.metric_name.replace(/_/g, ' ')}</td>
        <td><strong style="font-size: 1rem;">${m.value}</strong></td>
        <td>${m.unit}</td>
        <td>${m.reference_range || '--'}</td>
        <td><span class="badge badge-teal">${m.data_source}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="6" class="text-center text-muted">No discrete measurements recorded in this checkup session.</td></tr>';

    const filesRows = (checkup.files || []).map((f) => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; background: rgba(15, 23, 42, 0.5); border: 1px solid var(--border-color); border-radius: 4px; margin-bottom: 0.5rem;">
        <div>
          <strong>${f.original_filename}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">
            Module: <code>${f.health_module}</code> | ${(f.file_size_bytes / 1024).toFixed(1)} KB | SHA-256: <code>${f.sha256_checksum.slice(0, 12)}...</code>
          </div>
        </div>
        <a href="/api/v1/medical-files/${f.file_id}" target="_blank" class="btn btn-outline btn-xs">Download Report</a>
      </div>
    `).join('') || '<div class="text-muted" style="font-size: 0.85rem;">No files uploaded with this checkup.</div>';

    return `
      <div class="checkup-detail-modal">
        <div class="modal-header">
          <div>
            <h2>${checkup.checkup_type} — ${checkup.checkup_id}</h2>
            <div style="font-size: 0.85rem; color: var(--text-secondary);">
              Astronaut: <strong>${checkup.crew_name} (${checkup.astronaut_id})</strong> | Date: <strong>${checkup.checkup_date} ${checkup.checkup_time || ''}</strong>
            </div>
          </div>
          <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
        </div>

        <div style="display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap;">
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Location</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.location || 'Flight Habitat'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Medical Officer</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.medical_officer || 'Self-Reported'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Submission Mode</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.is_submitted_by_officer ? 'Medical Officer Proxy' : 'Astronaut Self-Entry'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Audit Status</div>
            <div style="margin-top: 0.25rem;"><span class="badge ${checkup.is_amendment ? 'badge-amber' : 'badge-green'}">${checkup.submission_status.toUpperCase()}</span></div>
          </div>
        </div>

        ${checkup.notes ? `
          <div class="card" style="margin-bottom: 1rem; padding: 0.75rem; background: rgba(30, 41, 59, 0.4);">
            <strong style="color: var(--teal); font-size: 0.85rem;">Clinical Notes & Observations:</strong>
            <p style="font-size: 0.9rem; margin: 0.25rem 0 0 0; white-space: pre-wrap;">${checkup.notes}</p>
          </div>
        ` : ''}

        <div class="modal-section" style="margin-top: 1rem;">
          <h3>Recorded Physiological & Laboratory Measurements</h3>
          <table class="data-table" style="font-size: 0.85rem;">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Metric</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Reference Range</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              ${measurementsRows}
            </tbody>
          </table>
        </div>

        <div class="modal-section" style="margin-top: 1.5rem;">
          <h3>Associated Medical Reports & Diagnostic Files</h3>
          <div>${filesRows}</div>
        </div>

        <div class="modal-footer" style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button class="btn btn-secondary" onclick="Components.closeModal()">Close Dossier</button>
          <button class="btn btn-outline" onclick="window.openAmendModal('${checkup.checkup_id}')">Submit Clinical Amendment</button>
        </div>
      </div>
    `;
  },

  openModal(html) {
    const overlay = document.getElementById('modal-overlay');
    const content = document.getElementById('modal-content');
    if (overlay && content) {
      content.innerHTML = html;
      overlay.classList.add('active');
    }
  },

  closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
      overlay.classList.remove('active');
    }
  },
};

// Global handlers for HTML inline clicks
window.Components = Components;
window.viewActionCard = async (cardId) => {
  try {
    const card = await API.getActionCard(cardId);
    Components.openModal(Components.renderActionCardModal(card));
  } catch (e) {
    alert(`Could not load action card: ${e.message}`);
  }
};
