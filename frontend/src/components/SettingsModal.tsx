import React, { useState } from 'react';
import { X, Sparkles, Key, CheckCircle, AlertCircle, RefreshCw, Server } from 'lucide-react';
import { updateLLMSettings } from '../api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsChanged: () => void;
  showDevTools: boolean;
  onToggleDevTools: (enabled: boolean) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSettingsChanged,
  showDevTools,
  onToggleDevTools,
}) => {
  const [provider, setProvider] = useState('groq');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  if (!isOpen) return null;

  const handleTestAndSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTestResult(null);

    try {
      const res = await updateLLMSettings(
        provider,
        apiKey.trim() || undefined,
        modelName.trim() || undefined,
        baseUrl.trim() || undefined
      );

      setTestResult({
        success: res.success,
        message: res.message,
      });

      onSettingsChanged();
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Failed to connect to model endpoint.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-lg rounded-2xl border border-slate-700 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">LLM Provider Configuration</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleTestAndSave} className="p-6 space-y-4 text-xs sm:text-sm">
          {testResult && (
            <div
              className={`p-3.5 rounded-xl border flex items-start space-x-2.5 ${
                testResult.success
                  ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                  : 'bg-red-950/40 border-red-500/40 text-red-300'
              }`}
            >
              {testResult.success ? (
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              )}
              <span className="text-xs leading-relaxed">{testResult.message}</span>
            </div>
          )}

          {/* Provider Select */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Select Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="groq">Groq (Ultra-Fast Inference - Default)</option>
              <option value="gemini">Google Gemini</option>
              <option value="ollama">Local Ollama (Offline Qwen 2.5)</option>
              <option value="openai">OpenAI / DeepSeek / Custom Compatible</option>
              <option value="local">Local Rule & Heuristic Fallback</option>
            </select>
          </div>

          {/* API Key */}
          {provider !== 'ollama' && provider !== 'local' && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                API Key
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Key className="w-3.5 h-3.5" />
                </div>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => {
                    const val = e.target.value;
                    setApiKey(val);
                    if (val.trim().startsWith('gsk_')) {
                      setProvider('groq');
                    }
                  }}
                  placeholder="Paste your API key here..."
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                {provider === 'groq' && 'Free keys available at console.groq.com/keys'}
                {provider === 'gemini' && 'Free keys at aistudio.google.com/app/apikey'}
              </p>
            </div>
          )}

          {/* Ollama Endpoint */}
          {provider === 'ollama' && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Ollama Endpoint URL
              </label>
              <input
                type="text"
                value={baseUrl || 'http://localhost:11434/v1'}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs font-mono"
              />
            </div>
          )}

          {/* Optional Model Name */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Target Model (Optional)
            </label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder={provider === 'groq' ? 'llama-3.3-70b-versatile' : provider === 'gemini' ? 'gemini-2.5-flash' : 'Default'}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white text-xs font-mono"
            />
          </div>

          {/* Mode & Navigation Settings */}
          <div className="pt-3 border-t border-slate-800">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/70 border border-slate-800">
              <div className="pr-4">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold text-white">Candidate Practice Mode</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-medium">
                    Recommended
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Hides internal RAG knowledge and question bank tabs to give candidates a realistic, spoiler-free interview experience.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                <input
                  type="checkbox"
                  checked={!showDevTools}
                  onChange={(e) => onToggleDevTools(!e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600"></div>
              </label>
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="pt-3 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-950/40 flex items-center space-x-1.5 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <span>Test & Apply Configuration</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
