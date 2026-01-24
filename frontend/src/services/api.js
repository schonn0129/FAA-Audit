/**
 * API service for communicating with the backend
 */

const API_BASE_URL = '/api';

export const api = {
  /**
   * Upload a PDF file
   */
  async uploadPDF(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
        throw new Error(errorData.error || `Upload failed: ${response.status} ${response.statusText}`);
      }

      return response.json();
    } catch (err) {
      if (err.message) {
        throw err;
      }
      throw new Error('Network error: Could not connect to server. Make sure the backend is running on port 5000.');
    }
  },

  /**
   * Get all audit records
   */
  async getAudits(page = 1, limit = 10, status = null) {
    const params = new URLSearchParams({ page, limit });
    if (status) params.append('status', status);

    const response = await fetch(`${API_BASE_URL}/audits?${params}`);
    if (!response.ok) throw new Error('Failed to fetch audits');
    return response.json();
  },

  /**
   * Get a specific audit record
   */
  async getAudit(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}`);
    if (!response.ok) throw new Error('Failed to fetch audit');
    return response.json();
  },

  /**
   * Update an audit record
   */
  async updateAudit(auditId, data) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update audit');
    return response.json();
  },

  /**
   * Delete an audit record
   */
  async deleteAudit(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete audit');
    return response.json();
  },

  /**
   * Search audit records
   */
  async searchAudits(query, dateFrom = null, dateTo = null) {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);

    const response = await fetch(`${API_BASE_URL}/audits/search?${params}`);
    if (!response.ok) throw new Error('Search failed');
    return response.json();
  },

  /**
   * Health check
   */
  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },

  // =============================================================================
  // OWNERSHIP ENDPOINTS (Phase 2)
  // =============================================================================

  /**
   * Run ownership assignment for an audit
   */
  async runOwnershipAssignment(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/ownership`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Assignment failed' }));
      throw new Error(error.error || 'Failed to run ownership assignment');
    }
    return response.json();
  },

  /**
   * Get ownership assignments for an audit
   */
  async getOwnershipAssignments(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/ownership`);
    if (!response.ok) throw new Error('Failed to fetch ownership assignments');
    return response.json();
  },

  /**
   * Override ownership assignment for a question
   */
  async overrideOwnership(auditId, qid, data) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/ownership/${qid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Override failed' }));
      throw new Error(error.error || 'Failed to override ownership');
    }
    return response.json();
  },

  // =============================================================================
  // SCOPE ENDPOINTS (Phase 3)
  // =============================================================================

  /**
   * Get scope configuration for an audit
   */
  async getAuditScope(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/scope`);
    if (!response.ok) throw new Error('Failed to fetch audit scope');
    return response.json();
  },

  /**
   * Save scope configuration for an audit
   */
  async saveAuditScope(auditId, scopeData) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/scope`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scopeData),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Save failed' }));
      throw new Error(error.error || 'Failed to save scope');
    }
    return response.json();
  },

  /**
   * Delete scope configuration (reset to all functions)
   */
  async deleteAuditScope(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/scope`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete scope');
    return response.json();
  },

  /**
   * Get coverage metrics for an audit
   */
  async getCoverageMetrics(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/coverage`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Fetch failed' }));
      throw new Error(error.error || 'Failed to fetch coverage metrics');
    }
    return response.json();
  },

  /**
   * Get deferred items report for an audit
   */
  async getDeferredItems(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/deferred`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Fetch failed' }));
      throw new Error(error.error || 'Failed to fetch deferred items');
    }
    return response.json();
  },

  // =============================================================================
  // MAP ENDPOINTS (Phase 4)
  // =============================================================================

  /**
   * Get MAP rows for an audit
   */
  async getAuditMap(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/map`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Fetch failed' }));
      throw new Error(error.error || 'Failed to fetch MAP');
    }
    return response.json();
  },

  /**
   * Build a download URL for MAP export
   */
  getAuditMapExportUrl(auditId, format = 'xlsx') {
    return `${API_BASE_URL}/audits/${auditId}/map/export?format=${format}`;
  },

  // =============================================================================
  // MANUAL ENDPOINTS
  // =============================================================================

  /**
   * Upload a company manual (AIP/GMM)
   */
  async uploadManual(file, manualType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('manual_type', manualType || 'Other');

    const response = await fetch(`${API_BASE_URL}/manuals/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new Error(error.error || 'Manual upload failed');
    }
    return response.json();
  },

  /**
   * List uploaded manuals
   */
  async getManuals(manualType = null) {
    const url = manualType
      ? `${API_BASE_URL}/manuals?type=${encodeURIComponent(manualType)}`
      : `${API_BASE_URL}/manuals`;
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Fetch failed' }));
      throw new Error(error.error || 'Failed to fetch manuals');
    }
    return response.json();
  },

  // =============================================================================
  // APPLICABILITY ENDPOINTS
  // =============================================================================

  async getApplicability(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/applicability`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Fetch failed' }));
      throw new Error(error.error || 'Failed to fetch applicability');
    }
    return response.json();
  },

  async setApplicability(auditId, qid, isApplicable, reason = '') {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/applicability/${qid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        is_applicable: isApplicable,
        reason
      })
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Update failed' }));
      throw new Error(error.error || 'Failed to update applicability');
    }
    return response.json();
  },

  async autoDetectApplicability(auditId) {
    const response = await fetch(`${API_BASE_URL}/audits/${auditId}/applicability/auto`, {
      method: 'POST'
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Auto-detect failed' }));
      throw new Error(error.error || 'Failed to auto-detect applicability');
    }
    return response.json();
  },
};
