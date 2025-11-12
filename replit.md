# School Paperwork Submission System

## Overview
A web application designed for schools to manage paperwork submissions from parents. The system features separate portals for administrators and parents, with secure authentication via Replit Auth.

## Features

### For Administrators
- Create and manage paperwork forms with deadlines
- View all submissions for each form
- Download submitted documents
- Activate/deactivate forms
- Track submission statistics

### For Parents
- View all assigned paperwork forms
- Submit forms with text content and file uploads
- Track submission deadlines
- Update previously submitted forms
- Download their own submitted documents

## Technology Stack
- **Backend**: Flask (Python)
- **Database**: PostgreSQL (Replit Database)
- **Authentication**: Replit Auth (supports Google, GitHub, email/password)
- **File Storage**: Database BLOB storage
- **Frontend**: HTML, CSS, Jinja2 templates

## Project Structure
```
├── app.py                  # Flask app initialization and database config
├── main.py                 # Application entry point
├── models.py               # Database models (User, Form, Submission, OAuth)
├── routes.py               # Application routes and business logic
├── replit_auth.py          # Replit authentication integration
├── templates/              # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── landing.html        # Landing page for logged-out users
│   ├── parent_dashboard.html    # Parent dashboard
│   ├── submit_form.html    # Form submission page
│   ├── admin_dashboard.html     # Admin dashboard
│   ├── create_form.html    # Form creation page
│   ├── view_submissions.html    # View form submissions
│   └── 403.html            # Access denied page
└── static/
    └── css/
        └── style.css       # Application styles

## Database Models

### User
- Stores user authentication information from Replit Auth
- Has `is_admin` flag to distinguish administrators from parents
- Linked to submissions

### Form
- Created by administrators
- Contains title, description, deadline
- Can be activated/deactivated

### Submission
- Links users to forms
- Stores text content and file uploads (as binary data)
- Tracks submission timestamp

## Getting Started

### Initial Setup (IMPORTANT)
1. **Configure Admin Emails**: Before using the app, set the `ADMIN_EMAILS` environment variable in Replit Secrets:
   - Click on "Secrets" in the left sidebar
   - Add a new secret with key: `ADMIN_EMAILS`
   - Value: comma-separated list of admin email addresses (e.g., `admin@school.com,principal@school.com`)
   
2. **First Login**: Login with an email address that matches one in `ADMIN_EMAILS`

3. **Become Admin**: Click the "Become Admin" button in the navigation

### Usage
1. **As Admin**: Create forms with titles, descriptions, and deadlines from the admin dashboard
2. **As Parent**: View assigned forms and submit required paperwork with optional file uploads
3. **File Uploads**: Supports PDF, DOC, DOCX, JPG, PNG files up to 16MB

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (automatically set by Replit)
- `SESSION_SECRET`: Flask session secret (automatically set by Replit)
- `REPL_ID`: Replit project ID (automatically set)
- `ADMIN_EMAILS`: **Required** - Comma-separated list of admin email addresses (must be set by user)

## Recent Changes
- November 12, 2025: Initial application setup with full functionality
- Implemented Replit Auth integration for secure user authentication
- Created admin and parent portals with role-based access
- Added file upload capability with database storage
- Implemented deadline tracking and form management

## User Preferences
None specified yet.

## Security Notes
- Admin access is controlled via `ADMIN_EMAILS` environment variable (see SECURITY.md)
- File uploads are validated for type and size
- Only authorized email addresses can become administrators
- See SECURITY.md for detailed security documentation

## Notes
- Forms can be edited after submission by parents
- All files are stored in the database as binary data
- The application uses responsive design for mobile compatibility
- Admin status is tied to email addresses configured in ADMIN_EMAILS
