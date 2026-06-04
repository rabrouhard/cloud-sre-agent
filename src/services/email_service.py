from __future__ import annotations
from collections.abc import Iterable
from email.message import EmailMessage
import smtplib


class SmtpEmailService:
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        timeout_seconds: int = 20,
    ):
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password, self.use_tls, self.timeout_seconds = (
            username,
            password,
            use_tls,
            timeout_seconds,
        )

    def send_advisory(
        self,
        recipients: Iterable[str],
        subject: str,
        body: str,
    ) -> dict[str, bool | list[str]]:
        """
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
            body (str): Body content of the email.

        Returns:
            dict[str, bool | list[str]]: A dictionary with the following structure:
                {
                    "sent": True if the email was sent successfully,
                    "recipients": list of recipient email addresses
                }
        """
        recipients_list = list(recipients)
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = (
            self.sender,
            ", ".join(recipients_list),
            subject,
        )
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg)
            return {"sent": True, "recipients": recipients_list}
        except Exception as e:
            return {"sent": False, "recipients": recipients_list, "error": str(e)}
