import React, { useState } from 'react';
import { ShoppingCart, ArrowRight, FileText, Download, Calendar } from 'lucide-react';

function PurchaseOrder({ requirement, workflowData, onComplete }) {
  // Get data from workflowData (passed from VendorEvaluation)
  const purchaseOrderData = workflowData?.purchaseOrderData;
  const selectedVendor = workflowData?.selectedVendor || { name: 'TCS Ltd.', commercial: 24500000 };
  const projectId = workflowData?.projectId || requirement?.reqId || requirement?.project_id;
  const projectTitle = workflowData?.projectTitle || requirement?.title;
  
  // Page tracking - This is Page 9 in the 10-page workflow
  const PAGE_INFO = {
    currentPage: 9,
    pageName: 'Purchase Order',
    nextPage: 10,
    nextPageName: 'Contract Signing'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 8,           // case 8 in App.js
    currentComponent: 'PurchaseOrder',
    nextStage: 9,              // case 9 in App.js
    nextComponent: 'ContractSigning',
    nextPageName: 'Contract Signing'
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

  // Use PO data from API response if available
  const [poDetails, setPoDetails] = useState({
    poNumber: purchaseOrderData?.po_number || `PO-${projectId}-${String(Math.floor(Math.random() * 10000)).padStart(4, '0')}`,
    poDate: purchaseOrderData?.po_date || new Date().toISOString().split('T')[0],
    deliveryPeriod: purchaseOrderData?.delivery_period || '12 weeks',
    paymentTerms: purchaseOrderData?.payment_terms || '30 Days from Delivery',
    warrantyPeriod: purchaseOrderData?.warranty_period || '3 year',
    penaltyClause: purchaseOrderData?.penalty_clause || '1% per week delay, max 10%',
  });

  const [confirmations, setConfirmations] = useState({
    termsVerified: false,
    budgetAllocated: false,
    vendorNotified: false,
  });

  const [submitting, setSubmitting] = useState(false);
  const [downloading, setDownloading] = useState(false);

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

  const handleDownloadPO = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setDownloading(true);
      
      // Download PO using project_id
      const downloadUrl = `http://localhost:8003/purchase/download/${projectId}`;
      window.open(downloadUrl, "_blank");

    } catch (err) {
      console.error(err);
      alert("Error downloading PO: " + err.message);
    } finally {
      setDownloading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setSubmitting(true);

      // Log page tracking info
      console.log('='.repeat(60));
      console.log('PURCHASE ORDER - PAGE TRACKING');
      console.log('='.repeat(60));
      console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
      console.log(`Project ID: ${projectId}`);
      console.log('-'.repeat(60));
      console.log('Step 1: Submitting PO...');

      // Step 1: Submit PO
      const payload = {
        project_id: projectId,
        purchase_order_number: poDetails.poNumber,
        vendor: selectedVendor.name,
        po_value: selectedVendor.commercial,
        delivery_period: poDetails.deliveryPeriod,
        payment_terms: poDetails.paymentTerms,
        warranty_period: poDetails.warrantyPeriod,
        penalty_clause: poDetails.penaltyClause
      };

      console.log("Payload:", payload);

      const res = await fetch("http://localhost:8003/purchase/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.detail || "Failed to submit purchase order");
        return;
      }

      console.log("PO submitted:", data);

      // Step 2: Generate Agreements
      console.log('-'.repeat(60));
      console.log('Step 2: Generating agreements...');

      const agreementRes = await fetch(`http://localhost:8003/purchase/generate-agreements/${projectId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const agreementData = await agreementRes.json();

      if (!agreementRes.ok) {
        alert(agreementData.detail || "Failed to generate agreements");
        return;
      }

      console.log("Agreements generated:", agreementData);
      console.log("Data sources used:", agreementData.data_sources_used);

      // Update progress tracking - Mark Page 9 as complete
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

      // Pass data to next stage (ContractSigning)
      onComplete({ 
        purchaseOrder: poDetails,
        purchaseOrderResponse: data,
        agreementData: agreementData,
        projectId: projectId,
        projectTitle: projectTitle,
        selectedVendor: selectedVendor,
        // Progress tracking info
        completedPage: PAGE_INFO.currentPage,
        completedPageName: PAGE_INFO.pageName,
        nextPage: PAGE_INFO.nextPage,
        nextPageName: PAGE_INFO.nextPageName,
        progress: progressData
      });

    } catch (err) {
      console.error(err);
      alert("Error: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const allConfirmed = Object.values(confirmations).every(v => v);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-500/20 rounded-lg">
            <ShoppingCart size={24} className="text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Purchase Order</h2>
            <p className="text-slate-400 text-sm">Stage 9 - Issue PO to Selected Vendor</p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-emerald-400 text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < PAGE_INFO.currentPage - 1 ? 'bg-psb-green' : 
                  i === PAGE_INFO.currentPage - 1 ? 'bg-emerald-400 animate-pulse' : 
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
            <span className="text-slate-400 ml-4">L1 Vendor Selected (Page 8 ✓)</span>
          </p>
        </div>
      )}

      {/* PO Header */}
      <div className="bg-slate-700/30 rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-slate-400 text-xs uppercase">Purchase Order Number</p>
            <p className="text-white font-mono text-xl">{poDetails.poNumber}</p>
          </div>
          <div className="text-right">
            <p className="text-slate-400 text-xs uppercase">Date</p>
            <p className="text-white">{poDetails.poDate}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-600">
          <div>
            <p className="text-slate-400 text-xs uppercase">Vendor</p>
            <p className="text-white font-medium text-lg">{selectedVendor.name}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs uppercase">PO Value</p>
            <p className="text-psb-green font-bold text-xl">{formatCurrency(selectedVendor.commercial)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PO Terms */}
        <div className="space-y-4">
          <h3 className="text-psb-gold font-medium">Purchase Order Terms</h3>
          
          <div>
            <label className="block text-slate-300 text-sm mb-1">Delivery Period</label>
            <select
              value={poDetails.deliveryPeriod}
              onChange={(e) => setPoDetails({...poDetails, deliveryPeriod: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            >
              <option value="4 weeks">4 Weeks</option>
              <option value="8 weeks">8 Weeks</option>
              <option value="12 weeks">12 Weeks</option>
              <option value="16 weeks">16 Weeks</option>
              <option value="24 weeks">24 Weeks</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">Payment Terms</label>
            <select
              value={poDetails.paymentTerms}
              onChange={(e) => setPoDetails({...poDetails, paymentTerms: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            >
              <option value="100% Advance">100% Advance</option>
              <option value="50% Advance, 50% on Delivery">50% Advance, 50% on Delivery</option>
              <option value="30 Days from Delivery">30 Days from Delivery</option>
              <option value="60 Days from Delivery">60 Days from Delivery</option>
              <option value="Milestone Based">Milestone Based</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">Warranty Period</label>
            <select
              value={poDetails.warrantyPeriod}
              onChange={(e) => setPoDetails({...poDetails, warrantyPeriod: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            >
              <option value="1 year">1 Year</option>
              <option value="2 year">2 Years</option>
              <option value="3 year">3 Years</option>
              <option value="5 year">5 Years</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">Penalty Clause</label>
            <input
              type="text"
              value={poDetails.penaltyClause}
              onChange={(e) => setPoDetails({...poDetails, penaltyClause: e.target.value})}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white"
            />
          </div>
        </div>

        {/* Confirmations & Actions */}
        <div>
          <h3 className="text-psb-gold font-medium mb-4">Pre-Issue Checklist</h3>
          <div className="space-y-3 mb-6">
            {[
              { key: 'termsVerified', label: 'All terms and conditions verified by Legal' },
              { key: 'budgetAllocated', label: 'Budget allocated and approved' },
              { key: 'vendorNotified', label: 'Vendor notified of award' },
            ].map(item => (
              <label 
                key={item.key}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition-all ${
                  confirmations[item.key]
                    ? 'bg-psb-green/10 border-psb-green/50'
                    : 'bg-slate-700/30 border-slate-600 hover:border-slate-500'
                }`}
              >
                <input
                  type="checkbox"
                  checked={confirmations[item.key]}
                  onChange={(e) => setConfirmations({...confirmations, [item.key]: e.target.checked})}
                  className="w-5 h-5 rounded border-slate-500 text-psb-green focus:ring-psb-green"
                />
                <span className="text-slate-300 text-sm">{item.label}</span>
              </label>
            ))}
          </div>

          {/* Download PO Button */}
          <button 
            onClick={handleDownloadPO}
            disabled={downloading || !projectId}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            <Download size={18} />
            {downloading ? "Downloading..." : "Download Draft PO"}
          </button>
        </div>
      </div>

      {/* Submit with Progress Info */}
      <div className="flex justify-between items-center mt-6 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm">
          <span>Completing this will mark </span>
          <span className="text-emerald-400 font-medium">Page {PAGE_INFO.currentPage}</span>
          <span> as done → Next: </span>
          <span className="text-slate-400">{PAGE_INFO.nextPageName}</span>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!allConfirmed || submitting}
          className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 font-medium"
        >
          {submitting ? "Submitting & Generating Agreements..." : "Issue PO & Proceed to Contract"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

export default PurchaseOrder;
