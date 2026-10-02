# 🌟 Online Job Portal

A modern, production-grade, full-stack **Online Job Portal** web application built with **Python, Flask, SQLite, and modern Bootstrap 5**.

The platform connects ambitious job seekers with innovative companies through role-based workflows, comprehensive job searching and filtering, one-click application submission, resume management, candidate evaluation tracking, and an administrative moderation panel.

---

## 🚀 Key Features

### 👤 1. Job Seeker (Candidate)
- **Candidate Profile & Resume Management**:
  - Customize headline, professional bio, skills tags, experience years, education, and location.
  - Upload, replace, and download PDF / DOCX resumes.
  - Add links to GitHub, LinkedIn, and personal portfolios.
  - Interactive profile completeness meter.
- **Search & Discovery Engine**:
  - Real-time search across job titles, company names, skills, and descriptions.
  - Granular multi-factor filters: Job Category, Job Type (Full-Time, Remote, Part-Time, Contract, Internship), Experience Level, and Location.
  - Sorting by Newest, Highest Salary, and Most Popular.
- **One-Click Application System**:
  - Apply with existing profile resume or attach a new version for specific roles.
  - Personalized cover letter / pitch submission.
  - Prevention of duplicate applications.
- **Application Tracking Dashboard**:
  - Real-time status badges: `Pending`, `Under Review`, `Shortlisted`, `Accepted`, `Rejected`.
- **Job Bookmarking**:
  - Save and organize favorite positions with AJAX toggle.

---

### 🏢 2. Employer (Recruiter / Company)
- **Company Profile Showcase**:
  - Public company landing page featuring about section, headquarters location, company size, founded year, and active vacancies.
- **Job Vacancy Management**:
  - Create and publish new job vacancies with salary ranges, experience requirements, responsibilities, perks, and application deadlines.
  - Edit active postings or set status to `Active`, `Closed`, or `Draft`.
  - Delete expired postings.
- **Candidate Applicant Management**:
  - Review all candidates who applied for each specific posting.
  - View applicant contact details, skills, experience, education, portfolio links, and cover letters.
  - Download candidate resumes directly in one click.
  - Update candidate pipeline status (`Under Review`, `Shortlisted`, `Accepted`, `Rejected`) and write internal recruiter notes.

---

### 🛡️ 3. Platform Administration (Super Admin)
- **Analytics Overview**: Real-time counter metrics for Total Users, Job Seekers, Employers, Active Vacancies, and Applications.
- **User Governance**: Moderate accounts with one-click activate / deactivate toggles.
- **Job Moderation**: Close or reopen job postings across any employer.
- **Category Management**: Add new job categories with Bootstrap icon classes and descriptions, or delete obsolete categories.
- **Security & Activity Audit Logs**: Full chronological tracking of administrative actions and system events.

---

## ⚡ Quick 1-Click Demo Logins

The application includes rich, realistic mock data with ready-to-test accounts. On the **Sign In** page, you can use the **1-Click Demo Buttons** or log in manually with:

| Role | Email | Password | What You Can Test |
| :--- | :--- | :--- | :--- |
| **Job Seeker** | `alex@example.com` | `password123` | Search jobs, apply with resume, check application statuses, manage profile |
| **Employer** | `techcorp@example.com` | `password123` | Post new vacancies, review candidate applicants, update candidate stages |
| **Admin** | `admin@portal.com` | `admin123` | Moderate users, oversee job listings, add categories, view audit logs |

---

## 🛠️ Technology Stack

- **Backend**: Python 3 (Flask 3.x, Werkzeug Security, Jinja2)
- **Database**: SQLite3 with foreign keys and relational integrity
- **Frontend**: HTML5, Modern CSS3, Bootstrap 5.3, Bootstrap Icons
- **Typography**: Google Fonts (*Plus Jakarta Sans*)
- **File Management**: Secure upload handling for candidate resumes and logos

---

## 📁 Project Structure

```
Onlinejobportal/
│
├── app.py                      # Core Flask application, controllers & routing logic
├── database.py                 # SQLite schema, migrations, connection helper & seed data
├── auth.py                     # Authentication utilities & role-based access decorators
├── requirements.txt            # Python dependencies
├── run.bat                     # Windows one-click start script
├── README.md                   # Complete documentation
│
├── static/
│   ├── css/
│   │   └── style.css           # Premium custom styles, color palette, badges & animations
│   ├── js/
│   │   └── main.js             # AJAX bookmarking, auto-dismiss alerts, toasts & clipboard
│   ├── uploads/
│   │   ├── resumes/            # Candidate uploaded resumes
│   │   └── logos/              # Employer company logos
│   └── images/                 # Default assets
│
└── templates/
    ├── base.html               # Master layout with responsive navbar & notifications
    ├── index.html              # Landing page with hero search, stats & featured jobs
    ├── jobs.html               # Job exploration & multi-filter search page
    ├── job_detail.html         # Job details, apply modal & similar roles
    ├── login.html              # Login page with 1-click Demo Logins
    ├── register.html           # Role-based user registration (Seeker / Employer)
    ├── seeker_dashboard.html   # Candidate dashboard & application status tracker
    ├── seeker_profile.html     # Candidate profile editing & resume upload
    ├── saved_jobs.html         # Candidate bookmarked jobs
    ├── employer_dashboard.html # Employer dashboard with postings & applicant feed
    ├── post_job.html           # Job posting creation and edit form
    ├── job_applicants.html     # Recruiter candidate review & status pipeline
    ├── company_profile.html    # Public company profile & active job openings
    ├── company_profile_edit.html # Employer organization settings
    ├── admin_dashboard.html    # Super Admin metrics, users, jobs & categories
    └── 404.html                # Friendly 404 error page
```

---

## 🏃 Getting Started & Running The Application

### Step 1: Clone or Navigate to the Directory
```bash
cd "c:\Users\Sumathi\OneDrive\Desktop\Onlinejobportal"
```

### Step 2: Install Dependencies (Optional, standard libraries already available)
```bash
pip install -r requirements.txt
```

### Step 3: Run the Server
On **Windows**, simply double-click `run.bat` or run:
```bash
python app.py
```

### Step 4: Open in Your Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

The database (`jobportal.db`) is automatically initialized and seeded with sample companies, categories, job vacancies, and applications on first start!

---

## 🔒 Security Features
- Password hashing with PBKDF2/SHA256 via `werkzeug.security`.
- Role-based route protection with `@login_required(role)`.
- Secure file upload validation (whitelisted extensions `.pdf`, `.doc`, `.docx` for resumes; `.png`, `.jpg`, `.jpeg` for logos).
- Parameterized SQL queries throughout to eliminate SQL injection risks.
- Unique application constraint per candidate and job to prevent duplicate submissions.
