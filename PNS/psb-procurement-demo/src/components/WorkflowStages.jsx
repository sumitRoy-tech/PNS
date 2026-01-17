import React, { useState } from 'react';
import { 
  FileText, Settings, Users, ClipboardCheck, CheckCircle, 
  Send, Inbox, UserCheck, ShoppingCart, FileSignature,
  ChevronDown, ChevronUp, AlertCircle
} from 'lucide-react';

// Icon mapping
const iconMap = {
  FileText, Settings, Users, ClipboardCheck, CheckCircle,
  Send, Inbox, UserCheck, ShoppingCart, FileSignature
};

function WorkflowStages({ stages, currentStage, isApproved }) {
  const [expandedStage, setExpandedStage] = useState(null);

  const getStageStatus = (stageId) => {
    if (stageId < currentStage) return 'completed';
    if (stageId === currentStage) return 'current';
    if (stageId === 5 && isApproved === false) return 'rejected';
    return 'pending';
  };

  const getStatusStyles = (status) => {
    switch (status) {
      case 'completed':
        return {
          container: 'bg-psb-green/10 border-psb-green/50',
          badge: 'bg-psb-green',
          text: 'text-psb-green',
          icon: 'bg-psb-green/20 text-psb-green'
        };
      case 'current':
        return {
          container: 'bg-psb-gold/10 border-psb-gold shadow-lg shadow-psb-gold/20',
          badge: 'bg-psb-gold',
          text: 'text-psb-gold',
          icon: 'bg-psb-gold/20 text-psb-gold'
        };
      case 'rejected':
        return {
          container: 'bg-red-900/20 border-red-500/50',
          badge: 'bg-red-500',
          text: 'text-red-400',
          icon: 'bg-red-500/20 text-red-400'
        };
      default:
        return {
          container: 'bg-slate-700/30 border-slate-600/50',
          badge: 'bg-slate-600',
          text: 'text-slate-400',
          icon: 'bg-slate-600/20 text-slate-400'
        };
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold text-white mb-5 flex items-center gap-2">
        <ClipboardCheck size={20} className="text-psb-gold" />
        RFP / Tendering Workflow
      </h2>

      <div className="space-y-3">
        {stages.map((stage, index) => {
          const status = getStageStatus(stage.id);
          const styles = getStatusStyles(status);
          const Icon = iconMap[stage.icon] || FileText;
          const isExpanded = expandedStage === stage.id;

          return (
            <div key={stage.id}>
              {/* Stage Card */}
              <div
                onClick={() => setExpandedStage(isExpanded ? null : stage.id)}
                className={`relative flex items-center gap-4 p-4 rounded-lg cursor-pointer 
                           transition-all duration-300 border ${styles.container}
                           hover:border-opacity-100`}
              >
                {/* Stage Number Badge */}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center 
                                font-bold text-sm text-white ${styles.badge}
                                ${status === 'current' ? 'animate-pulse' : ''}`}>
                  {status === 'completed' ? (
                    <CheckCircle size={20} />
                  ) : status === 'rejected' ? (
                    <AlertCircle size={20} />
                  ) : (
                    stage.id
                  )}
                </div>

                {/* Icon */}
                <div className={`p-2 rounded-lg ${styles.icon}`}>
                  <Icon size={20} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className={`font-medium ${styles.text}`}>
                      {stage.name}
                    </h3>
                    {stage.isGate && (
                      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded font-medium">
                        Approval Gate
                      </span>
                    )}
                  </div>
                  <p className="text-slate-500 text-sm truncate">{stage.dept}</p>
                </div>

                {/* Status Badge */}
                <div className={`px-3 py-1 rounded-full text-xs font-medium 
                                ${styles.icon} hidden sm:block`}>
                  {status === 'completed' ? 'Completed' :
                   status === 'current' ? 'In Progress' :
                   status === 'rejected' ? 'Rejected' : 'Pending'}
                </div>

                {/* Expand Icon */}
                <div className="text-slate-400">
                  {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="ml-14 mt-2 p-4 bg-slate-700/30 rounded-lg border border-slate-600/50 
                               animate-in slide-in-from-top-2 duration-200">
                  <p className="text-slate-300 text-sm mb-3">{stage.description}</p>
                  
                  {/* Stage Outputs */}
                  {stage.outputs && (
                    <div className="mt-3">
                      <p className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                        Stage Outputs:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {stage.outputs.map((output, idx) => (
                          <span key={idx} className="px-2 py-1 bg-slate-600/50 text-slate-300 
                                                     text-xs rounded">
                            {output}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Special note for approval gate */}
                  {stage.isGate && (
                    <div className="mt-3 p-3 bg-blue-900/20 rounded border border-blue-700/50">
                      <p className="text-blue-300 text-sm">
                        <strong>Note:</strong> This is a critical approval gate. 
                        If rejected, the entire procurement process terminates.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Connector Line */}
              {index < stages.length - 1 && (
                <div className="ml-9 h-3 border-l-2 border-dashed border-slate-600" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default WorkflowStages;
