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
    <header className="sticky top-0 z-40 w-full border-b border-[#162536] bg-[#060b11]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('interview')}>
          <div className="flex items-center justify-center w-10 h-10 rounded-lg border border-[#00e599]/40 bg-[#00e599]/10 text-[#00e599] shadow-[0_0_15px_rgba(0,229,153,0.15)]">
            <Shield className="w-5 h-5 text-[#00e599]" />
          </div>
          <div>
            <div className="text-[10px] font-mono tracking-[0.25em] text-slate-400 uppercase font-semibold leading-none">
              ISSB
            </div>
            <div className="text-sm font-bold tracking-tight text-white mt-1">
              Interview Simulator
            </div>
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

        {/* Right Status Badge from Lovable UI */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400 tracking-wider hidden sm:inline-block">
              CANDIDATE · CSAC
            </span>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#0a121d] border border-[#162536]">
              <span className={`w-1.5 h-1.5 rounded-full ${isLlmConnected ? 'bg-[#00e599]' : 'bg-amber-400'}`}></span>
              <span className={`text-[10px] uppercase font-bold tracking-wider ${isLlmConnected ? 'text-[#00e599]' : 'text-amber-400'}`}>
                {isLlmConnected ? 'LIVE INFERENCE' : 'OFFLINE DEMO'}
              </span>
            </div>
          </div>

          {showDevTools && (
            <div className="flex items-center space-x-2 border-l border-[#162536] pl-3">
              <button
                onClick={onOpenSettings}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                title="Configure LLM"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
