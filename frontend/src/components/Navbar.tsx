import React from 'react';
import { Shield, Award, BookOpen, Database, Settings, Terminal, Radio } from 'lucide-react';
import { SystemStatus } from '../types';

interface NavbarProps {
  activeTab: 'interview' | 'report' | 'rag' | 'questions';
  setActiveTab: (tab: 'interview' | 'report' | 'rag' | 'questions') => void;
  status: SystemStatus | null;
  onOpenSettings: () => void;
  hasReport: boolean;
  showDevTools?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  status,
  onOpenSettings,
  hasReport,
  showDevTools = false,
}) => {
  const isOnline = status?.status === 'online';
  const isLlmConnected = status?.llm_status.badge === 'success';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-background/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 shadow-lg shadow-emerald-950/40 border border-emerald-400/30">
            <Shield className="w-5 h-5 text-white" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold tracking-tight text-white">MY_ISSB_Evaluator</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold tracking-wider uppercase">
                v2.0 Defensible
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">AI Interview Simulation & Psychometric Rubrics</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          <button
            onClick={() => setActiveTab('interview')}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'interview'
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Radio className="w-4 h-4" />
            <span>Interview</span>
          </button>

          <button
            onClick={() => setActiveTab('report')}
            className={`relative flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'report'
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Award className="w-4 h-4" />
            <span>Report</span>
            {hasReport && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            )}
          </button>

          {showDevTools && (
            <>
              <button
                onClick={() => setActiveTab('rag')}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  activeTab === 'rag'
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <BookOpen className="w-4 h-4" />
                <span className="hidden md:inline">RAG Knowledge</span>
                <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">DEV</span>
              </button>

              <button
                onClick={() => setActiveTab('questions')}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  activeTab === 'questions'
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Database className="w-4 h-4" />
                <span className="hidden md:inline">Questions</span>
                <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">DEV</span>
              </button>
            </>
          )}
        </nav>

        {/* Right Action & Status (Dev Only) */}
        {showDevTools && (
          <div className="flex items-center space-x-3">
            {/* LLM Status Pill */}
            <button
              onClick={onOpenSettings}
              className={`hidden lg:flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                isLlmConnected
                  ? 'bg-emerald-950/50 text-emerald-400 border-emerald-500/30 hover:border-emerald-500/50'
                  : 'bg-amber-950/50 text-amber-400 border-amber-500/30 hover:border-amber-500/50'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isLlmConnected ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
              <span>{isLlmConnected ? 'Frontier LLM Active' : 'Heuristic Engine'}</span>
            </button>

            {/* Settings Trigger */}
            <button
              onClick={onOpenSettings}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors border border-slate-700/50"
              title="Configure LLM & Providers"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
