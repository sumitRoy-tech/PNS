import React, { useState, useEffect } from 'react';
import { UserCheck, ArrowRight, Star, Award, Building } from 'lucide-react';

function VendorEvaluation({ requirement, workflowData, onComplete }) {
  const [vendors, setVendors] = useState([]);
  const [evaluationComplete, setEvaluationComplete] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Store full evaluation response for API submission
  const [evaluationData, setEvaluationData] = useState(null);
  
  // Store project data fetched from API
  const [projectData, setProjectData] = useState(null);

  // Page tracking - This is Page 8 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 8,
    pageName: 'Vendor Evaluation',
    nextPage: 9,
    nextPageName: 'Purchase Order'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 7,           // case 7 in App.js
    currentComponent: 'VendorEvaluation',
    nextStage: 8,              // case 8 in App.js
    nextComponent: 'PurchaseOrder',
    nextPageName: 'Purchase Order'
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

  // Get project_id from workflowData chain or requirement
  const projectId = workflowData?.projectId ||
                    workflowData?.generatedRfp?.projectId || 
                    requirement?.project_id || 
                    requirement?.reqId ||
                    requirement?.projectId;

  // Get project title - prefer API data, then workflowData, then requirement
  const projectTitle = projectData?.project_title ||
                       workflowData?.generatedRfp?.projectTitle ||
                       requirement?.title ||
                       requirement?.projectTitle ||
                       "Project";

  // Fetch vendor bids data from API on component mount
  useEffect(() => {
    const fetchVendorBids = async () => {
      if (!projectId) {
        console.error('No project ID available');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        console.log('Fetching vendor bids for project:', projectId);
        
        // Use the correct API endpoint: /publish/vendor-bids/{project_id}
        const res = await fetch(`http://localhost:8003/publish/vendor-bids/${projectId}`);
        const data = await res.json();

        console.log('Vendor bids API response:', data);

        if (!res.ok) {
          throw new Error(data.detail || "Failed to fetch vendor bids");
        }

        // Store project data from API
        setProjectData({
          project_id: data.project_id,
          project_title: data.project_title,
          total_vendors: data.total_vendors
        });

        // Map to UI format - show basic info initially
        const mapped = data.vendor_bids.map((v, idx) => ({
          id: v.id || idx + 1,
          name: v.vendor_name,
          technical: v.technical_score || 0,
          commercial: v.commercial_bid || 0,
          technicalWeighted: null,
          commercialWeighted: null,
          totalScore: null,
          rank: v.rank || null
        }));

        console.log('Mapped vendors:', mapped);
        setVendors(mapped);

      } catch (err) {
        console.error('Error fetching vendor bids:', err);
        
        // Fallback: use bids from workflowData if API fails
        if (workflowData?.bids) {
          console.log('Using fallback workflowData bids');
          const mapped = workflowData.bids
            .filter(b => b.status === 'Received')
            .map((b, idx) => ({
              id: idx + 1,
              name: b.vendor,
              technical: 0,
              commercial: 0,
              technicalWeighted: null,
              commercialWeighted: null,
              totalScore: null,
              rank: null
            }));
          setVendors(mapped);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchVendorBids();
  }, [projectId]);

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

  const runEvaluation = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing. Please ensure you came from the previous workflow step.");
        return;
      }

      setEvaluating(true);
      console.log("Running evaluation for project:", projectId);

      const res = await fetch(`http://localhost:8003/publish/vendor-evaluation/${projectId}`, {
        method: "POST"
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Evaluation failed");
        return;
      }

      console.log("Evaluation response:", data);

      // Store full evaluation data for later API submission
      setEvaluationData(data);

      // Map backend response to UI format with full evaluation data
      const mapped = data.vendor_bids.map((v, idx) => ({
        id: idx + 1,
        name: v.vendor_name,
        technical: v.technical_score,
        commercial: v.commercial_bid,
        technicalWeighted: v.tech_score,
        commercialWeighted: v.comm_score,
        totalScore: v.total_score,
        rank: v.rank
      }));

      setVendors(mapped);
      setEvaluationComplete(true);
      setSelectedVendor({
        name: data.winner.vendor_name,
        commercial: data.winner.commercial_bid
      });

    } catch (err) {
      console.error(err);
      alert("Server error while evaluating vendors: " + err.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleSubmit = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing.");
        return;
      }

      if (!evaluationData) {
        alert("Evaluation data missing. Please run evaluation first.");
        return;
      }

      setSubmitting(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('VENDOR EVALUATION - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Creating purchase order from evaluation...');

      // Prepare request body
      const payload = {
        project_id: projectId,
        project_title: projectTitle,
        winner: {
          vendor_name: evaluationData.winner.vendor_name,
          commercial_bid: evaluationData.winner.commercial_bid,
          publication_date: new Date().toISOString().split('T')[0]
        },
        vendor_bids: evaluationData.vendor_bids
      };

      console.log("Payload:", payload);

      const res = await fetch("http://localhost:8003/purchase/create-from-evaluation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to create purchase order");
        return;
      }

      console.log("Purchase order created:", data);

      // Update progress tracking - Mark Page 8 as complete
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

      // Pass data to next stage (PurchaseOrder)
      onComplete({ 
        evaluation: vendors, 
        selectedVendor,
        projectId: projectId,
        projectTitle: projectTitle,
        purchaseOrderData: data,
        evaluationData: evaluationData,
        // Progress tracking info
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      alert("Server error while creating purchase order: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-500/20 rounded-lg">
            <UserCheck size={24} className="text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Vendor Evaluation</h2>
            <p className="text-slate-400 text-sm">Stage 8 - Technical & Commercial Evaluation</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-amber-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-amber-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Project ID Info */}
      {projectId && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-6">
          <p className="text-blue-400 text-sm">
            Project ID: <span className="text-white font-mono">{projectId}</span>
            {projectTitle && (
              <span className="ml-4">Title: <span className="text-white">{projectTitle}</span></span>
            )}
            <span className="text-slate-500 ml-4">|</span>
            <span className="text-slate-400 ml-4">Bids Received (Page 7 ✓)</span>
          </p>
        </div>
      )}

      {/* Selected Vendors Table - Shows before evaluation */}
      {!evaluationComplete && (
        <div className="mb-6">
          <h3 className="text-psb-gold font-medium mb-4">Selected Vendors</h3>
          
          {loading ? (
            <div className="text-center py-8 bg-slate-700/20 rounded-lg">
              <p className="text-slate-400">Loading vendors...</p>
            </div>
          ) : vendors.length === 0 ? (
            <div className="text-center py-8 bg-slate-700/20 rounded-lg">
              <p className="text-slate-400">No vendors found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-600">
                    <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">S.No</th>
                    <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Vendor Name</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Technical Score (%)</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Commercial Bid</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map((vendor, index) => (
                    <tr key={vendor.id} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                      <td className="py-3 px-4 text-white">{index + 1}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Building size={16} className="text-slate-400" />
                          <span className="text-white font-medium">{vendor.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Star size={14} className="text-yellow-400" />
                          <span className="text-white">{vendor.technical}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center text-white">
                        {vendor.commercial > 0 ? formatCurrency(vendor.commercial) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Run Evaluation Button */}
          <div className="flex justify-center mt-6">
            <button
              onClick={runEvaluation}
              disabled={evaluating || loading || vendors.length === 0}
              className="px-6 py-3 bg-psb-gold text-slate-900 rounded-lg font-medium hover:bg-psb-gold/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {evaluating ? "Evaluating..." : "Run Evaluation"}
            </button>
          </div>
        </div>
      )}

      {/* Evaluation Results - Shows after evaluation */}
      {evaluationComplete && (
        <>
          {/* Evaluation Criteria */}
          <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
            <h3 className="text-psb-gold font-medium mb-3">Evaluation Methodology</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-blue-400 font-bold">70%</span>
                </div>
                <div>
                  <p className="text-white font-medium">Technical Score</p>
                  <p className="text-slate-400 text-xs">Based on technical evaluation marks</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <span className="text-green-400 font-bold">30%</span>
                </div>
                <div>
                  <p className="text-white font-medium">Commercial Score</p>
                  <p className="text-slate-400 text-xs">L1 based scoring (lowest = 100%)</p>
                </div>
              </div>
            </div>
          </div>

          {/* Full Evaluation Results Table */}
          <div className="mb-6">
            <h3 className="text-psb-gold font-medium mb-4">Evaluation Results</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-600">
                    <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Rank</th>
                    <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Vendor</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Technical (100)</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Commercial Bid</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Tech (70%)</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Comm (30%)</th>
                    <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Total Score</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map((vendor) => (
                    <tr 
                      key={vendor.id} 
                      className={`border-b border-slate-700/50 ${
                        vendor.rank === 1 ? 'bg-psb-green/10' : 'hover:bg-slate-700/20'
                      }`}
                    >
                      <td className="py-3 px-4">
                        {vendor.rank === 1 ? (
                          <Award size={20} className="text-psb-gold" />
                        ) : (
                          <span className="text-white">{vendor.rank || '-'}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-white font-medium">{vendor.name}</span>
                        {vendor.rank === 1 && (
                          <span className="ml-2 px-2 py-0.5 bg-psb-gold/20 text-psb-gold text-xs rounded">L1</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Star size={14} className="text-yellow-400" />
                          <span className="text-white">{vendor.technical}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center text-white">{formatCurrency(vendor.commercial)}</td>
                      <td className="py-3 px-4 text-center text-blue-400">
                        {vendor.technicalWeighted?.toFixed(1)}
                      </td>
                      <td className="py-3 px-4 text-center text-green-400">
                        {vendor.commercialWeighted?.toFixed(1)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`font-bold ${vendor.rank === 1 ? 'text-psb-gold' : 'text-white'}`}>
                          {vendor.totalScore?.toFixed(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* L1 Declaration */}
          {selectedVendor && (
            <div className="bg-psb-green/10 border border-psb-green/30 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-3">
                <Award size={24} className="text-psb-gold" />
                <div>
                  <p className="text-psb-green font-medium">L1 Vendor Declared</p>
                  <p className="text-white text-lg font-semibold">{selectedVendor.name}</p>
                  <p className="text-slate-400 text-sm">Commercial Bid: {formatCurrency(selectedVendor.commercial)}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-amber-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!evaluationComplete || submitting}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {submitting ? "Creating PO..." : "Confirm L1 & Issue Purchase Order"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default VendorEvaluation;
