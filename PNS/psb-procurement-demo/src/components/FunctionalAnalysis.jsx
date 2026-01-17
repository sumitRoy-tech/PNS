import React, { useState } from 'react';
import { Settings, ArrowRight, CheckSquare } from 'lucide-react';

function FunctionalAnalysis({ requirement, onComplete }) {
  const [analysis, setAnalysis] = useState({
    functionalFit: '',
    technicalFeasibility: '',
    riskAssessment: '',
    recommendations: '',
  });

  const [checklist, setChecklist] = useState({
    requirementsClear: false,
    budgetVerified: false,
    stakeholdersIdentified: false,
    timelineRealistic: false,
    alternativesConsidered: false,
  });

  const [loading, setLoading] = useState(false);

  // Page tracking info - This is Page 2 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 2,
    pageName: 'Functional Assessment',
    nextPage: 3,
    nextPageName: 'Technical Review'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 1,           // case 1 in App.js
    currentComponent: 'FunctionalAnalysis',
    nextStage: 2,              // case 2 in App.js
    nextComponent: 'TechnicalReview',
    nextPageName: 'Technical Review'
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

  // Check if all checklist items are checked
  const allChecked = Object.values(checklist).every(v => v);

  // Check if all form fields are filled
  const allFieldsFilled = 
    analysis.functionalFit !== '' &&
    analysis.technicalFeasibility !== '' &&
    analysis.riskAssessment !== '' &&
    analysis.recommendations.trim() !== '';

  // Button is enabled only when ALL fields are filled AND all checklist items are checked
  const isFormValid = allChecked && allFieldsFilled;

  // Get project ID
  const projectId = requirement?.project_id || requirement?.reqId || requirement?.projectId;

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
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setLoading(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('FUNCTIONAL ANALYSIS - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Submitting functional assessment...');

      const formData = new FormData();
      formData.append("project_id", projectId);
      formData.append("functional_fit_assessment", analysis.functionalFit);
      formData.append("technical_feasibility", analysis.technicalFeasibility);
      formData.append("risk_assessment", analysis.riskAssessment);
      formData.append("recommendations", analysis.recommendations);

      const res = await fetch("http://localhost:8003/functional/assessment", {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        if (data.detail && data.detail.includes("already exists")) {
          // Assessment already exists - update progress and continue
          console.log('Assessment already exists, continuing workflow...');
          
          // Update progress tracking
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
          console.log('PROGRESS TRACKING:');
          if (progressData) {
            console.log(`  Current Page: ${progressData.current_page}`);
            console.log(`  Overall Progress: ${progressData.overall_progress}%`);
            console.log(`  Status: ${progressData.status}`);
          }
          console.log(`  Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName}) is now COMPLETED`);
          console.log(`  Next step: Navigate to Page ${PAGE_INFO.nextPage} (${PAGE_INFO.nextPageName})`);
          console.log('='.repeat(60));
          
          onComplete({ 
            functionalAnalysis: analysis, 
            analysisChecklist: checklist,
            completedPage: PAGE_INFO.currentPage,
            completedPageName: PAGE_INFO.pageName,
            nextPage: PAGE_INFO.nextPage,
            nextPageName: PAGE_INFO.nextPageName,
            progress: progressData
          });
          return;
        }
        alert(data.detail || "Failed to submit assessment");
        return;
      }

      console.log("Assessment saved:", data);

      // Update progress tracking - Mark Page 2 as complete
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
      console.log('PROGRESS TRACKING:');
      if (progressData) {
        console.log(`  Current Page: ${progressData.current_page}`);
        console.log(`  Overall Progress: ${progressData.overall_progress}%`);
        console.log(`  Status: ${progressData.status}`);
      }
      console.log(`  Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName}) is now COMPLETED`);
      console.log(`  Next step: Navigate to Page ${PAGE_INFO.nextPage} (${PAGE_INFO.nextPageName})`);
      console.log('='.repeat(60));

      // Pass data to next stage with progress info
      onComplete({ 
        functionalAnalysis: analysis, 
        analysisChecklist: checklist,
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      alert("Server error while submitting assessment");
    } finally {
      setLoading(false);
    }
  };

  // Calculate completion status for visual feedback
  const getFieldStatus = (value) => {
    if (typeof value === 'string') {
      return value.trim() !== '';
    }
    return !!value;
  };

  const filledFieldsCount = Object.values(analysis).filter(v => getFieldStatus(v)).length;
  const totalFields = Object.keys(analysis).length;
  const checkedCount = Object.values(checklist).filter(v => v).length;
  const totalChecklist = Object.keys(checklist).length;

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-psb-gold/20 rounded-lg">
            <Settings size={24} className="text-psb-gold" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Functional & Technical Analysis</h2>
            <p className="text-slate-400 text-sm">Stage 2 - IT & Business Teams Review</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-psb-gold text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-psb-gold animate-pulse' : 'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Requirement Summary */}
      <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
        <h3 className="text-sm text-slate-400 uppercase tracking-wide mb-2">Requirement Under Review</h3>
        <p className="text-white font-medium">{requirement?.title}</p>
        <div className="flex gap-4 mt-2 text-sm">
          <span className="text-slate-400">ID: <span className="text-white font-mono">{projectId}</span></span>
          <span className="text-slate-400">Value: <span className="text-psb-green">{requirement?.estimatedValue || requirement?.estimated_amount}</span></span>
          <span className="text-slate-400">Dept: <span className="text-white">{requirement?.department}</span></span>
        </div>
      </div>

      {/* Form Completion Status */}
      <div className="bg-slate-700/30 rounded-lg p-3 mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Form Completion:</span>
          <div className="flex items-center gap-4">
            <span className={`${filledFieldsCount === totalFields ? 'text-psb-green' : 'text-yellow-400'}`}>
              Fields: {filledFieldsCount}/{totalFields}
            </span>
            <span className={`${checkedCount === totalChecklist ? 'text-psb-green' : 'text-yellow-400'}`}>
              Checklist: {checkedCount}/{totalChecklist}
            </span>
            {isFormValid && (
              <span className="text-psb-green font-medium">✓ Ready to submit</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Analysis Form */}
        <div className="space-y-4">
          <h3 className="text-psb-gold font-medium">Analysis Report <span className="text-red-400 text-sm">(All fields required)</span></h3>
          
          <div>
            <label className="block text-slate-300 text-sm mb-1">
              Functional Fit Assessment <span className="text-red-400">*</span>
            </label>
            <select
              value={analysis.functionalFit}
              onChange={(e) => setAnalysis({...analysis, functionalFit: e.target.value})}
              className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white ${
                analysis.functionalFit ? 'border-psb-green' : 'border-slate-600'
              }`}
              required
            >
              <option value="">Select Assessment</option>
              <option value="Fully Meets Requirements">Fully Meets Requirements</option>
              <option value="Partially Meets Requirements">Partially Meets Requirements</option>
              <option value="Needs Modification">Needs Modification</option>
              <option value="Does Not Meet Requirements">Does Not Meet Requirements</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">
              Technical Feasibility <span className="text-red-400">*</span>
            </label>
            <select
              value={analysis.technicalFeasibility}
              onChange={(e) => setAnalysis({...analysis, technicalFeasibility: e.target.value})}
              className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white ${
                analysis.technicalFeasibility ? 'border-psb-green' : 'border-slate-600'
              }`}
              required
            >
              <option value="">Select Feasibility</option>
              <option value="Highly Feasible">Highly Feasible</option>
              <option value="Feasible with Modifications">Feasible with Modifications</option>
              <option value="Challenging but Achievable">Challenging but Achievable</option>
              <option value="Not Feasible">Not Feasible</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">
              Risk Assessment <span className="text-red-400">*</span>
            </label>
            <select
              value={analysis.riskAssessment}
              onChange={(e) => setAnalysis({...analysis, riskAssessment: e.target.value})}
              className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white ${
                analysis.riskAssessment ? 'border-psb-green' : 'border-slate-600'
              }`}
              required
            >
              <option value="">Select Risk Level</option>
              <option value="Low Risk">Low Risk</option>
              <option value="Medium Risk">Medium Risk</option>
              <option value="High Risk">High Risk</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">
              Recommendations <span className="text-red-400">*</span>
            </label>
            <textarea
              value={analysis.recommendations}
              onChange={(e) => setAnalysis({...analysis, recommendations: e.target.value})}
              rows={4}
              placeholder="Enter analysis recommendations..."
              className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 resize-none ${
                analysis.recommendations.trim() ? 'border-psb-green' : 'border-slate-600'
              }`}
              required
            />
          </div>
        </div>

        {/* Checklist */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Verification Checklist <span className="text-red-400 text-sm">(All required)</span></h3>
          <div className="space-y-3">
            {[
              { key: 'requirementsClear', label: 'Requirements are clear and complete' },
              { key: 'budgetVerified', label: 'Budget estimate verified and realistic' },
              { key: 'stakeholdersIdentified', label: 'All stakeholders identified' },
              { key: 'timelineRealistic', label: 'Timeline is realistic and achievable' },
              { key: 'alternativesConsidered', label: 'Alternatives have been considered' },
            ].map(item => (
              <label 
                key={item.key}
                className="flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/50 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={checklist[item.key]}
                  onChange={(e) => setChecklist({...checklist, [item.key]: e.target.checked})}
                  className="w-5 h-5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
                />
                <span className="text-slate-300 text-sm">{item.label}</span>
                {checklist[item.key] && <CheckSquare size={16} className="text-psb-green ml-auto" />}
              </label>
            ))}
          </div>

          <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
            <p className="text-blue-300 text-sm">
              <strong>Note:</strong> All form fields and checklist items must be completed before proceeding to Technical Review.
            </p>
          </div>
        </div>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          {!isFormValid ? (
            <span className="text-yellow-400">
              ⚠ Please complete all fields ({filledFieldsCount}/{totalFields}) and checklist ({checkedCount}/{totalChecklist})
            </span>
          ) : (
            <>
              <span>Completing this will mark </span>
              <span className="text-psb-gold font-medium">Page {PAGE_INFO.currentPage}</span>
              <span> as done → Next: </span>
              <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
            </>
          )}
        </div>
        <button
          onClick={handleSubmit}
          disabled={!isFormValid || loading}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {loading ? "Submitting..." : "Complete Analysis & Proceed"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default FunctionalAnalysis;
