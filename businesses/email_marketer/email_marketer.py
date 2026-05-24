"""
Email Marketing Automator
==========================
Sends automated deal alert emails to a subscriber list.
Monetized via:
  1. Amazon affiliate links (1–10% commission)
  2. Paid newsletter tier ($4.99/mo)
  3. Sponsored product placements

Uses Gmail SMTP (free) or SendGrid API (free tier = 100/day).

Revenue model:
  1,000 subscribers × 5% CTR × 5% conversion × $50 avg order × 4% commission
  = $50/month from affiliate alone

  Plus: 100 paid subs × $4.99 = $499/month recurring
"""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


class EmailMarketer:
    """Automated email marketing system for deal newsletters."""

    def __init__(
        self,
        sender_email: str,
        sender_name: str = "DealBot Newsletter",
        app_password: str = "",         # Gmail app password
        sendgrid_api_key: str = "",      # SendGrid alternative
        affiliate_tag: str = "",
    ):
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.app_password = app_password
        self.sendgrid_api_key = sendgrid_api_key
        self.affiliate_tag = affiliate_tag
        self.sent_count = 0
        self.failed_count = 0

    def _tag_url(self, url: str) -> str:
        """Add Amazon affiliate tag to URL."""
        if self.affiliate_tag and "amazon.com" in url:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}tag={self.affiliate_tag}"
        return url

    def _build_html_email(self, subject: str, deals: List[Dict], unsubscribe_url: str = "#") -> str:
        """Build a clean HTML email with deal listings."""
        deal_rows = ""
        for deal in deals:
            url = self._tag_url(deal.get("url", "#"))
            deal_rows += f"""
            <tr>
              <td style="padding:16px;border-bottom:1px solid #eee;">
                <h3 style="margin:0 0 8px;color:#333;">{deal.get('title','')}</h3>
                <p style="margin:0 0 8px;color:#666;font-size:14px;">{deal.get('description','')}</p>
                <span style="font-size:24px;font-weight:bold;color:#e74c3c;">
                  {deal.get('price','')}
                </span>
                {f'<s style="color:#999;font-size:16px;margin-left:8px;">{deal.get("original_price","")}</s>' if deal.get("original_price") else ""}
                <br><br>
                <a href="{url}"
                   style="background:#ff9900;color:white;padding:10px 20px;border-radius:4px;
                          text-decoration:none;font-weight:bold;display:inline-block;">
                  🛒 Shop Now on Amazon
                </a>
              </td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <div style="max-width:600px;margin:0 auto;background:white;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#ff9900,#ff6600);padding:24px;text-align:center;">
      <h1 style="color:white;margin:0;font-size:28px;">🔥 Today's Best Deals</h1>
      <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;">Handpicked savings just for you</p>
    </div>

    <!-- Deals -->
    <table style="width:100%;border-collapse:collapse;">
      {deal_rows}
    </table>

    <!-- CTA -->
    <div style="background:#fff8e1;padding:20px;text-align:center;border-top:3px solid #ff9900;">
      <p style="margin:0 0 12px;font-weight:bold;">Want EXCLUSIVE deals before everyone else?</p>
      <a href="https://paypal.me/digitalempiresk/4.99"
         style="background:#0070ba;color:white;padding:12px 24px;border-radius:4px;
                text-decoration:none;font-weight:bold;">
        ⭐ Go VIP — $4.99/month
      </a>
    </div>

    <!-- Footer -->
    <div style="padding:16px;text-align:center;color:#999;font-size:12px;">
      <p>You're receiving this because you subscribed to DealBot Newsletter.</p>
      <a href="{unsubscribe_url}" style="color:#999;">Unsubscribe</a>
    </div>
  </div>
</body>
</html>"""

    def send_via_gmail(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via Gmail SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.sender_email, self.app_password)
                smtp.send_message(msg)

            self.sent_count += 1
            return True
        except Exception as e:
            logger.error(f"Gmail send failed to {to_email}: {e}")
            self.failed_count += 1
            return False

    def send_via_sendgrid(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via SendGrid API."""
        import requests

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.sender_email, "name": self.sender_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }

        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 202):
                self.sent_count += 1
                return True
            else:
                logger.error(f"SendGrid failed: {resp.status_code} {resp.text}")
                self.failed_count += 1
                return False
        except Exception as e:
            logger.error(f"SendGrid exception: {e}")
            self.failed_count += 1
            return False

    def broadcast_campaign(
        self,
        subscribers: List[str],
        subject: str,
        deals: List[Dict],
        delay_seconds: float = 0.5,
    ) -> Dict:
        """
        Send a deal email to all subscribers.

        Args:
            subscribers: List of email addresses.
            subject: Email subject line.
            deals: List of deal dicts with title/description/price/url.
            delay_seconds: Delay between sends.

        Returns:
            Summary dict.
        """
        html = self._build_html_email(subject, deals)

        logger.info(f"Broadcasting to {len(subscribers)} subscribers...")

        for email in subscribers:
            if self.sendgrid_api_key:
                self.send_via_sendgrid(email, subject, html)
            elif self.app_password:
                self.send_via_gmail(email, subject, html)
            time.sleep(delay_seconds)

        summary = {
            "total": len(subscribers),
            "sent": self.sent_count,
            "failed": self.failed_count,
            "subject": subject,
        }
        logger.info(f"Campaign done: {self.sent_count} sent, {self.failed_count} failed")
        return summary
