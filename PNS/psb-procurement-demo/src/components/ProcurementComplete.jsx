import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, Download, RotateCcw, Award, Calendar, Building, 
  FileText, ShoppingCart, Loader2, Home, Package, CreditCard, Shield
} from 'lucide-react';

function ProcurementComplete({ requirement, workflowData, onReset }) {
  const [purchaseData, setPurchaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  // Page tracking - This is Page 11 (FINAL PAGE) - Completion Screen
  const PAGE_INFO = {
    currentPage: 11,
    pageName: 'Procurement Complete',
    nextPage: null,
    nextPageName: 'Dashboard'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 10,           // case 10 in App.js (final)
    currentComponent: 'ProcurementComplete',
    nextStage: null,            // No next stage - workflow complete
    nextComponent: null,
    nextPageName: 'Dashboard'
  };

  // Get project ID
  const projectId = workflowData?.projectId || 
                    requirement?.project_id || 
                    requirement?.reqId || 
                    requirement?.projectId;

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

  // Mark navigation as complete
  const markNavigationComplete = async (projId) => {
    try {
      console.log('Marking navigation as complete for project:', projId);
      const response = await fetch(`http://localhost:8003/requirements/navigation/${projId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_stage: 11,  // Stage 11 = Complete
          current_page_component: 'Complete',
          current_page_name: 'Workflow Complete'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Navigation marked as complete:', data);
        return data;
      }
    } catch (error) {
      console.error('Error marking navigation complete:', error);
    }
    return null;
  };

  // Fetch purchase data and mark as complete on component mount
  useEffect(() => {
    const initializeCompletionPage = async () => {
      if (!projectId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Log page tracking info
        console.log('='.repeat(60));
        console.log('PROCUREMENT COMPLETE - PAGE TRACKING (FINAL)');
        console.log('='.repeat(60));
        console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
        console.log(`Project ID: ${projectId}`);
        console.log('-'.repeat(60));

        // Step 1: Fetch purchase data
        console.log('Step 1: Fetching purchase data...');
        const response = await fetch(`http://localhost:8003/purchase/${projectId}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Purchase data fetched:', data);
          setPurchaseData(data);
        } else {
          console.error('Failed to fetch purchase data');
        }

        // Step 2: Update progress tracking - Mark Page 11 as complete (100%)
        console.log('-'.repeat(60));
        console.log('Step 2: Updating progress tracking...');
        const progressData = await updateProgress(projectId, PAGE_INFO.currentPage);
        
        if (progressData) {
          console.log(`  Current Page: ${progressData.current_page}`);
          console.log(`  Overall Progress: ${progressData.overall_progress}%`);
          console.log(`  Status: ${progressData.status}`);
        }

        // Step 3: Mark navigation as complete
        console.log('-'.repeat(60));
        console.log('Step 3: Marking navigation as complete...');
        const navData = await markNavigationComplete(projectId);
        
        if (navData) {
          console.log('  Navigation marked as COMPLETE');
        }

        // Final summary
        console.log('-'.repeat(60));
        console.log('');
        console.log('  ╔══════════════════════════════════════════════════════╗');
        console.log('  ║     🎉 WORKFLOW COMPLETED SUCCESSFULLY! 🎉          ║');
        console.log('  ║     All pages have been completed.                  ║');
        console.log('  ║     Overall Progress: 100%                          ║');
        console.log('  ╚══════════════════════════════════════════════════════╝');
        console.log('='.repeat(60));

      } catch (error) {
        console.error('Error initializing completion page:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeCompletionPage();
  }, [projectId]);

  // Format currency
  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', 
      currency: 'INR', 
      maximumFractionDigits: 0 
    }).format(amount);
  };

  // Download PO
  const handleDownloadPO = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      setDownloading(true);
      const downloadUrl = `http://localhost:8003/purchase/download/${projectId}`;
      window.open(downloadUrl, "_blank");
    } catch (err) {
      console.error(err);
      alert("Error downloading PO: " + err.message);
    } finally {
      setDownloading(false);
    }
  };

  // Download all agreements
  const handleDownloadAgreements = async () => {
    try {
      if (!projectId) {
        alert("Project ID missing");
        return;
      }

      const downloadUrl = `http://localhost:8003/purchase/agreements/${projectId}`;
      window.open(downloadUrl, "_blank");
    } catch (err) {
      console.error(err);
      alert("Error downloading agreements: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-center py-16">
          <Loader2 size={48} className="text-psb-green animate-spin" />
          <span className="text-slate-400 ml-4">Loading procurement details...</span>
        </div>
      </div>
    );
  }

  const poData = purchaseData?.purchase_data;

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-psb-green/50 rounded-xl p-6">
      {/* Header with Page Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-psb-green/20 rounded-lg">
            <CheckCircle size={24} className="text-psb-green" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Procurement Complete</h2>
            <p className="text-slate-400 text-sm">Stage 11 - Workflow Completed Successfully</p>
          </div>
        </div>
        
        {/* Step Indicator - All Complete */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-psb-green text-sm font-medium">Complete</span>
          <span className="text-slate-500 text-sm">100%</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-psb-green"
                title={`Step ${i + 1} ✓`}
              />
            ))}
          </div>
        </div>
        
        <span className="px-3 py-1 bg-psb-green/20 text-psb-green rounded-full text-sm font-medium">
          ✓ Completed
        </span>
      </div>

      {/* Success Header */}
      <div className="text-center py-8 border-b border-slate-700 mb-6">
        <div className="w-24 h-24 bg-psb-green/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle size={48} className="text-psb-green" />
        </div>
        <h2 className="text-3xl font-bold text-psb-green mb-2">Procurement Complete!</h2>
        <p className="text-slate-400 mb-4">The entire procurement workflow has been successfully completed.</p>
        
        {/* Progress Complete Badge */}
        <div className="inline-flex items-center gap-2 bg-psb-green/20 border border-psb-green/50 rounded-full px-6 py-2">
          <CheckCircle size={18} className="text-psb-green" />
          <span className="text-psb-green font-medium">All 10 Stages Completed</span>
          <span className="text-psb-green">•</span>
          <span className="text-psb-green font-bold">100%</span>
        </div>
      </div>

      {/* Project Info from Previous Page */}
      {projectId && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={18} className="text-blue-400" />
            <span className="text-blue-400 font-medium">Project Information</span>
          </div>
          <p className="text-blue-400 text-sm">
            Project ID: <span className="text-white font-mono">{projectId}</span>
            {(purchaseData?.project_title || requirement?.title) && (
              <span className="ml-4">Title: <span className="text-white">{purchaseData?.project_title || requirement?.title}</span></span>
            )}
            <span className="text-slate-500 ml-4">|</span>
            <span className="text-slate-400 ml-4">Contract Signed (Page 10 ✓)</span>
          </p>
        </div>
      )}

      {/* Purchase Order Details */}
      {poData && (
        <div className="bg-psb-green/10 border border-psb-green/30 rounded-lg p-5 mb-6">
          <h3 className="text-psb-green font-medium mb-4 flex items-center gap-2">
            <ShoppingCart size={20} />
            Purchase Order Details
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <p className="text-slate-400 text-xs uppercase">PO Number</p>
              <p className="text-white font-mono font-medium">{poData.purchase_order_number}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Vendor</p>
              <div className="flex items-center gap-2">
                <Building size={16} className="text-psb-gold" />
                <p className="text-white font-medium">{poData.vendor}</p>
              </div>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">PO Value</p>
              <p className="text-psb-green font-bold text-xl">{formatCurrency(poData.po_value)}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Delivery Period</p>
              <div className="flex items-center gap-2">
                <Package size={16} className="text-blue-400" />
                <p className="text-white">{poData.delivery_period}</p>
              </div>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Payment Terms</p>
              <div className="flex items-center gap-2">
                <CreditCard size={16} className="text-yellow-400" />
                <p className="text-white">{poData.payment_terms}</p>
              </div>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase">Warranty Period</p>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-cyan-400" />
                <p className="text-white">{poData.warranty_period}</p>
              </div>
            </div>
            <div className="md:col-span-2 lg:col-span-3">
              <p className="text-slate-400 text-xs uppercase">Penalty Clause</p>
              <p className="text-white">{poData.penalty_clause}</p>
            </div>
          </div>
        </div>
      )}

      {/* Vendor Award Section */}
      {poData?.vendor && (
        <div className="bg-psb-gold/10 border border-psb-gold/30 rounded-lg p-5 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-psb-gold/20 rounded-full flex items-center justify-center">
              <Award size={32} className="text-psb-gold" />
            </div>
            <div>
              <p className="text-psb-gold font-medium">Contract Awarded To</p>
              <p className="text-white text-2xl font-semibold">{poData.vendor}</p>
              <p className="text-slate-400 text-sm">Contract Value: {formatCurrency(poData.po_value)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Download Section */}
      <div className="bg-slate-700/30 rounded-lg p-5 mb-6">
        <h3 className="text-psb-gold font-medium mb-4 flex items-center gap-2">
          <Download size={20} />
          Download Documents
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleDownloadPO}
            disabled={downloading || !projectId}
            className="flex items-center justify-center gap-3 p-4 bg-psb-green/20 border border-psb-green/30 hover:bg-psb-green/30 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            <ShoppingCart size={20} className="text-psb-green" />
            <div className="text-left">
              <span className="text-white font-medium block">Purchase Order</span>
              {poData?.po_filename && (
                <span className="text-slate-400 text-xs">{poData.po_filename}</span>
              )}
            </div>
            <Download size={18} className="text-psb-green ml-auto" />
          </button>
          <button
            onClick={handleDownloadAgreements}
            disabled={!projectId}
            className="flex items-center justify-center gap-3 p-4 bg-blue-500/20 border border-blue-500/30 hover:bg-blue-500/30 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            <FileText size={20} className="text-blue-400" />
            <div className="text-left">
              <span className="text-white font-medium block">All Agreements</span>
              <span className="text-slate-400 text-xs">MSA, SLA, NDA, DPA</span>
            </div>
            <Download size={18} className="text-blue-400 ml-auto" />
          </button>
        </div>
      </div>

      {/* Workflow Completion Summary */}
      <div className="bg-slate-700/30 rounded-lg p-5 mb-6">
        <h3 className="text-psb-gold font-medium mb-4">Workflow Stages Completed</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {[
            { num: 1, name: 'Requirement' },
            { num: 2, name: 'Analysis' },
            { num: 3, name: 'Tech Review' },
            { num: 4, name: 'RFP Draft' },
            { num: 5, name: 'Approval' },
            { num: 6, name: 'Publish' },
            { num: 7, name: 'Bids' },
            { num: 8, name: 'Evaluation' },
            { num: 9, name: 'PO' },
            { num: 10, name: 'Contract' }
          ].map((stage) => (
            <div key={stage.num} className="flex items-center gap-2 p-2 bg-psb-green/10 border border-psb-green/20 rounded">
              <div className="w-5 h-5 bg-psb-green rounded-full flex items-center justify-center">
                <CheckCircle size={12} className="text-white" />
              </div>
              <span className="text-psb-green text-xs font-medium">{stage.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center pt-6 border-t border-slate-700">
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 px-8 py-4 bg-psb-green hover:bg-psb-green-light text-white rounded-lg transition-all duration-200 font-medium text-lg shadow-lg shadow-psb-green/20"
        >
          <Home size={20} />
          Back to Dashboard
        </button>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center justify-center gap-2 px-8 py-4 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all duration-200 font-medium"
        >
          <RotateCcw size={20} />
          Start New Procurement
        </button>
      </div>

      {/* Footer Note */}
      <div className="mt-8 text-center">
        <p className="text-slate-500 text-sm">
          This procurement has been successfully completed and all documents are ready for download.
        </p>
        <p className="text-slate-600 text-xs mt-2">
          Completed on {new Date().toLocaleDateString('en-IN', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })} at {new Date().toLocaleTimeString('en-IN')}
        </p>
      </div>
    </div>
  );
}

export default ProcurementComplete;
