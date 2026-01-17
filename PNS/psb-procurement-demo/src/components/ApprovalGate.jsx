import React, { useState } from 'react';
import { CheckCircle, XCircle, AlertTriangle, FileText, Clock } from 'lucide-react';

function ApprovalGate({ requirement, workflowData, onApproval, isApproved }) {
  const [loading, setLoading] = useState(false);

  // Page tracking - This is Page 5 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 5,
    pageName: 'Authority Approval',
    nextPage: 6,
    nextPageName: 'Publish RFP',
    rejectedPage: 2  // Special value to track rejected documents
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 4,           // case 4 in App.js
    currentComponent: 'ApprovalGate',
    nextStage: 5,              // case 5 in App.js
    nextComponent: 'PublishRFP',
    nextPageName: 'Publish RFP'
  };

  // Update navigation in database
  const updateNavigation = async (projId) => {
    try {
      console.log('Updating navigation for project:', projId);
      const response = await fetch(`http://localhost:8003/requirements/navigation/${projId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_stage: NAVIGATION.nextStage,
          current_page_component: NAVIGATION.nextComponent,
          current_page_name: NAVIGATION.nextPageName
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Navigation updated:', data);
        return data;
      }
    } catch (error) {
      console.error('Error updating navigation:', error);
    }
    return null;
  };

  // Delete navigation when rejected
  const deleteNavigation = async (projId) => {
    try {
      console.log('Deleting navigation for rejected project:', projId);
      const response = await fetch(`http://localhost:8003/requirements/navigation/${projId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Navigation deleted:', data);
        return data;
      }
    } catch (error) {
      console.error('Error deleting navigation:', error);
    }
    return null;
  };

  // Get project ID
  const projectId = requirement?.reqId || requirement?.project_id || requirement?.projectId;

  // Update progress tracking API call
  const updateProgress = async (projId, pageNumber) => {
    try {
      console.log(`[ApprovalGate] Calling progress update API...`);
      console.log(`[ApprovalGate] Project ID: ${projId}, Page: ${pageNumber}`);
      
      const requestBody = {
        project_id: projId,
        page_number: pageNumber,
        is_completed: true
      };
      
      console.log(`[ApprovalGate] Request body:`, JSON.stringify(requestBody));
      
      const response = await fetch('http://localhost:8003/requirements/progress/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      console.log(`[ApprovalGate] Response status: ${response.status}`);

      const data = await response.json();
      console.log(`[ApprovalGate] Response data:`, data);

      if (response.ok) {
        console.log('[ApprovalGate] Progress updated successfully:', data);
        return data;
      } else {
        console.error('[ApprovalGate] Progress update failed:', data);
        return null;
      }
    } catch (error) {
      console.error('[ApprovalGate] Error updating progress:', error);
    }
    return null;
  };

  const submitDecision = async (decision) => {
    try {
      setLoading(true);

      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('APPROVAL GATE - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log(`Decision: ${decision ? 'APPROVED ✓' : 'REJECTED ✗'}`);
      console.log('-'.repeat(60));

      // Submit authority decision to backend
      const res = await fetch("http://localhost:8003/tender/authority-decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          truth_value: decision ? 1 : 0
        })
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to submit authority decision");
        return;
      }

      console.log("Authority decision saved:", data);

      if (decision) {
        // APPROVED - Mark Page 5 as complete
        console.log('-'.repeat(60));
        console.log('[ApprovalGate] APPROVED - Updating progress tracking...');
        
        const progressData = await updateProgress(projectId, PAGE_INFO.currentPage);
        
        // Update navigation in database
        console.log('-'.repeat(60));
        console.log('UPDATING NAVIGATION:');
        const navData = await updateNavigation(projectId);
        if (navData) {
          console.log(`  Next Stage: ${NAVIGATION.nextStage} (case ${NAVIGATION.nextStage})`);
          console.log(`  Next Component: ${NAVIGATION.nextComponent}`);
        }
        
        console.log('-'.repeat(60));
        console.log('PROGRESS TRACKING (APPROVED):');
        if (progressData) {
          console.log(`  Current Page: ${progressData.current_page}`);
          console.log(`  Overall Progress: ${progressData.overall_progress}%`);
          console.log(`  Status: ${progressData.status}`);
          console.log(`  ✓ Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName}) is now COMPLETED`);
        } else {
          console.log('  ⚠️ Progress update returned null - check API response above');
        }
        console.log(`  Next step: Navigate to Page ${PAGE_INFO.nextPage} (${PAGE_INFO.nextPageName})`);
        console.log('='.repeat(60));
      } else {
  // REJECTED
  console.log('-'.repeat(60));
  console.log('PROGRESS TRACKING (REJECTED):');
  console.log(`  ⚠️ Document REJECTED at Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName})`);
  console.log('='.repeat(60));

  try {
    // 1️⃣ Remove progress
    console.log('[ApprovalGate] Removing progress tracking...');
    const removeProgressRes = await fetch(
      `http://localhost:8003/requirements/progress/remove/${projectId}`,
      { method: 'POST' }
    );

    if (!removeProgressRes.ok) {
      const err = await removeProgressRes.text();
      console.error('[ApprovalGate] Failed to remove progress:', err);
    } else {
      console.log('[ApprovalGate] Progress removed successfully');
    }

    // 2️⃣ Add to rejected table
    console.log('[ApprovalGate] Adding project to rejected list...');
    const rejectedRes = await fetch(
      `http://localhost:8003/requirements/rejected/${projectId}`,
      { method: 'POST' }
    );

    if (!rejectedRes.ok) {
      const err = await rejectedRes.text();
      console.error('[ApprovalGate] Failed to mark project as rejected:', err);
    } else {
      console.log('[ApprovalGate] Project marked as rejected successfully');
    }

    // 3️⃣ Delete navigation record
    console.log('[ApprovalGate] Deleting navigation record...');
    await deleteNavigation(projectId);

  } catch (error) {
    console.error('[ApprovalGate] Error during rejection handling:', error);
  }

  console.log('  Workflow TERMINATED');
  console.log('='.repeat(60));
}

      // Now move UI forward/backward
      onApproval(decision);

    } catch (err) {
      console.error(err);
      alert("Server error while submitting decision");
    } finally {
      setLoading(false);
    }
  };

  if (isApproved === false) {
    return (
      <div className="bg-slate-800/50 backdrop-blur border border-red-500/50 rounded-xl p-6">
        <div className="text-center py-12">
          <div className="w-24 h-24 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <XCircle size={48} className="text-red-500" />
          </div>
          <h2 className="text-2xl font-semibold text-red-400 mb-2">Requirement Rejected</h2>
          <p className="text-slate-400 mb-6">The procurement requirement has not been approved by the Competent Authority.</p>
          <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 max-w-md mx-auto">
            <p className="text-red-300 text-sm">
              The workflow has been terminated. Please review the feedback and submit a revised requirement if needed.
            </p>
          </div>
          {/* Rejection tracking info */}
          <div className="mt-4 text-slate-500 text-xs">
            <p>Project ID: {projectId} | Status: Rejected</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-500/20 rounded-lg">
            <CheckCircle size={24} className="text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">In-Principle Approval</h2>
            <p className="text-slate-400 text-sm">Stage 5 - Competent Authority Decision</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-blue-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-blue-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
        
        <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-sm font-medium">
          Approval Gate
        </span>
      </div>

      {/* Warning Banner */}
      <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-lg p-4 mb-6 flex items-start gap-3">
        <AlertTriangle size={20} className="text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-yellow-300 font-medium">Critical Decision Point</p>
          <p className="text-yellow-200/70 text-sm">This is a mandatory approval gate. Rejection will terminate the entire procurement process.</p>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-slate-700/30 rounded-lg p-5 mb-6">
        <h3 className="text-psb-gold font-medium mb-4">Procurement Summary for Approval</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div>
              <p className="text-slate-400 text-xs uppercase">Request ID</p>
              <p className="text-white font-mono">{projectId}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Title</p>
              <p className="text-white font-medium">{requirement?.title}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Department</p>
              <p className="text-white">{requirement?.department}</p>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-slate-400 text-xs uppercase">Estimated Value</p>
              <p className="text-psb-green font-semibold text-lg">{requirement?.estimatedValue}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Priority</p>
              <span className="inline-block px-2 py-1 bg-red-500/20 text-red-400 rounded text-sm">
                {requirement?.priority}
              </span>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Tender Type</p>
              <p className="text-white">{workflowData?.tenderDetails?.tenderType || 'Open Tender'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Previous Stage Summaries */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={16} className="text-psb-gold" />
            <h4 className="text-white text-sm font-medium">Functional Analysis</h4>
          </div>
          <p className="text-psb-green text-sm">{workflowData?.functionalAnalysis?.functionalFit || 'Completed'}</p>
          <p className="text-slate-500 text-xs">Page 2 ✓</p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={16} className="text-psb-gold" />
            <h4 className="text-white text-sm font-medium">Technical Review</h4>
          </div>
          <p className="text-psb-green text-sm">{workflowData?.technicalReview?.securityAssessment || 'Approved'}</p>
          <p className="text-slate-500 text-xs">Page 3 ✓</p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-psb-gold" />
            <h4 className="text-white text-sm font-medium">Tender Drafting</h4>
          </div>
          <p className="text-white text-sm">{workflowData?.tenderDetails?.bidValidity || '90 days'}</p>
          <p className="text-slate-500 text-xs">Page 4 ✓</p>
        </div>
      </div>

      {/* Approval Actions */}
      <div className="border-t border-slate-700 pt-6">
        <h3 className="text-white font-medium mb-4 text-center">Competent Authority Decision</h3>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => submitDecision(true)}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-8 py-4 bg-psb-green hover:bg-psb-green-light text-white rounded-lg transition-all duration-200 font-medium text-lg shadow-lg shadow-psb-green/20"
          >
            <CheckCircle size={24} />
            {loading ? "Processing..." : "Approve & Proceed"}
          </button>
          <button
            onClick={() => submitDecision(false)}
            disabled={loading}  
            className="flex items-center justify-center gap-2 px-8 py-4 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-all duration-200 font-medium text-lg"
          >
            <XCircle size={24} />
            {loading ? "Processing..." : "Reject Requirement"}
          </button>
        </div>
        <p className="text-slate-500 text-xs text-center mt-4">
          Approval will mark Page {PAGE_INFO.currentPage} complete and proceed to {PAGE_INFO.nextPageName}. 
          Rejection will terminate the workflow.
        </p>
      </div>
    </div>
  );
}

export default ApprovalGate;
