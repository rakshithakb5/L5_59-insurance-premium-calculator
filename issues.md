\# Issues found - premium\_calculator.py (SRN PES2UG24CS918)



Before: Pylint 5.73/10, Bandit 10 issues (1 High, 5 Medium, 4 Low), Flake8 19 issues

After: Pylint 10.00/10, Bandit 0 issues, Flake8 0 issues



| Issue | Type | Line(s) | Description | Fix Approach |

|-------|------|---------|-------------|--------------|

| tarfile.extractall without validation (B202) | Security (High) | 64 | A customer-uploaded archive can contain ../ paths and overwrite files outside claims\_docs. | Use a with-block and extract with filter="data" to block unsafe paths. |

| SSL certificate check disabled (B323) | Security (Medium) | 58 | \_create\_unverified\_context accepts any certificate, so rate downloads can be tampered with. | Use ssl.create\_default\_context(), which verifies the server. |

| urlopen accepts any URL scheme (B310) | Security (Medium) | 59 | file:// or other schemes can be passed as the URL. | Allow only https URLs and use http.client.HTTPSConnection. |

| Binding to all interfaces (B104) | Security (Medium) | 12 | HOST = "0.0.0.0" exposes the service on every network. | Default to 127.0.0.1, overridable with PREMIUM\_HOST. |

| Hardcoded /tmp log path (B108) | Security (Medium) | 14 | Predictable file in a shared temp folder can be tampered with. | Save the log next to the script. |

| XML parsed with stdlib ElementTree (B314, B405) | Security (Medium/Low) | 7, 48 | Untrusted partner XML can carry XML attacks. | Use defusedxml. |

| Hardcoded secret token (B105) | Security (Low) | 13 | Password is written in the source code. | Read from the UNDERWRITER\_TOKEN environment variable and compare with hmac.compare\_digest. |

| random for policy numbers (B311) | Security (Low) | 37 | random is predictable. | Use secrets.randbelow and regenerate if the number already exists. |

| Bare except and silent continue (E722, W0702, B112) | Bug | 53 | Hides every error and silently drops bad records. | Catch (TypeError, ValueError) and log a warning. |

| Mutable default argument (W0102) | Bug | 17, 27 | discounts=\[] is shared across calls and 500 was appended, so identical quotes differ (6000 vs 5500). | Default to None, create the list inside, and remove the hidden append. |

| smoker "no" treated as a smoker | Logic bug | 92 | A non-empty string is truthy, so a non-smoker paid 30% extra (7970 instead of 6900). | Applicant class checks smoker is True or False. |

| Negative premium | Logic bug | 25-26 | Stacked discounts gave -800. | Subtract the sum of discounts and keep the result at 0 or more. |

| Age ignores birthday | Logic bug | 33 | DOB 31-12-1990 gave 36, but the age is 35 until 31 Dec. | Subtract 1 if the birthday has not happened yet this year. |

| Instalment drops paise | Logic bug | 71 | math.floor loses money (664 x 12 is 7968, not 7970). | round(premium / months, 2) and reject months below 1. |

| Renewal crashes on 29 Feb | Logic bug | 81 | Raises ValueError when the next year is not a leap year. | Fall back to 28 Feb. |

| Files opened without with (R1732, W1514) | Code quality | 42-44, 63-65 | Resource leaks and no encoding. | Use with open(..., encoding="utf-8") and with tarfile.open(). |

| camelCase names and no docstrings (C0103, C0114, C0116) | Style | many | Not PEP 8. | snake\_case names and docstrings. |

| Too many arguments (R0913, R0917) | Design | 17 | 6 positional parameters. | Group them in an Applicant dataclass. |

| Flake8 E302, E305, E501 | Style | many | Missing blank lines and long lines. | Reformatted. |

