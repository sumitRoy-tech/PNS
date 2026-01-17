import React, { useState } from 'react';
import { Send, ArrowRight, Globe, Calendar, ExternalLink } from 'lucide-react';

function PublishRFP({ requirement, workflowData, onComplete }) {
  const [publication, setPublication] = useState({
    publishDate: new Date().toISOString().split('T')[0],
    portals: [],
    prebidDate: '',
    lastQueryDate: '',
    bidOpeningDate: '',
  });

  const [loading, setLoading] = useState(false);

  // Page tracking - This is Page 6 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 6,
    pageName: 'Publish RFP',
    nextPage: 7,
    nextPageName: 'Receive Bids'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 5,           // case 5 in App.js
    currentComponent: 'PublishRFP',
    nextStage: 6,              // case 6 in App.js
    nextComponent: 'ReceiveBids',
    nextPageName: 'Receive Bids'
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
  const projectId = requirement?.project_id || requirement?.reqId || requirement?.id || requirement?.projectId;

  const portalOptions = [
    { id: 'bank', name: 'Bank Website', url: 'www.psbindia.com' },
    { id: 'gem', name: 'GeM Portal', url: 'gem.gov.in' },
    { id: 'cppp', name: 'CPPP', url: 'eprocure.gov.in' },
    { id: 'newspaper', name: 'Newspaper Publication', url: '-' },
  ];

  const togglePortal = (portalId) => {
    if (publication.portals.includes(portalId)) {
      setPublication({...publication, portals: publication.portals.filter(p => p !== portalId)});
    } else {
      setPublication({...publication, portals: [...publication.portals, portalId]});
    }
  };

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
      console.log('PUBLISH RFP - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Publishing RFP to selected portals...');

      const payload = {
        project_id: projectId,
        bank_website: publication.portals.includes("bank") ? 1 : 0,
        gem_portal: publication.portals.includes("gem") ? 1 : 0,
        cppp: publication.portals.includes("cppp") ? 1 : 0,
        newspaper_publication: publication.portals.includes("newspaper") ? 1 : 0,
        publication_date: publication.publishDate || null,
        pre_bid_meeting: publication.prebidDate || null,
        query_last_date: publication.lastQueryDate || null,
        bid_opening_date: publication.bidOpeningDate || null
      };

      const res = await fetch("http://localhost:8003/publish/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to publish RFP");
        return;
      }

      console.log("Publish success:", data);

      // Update progress tracking - Mark Page 6 as complete
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

      // Move to next stage
      onComplete({ 
        publication,
        // Progress tracking info
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      alert("Server error while publishing RFP");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-cyan-500/20 rounded-lg">
            <Send size={24} className="text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Publish RFP</h2>
            <p className="text-slate-400 text-sm">Stage 6 - Make RFP Live for Vendor Submissions</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-cyan-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-cyan-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
        
        <span className="px-3 py-1 bg-psb-green/20 text-psb-green rounded-full text-sm font-medium">
          Approved ✓
        </span>
      </div>

      {/* RFP Summary */}
      <div className="bg-psb-green/10 border border-psb-green/30 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2 mb-2">
          <Globe size={18} className="text-psb-green" />
          <h3 className="text-psb-green font-medium">RFP Ready for Publication (Page 5 Approved)</h3>
        </div>
        <p className="text-white">{requirement?.title}</p>
        <p className="text-slate-400 text-sm">Project ID: <span className="font-mono">{projectId}</span></p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Publication Portals */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Select Publication Portals</h3>
          <div className="space-y-3">
            {portalOptions.map(portal => (
              <label 
                key={portal.id}
                className={`flex items-center gap-3 p-4 rounded-lg cursor-pointer border transition-all ${
                  publication.portals.includes(portal.id)
                    ? 'bg-psb-green/10 border-psb-green/50'
                    : 'bg-slate-700/30 border-slate-600 hover:border-slate-500'
                }`}
              >
                <input
                  type="checkbox"
                  checked={publication.portals.includes(portal.id)}
                  onChange={() => togglePortal(portal.id)}
                  className="w-5 h-5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
                />
                <div className="flex-1">
                  <span className="text-white font-medium">{portal.name}</span>
                  <p className="text-slate-400 text-xs flex items-center gap-1">
                    {portal.url !== '-' && <ExternalLink size={10} />}
                    {portal.url}
                  </p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Key Dates */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Key Dates</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-slate-300 text-sm mb-1 flex items-center gap-2">
                <Calendar size={14} /> Publication Date
              </label>
              <input
                type="date"
                value={publication.publishDate}
                onChange={(e) => setPublication({...publication, publishDate: e.target.value})}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
              />
            </div>
            <div>
              <label className="block text-slate-300 text-sm mb-1 flex items-center gap-2">
                <Calendar size={14} /> Pre-Bid Meeting Date
              </label>
              <input
                type="date"
                value={publication.prebidDate}
                onChange={(e) => setPublication({...publication, prebidDate: e.target.value})}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
              />
            </div>
            <div>
              <label className="block text-slate-300 text-sm mb-1 flex items-center gap-2">
                <Calendar size={14} /> Last Date for Queries
              </label>
              <input
                type="date"
                value={publication.lastQueryDate}
                onChange={(e) => setPublication({...publication, lastQueryDate: e.target.value})}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
              />
            </div>
            <div>
              <label className="block text-slate-300 text-sm mb-1 flex items-center gap-2">
                <Calendar size={14} /> Bid Opening Date
              </label>
              <input
                type="date"
                value={publication.bidOpeningDate}
                onChange={(e) => setPublication({...publication, bidOpeningDate: e.target.value})}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-cyan-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={publication.portals.length === 0 || loading}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {loading ? "Publishing..." : "Publish RFP & Proceed"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default PublishRFP;
