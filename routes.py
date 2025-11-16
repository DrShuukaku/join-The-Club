from flask import session, render_template, request, redirect, url_for, flash, send_file, jsonify
from io import BytesIO
from datetime import datetime
import os
import qrcode
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user
from models import User, Form, Submission, LaborHours

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
    
    return render_template('parent_dashboard.html', 
                         pending_forms=pending_forms,
                         completed_forms=completed_forms)

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
                return redirect(request.url)
        
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
        
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
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
        return redirect(request.referrer or url_for('parent_dashboard'))
    
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
    return render_template('parent_labor_hours.html', 
                         labor_records=labor_records,
                         active_session=active_session,
                         total_hours=total_hours)

@app.route('/parent/labor/check-in', methods=['POST'])
@require_login
def labor_check_in():
    task_description = request.form.get('task_description')
    custom_task = request.form.get('custom_task')
    
    if task_description == 'Custom' and custom_task:
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
