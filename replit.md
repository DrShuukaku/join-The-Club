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
- Verify parent volunteer labor hours via QR code or manual entry
- Track and approve volunteer work sessions
- **Filter all dashboards by classroom** to view only their classroom's parents
- View classroom assignments for all parents

### For Parents
- View all assigned paperwork forms
- Submit forms with text content and file uploads
- Track submission deadlines
- Update previously submitted forms
- Download their own submitted documents
- Log volunteer labor hours with check-in/check-out system
- Generate QR codes for admin verification
- View labor hours history and total hours contributed
- **Set their child's classroom** in their profile (Kindergarten-8th Grade)

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

### LaborHours
- Tracks parent volunteer work sessions
- Unique verification code for each session
- Check-in/check-out timestamps to prevent manipulation
- QR code generation for easy admin verification
- Admin verification with approval/rejection status
- Calculates hours worked automatically

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
- November 16, 2025:
  - **Added classroom-based filtering system**: Teachers/admins can now filter all dashboards by classroom
  - Parents can set their classroom in their profile (Kindergarten through 8th Grade)
  - Classroom filtering available on: Admin Dashboard, Form Submissions, Service Hours Dashboard
  - All admin views now display parent classroom information
  - Added "Profile" link to parent navigation for classroom management
- November 15, 2025: 
  - Added volunteer labor hours tracking system with QR code verification
  - Implemented service log enhancements: pre-filled task categories, printable reports, CSV export, monthly summaries
  - Created admin service hours dashboard for tracking all parents' volunteer hours
  - **Fixed deployment readiness**: Configured PostgreSQL database, added lazy database initialization to prevent startup crashes, configured production deployment with gunicorn
  - Changed "Login" button to "Admin" with grey styling
- November 12, 2025: Initial application setup with full functionality
- Implemented Replit Auth integration for secure user authentication
- Created admin and parent portals with role-based access
- Added file upload capability with database storage
- Implemented deadline tracking and form management

## Volunteer Labor Hours System

### How It Works

**For Parents:**
1. Navigate to "Labor Hours" in the navigation menu
2. Click "Check In" and select from pre-defined task categories (or enter custom task)
3. A unique QR code and verification code will be generated
4. Work on your volunteer task
5. Click "Check Out" when finished - hours are automatically calculated
6. Show the QR code to an administrator for verification
7. Export your service hours to CSV/Excel or print a service log report
8. View monthly summaries of your volunteer work

**For Administrators:**
1. Navigate to "Labor Verification" in the navigation menu
2. Use camera to scan parent's QR code OR manually enter verification code
3. Review the work session details (parent name, task, hours)
4. Verify or reject the labor hours with optional notes
5. View pending and verified labor hours
6. Access "Service Hours" dashboard to see all parents' volunteer hours

### New Features (November 15, 2025)
- **Pre-filled Service Categories**: 10 common volunteer tasks in dropdown menu
- **Printable Service Log**: Generate printer-friendly reports of all service hours
- **CSV/Excel Export**: Download service hours data as spreadsheet
- **Monthly Summary Reports**: Automatic monthly breakdown of hours worked
- **Admin Service Hours Dashboard**: View all parents' service hours in one centralized location

### Security Features
- Timestamps are server-generated and cannot be manipulated
- Unique verification codes prevent fraud
- QR codes contain encrypted verification data
- Camera-based scanning for quick verification
- Admin must explicitly approve each work session

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
