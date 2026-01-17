import React, { useState } from 'react';
import { ClipboardCheck, ArrowRight, FileText, Download } from 'lucide-react';

function TenderDrafting({ requirement, workflowData, onComplete }) {
  const [tender, setTender] = useState({
    tenderType: '',
    bidValidity: '90 days',
    submissionDeadline: '',
    technicalCriteria: '',
    commercialCriteria: '',
    eligibilityCriteria: '',
    emdAmount: '',
  });

  const [sections, setSections] = useState({
    scopeOfWork: false,
    technicalSpecs: false,
    commercialTerms: false,
    eligibility: false,
    evaluation: false,
    slaTerms: false,
  });

  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(false);

  // Page tracking - This is Page 4 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 4,
    pageName: 'Tender Drafting',
    nextPage: 5,
    nextPageName: 'Authority Approval'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 3,           // case 3 in App.js
    currentComponent: 'TenderDrafting',
    nextStage: 4,              // case 4 in App.js
    nextComponent: 'ApprovalGate',
    nextPageName: 'Authority Approval'
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

  // Get rfp_id and project_id from workflowData (passed from TechnicalReview)
  const rfpId = workflowData?.generatedRfp?.rfpId;
  const projectId = workflowData?.generatedRfp?.projectId || requirement?.project_id || requirement?.reqId || requirement?.projectId;

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

  const handleDownloadRFP = async () => {
    try {
      setGenerating(true);

      // Use rfp_id if available, otherwise fall back to fetching by project_id
      if (rfpId) {
        // Direct download using rfp_id
        const downloadUrl = `http://localhost:8003/technical-review/rfp/download/${rfpId}`;
        window.open(downloadUrl, "_blank");
      } else {
        // Fallback: fetch RFP by project_id
        const res = await fetch(`http://localhost:8003/technical-review/rfp/project/${projectId}`);
        const data = await res.json();

        if (!res.ok) {
          alert(data.detail || "No RFP found for this project");
          return;
        }

        // Get latest version
        const latest = data.rfps[0];
        const downloadUrl = `http://localhost:8003${latest.download_url}`;
        window.open(downloadUrl, "_blank");
      }
    } catch (err) {
      console.error(err);
      alert("Error downloading RFP");
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmit = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setLoading(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('TENDER DRAFTING - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Submitting tender draft...');

      const res = await fetch("http://localhost:8003/tender/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          select_rfp_template: tender.tenderType,
          bid_validity_period: tender.bidValidity,
          submission_deadline: tender.submissionDeadline,
          emd_amount: tender.emdAmount,
          eligibility_criteria: tender.eligibilityCriteria
        })
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to submit tender draft");
        return;
      }

      console.log("Tender draft saved:", data);

      // Update progress tracking - Mark Page 4 as complete
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

      // Move to approval stage, passing along rfp info
      onComplete({ 
        tenderDetails: tender, 
        tenderSections: sections,
        rfpId: rfpId,
        projectId: projectId,
        // Progress tracking info
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      alert("Server error while submitting tender draft");
    } finally {
      setLoading(false);
    }
  };

  const allSectionsComplete = Object.values(sections).every(v => v);

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-orange-500/20 rounded-lg">
            <ClipboardCheck size={24} className="text-orange-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Tender/RFP Drafting</h2>
            <p className="text-slate-400 text-sm">Stage 4 - Procurement Cell Document Preparation</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-orange-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-orange-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* RFP Info Banner */}
      {rfpId && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-green-400" />
            <span className="text-green-400 font-medium">RFP Generated (Page 3)</span>
          </div>
          <p className="text-slate-300 text-sm mt-1">
            RFP ID: <span className="text-white font-mono">{rfpId}</span> | 
            Project: <span className="text-white font-mono">{projectId}</span>
            {workflowData?.generatedRfp?.version && (
              <> | Version: <span className="text-white">{workflowData.generatedRfp.version}</span></>
            )}
          </p>
        </div>
      )}

      {/* Template Selection */}
      <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
        <h3 className="text-psb-gold font-medium mb-3">Select RFP Template</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {['Open Tender', 'Limited Tender', 'Single Source'].map(type => (
            <label 
              key={type}
              className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition-all ${
                tender.tenderType === type 
                  ? 'bg-psb-green/20 border-psb-green' 
                  : 'bg-slate-600/30 border-slate-600 hover:border-slate-500'
              }`}
            >
              <input
                type="radio"
                name="tenderType"
                checked={tender.tenderType === type}
                onChange={() => setTender({...tender, tenderType: type})}
                className="w-4 h-4 text-psb-green"
              />
              <span className="text-white text-sm">{type}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tender Parameters */}
        <div className="space-y-4">
          <h3 className="text-psb-gold font-medium">Tender Parameters</h3>
          
          <div>
            <label className="block text-slate-300 text-sm mb-1">Bid Validity Period</label>
            <select
              value={tender.bidValidity}
              onChange={(e) => setTender({...tender, bidValidity: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            >
              <option value="60 days">60 Days</option>
              <option value="90 days">90 Days</option>
              <option value="120 days">120 Days</option>
              <option value="180 days">180 Days</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">Submission Deadline</label>
            <input
              type="date"
              value={tender.submissionDeadline}
              onChange={(e) => setTender({...tender, submissionDeadline: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            />
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">EMD Amount</label>
            <input
              type="text"
              value={tender.emdAmount}
              onChange={(e) => setTender({...tender, emdAmount: e.target.value})}
              placeholder="e.g., Rs. 5,00,000"
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400"
            />
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">Eligibility Criteria</label>
            <textarea
              value={tender.eligibilityCriteria}
              onChange={(e) => setTender({...tender, eligibilityCriteria: e.target.value})}
              rows={3}
              placeholder="Minimum turnover, experience, certifications..."
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 resize-none"
            />
          </div>
        </div>

        {/* Document Sections Checklist */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">RFP Document Sections</h3>
          <div className="space-y-3">
            {[
              { key: 'scopeOfWork', label: 'Scope of Work', desc: 'Detailed requirements and deliverables' },
              { key: 'technicalSpecs', label: 'Technical Specifications', desc: 'Hardware, software, integration needs' },
              { key: 'commercialTerms', label: 'Commercial Terms', desc: 'Pricing format, payment terms' },
              { key: 'eligibility', label: 'Eligibility Criteria', desc: 'Vendor qualification requirements' },
              { key: 'evaluation', label: 'Evaluation Methodology', desc: 'Scoring criteria and weights' },
              { key: 'slaTerms', label: 'SLA Terms', desc: 'Service levels and penalties' },
            ].map(item => (
              <label 
                key={item.key}
                className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer border transition-all ${
                  sections[item.key] 
                    ? 'bg-psb-green/10 border-psb-green/50' 
                    : 'bg-slate-700/30 border-slate-600 hover:border-slate-500'
                }`}
              >
                <input
                  type="checkbox"
                  checked={sections[item.key]}
                  onChange={(e) => setSections({...sections, [item.key]: e.target.checked})}
                  className="w-5 h-5 mt-0.5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
                />
                <div>
                  <span className="text-white text-sm font-medium">{item.label}</span>
                  <p className="text-slate-400 text-xs">{item.desc}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Download Draft Button */}
          <button
            onClick={handleDownloadRFP}
            disabled={generating}
            className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <Download size={18} />
            {generating ? "Downloading..." : "Download Draft RFP (Preview)"}
          </button>
        </div>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-orange-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!allSectionsComplete || !tender.tenderType || loading}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {loading ? "Submitting..." : "Submit for In-Principle Approval"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default TenderDrafting;
