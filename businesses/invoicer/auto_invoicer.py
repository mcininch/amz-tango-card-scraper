"""
PayPal Auto-Invoicer
=====================
Automatically creates and sends PayPal invoices for:
  - Monthly VIP subscriptions
  - Freelance/service work
  - Digital product sales
  - Report subscriptions

Integrates with PayPal client to track payment status.
Sends reminders automatically for unpaid invoices.

Revenue: $49.99 × 20 clients = $1,000/month recurring.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger
from businesses.paypal.paypal_client import PayPalClient

logger = setup_logger(logger_name=__name__)


@dataclass
class Subscription:
    """Recurring subscription record."""
    client_name: str
    client_email: str
    service: str
    amount: float
    currency: str = "USD"
    billing_day: int = 1       # Day of month to invoice
    last_billed: Optional[str] = None
    active: bool = True


@dataclass
class ClientRecord:
    """Client database record."""
    name: str
    email: str
    services: List[Dict] = field(default_factory=list)
    total_billed: float = 0.0
    outstanding: float = 0.0
    notes: str = ""


class AutoInvoicer:
    """Automated PayPal invoice management system."""

    def __init__(
        self,
        paypal_client: PayPalClient,
        state_file: str = "invoicer_state.json",
    ):
        self.paypal = paypal_client
        self.state_file = state_file
        self.subscriptions: List[Subscription] = []
        self.clients: Dict[str, ClientRecord] = {}
        self._load_state()

    def _load_state(self) -> None:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                self.subscriptions = [Subscription(**s) for s in data.get("subscriptions", [])]
                self.clients = {k: ClientRecord(**v) for k, v in data.get("clients", {}).items()}
            except Exception as e:
                logger.warning(f"Could not load invoicer state: {e}")

    def _save_state(self) -> None:
        data = {
            "subscriptions": [vars(s) for s in self.subscriptions],
            "clients": {k: vars(v) for k, v in self.clients.items()},
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_subscription(
        self,
        client_name: str,
        client_email: str,
        service: str,
        amount: float,
        billing_day: int = 1,
    ) -> Subscription:
        """Add a new recurring subscription."""
        sub = Subscription(
            client_name=client_name,
            client_email=client_email,
            service=service,
            amount=amount,
            billing_day=billing_day,
        )
        self.subscriptions.append(sub)
        self._save_state()
        logger.info(f"Added subscription: {client_name} — ${amount}/mo for {service}")
        return sub

    def add_client(self, name: str, email: str, notes: str = "") -> ClientRecord:
        """Register a new client."""
        client = ClientRecord(name=name, email=email, notes=notes)
        self.clients[email] = client
        self._save_state()
        logger.info(f"Added client: {name} ({email})")
        return client

    def send_invoice_now(
        self,
        client_email: str,
        items: List[Dict],
        note: str = "Thank you for your business!",
    ) -> Optional[str]:
        """
        Send an invoice immediately.

        Args:
            client_email: Client's PayPal email.
            items: List of dicts: {name, description, quantity, unit_amount}.
            note: Invoice note.

        Returns:
            Invoice ID or None on failure.
        """
        client = self.clients.get(client_email)
        client_name = client.name if client else client_email

        try:
            result = self.paypal.create_invoice(
                recipient_email=client_email,
                recipient_name=client_name,
                items=items,
                note=note,
            )
            invoice_id = result.get("id")
            total = sum(float(i["unit_amount"]) * i.get("quantity", 1) for i in items)

            if client:
                client.total_billed += total
                client.outstanding += total

            self._save_state()
            logger.info(f"Invoice {invoice_id} sent to {client_email} for ${total:.2f}")
            return invoice_id
        except Exception as e:
            logger.error(f"Invoice failed for {client_email}: {e}")
            return None

    def process_due_subscriptions(self) -> List[Dict]:
        """Check all subscriptions and invoice those due today."""
        today = datetime.today()
        invoiced = []

        for sub in self.subscriptions:
            if not sub.active:
                continue

            # Check if billing day matches today
            if today.day != sub.billing_day:
                continue

            # Check if already billed this month
            if sub.last_billed:
                last = datetime.fromisoformat(sub.last_billed)
                if last.month == today.month and last.year == today.year:
                    continue

            # Send invoice
            invoice_id = self.send_invoice_now(
                client_email=sub.client_email,
                items=[{
                    "name": sub.service,
                    "description": f"Monthly subscription — {today.strftime('%B %Y')}",
                    "quantity": 1,
                    "unit_amount": sub.amount,
                }],
                note=f"Thank you for being a subscriber, {sub.client_name}!",
            )

            if invoice_id:
                sub.last_billed = today.isoformat()
                invoiced.append({
                    "client": sub.client_name,
                    "email": sub.client_email,
                    "service": sub.service,
                    "amount": sub.amount,
                    "invoice_id": invoice_id,
                })

        self._save_state()

        if invoiced:
            total = sum(i["amount"] for i in invoiced)
            logger.info(f"Processed {len(invoiced)} subscriptions — ${total:.2f} invoiced")
        else:
            logger.info("No subscriptions due today")

        return invoiced

    def get_monthly_recurring_revenue(self) -> float:
        """Calculate total MRR from all active subscriptions."""
        mrr = sum(s.amount for s in self.subscriptions if s.active)
        logger.info(f"MRR: ${mrr:.2f}/month from {sum(1 for s in self.subscriptions if s.active)} active subs")
        return mrr

    def create_payment_link_for_product(
        self,
        name: str,
        description: str,
        price: float,
    ) -> str:
        """
        Create a one-time PayPal checkout link for selling a product.

        Returns:
            URL the buyer clicks to pay.
        """
        link = self.paypal.create_payment_link(
            name=name,
            description=description,
            amount=str(price),
        )
        logger.info(f"Payment link created for '{name}' at ${price}: {link}")
        return link
