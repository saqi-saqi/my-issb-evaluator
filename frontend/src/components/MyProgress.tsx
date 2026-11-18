import React, { useEffect, useState } from 'react';
import { fetchProgress, fetchReport } from '../api';

interface MyProgressProps {
  onOpenReport: (report: any) => void;
}

export const MyProgress: React.FC<MyProgressProps> = ({ onOpenReport }) => {
  const [progress, setProgress] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProgress().then(setProgress).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="max-w-4xl mx-auto p-6 text-red-300">{error}</div>;
  if (!progress) return <div className="max-w-4xl mx-auto p-6 text-slate-400">Complete an interview to start tracking progress.</div>;

  const latest = progress.latest;
  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <div>
        <p className="text-xs font-mono tracking-widest text-emerald-400 uppercase">Candidate progress</p>
        <h1 className="text-2xl font-bold text-white mt-2">My Progress</h1>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="military-card p-4 rounded-xl"><p className="text-xs text-slate-400">Sessions</p><p className="text-2xl text-white font-mono">{progress.total_sessions}</p></div>
        <div className="military-card p-4 rounded-xl"><p className="text-xs text-slate-400">Latest score</p><p className="text-2xl text-emerald-400 font-mono">{latest?.score ?? '—'}</p></div>
        <div className="military-card p-4 rounded-xl col-span-2"><p className="text-xs text-slate-400">Latest band</p><p className="text-white mt-1">{latest?.performance_band?.tier ?? 'Complete a session'}</p></div>
      </div>
      <div className="military-card p-5 rounded-xl">
        <h2 className="text-sm font-bold text-white mb-4">Score trend</h2>
        <div className="flex items-end gap-2 h-32">
          {progress.trend.map((item: any) => (
            <div key={item.session_id} className="flex-1 min-w-0 flex flex-col items-center gap-1">
              <span className="text-[10px] text-emerald-300">{Math.round(item.score)}</span>
              <div className="w-full bg-emerald-500/30 rounded-t" style={{ height: `${Math.max(8, item.score)}%` }} />
            </div>
          ))}
        </div>
      </div>
      <div className="military-card rounded-xl overflow-hidden">
        <h2 className="p-5 text-sm font-bold text-white">Sessions</h2>
        {progress.sessions.map((session: any) => (
          <button key={session.session_id} className="w-full flex items-center justify-between gap-3 p-4 border-t border-[#162536] text-left hover:bg-slate-800/40" onClick={() => fetchReport(session.session_id).then(onOpenReport)}>
            <span><span className="block text-white text-sm">{session.candidate_name}</span><span className="text-xs text-slate-500">{new Date(session.date).toLocaleDateString()}</span></span>
            <span className="text-emerald-400 font-mono">{Math.round(session.score)}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
