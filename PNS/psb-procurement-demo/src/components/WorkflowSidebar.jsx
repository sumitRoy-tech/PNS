import React, { useState, useEffect } from 'react';
import { 
  FileText, Settings, Users, ClipboardCheck, CheckCircle, 
  Send, Inbox, UserCheck, ShoppingCart, FileSignature, AlertCircle, Loader2
} from 'lucide-react';

const iconMap = {
  FileText, Settings, Users, ClipboardCheck, CheckCircle,
  Send, Inbox, UserCheck, ShoppingCart, FileSignature
};

function WorkflowSidebar({ stages, currentStage, isApproved, requirement }) {
  // State for API-fetched project data
  const [projectData, setProjectData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Get project ID from requirement
  const projectId = requirement?.projectId || requirement?.reqId || requirement?.project_id;

  // Fetch project data from API when projectId changes
  useEffect(() => {
    const fetchProjectData = async () => {
      if (!projectId) return;

      try {
        setLoading(true);
        console.log('WorkflowSidebar: Fetching project data for:', projectId);
        
        const response = await fetch(`http://localhost:8003/functional/projects/${projectId}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('WorkflowSidebar: Project data fetched:', data);
          setProjectData(data);
        } else {
          console.error('WorkflowSidebar: Failed to fetch project data');
        }
      } catch (error) {
        console.error('WorkflowSidebar: Error fetching project data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProjectData();
  }, [projectId]);

  // Format currency
  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    // If amount is in crores (small number like 5.0), multiply by 10000000
    const actualAmount = amount < 1000 ? amount * 10000000 : amount;
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', 
      currency: 'INR', 
      maximumFractionDigits: 0 
    }).format(actualAmount);
  };

  // Get display values - prefer API data over requirement prop
  const displayTitle = projectData?.project?.title || requirement?.title || 'No Title';
  const displayAmount = projectData?.project?.estimated_amount || requirement?.estimatedAmountRupees;
  const displayDepartment = projectData?.project?.department || requirement?.department;
  const displayPriority = projectData?.project?.priority || requirement?.priority;

  const getStageStatus = (stageId) => {
    if (currentStage === 0) return 'pending';
    // Fix: For stage 9 (Contract Signing), mark as current when currentStage is 9
    if (stageId < currentStage) return 'completed';
    if (stageId === currentStage) return 'current';
    // Special case: if currentStage is 9 and stageId is 10, mark stage 10 as current
    if (currentStage === 9 && stageId === 10) return 'pending';
    if (stageId === 5 && isApproved === false) return 'rejected';
    return 'pending';
  };

  // Fix progress calculation - currentStage 9 means we're on stage 10 (index 9)
  // Progress should show completion based on stages completed
  const progress = currentStage === 0 ? 0 : Math.round((currentStage / stages.length) * 100);

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
      <h3 className="text-white font-semibold mb-4">Workflow Progress</h3>
      
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-slate-400">Progress</span>
          <span className="text-white">{progress}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div 
            className="h-2 rounded-full transition-all duration-500"
            style={{ 
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #167947 0%, #CFA550 100%)'
            }}
          />
        </div>
      </div>

      {/* Requirement Summary - Now uses API data */}
      {(projectId || requirement) && (
        <div className="mb-4 p-3 bg-slate-700/50 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center py-2">
              <Loader2 size={16} className="text-psb-gold animate-spin" />
              <span className="text-slate-400 text-xs ml-2">Loading...</span>
            </div>
          ) : (
            <>
              <p className="text-slate-400 text-xs uppercase mb-1">Current Request</p>
              <p className="text-white text-sm font-medium truncate" title={displayTitle}>
                {displayTitle}
              </p>
              <p className="text-psb-gold text-sm font-semibold">
                {displayAmount ? formatCurrency(displayAmount) : requirement?.estimatedValue || 'N/A'}
              </p>
              {displayDepartment && (
                <p className="text-slate-400 text-xs mt-1 truncate">{displayDepartment}</p>
              )}
              {displayPriority && (
                <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${
                  displayPriority === 'critical' ? 'bg-red-500/20 text-red-400' :
                  displayPriority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                  displayPriority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                  {displayPriority.charAt(0).toUpperCase() + displayPriority.slice(1)} Priority
                </span>
              )}
              {projectId && (
                <p className="text-slate-500 text-xs mt-2 font-mono truncate" title={projectId}>
                  {projectId}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* Stages List */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {stages.map((stage) => {
          const status = getStageStatus(stage.id);
          const Icon = iconMap[stage.icon] || FileText;
          
          return (
            <div 
              key={stage.id}
              className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                status === 'completed' ? 'bg-psb-green/10' :
                status === 'current' ? 'bg-psb-gold/10 border border-psb-gold/50' :
                status === 'rejected' ? 'bg-red-900/20' :
                'bg-transparent'
              }`}
            >
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                status === 'completed' ? 'bg-psb-green text-white' :
                status === 'current' ? 'bg-psb-gold text-slate-900' :
                status === 'rejected' ? 'bg-red-500 text-white' :
                'bg-slate-600 text-slate-300'
              }`}>
                {status === 'completed' ? <CheckCircle size={14} /> :
                 status === 'rejected' ? <AlertCircle size={14} /> :
                 stage.id}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium truncate ${
                  status === 'completed' ? 'text-psb-green' :
                  status === 'current' ? 'text-psb-gold' :
                  status === 'rejected' ? 'text-red-400' :
                  'text-slate-400'
                }`}>
                  {stage.name}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current Stage Info */}
      {currentStage > 0 && currentStage <= stages.length && (
        <div className="mt-4 pt-3 border-t border-slate-700">
          <p className="text-slate-400 text-xs">Currently on</p>
          <p className="text-psb-gold text-sm font-medium">
            Stage {currentStage}: {stages[currentStage - 1]?.name || 'Unknown'}
          </p>
        </div>
      )}
    </div>
  );
}

export default WorkflowSidebar;
