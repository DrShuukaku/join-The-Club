# Security Documentation

## Admin Access Control

### Configuration
Admin access is controlled via the `ADMIN_EMAILS` environment variable. Only users whose email addresses are listed in this variable can become administrators.

**Setup:**
1. In Replit Secrets, add `ADMIN_EMAILS` with comma-separated email addresses:
   ```
   admin@school.com,principal@school.com
   ```
2. Users with matching email addresses can click "Become Admin" to gain admin privileges
3. Non-authorized users will receive an error message

### Initial Setup
For first-time setup when no admins exist:
1. Login with your authorized admin email
2. Click "Become Admin" in the navigation
3. You will now have access to the admin dashboard

## File Upload Security

### Allowed File Types
The system restricts uploads to specific file types:
- **Documents**: PDF (.pdf), DOC (.doc), DOCX (.docx)
- **Images**: JPG/JPEG (.jpg, .jpeg), PNG (.png)

### Validation
- File extension validation
- MIME type validation
- Size limit: 16MB (configured in `app.py`)

Files are validated on both extension and MIME type to prevent malicious uploads.

## Authentication

### Replit Auth Integration
The application uses Replit's OpenID Connect authentication. Key points:

1. **JWT Token Handling**: The `replit_auth.py` blueprint decodes JWT tokens with `verify_signature=False`. This is based on the official Replit Auth blueprint and relies on Replit's OIDC provider being trusted within the Replit ecosystem.

2. **Session Management**: Uses database-backed sessions (not in-memory or cookie-based) for production reliability.

3. **User Data**: User information (name, email, profile image) is pulled from the ID token claims and stored in the database.

### Best Practices Implemented
- All admin routes check `current_user.is_admin` before allowing access
- File downloads verify ownership (users can only download their own files, admins can download all)
- Session tokens are stored securely in the database
- HTTPS is enforced through Replit's proxy configuration

## Data Storage

### Database Security
- PostgreSQL database provided by Replit
- User passwords are NOT stored (authentication handled by Replit Auth)
- File uploads stored as binary data in database
- No sensitive data logged

### File Storage
Files are stored as BLOB data in the database rather than filesystem to:
- Ensure database backup includes all submission data
- Prevent direct file access bypass
- Simplify deployment and rollback

## Recommendations for Production

1. **Admin Setup**: Configure `ADMIN_EMAILS` immediately after deployment
2. **Monitor Uploads**: Regularly review uploaded files for inappropriate content
3. **Audit Logs**: Consider adding audit logging for admin actions
4. **Rate Limiting**: Consider adding rate limiting for file uploads
5. **Content Scanning**: For production use, consider adding virus scanning for uploaded files

## Known Limitations

1. **JWT Signature Verification**: Following the Replit Auth blueprint pattern, JWT signatures are not verified in application code. This is acceptable within the Replit ecosystem where the OIDC provider is trusted, but should be reviewed if deploying outside Replit.

2. **File Content Validation**: Currently validates file types by extension and MIME type only. Does not scan file contents for malicious code or viruses.

3. **No Audit Trail**: Admin actions are not logged. Consider adding this for production deployments.

## Reporting Security Issues

If you discover a security vulnerability, please contact the school administration immediately. Do not disclose the issue publicly until it has been addressed.
