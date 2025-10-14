import { useState } from 'react';
import { Settings as SettingsIcon, X } from 'lucide-react';
import { apiService } from '../services/api';

interface SettingsProps {
  onClose: () => void;
}

export function Settings({ onClose }: SettingsProps) {
  const config = apiService.getConfig();
  const [repoPath, setRepoPath] = useState(config.repoPath);
  const [docsPath, setDocsPath] = useState(config.docsPath);
  const [extractionOutputPath, setExtractionOutputPath] = useState(config.extractionOutputPath);
  const [validationOutputPath, setValidationOutputPath] = useState(config.validationOutputPath);

  const handleSave = () => {
    apiService.updateConfig({
      repoPath,
      docsPath,
      extractionOutputPath,
      validationOutputPath,
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
          <div>
            <label className="block text-sm font-medium mb-2">
              Repository Path
            </label>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
              placeholder="/path/to/stackbench-v2"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Root path of the StackBench repository
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Documentation Path
            </label>
            <input
              type="text"
              value={docsPath}
              onChange={(e) => setDocsPath(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
              placeholder="/path/to/docs/src/python"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Path to the documentation markdown files
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Extraction Output Path
            </label>
            <input
              type="text"
              value={extractionOutputPath}
              onChange={(e) => setExtractionOutputPath(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
              placeholder="/path/to/extraction_output"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Path to the extraction output JSON files
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Validation Output Path
            </label>
            <input
              type="text"
              value={validationOutputPath}
              onChange={(e) => setValidationOutputPath(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
              placeholder="/path/to/ast_validation_output"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Path to the AST validation output JSON files
            </p>
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
