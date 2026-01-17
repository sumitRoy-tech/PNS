import React, { useState, useEffect } from 'react';
import { Inbox, ArrowRight, Building, Check, X, FileCheck } from 'lucide-react';

function ReceiveBids({ requirement, workflowData, onComplete }) {
  const [bids, setBids] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [bidOpeningDone, setBidOpeningDone] = useState(false);

  // Page tracking - This is Page 7 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 7,
    pageName: 'Receive Bids',
    nextPage: 8,
    nextPageName: 'Vendor Evaluation'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 6,           // case 6 in App.js
    currentComponent: 'ReceiveBids',
    nextStage: 7,              // case 7 in App.js
    nextComponent: 'VendorEvaluation',
    nextPageName: 'Vendor Evaluation'
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

  // Get project_id from workflowData (passed from TechnicalReview -> TenderDrafting) or requirement
  const projectId = workflowData?.generatedRfp?.projectId || 
                    workflowData?.projectId || 
                    requirement?.project_id || 
                    requirement?.reqId ||
                    requirement?.projectId;

  // Fetch vendors on component mount
  useEffect(() => {
    const fetchVendors = async () => {
      try {
        setLoading(true);
        const res = await fetch("http://localhost:8003/publish/get_vendors");
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail || "Failed to fetch vendors");
        }

        const mapped = data.vendors.map((v, idx) => ({
          id: idx + 1,
          vendor: v.vendor_name,
          technicalSubmitted: v["Technical Bid"] === 1,
          commercialSubmitted: v["Commercial Bid"] === 1,
          emdSubmitted: v["EMD"] === 1,
          status: v.status
        }));
        setBids(mapped);
      } catch (err) {
        console.error(err);
        alert("Failed to load vendors: " + err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchVendors();
  }, []);

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
        alert("Project ID missing. Please ensure you came from the previous workflow step.");
        return;
      }

      setSubmitting(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('RECEIVE BIDS - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Submitting vendor bids...');

      const payload = {
        project_id: projectId,
        vendors: bids.map(b => ({
          vendor_name: b.vendor,
          "Technical Bid": b.technicalSubmitted ? 1 : 0,
          "Commercial Bid": b.commercialSubmitted ? 1 : 0,
          "EMD": b.emdSubmitted ? 1 : 0,
          status: b.status
        }))
      };

      console.log("Payload:", payload);

      const res = await fetch("http://localhost:8003/publish/vendor-bids/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to submit vendor bids");
        return;
      }

      console.log("Vendor bids submitted:", data);

      // Update progress tracking - Mark Page 7 as complete
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

      // Pass data to next stage (VendorEvaluation)
      onComplete({ 
        bids, 
        bidOpeningDone: true,
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
      alert("Error submitting vendor bids: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const completeBids = bids.filter(b => b.status === 'Received').length;

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-500/20 rounded-lg">
            <Inbox size={24} className="text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Receive Bids</h2>
            <p className="text-slate-400 text-sm">Stage 7 - Technical & Commercial Bid Collection</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-indigo-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-indigo-400 animate-pulse' : 
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
            <span className="text-slate-500 ml-4">|</span>
            <span className="text-slate-400 ml-4">RFP Published (Page 6 ✓)</span>
          </p>
        </div>
      )}

      {/* Bid Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-700/30 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-white">{bids.length}</p>
          <p className="text-slate-400 text-sm">Total Bids</p>
        </div>
        <div className="bg-psb-green/10 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-psb-green">{completeBids}</p>
          <p className="text-slate-400 text-sm">Complete Bids</p>
        </div>
        <div className="bg-yellow-500/10 rounded-lg p-4 text-center">
          <p className="text-3xl font-bold text-yellow-400">{bids.length - completeBids}</p>
          <p className="text-slate-400 text-sm">Incomplete Bids</p>
        </div>
      </div>

      {/* Bid Register */}
      <div className="mb-6">
        <h3 className="text-psb-gold font-medium mb-4">Bid Register</h3>
        
        {loading ? (
          <div className="text-center py-8">
            <p className="text-slate-400">Loading vendors...</p>
          </div>
        ) : bids.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-slate-400">No vendors found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">S.No</th>
                  <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Vendor Name</th>
                  <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Technical Bid</th>
                  <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Commercial Bid</th>
                  <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">EMD</th>
                  <th className="text-center py-3 px-4 text-slate-400 text-sm font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((bid, index) => (
                  <tr key={bid.id} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                    <td className="py-3 px-4 text-white">{index + 1}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Building size={16} className="text-slate-400" />
                        <span className="text-white">{bid.vendor}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {bid.technicalSubmitted ? (
                        <Check size={18} className="text-psb-green mx-auto" />
                      ) : (
                        <X size={18} className="text-red-400 mx-auto" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {bid.commercialSubmitted ? (
                        <Check size={18} className="text-psb-green mx-auto" />
                      ) : (
                        <X size={18} className="text-red-400 mx-auto" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {bid.emdSubmitted ? (
                        <Check size={18} className="text-psb-green mx-auto" />
                      ) : (
                        <X size={18} className="text-red-400 mx-auto" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        bid.status === 'Received' 
                          ? 'bg-psb-green/20 text-psb-green' 
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {bid.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bid Opening Confirmation */}
      <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={bidOpeningDone}
            onChange={(e) => setBidOpeningDone(e.target.checked)}
            className="w-5 h-5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
          />
          <div className="flex items-center gap-2">
            <FileCheck size={18} className="text-psb-gold" />
            <span className="text-white">Bid Opening Completed in presence of Committee Members</span>
          </div>
        </label>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-indigo-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!bidOpeningDone || loading || bids.length === 0 || submitting}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {submitting ? "Submitting..." : "Proceed to Vendor Evaluation"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default ReceiveBids;
