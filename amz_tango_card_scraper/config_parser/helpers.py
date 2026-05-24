"""Module that contains helper functions for the config parser."""

from typing import Dict, List, Union


def verify_gmail_section(gmail: Dict[str, str]) -> Dict[str, str]:
    """
    Verify the Gmail section of the config file.

    Supports two auth methods:
      - App Password: requires 'email' + 'app_password'
      - OAuth2:       requires 'email' + 'token_file' + 'credentials_file'

    Args:
        gmail: The Gmail section of the config file.

    Raises:
        ValueError: If the Gmail section is invalid.

    Returns:
        The verified Gmail section of the config file.
    """
    if "email" not in gmail:
        raise ValueError("Missing 'email' in Gmail section of config file.")

    has_password = "password" in gmail and gmail["password"]
    has_app_password = "app_password" in gmail and gmail["app_password"]
    has_oauth2 = "token_file" in gmail and "credentials_file" in gmail

    if not has_password and not has_app_password and not has_oauth2:
        raise ValueError(
            "Gmail auth missing. Provide one of:\n"
            "  - 'password' (browser/web mode — easiest)\n"
            "  - 'app_password' (IMAP + App Password)\n"
            "  - 'token_file' + 'credentials_file' (OAuth2)"
        )
    return gmail


def verify_amazon_section(amazon: Dict[str, str]) -> Dict[str, str]:
    """
    Verify the Amazon section of the config file.

    Args:
        amazon: The Amazon section of the config file.

    Raises:
        ValueError: If the Amazon section is invalid.

    Returns:
        The verified Amazon section of the config file.
    """

    required_fields = ("email", "password", "otp")
    if not all(field in amazon for field in required_fields):
        raise ValueError("Missing required field(s) in Amazon section of config file.")
    return amazon


def verify_from_section(from_list: List[str]) -> List[str]:
    """
    Verify the From section of the config file.

    Args:
        from_list: The From section of the config file.

    Raises:
        ValueError: If the From section is invalid.

    Returns:
        The verified From section of the config file.
    """

    # Check if the list is empty
    if not from_list:
        raise ValueError("Empty from section in config file. Please add at least one" " email address.")
    return from_list


def verify_script_section(script: Dict[str, bool]) -> Dict[str, bool]:
    """
    Verify the Script section of the config file.

    Args:
        script: The Script section of the config file.

    Raises:
        ValueError: If the Script section is invalid.

    Returns:
        The verified Script section of the config file.
    """
    required_fields = (
        "no_images",
        "headless",
        "virtual_display",
        "trash",
        "redeem_amz",
    )
    if not all(field in script for field in required_fields):
        raise ValueError("Missing required field(s) in Script section of config file.")
    return script


def verify_proxies_section(proxies: Union[Dict[str, bool], Dict[str, str]]) -> Union[Dict[str, bool], Dict[str, str]]:
    """
    Verify the Proxies section of the config file.

    Args:
        proxies: The Proxies section of the config file.

    Raises:
        ValueError: If the Proxies section is invalid.

    Returns:
        The verified Proxies section of the config file.
    """

    required_fields = ("enable", "list")
    if not all(field in proxies for field in required_fields):
        raise ValueError("Missing required field(s) in Proxies section of config file.")
    return proxies


def verify_telegram_section(telegram: Dict[str, str]) -> Dict[str, str]:
    """
    Verify the Telegram section of the config file.

    Args:
        telegram: The Telegram section of the config file.

    Raises:
        ValueError: If the Telegram section is invalid.

    Returns:
        The verified Telegram section of the config file.
    """

    required_fields = ("enable", "token", "chat_id")
    if not all(field in telegram for field in required_fields):
        raise ValueError("Missing required field(s) in Telegram section of config file.")
    return telegram
