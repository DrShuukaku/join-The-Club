from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    classroom = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    submissions = db.relationship('Submission', back_populates='user', cascade='all, delete-orphan')
    labor_hours = db.relationship('LaborHours', back_populates='user', cascade='all, delete-orphan')

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Form(db.Model):
    __tablename__ = 'forms'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    submissions = db.relationship('Submission', back_populates='form', cascade='all, delete-orphan')

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    file_data = db.Column(db.LargeBinary, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    
    form = db.relationship('Form', back_populates='submissions')
    user = db.relationship('User', back_populates='submissions')

class LaborHours(db.Model):
    __tablename__ = 'labor_hours'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    task_description = db.Column(db.String(500), nullable=False)
    verification_code = db.Column(db.String(20), unique=True, nullable=False)
    
    check_in_time = db.Column(db.DateTime, nullable=False)
    check_out_time = db.Column(db.DateTime, nullable=True)
    admin_verified_at = db.Column(db.DateTime, nullable=True)
    verified_by_admin_id = db.Column(db.String, nullable=True)
    
    status = db.Column(db.String(20), default='checked_in')
    hours_worked = db.Column(db.Float, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', back_populates='labor_hours')
    
    @staticmethod
    def generate_verification_code():
        return secrets.token_hex(8).upper()
    
    def calculate_hours(self):
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return round(delta.total_seconds() / 3600, 2)
        return 0

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False, default='general')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class JobEligibility(db.Model):
    __tablename__ = 'job_eligibility'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    verified_at = db.Column(db.DateTime, default=datetime.now)
    verified_by_admin_id = db.Column(db.String, nullable=True)
    
    __table_args__ = (UniqueConstraint('user_id', 'category', name='uq_user_category'),)
    
    user = db.relationship('User')

class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(100), nullable=True)
    
    # Adding specific background check fields
    fingerprint_file_data = db.Column(db.LargeBinary, nullable=True)
    fingerprint_file_name = db.Column(db.String(255), nullable=True)
    fingerprint_file_type = db.Column(db.String(100), nullable=True)
    
    status = db.Column(db.String(20), default='pending')
    admin_notes = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_admin_id = db.Column(db.String, nullable=True)
    
    user = db.relationship('User')
