import React from 'react';
import { RotateCcw, Home } from 'lucide-react';

const PSBLogo = () => (
  <svg width="48" height="48" viewBox="0 0 100 100" className="rounded-lg">
    <rect width="100" height="100" fill="#167947" rx="12"/>
    <rect x="0" y="75" width="100" height="25" fill="#CFA550"/>
    <text x="50" y="55" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold" fontFamily="Arial">PSB</text>
    <circle cx="20" cy="25" r="3" fill="#CFA550"/>
    <circle cx="50" cy="20" r="3" fill="#CFA550"/>
    <circle cx="80" cy="25" r="3" fill="#CFA550"/>
  </svg>
);

function Header({ onReset, currentStage, viewMode }) {
  return (
    <div className="max-w-7xl mx-auto mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <PSBLogo />
          <div>
            <h1 className="text-2xl font-bold text-white">Punjab & Sind Bank</h1>
            <p className="text-slate-400 text-sm">Procurement Workflow Automation System</p>
          </div>
        </div>
        {viewMode === 'workflow' && (
          <button
            onClick={onReset}
            className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all duration-200 font-medium"
          >
            <Home size={18} />
            <span>Dashboard</span>
          </button>
        )}
      </div>
      <div className="mt-6 h-px bg-gradient-to-r from-transparent via-psb-gold/30 to-transparent" />
    </div>
  );
}

export default Header;
