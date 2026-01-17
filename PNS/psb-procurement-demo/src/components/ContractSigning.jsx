import React, { useState } from 'react';
import { FileSignature, CheckCircle, Download, RotateCcw, Award, Calendar, Building, ArrowRight } from 'lucide-react';

function ContractSigning({ requirement, workflowData, onComplete }) {
  // Get data from previous pages
  const selectedVendor = workflowData?.selectedVendor || { name: 'TCS Ltd.', commercial: 24500000 };
  const poDetails = workflowData?.purchaseOrder || {};
  const agreementData = workflowData?.agreementData;
  const projectId = workflowData?.projectId || requirement?.reqId || requirement?.project_id || requirement?.projectId;
  const projectTitle = workflowData?.projectTitle || requirement?.title;
  const purchaseOrderResponse = workflowData?.purchaseOrderResponse;

  // Page tracking - This is Page 10 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 10,
    pageName: 'Contract Signing',
    nextPage: 11,
    nextPageName: 'Procurement Complete'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 9,           // case 9 in App.js
    currentComponent: 'ContractSigning',
    nextStage: 10,             // case 10 in App.js (ProcurementComplete)
    nextComponent: 'ProcurementComplete',
    nextPageName: 'Procurement Complete'
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
  
  const [signatures, setSignatures] = useState({
    vendorSigned: false,
    bankSigned: false,
    witnessSigned: false,
  });

  const [downloading, setDownloading] = useState({});
  const [completing, setCompleting] = useState(false);

  // Document download configurations
  const documents = [
    { key: 'msa', name: 'Master Service Agreement', endpoint: 'msa' },
    { key: 'sla', name: 'Service Level Agreement (SLA)', endpoint: 'sla' },
    { key: 'nda', name: 'Non-Disclosure Agreement', endpoint: 'nda' },
    { key: 'dpa', name: 'Data Processing Agreement', endpoint: 'dpa' },
    { key: 'annexures', name: 'Annexures & Schedules', endpoint: 'annexures' },
  ];

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

  const handleDownloadDocument = async (endpoint, key) => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setDownloading(prev => ({ ...prev, [key]: true }));
      
      const downloadUrl = `http://localhost:8003/purchase/download/${endpoint}/${projectId}`;
      window.open(downloadUrl, "_blank");

    } catch (err) {
      console.error(err);
      alert("Error downloading document: " + err.message);
    } finally {
      setDownloading(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleDownloadAllDocuments = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setDownloading(prev => ({ ...prev, all: true }));
      
      const downloadUrl = `http://localhost:8003/purchase/agreements/${projectId}`;
      window.open(downloadUrl, "_blank");

    } catch (err) {
      console.error(err);
      alert("Error downloading documents: " + err.message);
    } finally {
      setDownloading(prev => ({ ...prev, all: false }));
    }
  };

  const handleComplete = async () => {
    try {
      setCompleting(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('CONTRACT SIGNING - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Next Page: ${PAGE_INFO.nextPage} - ${PAGE_INFO.nextPageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));

      // Update progress tracking - Mark Page 10 as complete (100%)
      const progressData = await updateProgress(projectId, PAGE_INFO.currentPage);

      // Update navigation to go to ProcurementComplete
      console.log('-'.repeat(60));
      console.log('UPDATING NAVIGATION:');
      console.log(`  From: Stage ${NAVIGATION.currentStage} (${NAVIGATION.currentComponent})`);
      console.log(`  To: Stage ${NAVIGATION.nextStage} (${NAVIGATION.nextComponent})`);
      
      const navData = await updateNavigation(projectId);
      if (navData) {
        console.log('  Navigation updated successfully');
      }

      // Progress summary
      console.log('-'.repeat(60));
      console.log('PROGRESS TRACKING:');
      if (progressData) {
        console.log(`  Current Page: ${progressData.current_page}`);
        console.log(`  Overall Progress: ${progressData.overall_progress}%`);
        console.log(`  Status: ${progressData.status}`);
      }
      console.log(`  Page ${PAGE_INFO.currentPage} (${PAGE_INFO.pageName}) → Moving to ${PAGE_INFO.nextPageName}`);
      console.log('='.repeat(60));

      // Call onComplete to navigate to ProcurementComplete (case 10)
      if (onComplete) {
        onComplete({
          contractSigned: true,
          projectId: projectId,
          projectTitle: projectTitle,
          signatures: signatures
        });
      }

    } catch (err) {
      console.error(err);
      alert("Error completing contract signing: " + err.message);
    } finally {
      setCompleting(false);
    }
  };

  const allSigned = Object.values(signatures).every(v => v);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-violet-500/20 rounded-lg">
            <FileSignature size={24} className="text-violet-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">SLA & Contract Signing</h2>
            <p className="text-slate-400 text-sm">Stage 10 - Final Documentation & Project Initiation</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-violet-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-violet-400 animate-pulse' : 
                  'bg-slate-600'
                }`}
                title={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>
        
        <span className="px-3 py-1 bg-violet-500/20 text-violet-400 rounded-full text-sm font-medium">
          Final Stage
        </span>
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
            <span className="text-slate-400 ml-4">PO Issued (Page 9 ✓)</span>
          </p>
        </div>
      )}

      {/* Agreement Info from API */}
      {agreementData && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <FileSignature size={18} className="text-green-400" />
            <span className="text-green-400 font-medium">Agreement Generated</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {agreementData.agreement_id && (
              <div>
                <p className="text-slate-400 text-xs">Agreement ID</p>
                <p className="text-white font-mono">{agreementData.agreement_id}</p>
              </div>
            )}
            {agreementData.generated_at && (
              <div>
                <p className="text-slate-400 text-xs">Generated At</p>
                <p className="text-white">{new Date(agreementData.generated_at).toLocaleString()}</p>
              </div>
            )}
            {agreementData.documents_count && (
              <div>
                <p className="text-slate-400 text-xs">Documents</p>
                <p className="text-white">{agreementData.documents_count}</p>
              </div>
            )}
            {agreementData.status && (
              <div>
                <p className="text-slate-400 text-xs">Status</p>
                <p className="text-white">{agreementData.status}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Contract Summary */}
      <div className="bg-slate-700/30 rounded-lg p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3">
            <Building size={20} className="text-psb-gold" />
            <div>
              <p className="text-slate-400 text-xs uppercase">Vendor</p>
              <p className="text-white font-medium">{selectedVendor.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Award size={20} className="text-psb-green" />
            <div>
              <p className="text-slate-400 text-xs uppercase">Contract Value</p>
              <p className="text-psb-green font-bold">{formatCurrency(selectedVendor.commercial)}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Calendar size={20} className="text-blue-400" />
            <div>
              <p className="text-slate-400 text-xs uppercase">Delivery Period</p>
              <p className="text-white">{poDetails.deliveryPeriod || '12 weeks'}</p>
            </div>
          </div>
        </div>

        {/* Additional PO Details */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-600">
          <div>
            <p className="text-slate-400 text-xs uppercase">PO Number</p>
            <p className="text-white font-mono">{poDetails.poNumber || '-'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs uppercase">Payment Terms</p>
            <p className="text-white">{poDetails.paymentTerms || '-'}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs uppercase">Warranty Period</p>
            <p className="text-white">{poDetails.warrantyPeriod || '-'}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contract Documents */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Contract Documents</h3>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.key} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileSignature size={18} className="text-slate-400" />
                  <span className="text-white text-sm">{doc.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-psb-green/20 text-psb-green text-xs rounded">Ready</span>
                  <button
                    onClick={() => handleDownloadDocument(doc.endpoint, doc.key)}
                    disabled={downloading[doc.key] || !projectId}
                    className="p-1.5 rounded hover:bg-slate-600 transition-colors disabled:opacity-50"
                  >
                    <Download 
                      size={16} 
                      className={`${downloading[doc.key] ? 'text-slate-500 animate-pulse' : 'text-slate-400 hover:text-white'}`} 
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Download All Button */}
          <button
            onClick={handleDownloadAllDocuments}
            disabled={downloading.all || !projectId}
            className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            <Download size={18} />
            {downloading.all ? "Downloading..." : "Download All Agreements"}
          </button>
        </div>

        {/* Signature Section */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Digital Signatures</h3>
          <div className="space-y-4">
            {[
              { key: 'vendorSigned', label: 'Vendor Authorized Signatory', role: 'CEO / Director' },
              { key: 'bankSigned', label: 'Bank Authorized Signatory', role: 'GM / DGM Procurement' },
              { key: 'witnessSigned', label: 'Witness', role: 'Legal Department' },
            ].map(item => (
              <label 
                key={item.key}
                className={`block p-4 rounded-lg cursor-pointer border transition-all ${
                  signatures[item.key]
                    ? 'bg-psb-green/10 border-psb-green/50'
                    : 'bg-slate-700/30 border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={signatures[item.key]}
                    onChange={(e) => setSignatures({...signatures, [item.key]: e.target.checked})}
                    className="w-5 h-5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
                  />
                  <div>
                    <p className="text-white font-medium">{item.label}</p>
                    <p className="text-slate-400 text-xs">{item.role}</p>
                  </div>
                  {signatures[item.key] && (
                    <CheckCircle size={20} className="text-psb-green ml-auto" />
                  )}
                </div>
              </label>
            ))}
          </div>

          {/* Stamp Paper Info */}
          <div className="mt-4 p-3 bg-blue-900/20 border border-blue-700/50 rounded-lg">
            <p className="text-blue-300 text-sm">
              <strong>Note:</strong> Contract to be executed on appropriate stamp paper as per applicable laws.
            </p>
          </div>
        </div>
      </div>

      {/* Complete Button with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-violet-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-psb-green font-medium">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleComplete}
          disabled={!allSigned || completing}
          className="flex items-center gap-2 px-8 py-4 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium text-lg shadow-lg shadow-psb-green/20"
        >
          {completing ? "Processing..." : "Complete Contract Signing"}
          <ArrowRight size={20} />
        </button>
      </div>
    </div>
  );
}

export default ContractSigning;
