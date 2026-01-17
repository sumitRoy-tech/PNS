import React, { useState, useEffect } from 'react';
import { 
  Plus, FileText, Clock, CheckCircle, XCircle, Send, 
  TrendingUp, AlertTriangle, Calendar, ArrowRight, Eye,
  Activity, Target, BarChart3, Loader2, X, RefreshCw
} from 'lucide-react';

// Custom scrollbar styles
const scrollbarStyles = `
  .custom-scrollbar {
    scrollbar-width: thin;
    scrollbar-color: rgba(100, 116, 139, 0.5) transparent;
  }
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
    border-radius: 3px;
    margin: 4px 0;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(100, 116, 139, 0.5);
    border-radius: 3px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(100, 116, 139, 0.8);
  }
`;

function Dashboard({ onNewRequirement, onViewRequirement, onViewProjectById, requirements }) {

  const [progressData, setProgressData] = useState([]);
  const [progressSummary, setProgressSummary] = useState(null);
  const [rejectedData, setRejectedData] = useState({ total_rejected: 0, projects: [] });
  const [navigationData, setNavigationData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal states
  const [showAllRequests, setShowAllRequests] = useState(false);
  const [showCompletedRFPs, setShowCompletedRFPs] = useState(false);

  // Fetch all data on component mount
  useEffect(() => {
    fetchAllData();
  }, []);

  // Fetch all dashboard data
  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchProgressData(),
      fetchProgressSummary(),
      fetchRejectedProjects(),
      fetchNavigationData()
    ]);
    setLoading(false);
  };

  const fetchProgressData = async () => {
    try {
      const response = await fetch('http://localhost:8003/requirements/progress/list/all');
      if (response.ok) {
        const data = await response.json();
        setProgressData(data.projects || []);
      }
    } catch (error) {
      console.error('Error fetching progress data:', error);
    }
  };

  const fetchProgressSummary = async () => {
    try {
      const response = await fetch('http://localhost:8003/requirements/progress/summary');
      if (response.ok) {
        const data = await response.json();
        setProgressSummary(data);
      }
    } catch (error) {
      console.error('Error fetching progress summary:', error);
    }
  };

  const fetchRejectedProjects = async () => {
    try {
      const response = await fetch('http://localhost:8003/requirements/rejected/list');
      if (response.ok) {
        const data = await response.json();
        setRejectedData(data);
        console.log('Rejected projects:', data);
      }
    } catch (error) {
      console.error('Error fetching rejected projects:', error);
    }
  };

  const fetchNavigationData = async () => {
    try {
      const response = await fetch('http://localhost:8003/requirements/navigation/list/all');
      if (response.ok) {
        const data = await response.json();
        setNavigationData(data.projects || []);
        console.log('Navigation data:', data);
      }
    } catch (error) {
      console.error('Error fetching navigation data:', error);
    }
  };

  // Get navigation info for a specific project
  const getProjectNavigation = (projectId) => {
    return navigationData.find(nav => nav.project_id === projectId);
  };

  // Check if a project is rejected
  const isProjectRejected = (projectId) => {
    return rejectedData.projects.some(r => r.project_id === projectId);
  };
  
  // Calculate stats from DATABASE data (not local state)
  const totalProjects = progressSummary?.total_projects || progressData.length || 0;
  const totalRejected = rejectedData.total_rejected || 0;
  const totalCompleted = progressData.filter(p => p.overall_progress === 100).length;
  const totalInProgress = progressData.filter(p => p.overall_progress > 0 && p.overall_progress < 100).length;
  
  const stats = {
    total: totalProjects,
    pending: progressData.filter(p => p.current_page <= 5 && p.overall_progress < 100).length,
    approved: progressData.filter(p => p.current_page > 5).length,
    rejected: totalRejected,
    inProgress: totalInProgress,
    completed: totalCompleted,
  };

  const getStatusBadge = (req) => {
    if (req.status === 'Rejected') {
      return <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">Rejected</span>;
    }
    if (req.stage === 10) {
      return <span className="px-2 py-1 bg-psb-green/20 text-psb-green rounded text-xs">Completed</span>;
    }
    if (req.stage === 5) {
      return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs">Awaiting Approval</span>;
    }
    if (req.stage > 0) {
      return <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">In Progress</span>;
    }
    return <span className="px-2 py-1 bg-slate-500/20 text-slate-400 rounded text-xs">Draft</span>;
  };

  const getStageName = (stage) => {
    const stages = [
      'Draft', 'Submitted', 'Analysis', 'Tech Review', 'RFP Draft', 
      'Approval', 'Published', 'Bidding', 'Evaluation', 'PO Issued', 'Completed'
    ];
    return stages[stage] || 'Unknown';
  };

  const getProgressColor = (progress) => {
    if (progress >= 80) return 'bg-psb-green';
    if (progress >= 50) return 'bg-blue-500';
    if (progress >= 25) return 'bg-yellow-500';
    return 'bg-slate-500';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-psb-green';
      case 'in_progress': return 'text-blue-400';
      case 'on_hold': return 'text-yellow-400';
      case 'not_started': return 'text-slate-400';
      default: return 'text-slate-400';
    }
  };

  // Progress Step Indicator Component
  const ProgressSteps = ({ currentPage, overallProgress }) => {
    const steps = [
      { num: 1, label: 'Req' },
      { num: 2, label: 'Func' },
      { num: 3, label: 'Tech' },
      { num: 4, label: 'RFP' },
      { num: 5, label: 'Tender' },
      { num: 6, label: 'Approve' },
      { num: 7, label: 'Publish' },
      { num: 8, label: 'Bid' },
      { num: 9, label: 'Eval' },
      { num: 10, label: 'PO' }
    ];

    return (
      <div className="flex items-center gap-1">
        {steps.map((step, idx) => (
          <div
            key={step.num}
            className={`w-2 h-2 rounded-full ${
              step.num < currentPage 
                ? 'bg-psb-green' 
                : step.num === currentPage 
                  ? 'bg-blue-500 animate-pulse' 
                  : 'bg-slate-600'
            }`}
            title={`${step.label}: ${step.num < currentPage ? 'Completed' : step.num === currentPage ? 'Current' : 'Pending'}`}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Custom scrollbar styles */}
      <style>{scrollbarStyles}</style>
      
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-psb-green/20 to-psb-gold/20 border border-psb-green/30 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Procurement Dashboard</h2>
            <p className="text-slate-400">Manage and track all procurement requirements</p>
          </div>
          <button
            onClick={onNewRequirement}
            className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light text-white rounded-lg transition-all duration-200 font-medium shadow-lg shadow-psb-green/20"
          >
            <Plus size={20} />
            New Requirement
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <FileText size={20} className="text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-slate-400 text-sm">Total Requests</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Clock size={20} className="text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.inProgress}</p>
              <p className="text-slate-400 text-sm">In Progress</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-psb-green/20 rounded-lg">
              <CheckCircle size={20} className="text-psb-green" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.completed}</p>
              <p className="text-slate-400 text-sm">Completed</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <XCircle size={20} className="text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.rejected}</p>
              <p className="text-slate-400 text-sm">Rejected</p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Overview Section */}
      {progressSummary && (
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 size={20} className="text-psb-gold" />
            Progress Overview
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-slate-700/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-white">{progressSummary.total_projects}</p>
              <p className="text-slate-400 text-xs">Total Projects</p>
            </div>
            <div className="bg-slate-700/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-psb-green">{progressSummary.status_counts?.completed || 0}</p>
              <p className="text-slate-400 text-xs">Completed</p>
            </div>
            <div className="bg-slate-700/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-blue-400">{progressSummary.status_counts?.in_progress || 0}</p>
              <p className="text-slate-400 text-xs">In Progress</p>
            </div>
            <div className="bg-slate-700/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-yellow-400">{progressSummary.status_counts?.on_hold || 0}</p>
              <p className="text-slate-400 text-xs">On Hold</p>
            </div>
            <div className="bg-slate-700/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-cyan-400">{progressSummary.average_progress || 0}%</p>
              <p className="text-slate-400 text-xs">Avg Progress</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid - Changed to full width for progress */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* Project Progress List - Now takes 3 columns */}
        <div className="lg:col-span-3 bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5 h-fit">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity size={20} className="text-psb-gold" />
              Project Progress
              <span className="text-slate-400 text-sm font-normal ml-2">
                ({progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length} in progress)
              </span>
            </h3>
            <button 
              onClick={fetchAllData}
              className="text-slate-400 hover:text-white text-sm flex items-center gap-1.5 hover:bg-slate-700/50 px-2 py-1 rounded transition-colors"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={32} className="text-psb-green animate-spin" />
            </div>
          ) : progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length === 0 ? (
            <div className="text-center py-12">
              <Target size={48} className="text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400">No projects in progress</p>
              <p className="text-slate-500 text-sm">Create a new requirement to start tracking</p>
            </div>
          ) : (
            <div 
              className="custom-scrollbar space-y-3 overflow-y-auto -mr-2 pr-2"
              style={{ maxHeight: progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length > 4 ? '520px' : 'none' }}
            >
              {progressData
                .filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100)
                .map((project, index) => {
                const navInfo = getProjectNavigation(project.project_id);
                
                return (
                <div 
                  key={index}
                  onClick={() => onViewProjectById && onViewProjectById(project.project_id, project.current_page, project)}
                  className="p-4 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 hover:border-psb-green/50 border border-transparent transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium truncate group-hover:text-psb-green transition-colors">{project.project_title}</p>
                      <p className="text-slate-500 text-xs">{project.project_id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${getStatusColor(project.status)}`}>
                        {project.status?.replace('_', ' ').toUpperCase()}
                      </span>
                      <ArrowRight size={16} className="text-slate-500 group-hover:text-psb-green group-hover:translate-x-1 transition-all" />
                    </div>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="mb-2">
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>
                        {navInfo ? (
                          <>Next: <span className="text-psb-gold">{navInfo.current_page_component}</span></>
                        ) : (
                          <>Stage: {project.current_page_name}</>
                        )}
                      </span>
                      <span>{project.overall_progress}%</span>
                    </div>
                    <div className="w-full bg-slate-600 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full transition-all duration-500 ${getProgressColor(project.overall_progress)}`}
                        style={{ width: `${project.overall_progress}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* Step Indicators */}
                  <div className="flex items-center justify-between">
                    <ProgressSteps 
                      currentPage={navInfo?.current_stage + 1 || project.current_page} 
                      overallProgress={project.overall_progress} 
                    />
                    <span className="text-slate-500 text-xs group-hover:text-slate-400">
                      Click to continue → {navInfo ? `Stage ${navInfo.current_stage}` : `Page ${project.current_page}`}/10
                    </span>
                  </div>
                </div>
              )})}
            </div>
          )}
        </div>

        {/* Right Sidebar - Now takes 1 column */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* Quick Actions */}
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-psb-gold" />
              Quick Actions
            </h3>
            <div className="space-y-2">
              <button
                onClick={onNewRequirement}
                className="w-full flex items-center gap-3 p-3 bg-psb-green/10 border border-psb-green/30 rounded-lg hover:bg-psb-green/20 transition-colors text-left"
              >
                <Plus size={18} className="text-psb-green" />
                <span className="text-white">New Requirement</span>
              </button>
              <button 
                onClick={() => setShowAllRequests(true)}
                className="w-full flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors text-left"
              >
                <Eye size={18} className="text-blue-400" />
                <span className="text-white">View All Requests</span>
                <span className="ml-auto text-slate-400 text-xs">{progressData.length}</span>
              </button>
              <button 
                onClick={() => setShowCompletedRFPs(true)}
                className="w-full flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors text-left"
              >
                <Send size={18} className="text-cyan-400" />
                <span className="text-white">Published RFPs</span>
                <span className="ml-auto text-psb-green text-xs">{progressData.filter(p => p.overall_progress === 100).length}</span>
              </button>
            </div>
          </div>

          {/* Stage Distribution */}
          {progressSummary?.projects_by_stage && (
            <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Target size={20} className="text-psb-gold" />
                By Stage
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {Object.entries(progressSummary.projects_by_stage).map(([stage, count], idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-slate-700/20 rounded">
                    <span className="text-slate-300 text-sm truncate">{stage}</span>
                    <span className="text-white font-medium ml-2">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rejected Projects */}
          {rejectedData.total_rejected > 0 && (
            <div className="bg-slate-800/50 backdrop-blur border border-red-500/30 rounded-xl p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <XCircle size={20} className="text-red-400" />
                Rejected Projects ({rejectedData.total_rejected})
              </h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {rejectedData.projects.slice(0, 5).map((project, idx) => (
                  <div key={idx} className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-white text-sm font-mono truncate">{project.project_id}</p>
                    <p className="text-red-400 text-xs">
                      Rejected: {new Date(project.rejected_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                {rejectedData.total_rejected > 5 && (
                  <p className="text-slate-500 text-xs text-center pt-2">
                    +{rejectedData.total_rejected - 5} more rejected
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Pending Approvals */}
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle size={20} className="text-yellow-400" />
              Pending Actions
            </h3>
            {stats.pending > 0 ? (
              <div className="space-y-3">
                {requirements.filter(r => r.stage === 5 && r.status !== 'Rejected').slice(0, 3).map((req, index) => (
                  <div key={index} className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                    <p className="text-white text-sm font-medium truncate">{req.title}</p>
                    <p className="text-yellow-400 text-xs">Awaiting Approval</p>
                  </div>
                ))}
                {stats.pending === 0 && (
                  <p className="text-slate-400 text-sm text-center py-4">No pending approvals</p>
                )}
              </div>
            ) : (
              <p className="text-slate-400 text-sm text-center py-4">No pending actions</p>
            )}
          </div>

          {/* Calendar / Timeline */}
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Calendar size={20} className="text-psb-gold" />
              Upcoming Deadlines
            </h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-2">
                <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                <div>
                  <p className="text-white text-sm">RFP Submission Deadline</p>
                  <p className="text-slate-500 text-xs">15 Jan 2025</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-2">
                <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                <div>
                  <p className="text-white text-sm">Bid Opening</p>
                  <p className="text-slate-500 text-xs">20 Jan 2025</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-2">
                <div className="w-2 h-2 bg-psb-green rounded-full"></div>
                <div>
                  <p className="text-white text-sm">Contract Renewal</p>
                  <p className="text-slate-500 text-xs">31 Jan 2025</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Recent Requirements Section */}
      <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText size={20} className="text-psb-gold" />
            Recent Requirements
          </h3>
        </div>

        {requirements.length === 0 ? (
          <div className="text-center py-12">
            <FileText size={48} className="text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No requirements yet</p>
            <p className="text-slate-500 text-sm">Click "New Requirement" to create your first one</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {requirements.slice(0, 6).map((req, index) => (
              <div 
                key={index}
                className="p-4 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer"
                onClick={() => onViewRequirement(index)}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-white font-medium truncate flex-1">{req.title}</p>
                  {getStatusBadge(req)}
                </div>
                <div className="space-y-1 text-sm">
                  <p className="text-slate-400">{req.reqId}</p>
                  <div className="flex justify-between">
                    <span className="text-slate-500">{req.department}</span>
                    <span className="text-psb-green">{req.estimatedValue}</span>
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-slate-400 text-xs">Stage: {getStageName(req.stage)}</span>
                    <ArrowRight size={16} className="text-slate-500" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ==================== MODALS ==================== */}
      
      {/* View All Requests Modal - Shows ALL projects (in-progress, completed, rejected) */}
      {showAllRequests && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Eye size={24} className="text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">All Procurement Requests</h2>
                  <p className="text-slate-400 text-sm">
                    {progressData.length + rejectedData.total_rejected} total projects 
                    <span className="mx-2">•</span>
                    <span className="text-blue-400">{progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length} In Progress</span>
                    <span className="mx-2">•</span>
                    <span className="text-psb-green">{progressData.filter(p => p.overall_progress === 100).length} Completed</span>
                    <span className="mx-2">•</span>
                    <span className="text-red-400">{rejectedData.total_rejected} Rejected</span>
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowAllRequests(false)}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X size={24} className="text-slate-400 hover:text-white" />
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-5 overflow-y-auto max-h-[calc(90vh-80px)]">
              {progressData.length === 0 && rejectedData.projects.length === 0 ? (
                <div className="text-center py-12">
                  <Target size={48} className="text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No projects found</p>
                </div>
              ) : (
                <div className="space-y-6">
                  
                  {/* In-Progress Projects Section */}
                  {progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length > 0 && (
                    <div>
                      <h3 className="text-lg font-medium text-blue-400 mb-3 flex items-center gap-2">
                        <Clock size={18} />
                        In Progress ({progressData.filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100).length})
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {progressData
                          .filter(p => !isProjectRejected(p.project_id) && p.overall_progress < 100)
                          .map((project, index) => {
                            const navInfo = getProjectNavigation(project.project_id);
                            
                            return (
                              <div 
                                key={index}
                                onClick={() => {
                                  setShowAllRequests(false);
                                  onViewProjectById && onViewProjectById(project.project_id, project.current_page, project);
                                }}
                                className="p-4 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 hover:border-blue-500/50 border border-transparent transition-all cursor-pointer group"
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex-1 min-w-0">
                                    <p className="text-white font-medium truncate group-hover:text-blue-400 transition-colors">
                                      {project.project_title}
                                    </p>
                                    <p className="text-slate-500 text-xs font-mono">{project.project_id}</p>
                                  </div>
                                  <ArrowRight size={16} className="text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
                                </div>
                                
                                {/* Progress Bar */}
                                <div className="mb-3">
                                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                                    <span>
                                      {navInfo ? (
                                        <>Stage: <span className="text-psb-gold">{navInfo.current_page_component}</span></>
                                      ) : (
                                        <>Stage: {project.current_page_name}</>
                                      )}
                                    </span>
                                    <span className="font-medium">{project.overall_progress}%</span>
                                  </div>
                                  <div className="w-full bg-slate-600 rounded-full h-2">
                                    <div 
                                      className={`h-2 rounded-full transition-all duration-500 ${getProgressColor(project.overall_progress)}`}
                                      style={{ width: `${project.overall_progress}%` }}
                                    />
                                  </div>
                                </div>
                                
                                {/* Step Indicators */}
                                <div className="flex items-center justify-between">
                                  <ProgressSteps 
                                    currentPage={navInfo?.current_stage + 1 || project.current_page} 
                                    overallProgress={project.overall_progress} 
                                  />
                                  <span className="text-xs font-medium px-2 py-0.5 rounded text-blue-400 bg-blue-500/20">
                                    In Progress
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}

                  {/* Completed Projects Section */}
                  {progressData.filter(p => p.overall_progress === 100).length > 0 && (
                    <div>
                      <h3 className="text-lg font-medium text-psb-green mb-3 flex items-center gap-2">
                        <CheckCircle size={18} />
                        Completed ({progressData.filter(p => p.overall_progress === 100).length})
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {progressData
                          .filter(p => p.overall_progress === 100)
                          .map((project, index) => (
                            <div 
                              key={index}
                              onClick={() => {
                                setShowAllRequests(false);
                                onViewProjectById && onViewProjectById(project.project_id, project.current_page, project);
                              }}
                              className="p-4 bg-psb-green/10 border border-psb-green/30 rounded-lg hover:bg-psb-green/20 transition-all cursor-pointer group"
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex-1 min-w-0">
                                  <p className="text-white font-medium truncate group-hover:text-psb-green transition-colors">
                                    {project.project_title}
                                  </p>
                                  <p className="text-slate-500 text-xs font-mono">{project.project_id}</p>
                                </div>
                                <CheckCircle size={20} className="text-psb-green" />
                              </div>
                              
                              {/* Completed Badge */}
                              <div className="flex items-center justify-between mb-3">
                                <span className="text-psb-green text-sm font-medium">✓ All stages completed</span>
                                <span className="text-psb-green font-bold">100%</span>
                              </div>
                              
                              {/* Full Progress Bar */}
                              <div className="w-full bg-slate-600 rounded-full h-2 mb-3">
                                <div className="h-2 rounded-full bg-psb-green w-full" />
                              </div>
                              
                              {/* Step Indicators - All Complete */}
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1">
                                  {[...Array(10)].map((_, i) => (
                                    <div key={i} className="w-2 h-2 rounded-full bg-psb-green" />
                                  ))}
                                </div>
                                <span className="text-slate-400 text-xs">
                                  {project.updated_at ? new Date(project.updated_at).toLocaleDateString() : 'Completed'}
                                </span>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Rejected Projects Section */}
                  {rejectedData.projects.length > 0 && (
                    <div>
                      <h3 className="text-lg font-medium text-red-400 mb-3 flex items-center gap-2">
                        <XCircle size={18} />
                        Rejected ({rejectedData.total_rejected})
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {rejectedData.projects.map((project, index) => (
                          <div 
                            key={index}
                            className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg"
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex-1 min-w-0">
                                <p className="text-white font-medium truncate">
                                  {project.project_title || project.project_id}
                                </p>
                                <p className="text-slate-500 text-xs font-mono">{project.project_id}</p>
                              </div>
                              <XCircle size={20} className="text-red-400" />
                            </div>
                            
                            {/* Rejected Info */}
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-red-400 text-sm font-medium">✗ Rejected at Approval</span>
                            </div>
                            
                            {/* Rejection Details */}
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-400">
                                Rejected: {new Date(project.rejected_at).toLocaleDateString()}
                              </span>
                              <span className="text-xs font-medium px-2 py-0.5 rounded text-red-400 bg-red-500/20">
                                Rejected
                              </span>
                            </div>
                            
                            {/* Rejection Reason if available */}
                            {project.rejection_reason && (
                              <div className="mt-2 p-2 bg-red-500/5 rounded text-xs text-slate-400">
                                Reason: {project.rejection_reason}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Published/Completed RFPs Modal */}
      {showCompletedRFPs && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-5xl max-h-[85vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-psb-green/20 rounded-lg">
                  <CheckCircle size={24} className="text-psb-green" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">Completed Procurements</h2>
                  <p className="text-slate-400 text-sm">
                    {progressData.filter(p => p.overall_progress === 100).length} completed projects (100% progress)
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowCompletedRFPs(false)}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X size={24} className="text-slate-400 hover:text-white" />
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-5 overflow-y-auto max-h-[calc(85vh-80px)]">
              {progressData.filter(p => p.overall_progress === 100).length === 0 ? (
                <div className="text-center py-12">
                  <Send size={48} className="text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No completed procurements yet</p>
                  <p className="text-slate-500 text-sm">Projects will appear here when they reach 100% completion</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {progressData
                    .filter(p => p.overall_progress === 100)
                    .map((project, index) => (
                      <div 
                        key={index}
                        onClick={() => {
                          setShowCompletedRFPs(false);
                          onViewProjectById && onViewProjectById(project.project_id, project.current_page, project);
                        }}
                        className="p-4 bg-psb-green/10 border border-psb-green/30 rounded-lg hover:bg-psb-green/20 transition-all cursor-pointer group"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-white font-medium truncate group-hover:text-psb-green transition-colors">
                              {project.project_title}
                            </p>
                            <p className="text-slate-500 text-xs font-mono">{project.project_id}</p>
                          </div>
                          <CheckCircle size={20} className="text-psb-green" />
                        </div>
                        
                        {/* Completed Badge */}
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-psb-green text-sm font-medium">✓ All 10 stages completed</span>
                          <span className="text-psb-green font-bold">100%</span>
                        </div>
                        
                        {/* Full Progress Bar */}
                        <div className="w-full bg-slate-600 rounded-full h-2 mb-3">
                          <div className="h-2 rounded-full bg-psb-green w-full" />
                        </div>
                        
                        {/* Step Indicators - All Complete */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            {[...Array(10)].map((_, i) => (
                              <div key={i} className="w-2 h-2 rounded-full bg-psb-green" />
                            ))}
                          </div>
                          <span className="text-slate-400 text-xs">
                            {project.updated_at ? new Date(project.updated_at).toLocaleDateString() : 'Completed'}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default Dashboard;
