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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            Configuration
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-accent hover:text-accent-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-start gap-3">
              <FolderOpen className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-900">
                <p className="font-medium mb-1">Data Directory Configuration</p>
                <p className="text-xs text-blue-700">
                  The base data directory contains all stackbench validation runs. Each run is stored in a
                  subdirectory with a unique ID. When you run <code className="px-1 py-0.5 bg-blue-100 rounded">stackbench run</code>,
                  results are automatically saved here.
                </p>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Base Data Directory
            </label>
            <input
              type="text"
              value={baseDataDir}
              onChange={(e) => setBaseDataDir(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm font-mono"
              placeholder="/path/to/stackbench-v3/data"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Directory where stackbench stores validation run results
            </p>
          </div>

          <div className="pt-4 border-t border-border">
            <h3 className="text-sm font-semibold mb-2">Expected Structure</h3>
            <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
{`data/
└── {run-uuid}/
    ├── metadata.json
    ├── repository/
    └── results/
        ├── extraction/
        ├── api_validation/
        └── code_validation/`}
            </pre>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Save & Reload
          </button>
        </div>
      </div>
    </div>
  );
}
