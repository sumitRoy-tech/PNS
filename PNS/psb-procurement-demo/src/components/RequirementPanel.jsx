import React from 'react';
import { FileText, Tag, Building2, IndianRupee, AlertTriangle, User, Calendar } from 'lucide-react';

function RequirementPanel({ requirement, currentStage, totalStages }) {
  const progress = Math.round((currentStage / totalStages) * 100);

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
      {/* Header */}
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <FileText size={20} className="text-psb-gold" />
        Current Requirement
      </h2>

      {/* Requirement Details */}
      <div className="space-y-4">
        {/* Request ID */}
        <div className="flex items-start gap-3">
          <Tag size={16} className="text-slate-400 mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Request ID</p>
            <p className="text-white font-mono text-sm">{requirement.reqId}</p>
          </div>
        </div>

        {/* Title */}
        <div>
          <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Title</p>
          <p className="text-white font-medium">{requirement.title}</p>
        </div>

        {/* Department */}
        <div className="flex items-start gap-3">
          <Building2 size={16} className="text-slate-400 mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Department</p>
            <p className="text-white text-sm">{requirement.department}</p>
          </div>
        </div>

        {/* Estimated Value */}
        <div className="flex items-start gap-3">
          <IndianRupee size={16} className="text-psb-green mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Estimated Value</p>
            <p className="text-psb-green font-semibold">{requirement.estimatedValue}</p>
          </div>
        </div>

        {/* Priority */}
        <div className="flex items-start gap-3">
          <AlertTriangle size={16} className="text-red-400 mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Priority</p>
            <span className="inline-block px-2 py-1 bg-red-500/20 text-red-400 rounded text-sm font-medium">
              {requirement.priority}
            </span>
          </div>
        </div>

        {/* Submitted By */}
        <div className="flex items-start gap-3">
          <User size={16} className="text-slate-400 mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Submitted By</p>
            <p className="text-white text-sm">{requirement.submittedBy}</p>
          </div>
        </div>

        {/* Date */}
        <div className="flex items-start gap-3">
          <Calendar size={16} className="text-slate-400 mt-1" />
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Date</p>
            <p className="text-white text-sm">{requirement.submittedDate}</p>
          </div>
        </div>
      </div>

      {/* Progress Indicator */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="flex justify-between items-center mb-2">
          <span className="text-slate-400 text-sm">Workflow Progress</span>
          <span className="text-white font-medium">{progress}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2.5 overflow-hidden">
          <div 
            className="h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ 
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #167947 0%, #CFA550 100%)'
            }}
          />
        </div>
        <p className="text-slate-500 text-xs mt-2">
          Stage {currentStage} of {totalStages}
        </p>
      </div>
    </div>
  );
}

export default RequirementPanel;
