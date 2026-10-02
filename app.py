import os
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db
from auth import login_required, get_current_user

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'online-job-portal-super-secret-key-2026')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
LOGO_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')

ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESUME_FOLDER'] = RESUME_FOLDER
app.config['LOGO_FOLDER'] = LOGO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

os.makedirs(RESUME_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.context_processor
def inject_global_data():
    current_user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, icon FROM categories ORDER BY name ASC")
    categories = cursor.fetchall()
    
    saved_count = 0
    applications_count = 0
    if current_user and current_user['role'] == 'seeker':
        cursor.execute("SELECT COUNT(*) as cnt FROM saved_jobs WHERE user_id = ?", (current_user['id'],))
        saved_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE seeker_id = ?", (current_user['id'],))
        applications_count = cursor.fetchone()['cnt']
    elif current_user and current_user['role'] == 'employer':
        cursor.execute("""
            SELECT COUNT(a.id) as cnt 
            FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE j.employer_id = ?
        """, (current_user['id'],))
        applications_count = cursor.fetchone()['cnt']
        
    conn.close()
    return {
        'current_user': current_user,
        'global_categories': categories,
        'saved_count': saved_count,
        'applications_count': applications_count,
        'current_year': datetime.now().year
    }

# -------------------------------------------------------------
# Home & Public Routes
# -------------------------------------------------------------
@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()

    # Metrics
    cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'Active'")
    total_jobs = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'employer' AND is_active = 1")
    total_companies = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'seeker' AND is_active = 1")
    total_candidates = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE status = 'Accepted'")
    total_hires = cursor.fetchone()['cnt']

    # Featured Jobs (up to 6 active)
    cursor.execute("""
        SELECT j.*, c.name as category_name, c.icon as category_icon,
               ep.company_name, ep.logo_filename, ep.company_location
        FROM jobs j
        JOIN categories c ON j.category_id = c.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        WHERE j.status = 'Active'
        ORDER BY j.created_at DESC
        LIMIT 6
    """)
    featured_jobs = cursor.fetchall()

    # Top categories with job count
    cursor.execute("""
        SELECT c.*, COUNT(j.id) as job_count
        FROM categories c
        LEFT JOIN jobs j ON c.id = j.category_id AND j.status = 'Active'
        GROUP BY c.id
        ORDER BY job_count DESC, c.name ASC
        LIMIT 8
    """)
    categories = cursor.fetchall()

    # Recent companies
    cursor.execute("""
        SELECT ep.*, u.name as recruiter_name, COUNT(j.id) as active_jobs_count
        FROM employer_profiles ep
        JOIN users u ON ep.user_id = u.id
        LEFT JOIN jobs j ON ep.user_id = j.employer_id AND j.status = 'Active'
        WHERE u.is_active = 1
        GROUP BY ep.id
        ORDER BY active_jobs_count DESC
        LIMIT 4
    """)
    featured_companies = cursor.fetchall()

    conn.close()

    return render_template(
        'index.html',
        total_jobs=total_jobs,
        total_companies=total_companies,
        total_candidates=total_candidates,
        total_hires=total_hires,
        featured_jobs=featured_jobs,
        categories=categories,
        featured_companies=featured_companies
    )

@app.route('/jobs')
def job_search():
    keyword = request.args.get('q', '').strip()
    category_id = request.args.get('category', '').strip()
    job_type = request.args.get('type', '').strip()
    experience = request.args.get('experience', '').strip()
    location = request.args.get('location', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    query = """
        SELECT j.*, c.name as category_name, c.icon as category_icon,
               ep.company_name, ep.logo_filename, ep.company_location
        FROM jobs j
        JOIN categories c ON j.category_id = c.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        WHERE j.status = 'Active'
    """
    params = []

    if keyword:
        query += " AND (j.title LIKE ? OR j.description LIKE ? OR ep.company_name LIKE ? OR j.requirements LIKE ?)"
        term = f"%{keyword}%"
        params.extend([term, term, term, term])

    if category_id and category_id.isdigit():
        query += " AND j.category_id = ?"
        params.append(int(category_id))

    if job_type:
        query += " AND j.job_type = ?"
        params.append(job_type)

    if experience:
        query += " AND j.experience_level = ?"
        params.append(experience)

    if location:
        query += " AND (j.location LIKE ? OR ep.company_location LIKE ?)"
        loc_term = f"%{location}%"
        params.extend([loc_term, loc_term])

    # Sorting
    if sort_by == 'highest_salary':
        query += " ORDER BY j.salary_max DESC NULLS LAST"
    elif sort_by == 'popular':
        query += " ORDER BY j.views_count DESC"
    else:
        query += " ORDER BY j.created_at DESC"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    jobs = cursor.fetchall()

    # Get user saved job IDs if seeker logged in
    user = get_current_user()
    saved_job_ids = set()
    applied_job_ids = set()
    if user and user['role'] == 'seeker':
        cursor.execute("SELECT job_id FROM saved_jobs WHERE user_id = ?", (user['id'],))
        saved_job_ids = {row['job_id'] for row in cursor.fetchall()}

        cursor.execute("SELECT job_id FROM applications WHERE seeker_id = ?", (user['id'],))
        applied_job_ids = {row['job_id'] for row in cursor.fetchall()}

    conn.close()

    return render_template(
        'jobs.html',
        jobs=jobs,
        keyword=keyword,
        selected_category=int(category_id) if category_id.isdigit() else '',
        selected_type=job_type,
        selected_experience=experience,
        selected_location=location,
        selected_sort=sort_by,
        saved_job_ids=saved_job_ids,
        applied_job_ids=applied_job_ids,
        total_results=len(jobs)
    )

@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    conn = get_db()
    cursor = conn.cursor()

    # Increment views
    cursor.execute("UPDATE jobs SET views_count = views_count + 1 WHERE id = ?", (job_id,))
    conn.commit()

    cursor.execute("""
        SELECT j.*, c.name as category_name, c.icon as category_icon,
               ep.company_name, ep.company_website, ep.company_location,
               ep.industry, ep.company_size, ep.company_description,
               ep.logo_filename, ep.founded_year, u.email as employer_email
        FROM jobs j
        JOIN categories c ON j.category_id = c.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        JOIN users u ON j.employer_id = u.id
        WHERE j.id = ?
    """, (job_id,))
    job = cursor.fetchone()

    if not job:
        conn.close()
        abort(404)

    # Check if current user saved or applied
    user = get_current_user()
    is_saved = False
    has_applied = False
    existing_application = None

    if user and user['role'] == 'seeker':
        cursor.execute("SELECT id FROM saved_jobs WHERE user_id = ? AND job_id = ?", (user['id'], job_id))
        is_saved = cursor.fetchone() is not None

        cursor.execute("SELECT * FROM applications WHERE seeker_id = ? AND job_id = ?", (user['id'], job_id))
        existing_application = cursor.fetchone()
        has_applied = existing_application is not None

    # Get seeker profile for quick apply prefill
    seeker_profile = None
    if user and user['role'] == 'seeker':
        cursor.execute("SELECT * FROM seeker_profiles WHERE user_id = ?", (user['id'],))
        seeker_profile = cursor.fetchone()

    # Similar Jobs (same category or type)
    cursor.execute("""
        SELECT j.*, ep.company_name, ep.logo_filename
        FROM jobs j
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        WHERE j.category_id = ? AND j.id != ? AND j.status = 'Active'
        ORDER BY j.created_at DESC
        LIMIT 3
    """, (job['category_id'], job_id))
    similar_jobs = cursor.fetchall()

    conn.close()

    return render_template(
        'job_detail.html',
        job=job,
        is_saved=is_saved,
        has_applied=has_applied,
        existing_application=existing_application,
        seeker_profile=seeker_profile,
        similar_jobs=similar_jobs
    )

@app.route('/companies/<int:employer_id>')
def company_profile(employer_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ep.*, u.name, u.email, u.phone, u.created_at as joined_at
        FROM employer_profiles ep
        JOIN users u ON ep.user_id = u.id
        WHERE ep.user_id = ? AND u.is_active = 1
    """, (employer_id,))
    company = cursor.fetchone()

    if not company:
        conn.close()
        abort(404)

    # Active jobs posted by this company
    cursor.execute("""
        SELECT j.*, c.name as category_name
        FROM jobs j
        JOIN categories c ON j.category_id = c.id
        WHERE j.employer_id = ? AND j.status = 'Active'
        ORDER BY j.created_at DESC
    """, (employer_id,))
    jobs = cursor.fetchall()

    conn.close()

    return render_template('company_profile.html', company=company, jobs=jobs)

# -------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('login.html')

            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['email'] = user['email']

            flash(f"Welcome back, {user['name']}!", 'success')

            next_page = request.args.get('next')
            if next_page and not next_page.startswith('//') and not next_page.startswith('http'):
                return redirect(next_page)

            if user['role'] == 'seeker':
                return redirect(url_for('seeker_dashboard'))
            elif user['role'] == 'employer':
                return redirect(url_for('employer_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/demo-login/<role>')
def demo_login(role):
    demo_emails = {
        'seeker': 'alex@example.com',
        'employer': 'techcorp@example.com',
        'admin': 'admin@portal.com'
    }

    email = demo_emails.get(role)
    if not email:
        flash('Invalid demo role selected.', 'danger')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['role'] = user['role']
        session['email'] = user['email']
        flash(f"Logged in as Demo {user['role'].capitalize()} ({user['name']})", 'info')

        if user['role'] == 'seeker':
            return redirect(url_for('seeker_dashboard'))
        elif user['role'] == 'employer':
            return redirect(url_for('employer_dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    flash('Demo user could not be loaded.', 'danger')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        role = request.form.get('role', 'seeker')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()

        # Extra employer fields
        company_name = request.form.get('company_name', '').strip()
        industry = request.form.get('industry', '').strip()
        company_location = request.form.get('company_location', '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        if role not in ('seeker', 'employer'):
            flash('Invalid role specified.', 'danger')
            return render_template('register.html')

        if role == 'employer' and not company_name:
            flash('Company name is required for employer registration.', 'danger')
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()

        # Check duplicate email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash('An account with this email already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        pwd_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, pwd_hash, role, phone))
        user_id = cursor.lastrowid

        if role == 'seeker':
            cursor.execute("""
                INSERT INTO seeker_profiles (user_id, title, bio, skills, location)
                VALUES (?, 'Job Seeker', '', '', '')
            """, (user_id,))
        elif role == 'employer':
            cursor.execute("""
                INSERT INTO employer_profiles (user_id, company_name, company_location, industry)
                VALUES (?, ?, ?, ?)
            """, (user_id, company_name, company_location, industry))

        conn.commit()
        conn.close()

        # Log user in
        session['user_id'] = user_id
        session['name'] = name
        session['role'] = role
        session['email'] = email

        flash('Registration successful! Welcome to the Online Job Portal.', 'success')
        if role == 'seeker':
            return redirect(url_for('seeker_profile'))
        else:
            return redirect(url_for('employer_dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))

# -------------------------------------------------------------
# Job Seeker Routes
# -------------------------------------------------------------
@app.route('/seeker/dashboard')
@login_required('seeker')
def seeker_dashboard():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    # Fetch applied jobs
    cursor.execute("""
        SELECT a.*, j.title as job_title, j.job_type, j.location as job_location,
               j.salary_min, j.salary_max, j.salary_currency,
               ep.company_name, ep.logo_filename, c.name as category_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        JOIN categories c ON j.category_id = c.id
        WHERE a.seeker_id = ?
        ORDER BY a.applied_at DESC
    """, (user['id'],))
    applications = cursor.fetchall()

    # Fetch saved jobs
    cursor.execute("""
        SELECT sj.created_at as saved_at, j.*, ep.company_name, ep.logo_filename, c.name as category_name
        FROM saved_jobs sj
        JOIN jobs j ON sj.job_id = j.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        JOIN categories c ON j.category_id = c.id
        WHERE sj.user_id = ?
        ORDER BY sj.created_at DESC
        LIMIT 5
    """, (user['id'],))
    saved_jobs = cursor.fetchall()

    # Seeker profile
    cursor.execute("SELECT * FROM seeker_profiles WHERE user_id = ?", (user['id'],))
    profile = cursor.fetchone()

    # Profile completeness score
    fields = [profile['title'], profile['bio'], profile['skills'], profile['education'], profile['location'], profile['resume_filename']]
    completed_fields = sum(1 for f in fields if f and str(f).strip())
    completeness = int((completed_fields / len(fields)) * 100)

    # Status counts
    status_counts = {'Pending': 0, 'Under Review': 0, 'Shortlisted': 0, 'Accepted': 0, 'Rejected': 0}
    for app_row in applications:
        st = app_row['status']
        if st in status_counts:
            status_counts[st] += 1

    conn.close()

    return render_template(
        'seeker_dashboard.html',
        profile=profile,
        applications=applications,
        saved_jobs=saved_jobs,
        completeness=completeness,
        status_counts=status_counts
    )

@app.route('/seeker/profile', methods=['GET', 'POST'])
@login_required('seeker')
def seeker_profile():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        title = request.form.get('title', '').strip()
        bio = request.form.get('bio', '').strip()
        skills = request.form.get('skills', '').strip()
        experience_years = request.form.get('experience_years', 0)
        education = request.form.get('education', '').strip()
        location = request.form.get('location', '').strip()
        website = request.form.get('website', '').strip()
        github = request.form.get('github', '').strip()
        linkedin = request.form.get('linkedin', '').strip()

        # Update users table
        cursor.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user['id']))

        # Handle resume upload
        resume_filename = None
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename != '' and allowed_file(file.filename, ALLOWED_RESUME_EXTENSIONS):
                ext = file.filename.rsplit('.', 1)[1].lower()
                clean_name = f"resume_{user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
                file_path = os.path.join(app.config['RESUME_FOLDER'], clean_name)
                file.save(file_path)
                resume_filename = clean_name

        if resume_filename:
            cursor.execute("""
                UPDATE seeker_profiles SET
                    title = ?, bio = ?, skills = ?, experience_years = ?, education = ?,
                    location = ?, resume_filename = ?, website = ?, github = ?, linkedin = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (title, bio, skills, experience_years, education, location, resume_filename, website, github, linkedin, user['id']))
        else:
            cursor.execute("""
                UPDATE seeker_profiles SET
                    title = ?, bio = ?, skills = ?, experience_years = ?, education = ?,
                    location = ?, website = ?, github = ?, linkedin = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (title, bio, skills, experience_years, education, location, website, github, linkedin, user['id']))

        conn.commit()
        conn.close()
        session['name'] = name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('seeker_profile'))

    cursor.execute("SELECT * FROM seeker_profiles WHERE user_id = ?", (user['id'],))
    profile = cursor.fetchone()
    conn.close()

    return render_template('seeker_profile.html', profile=profile, user=user)

@app.route('/seeker/saved')
@login_required('seeker')
def saved_jobs():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sj.id as saved_id, sj.created_at as saved_at,
               j.*, ep.company_name, ep.logo_filename, ep.company_location, c.name as category_name
        FROM saved_jobs sj
        JOIN jobs j ON sj.job_id = j.id
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        JOIN categories c ON j.category_id = c.id
        WHERE sj.user_id = ?
        ORDER BY sj.created_at DESC
    """, (user['id'],))
    saved_list = cursor.fetchall()
    conn.close()

    return render_template('saved_jobs.html', saved_jobs=saved_list)

@app.route('/jobs/<int:job_id>/apply', methods=['POST'])
@login_required('seeker')
def apply_job(job_id):
    user = get_current_user()
    cover_letter = request.form.get('cover_letter', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    # Check job validity
    cursor.execute("SELECT * FROM jobs WHERE id = ? AND status = 'Active'", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        flash('This job posting is no longer accepting applications.', 'danger')
        return redirect(url_for('job_search'))

    # Check already applied
    cursor.execute("SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?", (job_id, user['id']))
    if cursor.fetchone():
        conn.close()
        flash('You have already submitted an application for this position.', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))

    # Retrieve existing resume or save newly uploaded
    cursor.execute("SELECT resume_filename FROM seeker_profiles WHERE user_id = ?", (user['id'],))
    profile = cursor.fetchone()
    resume_file = profile['resume_filename'] if profile else None

    if 'new_resume' in request.files:
        file = request.files['new_resume']
        if file and file.filename != '' and allowed_file(file.filename, ALLOWED_RESUME_EXTENSIONS):
            ext = file.filename.rsplit('.', 1)[1].lower()
            clean_name = f"resume_{user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
            file.save(os.path.join(app.config['RESUME_FOLDER'], clean_name))
            resume_file = clean_name
            # also update profile resume
            cursor.execute("UPDATE seeker_profiles SET resume_filename = ? WHERE user_id = ?", (resume_file, user['id']))

    if not resume_file:
        conn.close()
        flash('Please upload your resume before submitting your application.', 'danger')
        return redirect(url_for('job_detail', job_id=job_id))

    cursor.execute("""
        INSERT INTO applications (job_id, seeker_id, cover_letter, resume_filename, status)
        VALUES (?, ?, ?, ?, 'Pending')
    """, (job_id, user['id'], cover_letter, resume_file))

    conn.commit()
    conn.close()

    flash('Your job application has been submitted successfully! Good luck.', 'success')
    return redirect(url_for('seeker_dashboard'))

@app.route('/jobs/<int:job_id>/save', methods=['POST'])
@login_required('seeker')
def toggle_save_job(job_id):
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM saved_jobs WHERE user_id = ? AND job_id = ?", (user['id'], job_id))
    existing = cursor.fetchone()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if existing:
        cursor.execute("DELETE FROM saved_jobs WHERE id = ?", (existing['id'],))
        conn.commit()
        conn.close()
        if is_ajax:
            return jsonify({'status': 'unsaved', 'message': 'Job removed from saved list.'})
        flash('Job removed from saved bookmarks.', 'info')
    else:
        cursor.execute("INSERT INTO saved_jobs (user_id, job_id) VALUES (?, ?)", (user['id'], job_id))
        conn.commit()
        conn.close()
        if is_ajax:
            return jsonify({'status': 'saved', 'message': 'Job saved to your bookmarks!'})
        flash('Job saved to your bookmarks!', 'success')

    return redirect(request.referrer or url_for('job_detail', job_id=job_id))

# -------------------------------------------------------------
# Employer Routes
# -------------------------------------------------------------
@app.route('/employer/dashboard')
@login_required('employer')
def employer_dashboard():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    # Employer profile
    cursor.execute("SELECT * FROM employer_profiles WHERE user_id = ?", (user['id'],))
    profile = cursor.fetchone()

    # Job listings
    cursor.execute("""
        SELECT j.*, c.name as category_name,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as applicant_count,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id AND status = 'Pending') as pending_count
        FROM jobs j
        JOIN categories c ON j.category_id = c.id
        WHERE j.employer_id = ?
        ORDER BY j.created_at DESC
    """, (user['id'],))
    jobs = cursor.fetchall()

    # Metrics
    total_jobs = len(jobs)
    active_jobs = sum(1 for j in jobs if j['status'] == 'Active')
    total_applicants = sum(j['applicant_count'] for j in jobs)
    pending_applicants = sum(j['pending_count'] for j in jobs)

    # Recent applications across all jobs
    cursor.execute("""
        SELECT a.*, j.title as job_title, u.name as candidate_name, u.email as candidate_email,
               sp.title as candidate_title, sp.experience_years
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.seeker_id = u.id
        LEFT JOIN seeker_profiles sp ON u.id = sp.user_id
        WHERE j.employer_id = ?
        ORDER BY a.applied_at DESC
        LIMIT 8
    """, (user['id'],))
    recent_applications = cursor.fetchall()

    conn.close()

    return render_template(
        'employer_dashboard.html',
        profile=profile,
        jobs=jobs,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applicants=total_applicants,
        pending_applicants=pending_applicants,
        recent_applications=recent_applications
    )

@app.route('/employer/jobs/new', methods=['GET', 'POST'])
@login_required('employer')
def post_job():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        job_type = request.form.get('job_type')
        experience_level = request.form.get('experience_level')
        location = request.form.get('location', '').strip()
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        salary_currency = request.form.get('salary_currency', '$')
        description = request.form.get('description', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        requirements = request.form.get('requirements', '').strip()
        benefits = request.form.get('benefits', '').strip()
        status = request.form.get('status', 'Active')
        deadline = request.form.get('deadline') or None

        if not title or not category_id or not job_type or not location or not description:
            flash('Please fill in all mandatory job fields.', 'danger')
            cursor.execute("SELECT * FROM categories ORDER BY name ASC")
            categories = cursor.fetchall()
            conn.close()
            return render_template('post_job.html', categories=categories, job=None)

        cursor.execute("""
            INSERT INTO jobs (
                employer_id, category_id, title, job_type, experience_level, location,
                salary_min, salary_max, salary_currency, description, responsibilities,
                requirements, benefits, status, deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user['id'], category_id, title, job_type, experience_level, location,
            salary_min, salary_max, salary_currency, description, responsibilities,
            requirements, benefits, status, deadline
        ))
        conn.commit()
        conn.close()

        flash('Job posting published successfully!', 'success')
        return redirect(url_for('employer_dashboard'))

    cursor.execute("SELECT * FROM categories ORDER BY name ASC")
    categories = cursor.fetchall()
    conn.close()

    return render_template('post_job.html', categories=categories, job=None)

@app.route('/employer/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required('employer')
def edit_job(job_id):
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id = ? AND employer_id = ?", (job_id, user['id']))
    job = cursor.fetchone()

    if not job:
        conn.close()
        flash('Job not found or access denied.', 'danger')
        return redirect(url_for('employer_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        job_type = request.form.get('job_type')
        experience_level = request.form.get('experience_level')
        location = request.form.get('location', '').strip()
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        salary_currency = request.form.get('salary_currency', '$')
        description = request.form.get('description', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        requirements = request.form.get('requirements', '').strip()
        benefits = request.form.get('benefits', '').strip()
        status = request.form.get('status', 'Active')
        deadline = request.form.get('deadline') or None

        cursor.execute("""
            UPDATE jobs SET
                category_id = ?, title = ?, job_type = ?, experience_level = ?, location = ?,
                salary_min = ?, salary_max = ?, salary_currency = ?, description = ?,
                responsibilities = ?, requirements = ?, benefits = ?, status = ?,
                deadline = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND employer_id = ?
        """, (
            category_id, title, job_type, experience_level, location,
            salary_min, salary_max, salary_currency, description, responsibilities,
            requirements, benefits, status, deadline, job_id, user['id']
        ))
        conn.commit()
        conn.close()

        flash('Job posting updated successfully.', 'success')
        return redirect(url_for('employer_dashboard'))

    cursor.execute("SELECT * FROM categories ORDER BY name ASC")
    categories = cursor.fetchall()
    conn.close()

    return render_template('post_job.html', categories=categories, job=job)

@app.route('/employer/jobs/<int:job_id>/delete', methods=['POST'])
@login_required('employer')
def delete_job(job_id):
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM jobs WHERE id = ? AND employer_id = ?", (job_id, user['id']))
    conn.commit()
    conn.close()

    flash('Job posting deleted successfully.', 'info')
    return redirect(url_for('employer_dashboard'))

@app.route('/employer/jobs/<int:job_id>/applicants')
@login_required('employer')
def job_applicants(job_id):
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    # Verify ownership
    cursor.execute("SELECT * FROM jobs WHERE id = ? AND employer_id = ?", (job_id, user['id']))
    job = cursor.fetchone()

    if not job:
        conn.close()
        flash('Job not found or access denied.', 'danger')
        return redirect(url_for('employer_dashboard'))

    # Fetch applicants with full profile details
    cursor.execute("""
        SELECT a.*, u.name as candidate_name, u.email as candidate_email, u.phone as candidate_phone,
               sp.title as candidate_title, sp.skills as candidate_skills,
               sp.experience_years, sp.education, sp.location as candidate_location,
               sp.website, sp.github, sp.linkedin
        FROM applications a
        JOIN users u ON a.seeker_id = u.id
        LEFT JOIN seeker_profiles sp ON u.id = sp.user_id
        WHERE a.job_id = ?
        ORDER BY a.applied_at DESC
    """, (job_id,))
    applicants = cursor.fetchall()

    conn.close()

    return render_template('job_applicants.html', job=job, applicants=applicants)

@app.route('/employer/application/<int:app_id>/status', methods=['POST'])
@login_required('employer')
def update_application_status(app_id):
    user = get_current_user()
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')

    valid_statuses = ('Pending', 'Under Review', 'Shortlisted', 'Accepted', 'Rejected')
    if new_status not in valid_statuses:
        flash('Invalid application status.', 'danger')
        return redirect(request.referrer or url_for('employer_dashboard'))

    conn = get_db()
    cursor = conn.cursor()

    # Check that this application belongs to a job posted by this employer
    cursor.execute("""
        SELECT a.id, a.job_id 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ? AND j.employer_id = ?
    """, (app_id, user['id']))
    app_record = cursor.fetchone()

    if not app_record:
        conn.close()
        flash('Application not found or unauthorized.', 'danger')
        return redirect(url_for('employer_dashboard'))

    cursor.execute("""
        UPDATE applications SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, notes, app_id))
    conn.commit()
    conn.close()

    flash(f'Application status updated to "{new_status}".', 'success')
    return redirect(request.referrer or url_for('job_applicants', job_id=app_record['job_id']))

@app.route('/employer/profile', methods=['GET', 'POST'])
@login_required('employer')
def employer_profile():
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        company_website = request.form.get('company_website', '').strip()
        company_location = request.form.get('company_location', '').strip()
        industry = request.form.get('industry', '').strip()
        company_size = request.form.get('company_size', '').strip()
        company_description = request.form.get('company_description', '').strip()
        founded_year = request.form.get('founded_year') or None
        phone = request.form.get('phone', '').strip()

        # Update contact phone in users
        cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (phone, user['id']))

        # Handle logo upload
        logo_filename = None
        if 'company_logo' in request.files:
            file = request.files['company_logo']
            if file and file.filename != '' and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
                ext = file.filename.rsplit('.', 1)[1].lower()
                clean_name = f"logo_{user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(app.config['LOGO_FOLDER'], clean_name))
                logo_filename = clean_name

        if logo_filename:
            cursor.execute("""
                UPDATE employer_profiles SET
                    company_name = ?, company_website = ?, company_location = ?, industry = ?,
                    company_size = ?, company_description = ?, founded_year = ?, logo_filename = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (company_name, company_website, company_location, industry, company_size, company_description, founded_year, logo_filename, user['id']))
        else:
            cursor.execute("""
                UPDATE employer_profiles SET
                    company_name = ?, company_website = ?, company_location = ?, industry = ?,
                    company_size = ?, company_description = ?, founded_year = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (company_name, company_website, company_location, industry, company_size, company_description, founded_year, user['id']))

        conn.commit()
        conn.close()

        flash('Company profile updated successfully.', 'success')
        return redirect(url_for('employer_profile'))

    cursor.execute("SELECT * FROM employer_profiles WHERE user_id = ?", (user['id'],))
    profile = cursor.fetchone()
    conn.close()

    return render_template('company_profile_edit.html', profile=profile, user=user)

# -------------------------------------------------------------
# Admin Routes
# -------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'seeker'")
    total_seekers = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'employer'")
    total_employers = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM jobs")
    total_jobs = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM applications")
    total_applications = cursor.fetchone()['cnt']

    # All users
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    all_users = cursor.fetchall()

    # All jobs with employer details
    cursor.execute("""
        SELECT j.*, ep.company_name, c.name as category_name,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as app_count
        FROM jobs j
        JOIN employer_profiles ep ON j.employer_id = ep.user_id
        JOIN categories c ON j.category_id = c.id
        ORDER BY j.created_at DESC
    """)
    all_jobs = cursor.fetchall()

    # Categories
    cursor.execute("""
        SELECT c.*, (SELECT COUNT(*) FROM jobs WHERE category_id = c.id) as job_count
        FROM categories c
        ORDER BY name ASC
    """)
    categories = cursor.fetchall()

    # Activity logs
    cursor.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 20")
    logs = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_seekers=total_seekers,
        total_employers=total_employers,
        total_jobs=total_jobs,
        total_applications=total_applications,
        users=all_users,
        jobs=all_jobs,
        categories=categories,
        logs=logs
    )

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required('admin')
def admin_toggle_user(user_id):
    if user_id == session.get('user_id'):
        flash('Cannot deactivate yourself.', 'warning')
        return redirect(url_for('admin_dashboard'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active, name FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()

    if target:
        new_status = 0 if target['is_active'] == 1 else 1
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        action_text = "activated" if new_status == 1 else "deactivated"
        cursor.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                       (session.get('user_id'), 'USER_STATUS_CHANGE', f"User {target['name']} ({user_id}) was {action_text}."))
        conn.commit()
        flash(f"User {target['name']} has been {action_text}.", 'info')

    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/jobs/<int:job_id>/toggle-status', methods=['POST'])
@login_required('admin')
def admin_toggle_job(job_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status, title FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()

    if job:
        new_status = 'Closed' if job['status'] == 'Active' else 'Active'
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
        cursor.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                       (session.get('user_id'), 'JOB_STATUS_CHANGE', f"Job '{job['title']}' status updated to {new_status}."))
        conn.commit()
        flash(f"Job status changed to {new_status}.", 'info')

    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories/add', methods=['POST'])
@login_required('admin')
def admin_add_category():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'bi-briefcase').strip()
    description = request.form.get('description', '').strip()

    if name:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO categories (name, icon, description) VALUES (?, ?, ?)", (name, icon, description))
            cursor.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                           (session.get('user_id'), 'CATEGORY_ADDED', f"Category '{name}' created."))
            conn.commit()
            flash(f"Category '{name}' added successfully.", 'success')
        except Exception:
            flash(f"Category '{name}' already exists or could not be added.", 'danger')
        conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories/<int:cat_id>/delete', methods=['POST'])
@login_required('admin')
def admin_delete_category(cat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat = cursor.fetchone()
    if cat:
        cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        cursor.execute("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                       (session.get('user_id'), 'CATEGORY_DELETED', f"Category '{cat['name']}' deleted."))
        conn.commit()
        flash(f"Category '{cat['name']}' deleted.", 'info')
    conn.close()
    return redirect(url_for('admin_dashboard'))

# -------------------------------------------------------------
# File Serving
# -------------------------------------------------------------
@app.route('/uploads/resumes/<filename>')
@login_required()
def download_resume(filename):
    # Only allow employers, admins, or the candidate themselves
    user = get_current_user()
    conn = get_db()
    cursor = conn.cursor()

    allowed = False
    if user['role'] in ('admin', 'employer'):
        allowed = True
    else:
        cursor.execute("SELECT id FROM seeker_profiles WHERE user_id = ? AND resume_filename = ?", (user['id'], filename))
        if cursor.fetchone():
            allowed = True
        else:
            cursor.execute("SELECT id FROM applications WHERE seeker_id = ? AND resume_filename = ?", (user['id'], filename))
            if cursor.fetchone():
                allowed = True

    conn.close()

    if not allowed:
        abort(403)

    return send_from_directory(app.config['RESUME_FOLDER'], filename, as_attachment=True)

# -------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', message="An internal server error occurred. Please try again."), 500

if __name__ == '__main__':
    init_db(seed=True)
    print("Online Job Portal server running at http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
