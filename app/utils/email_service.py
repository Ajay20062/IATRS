"""
Email service for sending notifications, interview reminders, and application updates.
"""
import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from pydantic import BaseModel, EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class EmailConfig:
    """Email server configuration."""
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_email: str
    from_name: str
    use_tls: bool = True


class EmailMessage(BaseModel):
    """Email message model."""
    to_email: EmailStr
    subject: str
    body_text: str
    body_html: Optional[str] = None
    cc: Optional[list[EmailStr]] = None
    bcc: Optional[list[EmailStr]] = None


def get_email_config() -> Optional[EmailConfig]:
    """Get email configuration from environment."""
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_password = settings.smtp_password
    
    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
        return None
    
    return EmailConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=settings.from_email or smtp_user,
        from_name=settings.from_name or "IATRS",
    )


def create_email_message(
    config: EmailConfig,
    message: EmailMessage
) -> MIMEMultipart:
    """Create email message with both plain text and HTML parts."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = message.subject
    msg["From"] = f"{config.from_name} <{config.from_email}>"
    msg["To"] = message.to_email
    
    if message.cc:
        msg["Cc"] = ", ".join(message.cc)
    
    # Attach plain text part
    text_part = MIMEText(message.body_text, "plain", "utf-8")
    msg.attach(text_part)
    
    # Attach HTML part if provided
    if message.body_html:
        html_part = MIMEText(message.body_html, "html", "utf-8")
        msg.attach(html_part)
    
    return msg


async def send_email_async(message: EmailMessage) -> bool:
    """Send email asynchronously using aiosmtplib."""
    config = get_email_config()
    if not config:
        logger.warning("Email configuration not found. Email not sent.")
        return False
    
    try:
        email_message = create_email_message(config, message)
        
        # Add CC/BCC recipients
        recipients = [message.to_email]
        if message.cc:
            recipients.extend(message.cc)
        if message.bcc:
            recipients.extend(message.bcc)
        
        await aiosmtplib.send(
            email_message,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            start_tls=config.use_tls,
        )
        
        logger.info(f"Email sent successfully to {message.to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {message.to_email}: {str(e)}")
        return False


def send_email_sync(message: EmailMessage) -> bool:
    """Send email synchronously (for non-async contexts)."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(send_email_async(message))


# Email Templates

def get_welcome_email_template(user_name: str, role: str) -> EmailMessage:
    """Generate welcome email for new users."""
    subject = "Welcome to IATRS!"
    
    body_text = f"""
Dear {user_name},

Welcome to Intelligent Applicant Tracking System (IATRS)!

You have successfully registered as a {role}.

Get started by logging in to your dashboard and exploring all the features:
- Post/Apply to jobs
- Track applications
- Schedule interviews
- And much more!

If you have any questions, feel free to reach out to our support team.

Best regards,
The IATRS Team
"""
    
    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">Welcome to IATRS, {user_name}!</h2>
        
        <p>You have successfully registered as a <strong>{role}</strong>.</p>
        
        <p>Get started by logging in to your dashboard and exploring all the features:</p>
        <ul>
            <li>Post/Apply to jobs</li>
            <li>Track applications</li>
            <li>Schedule interviews</li>
            <li>And much more!</li>
        </ul>
        
        <p style="margin-top: 30px;">
            <a href="http://localhost:8000/frontend/login.html" 
               style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Login to Your Account
            </a>
        </p>
        
        <p style="margin-top: 30px; color: #666; font-size: 14px;">
            If you have any questions, feel free to reach out to our support team.
        </p>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>The IATRS Team</p>
    </div>
</body>
</html>
"""
    
    return EmailMessage(
        to_email="",  # To be filled when sending
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


def get_application_confirmation_template(
    candidate_name: str,
    job_title: str,
    company_name: str
) -> EmailMessage:
    """Generate application confirmation email."""
    subject = f"Application Received - {job_title}"
    
    body_text = f"""
Dear {candidate_name},

Thank you for applying to the {job_title} position at {company_name}!

Your application has been successfully submitted. Here are the details:

Position: {job_title}
Company: {company_name}
Application Date: {datetime.now().strftime('%B %d, %Y')}

What's next?
- Our team will review your application
- If your profile matches our requirements, we'll contact you for the next steps
- You can track your application status from your dashboard

We appreciate your interest in joining our team!

Best regards,
The Recruitment Team
"""
    
    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">Application Received!</h2>
        
        <p>Dear {candidate_name},</p>
        
        <p>Thank you for applying to the <strong>{job_title}</strong> position at <strong>{company_name}</strong>!</p>
        
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Position:</strong> {job_title}</p>
            <p><strong>Company:</strong> {company_name}</p>
            <p><strong>Application Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <h3>What's next?</h3>
        <ol>
            <li>Our team will review your application</li>
            <li>If your profile matches our requirements, we'll contact you for the next steps</li>
            <li>You can track your application status from your dashboard</li>
        </ol>
        
        <p>We appreciate your interest in joining our team!</p>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>The Recruitment Team</p>
    </div>
</body>
</html>
"""
    
    return EmailMessage(
        to_email="",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


def get_interview_invitation_template(
    candidate_name: str,
    job_title: str,
    interview_type: str,
    scheduled_at: str,
    interviewer_name: str = "",
    meeting_link: str = ""
) -> EmailMessage:
    """Generate interview invitation email."""
    subject = f"Interview Invitation - {job_title}"
    
    body_text = f"""
Dear {candidate_name},

Great news! We would like to invite you for an interview for the {job_title} position.

Interview Details:
- Type: {interview_type}
- Date & Time: {scheduled_at}
- Interviewer: {interviewer_name or 'To be announced'}
{f'- Meeting Link: {meeting_link}' if meeting_link else ''}

Please confirm your availability by responding to this email.

If you need to reschedule, please let us know at your earliest convenience.

We look forward to speaking with you!

Best regards,
The Recruitment Team
"""
    
    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #059669;">Interview Invitation!</h2>
        
        <p>Dear {candidate_name},</p>
        
        <p>Great news! We would like to invite you for an interview for the <strong>{job_title}</strong> position.</p>
        
        <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #059669;">
            <h3 style="margin-top: 0; color: #059669;">Interview Details</h3>
            <p><strong>Type:</strong> {interview_type}</p>
            <p><strong>Date & Time:</strong> {scheduled_at}</p>
            <p><strong>Interviewer:</strong> {interviewer_name or 'To be announced'}</p>
            {f'<p><strong>Meeting Link:</strong> <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''}
        </div>
        
        <p>Please confirm your availability by responding to this email.</p>
        
        <p>If you need to reschedule, please let us know at your earliest convenience.</p>
        
        <p>We look forward to speaking with you!</p>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>The Recruitment Team</p>
    </div>
</body>
</html>
"""
    
    return EmailMessage(
        to_email="",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


def get_application_status_update_template(
    candidate_name: str,
    job_title: str,
    new_status: str
) -> EmailMessage:
    """Generate application status update email."""
    subject = f"Application Update - {job_title}"
    
    status_messages = {
        "Screening": "Your application is currently under review by our recruitment team.",
        "Interviewing": "Congratulations! We'd like to move forward with your application.",
        "Rejected": "Thank you for your interest. While we've decided to move forward with other candidates, we encourage you to apply for future opportunities.",
        "Hired": "Congratulations! We're excited to offer you the position!",
    }
    
    body_text = f"""
Dear {candidate_name},

We're writing to update you on the status of your application for the {job_title} position.

Current Status: {new_status}

{status_messages.get(new_status, '')}

You can always check your application status from your dashboard.

Best regards,
The Recruitment Team
"""
    
    status_colors = {
        "Screening": "#f59e0b",
        "Interviewing": "#3b82f6",
        "Rejected": "#ef4444",
        "Hired": "#10b981",
    }
    
    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">Application Update</h2>
        
        <p>Dear {candidate_name},</p>
        
        <p>We're writing to update you on the status of your application for the <strong>{job_title}</strong> position.</p>
        
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <p style="margin: 0; color: #666; font-size: 14px;">Current Status</p>
            <span style="background-color: {status_colors.get(new_status, '#6b7280')}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold;">
                {new_status}
            </span>
        </div>
        
        <p style="color: #666;">{status_messages.get(new_status, '')}</p>
        
        <p>You can always check your application status from your dashboard.</p>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>The Recruitment Team</p>
    </div>
</body>
</html>
"""
    
    return EmailMessage(
        to_email="",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


def get_password_reset_template(
    user_name: str,
    reset_token: str,
    reset_link: str
) -> EmailMessage:
    """Generate password reset email."""
    subject = "Password Reset Request"
    
    body_text = f"""
Dear {user_name},

We received a request to reset your password.

To reset your password, click the link below:
{reset_link}

Or enter this code: {reset_token}

This link/code will expire in 1 hour.

If you didn't request this, please ignore this email and your password will remain unchanged.

Best regards,
The IATRS Team
"""
    
    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">Password Reset Request</h2>
        
        <p>Dear {user_name},</p>
        
        <p>We received a request to reset your password.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">
                Reset Password
            </a>
        </div>
        
        <p style="text-align: center;">Or enter this code:</p>
        <p style="text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 4px; color: #2563eb;">{reset_token}</p>
        
        <p style="color: #666; font-size: 14px;">This link/code will expire in 1 hour.</p>
        
        <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email and your password will remain unchanged.</p>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>The IATRS Team</p>
    </div>
</body>
</html>
"""
    
    return EmailMessage(
        to_email="",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


# Import datetime for templates
from datetime import datetime
