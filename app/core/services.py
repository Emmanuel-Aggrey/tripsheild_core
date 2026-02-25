import logging
import re
import requests
from datetime import datetime
from pathlib import Path
from fastapi_mail import FastMail, ConnectionConfig
from fastapi_mail import MessageSchema, MessageType
from app import settings
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class CoreService:
    def __init__(self):
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS,
            TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates',
        )
        self.fastmail = FastMail(self.conf)

    async def send_template_email(self, recipients: list, subject: str, template_name: str, context: dict):

        context.update({
            "app_name": settings.APP_NAME,
            "current_year": datetime.now().year,
            "frontend_url": settings.FRONTEND_URL,
            "current_date": datetime.now().strftime("%B %d, %Y"),
        })

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html,
        )
        try:
            message
            # await self.fastmail.send_message(message, template_name=template_name)
        except Exception as e:
            logger.error(
                f"Failed to send email to {recipients} with subject '{subject}': {e}")

    def send_text_message(self, to_number, message):

        def clean_message(message):
            lines = message.split("\n")
            cleaned_lines = []

            for line in lines:
                # Remove multiple spaces within each line
                cleaned_line = " ".join(line.split())
                # Remove spaces before punctuation
                cleaned_line = re.sub(r"\s+([.,!?\'\":])", r"\1", cleaned_line)
                cleaned_lines.append(cleaned_line)

            # Join back with newlines
            return "\n".join(cleaned_lines).strip()

        try:
            hubtel_configuration = settings.HUBTEL_SMS_CONFIGURATION

            clientsecret = hubtel_configuration.get("clientsecret", None)
            clientid = hubtel_configuration.get("clientid", None)
            sender = hubtel_configuration.get("from", None)
            url = hubtel_configuration.get("url", None)

            if not all([clientsecret, clientid, sender, url]):
                logger.error(
                    "Missing Hubtel SMS configuration values: clientsecret, clientid, from, url."
                )
                return

            message = clean_message(message)

            url = "{}?clientsecret={}&clientid={}&from={}&to={}&content={}".format(
                url, clientsecret, clientid, sender, to_number, quote_plus(
                    message)
            )

            #
            # response =  requests.get(url, timeout=10)

            return {}  # response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending SMS: {e}")
            return None
