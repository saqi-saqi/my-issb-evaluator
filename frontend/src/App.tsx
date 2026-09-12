import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { InterviewRoom } from './components/InterviewRoom';
import { EvaluationReport } from './components/EvaluationReport';
import { RagExplorer } from './components/RagExplorer';
import { QuestionBankExplorer } from './components/QuestionBankExplorer';
import { SettingsModal } from './components/SettingsModal';
import { EvaluationReportData, SystemStatus } from './types';
import { fetchReport, fetchStatus } from './api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'interview' | 'report' | 'rag' | 'questions'>('interview');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [report, setReport] = useState<EvaluationReportData | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showDevTools, setShowDevTools] = useState<boolean>(() => {
    return localStorage.getItem('issb_show_dev_tools') === 'true';
  });

  const handleToggleDevTools = (enabled: boolean) => {
    setShowDevTools(enabled);
    localStorage.setItem('issb_show_dev_tools', String(enabled));
    if (!enabled && (activeTab === 'rag' || activeTab === 'questions')) {
      setActiveTab('interview');
    }
  };

  const loadStatus = () => {
    fetchStatus()
      .then(setStatus)
      .catch((err) => console.error('Failed to load system status:', err));
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSessionComplete = async (sessionId: string) => {
    try {
      const data = await fetchReport(sessionId);
      setReport(data);
      setActiveTab('report');
    } catch (err) {
      console.error('Failed to load completed report:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
        onOpenSettings={() => setIsSettingsOpen(true)}
        hasReport={report !== null}
        showDevTools={showDevTools}
      />

      <main className="flex-1">
        {activeTab === 'interview' && (
          <InterviewRoom onSessionComplete={handleSessionComplete} />
        )}

        {activeTab === 'report' && (
          <EvaluationReport
            report={report}
            onRetake={() => setActiveTab('interview')}
          />
        )}

        {activeTab === 'rag' && <RagExplorer />}

        {activeTab === 'questions' && <QuestionBankExplorer />}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSettingsChanged={loadStatus}
        showDevTools={showDevTools}
        onToggleDevTools={handleToggleDevTools}
      />
    </div>
  );
};

export default App;
