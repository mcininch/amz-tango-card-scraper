"""
PayPal Business Integration
============================
Handles:
  - Sending money to yourself / partners
  - Generating payment links to sell things
  - Auto-creating invoices for services
  - Receiving webhook callbacks when paid
  - Checking account balance

Setup:
  1. Go to https://developer.paypal.com
  2. Create an App -> get Client ID + Secret
  3. Go live: switch PAYPAL_MODE to 'live'
  4. Fill in config.yaml paypal section
"""

import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
LIVE_BASE = "https://api-m.paypal.com"


class PayPalClient:
    """Full PayPal REST API client for business automation."""

    def __init__(self, client_id: str, client_secret: str, mode: str = "sandbox"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = LIVE_BASE if mode == "live" else SANDBOX_BASE
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    #  Auth
    # ------------------------------------------------------------------ #

    def _get_access_token(self) -> str:
        """Fetch (or return cached) OAuth2 bearer token."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        resp = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
        logger.info("PayPal token refreshed")
        return self._access_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    #  Balance
    # ------------------------------------------------------------------ #

    def get_balance(self) -> Dict[str, Any]:
        """Return all currency balances on the account."""
        resp = requests.get(
            f"{self.base_url}/v1/reporting/balances",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    #  Payouts — send money
    # ------------------------------------------------------------------ #

    def send_payout(
        self,
        recipient_email: str,
        amount: str,
        currency: str = "USD",
        note: str = "Automated payout",
        sender_item_id: str = "auto_001",
    ) -> Dict[str, Any]:
        """
        Send money to any PayPal email instantly.

        Args:
            recipient_email: PayPal email of the recipient.
            amount: Dollar amount as string e.g. '25.00'.
            currency: ISO currency code.
            note: Message shown to recipient.
            sender_item_id: Your internal reference ID.

        Returns:
            PayPal payout batch response dict.
        """
        payload = {
            "sender_batch_header": {
                "sender_batch_id": f"batch_{int(time.time())}",
                "email_subject": "You have a payment!",
                "email_message": note,
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {"value": amount, "currency": currency},
                    "note": note,
                    "sender_item_id": sender_item_id,
                    "receiver": recipient_email,
                }
            ],
        }
        resp = requests.post(
            f"{self.base_url}/v1/payments/payouts",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Payout sent to {recipient_email}: ${amount} — batch {result.get('batch_header', {}).get('payout_batch_id')}")
        return result

    # ------------------------------------------------------------------ #
    #  Invoices — bill clients automatically
    # ------------------------------------------------------------------ #

    def create_invoice(
        self,
        recipient_email: str,
        recipient_name: str,
        items: List[Dict[str, Any]],
        note: str = "Thank you for your business!",
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """
        Create and send a PayPal invoice automatically.

        Args:
            recipient_email: Client's email.
            recipient_name: Client's display name.
            items: List of dicts with keys: name, description, quantity, unit_amount
            note: Invoice footer note.
            currency: ISO currency code.

        Returns:
            Invoice dict with 'id' and 'href'.

        Example item:
            {"name": "SEO Report", "description": "May 2026", "quantity": 1, "unit_amount": "49.00"}
        """
        detail_items = [
            {
                "name": item["name"],
                "description": item.get("description", ""),
                "quantity": str(item["quantity"]),
                "unit_amount": {"currency_code": currency, "value": str(item["unit_amount"])},
            }
            for item in items
        ]

        payload = {
            "detail": {
                "invoice_number": f"INV-{int(time.time())}",
                "currency_code": currency,
                "note": note,
                "payment_term": {"term_type": "DUE_ON_RECEIPT"},
            },
            "invoicer": {},
            "primary_recipients": [
                {
                    "billing_info": {
                        "email_address": recipient_email,
                        "name": {"full_name": recipient_name},
                    }
                }
            ],
            "items": detail_items,
        }

        # Create draft
        resp = requests.post(
            f"{self.base_url}/v2/invoicing/invoices",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        invoice = resp.json()
        invoice_id = invoice["id"]
        logger.info(f"Invoice {invoice_id} created for {recipient_email}")

        # Send it
        requests.post(
            f"{self.base_url}/v2/invoicing/invoices/{invoice_id}/send",
            headers=self._headers(),
            json={"send_to_recipient": True},
            timeout=30,
        )
        logger.info(f"Invoice {invoice_id} sent to {recipient_email}")
        return invoice

    # ------------------------------------------------------------------ #
    #  Payment Links — sell products / gift cards
    # ------------------------------------------------------------------ #

    def create_payment_link(
        self,
        name: str,
        description: str,
        amount: str,
        currency: str = "USD",
        return_url: str = "https://yoursite.com/success",
        cancel_url: str = "https://yoursite.com/cancel",
    ) -> str:
        """
        Create a one-time PayPal checkout link (order).

        Returns:
            Approval URL the buyer clicks to pay.
        """
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": description,
                    "amount": {
                        "currency_code": currency,
                        "value": amount,
                        "breakdown": {
                            "item_total": {"currency_code": currency, "value": amount}
                        },
                    },
                    "items": [
                        {
                            "name": name,
                            "unit_amount": {"currency_code": currency, "value": amount},
                            "quantity": "1",
                            "category": "DIGITAL_GOODS",
                        }
                    ],
                }
            ],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "brand_name": "AutoBusiness Suite",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
            },
        }
        resp = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        order = resp.json()

        for link in order.get("links", []):
            if link["rel"] == "approve":
                logger.info(f"Payment link created: {link['href']}")
                return link["href"]

        raise ValueError(f"No approval link in PayPal response: {order}")

    # ------------------------------------------------------------------ #
    #  Transaction History
    # ------------------------------------------------------------------ #

    def list_transactions(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """List recent transactions for income tracking."""
        from datetime import datetime, timedelta, timezone

        start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = urlencode({
            "start_date": start,
            "end_date": end,
            "fields": "all",
            "page_size": 100,
        })

        resp = requests.get(
            f"{self.base_url}/v1/reporting/transactions?{params}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        txns = data.get("transaction_details", [])
        logger.info(f"Found {len(txns)} transactions in last {days_back} days")
        return txns
