import React, { useState, useRef } from 'react';
import { FileText, Send, Upload, AlertCircle, X, File, Loader2, CheckCircle } from 'lucide-react';
import { departments, categories, priorities } from '../data/workflowData';

function RequirementForm({ onSubmit }) {
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('');
  const [category, setCategory] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [estimatedValue, setEstimatedValue] = useState('');
  const [justification, setJustification] = useState('');
  const [specifications, setSpecifications] = useState('');
  const [timeline, setTimeline] = useState('');
  const [submittedBy, setSubmittedBy] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [files, setFiles] = useState([]);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState(null);
  
  const fileInputRef = useRef(null);

  // Page tracking info for logging/debugging
  const PAGE_INFO = {
    currentPage: 1,
    pageName: 'Requirement Submission',
    nextPage: 2,
    nextPageName: 'Functional Assessment'
  };

  // Navigation constants for App.js case mapping
  const NAVIGATION = {
    currentStage: 0,           // case 0 in App.js
    currentComponent: 'RequirementForm',
    nextStage: 1,              // case 1 in App.js
    nextComponent: 'FunctionalAnalysis',
    nextPageName: 'Functional Analysis'
  };

  // Update navigation in database
  const updateNavigation = async (projectId) => {
    try {
      console.log('Updating navigation for project:', projectId);
      const response = await fetch(`http://localhost:8003/requirements/navigation/${projectId}`, {
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

  const validate = () => {
    const newErrors = {};
    if (!title) newErrors.title = 'Title is required';
    if (!department) newErrors.department = 'Department is required';
    if (!category) newErrors.category = 'Category is required';
    if (!estimatedValue) newErrors.estimatedValue = 'Estimated value is required';
    if (!justification) newErrors.justification = 'Business justification is required';
    if (!submittedBy) newErrors.submittedBy = 'Submitter name is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSubmitSuccess(null);
    
    if (!validate()) return;
    
    setIsSubmitting(true);
    
    // Log current page info
    console.log('='.repeat(60));
    console.log('REQUIREMENT FORM SUBMISSION - PAGE TRACKING');
    console.log('='.repeat(60));
    console.log(`Current Page: ${PAGE_INFO.currentPage} - ${PAGE_INFO.pageName}`);
    console.log(`After submission, will redirect to: Page ${PAGE_INFO.nextPage} - ${PAGE_INFO.nextPageName}`);
    console.log('-'.repeat(60));
    
    try {
      // Create FormData for multipart/form-data submission
      const formData = new FormData();
      formData.append('title', title);
      formData.append('department', department);
      formData.append('category', category);
      formData.append('submitted_by', submittedBy);
      formData.append('priority', priority.toLowerCase());
      formData.append('estimated_amount', estimatedValue);
      formData.append('business_justification', justification);
      formData.append('expected_timeline', timeline);
      formData.append('technical_specification', specifications);
      formData.append('email', contactEmail);
      formData.append('number', contactPhone);
      
      // Append files
      files.forEach((file) => {
        formData.append('files', file);
      });
      
      console.log('Submitting requirement to API...');
      
      const response = await fetch('http://localhost:8003/requirements/', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Log API response with progress info
      console.log('-'.repeat(60));
      console.log('API RESPONSE:');
      console.log(`  Project ID: ${data.project_id}`);
      console.log(`  Message: ${data.message}`);
      console.log(`  Files Uploaded: ${data.files_uploaded}`);
      
      // Log progress tracking info from response
      if (data.progress) {
        console.log('-'.repeat(60));
        console.log('PROGRESS TRACKING:');
        console.log(`  Current Page: ${data.progress.current_page}`);
        console.log(`  Overall Progress: ${data.progress.overall_progress}%`);
        console.log(`  Status: ${data.progress.status}`);
        console.log(`  Page 1 (Requirement) is now COMPLETED`);
        console.log(`  Next step: Navigate to Page 2 (Functional Assessment)`);
      }
      
      // Update navigation in database
      console.log('-'.repeat(60));
      console.log('UPDATING NAVIGATION:');
      const navData = await updateNavigation(data.project_id);
      if (navData) {
        console.log(`  Next Stage: ${NAVIGATION.nextStage} (case ${NAVIGATION.nextStage})`);
        console.log(`  Next Component: ${NAVIGATION.nextComponent}`);
      }
      
      console.log('='.repeat(60));
      
      // Set success state for UI feedback
      setSubmitSuccess({
        projectId: data.project_id,
        progress: data.progress
      });
      
      // Call onSubmit with the API response and form data
      // The parent component can use project_id to navigate or update state
      if (onSubmit) {
        onSubmit({
          // API response data
          projectId: data.project_id,
          message: data.message,
          estimatedAmountRupees: data.estimated_amount_rupees,
          filesUploaded: data.files_uploaded,
          uploadedFiles: data.files,
          
          // Progress tracking data
          progress: data.progress || {
            current_page: 2,
            overall_progress: 10.0,
            status: 'in_progress'
          },
          
          // Page navigation info
          completedPage: PAGE_INFO.currentPage,
          completedPageName: PAGE_INFO.pageName,
          nextPage: PAGE_INFO.nextPage,
          nextPageName: PAGE_INFO.nextPageName,
          
          // Form data for reference
          title,
          department,
          category,
          priority,
          estimatedValue,
          justification,
          specifications,
          timeline,
          submittedBy,
          contactEmail,
          contactPhone,
          submittedDate: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
          status: 'Submitted',
        });
      }
      
    } catch (error) {
      console.error('Submission error:', error);
      setSubmitError(error.message || 'Failed to submit requirement. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearError = (field) => {
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = {...prev};
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      {/* Header with Page Info */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-psb-green/20 rounded-lg">
            <FileText size={24} className="text-psb-green" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">New Procurement Requirement</h2>
            <p className="text-slate-400 text-sm">Business Department Submission Form</p>
          </div>
        </div>
        
        {/* Page Indicator */}
        <div className="hidden md:flex items-center gap-2 bg-slate-700/50 px-4 py-2 rounded-lg">
          <span className="text-psb-gold text-sm font-medium">Step {PAGE_INFO.currentPage}</span>
          <span className="text-slate-500 text-sm">of 10</span>
          <div className="flex gap-1 ml-2">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i === 0 ? 'bg-psb-green' : 'bg-slate-600'
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Success Message */}
      {submitSuccess && (
        <div className="mb-6 p-4 bg-psb-green/10 border border-psb-green/50 rounded-lg">
          <div className="flex items-center gap-3">
            <CheckCircle size={20} className="text-psb-green flex-shrink-0" />
            <div>
              <p className="text-psb-green font-medium">Requirement Submitted Successfully!</p>
              <p className="text-slate-400 text-sm">
                Project ID: {submitSuccess.projectId} | Progress: {submitSuccess.progress?.overall_progress}%
              </p>
              <p className="text-slate-500 text-xs mt-1">
                Page 1 completed. Redirecting to Functional Assessment...
              </p>
            </div>
          </div>
        </div>
      )}

      {submitError && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-3">
          <AlertCircle size={20} className="text-red-400 flex-shrink-0" />
          <p className="text-red-400 text-sm">{submitError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        
        <div className="border-b border-slate-700 pb-6">
          <h3 className="text-psb-gold font-medium mb-4">Basic Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <div className="md:col-span-2">
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Requirement Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => { setTitle(e.target.value); clearError('title'); }}
                placeholder="e.g., Core Banking System Upgrade"
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.title ? 'border-red-500' : 'border-slate-600')}
              />
              {errors.title && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.title}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Department <span className="text-red-400">*</span>
              </label>
              <select
                value={department}
                onChange={(e) => { setDepartment(e.target.value); clearError('department'); }}
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.department ? 'border-red-500' : 'border-slate-600')}
              >
                <option value="">Select Department</option>
                {departments.map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
              {errors.department && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.department}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Category <span className="text-red-400">*</span>
              </label>
              <select
                value={category}
                onChange={(e) => { setCategory(e.target.value); clearError('category'); }}
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.category ? 'border-red-500' : 'border-slate-600')}
              >
                <option value="">Select Category</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              {errors.category && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.category}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {priorities.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Estimated Value (₹ Crores) <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={estimatedValue}
                onChange={(e) => { setEstimatedValue(e.target.value); clearError('estimatedValue'); }}
                placeholder="e.g., 2.5 or 2.5 CR"
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.estimatedValue ? 'border-red-500' : 'border-slate-600')}
              />
              {errors.estimatedValue && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.estimatedValue}
                </p>
              )}
            </div>

          </div>
        </div>

        <div className="border-b border-slate-700 pb-6">
          <h3 className="text-psb-gold font-medium mb-4">Requirement Details</h3>
          <div className="space-y-4">
            
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Business Justification <span className="text-red-400">*</span>
              </label>
              <textarea
                value={justification}
                onChange={(e) => { setJustification(e.target.value); clearError('justification'); }}
                placeholder="Explain why this procurement is needed and its business impact..."
                rows={4}
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 resize-none disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.justification ? 'border-red-500' : 'border-slate-600')}
              />
              {errors.justification && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.justification}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">Technical Specifications</label>
              <textarea
                value={specifications}
                onChange={(e) => setSpecifications(e.target.value)}
                placeholder="Provide technical requirements, features needed, compatibility requirements..."
                rows={4}
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">Expected Timeline</label>
              <input
                type="text"
                value={timeline}
                onChange={(e) => setTimeline(e.target.value)}
                placeholder="e.g., Q2 2025 or 6 months from PO"
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

          </div>
        </div>

        <div className="border-b border-slate-700 pb-6">
          <h3 className="text-psb-gold font-medium mb-4">Contact Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">
                Submitted By <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={submittedBy}
                onChange={(e) => { setSubmittedBy(e.target.value); clearError('submittedBy'); }}
                placeholder="Name & Designation"
                disabled={isSubmitting}
                className={'w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed ' + (errors.submittedBy ? 'border-red-500' : 'border-slate-600')}
              />
              {errors.submittedBy && (
                <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                  <AlertCircle size={12} /> {errors.submittedBy}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                placeholder="email@psbindia.com"
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1">Phone</label>
              <input
                type="text"
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                placeholder="Extension or Mobile"
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-psb-gold/50 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

          </div>
        </div>

        <div className="border-b border-slate-700 pb-6">
          <h3 className="text-psb-gold font-medium mb-4">Supporting Documents</h3>
          
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx"
            className="hidden"
            disabled={isSubmitting}
          />
          
          <div 
            onClick={!isSubmitting ? handleFileClick : undefined}
            className={'border-2 border-dashed border-slate-600 rounded-lg p-6 text-center transition-colors ' + (isSubmitting ? 'opacity-50 cursor-not-allowed' : 'hover:border-psb-gold/50 cursor-pointer')}
          >
            <Upload size={32} className="text-slate-400 mx-auto mb-2" />
            <p className="text-slate-300 text-sm">Click to upload or drag and drop</p>
            <p className="text-slate-500 text-xs mt-1">PDF, DOC, XLS up to 10MB each</p>
          </div>

          {files.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-slate-400 text-sm">Uploaded Files:</p>
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg">
                  <div className="flex items-center gap-2">
                    <File size={16} className="text-psb-gold" />
                    <span className="text-white text-sm">{file.name}</span>
                    <span className="text-slate-500 text-xs">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    disabled={isSubmitting}
                    className="text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-between items-center">
          {/* Progress Info */}
          <div className="text-slate-500 text-sm">
            <span>Completing this will mark </span>
            <span className="text-psb-gold">Page 1</span>
            <span> as done</span>
          </div>
          
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-3 bg-psb-green hover:bg-psb-green-light text-white rounded-lg transition-all duration-200 font-medium shadow-lg shadow-psb-green/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-psb-green"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Send size={18} />
                Submit Requirement
              </>
            )}
          </button>
        </div>

      </form>
    </div>
  );
}

export default RequirementForm;
