# User Guide

## Getting Started

### 1. Access the Platform

Open your browser and navigate to:
- Frontend: `http://localhost:3333`
- API Docs: `http://localhost:7777/docs`

### 2. Navigation

The main navigation includes:
- **Workflow** - Start new analysis
- **Projects** - Manage projects
- **Docs** - View documentation
- **Matrix** - Document matrix
- **Contracts** - Contract comparison
- **LLM** - AI assistant
- **Settings** - Configuration

---

## Running an Analysis

### Step 1: Start Workflow

1. Click "Start Analysis" or navigate to `/workflow`
2. Enter the repository URL
3. Select evaluation profile (optional)
4. Click "Analyze"

### Step 2: Review Results

Analysis results include:
- **Repository Health Score** (0-12)
- **Technical Debt Score** (0-15)
- **Product Level** (1-5)
- **Cost Estimate**

### Step 3: Generate Documents

From the analysis page:
1. Go to "Documents" tab
2. Select document type
3. Click "Generate"
4. Download the document

---

## Contract Comparison

### Step 1: Upload Contract

1. Navigate to `/contract-comparison` (click "Contracts")
2. Click "Upload Contract" tab
3. Drag and drop your contract file or click to browse
4. Optionally enter a custom name
5. Click "Upload"

**Supported formats:** PDF, DOCX, DOC, TXT

### Step 2: View Parsed Data

1. Click "Parsed Data" tab
2. Review extracted information:
   - Work Plan activities
   - Milestones
   - Budget lines
   - Indicators
   - Policies
   - Document templates

### Step 3: Run Comparison

1. Click "Comparison" tab
2. Select the parsed contract
3. Select analysis to compare with
4. Click "Compare"
5. Review results:
   - Overall status and score
   - Work plan progress
   - Budget comparison
   - Indicator achievement
   - Risks and recommendations

### Using Demo Data

For testing:
1. Click "Load Demo Contract"
2. Click "Run Demo Comparison"
3. Review sample results

---

## Document Matrix

### Accessing the Matrix

1. Navigate to `/document-matrix` (click "Matrix")
2. Select product level (1-5)
3. View required documents for that level

### Document Categories

- **Technical** - Architecture, API docs, etc.
- **Quality** - Test reports, security audits
- **Operational** - Deployment guides, runbooks
- **Business** - User guides, release notes

---

## Project Management

### Creating a Project

1. Navigate to `/projects`
2. Click "New Project"
3. Fill in project details:
   - Name
   - Description
   - Contract reference
   - Start/End dates
4. Click "Create"

### Tracking Progress

1. Open project details
2. View activities and progress
3. Add activities as needed
4. Update status

### Linking Analysis

1. Open project
2. Click "Link Analysis"
3. Select analysis from list
4. View comparison data

---

## Settings

### Evaluation Profiles

1. Navigate to `/settings`
2. View available profiles:
   - Default
   - Global Fund R13
   - Internal Tool
3. Select profile for analysis

### Configuration Options

- API keys (if required)
- Rate limits
- Default hourly rate
- Currency

---

## Tips and Best Practices

### For Better Analysis

1. Ensure repository has:
   - README file
   - Clear structure
   - Configuration files
   - Some git history

2. For accurate cost estimates:
   - Set appropriate hourly rate
   - Use correct complexity factors

### For Contract Comparison

1. Upload complete contract documents
2. Ensure contract has clear:
   - Work plan with activities
   - Budget breakdown
   - KPI indicators

3. Update project progress regularly

### For Document Generation

1. Complete analysis first
2. Review scores before generating
3. Customize templates in settings

---

## Troubleshooting

### Analysis Not Starting

- Check repository URL is accessible
- Verify git credentials if private repo
- Check backend logs

### Contract Parsing Fails

- Ensure file format is supported
- Check file is not corrupted
- Try plain text version

### Comparison Shows N/A

- Verify contract has required data
- Check analysis completed successfully
- Ensure mapping between indicators

### Documents Not Generating

- Complete analysis first
- Check all required fields
- Verify template exists

---

## Support

For issues or questions:
1. Check documentation
2. Review API docs at `/docs`
3. Check backend logs
4. Report issues on GitHub
