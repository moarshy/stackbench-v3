import { useState } from 'react';
import { Settings as SettingsIcon, X, FolderOpen } from 'lucide-react';
import { apiService } from '../services/api';

interface SettingsProps {
  onClose: () => void;
}

export function Settings({ onClose }: SettingsProps) {
  const config = apiService.getConfig();
  const [baseDataDir, setBaseDataDir] = useState(config.baseDataDir);

  const handleSave = () => {
    apiService.updateConfig({
      baseDataDir,
    });
    onClose();
    // Reload the page to apply new settings
    window.location.reload();
  };

  return (
    <div className="settings-modal-backdrop">
      <div className="settings-modal-container">
        {/* Header */}
        <div className="settings-modal-header">
          <h2 className="settings-modal-title">
            <SettingsIcon className="h-5 w-5" />
            Configuration
          </h2>
          <button
            onClick={onClose}
            className="settings-modal-close-btn"
            aria-label="Close settings"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="settings-modal-content">
          {/* Help Box */}
          <div className="settings-help-box">
            <div className="settings-help-box-content">
              <FolderOpen className="h-5 w-5 settings-help-box-icon" />
              <div className="settings-help-box-text">
                <p className="settings-help-box-title">Data Directory Configuration</p>
                <p className="settings-help-box-description">
                  The base data directory contains all stackbench validation runs. Each run is stored in a
                  subdirectory with a unique ID. When you run <code className="settings-help-box-code">stackbench run</code>,
                  results are automatically saved here.
                </p>
                <p className="settings-help-box-description" style={{ marginTop: '0.75rem', fontWeight: 600 }}>
                  ⚠️ Important: Use an <strong>absolute path</strong> (e.g., <code className="settings-help-box-code">/Users/username/project/data</code>).
                  Relative paths won't work.
                </p>
              </div>
            </div>
          </div>

          {/* Base Data Directory Input */}
          <div className="settings-section">
            <label className="settings-label">
              <FolderOpen className="settings-label-icon" />
              Base Data Directory
            </label>
            <input
              type="text"
              value={baseDataDir}
              onChange={(e) => setBaseDataDir(e.target.value)}
              className="settings-input"
              placeholder="/absolute/path/to/stackbench-v3/data"
            />
            <p className="settings-input-hint">
              Must be an absolute path to where stackbench stores validation run results.
              Example: <code className="settings-help-box-code">/Users/your-username/stackbench-v3/data</code>
            </p>
          </div>

          {/* Expected Structure */}
          <div className="settings-divider">
            <h3 className="settings-subsection-title">Expected Structure</h3>
            <pre className="settings-code-block">{`data/
└── {run-uuid}/
    ├── metadata.json
    ├── repository/
    └── results/
        ├── extraction/
        ├── api_validation/
        ├── code_validation/
        └── clarity_validation/`}</pre>
          </div>
        </div>

        {/* Footer */}
        <div className="settings-modal-footer">
          <button
            onClick={onClose}
            className="settings-btn settings-btn-cancel"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="settings-btn settings-btn-save"
          >
            Save & Reload
          </button>
        </div>
      </div>
    </div>
  );
}
