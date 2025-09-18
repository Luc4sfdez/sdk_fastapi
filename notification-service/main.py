"""
notification-service - Notification Service

Multi-channel notification service (Email, SMS, Push)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from enum import Enum
import smtplib
import logging
import uuid
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="notification-service",
    description="Multi-channel notification service (Email, SMS, Push)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SCHEDULED = "scheduled"

# Models
class NotificationRequest(BaseModel):
    recipient: str
    channel: NotificationChannel
    subject: Optional[str] = None
    content: str
    template_id: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None

class NotificationTemplate(BaseModel):
    id: Optional[str] = None
    name: str
    channel: NotificationChannel
    subject_template: Optional[str] = None
    content_template: str
    variables: List[str] = []

class NotificationResponse(BaseModel):
    id: str
    status: NotificationStatus
    message: str

class NotificationHistory(BaseModel):
    id: str
    recipient: str
    channel: NotificationChannel
    subject: Optional[str]
    content: str
    status: NotificationStatus
    created_at: datetime
    sent_at: Optional[datetime]
    error_message: Optional[str]

# In-memory storage (use database in production)
notifications_db = {}
templates_db = {}
delivery_history = []

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@example.com")

# Notification handlers
class NotificationHandler:
    @staticmethod
    async def send_email(recipient: str, subject: str, content: str) -> bool:
        """Send email notification"""
        try:
            if not SMTP_USERNAME or not SMTP_PASSWORD:
                logger.warning("SMTP credentials not configured, simulating email send")
                return True
            
            msg = MimeMultipart()
            msg['From'] = FROM_EMAIL
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MimeText(content, 'html'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(FROM_EMAIL, recipient, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False
    
    @staticmethod
    async def send_sms(recipient: str, content: str) -> bool:
        """Send SMS notification (simulated)"""
        try:
            # In production, integrate with SMS provider (Twilio, AWS SNS, etc.)
            logger.info(f"SMS sent successfully to {recipient}: {content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {recipient}: {e}")
            return False
    
    @staticmethod
    async def send_push(recipient: str, subject: str, content: str) -> bool:
        """Send push notification (simulated)"""
        try:
            # In production, integrate with push service (Firebase, OneSignal, etc.)
            logger.info(f"Push notification sent to {recipient}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send push notification to {recipient}: {e}")
            return False

def apply_template(template: NotificationTemplate, variables: Dict[str, Any]) -> tuple:
    """Apply variables to template"""
    subject = template.subject_template or ""
    content = template.content_template
    
    for var_name, var_value in variables.items():
        placeholder = f"{{{var_name}}}"
        subject = subject.replace(placeholder, str(var_value))
        content = content.replace(placeholder, str(var_value))
    
    return subject, content

async def process_notification(notification_id: str):
    """Process notification in background"""
    notification = notifications_db.get(notification_id)
    if not notification:
        return
    
    try:
        recipient = notification["recipient"]
        channel = notification["channel"]
        subject = notification.get("subject", "")
        content = notification["content"]
        
        # Apply template if specified
        if notification.get("template_id"):
            template = templates_db.get(notification["template_id"])
            if template:
                variables = notification.get("variables", {})
                subject, content = apply_template(template, variables)
        
        # Send notification based on channel
        success = False
        if channel == NotificationChannel.EMAIL:
            success = await NotificationHandler.send_email(recipient, subject, content)
        elif channel == NotificationChannel.SMS:
            success = await NotificationHandler.send_sms(recipient, content)
        elif channel == NotificationChannel.PUSH:
            success = await NotificationHandler.send_push(recipient, subject, content)
        
        # Update status
        if success:
            notification["status"] = NotificationStatus.SENT
            notification["sent_at"] = datetime.utcnow()
        else:
            notification["status"] = NotificationStatus.FAILED
            notification["error_message"] = "Failed to send notification"
        
        # Add to history
        delivery_history.append({
            "id": notification_id,
            "recipient": recipient,
            "channel": channel,
            "subject": subject,
            "content": content,
            "status": notification["status"],
            "created_at": notification["created_at"],
            "sent_at": notification.get("sent_at"),
            "error_message": notification.get("error_message")
        })
        
    except Exception as e:
        logger.error(f"Error processing notification {notification_id}: {e}")
        notification["status"] = NotificationStatus.FAILED
        notification["error_message"] = str(e)

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "notification-service",
        "version": "1.0.0",
        "status": "running",
        "description": "Multi-channel notification service",
        "channels": ["email", "sms", "push"],
        "endpoints": {
            "send": "/send",
            "schedule": "/schedule",
            "templates": "/templates",
            "status": "/status/{id}",
            "history": "/history",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "notification-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "total_notifications": len(notifications_db),
            "total_templates": len(templates_db),
            "history_count": len(delivery_history)
        }
    }

@app.post("/send", response_model=NotificationResponse)
async def send_notification(
    notification: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """Send immediate notification"""
    notification_id = str(uuid.uuid4())
    
    # Store notification
    notifications_db[notification_id] = {
        "id": notification_id,
        "recipient": notification.recipient,
        "channel": notification.channel,
        "subject": notification.subject,
        "content": notification.content,
        "template_id": notification.template_id,
        "variables": notification.variables,
        "status": NotificationStatus.PENDING,
        "created_at": datetime.utcnow()
    }
    
    # Process in background
    background_tasks.add_task(process_notification, notification_id)
    
    return NotificationResponse(
        id=notification_id,
        status=NotificationStatus.PENDING,
        message="Notification queued for processing"
    )

@app.post("/schedule", response_model=NotificationResponse)
async def schedule_notification(notification: NotificationRequest):
    """Schedule notification for later"""
    if not notification.scheduled_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_at is required for scheduled notifications"
        )
    
    notification_id = str(uuid.uuid4())
    
    # Store scheduled notification
    notifications_db[notification_id] = {
        "id": notification_id,
        "recipient": notification.recipient,
        "channel": notification.channel,
        "subject": notification.subject,
        "content": notification.content,
        "template_id": notification.template_id,
        "variables": notification.variables,
        "status": NotificationStatus.SCHEDULED,
        "created_at": datetime.utcnow(),
        "scheduled_at": notification.scheduled_at
    }
    
    return NotificationResponse(
        id=notification_id,
        status=NotificationStatus.SCHEDULED,
        message=f"Notification scheduled for {notification.scheduled_at}"
    )

@app.get("/templates")
async def list_templates():
    """List all notification templates"""
    return {
        "templates": list(templates_db.values()),
        "total": len(templates_db)
    }

@app.post("/templates")
async def create_template(template: NotificationTemplate):
    """Create notification template"""
    template_id = template.id or str(uuid.uuid4())
    
    template_data = {
        "id": template_id,
        "name": template.name,
        "channel": template.channel,
        "subject_template": template.subject_template,
        "content_template": template.content_template,
        "variables": template.variables,
        "created_at": datetime.utcnow()
    }
    
    templates_db[template_id] = template_data
    
    return {
        "message": "Template created successfully",
        "template": template_data
    }

@app.get("/status/{notification_id}")
async def get_notification_status(notification_id: str):
    """Get notification status"""
    notification = notifications_db.get(notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {
        "id": notification_id,
        "status": notification["status"],
        "created_at": notification["created_at"],
        "sent_at": notification.get("sent_at"),
        "error_message": notification.get("error_message")
    }

@app.get("/history")
async def get_notification_history(limit: int = 50, offset: int = 0):
    """Get notification history"""
    total = len(delivery_history)
    history_slice = delivery_history[offset:offset + limit]
    
    return {
        "history": history_slice,
        "total": total,
        "limit": limit,
        "offset": offset
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )