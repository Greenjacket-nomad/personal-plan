# Curriculum Tracker

A Flask-based web application for tracking progress through a 17-week AI-First SaaS development curriculum.

## Curriculum Overview

This tracker manages a comprehensive 408-hour curriculum spanning 17 weeks across 4 specialized phases:

### **PHASE 1: REVENUE ARCHITECT** (Weeks 1-4, 96 hours)
Build the foundation for AI-powered automation and data management.
- AI toolchain setup and configuration
- Advanced workflow automation with n8n
- Database schema design (PostgreSQL)
- Git fundamentals and workflow
- API authentication and security
- Webhooks and error handling
- AI function calling and prompt engineering
- Environment variables and deployment basics

**Key Deliverables:**
- Self-Healing Agent stored in GitHub repo
- Listening Agent that populates your DB
- AI Node that parses text into your schema
- Package for client handoff

### **PHASE 2: BACKEND ENGINEER** (Weeks 5-8, 96 hours)
Master backend architecture and database optimization.
- Advanced SQL (JSONB querying, complex JOINs, indexing)
- Python fundamentals and data structures
- Pydantic for data validation
- AsyncIO and error handling
- FastAPI development (setup, validation, dependency injection)
- Docker containerization
- Testing with Pytest and CI/CD
- Vector databases (pgvector) and RAG pipelines

**Key Deliverables:**
- Optimized schema for your SaaS
- Robust data processing script
- CI/CD + PYTEST setup
- Working RAG system

### **PHASE 3: AI ARCHITECT** (Weeks 9-12, 96 hours)
Design and secure advanced AI systems.
- Model Context Protocol (MCP) basics and architecture
- Building MCP servers to connect AI to databases
- Agentic RAG and query routing
- Self-correction and multi-step reasoning
- Cost modeling for AI applications
- OWASP Top 10 security principles
- SQL injection and XSS/CSRF prevention
- Security headers and rate limiting
- LangGraph for stateful multi-agent flows
- ReAct pattern and evaluation frameworks

**Key Deliverables:**
- Claude connected to Postgres via MCP
- Retrieval agent + Cost spreadsheet
- Security + Privacy Checklists
- Multi-agent system

### **PHASE 4: SAAS BUILD** (Weeks 13-17, 120 hours)
Build and deploy a production SaaS application.
- Modern JavaScript (ES6+, async/await, array methods)
- React fundamentals (components, props, hooks)
- Next.js 14 App Router
- Server vs Client Components
- Data fetching and caching strategies
- Server Actions for form handling
- Tailwind CSS styling
- Authentication (Clerk/Supabase Auth, OAuth, RBAC)
- Organization management and middleware
- Stripe integration (checkout, webhooks, payments)
- Monitoring and error tracking (Sentry)
- GitHub Actions for CI/CD
- End-to-end testing with Playwright
- Production deployment and user onboarding

**Key Deliverables:**
- Dashboard shell component
- Connect Dashboard + Playwright
- Wire auth into SaaS Dashboard
- Connect Stripe, deploy staging
- Collect feedback, prioritize v1.1

---

## Total Commitment

- **Duration:** 17 weeks
- **Total Hours:** 408 hours
- **Weekly Target:** 24 hours/week (4 hours/day × 6 days)

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- SQLite3 (included with Python)

### Installation

1. **Clone the repository:**
   ```bash
   cd curriculum-tracker
   ```

2. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Import the curriculum data:**
   ```bash
   python3 import_csv.py
   ```
   This will create `tracker.db` and populate it with all 102 learning resources from the curriculum.

4. **Run the application:**
   ```bash
   python3 app.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:5000`

---

## Features

### 📊 Dashboard
- **Progress Tracking:** Monitor hours logged per week and total progress
- **Phase Overview:** View all 4 phases with completion status
- **Week Navigation:** Navigate through curriculum weeks with tabs
- **Metrics Tracking:** Check off key deliverables (BUILD DAY projects)
- **Completion Statistics:** Per-day, per-week, and per-phase completion rollups
- **Resource Management:** View, complete, and favorite resources for each day
- **Search:** Filter dashboard resources by title, notes, or topic

### 📚 Resources Page
- **Filter by Phase:** View resources for specific curriculum phases
- **Filter by Type:** Course, Docs, Project, Article, Video, etc.
- **Filter by Status:** Completed, Pending, or Favorites
- **Tag Management:** Create custom tags and organize resources
- **Search:** Full-text search across all resources

### ⏱️ Time Logging
- **Daily Logging:** Record hours spent with optional notes
- **Phase Tracking:** Automatically associates logged hours with current phase
- **Recent Activity:** View last 7 days of time logs
- **Progress Visualization:** See hours logged vs. target hours

### 🎯 Metrics & Deliverables
- **BUILD DAY Tracking:** Each phase has 4-5 key deliverables
- **Auto-Completion:** Day 6 resources auto-complete corresponding metrics
- **Phase Completion:** Track overall phase progress based on deliverables

### 📤 Data Export
- **JSON Export:** Export all progress, resources, and configuration
- **Backup & Restore:** Save your progress and import on another device

### 🔄 Progress Reset
- **Clean Slate:** Reset all progress while preserving resources
- **Complete Reset:** Clears config, time logs, metrics, and resource completion

---

## Project Structure

```
curriculum-tracker/
├── app.py                    # Main Flask application (SQLite)
├── import_csv.py             # CSV import script with auto-tagging
├── curriculum.yaml           # Phase/metrics configuration
├── curriculum_data.csv       # Source of truth (102 resources)
├── tracker.db                # SQLite database
├── requirements.txt          # Python dependencies
├── templates/
│   ├── dashboard.html        # Main dashboard view
│   └── resources.html        # Resources listing page
└── README.md                 # This file
```

---

## Database Schema

### Tables
- **config:** Application settings (start_date, current_phase, current_week)
- **time_logs:** Daily time entries with phase tracking
- **completed_metrics:** Checked-off BUILD DAY deliverables
- **resources:** Learning materials (courses, docs, projects, etc.)
- **tags:** Custom tags for organizing resources
- **resource_tags:** Many-to-many relationship for resource tagging

---

## Technology Stack

- **Backend:** Flask (Python)
- **Database:** SQLite3
- **Frontend:** HTML, Tailwind CSS, Font Awesome icons
- **Data Format:** CSV (source), YAML (configuration), JSON (export)

---

## Resource Types

The curriculum includes diverse learning materials:
- 🎓 **Courses:** Udemy, Codecademy, DeepLearning.ai
- 📚 **Docs:** Official documentation and technical references
- 🛠️ **Projects:** Hands-on BUILD DAY deliverables
- 📄 **Articles:** Technical reading and best practices
- 🎬 **Videos:** YouTube tutorials and lectures
- 🔬 **Labs:** Interactive security labs (PortSwigger)
- 📝 **Notes:** Quick reference and checklists
- ✅ **Actions:** Practical tasks and exercises

---

## Usage Tips

1. **Start Fresh:** Run `python3 import_csv.py` to import the curriculum on first setup
2. **Daily Habit:** Log hours each day to track your progress
3. **Week Navigation:** Use week tabs to browse ahead or review past weeks
4. **Tag Resources:** Add custom tags to organize by topics or priorities
5. **Mark Favorites:** Star important resources for quick reference
6. **BUILD DAYS:** Focus on Day 6 deliverables—they're the key learning milestones
7. **Search Feature:** Use the search box to quickly find specific resources
8. **Export Regularly:** Download your progress as JSON for backup

---

## Curriculum Philosophy

This is an **AI-First** curriculum designed for aspiring CTOs and technical architects. The focus is on:

- **Architecture over Implementation:** You design and spec; AI builds
- **Security First:** OWASP, authentication, and audit skills from the start
- **Practical Deliverables:** Every week includes hands-on projects
- **Modern Stack:** FastAPI, Next.js, Supabase, Stripe, Vercel
- **AI Integration:** MCP, RAG, vector databases, and agentic workflows
- **Production Ready:** Deploy real SaaS products, not toy projects

By Week 17, you'll have shipped a production SaaS application with payments, authentication, AI features, and real users.

---

## License

MIT

---

## Support

For issues or questions, please check the existing resources in the `/resources` page or review the curriculum materials.

---

**Happy Learning! 🚀**

