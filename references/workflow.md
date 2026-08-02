# Patrol workflow

## State machine

`OPEN_STORE -> SESSION_CHECK -> SIGN_IN_EMAIL -> PASSWORD -> MFA -> ACCOUNT_SWITCHER -> MARKETPLACE_HOME -> HEALTH -> NOTIFICATIONS -> RECORD -> OPTIONAL_DELIVERY`

## Inputs

- `store_id`: User-selected Ziniao store identifier.
- `marketplaces`: One supported marketplace code or all configured codes.
- `timezone` and `working_hours`: Optional schedule gate; both must be supplied together.
- `output_dir`: Local destination for logs and Markdown records.
- `send_feishu`: Explicit opt-in for delivery.

Do not derive these inputs from private examples or embed user-specific values in the skill.

## Authentication

Reuse the selected store's saved session. If sign-in appears:

1. Require an autofilled `#ap_email`; never type an email.
2. Continue to the saved password flow and require the submit control.
3. If MFA appears, require an already autofilled current OTP.
4. Submit the OTP once. If it is missing, stale, or rejected, stop and request a fresh code through the existing browser integration.

## Marketplace selection and proof

Expand the marketplace list, select the exact target country row, then click the final visible Select account control. Accept the marketplace only when all applicable proof agrees:

- the page is a workbench route such as `/home` or `/amazonsell/business`;
- the target marketplace ID appears in the URL when Amazon supplies `mons_sel_mkid`;
- the rendered page includes the expected country label;
- the host or marketplace ID matches the target.

Do not treat the Seller Central domain alone, a click event, or a returned account-switcher page as success.

## Evidence and output

Collect the account-health page and performance-notifications page independently. After each navigation, require the actual URL path to match the target page and require non-empty rendered text. The Markdown output persists both actual page URLs, both raw page texts, summaries, action suggestions, and the two screenshot paths. The timestamped log is written under `--output-dir`; screenshots remain at the paths returned by `ziniao-cli` and are not copied into that directory. A market succeeds only when both screenshot paths are non-empty and both files exist. All runtime evidence may contain private account data and should remain in user-approved private locations.

## Retry limits

- Navigation timeout: inspect current URL and content first; retry only if the target did not load.
- Browser crash/error page: refresh at most twice.
- Marketplace confirmation: retry once if still on account switcher.
- MFA submission: never retry with the same stale or missing code.
- Batch patrol: continue to the next marketplace after preserving the failure.

## Delivery

Local-only output is the default. Send to Feishu only with `--send-feishu` and a configured chat ID plus app credentials. Report API acceptance only when every message returns code `0` and a non-empty `message_id`; return those IDs in `feishu.message_ids`. Actual chat delivery should still be checked separately when delivery proof matters. A failed or unknown request must not be retried automatically, delete local evidence, or be reported as success.
