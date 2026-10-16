"""Insurance premium calculator.

Quotes health, motor and life premiums, works out an applicant's age,
saves quotes to a log, imports policies from partner XML, downloads rate
tables, extracts customer claim archives, splits premiums into
instalments and computes renewal dates.
"""
import csv
import hmac
import http.client
import logging
import os
import secrets
import ssl
import tarfile
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from defusedxml import ElementTree as ET

# Global quote book
quotes = {}
# Bind to loopback by default; override with PREMIUM_HOST when deploying.
HOST = os.environ.get("PREMIUM_HOST", "127.0.0.1")
# Secret comes from the environment, never from source control.
UNDERWRITER_TOKEN = os.environ.get("UNDERWRITER_TOKEN", "")
# Log lives next to the script (not in world-writable /tmp).
LOG_FILE = os.environ.get(
    "PREMIUM_LOG_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "premium_quotes.log"))
BASE_RATES = {"health": 5000, "motor": 3000, "life": 8000}


@dataclass
class Applicant:
    """Details of the person being quoted."""

    policy_type: str
    age: int
    sum_insured: int
    smoker: bool
    claims: int

    def __post_init__(self):
        if self.policy_type not in BASE_RATES:
            raise ValueError(f"Unknown policy type: {self.policy_type!r}")
        if not isinstance(self.smoker, bool):
            raise TypeError(
                f"smoker must be True or False, got {self.smoker!r}")
        if self.age < 0 or self.sum_insured < 0 or self.claims < 0:
            raise ValueError("age, sum_insured and claims cannot be negative")


def calculate_premium(applicant, discounts=None):
    """Return the premium for an applicant, minus any discounts."""
    if discounts is None:
        discounts = []
    base = BASE_RATES[applicant.policy_type]
    premium = base + applicant.sum_insured * 0.002
    if applicant.age > 45:
        premium = premium * 1.5
    if applicant.smoker:
        premium = premium * 1.3
    premium = premium + applicant.claims * 1000
    premium = premium - sum(discounts)
    return max(premium, 0.0)  # discounts can never make a premium negative


def age_from_dob(dob, today=None):
    """Return age in whole years from a DD-MM-YYYY date of birth."""
    born = datetime.strptime(dob, "%d-%m-%Y")
    today = today or datetime.now()
    had_birthday = (today.month, today.day) >= (born.month, born.day)
    return today.year - born.year - (0 if had_birthday else 1)


def policy_number():
    """Return a random, hard-to-guess policy number."""
    return "POL-" + str(100000 + secrets.randbelow(900000))


def save_quote(name, premium):
    """Record a quote in the quote book and the log file."""
    number = policy_number()
    while number in quotes:  # never overwrite an existing quote
        number = policy_number()
    quotes[number] = {"name": name, "premium": premium}
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as log:
        # csv module quotes commas/newlines in names so rows stay intact
        csv.writer(log).writerow([number, name, f"{premium:.2f}"])
    return number


def import_policies(xml_text):
    """Parse partner XML into (type, age, sum) tuples, skipping bad rows."""
    root = ET.fromstring(xml_text)
    result = []
    for policy in root.findall("policy"):
        try:
            policy_type = policy.get("type")
            if policy_type not in BASE_RATES:
                raise ValueError(policy_type)
            result.append((policy_type, int(policy.get("age")),
                           int(policy.get("sum"))))
        except (TypeError, ValueError):
            logging.warning("Skipping malformed policy record: %s",
                            policy.attrib)
    return result


def fetch_rates(url):
    """Download a rate table over verified HTTPS and return its bytes."""
    parts = urlparse(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Only https:// URLs are allowed")
    ctx = ssl.create_default_context()  # verifies certificate and hostname
    conn = http.client.HTTPSConnection(parts.hostname, parts.port,
                                       timeout=10, context=ctx)
    try:
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        conn.request("GET", path)
        resp = conn.getresponse()
        if resp.status != 200:
            raise OSError(f"Rate download failed: HTTP {resp.status}")
        return resp.read()
    finally:
        conn.close()


def import_claim_documents(archive_path):
    """Extract a customer-uploaded claim archive into claims_docs/."""
    with tarfile.open(archive_path) as tar:
        # filter="data" blocks absolute paths, ../ traversal, links
        # outside the target and special files (path-traversal defence).
        tar.extractall("claims_docs", filter="data")


def monthly_instalment(premium, months=12):
    """Return the amount payable per month, rounded to the paisa."""
    if months < 1:
        raise ValueError("months must be at least 1")
    return round(premium / months, 2)


def is_authorised(token):
    """Return True only if token matches the configured underwriter token."""
    if not UNDERWRITER_TOKEN:
        return False  # no secret configured: nobody is authorised
    return hmac.compare_digest(str(token), UNDERWRITER_TOKEN)


def renewal_due(start, years=1):
    """Return the renewal date, `years` after a YYYY-MM-DD start date."""
    date = datetime.strptime(start, "%Y-%m-%d")
    try:
        renewal = date.replace(year=date.year + years)
    except ValueError:  # 29 Feb start and a non-leap target year
        renewal = date.replace(year=date.year + years, day=28)
    return renewal.strftime("%Y-%m-%d")


def print_quotes():
    """Print the quote book."""
    print("===== Quote Book =====")
    for i, (number, quote) in enumerate(quotes.items(), start=1):
        print(i, number, quote["name"], "Rs.", quote["premium"])


def main():
    """Run a demonstration of the calculator."""
    p1 = calculate_premium(Applicant("health", 30, 500000, False, 0))
    p2 = calculate_premium(Applicant("health", 30, 500000, False, 0))
    p3 = calculate_premium(Applicant("motor", 50, 800000, False, 0))
    p4 = calculate_premium(Applicant("life", 25, 100000, False, 0),
                           [3000, 3000, 3000])
    print("Quote 1:", p1)
    print("Quote 2 (same customer details):", p2)
    print("Non-smoker aged 50:", p3)
    print("Life with stacked discounts:", p4)
    print("Age from DOB 31-12-1990:", age_from_dob("31-12-1990"))
    print("Monthly instalment:", monthly_instalment(p3))
    print("Renewal due:", renewal_due("2025-03-15"))
    xml_text = ("<policies>"
                "<policy type='health' age='40' sum='300000'/>"
                "<policy type='motor' age='abc' sum='1'/>"
                "</policies>")
    print("Imported:", import_policies(xml_text))
    print("Saved as:", save_quote("Kiran", p1))
    print("Authorised:", is_authorised("wrong-token"))
    print("Server would listen on", HOST)
    print_quotes()


if __name__ == "__main__":
    main()
