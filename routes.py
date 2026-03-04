from flask import session, render_template, request, redirect, url_for, flash, send_file, jsonify
from urllib.parse import urlparse
from io import BytesIO
from datetime import datetime
import os
import qrcode
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user
from models import User, Form, Submission, LaborHours, Job, JobEligibility, JobApplication, JobSignup

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
ALLOWED_MIMETYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png'
}

def allowed_file(filename, mimetype):
    if not filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return extension in ALLOWED_EXTENSIONS and mimetype in ALLOWED_MIMETYPES

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('parent_dashboard'))
    return render_template('landing.html')

@app.route('/parent/dashboard')
@require_login
def parent_dashboard():
    active_forms = Form.query.filter_by(is_active=True).order_by(Form.deadline.asc()).all()
    user_submissions = {s.form_id: s for s in current_user.submissions}
    
    pending_forms = []
    completed_forms = []
    
    for form in active_forms:
        if form.id in user_submissions:
            completed_forms.append({
                'form': form,
                'submission': user_submissions[form.id]
            })
        else:
            pending_forms.append(form)
    
    # Check verification status for the UI
    user_eligibilities = [e.category for e in current_user.job_eligibilities] if hasattr(current_user, 'job_eligibilities') else [e.category for e in JobEligibility.query.filter_by(user_id=current_user.id).all()]
    is_verified_child = 'child_interaction' in user_eligibilities
    
    # Get the latest application for child interaction
    child_app = JobApplication.query.filter_by(
        user_id=current_user.id, 
        category='child_interaction'
    ).order_by(JobApplication.submitted_at.desc()).first()
    
    # Status logic for individual components
    # Background Check
    bg_status = 'not_submitted'
    if is_verified_child:
        bg_status = 'approved'
    elif child_app:
        if child_app.status == 'pending':
            bg_status = 'pending'
        elif child_app.status == 'rejected':
            bg_status = 'rejected'
            
    # Fingerprints
    fp_status = 'not_submitted'
    if is_verified_child:
        fp_status = 'approved'
    elif child_app and child_app.fingerprint_file_data:
        if child_app.status == 'pending':
            fp_status = 'pending'
        elif child_app.status == 'rejected':
            fp_status = 'rejected'

    return render_template('parent_dashboard.html', 
                         pending_forms=pending_forms,
                         completed_forms=completed_forms,
                         is_verified_child=is_verified_child,
                         bg_status=bg_status,
                         fp_status=fp_status)

@app.route('/parent/submit/<int:form_id>', methods=['GET', 'POST'])
@require_login
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    if request.method == 'POST':
        content = request.form.get('content', '')
        file = request.files.get('file')
        
        if file and file.filename:
            if not allowed_file(file.filename, file.content_type):
                flash('Invalid file type. Only PDF, DOC, DOCX, JPG, and PNG files are allowed.', 'danger')
                return redirect(url_for('submit_form', form_id=form_id))
        
        existing = Submission.query.filter_by(form_id=form_id, user_id=current_user.id).first()
        if existing:
            existing.content = content
            existing.submitted_at = datetime.now()
            if file and file.filename:
                existing.file_data = file.read()
                existing.file_name = file.filename
                existing.file_type = file.content_type
            submission = existing
        else:
            submission = Submission(
                form_id=form_id,
                user_id=current_user.id,
                content=content
            )
            if file and file.filename:
                submission.file_data = file.read()
                submission.file_name = file.filename
                submission.file_type = file.content_type
            db.session.add(submission)
        
        db.session.commit()
        flash('Your submission has been saved successfully!', 'success')
        return redirect(url_for('parent_dashboard'))
    
    existing_submission = Submission.query.filter_by(form_id=form_id, user_id=current_user.id).first()
    return render_template('submit_form.html', form=form, submission=existing_submission)

@app.route('/parent/profile')
@require_login
def parent_profile():
    return render_template('parent_profile.html')

@app.route('/parent/profile/update', methods=['POST'])
@require_login
def update_profile():
    classroom = request.form.get('classroom')
    if classroom:
        current_user.classroom = classroom
        db.session.commit()
        flash(f'Your classroom has been updated to {classroom}', 'success')
    else:
        flash('Please select a classroom', 'danger')
    return redirect(url_for('parent_profile'))

@app.route('/admin/dashboard')
@require_login
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    selected_classroom = request.args.get('classroom', '')
    
    forms = Form.query.order_by(Form.deadline.desc()).all()
    total_users = User.query.count()
    total_submissions = Submission.query.count()
    
    all_classrooms = db.session.query(User.classroom).filter(User.classroom.isnot(None)).distinct().order_by(User.classroom).all()
    classrooms = [c[0] for c in all_classrooms if c[0]]
    
    return render_template('admin_dashboard.html', 
                         forms=forms,
                         total_users=total_users,
                         total_submissions=total_submissions,
                         classrooms=classrooms,
                         selected_classroom=selected_classroom)

@app.route('/admin/form/create', methods=['GET', 'POST'])
@require_login
def create_form():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        
        if not deadline_str:
            flash('Please set a deadline for this form.', 'danger')
            return redirect(url_for('create_form'))
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid deadline format. Please try again.', 'danger')
            return redirect(url_for('create_form'))
        
        form = Form(
            title=title,
            description=description,
            deadline=deadline
        )
        db.session.add(form)
        db.session.commit()
        
        flash('Form created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_form.html')

@app.route('/admin/form/<int:form_id>/submissions')
@require_login
def view_submissions(form_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    selected_classroom = request.args.get('classroom', '')
    
    form = Form.query.get_or_404(form_id)
    
    query = Submission.query.filter_by(form_id=form_id).join(User)
    if selected_classroom:
        query = query.filter(User.classroom == selected_classroom)
    submissions = query.all()
    
    all_classrooms = db.session.query(User.classroom).filter(User.classroom.isnot(None)).distinct().order_by(User.classroom).all()
    classrooms = [c[0] for c in all_classrooms if c[0]]
    
    return render_template('view_submissions.html', 
                         form=form, 
                         submissions=submissions,
                         classrooms=classrooms,
                         selected_classroom=selected_classroom)

@app.route('/admin/form/<int:form_id>/toggle')
@require_login
def toggle_form(form_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    form = Form.query.get_or_404(form_id)
    form.is_active = not form.is_active
    db.session.commit()
    
    status = "activated" if form.is_active else "deactivated"
    flash(f'Form has been {status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/form/<int:form_id>/delete', methods=['POST'])
@require_login
def delete_form(form_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    form = Form.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    
    flash('Form deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/download/<int:submission_id>')
@require_login
def download_file(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    
    if not current_user.is_admin and submission.user_id != current_user.id:
        flash('You do not have permission to access this file.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    if not submission.file_data:
        flash('No file attached to this submission.', 'warning')
        referrer = request.referrer
        if referrer:
            parsed = urlparse(referrer)
            if parsed.netloc and parsed.netloc != request.host:
                referrer = None
        return redirect(referrer or url_for('parent_dashboard'))
    
    return send_file(
        BytesIO(submission.file_data),
        download_name=submission.file_name,
        as_attachment=True,
        mimetype=submission.file_type
    )

@app.route('/parent/labor-hours')
@require_login
def parent_labor_hours():
    labor_records = LaborHours.query.filter_by(user_id=current_user.id).order_by(LaborHours.created_at.desc()).all()
    active_session = LaborHours.query.filter_by(user_id=current_user.id, status='checked_in').first()
    total_hours = sum([record.hours_worked for record in labor_records if record.hours_worked])

    is_verified_child = JobEligibility.query.filter_by(
        user_id=current_user.id, category='child_interaction'
    ).first() is not None

    all_jobs = Job.query.filter_by(is_active=True).order_by(Job.title).all()
    available_jobs = [
        j for j in all_jobs
        if j.category == 'general' or (j.category == 'child_interaction' and is_verified_child)
    ]

    return render_template('parent_labor_hours.html',
                         labor_records=labor_records,
                         active_session=active_session,
                         total_hours=total_hours,
                         available_jobs=available_jobs)

@app.route('/parent/labor/check-in', methods=['POST'])
@require_login
def labor_check_in():
    task_description = request.form.get('task_description')
    custom_task = request.form.get('custom_task')
    
    if task_description in ('Custom', 'Other') and custom_task:
        task_description = custom_task
    
    if not task_description:
        flash('Please provide a task description.', 'danger')
        return redirect(url_for('parent_labor_hours'))
    
    active_session = LaborHours.query.filter_by(user_id=current_user.id, status='checked_in').first()
    if active_session:
        flash('You already have an active work session. Please check out first.', 'warning')
        return redirect(url_for('parent_labor_hours'))
    
    verification_code = LaborHours.generate_verification_code()
    labor_session = LaborHours(
        user_id=current_user.id,
        task_description=task_description,
        verification_code=verification_code,
        check_in_time=datetime.now(),
        status='checked_in'
    )
    db.session.add(labor_session)
    db.session.commit()
    
    flash('Successfully checked in! Show your QR code to an administrator when finished.', 'success')
    return redirect(url_for('view_labor_qr', labor_id=labor_session.id))

@app.route('/parent/labor/<int:labor_id>/check-out', methods=['POST'])
@require_login
def labor_check_out(labor_id):
    labor_session = LaborHours.query.get_or_404(labor_id)
    
    if labor_session.user_id != current_user.id:
        flash('You do not have permission to access this session.', 'danger')
        return redirect(url_for('parent_labor_hours'))
    
    if labor_session.status != 'checked_in':
        flash('This session is not active.', 'warning')
        return redirect(url_for('parent_labor_hours'))
    
    labor_session.check_out_time = datetime.now()
    labor_session.hours_worked = labor_session.calculate_hours()
    labor_session.status = 'pending_verification'
    db.session.commit()
    
    flash('Checked out successfully! Your hours are pending admin verification.', 'success')
    return redirect(url_for('parent_labor_hours'))

@app.route('/parent/labor/<int:labor_id>/qr')
@require_login
def view_labor_qr(labor_id):
    labor_session = LaborHours.query.get_or_404(labor_id)
    
    if labor_session.user_id != current_user.id:
        flash('You do not have permission to access this session.', 'danger')
        return redirect(url_for('parent_labor_hours'))
    
    return render_template('labor_qr_code.html', labor_session=labor_session)

@app.route('/labor/<int:labor_id>/qr-image')
@require_login
def generate_qr_code(labor_id):
    labor_session = LaborHours.query.get_or_404(labor_id)
    
    if labor_session.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to access this QR code.', 'danger')
        return redirect(url_for('index'))
    
    qr_data = f"{request.url_root}verify/{labor_session.verification_code}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/admin/labor-verification')
@require_login
def admin_labor_verification():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    pending_sessions = LaborHours.query.filter_by(status='pending_verification').order_by(LaborHours.check_out_time.desc()).all()
    verified_sessions = LaborHours.query.filter(LaborHours.status.in_(['verified', 'rejected'])).order_by(LaborHours.admin_verified_at.desc()).limit(50).all()
    
    return render_template('admin_labor_verification.html',
                         pending_sessions=pending_sessions,
                         verified_sessions=verified_sessions)

@app.route('/api/verify-code/<code>')
@require_login
def api_verify_code(code):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    labor_session = LaborHours.query.filter_by(verification_code=code.upper()).first()
    
    if not labor_session:
        return jsonify({'error': 'Invalid verification code'}), 404
    
    return jsonify({
        'id': labor_session.id,
        'parent_name': f"{labor_session.user.first_name} {labor_session.user.last_name or ''}".strip() or labor_session.user.email,
        'task': labor_session.task_description,
        'check_in': labor_session.check_in_time.strftime('%Y-%m-%d %I:%M %p'),
        'check_out': labor_session.check_out_time.strftime('%Y-%m-%d %I:%M %p') if labor_session.check_out_time else 'Not checked out',
        'hours': labor_session.hours_worked,
        'status': labor_session.status
    })

@app.route('/admin/labor/<int:labor_id>/verify', methods=['POST'])
@require_login
def admin_verify_labor(labor_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    labor_session = LaborHours.query.get_or_404(labor_id)
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action == 'verify':
        labor_session.status = 'verified'
        labor_session.admin_verified_at = datetime.now()
        labor_session.verified_by_admin_id = current_user.id
        labor_session.admin_notes = notes
        flash('Labor hours verified successfully!', 'success')
    elif action == 'reject':
        labor_session.status = 'rejected'
        labor_session.admin_verified_at = datetime.now()
        labor_session.verified_by_admin_id = current_user.id
        labor_session.admin_notes = notes
        flash('Labor hours rejected.', 'info')
    
    db.session.commit()
    return redirect(url_for('admin_labor_verification'))

@app.route('/admin/make-me-admin', methods=['POST'])
@require_login
def make_admin():
    admin_emails = os.environ.get('ADMIN_EMAILS', '').split(',')
    admin_emails = [email.strip().lower() for email in admin_emails if email.strip()]
    
    if current_user.email and current_user.email.lower() in admin_emails:
        current_user.is_admin = True
        db.session.commit()
        flash('Admin privileges granted!', 'success')
    else:
        flash('You are not authorized to become an admin.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/debug/auth-status')
def debug_auth_status():
    """Debugging route to check authentication status"""
    admin_emails_list = [email.strip().lower() for email in os.environ.get('ADMIN_EMAILS', '').split(',') if email.strip()]
    status = {
        'authenticated': current_user.is_authenticated if current_user else False,
        'is_admin': current_user.is_admin if current_user.is_authenticated else False,
        'email': current_user.email if current_user.is_authenticated else None,
        'admin_emails_configured': len(admin_emails_list) > 0,
        'admin_emails_count': len(admin_emails_list),
        'repl_id_configured': os.environ.get('REPL_ID', '') != '',
        'issuer_url': os.environ.get('ISSUER_URL', 'https://replit.com/oidc (default)'),
    }
    return jsonify(status)

@app.route('/test-login')
def test_login_page():
    """Test page to try login"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Test - Saint Philip Neri</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .btn { display: inline-block; padding: 15px 30px; background: #dc2626; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
            .status { background: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0; }
            h1 { color: #1f2937; }
        </style>
    </head>
    <body>
        <h1>🔐 Login Test</h1>
        <p>Click the button below to test Replit Auth login:</p>
        <a href="/auth/replit_auth" class="btn">Test Login</a>
        
        <div class="status">
            <h3>Current Status:</h3>
            <p id="status">Loading...</p>
        </div>
        
        <p><a href="/">← Back to Home</a></p>
        
        <script>
            fetch('/debug/auth-status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').innerHTML = `
                        <strong>Authenticated:</strong> ${data.authenticated}<br>
                        <strong>Is Admin:</strong> ${data.is_admin}<br>
                        <strong>Email:</strong> ${data.email || 'Not logged in'}<br>
                        <strong>Admin Emails Configured:</strong> ${data.admin_emails_configured} (${data.admin_emails_count} emails)<br>
                        <strong>REPL_ID Set:</strong> ${data.repl_id_configured}
                    `;
                });
        </script>
    </body>
    </html>
    '''

@app.route('/parent/service-log/print')
@require_login
def print_service_log():
    labor_records = LaborHours.query.filter_by(user_id=current_user.id).order_by(LaborHours.check_in_time.desc()).all()
    total_hours = sum([record.hours_worked for record in labor_records if record.hours_worked and record.status == 'verified'])
    return render_template('print_service_log.html', labor_records=labor_records, total_hours=total_hours)

@app.route('/parent/service-log/csv')
@require_login
def export_service_log_csv():
    import csv
    from io import StringIO
    
    labor_records = LaborHours.query.filter_by(user_id=current_user.id).order_by(LaborHours.check_in_time.desc()).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Task', 'Check In', 'Check Out', 'Hours', 'Status', 'Admin Notes'])
    
    for record in labor_records:
        writer.writerow([
            record.check_in_time.strftime('%Y-%m-%d'),
            record.task_description,
            record.check_in_time.strftime('%I:%M %p'),
            record.check_out_time.strftime('%I:%M %p') if record.check_out_time else 'N/A',
            f"{record.hours_worked:.2f}" if record.hours_worked else '0.00',
            record.status.replace('_', ' ').title(),
            record.admin_notes or ''
        ])
    
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'service_hours_{current_user.first_name}_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/parent/service-log/monthly')
@require_login
def monthly_summary_report():
    from collections import defaultdict
    
    labor_records = LaborHours.query.filter_by(user_id=current_user.id).filter(
        LaborHours.status == 'verified'
    ).order_by(LaborHours.check_in_time.desc()).all()
    
    monthly_data = defaultdict(lambda: {'hours': 0, 'sessions': 0, 'tasks': []})
    
    for record in labor_records:
        if record.hours_worked:
            month_key = record.check_in_time.strftime('%Y-%m')
            month_name = record.check_in_time.strftime('%B %Y')
            monthly_data[month_key]['month_name'] = month_name
            monthly_data[month_key]['hours'] += record.hours_worked
            monthly_data[month_key]['sessions'] += 1
            monthly_data[month_key]['tasks'].append({
                'date': record.check_in_time.strftime('%b %d, %Y'),
                'task': record.task_description,
                'hours': record.hours_worked
            })
    
    sorted_months = sorted(monthly_data.items(), reverse=True)
    
    return render_template('monthly_summary.html', monthly_data=sorted_months)

@app.route('/admin/service-hours-dashboard')
@require_login
def admin_service_hours_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    selected_classroom = request.args.get('classroom', '')
    
    query = LaborHours.query.join(User)
    if selected_classroom:
        query = query.filter(User.classroom == selected_classroom)
    all_labor_records = query.order_by(LaborHours.check_in_time.desc()).all()
    
    parent_summaries = {}
    for record in all_labor_records:
        user_id = record.user_id
        if user_id not in parent_summaries:
            parent_summaries[user_id] = {
                'name': f"{record.user.first_name} {record.user.last_name or ''}".strip() or record.user.email,
                'email': record.user.email,
                'classroom': record.user.classroom or 'Not set',
                'total_hours': 0,
                'verified_hours': 0,
                'pending_hours': 0,
                'sessions': 0
            }
        
        parent_summaries[user_id]['sessions'] += 1
        if record.hours_worked:
            parent_summaries[user_id]['total_hours'] += record.hours_worked
            if record.status == 'verified':
                parent_summaries[user_id]['verified_hours'] += record.hours_worked
            elif record.status == 'pending_verification':
                parent_summaries[user_id]['pending_hours'] += record.hours_worked
    
    all_classrooms = db.session.query(User.classroom).filter(User.classroom.isnot(None)).distinct().order_by(User.classroom).all()
    classrooms = [c[0] for c in all_classrooms if c[0]]
    
    return render_template('admin_service_dashboard.html', 
                         parent_summaries=parent_summaries.values(),
                         all_labor_records=all_labor_records,
                         classrooms=classrooms,
                         selected_classroom=selected_classroom)

@app.route('/parent/jobs')
@require_login
def parent_view_jobs():
    jobs = Job.query.filter_by(is_active=True).order_by(Job.created_at.desc()).all()

    user_eligibilities = [e.category for e in JobEligibility.query.filter_by(user_id=current_user.id).all()]
    is_verified_child = 'child_interaction' in user_eligibilities
    pending_child_app = JobApplication.query.filter_by(
        user_id=current_user.id,
        category='child_interaction',
        status='pending'
    ).first()

    user_signups = {s.job_id for s in JobSignup.query.filter_by(user_id=current_user.id).all()}

    return render_template('parent_jobs.html',
                         jobs=jobs,
                         is_verified_child=is_verified_child,
                         pending_child_app=pending_child_app,
                         user_signups=user_signups)

@app.route('/parent/jobs/<int:job_id>/signup', methods=['POST'])
@require_login
def signup_for_job(job_id):
    job = Job.query.get_or_404(job_id)
    if not job.is_active:
        flash('This job is no longer available.', 'warning')
        return redirect(url_for('parent_view_jobs'))

    if job.category == 'child_interaction':
        is_verified = JobEligibility.query.filter_by(user_id=current_user.id, category='child_interaction').first()
        if not is_verified:
            flash('You need to be verified for child-interaction jobs before signing up.', 'danger')
            return redirect(url_for('parent_view_jobs'))

    existing = JobSignup.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if existing:
        flash('You are already signed up for this job.', 'info')
        return redirect(url_for('parent_view_jobs'))

    signup = JobSignup(job_id=job_id, user_id=current_user.id)
    db.session.add(signup)
    db.session.commit()
    flash(f'You are signed up for "{job.title}"!', 'success')
    return redirect(url_for('parent_view_jobs'))

@app.route('/parent/jobs/<int:job_id>/unsignup', methods=['POST'])
@require_login
def unsignup_from_job(job_id):
    signup = JobSignup.query.filter_by(job_id=job_id, user_id=current_user.id).first()
    if signup:
        db.session.delete(signup)
        db.session.commit()
        flash('You have cancelled your sign-up.', 'info')
    return redirect(url_for('parent_view_jobs'))

@app.route('/admin/jobs')
@require_login
def admin_jobs():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    jobs = Job.query.filter_by(is_active=True).order_by(Job.created_at.desc()).all()
    signup_counts = {
        job.id: JobSignup.query.filter_by(job_id=job.id).count()
        for job in jobs
    }
    return render_template('admin_jobs.html', jobs=jobs, signup_counts=signup_counts)

@app.route('/admin/jobs/<int:job_id>/signups')
@require_login
def admin_job_signups(job_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    job = Job.query.get_or_404(job_id)
    signups = JobSignup.query.filter_by(job_id=job_id).order_by(JobSignup.signed_up_at).all()
    return render_template('admin_job_checkin.html', job=job, signups=signups)

@app.route('/admin/jobs/<int:job_id>/checkin/<int:signup_id>', methods=['POST'])
@require_login
def admin_checkin_parent(job_id, signup_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    signup = JobSignup.query.get_or_404(signup_id)
    signup.checked_in = True
    signup.checked_in_at = datetime.now()
    signup.checked_in_by_admin_id = current_user.id
    db.session.commit()
    flash(f'{signup.user.first_name or signup.user.email} checked in successfully.', 'success')
    return redirect(url_for('admin_job_signups', job_id=job_id))

@app.route('/admin/jobs/<int:job_id>/undo-checkin/<int:signup_id>', methods=['POST'])
@require_login
def admin_undo_checkin(job_id, signup_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    signup = JobSignup.query.get_or_404(signup_id)
    signup.checked_in = False
    signup.checked_in_at = None
    signup.checked_in_by_admin_id = None
    db.session.commit()
    flash('Check-in undone.', 'info')
    return redirect(url_for('admin_job_signups', job_id=job_id))

@app.route('/admin/jobs/post', methods=['GET', 'POST'])
@require_login
def post_job():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    if request.method == 'POST':
        job_type = request.form.get('job_type')
        custom_job = request.form.get('custom_job')
        description = request.form.get('description')
        category = request.form.get('category', 'general')
        
        job_title = custom_job if job_type == 'custom' and custom_job else job_type
        
        if not job_title:
            flash('Please select or enter a job title.', 'danger')
            return redirect(url_for('post_job'))
        
        job = Job(title=job_title, description=description, category=category)
        db.session.add(job)
        db.session.commit()
        flash(f'Job "{job_title}" posted successfully!', 'success')
        return redirect(url_for('admin_jobs'))
    
    predefined_jobs = [
        'Parking Attendant',
        'School Trip Chaperone',
        'Classroom Teacher\'s Aid',
        'Classroom Parent Visitor'
    ]
    job_categories = [
        ('general', 'General - No special requirements'),
        ('child_interaction', 'Works with Children - Requires verification')
    ]
    return render_template('post_job.html', predefined_jobs=predefined_jobs, job_categories=job_categories)

@app.route('/admin/jobs/<int:job_id>/deactivate', methods=['POST'])
@require_login
def deactivate_job(job_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    job = Job.query.get_or_404(job_id)
    job.is_active = False
    db.session.commit()
    flash(f'Job "{job.title}" has been deactivated.', 'success')
    return redirect(url_for('admin_jobs'))

@app.route('/admin/parent-verification')
@require_login
def admin_parent_verification():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    all_parents = User.query.filter_by(is_admin=False).order_by(User.first_name).all()
    verified_data = {}
    
    for parent in all_parents:
        verified_data[parent.id] = {
            'parent': parent,
            'verified_for': [e.category for e in JobEligibility.query.filter_by(user_id=parent.id).all()]
        }
    
    categories = [
        ('general', 'General Jobs'),
        ('child_interaction', 'Works with Children')
    ]
    
    return render_template('admin_parent_verification.html', verified_data=verified_data, categories=categories)

@app.route('/admin/parent/<parent_id>/verify/<category>', methods=['POST'])
@require_login
def verify_parent_category(parent_id, category):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    parent = User.query.get_or_404(parent_id)
    
    existing = JobEligibility.query.filter_by(user_id=parent_id, category=category).first()
    if existing:
        return jsonify({'error': 'Already verified'}), 400
    
    eligibility = JobEligibility(user_id=parent_id, category=category, verified_by_admin_id=current_user.id)
    db.session.add(eligibility)
    db.session.commit()
    
    flash(f'{parent.first_name or parent.email} verified for {category} jobs.', 'success')
    return redirect(url_for('admin_parent_verification'))

@app.route('/admin/parent/<parent_id>/revoke/<category>', methods=['POST'])
@require_login
def revoke_parent_category(parent_id, category):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    eligibility = JobEligibility.query.filter_by(user_id=parent_id, category=category).first()
    if eligibility:
        db.session.delete(eligibility)
        db.session.commit()
        flash(f'Verification revoked.', 'success')
    
    return redirect(url_for('admin_parent_verification'))

@app.route('/parent/notifications')
@require_login
def notification_settings():
    return render_template('push_setup.html')

@app.route('/parent/apply-for-job/<category>', methods=['GET', 'POST'])
@require_login
def apply_for_job(category):
    existing_app = JobApplication.query.filter_by(user_id=current_user.id, category=category).first()
    existing_eligibility = JobEligibility.query.filter_by(user_id=current_user.id, category=category).first()
    
    if existing_eligibility:
        flash(f'You are already verified for this job category!', 'info')
        return redirect(url_for('parent_view_jobs'))
    
    if request.method == 'POST':
        file = request.files.get('document')
        fingerprint_file = request.files.get('fingerprint')
        
        if not file or not file.filename:
            flash('Please upload your background check document.', 'danger')
            return redirect(url_for('apply_for_job', category=category))
        
        if category == 'child_interaction' and (not fingerprint_file or not fingerprint_file.filename):
            flash('Please upload your fingerprint document for this category.', 'danger')
            return redirect(url_for('apply_for_job', category=category))
        
        if not allowed_file(file.filename, file.content_type):
            flash('Invalid background check file type.', 'danger')
            return redirect(url_for('apply_for_job', category=category))
            
        if fingerprint_file and fingerprint_file.filename and not allowed_file(fingerprint_file.filename, fingerprint_file.content_type):
            flash('Invalid fingerprint file type.', 'danger')
            return redirect(url_for('apply_for_job', category=category))
        
        if existing_app:
            existing_app.file_data = file.read()
            existing_app.file_name = file.filename
            existing_app.file_type = file.content_type
            if fingerprint_file and fingerprint_file.filename:
                existing_app.fingerprint_file_data = fingerprint_file.read()
                existing_app.fingerprint_file_name = fingerprint_file.filename
                existing_app.fingerprint_file_type = fingerprint_file.content_type
            existing_app.submitted_at = datetime.now()
            existing_app.status = 'pending'
        else:
            app_record = JobApplication(
                user_id=current_user.id,
                category=category,
                file_data=file.read(),
                file_name=file.filename,
                file_type=file.content_type,
                status='pending'
            )
            if fingerprint_file and fingerprint_file.filename:
                app_record.fingerprint_file_data = fingerprint_file.read()
                app_record.fingerprint_file_name = fingerprint_file.filename
                app_record.fingerprint_file_type = fingerprint_file.content_type
            db.session.add(app_record)
        
        db.session.commit()
        flash('Your application with background check documents has been submitted!', 'success')
        return redirect(url_for('parent_view_jobs'))
    
    return render_template('apply_for_job.html', category=category, existing_app=existing_app)

@app.route('/admin/job-applications')
@require_login
def admin_job_applications():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    pending_apps = JobApplication.query.filter_by(status='pending').order_by(JobApplication.submitted_at.desc()).all()
    reviewed_apps = JobApplication.query.filter(JobApplication.status.in_(['approved', 'rejected'])).order_by(JobApplication.reviewed_at.desc()).limit(50).all()
    
    return render_template('admin_job_applications.html', pending_apps=pending_apps, reviewed_apps=reviewed_apps)

@app.route('/admin/application/<int:app_id>/approve', methods=['POST'])
@require_login
def approve_application(app_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    app_record = JobApplication.query.get_or_404(app_id)
    app_record.status = 'approved'
    app_record.reviewed_at = datetime.now()
    app_record.reviewed_by_admin_id = current_user.id
    
    eligibility = JobEligibility(user_id=app_record.user_id, category=app_record.category, verified_by_admin_id=current_user.id)
    db.session.add(eligibility)
    
    # Send email notification
    try:
        from utils.replitmail import send_email
        subject = f"Job Application Approved: {app_record.category}"
        text = f"Hello {app_record.user.first_name or 'there'},\n\nYour application for the '{app_record.category}' job category has been approved! You can now view and apply for these jobs in the dashboard.\n\nBest regards,\nSaint Philip Neri School"
        send_email(subject=subject, text=text)
    except Exception as e:
        print(f"Failed to send approval email: {e}")
        
    db.session.commit()
    
    flash(f'{app_record.user.first_name or app_record.user.email} approved for {app_record.category} jobs.', 'success')
    return redirect(url_for('admin_job_applications'))

@app.route('/admin/application/<int:app_id>/reject', methods=['POST'])
@require_login
def reject_application(app_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    app_record = JobApplication.query.get_or_404(app_id)
    notes = request.form.get('notes', '')
    
    app_record.status = 'rejected'
    app_record.reviewed_at = datetime.now()
    app_record.reviewed_by_admin_id = current_user.id
    app_record.admin_notes = notes
    
    # Send email notification
    try:
        from utils.replitmail import send_email
        subject = f"Job Application Update: {app_record.category}"
        text = f"Hello {app_record.user.first_name or 'there'},\n\nYour application for the '{app_record.category}' job category has been reviewed. Unfortunately, it was not approved at this time.\n\nAdmin Notes: {notes or 'No notes provided.'}\n\nYou can resubmit your application with the required documentation in the dashboard.\n\nBest regards,\nSaint Philip Neri School"
        send_email(subject=subject, text=text)
    except Exception as e:
        print(f"Failed to send rejection email: {e}")
        
    db.session.commit()
    
    flash(f'Application rejected.', 'success')
    return redirect(url_for('admin_job_applications'))

@app.route('/download/application/<int:app_id>/<file_type>')
@require_login
def download_application_file(app_id, file_type):
    app_record = JobApplication.query.get_or_404(app_id)
    
    if not current_user.is_admin and app_record.user_id != current_user.id:
        flash('You do not have permission to access this file.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    if file_type == 'fingerprint':
        data = app_record.fingerprint_file_data
        name = app_record.fingerprint_file_name
        mimetype = app_record.fingerprint_file_type
    else:
        data = app_record.file_data
        name = app_record.file_name
        mimetype = app_record.file_type

    if not data:
        flash('File not found.', 'warning')
        referrer = request.referrer
        if referrer and urlparse(referrer).netloc == urlparse(request.host_url).netloc:
            return redirect(referrer)
        return redirect(url_for('parent_dashboard'))
    
    return send_file(
        BytesIO(data),
        download_name=name,
        as_attachment=True,
        mimetype=mimetype
    )
