# Element Selectors

This document lists the DOM selectors, labels, and verification points used during the login and operation stages of the Amazon Account Patrol automation.

## Core Selectors

| Phase / Stage | Function | Recommended Selector | Alternative Selector / Detection | Pitfall Prevention |
|---|---|---|---|---|
| **Login** | Email Address input | `#ap_email` | - | **Do not type manually**. Must be autofilled by Ziniao. |
| **Login** | Submit Sign-In | `#signInSubmit` | `#auth-signin-button` | Check for email input presence first before submitting. |
| **Login** | Password field | `#ap_password` | - | Must be autofilled. |
| **Login** | MFA OTP code | `#auth-mfa-otpcode` | - | OTP is short-lived. Never submit an expired code. |
| **Account Switcher** | Open Switcher list | `.full-page-account-switcher-account button` | - | Expand first to expose countries. |
| **Account Switcher** | Select Marketplace | Country Row Buttons | Custom labels per market | Target the exact country row button. |
| **Account Switcher** | Confirm Choice | `kat-button` (lower right) | `Select account` button | Ensure the account row is expanded. Click button, retry once if redirect fails. |
| **Workbench** | Account Health | `/performance/dashboard` | - | Verify workbench URL (`/home` or `/amazonsell/business`). |
| **Workbench** | Notifications | `/performance/notifications` | - | Verify the workbench route and country label, plus the target host or `mons_sel_mkid` marketplace ID. |

## Target Marketplace Identifiers

| Code | Host Suffix | Simplified Chinese | English | Marketplace ID (mons_sel_mkid) |
|---|---|---|---|---|
| **us** | `com` | 美国 | United States / US | `ATVPDKIKX0DER` |
| **ca** | `ca` | 加拿大 | Canada | `A2EUQ1WTGCTBG2` |
| **mx** | `com.mx` | 墨西哥 | Mexico / México | `A1AM78C64UM0Y8` |
| **uk** | `co.uk` | 英国 | United Kingdom / UK | `A1F83G8C2ARO7P` |
| **de** | `de` | 德国 | Germany | `A1PA6795UKMFR9` |
| **fr** | `fr` | 法国 | France | `A13V1IB3VIYZZH` |
| **it** | `it` | 意大利 | Italy | `APJ6JRA9NG5V4` |
| **es** | `es` | 西班牙 | Spain | `A1RKKUPIHCS9HS` |
| **nl** | `nl` | 荷兰 | Netherlands | `A1805IZSGTT6HS` |

## Pitfalls & Notes

- **Multi-lingual Support**: Amazon pages may load in English, Spanish, French, German, Italian, Dutch, Simplified Chinese, or Traditional Chinese. Never rely on a single translated text selector; always double-check with fallback tags and attributes like the `mons_sel_mkid` parameter or relative DOM structure.
- **Redirects**: If confirming a marketplace leaves the browser on the `account-switcher` URL, the script will perform one refresh and retry the selection.
