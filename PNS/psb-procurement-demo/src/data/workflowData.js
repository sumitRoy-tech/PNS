export const stages = [
  { id: 1, name: 'Requirement Raised', dept: 'Business Department', icon: 'FileText' },
  { id: 2, name: 'Functional & Technical Analysis', dept: 'IT & Business Teams', icon: 'Settings' },
  { id: 3, name: 'Technical Review', dept: 'Technical Committee', icon: 'Users' },
  { id: 4, name: 'Tender/RFP Drafting', dept: 'Procurement Cell', icon: 'ClipboardCheck' },
  { id: 5, name: 'In-Principle Approval', dept: 'Competent Authority', icon: 'CheckCircle', isGate: true },
  { id: 6, name: 'Publish RFP', dept: 'Procurement Cell', icon: 'Send' },
  { id: 7, name: 'Receive Bids', dept: 'Procurement Cell', icon: 'Inbox' },
  { id: 8, name: 'Vendor Evaluation', dept: 'Evaluation Committee', icon: 'UserCheck' },
  { id: 9, name: 'Purchase Order', dept: 'Procurement Cell', icon: 'ShoppingCart' },
  { id: 10, name: 'SLA & Contract', dept: 'Legal & Procurement', icon: 'FileSignature' },
];

export const departments = [
  'Information Technology',
  'Operations',
  'Treasury',
  'Retail Banking',
  'Corporate Banking',
  'Human Resources',
  'Finance & Accounts',
  'Risk Management',
  'Compliance',
  'Legal',
];

export const categories = [
  'IT Infrastructure',
  'Software/Application',
  'Hardware',
  'Professional Services',
  'AMC/Support',
  'Security Solutions',
  'Network Equipment',
  'Cloud Services',
  'Consultancy',
  'Other',
];

export const priorities = ['High', 'Medium', 'Low'];
