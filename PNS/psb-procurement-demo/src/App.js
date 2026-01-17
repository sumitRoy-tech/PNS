import React, { useState } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import RequirementForm from './components/RequirementForm';
import FunctionalAnalysis from './components/FunctionalAnalysis';
import TechnicalReview from './components/TechnicalReview';
import TenderDrafting from './components/TenderDrafting';
import ApprovalGate from './components/ApprovalGate';
import PublishRFP from './components/PublishRFP';
import ReceiveBids from './components/ReceiveBids';
import VendorEvaluation from './components/VendorEvaluation';
import PurchaseOrder from './components/PurchaseOrder';
import ContractSigning from './components/ContractSigning';
import ProcurementComplete from './components/ProcurementComplete';
import WorkflowSidebar from './components/WorkflowSidebar';
import { stages } from './data/workflowData';

function App() {
  // View mode: 'dashboard' or 'workflow'
  const [viewMode, setViewMode] = useState('dashboard');
  
  // All requirements stored
  const [allRequirements, setAllRequirements] = useState([]);
  
  // Current active requirement index
  const [activeIndex, setActiveIndex] = useState(null);
  
  // Current stage in workflow (0 = form, 1-10 = stages)
  const [currentStage, setCurrentStage] = useState(0);
  
  // Approval status
  const [isApproved, setIsApproved] = useState(null);
  
  // Workflow data collected during stages
  const [workflowData, setWorkflowData] = useState({});

  // Get current requirement
  const currentRequirement = activeIndex !== null ? allRequirements[activeIndex] : null;

  // Start new requirement
  const handleNewRequirement = () => {
    setActiveIndex(null);
    setCurrentStage(0);
    setIsApproved(null);
    setWorkflowData({});
    setViewMode('workflow');
  };

  // View existing requirement
  const handleViewRequirement = (index) => {
    const req = allRequirements[index];
    setActiveIndex(index);
    setCurrentStage(req.stage || 1);
    setIsApproved(req.isApproved || null);
    setWorkflowData(req.workflowData || {});
    setViewMode('workflow');
  };

  // View project by ID from database (for Dashboard progress cards)
  const handleViewProjectById = async (projectId, currentPage, projectData) => {
    console.log('='.repeat(60));
    console.log('NAVIGATING TO PROJECT FROM DASHBOARD');
    console.log('='.repeat(60));
    console.log('Project ID:', projectId);
    console.log('Current Page from DB (progress):', currentPage);
    console.log('Project Data:', projectData);

    try {
      // Step 1: Fetch navigation state from the new navigation API
      console.log('-'.repeat(60));
      console.log('Step 1: Fetching navigation state...');
      
      const navResponse = await fetch(`http://localhost:8003/requirements/navigation/${projectId}`);
      const navData = await navResponse.json();
      
      console.log('Navigation API response:', navData);

      // Step 2: Fetch full project details
      console.log('-'.repeat(60));
      console.log('Step 2: Fetching project details...');
      
      const response = await fetch(`http://localhost:8003/requirements/project/${projectId}`);
      
      if (!response.ok) {
        console.error('Failed to fetch project details');
        alert('Failed to load project details');
        return;
      }

      const project = await response.json();
      console.log('Fetched project details:', project);

      // Check if project already exists in local state
      const existingIndex = allRequirements.findIndex(
        req => req.projectId === projectId || req.reqId === projectId
      );

      // Use navigation API stage if available, otherwise fallback to progress-based calculation
      let frontendStage;
      
      if (navData.found && navData.current_stage !== undefined) {
        // Use the stage from navigation API (this is the exact App.js case number)
        frontendStage = navData.current_stage;
        console.log('Using navigation API stage:', frontendStage);
        console.log('Component to render:', navData.current_page_component);
      } else {
        // Fallback: Calculate from progress current_page
        // Database current_page is 1-indexed, frontend stage is 0-indexed
        frontendStage = currentPage - 1;
        console.log('Fallback: Calculated stage from progress:', frontendStage);
      }
      
      // Handle completed workflows - ONLY use navigation stage, not overall_progress
      // Navigation stage 10 = ProcurementComplete, stage 11 = Workflow Complete
      // Do NOT check overall_progress as it can be 100% before ContractSigning is done
      if (frontendStage >= 11) {
        console.log('Workflow is fully complete - showing completion screen');
        frontendStage = 10; // Show ProcurementComplete
      }

      console.log('-'.repeat(60));
      console.log('NAVIGATION DECISION:');
      console.log('  Frontend Stage (case):', frontendStage);
      console.log('  Component:', navData.current_page_component || 'calculated');

      // Create requirement object from API data
      const reqFromApi = {
        projectId: project.project_id,
        reqId: project.project_id,
        title: project.title,
        department: project.department,
        category: project.category,
        priority: project.priority,
        estimatedValue: `₹${(project.estimated_amount / 10000000).toFixed(2)} Cr`,
        justification: project.business_justification,
        specifications: project.technical_specification,
        timeline: project.expected_timeline,
        submittedBy: project.submitted_by,
        contactEmail: project.email,
        contactPhone: project.phone_number,
        submittedDate: project.created_at,
        estimatedAmountRupees: project.estimated_amount,
        stage: frontendStage,
        status: project.overall_progress === 100 ? 'Completed' : 'In Progress',
        workflowData: {},
        isApproved: frontendStage >= 5 ? true : null, // If past approval stage, must be approved
      };

      if (existingIndex !== -1) {
        // Update existing requirement
        console.log('Updating existing requirement at index:', existingIndex);
        setAllRequirements(prev => prev.map((req, i) => 
          i === existingIndex ? { ...req, ...reqFromApi } : req
        ));
        setActiveIndex(existingIndex);
      } else {
        // Add new requirement to state
        console.log('Adding new requirement to state');
        const newIndex = allRequirements.length;
        setAllRequirements(prev => [...prev, reqFromApi]);
        setActiveIndex(newIndex);
      }

      // Set current stage and navigate
      setCurrentStage(frontendStage);
      setIsApproved(frontendStage >= 5 ? true : null);
      setWorkflowData({});
      setViewMode('workflow');

      console.log('-'.repeat(60));
      console.log('Navigation complete!');
      console.log('Now rendering case:', frontendStage);
      console.log('='.repeat(60));

    } catch (error) {
      console.error('Error navigating to project:', error);
      alert('Error loading project. Please try again.');
    }
  };

  // Submit new requirement form
  const handleRequirementSubmit = (data) => {
    // data now contains projectId from API response
    const newReq = {
      // Use projectId from API as reqId
      projectId: data.projectId,
      reqId: data.projectId,
      projectId: data.projectId,
      // Form data
      title: data.title,
      department: data.department,
      category: data.category,
      priority: data.priority,
      estimatedValue: data.estimatedValue,
      justification: data.justification,
      specifications: data.specifications,
      timeline: data.timeline,
      submittedBy: data.submittedBy,
      contactEmail: data.contactEmail,
      contactPhone: data.contactPhone,
      submittedDate: data.submittedDate,
      // API response data
      estimatedAmountRupees: data.estimatedAmountRupees,
      filesUploaded: data.filesUploaded,
      uploadedFiles: data.uploadedFiles,
      // Workflow state
      stage: 1,
      status: 'In Progress',
      workflowData: {},
      isApproved: null,
    };
    
    const newIndex = allRequirements.length;
    setAllRequirements(prev => [...prev, newReq]);
    setActiveIndex(newIndex);
    setCurrentStage(1);
    
    // Log the project ID for verification
    console.log('Requirement created with Project ID:', data.projectId);
  };

  // Complete a stage and move to next
  const handleStageComplete = (stageData) => {
    const newWorkflowData = { ...workflowData, ...stageData };
    setWorkflowData(newWorkflowData);
    
    const newStage = currentStage + 1;
    setCurrentStage(newStage);
    
    // Update stored requirement
    if (activeIndex !== null) {
      setAllRequirements(prev => prev.map((req, i) => 
        i === activeIndex 
          ? { ...req, stage: newStage, workflowData: newWorkflowData }
          : req
      ));
    }
  };

  // Handle approval decision
  const handleApproval = (approved) => {
    setIsApproved(approved);
    
    if (approved) {
      setCurrentStage(5);  // Fixed: Go to PublishRFP (case 5), not ReceiveBids (case 6)
      if (activeIndex !== null) {
        setAllRequirements(prev => prev.map((req, i) => 
          i === activeIndex 
            ? { ...req, stage: 5, isApproved: true, status: 'Approved' }
            : req
        ));
      }
    } else {
      if (activeIndex !== null) {
        setAllRequirements(prev => prev.map((req, i) => 
          i === activeIndex 
            ? { ...req, isApproved: false, status: 'Rejected' }
            : req
        ));
      }
    }
  };

  // Go back to dashboard
  const handleBackToDashboard = () => {
    setViewMode('dashboard');
    setActiveIndex(null);
    setCurrentStage(0);
    setIsApproved(null);
    setWorkflowData({});
  };

  // Reset current workflow (for completed)
  const handleReset = () => {
    if (currentStage >= 10) {
      // Mark as completed
      if (activeIndex !== null) {
        setAllRequirements(prev => prev.map((req, i) => 
          i === activeIndex 
            ? { ...req, stage: 10, status: 'Completed' }
            : req
        ));
      }
    }
    handleBackToDashboard();
  };

  // Render current workflow screen
  const renderWorkflowScreen = () => {
    switch (currentStage) {
      case 0:
        return <RequirementForm onSubmit={handleRequirementSubmit} />;
      case 1:
        return <FunctionalAnalysis requirement={currentRequirement} onComplete={handleStageComplete} />;
      case 2:
        return <TechnicalReview requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 3:
        return <TenderDrafting requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 4:
        return <ApprovalGate requirement={currentRequirement} workflowData={workflowData} onApproval={handleApproval} isApproved={isApproved} />;
      case 5:
        return <PublishRFP requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 6:
        return <ReceiveBids requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 7:
        return <VendorEvaluation requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 8:
        return <PurchaseOrder requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 9:
        return <ContractSigning requirement={currentRequirement} workflowData={workflowData} onComplete={handleStageComplete} />;
      case 10:
        return <ProcurementComplete requirement={currentRequirement} workflowData={workflowData} onReset={handleReset} />;
      default:
        return <RequirementForm onSubmit={handleRequirementSubmit} />;
    }
  };

  return (
    <div className="min-h-screen p-6">
      <Header 
        onReset={handleBackToDashboard} 
        currentStage={currentStage} 
        viewMode={viewMode}
      />
      
      {viewMode === 'dashboard' ? (
        <div className="max-w-7xl mx-auto">
          <Dashboard 
            onNewRequirement={handleNewRequirement}
            onViewRequirement={handleViewRequirement}
            onViewProjectById={handleViewProjectById}
            requirements={allRequirements}
          />
        </div>
      ) : (
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <WorkflowSidebar 
              stages={stages} 
              currentStage={currentStage} 
              isApproved={isApproved}
              requirement={currentRequirement}
            />
            {/* Back to Dashboard button */}
            <button
              onClick={handleBackToDashboard}
              className="w-full mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm"
            >
              ← Back to Dashboard
            </button>
          </div>
          
          <div className="lg:col-span-3">
            {renderWorkflowScreen()}
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto mt-8 text-center">
        <p className="text-slate-500 text-sm">
          SPNX Consulting - Workflow Automation Demo - Punjab and Sind Bank
        </p>
      </div>
    </div>
  );
}

export default App;