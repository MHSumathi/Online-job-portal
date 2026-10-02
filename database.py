import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobportal.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(seed=True):
    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('seeker', 'employer', 'admin')),
        phone TEXT,
        avatar TEXT DEFAULT 'default_avatar.png',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS seeker_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        title TEXT,
        bio TEXT,
        skills TEXT,
        experience_years INTEGER DEFAULT 0,
        education TEXT,
        location TEXT,
        resume_filename TEXT,
        website TEXT,
        github TEXT,
        linkedin TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS employer_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        company_name TEXT NOT NULL,
        company_website TEXT,
        company_location TEXT,
        industry TEXT,
        company_size TEXT,
        company_description TEXT,
        logo_filename TEXT DEFAULT 'default_company.png',
        founded_year INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT NOT NULL DEFAULT 'bi-briefcase',
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employer_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        job_type TEXT NOT NULL,
        experience_level TEXT NOT NULL,
        location TEXT NOT NULL,
        salary_min INTEGER,
        salary_max INTEGER,
        salary_currency TEXT DEFAULT '$',
        description TEXT NOT NULL,
        responsibilities TEXT,
        requirements TEXT,
        benefits TEXT,
        status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Closed', 'Draft')),
        deadline DATE,
        views_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        seeker_id INTEGER NOT NULL,
        cover_letter TEXT,
        resume_filename TEXT NOT NULL,
        status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Under Review', 'Shortlisted', 'Accepted', 'Rejected')),
        notes TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(job_id, seeker_id),
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        FOREIGN KEY (seeker_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS saved_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, job_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    conn.commit()

    if seed:
        # Check if users already seeded
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        if cursor.fetchone()['cnt'] == 0:
            seed_database(conn)

    conn.close()

def seed_database(conn):
    cursor = conn.cursor()
    pwd_default = generate_password_hash('password123')
    admin_pwd = generate_password_hash('admin123')

    # Seed Admin
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, phone)
        VALUES (?, ?, ?, 'admin', ?)
    """, ('Platform Admin', 'admin@portal.com', admin_pwd, '+1 800-555-0100'))

    # Seed Employers
    employers = [
        ('TechCorp Solutions', 'techcorp@example.com', '+1 555-0121',
         'TechCorp Solutions', 'https://techcorp.example.com', 'San Francisco, CA', 'Technology & Cloud', '250-500 Employees',
         'Leading enterprise cloud software and developer tooling provider building resilient infrastructure.', 2014),
        ('CloudScale Labs', 'cloudscale@example.com', '+1 555-0122',
         'CloudScale Labs', 'https://cloudscale.example.com', 'New York, NY', 'Cloud Computing & AI', '100-250 Employees',
         'Next-generation serverless platform and machine learning inference engine for scalable engineering teams.', 2018),
        ('DesignSpark Studio', 'designspark@example.com', '+1 555-0123',
         'DesignSpark Studio', 'https://designspark.example.com', 'Austin, TX', 'Product Design & Creative', '20-50 Employees',
         'Human-centered digital product design, UX research, and branding agency serving global tech brands.', 2020)
    ]

    employer_ids = []
    for name, email, phone, c_name, c_web, c_loc, ind, c_size, c_desc, f_year in employers:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, 'employer', ?)
        """, (name, email, pwd_default, phone))
        emp_id = cursor.lastrowid
        employer_ids.append(emp_id)
        cursor.execute("""
            INSERT INTO employer_profiles (user_id, company_name, company_website, company_location, industry, company_size, company_description, founded_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (emp_id, c_name, c_web, c_loc, ind, c_size, c_desc, f_year))

    # Seed Seekers
    seekers = [
        ('Alex Rivera', 'alex@example.com', '+1 555-0144',
         'Senior Full-Stack Engineer',
         'Full-stack engineer with 6+ years building performant web applications using Python, JavaScript, and cloud architectures.',
         'Python, Flask, Django, React, PostgreSQL, Docker, AWS, REST APIs',
         6, 'B.S. in Computer Science, University of California, Berkeley', 'San Francisco, CA / Remote',
         'https://alexrivera.dev', 'https://github.com/alexrivera-dev', 'https://linkedin.com/in/alexrivera-mock'),
        ('Sarah Jenkins', 'sarah@example.com', '+1 555-0145',
         'Lead Product Designer & UX Researcher',
         'Passionate product designer dedicated to crafting delightful, accessible user journeys and clean design systems.',
         'Figma, UI/UX Design, User Research, Wireframing, Prototyping, Design Systems, HTML/CSS',
         5, 'B.A. in Graphic Design & Interaction, Pratt Institute', 'Austin, TX / Remote',
         'https://sarahdesigns.io', 'https://github.com/sarah-designs', 'https://linkedin.com/in/sarahjenkins-mock')
    ]

    seeker_ids = []
    for name, email, phone, title, bio, skills, exp, edu, loc, web, gh, li in seekers:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, 'seeker', ?)
        """, (name, email, pwd_default, phone))
        seek_id = cursor.lastrowid
        seeker_ids.append(seek_id)
        cursor.execute("""
            INSERT INTO seeker_profiles (user_id, title, bio, skills, experience_years, education, location, resume_filename, website, github, linkedin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (seek_id, title, bio, skills, exp, edu, loc, 'sample_resume.pdf', web, gh, li))

    # Seed Categories
    categories = [
        ('Software & IT', 'bi-code-slash', 'Software engineering, web development, DevOps, cybersecurity, and system architecture.'),
        ('Data & Artificial Intelligence', 'bi-cpu', 'Machine learning, data science, big data analytics, and generative AI research.'),
        ('Product & Design', 'bi-palette', 'UI/UX design, design systems, product management, and creative direction.'),
        ('Marketing & Content', 'bi-megaphone', 'Digital marketing, SEO, social media growth, copywriting, and performance marketing.'),
        ('Finance & Accounting', 'bi-cash-coin', 'Financial planning, accounting, corporate treasury, and investment analysis.'),
        ('Healthcare & Life Sciences', 'bi-heart-pulse', 'Clinical healthcare, biomedical engineering, nursing, and telehealth systems.'),
        ('Human Resources', 'bi-people', 'Talent acquisition, organizational development, culture, and employee relations.'),
        ('Customer Success & Sales', 'bi-headset', 'Account management, business development, enterprise sales, and customer experience.')
    ]

    cat_map = {}
    for c_name, icon, c_desc in categories:
        cursor.execute("""
            INSERT INTO categories (name, icon, description) VALUES (?, ?, ?)
        """, (c_name, icon, c_desc))
        cat_map[c_name] = cursor.lastrowid

    # Seed Sample Jobs
    sample_jobs = [
        (
            employer_ids[0], cat_map['Software & IT'],
            'Senior Python / Backend Developer', 'Full-Time', 'Senior Level', 'San Francisco, CA (Hybrid)',
            135000, 165000, '$',
            'We are seeking a seasoned Senior Backend Engineer to architect, build, and maintain mission-critical backend services and high-throughput APIs.',
            'Architect scalable backend RESTful microservices in Python.\nOptimize PostgreSQL databases, caching layers, and asynchronous task queues.\nCollaborate closely with frontend engineers and DevOps on CI/CD pipelines.\nConduct code reviews and mentor junior engineering team members.',
            '5+ years professional backend development with Python (Flask, Django, or FastAPI).\nStrong experience with SQL (PostgreSQL/MySQL) schema design and optimization.\nFamiliarity with containerization (Docker) and AWS cloud services.\nSolid understanding of REST API principles and asynchronous programming.',
            'Competitive equity package\nComprehensive health, dental, and vision insurance\n401(k) with 5% employer match\n$2,500 annual professional development stipend\nFlexible work-from-home policy',
            '2026-11-30', 142
        ),
        (
            employer_ids[0], cat_map['Software & IT'],
            'DevOps & Infrastructure Engineer', 'Full-Time', 'Mid Level', 'Remote (US)',
            115000, 140000, '$',
            'Join our platform team to automate infrastructure deployment, improve monitoring observability, and guarantee 99.99% uptime for cloud customers.',
            'Manage Kubernetes clusters and Terraform infrastructure as code.\nBuild and optimize automated CI/CD deployment pipelines using GitHub Actions.\nImplement centralized monitoring, logging, and alerting systems.\nParticipate in on-call rotation and incident post-mortems.',
            '3+ years experience with Linux administration and AWS / GCP infrastructure.\nProficiency with Docker, Kubernetes, and Terraform.\nStrong scripting skills in Bash or Python.\nExperience with Prometheus, Grafana, or Datadog monitoring.',
            'Full remote flexibility\nHome office equipment reimbursement ($1,500)\nHealth insurance with 100% premium covered\nUnlimited PTO and wellness days',
            '2026-12-15', 98
        ),
        (
            employer_ids[1], cat_map['Data & Artificial Intelligence'],
            'Machine Learning Engineer (LLMs & NLP)', 'Full-Time', 'Senior Level', 'New York, NY (Hybrid)',
            145000, 185000, '$',
            'Work at the forefront of AI. You will fine-tune modern language models, implement retrieval-augmented generation (RAG) pipelines, and deploy scalable ML services.',
            'Develop, fine-tune, and deploy transformer-based models for production inference.\nDesign low-latency RAG architectures using vector databases.\nCollaborate with product teams to translate business requirements into ML solutions.\nBenchmark model performance, accuracy, and inference cost.',
            '4+ years practical experience with PyTorch, Hugging Face, and Python ML stack.\nDeep understanding of NLP, transformers, and prompt engineering strategies.\nExperience deploying models to production with Triton, FastAPI, or TorchServe.\nStrong mathematical foundation in statistics and linear algebra.',
            'Top-tier salary with stock options\nPremium medical and dental benefits\nCommuter transit benefits\nAnnual paid conference attendance anywhere in the world',
            '2026-12-01', 230
        ),
        (
            employer_ids[2], cat_map['Product & Design'],
            'Lead Product Designer (UI/UX)', 'Full-Time', 'Lead / Executive', 'Austin, TX / Remote',
            120000, 150000, '$',
            'Lead our digital product design initiatives. You will shape product aesthetics, design intuitive user experiences, and maintain our multi-platform design system.',
            'Own end-to-end design from customer discovery and wireframing to high-fidelity prototypes.\nMaintain and evolve our shared Figma design system component library.\nPartner with product managers and engineers to execute seamless feature launches.\nConduct usability studies and synthesize user feedback into actionable design iterations.',
            '5+ years UI/UX product design experience for responsive web and mobile apps.\nA stellar portfolio demonstrating clean aesthetic sense and thoughtful UX problem-solving.\nDeep mastery of Figma, prototyping, and design tokens.\nExcellent communication skills to articulate design decisions to stakeholders.',
            'Flexible remote work environment\nModern hardware setup of your choice\nMonthly wellness stipend\nGenerous parental leave policy',
            '2026-11-25', 185
        ),
        (
            employer_ids[1], cat_map['Software & IT'],
            'Frontend React Developer', 'Full-Time', 'Mid Level', 'Remote',
            95000, 125000, '$',
            'Build sleek, responsive, and blazing-fast user interfaces for our customer portal and real-time dashboard analytics.',
            'Write clean, accessible, and maintainable TypeScript / React code.\nIntegrate REST and WebSocket APIs into interactive client applications.\nOptimize page load speeds, Web Vitals, and responsive cross-browser layouts.\nContribute to component unit testing and Cypress end-to-end suites.',
            '3+ years hands-on experience with modern React, Hooks, and TypeScript.\nStrong grasp of HTML5, CSS3, modern CSS frameworks (Bootstrap, Tailwind).\nExperience with state management and REST API integrations.\nFamiliarity with Git and Agile development processes.',
            '100% Remote\nFlexible working hours\nHealth & Dental coverage\nContinuous learning budget',
            '2026-12-10', 114
        ),
        (
            employer_ids[2], cat_map['Marketing & Content'],
            'Digital Growth & Performance Marketer', 'Full-Time', 'Mid Level', 'Austin, TX',
            80000, 105000, '$',
            'Drive customer acquisition and brand visibility across paid channels, search engine optimization, email funnels, and organic growth campaigns.',
            'Plan and execute ROI-positive PPC, social, and search marketing campaigns.\nAnalyze conversion funnels, landing page bounce rates, and run A/B split tests.\nCollaborate with content creators to produce high-ranking SEO editorial guides.\nDeliver weekly KPI reports on CAC, LTV, and conversion rate trends.',
            '3+ years in growth marketing for B2B or consumer tech products.\nProven track record managing paid ad budgets on Google Ads and LinkedIn Ads.\nStrong proficiency in Google Analytics 4, Tag Manager, and Excel/SQL.\nCreative mindset with sharp analytical interpretation skills.',
            'Competitive bonus structure based on growth targets\nHealth insurance\nCatered lunches and snacks in office\nCompany retreat twice a year',
            '2026-11-20', 76
        ),
        (
            employer_ids[0], cat_map['Software & IT'],
            'Cybersecurity Operations Specialist', 'Full-Time', 'Senior Level', 'San Francisco, CA',
            130000, 160000, '$',
            'Protect our infrastructure, data assets, and application perimeter against evolving cyber threats and vulnerabilities.',
            'Monitor SIEM alerts, investigate suspicious traffic, and coordinate incident response.\nConduct periodic vulnerability scans, threat modeling, and code security audits.\nImplement zero-trust security policies and IAM access controls.\nEnsure compliance with SOC 2 Type II, ISO 27001, and GDPR standards.',
            '4+ years in cybersecurity operations or security engineering.\nCertifications such as CISSP, CEH, or AWS Security Specialty preferred.\nFamiliarity with cloud security controls (AWS IAM, GuardDuty, CloudTrail).\nSolid understanding of OWASP Top 10 vulnerabilities.',
            'Health, Vision & Dental coverage\nGym membership reimbursement\n401(k) matching\nRelocation assistance if needed',
            '2026-12-20', 88
        ),
        (
            employer_ids[1], cat_map['Customer Success & Sales'],
            'Enterprise Account Executive', 'Full-Time', 'Mid Level', 'New York, NY',
            90000, 130000, '$',
            'Drive net-new revenue by prospecting, qualifying, and closing strategic enterprise software subscriptions with Fortune 500 decision makers.',
            'Manage full sales cycle from initial discovery call to contract signing.\nDeliver compelling product demonstrations tailored to customer pain points.\nBuild and manage a healthy sales pipeline inside Salesforce CRM.\nCollaborate with customer success team for smooth client onboarding.',
            '3+ years enterprise SaaS quota-carrying sales experience.\nDemonstrated history of meeting or exceeding quarterly quota targets.\nExceptional presentation, negotiation, and relationship-building skills.\nExperience using Salesforce, LinkedIn Sales Navigator, and ZoomInfo.',
            'Uncapped commission structure\nFull benefits package\nCompany cell phone and travel stipend\nPresident’s Club rewards trip for top performers',
            '2026-12-05', 65
        )
    ]

    job_ids = []
    for job in sample_jobs:
        cursor.execute("""
            INSERT INTO jobs (
                employer_id, category_id, title, job_type, experience_level, location,
                salary_min, salary_max, salary_currency, description, responsibilities,
                requirements, benefits, status, deadline, views_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
        """, job)
        job_ids.append(cursor.lastrowid)

    # Seed Sample Applications
    # Alex applied for Senior Python Backend (job_ids[0]) and Frontend React Developer (job_ids[4])
    cursor.execute("""
        INSERT INTO applications (job_id, seeker_id, cover_letter, resume_filename, status, notes)
        VALUES (?, ?, ?, ?, 'Shortlisted', 'Strong candidate with impressive Python experience.')
    """, (
        job_ids[0], seeker_ids[0],
        'Dear Hiring Team,\n\nI am thrilled to apply for the Senior Python / Backend Developer role at TechCorp Solutions. With over 6 years of experience designing scalable microservices in Python and managing robust cloud infrastructures, I am confident I can make an immediate impact on your engineering initiatives.\n\nBest regards,\nAlex Rivera',
        'sample_resume.pdf'
    ))

    cursor.execute("""
        INSERT INTO applications (job_id, seeker_id, cover_letter, resume_filename, status, notes)
        VALUES (?, ?, ?, ?, 'Under Review', 'Reviewing portfolio.')
    """, (
        job_ids[4], seeker_ids[0],
        'Hello CloudScale team,\n\nI have extensive experience with React and TypeScript, building high-speed analytics dashboards. I would love the opportunity to contribute to your frontend applications.\n\nWarm regards,\nAlex Rivera',
        'sample_resume.pdf'
    ))

    # Sarah applied for Lead Product Designer (job_ids[3])
    cursor.execute("""
        INSERT INTO applications (job_id, seeker_id, cover_letter, resume_filename, status, notes)
        VALUES (?, ?, ?, ?, 'Accepted', 'Excellent portfolio, accepted after final interview round.')
    """, (
        job_ids[3], seeker_ids[1],
        'Hi DesignSpark Team,\n\nAs a passionate Product Designer with 5 years leading UI/UX projects and building enterprise design systems in Figma, I would be thrilled to join your design collective.\n\nSincerely,\nSarah Jenkins',
        'sample_resume.pdf'
    ))

    # Seed Saved Jobs
    cursor.execute("INSERT INTO saved_jobs (user_id, job_id) VALUES (?, ?)", (seeker_ids[0], job_ids[2]))
    cursor.execute("INSERT INTO saved_jobs (user_id, job_id) VALUES (?, ?)", (seeker_ids[0], job_ids[6]))
    cursor.execute("INSERT INTO saved_jobs (user_id, job_id) VALUES (?, ?)", (seeker_ids[1], job_ids[5]))

    # Seed Activity Logs
    cursor.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                   (1, 'SYSTEM_INIT', 'Database schema created and initial mock data seeded.'))

    conn.commit()

if __name__ == '__main__':
    print("Initializing database...")
    init_db(seed=True)
    print("Database initialized successfully!")
