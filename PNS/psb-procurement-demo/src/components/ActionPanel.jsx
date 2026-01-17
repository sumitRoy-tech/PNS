import React from 'react';
import { CheckCircle, XCircle, ArrowRight, Sparkles } from 'lucide-react';

function ActionPanel({ currentStage, totalStages, isApproved, isRunning, onApproval, onNext }) {
  // Not started
  if (currentStage === 0) {
    return (
      <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
        <div className="text-center py-6">
          <Sparkles size={48} className="text-psb-gold mx-auto mb-3 opacity-50" />
          <p className="text-slate-400">Click "Auto Demo" to start the workflow</p>
          <p className="text-slate-500 text-sm mt-1">or step through manually</p>
        </div>
      </div>
    );
  }

  // Workflow complete
  if (currentStage >= totalStages) {
    return (
      <div className="bg-slate-800/50 backdrop-blur border border-psb-green/50 rounded-xl p-5">
        <div className="text-center py-4">
          <div className="w-16 h-16 bg-psb-green/20 rounded-full flex items-center justify-center mx-auto mb-3">
            <CheckCircle size={40} className="text-psb-green" />
          </div>
          <p className="text-psb-green font-semibold text-lg">Workflow Complete!</p>
          <p className="text-slate-400 text-sm mt-1">Contract signed successfully</p>
        </div>
      </div>
    );
  }

  // Rejected
  if (isApproved === false) {
    return (
      <div className="bg-slate-800/50 backdrop-blur border border-red-500/50 rounded-xl p-5">
        <div className="text-center py-4">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
            <XCircle size={40} className="text-red-500" />
          </div>
          <p className="text-red-400 font-semibold text-lg">Process Terminated</p>
          <p className="text-slate-400 text-sm mt-1">Requirement not approved</p>
          <p className="text-slate-500 text-xs mt-2">Click Reset to start over</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
      <h3 className="text-white font-medium mb-4 flex items-center gap-2">
        <span className="w-2 h-2 bg-psb-gold rounded-full animate-pulse" />
        Current Stage Actions
      </h3>

      {/* At approval gate */}
      {currentStage === 5 && isApproved === null ? (
        <div className="space-y-3">
          <p className="text-slate-400 text-sm mb-4">
            Approval Decision Required by Competent Authority:
          </p>
          <button
            onClick={() => onApproval(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 
                       bg-psb-green hover:bg-psb-green-light text-white rounded-lg 
                       transition-all duration-200 font-medium"
          >
            <CheckCircle size={20} /> 
            Approve Requirement
          </button>
          <button
            onClick={() => onApproval(false)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 
                       bg-red-600 hover:bg-red-700 text-white rounded-lg 
                       transition-all duration-200 font-medium"
          >
            <XCircle size={20} /> 
            Reject Requirement
          </button>
          <p className="text-slate-500 text-xs text-center mt-2">
            This is a critical decision gate
          </p>
        </div>
      ) : (
        /* Normal progression */
        <div className="space-y-3">
          <button
            onClick={onNext}
            disabled={isRunning}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 
                       bg-psb-gold hover:bg-psb-gold/90 disabled:bg-slate-600 
                       text-slate-900 disabled:text-slate-400 rounded-lg 
                       transition-all duration-200 font-medium disabled:cursor-not-allowed"
          >
            Proceed to Next Stage 
            <ArrowRight size={20} />
          </button>
          <p className="text-slate-500 text-xs text-center">
            {isRunning ? 'Auto-advancing...' : 'Manual progression mode'}
          </p>
        </div>
      )}
    </div>
  );
}

export default ActionPanel;
