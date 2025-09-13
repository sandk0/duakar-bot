import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.config import settings
from database.models import User

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification service"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'smtp_server', None)
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_username = getattr(settings, 'smtp_username', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.from_email = getattr(settings, 'from_email', 'noreply@vpnbot.com')
        self.enabled = all([
            self.smtp_server,
            self.smtp_username, 
            self.smtp_password
        ])
    
    async def send_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> bool:
        """Send notification via email"""
        if not self.enabled:
            logger.warning("Email notifications are not configured")
            return False
        
        try:
            # Get user email from database (if stored)
            # Note: This assumes email is stored in user metadata or separate field
            email = await self._get_user_email(user_id)
            if not email:
                logger.debug(f"No email found for user {user_id}")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = title
            
            # Create HTML and plain text versions
            html_body = self._create_html_message(title, message, data)
            plain_body = self._create_plain_message(message, data)
            
            msg.attach(MIMEText(plain_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification to user {user_id}: {e}")
            return False
    
    async def _get_user_email(self, user_id: int) -> Optional[str]:
        """Get user email from database"""
        # This is a placeholder implementation
        # In a real implementation, you would query the database for user email
        # For now, return None as emails are not stored in the current schema
        return None
    
    def _create_html_message(
        self,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> str:
        """Create HTML email message"""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #007bff;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    padding: 20px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 10px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <p>{message.replace(chr(10), '<br>')}</p>
            </div>
            <div class="footer">
                <p>VPN Bot Service</p>
                <p>Это автоматическое сообщение, не отвечайте на него.</p>
            </div>
        </body>
        </html>
        """
        return html_template
    
    def _create_plain_message(
        self,
        message: str,
        data: Dict[str, Any] = None
    ) -> str:
        """Create plain text email message"""
        plain_message = f"{message}\n\n"
        plain_message += "---\n"
        plain_message += "VPN Bot Service\n"
        plain_message += "Это автоматическое сообщение, не отвечайте на него."
        
        return plain_message
    
    async def send_subscription_expiry_email(
        self,
        user_id: int,
        days_remaining: int
    ) -> bool:
        """Send subscription expiry email"""
        if days_remaining <= 0:
            title = "Ваша VPN подписка истекла"
            message = ("Ваша подписка на VPN сервис истекла.\n\n"
                      "Для продолжения использования сервиса, пожалуйста, "
                      "продлите подписку в Telegram боте.")
        else:
            title = f"Ваша VPN подписка истекает через {days_remaining} дней"
            message = (f"Напоминаем, что ваша подписка на VPN сервис "
                      f"истекает через {days_remaining} дней.\n\n"
                      "Для продолжения использования сервиса, пожалуйста, "
                      "продлите подписку в Telegram боте.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_payment_confirmation_email(
        self,
        user_id: int,
        amount: float,
        currency: str,
        payment_id: str
    ) -> bool:
        """Send payment confirmation email"""
        title = "Подтверждение оплаты VPN подписки"
        message = (f"Ваш платеж успешно обработан.\n\n"
                  f"Сумма: {amount} {currency}\n"
                  f"ID платежа: {payment_id}\n\n"
                  "Ваша подписка активирована. "
                  "Вы можете получить новую конфигурацию VPN в Telegram боте.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )
    
    async def send_welcome_email(self, user_id: int) -> bool:
        """Send welcome email to new user"""
        title = "Добро пожаловать в VPN Bot!"
        message = ("Спасибо за регистрацию в нашем VPN сервисе!\n\n"
                  "Вы можете начать с бесплатного пробного периода на 7 дней.\n\n"
                  "Для управления подпиской используйте наш Telegram бот.")
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            message=message
        )