from flask import session, render_template, request, redirect, url_for, flash, send_file
from io import BytesIO
from datetime import datetime
import os
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user
from models import User, Form, Submission

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

@app.route('/admin/dashboard')
@require_login
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    forms = Form.query.order_by(Form.deadline.desc()).all()
    total_users = User.query.count()
    total_submissions = Submission.query.count()
    
    return render_template('admin_dashboard.html', 
                         forms=forms,
                         total_users=total_users,
                         total_submissions=total_submissions)

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
    
    form = Form.query.get_or_404(form_id)
    submissions = Submission.query.filter_by(form_id=form_id).all()
    
    return render_template('view_submissions.html', form=form, submissions=submissions)

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
