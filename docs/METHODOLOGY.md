# Scoring Methodology

## Repository Health Score (0-12 points)

### 1. Documentation (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | No README or documentation |
| 1 | Basic README exists |
| 2 | Comprehensive README with setup instructions |
| 3 | Full documentation including API docs, architecture |

### 2. Structure (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | Disorganized, no clear structure |
| 1 | Basic folder structure |
| 2 | Well-organized with separation of concerns |
| 3 | Professional structure with configs, CI/CD |

### 3. Runability (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | Cannot be run without significant effort |
| 1 | Can run with manual configuration |
| 2 | Clear setup instructions, can run easily |
| 3 | One-command setup, containerized |

### 4. History (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | Single commit or no history |
| 1 | Some commits but irregular |
| 2 | Regular commits with messages |
| 3 | Professional history with tags, branches |

---

## Technical Debt Score (0-15 points)

### 1. Architecture (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | No architecture, monolithic blob |
| 1 | Basic separation |
| 2 | Clear layers, some patterns |
| 3 | Clean architecture, well-defined patterns |

### 2. Code Quality (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | No standards, inconsistent code |
| 1 | Some consistency |
| 2 | Follows conventions, linting |
| 3 | High quality, follows best practices |

### 3. Testing (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | No tests |
| 1 | Few tests exist |
| 2 | Moderate coverage |
| 3 | Comprehensive tests, CI/CD integration |

### 4. Infrastructure (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | No deployment config |
| 1 | Basic deployment possible |
| 2 | Docker/containerization |
| 3 | Full CI/CD, IaC, monitoring |

### 5. Security (0-3 points)

| Score | Criteria |
|-------|----------|
| 0 | Security issues, exposed secrets |
| 1 | Basic security |
| 2 | Good security practices |
| 3 | Security hardened, audited |

---

## Product Level Classification

### Level 1: Prototype/PoC (0-5 total score)
- Experimental code
- May not run
- No documentation
- Not suitable for production

### Level 2: Alpha (6-10 total score)
- Basic functionality
- May have bugs
- Limited documentation
- Internal testing only

### Level 3: Beta (11-17 total score)
- Core features complete
- Some issues expected
- Documentation available
- Limited external use

### Level 4: Production (18-22 total score)
- Stable and tested
- Good documentation
- Ready for production
- Active maintenance

### Level 5: Enterprise (23-27 total score)
- Production-hardened
- Comprehensive documentation
- Full test coverage
- Enterprise-grade security

---

## Cost Estimation Methodology

### Base Calculation

Hours = Base Hours x Complexity Factor x Quality Factor
Cost = Hours x Hourly Rate

### Complexity Factors

| Factor | Description | Multiplier |
|--------|-------------|------------|
| Size | Lines of code | 1.0 - 2.0 |
| Languages | Number of languages | 1.0 - 1.5 |
| Dependencies | External dependencies | 1.0 - 1.3 |
| Custom code | Framework vs custom | 1.0 - 1.5 |

### Quality Factors

| Factor | Description | Multiplier |
|--------|-------------|------------|
| Documentation | Docs quality | 0.8 - 1.2 |
| Tests | Test coverage | 0.8 - 1.2 |
| Tech debt | Debt level | 1.0 - 1.5 |

### Activity Breakdown

| Activity | Percentage |
|----------|------------|
| Development | 50% |
| Testing | 20% |
| Documentation | 15% |
| Deployment | 10% |
| Review | 5% |
