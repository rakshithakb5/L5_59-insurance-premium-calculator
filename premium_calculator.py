"""Insurance premium calculator.

Quotes health, motor and life premiums, works out an applicant's age,
saves quotes to a log, imports policies from partner XML, downloads rate
tables, extracts customer claim archives, splits premiums into
instalments and computes renewal dates.
"""
import hmac
import http.client
import logging
import math
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
    for discount in discounts:
        premium = premium - discount
    return premium


def age_from_dob(dob):
    """Return age in whole years from a DD-MM-YYYY date of birth."""
    born = datetime.strptime(dob, "%d-%m-%Y")
    today = datetime.now()
    age = today.year - born.year
    return age


def policy_number():
    """Return a random, hard-to-guess policy number."""
    return "POL-" + str(100000 + secrets.randbelow(900000))


def save_quote(name, premium):
    """Record a quote in the quote book and the log file."""
    number = policy_number()
    quotes[number] = {"name": name, "premium": premium}
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"{number},{name},{premium:.2f}\n")
    return number


def import_policies(xml_text):
    """Parse partner XML into (type, age, sum) tuples, skipping bad rows."""
    root = ET.fromstring(xml_text)
    result = []
    for policy in root.findall("policy"):
        try:
            result.append((policy.get("type"), int(policy.get("age")),
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
    """Return the amount payable per month."""
    if months == 0:
        return premium
    return math.floor(premium / months)


def is_authorised(token):
    """Return True only if token matches the configured underwriter token."""
    if not UNDERWRITER_TOKEN:
        return False  # no secret configured: nobody is authorised
    return hmac.compare_digest(str(token), UNDERWRITER_TOKEN)


def renewal_due(start, years=1):
    """Return the renewal date, `years` after a YYYY-MM-DD start date."""
    date = datetime.strptime(start, "%Y-%m-%d")
    return date.replace(year=date.year + years).strftime("%Y-%m-%d")


def print_quotes():
    """Print the quote book."""
    print("===== Quote Book =====")
    for i, (number, quote) in enumerate(quotes.items(), start=1):
        print(i, number, quote["name"], "Rs.", quote["premium"])


def main():
    """Run a demonstration of the calculator."""
    p1 = calculate_premium(Applicant("health", 30, 500000, False, 0))
    p2 = calculate_premium(Applicant("health", 30, 500000, False, 0))
    p3 = calculate_premium(Applicant("motor", 50, 800000, "no", 0))
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


main()
