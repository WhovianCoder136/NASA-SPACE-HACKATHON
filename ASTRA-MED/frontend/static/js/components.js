/**
 * ASTRA-MED Component Library
 * Reusable UI renderers for clinical dashboards, charts, alerts, and modals.
 * Deep-Space Mission Control & Aerospace Medical Intelligence System.
 */

const Components = {
  renderSeverityBadge(severity) {
    const sev = (severity || 'GREEN').toUpperCase();
    let badgeClass = 'badge-green';
    let icon = '●';
    if (sev === 'AMBER' || sev === 'CAUTION') {
      badgeClass = 'badge-amber';
      icon = '▲';
    } else if (sev === 'RED' || sev === 'CRITICAL') {
      badgeClass = 'badge-red';
      icon = '■';
    }
    return `<span class="badge ${badgeClass}"><span class="badge-dot">${icon}</span> ${sev}</span>`;
  },

  renderStatCard(title, value, unit = '', subtitle = '', severity = '') {
    let sevClass = '';
    const s = (severity || '').toUpperCase();
    if (s === 'RED') sevClass = 'border-red';
    else if (s === 'AMBER') sevClass = 'border-amber';
    else if (s === 'GREEN') sevClass = 'border-green';

    return `
      <div class="stat-card ${sevClass}">
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
    const metVal = typeof alert.timestamp_met === 'number' ? alert.timestamp_met.toFixed(1) : (alert.timestamp_met || '142.0');

    return `
      <div class="alert-card ${borderClass}" data-alert-id="${alert.id}">
        <div class="alert-top">
          <div class="alert-tags">
            ${badge}
            <span class="hazard-tag">${(alert.hazard || '').replace(/_/g, ' ')}</span>
            <span class="met-tag">MET: ${metVal}h</span>
          </div>
          ${!alert.acknowledged && canAcknowledge ? `
            <button class="btn btn-sm btn-outline ack-btn" onclick="window.acknowledgeAlert(${alert.id})">
              Acknowledge Alert
            </button>
          ` : '<span class="ack-status">✓ Acknowledged</span>'}
        </div>
        <div class="alert-metric">
          <strong>${alert.metric_name}</strong>: <span class="metric-value">${alert.observed_value}</span>
          <span class="z-score">(z = ${typeof alert.z_score === 'number' ? alert.z_score.toFixed(2) : alert.z_score})</span>
        </div>
        <p class="alert-summary">${alert.summary_text}</p>
        ${alert.action_card_id ? `
          <div class="alert-action-footer">
            <button class="btn btn-sm btn-teal" onclick="window.viewActionCard('${alert.action_card_id}')">
              View Protocol: ${alert.action_card_id} &rarr;
            </button>
          </div>
        ` : ''}
      </div>
    `;
  },

  renderModuleHealthCard(mod) {
    const isLive = mod.status === 'live';
    const statusText = isLive ? 'ONLINE' : 'STANDBY';
    const badgeClass = isLive ? 'badge-green' : 'badge-amber';

    return `
      <div class="module-card">
        <div class="module-header">
          <span class="module-name">${(mod.module || '').toUpperCase()}</span>
          <span class="badge ${badgeClass}">${statusText}</span>
        </div>
        <div class="module-meta">
          <span>Ver: <code style="color: var(--accent-primary);">${mod.version || '1.0.0'}</code></span>
          <span>Status: <strong>${isLive ? 'Telemetry Active' : 'Pre-flight Calibrated'}</strong></span>
        </div>
      </div>
    `;
  },

  renderProgressBar(label, value, max = 100, unit = '%') {
    const pct = Math.min(Math.max((value / max) * 100, 0), 100);
    let barColor = 'var(--accent-primary)';
    if (pct < 30) barColor = 'var(--red)';
    else if (pct < 70) barColor = 'var(--amber)';
    else barColor = 'var(--green)';

    return `
      <div class="progress-container">
        <div class="progress-labels">
          <span class="progress-title">${label}</span>
          <span class="progress-value">${typeof value === 'number' ? value.toFixed(1) : value}${unit}</span>
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
      .map(([k, v]) => `<div><strong>${k.replace(/_/g, ' ')}:</strong> <code>${v}</code></div>`)
      .join('');

    return `
      <div class="action-card-detail">
        <div class="modal-header">
          <div>
            <h2>${card.title}</h2>
            <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.2rem;">
              Protocol Identifier: <code>${card.card_id}</code> | Revision: <code>v${card.version}</code>
            </div>
          </div>
          <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
        </div>
        <div class="modal-meta" style="display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem;">
          ${this.renderSeverityBadge(card.severity)}
          <span class="system-tag">NASA STD-3001 COMPLIANT</span>
          <span class="system-tag">AUTONOMOUS CONTINGENCY</span>
        </div>
        <div class="modal-summary" style="background: rgba(13, 21, 39, 0.6); padding: 0.85rem; border-radius: var(--radius-sm); border-left: 3px solid var(--accent-primary); margin-bottom: 1.25rem;">
          <p style="margin: 0; font-size: 0.92rem; line-height: 1.5;">${card.plain_language_summary}</p>
        </div>
        <div class="modal-section">
          <h3>Crew Action Instructions</h3>
          <ol class="instructions-list">
            ${instructionsList}
          </ol>
        </div>
        ${limits ? `
          <div class="modal-section safety-box">
            <h3 style="color: var(--amber);">Clinical Safety Boundaries</h3>
            <div class="safety-grid">${limits}</div>
          </div>
        ` : ''}
        ${card.de_escalation_criteria ? `
          <div class="modal-section de-escalation-box">
            <h3 style="color: var(--green);">De-escalation & Resolution Criteria</h3>
            <p style="margin: 0;">${card.de_escalation_criteria}</p>
          </div>
        ` : ''}
        <div class="modal-footer" style="margin-top: 1.5rem; display: flex; justify-content: flex-end;">
          <button class="btn btn-secondary" onclick="Components.closeModal()">Dismiss Protocol</button>
        </div>
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
    let sevBadge = '<span class="badge badge-teal">● MONITOR</span>';
    let borderClass = 'alert-border-green';
    if (sev === 'warning' || sev === 'amber') {
      sevBadge = '<span class="badge badge-amber">▲ CAUTION</span>';
      borderClass = 'alert-border-amber';
    } else if (sev === 'critical' || sev === 'red') {
      sevBadge = '<span class="badge badge-red">■ CRITICAL REVIEW</span>';
      borderClass = 'alert-border-red';
    }

    const timeStr = insight.created_at ? new Date(insight.created_at).toLocaleTimeString() : 'Recent MET';

    return `
      <div class="alert-card ${borderClass}" data-insight-id="${insight.id}">
        <div class="alert-top">
          <div class="alert-tags">
            ${sevBadge}
            <span class="hazard-tag">${(insight.module || 'health').toUpperCase()}</span>
            <span class="met-tag">${timeStr}</span>
            ${insight.requires_medical_review ? '<span class="badge badge-red">Flight Surgeon Review Flagged</span>' : ''}
          </div>
          ${!insight.acknowledged && canAcknowledge ? `
            <button class="btn btn-sm btn-outline ack-btn" onclick="window.acknowledgeInsight(${insight.id})">
              Acknowledge
            </button>
          ` : '<span class="ack-status">✓ Acknowledged</span>'}
        </div>
        <p class="alert-summary" style="font-size: 0.95rem; line-height: 1.55; margin: 0.75rem 0; color: var(--text-bright);">
          ${insight.observation}
        </p>
        <div class="insight-meta" style="font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 1.25rem; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; flex-wrap: wrap;">
          <span>Subject: <strong style="color: var(--accent-primary);">${insight.subject_id}</strong></span>
          <span>Baseline Deviation: <strong>${insight.baseline_deviation_detected ? 'Yes (Statistically Significant)' : 'Within ±2σ'}</strong></span>
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
      ? `<div class="phase-updates-box" style="margin-top: 0.5rem; padding: 0.65rem; background: rgba(56, 189, 248, 0.05); border-left: 3px solid var(--accent-primary); font-size: 0.85rem; border-radius: var(--radius-xs);">
          <strong style="color: var(--accent-primary);">Approved Future Phase Adaptation:</strong>
          <pre style="margin: 0.25rem 0 0 0; font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-cyan);">${JSON.stringify(rep.future_phase_updates, null, 2)}</pre>
        </div>`
      : '';

    const physicianComments = rep.physician_comments
      ? `<div class="physician-comments" style="margin: 0.75rem 0; padding: 0.65rem 0.85rem; background: rgba(56, 189, 248, 0.08); border-radius: var(--radius-sm); border: 1px solid rgba(56, 189, 248, 0.2); font-size: 0.88rem;">
          <strong style="color: var(--accent-primary);">Ground Flight Surgeon Decision: ${rep.physician_decision || 'Reviewed'}</strong>
          <p style="margin: 0.25rem 0 0 0; color: var(--text-primary);">${rep.physician_comments}</p>
          ${updates}
        </div>`
      : '';

    return `
      <div class="card medical-report-card" style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <h3 style="margin: 0 0 0.25rem 0; font-size: 1.1rem; color: var(--text-bright);">${rep.title}</h3>
            <span class="text-muted" style="font-size: 0.82rem;">ID: <code style="color: var(--accent-primary);">${rep.report_id}</code> | Domain: <strong>${(rep.domain || '').toUpperCase()}</strong></span>
          </div>
          <div>${statusBadge}</div>
        </div>
        <p style="font-size: 0.92rem; line-height: 1.5; color: var(--text-secondary); margin: 0.5rem 0;">${rep.summary}</p>
        ${physicianComments}
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; margin-top: 0.5rem; font-size: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
          <span class="text-muted">Checksum: <code class="checksum">${rep.checksum ? rep.checksum.slice(0, 16) + '...' : '--'}</code></span>
          <div>
            ${rep.status === 'queued_for_sync' ? `
              <button class="btn btn-teal btn-xs" onclick="window.syncMedicalReport('${rep.report_id}')">Simulate 20-min Downlink</button>
            ` : ''}
            ${rep.status === 'transmitted' ? `
              <button class="btn btn-primary btn-xs" onclick="window.openSurgeonReviewModal('${rep.report_id}')">Simulate Ground Surgeon Review</button>
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

    const width = 540;
    const height = 180;
    const padding = 38;

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
      <circle cx="${getX(i).toFixed(1)}" cy="${getY(d.val).toFixed(1)}" r="4.5" fill="var(--accent-primary)" stroke="#080D1A" stroke-width="2">
        <title>MET Day ${d.met}: ${d.val} ${unit}</title>
      </circle>
    `).join('');

    return `
      <div class="trend-chart-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
          <h4 style="margin: 0; font-size: 0.95rem; color: var(--text-bright);">${title}</h4>
          <span style="font-size: 0.8rem; color: var(--accent-primary); font-family: var(--font-mono);">Baseline: ${baselineMean.toFixed(1)} ± ${baselineStd.toFixed(1)} ${unit}</span>
        </div>
        <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; background: rgba(10, 15, 30, 0.7); border-radius: var(--radius-sm); border: 1px solid var(--border-light);">
          <!-- ±2σ Confidence Corridor -->
          <rect x="${padding}" y="${upperY}" width="${width - 2 * padding}" height="${corridorHeight}" fill="rgba(56, 189, 248, 0.08)" />

          <!-- Upper and Lower ±2σ Thresholds -->
          <line x1="${padding}" y1="${upperY}" x2="${width - padding}" y2="${upperY}" stroke="rgba(245, 158, 11, 0.45)" stroke-dasharray="4,4" stroke-width="1.2" />
          <text x="${width - padding + 5}" y="${upperY}" fill="var(--amber)" font-size="9" alignment-baseline="middle" font-family="var(--font-mono)">+2σ</text>

          <line x1="${padding}" y1="${lowerY}" x2="${width - padding}" y2="${lowerY}" stroke="rgba(245, 158, 11, 0.45)" stroke-dasharray="4,4" stroke-width="1.2" />
          <text x="${width - padding + 5}" y="${lowerY}" fill="var(--amber)" font-size="9" alignment-baseline="middle" font-family="var(--font-mono)">-2σ</text>

          <!-- Baseline Mean (μ) Line -->
          <line x1="${padding}" y1="${meanY}" x2="${width - padding}" y2="${meanY}" stroke="rgba(20, 184, 166, 0.7)" stroke-width="1.5" />
          <text x="${width - padding + 5}" y="${meanY}" fill="var(--teal)" font-size="10" alignment-baseline="middle" font-family="var(--font-mono)">μ</text>

          <!-- Telemetry Line -->
          <polyline fill="none" stroke="var(--accent-primary)" stroke-width="2.5" points="${polyPoints}" />
          ${dots}

          <!-- Axis Labels -->
          <text x="${padding}" y="${height - 12}" fill="var(--text-muted)" font-size="9" font-family="var(--font-mono)">MET Day ${dataPoints[0].met}</text>
          <text x="${width - padding}" y="${height - 12}" fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">MET Day ${dataPoints[dataPoints.length - 1].met}</text>
        </svg>
      </div>
    `;
  },

  renderSimpleSVGSparkline(values, width = 200, height = 40, color = 'var(--accent-primary)') {
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
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem; filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4));">📄</div>
        <div style="font-weight: 600; font-size: 1.05rem; color: var(--accent-primary); margin-bottom: 0.25rem;">
          Click to Browse or Drag & Drop Diagnostic Files
        </div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 0.65rem 0;">
          Supported formats: <strong>${allowedText}</strong> (Max 100 MB per file)
        </p>
        <div style="font-size: 0.75rem; color: var(--text-muted); background: rgba(56, 189, 248, 0.06); padding: 0.35rem 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-light); display: inline-block;">
          Diagnostic payload is preserved securely in onboard storage; SHA-256 cryptographic signatures are audited for flight logs.
        </div>
      </div>
      <div id="selected-files-list" class="selected-files-container" style="margin-top: 0.75rem;"></div>
    `;
  },

  renderCheckupDetailModal(checkup) {
    const measurementsRows = (checkup.measurements || []).map((m) => `
      <tr>
        <td><strong style="color: var(--accent-primary);">${(m.domain || '').toUpperCase()}</strong></td>
        <td>${(m.metric_name || '').replace(/_/g, ' ')}</td>
        <td><strong style="font-size: 1rem; font-family: var(--font-mono); color: var(--text-bright);">${m.value}</strong></td>
        <td style="color: var(--text-secondary);">${m.unit}</td>
        <td style="font-family: var(--font-mono); color: var(--text-muted);">${m.reference_range || '--'}</td>
        <td><span class="badge badge-teal">${m.data_source || 'CLINICAL'}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="6" class="text-center text-muted" style="padding: 1.5rem;">No discrete physiological measurements recorded in this checkup session.</td></tr>';

    const filesRows = (checkup.files || []).map((f) => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0.85rem; background: var(--bg-secondary); border: 1px solid var(--border-light); border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
        <div>
          <strong style="color: var(--text-bright);">${f.original_filename}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem;">
            Module: <code>${f.health_module}</code> | ${(f.file_size_bytes / 1024).toFixed(1)} KB | SHA-256: <code>${f.sha256_checksum.slice(0, 12)}...</code>
          </div>
        </div>
        <a href="/api/v1/medical-files/${f.file_id}" target="_blank" class="btn btn-outline btn-xs">Download File</a>
      </div>
    `).join('') || '<div class="text-muted" style="font-size: 0.85rem;">No diagnostic attachments uploaded with this checkup.</div>';

    return `
      <div class="checkup-detail-modal">
        <div class="modal-header">
          <div>
            <h2>${checkup.checkup_type} — ${checkup.checkup_id}</h2>
            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.2rem;">
              Astronaut: <strong style="color: var(--accent-primary);">${checkup.crew_name} (${checkup.astronaut_id})</strong> | Timestamp: <strong>${checkup.checkup_date} ${checkup.checkup_time || ''}</strong>
            </div>
          </div>
          <button class="close-modal-btn" onclick="Components.closeModal()">&times;</button>
        </div>

        <div style="display: flex; gap: 0.85rem; margin: 1rem 0; flex-wrap: wrap;">
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Facility</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.location || 'Flight Habitat'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Examiner</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.medical_officer || 'Self-Reported'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Submission Mode</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 0.25rem;">${checkup.is_submitted_by_officer ? 'Medical Officer Proxy' : 'Astronaut Self-Entry'}</div>
          </div>
          <div class="stat-card" style="flex: 1; min-width: 140px; padding: 0.75rem;">
            <div class="stat-title">Audit Record</div>
            <div style="margin-top: 0.25rem;"><span class="badge ${checkup.is_amendment ? 'badge-amber' : 'badge-green'}">${(checkup.submission_status || 'verified').toUpperCase()}</span></div>
          </div>
        </div>

        ${checkup.notes ? `
          <div class="card" style="margin-bottom: 1.25rem; padding: 0.85rem; background: rgba(13, 21, 39, 0.6); border-left: 3px solid var(--accent-primary);">
            <strong style="color: var(--accent-primary); font-size: 0.85rem;">Clinical Notes & Observations:</strong>
            <p style="font-size: 0.9rem; margin: 0.35rem 0 0 0; white-space: pre-wrap; color: var(--text-primary); line-height: 1.5;">${checkup.notes}</p>
          </div>
        ` : ''}

        <div class="modal-section" style="margin-top: 1rem;">
          <h3>Physiological & Laboratory Telemetry Data</h3>
          <div class="table-container">
            <table class="data-table">
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
        </div>

        <div class="modal-section" style="margin-top: 1.5rem;">
          <h3>Diagnostic Reports & Medical Attachments</h3>
          <div>${filesRows}</div>
        </div>

        <div class="modal-footer" style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
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
