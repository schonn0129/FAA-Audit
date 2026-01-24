import { useState, useEffect } from 'react';
import { api } from '../services/api';

/**
 * ScopeSelector Component
 *
 * Allows users to define which of the 7 functions are in-scope for an audit.
 * This is a FILTER/VIEW - it doesn't modify ownership assignments.
 */
export default function ScopeSelector({ auditId, onScopeChange }) {
  const [availableFunctions, setAvailableFunctions] = useState([]);
  const [selectedFunctions, setSelectedFunctions] = useState([]);
  const [scopeName, setScopeName] = useState('');
  const [scopeRationale, setScopeRationale] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [hasExistingScope, setHasExistingScope] = useState(false);

  // Load existing scope on mount
  useEffect(() => {
    loadScope();
  }, [auditId]);

  const loadScope = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditScope(auditId);
      setAvailableFunctions(data.available_functions || []);

      if (data.scope) {
        setSelectedFunctions(data.scope.in_scope_functions || []);
        setScopeName(data.scope.scope_name || '');
        setScopeRationale(data.scope.scope_rationale || '');
        setHasExistingScope(true);
      } else {
        // Default: all functions selected
        setSelectedFunctions(data.available_functions || []);
        setHasExistingScope(false);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFunctionToggle = (func) => {
    setSelectedFunctions(prev => {
      if (prev.includes(func)) {
        return prev.filter(f => f !== func);
      } else {
        return [...prev, func];
      }
    });
  };

  const handleSelectAll = () => {
    setSelectedFunctions([...availableFunctions]);
  };

  const handleClearAll = () => {
    setSelectedFunctions([]);
  };

  const handleSave = async () => {
    if (selectedFunctions.length === 0) {
      setError('At least one function must be selected');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await api.saveAuditScope(auditId, {
        in_scope_functions: selectedFunctions,
        scope_name: scopeName || null,
        scope_rationale: scopeRationale || null,
      });
      setHasExistingScope(true);
      if (onScopeChange) {
        onScopeChange(selectedFunctions);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset scope to include all functions?')) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await api.deleteAuditScope(auditId);
      setSelectedFunctions([...availableFunctions]);
      setScopeName('');
      setScopeRationale('');
      setHasExistingScope(false);
      if (onScopeChange) {
        onScopeChange(availableFunctions);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="scope-selector loading">Loading scope configuration...</div>;
  }

  const inScopeCount = selectedFunctions.length;
  const totalFunctions = availableFunctions.length;

  return (
    <div className="scope-selector">
      <div className="scope-header">
        <h3>Audit Scope Selection</h3>
        <p className="scope-description">
          Select which functions to include in this audit. Out-of-scope items
          will be tracked as "deferred" with their assigned owners.
        </p>
      </div>

      {error && (
        <div className="scope-error">
          {error}
        </div>
      )}

      <div className="scope-metadata">
        <div className="form-group">
          <label htmlFor="scopeName">Scope Name (optional)</label>
          <input
            id="scopeName"
            type="text"
            value={scopeName}
            onChange={(e) => setScopeName(e.target.value)}
            placeholder="e.g., Q1 2026 Maintenance Focus"
          />
        </div>
        <div className="form-group">
          <label htmlFor="scopeRationale">Rationale (optional)</label>
          <textarea
            id="scopeRationale"
            value={scopeRationale}
            onChange={(e) => setScopeRationale(e.target.value)}
            placeholder="Why these functions were selected for this audit cycle..."
            rows={2}
          />
        </div>
      </div>

      <div className="scope-actions-top">
        <button
          type="button"
          onClick={handleSelectAll}
          className="btn-secondary"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={handleClearAll}
          className="btn-secondary"
        >
          Clear All
        </button>
        <span className="scope-count">
          {inScopeCount} of {totalFunctions} functions selected
        </span>
      </div>

      <div className="function-list">
        {availableFunctions.map(func => (
          <label key={func} className="function-checkbox">
            <input
              type="checkbox"
              checked={selectedFunctions.includes(func)}
              onChange={() => handleFunctionToggle(func)}
            />
            <span className="function-name">{func}</span>
            <span className={`status-badge ${selectedFunctions.includes(func) ? 'in-scope' : 'deferred'}`}>
              {selectedFunctions.includes(func) ? 'In Scope' : 'Deferred'}
            </span>
          </label>
        ))}
      </div>

      <div className="scope-actions">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || selectedFunctions.length === 0}
          className="btn-primary"
        >
          {saving ? 'Saving...' : 'Save Scope'}
        </button>
        {hasExistingScope && (
          <button
            type="button"
            onClick={handleReset}
            disabled={saving}
            className="btn-danger"
          >
            Reset to All
          </button>
        )}
      </div>

      {hasExistingScope && (
        <div className="scope-saved-notice">
          Scope is saved. Changes will take effect immediately.
        </div>
      )}
    </div>
  );
}
