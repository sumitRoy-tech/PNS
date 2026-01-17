import React, { useState } from 'react';
import { Users, ArrowRight, Shield, Server, Database } from 'lucide-react';

function TechnicalReview({ requirement, workflowData, onComplete }) {
  const [review, setReview] = useState({
    architectureReview: '',
    securityAssessment: '',
    integrationComplexity: '',
    complianceCheck: '',
    technicalRecommendation: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Page tracking - This is Page 3 (includes RFP generation as part of this step)
  const PAGE_INFO = {
    currentPage: 3,
    pageName: 'Technical Review',
    nextPage: 4,
    nextPageName: 'Tender Drafting'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 2,           // case 2 in App.js
    currentComponent: 'TechnicalReview',
    nextStage: 3,              // case 3 in App.js
    nextComponent: 'TenderDrafting',
    nextPageName: 'Tender Drafting'
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

  // Get project ID
  const projectId = requirement?.project_id || requirement?.id || requirement?.reqId || requirement?.projectId;

  // Update progress tracking API call
  const updateProgress = async (projId, pageNumber) => {
    try {
      console.log(`Updating progress: Page ${pageNumber} completed for project ${projId}`);
      
      const response = await fetch('http://localhost:8003/requirements/progress/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projId,
          page_number: pageNumber,
          is_completed: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Progress updated:', data);
        return data;
      }
    } catch (error) {
      console.error('Error updating progress:', error);
    }
    return null;
  };

  const handleSubmit = async () => {
    if (!projectId) {
      alert("Project ID missing");
      return;
    }

    const payload = {
      project_id: projectId,
      architecture_review: review.architectureReview,
      security_assessment: review.securityAssessment,
      integration_complexity: review.integrationComplexity,
      rbi_compliance_check: review.complianceCheck,
      technical_committee_recommendation: review.technicalRecommendation,
    };

    try {
      setLoading(true);
      setError(null);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('TECHNICAL REVIEW - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Step 1: Submitting technical review...');

      // Step 1: Submit technical review
      const res = await fetch("http://localhost:8003/technical-review/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to submit technical review");
      }

      const submitData = await res.json();
      console.log("Technical review submitted:", submitData);

      // Step 2: Generate RFP (part of Page 3)
      console.log('-'.repeat(60));
      console.log('Step 2: Generating RFP...');

      const generateRes = await fetch("http://localhost:8003/technical-review/generate-rfp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: submitData.project_id || projectId
        })
      });

      if (!generateRes.ok) {
        const err = await generateRes.json();
        throw new Error(err.detail || "Failed to generate RFP");
      }

      const rfpData = await generateRes.json();
      console.log("RFP generated:", rfpData);

      // Update progress - Mark Page 3 as complete
      const progressData = await updateProgress(projectId, PAGE_INFO.currentPage);

      // Update navigation in database
      console.log('-'.repeat(60));
      console.log('UPDATING NAVIGATION:');
      const navData = await updateNavigation(projectId);
      if (navData) {
        console.log(`  Next Stage: ${NAVIGATION.nextStage} (case ${NAVIGATION.nextStage})`);
        console.log(`  Next Component: ${NAVIGATION.nextComponent}`);
      }

      // Progress summary
      console.log('-'.repeat(60));
      console.log('PROGRESS TRACKING:');
      if (progressData) {
        console.log(`  Current Page: ${progressData.current_page}`);
        console.log(`  Overall Progress: ${progressData.overall_progress}%`);
        console.log(`  Status: ${progressData.status}`);
      }
      console.log(`  Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName}) is now COMPLETED`);
      console.log(`  Next step: Navigate to Page ${PAGE_INFO.nextPage} (${PAGE_INFO.nextPageName})`);
      console.log('='.repeat(60));

      // Pass generated RFP info into workflow for next stage
      onComplete({
        technicalReview: review,
        generatedRfp: {
          rfpId: rfpData.rfp_id,
          projectId: rfpData.project_id,
          projectTitle: rfpData.project_title,
          version: rfpData.version,
          filename: rfpData.filename,
          downloadUrl: rfpData.download_url
        },
        // Progress tracking info
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      setError(err.message);
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/20 rounded-lg">
            <Users size={24} className="text-purple-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Technical Committee Review</h2>
            <p className="text-slate-400 text-sm">Stage 3 - Technical Assessment & RFP Generation</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-purple-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-purple-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Requirement & Previous Analysis Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-700/30 rounded-lg p-4">
          <h3 className="text-sm text-slate-400 uppercase tracking-wide mb-2">Requirement</h3>
          <p className="text-white font-medium">{requirement?.title}</p>
          <p className="text-psb-green text-sm mt-1">{requirement?.estimatedValue}</p>
          <p className="text-slate-400 text-xs mt-1">ID: <span className="text-white font-mono">{projectId}</span></p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-4">
          <h3 className="text-sm text-slate-400 uppercase tracking-wide mb-2">Previous Analysis (Page 2)</h3>
          <p className="text-white text-sm">
            Feasibility: <span className="text-psb-gold">{workflowData?.functionalAnalysis?.technicalFeasibility || 'Completed'}</span>
          </p>
          <p className="text-white text-sm">
            Risk: <span className="text-psb-gold">{workflowData?.functionalAnalysis?.riskAssessment || 'Assessed'}</span>
          </p>
        </div>
      </div>

      {/* Technical Review Areas */}
      <div className="space-y-6">
        <h3 className="text-psb-gold font-medium">Technical Assessment Areas</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Architecture Review */}
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Server size={18} className="text-blue-400" />
              <h4 className="text-white font-medium">Architecture Review</h4>
            </div>
            <select
              value={review.architectureReview}
              onChange={(e) => setReview({ ...review, architectureReview: e.target.value })}
              className="w-full px-3 py-2 bg-slate-600/50 border border-slate-500 rounded-lg text-white text-sm"
            >
              <option value="">Select Status</option>
              <option value="Compatible with existing architecture">Compatible with existing architecture</option>
              <option value="Requires minor modifications">Requires minor modifications</option>
              <option value="Requires significant changes">Requires significant changes</option>
              <option value="New architecture needed">New architecture needed</option>
            </select>
          </div>

          {/* Security Assessment */}
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield size={18} className="text-green-400" />
              <h4 className="text-white font-medium">Security Assessment</h4>
            </div>
            <select
              value={review.securityAssessment}
              onChange={(e) => setReview({ ...review, securityAssessment: e.target.value })}
              className="w-full px-3 py-2 bg-slate-600/50 border border-slate-500 rounded-lg text-white text-sm"
            >
              <option value="">Select Status</option>
              <option value="Meets all security requirements">Meets all security requirements</option>
              <option value="Minor security concerns">Minor security concerns</option>
              <option value="Requires security review">Requires security review</option>
              <option value="Major security concerns">Major security concerns</option>
            </select>
          </div>

          {/* Integration Complexity */}
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Database size={18} className="text-yellow-400" />
              <h4 className="text-white font-medium">Integration Complexity</h4>
            </div>
            <select
              value={review.integrationComplexity}
              onChange={(e) => setReview({ ...review, integrationComplexity: e.target.value })}
              className="w-full px-3 py-2 bg-slate-600/50 border border-slate-500 rounded-lg text-white text-sm"
            >
              <option value="">Select Complexity</option>
              <option value="Simple - Standard APIs">Simple - Standard APIs</option>
              <option value="Moderate - Custom integration">Moderate - Custom integration</option>
              <option value="Complex - Multiple systems">Complex - Multiple systems</option>
              <option value="Very Complex - Legacy systems">Very Complex - Legacy systems</option>
            </select>
          </div>

          {/* Compliance Check */}
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield size={18} className="text-orange-400" />
              <h4 className="text-white font-medium">RBI/Compliance Check</h4>
            </div>
            <select
              value={review.complianceCheck}
              onChange={(e) => setReview({ ...review, complianceCheck: e.target.value })}
              className="w-full px-3 py-2 bg-slate-600/50 border border-slate-500 rounded-lg text-white text-sm"
            >
              <option value="">Select Status</option>
              <option value="Fully Compliant">Fully Compliant</option>
              <option value="Compliant with conditions">Compliant with conditions</option>
              <option value="Requires compliance review">Requires compliance review</option>
              <option value="Non-compliant">Non-compliant</option>
            </select>
          </div>
        </div>

        {/* Technical Recommendation */}
        <div>
          <label className="block text-slate-300 text-sm mb-2">Technical Committee Recommendation</label>
          <textarea
            value={review.technicalRecommendation}
            onChange={(e) => setReview({ ...review, technicalRecommendation: e.target.value })}
            rows={4}
            placeholder="Enter technical committee's recommendations, concerns, and suggestions..."
            className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 resize-none"
          />
        </div>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-purple-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 text-white rounded-lg transition-all duration-200 font-medium"
        >
          {loading ? "Submitting & Generating RFP..." : "Submit and Generate RFP"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default TechnicalReview;
