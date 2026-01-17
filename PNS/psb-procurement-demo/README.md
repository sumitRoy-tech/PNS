# Punjab & Sind Bank - Procurement Workflow Demo

A React-based interactive demonstration of the RFP/Tendering workflow for Punjab & Sind Bank.

## 🎯 Features

- **10-Stage Visual Workflow** - Complete procurement lifecycle visualization
- **Auto Demo Mode** - Automated walkthrough of the entire process
- **Manual Progression** - Step through stages one by one
- **Approval Gate** - Interactive approve/reject decision at Stage 5
- **Expandable Details** - Click any stage to see outputs and description
- **Progress Tracking** - Real-time percentage and progress bar
- **PSB Branding** - Uses official bank colors (Green #167947, Gold #CFA550)

## 📁 Project Structure

```
psb-procurement-demo/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Header.jsx          # Logo + Action buttons
│   │   ├── RequirementPanel.jsx # Left panel with requirement details
│   │   ├── ActionPanel.jsx      # Stage actions and approval
│   │   └── WorkflowStages.jsx   # Main workflow visualization
│   ├── data/
│   │   └── workflowData.js      # Stages config & sample data
│   ├── App.js                   # Main app component
│   ├── index.js                 # Entry point
│   └── index.css                # Global styles + Tailwind
├── package.json
├── tailwind.config.js
└── postcss.config.js
```

## 🚀 How to Run

### Step 1: Install Node.js
If not already installed, download from: https://nodejs.org/

### Step 2: Open Terminal/Command Prompt
Navigate to the project folder:
```bash
cd psb-procurement-demo
```

### Step 3: Install Dependencies
```bash
npm install
```

### Step 4: Start the Application
```bash
npm start
```

The app will open automatically at `http://localhost:3000`

## 🎮 Demo Instructions

1. **Auto Demo**: Click "Auto Demo" button to see full workflow animate through all 10 stages
2. **Manual Mode**: Click "Reset", then use "Proceed to Next Stage" to step through manually
3. **Approval Gate**: At Stage 5, you can choose to Approve or Reject
   - Approve → Continues to Stage 6
   - Reject → Process terminates
4. **Expand Stages**: Click any stage card to see detailed description and outputs

## 🎨 Customization

### To Add PSB Official Logo
Replace the `PSBLogo` component in `src/components/Header.jsx` with the actual logo image:

```jsx
<img 
  src="/path/to/psb-logo.png" 
  alt="Punjab & Sind Bank" 
  className="w-12 h-12 rounded-lg"
/>
```

### To Modify Stages
Edit `src/data/workflowData.js` to change stage names, descriptions, or outputs.

### To Add New Stages
Add new objects to the `stages` array in `workflowData.js`.

## 🏦 Presented by

**SPNX Consulting**  
Workflow Automation Solutions for Banking Sector

---

For any questions, contact the development team.
