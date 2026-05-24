"""
Multi-Account Rewards Scaler
=============================
Runs the full scrape+redeem+flip pipeline across MULTIPLE Gmail/Amazon
accounts in parallel or sequentially.

Each account has its own config file in:
  accounts/account_01.yaml
  accounts/account_02.yaml
  ...
  accounts/account_N.yaml

Income scales linearly: 10 accounts × $50/mo = $500/mo passive.

Usage:
  python -m businesses.multi_account.runner
"""

import concurrent.futures
import glob
import os
import time
from typing import List, Optional

import yaml

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


def run_single_account(config_path: str) -> dict:
    """
    Run the full pipeline for one account config file.

    Args:
        config_path: Path to a YAML config file for one account.

    Returns:
        Dict with keys: account, cards_found, total_value, status
    """
    account_name = os.path.basename(config_path).replace(".yaml", "")
    logger.info(f"[{account_name}] Starting pipeline...")

    result = {
        "account": account_name,
        "cards_found": 0,
        "amazon_codes": [],
        "total_value": 0.0,
        "status": "ok",
        "error": None,
    }

    try:
        from amz_tango_card_scraper.config_parser.config_parser import parse_config
        from amz_tango_card_scraper.gmail_scraper.gmail_scraper import scrape_tango_cards
        from amz_tango_card_scraper.tango_scraper.tango_scraper import scrap_amazon_gift_cards
        from amz_tango_card_scraper.browser.chrome import get_chrome_browser

        config = parse_config(config_path)

        # Scrape tango cards from Gmail
        tango_cards = scrape_tango_cards(
            email=config.gmail.get("email", ""),
            from_list=config.from_list,
            trash=config.script.get("trash", False),
            app_password=config.gmail.get("app_password", ""),
            token_file=config.gmail.get("token_file", ""),
            credentials_file=config.gmail.get("credentials_file", ""),
        )

        if not tango_cards:
            logger.info(f"[{account_name}] No new Tango Cards found")
            return result

        result["cards_found"] = len(tango_cards)

        # Get Amazon codes
        browser = get_chrome_browser(
            headless=True,
            no_images=True,
            proxies=config.proxies.get("list", []) if config.proxies.get("enable", False) else [],
        )

        try:
            amazon_cards = scrap_amazon_gift_cards(browser=browser, tango_cards=tango_cards)
            result["amazon_codes"] = [c.redeem_code for c in amazon_cards]
            result["total_value"] = len(amazon_cards) * 5.0  # $5 per card default
        finally:
            browser.quit()

        logger.info(f"[{account_name}] Found {len(tango_cards)} tango cards, {len(result['amazon_codes'])} Amazon codes")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"[{account_name}] Pipeline failed: {e}")

    return result


def run_all_accounts(
    accounts_dir: str = "accounts",
    max_workers: int = 3,
    delay_between: float = 5.0,
) -> List[dict]:
    """
    Run the pipeline for all account config files in parallel.

    Args:
        accounts_dir: Directory containing account_XX.yaml files.
        max_workers: How many accounts to run simultaneously.
        delay_between: Seconds to wait between spawning each worker.

    Returns:
        List of result dicts for all accounts.
    """
    pattern = os.path.join(accounts_dir, "*.yaml")
    config_files = sorted(glob.glob(pattern))

    if not config_files:
        logger.warning(f"No account configs found in '{accounts_dir}/'")
        logger.info("Create accounts/account_01.yaml, account_02.yaml, etc.")
        logger.info("Copy config.example.yaml as a template")
        return []

    logger.info(f"Running {len(config_files)} accounts with {max_workers} workers...")

    results = []

    if max_workers == 1:
        # Sequential mode — safest, least detectable
        for cfg in config_files:
            result = run_single_account(cfg)
            results.append(result)
            time.sleep(delay_between)
    else:
        # Parallel mode — faster
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_single_account, cfg): cfg for cfg in config_files}
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Worker crashed: {e}")

    # Summary
    total_cards = sum(r["cards_found"] for r in results)
    total_value = sum(r["total_value"] for r in results)
    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")

    logger.info("=" * 50)
    logger.info("MULTI-ACCOUNT RUN COMPLETE")
    logger.info(f"  Accounts: {len(results)} ({ok} ok, {errors} errors)")
    logger.info(f"  Cards found: {total_cards}")
    logger.info(f"  Total value: ${total_value:.2f}")
    logger.info("=" * 50)

    return results


def create_account_template(output_path: str, email: str, app_password: str) -> None:
    """Helper: create a per-account YAML config file."""
    template = {
        "gmail": {"email": email, "app_password": app_password},
        "amazon": {"email": email, "password": "FILL_ME", "otp": "FILL_ME"},
        "from": ["microsoftrewards@email.microsoftrewards.com"],
        "script": {
            "no_images": True,
            "headless": True,
            "virtual_display": False,
            "trash": True,
            "redeem_amz": True,
        },
        "proxies": {"enable": False, "list": []},
        "telegram": {"enable": False, "token": "", "chat_id": ""},
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(template, f, default_flow_style=False)
    logger.info(f"Account template written to {output_path}")


if __name__ == "__main__":
    results = run_all_accounts()
    for r in results:
        print(f"[{r['account']}] {r['cards_found']} cards | ${r['total_value']:.2f} | {r['status']}")

PAYPAL_PAYOUT_EMAIL = "jayjay@collector.org"
PAYPAL_HANDLE = "@digitalempiresk"
PAYPAL_ME = "https://paypal.me/digitalempiresk"

def get_paypal_summary() -> dict:
    """Return PayPal destination for all multi-account income."""
    return {
        "payout_email": PAYPAL_PAYOUT_EMAIL,
        "handle": PAYPAL_HANDLE,
        "link": PAYPAL_ME,
    }
