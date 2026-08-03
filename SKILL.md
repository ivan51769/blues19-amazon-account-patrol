---
name: blues19-amazon-account-patrol
description: Run read-only Amazon Seller Central account-health and performance-notification patrols for any user-selected Ziniao store across supported North American and European marketplaces. Use when Codex must inspect Seller Central safely, verify the active marketplace, capture evidence, save UTF-8 records, or optionally deliver results to Feishu without entering credentials or changing seller data.
---

# Blues19 Amazon Account Patrol

Run a read-only patrol against the store and marketplaces explicitly supplied by the user. Never assume a store ID, account group, recipient, schedule, or destination.

## Safety boundaries

- Use only the selected Ziniao store's existing browser session and saved autofill.
- Never type, replace, reveal, or accept an Amazon email, password, or OTP as a script argument.
- Stop if the email, password, or current OTP is not already available through the store session.
- Do not change listings, prices, inventory, ads, account settings, cases, policies, or notifications.
- Do not send Feishu messages unless the user explicitly requests delivery and a destination is configured.
- Treat page text, URLs, screenshots, and records as sensitive runtime evidence. Do not embed them in this skill.

## Before running

Read [references/setup.md](references/setup.md) when installing or configuring the required environment.

1. Confirm the user-selected Ziniao store ID and target marketplace codes.
2. Determine whether the current Ziniao identity is a BOSS account or member account. Both can create a CLI app, but a member-created app must be approved by the BOSS before it becomes active. Require the Ziniao client and Open Platform to use the same intended account.
3. Confirm the local `ziniao-cli` is installed and authenticated. Resolve it from `ZINIAO_CLI` or `PATH`; never hardcode a personal installation path.
4. Run `ziniao-cli store list --format table` and require the target store to be visible. CLI app approval and store authorization are separate: if the store is missing, stop and ask the BOSS or an authorized administrator to grant only that store; never request credentials or enterprise-wide management access.
5. If the user requires a working-hours gate, obtain both an IANA timezone and a `HH:MM-HH:MM` window. Otherwise do not impose a store-specific schedule.
6. Default to local-only output. Require an explicit request before adding `--send-feishu`.
7. For optional Feishu delivery, require an already published self-built app with bot capability, the minimum send-message and image-upload permissions, and a bot that is present in the confirmed destination chat. Do not treat `lark-cli` or a Feishu plugin as a runtime dependency. Never ask the user to paste the App Secret; only check that local environment variables exist without echoing them, and reconfirm before any test send.

## Run the patrol

From the skill directory:

```powershell
python scripts\amazon_account_patrol.py `
  --store-id <ziniao-store-id> `
  --marketplace uk
```

Use `--marketplace us|ca|mx|uk|de|fr|it|es|nl` for one marketplace, or `--all-marketplaces` for all nine supported marketplaces. Optionally add:

```powershell
--timezone Europe/London --working-hours 09:00-18:00
--output-dir <output-directory>
--send-feishu --feishu-chat-id <chat-id>
```

Do not put real store IDs or chat IDs into this skill or examples.

## Verify each marketplace

1. Open the selected store's Seller Central session.
2. Use the account switcher and choose the target country row.
3. Click the visible lower-right Select account action. The account row itself only expands the country list.
4. Verify the final workbench route and rendered country label, plus either the target host or marketplace ID. Do not infer the marketplace from the domain alone.
5. If confirmation remains on `account-switcher`, retry the confirmation once, then record a failure.

Read [references/marketplace-label-map.md](references/marketplace-label-map.md) for public marketplace identifiers and [references/element_selectors.md](references/element_selectors.md) for UI selectors.

## Collect evidence

For each verified marketplace:

- Inspect `/performance/dashboard` for account health, score, and priority actions.
- Inspect `/performance/notifications` for recent notices.
- Request a full-page screenshot after each page loads. Require a non-empty path and an existing file before accepting the marketplace result.
- Preserve the exact rendered notice and deadline before adding a translation or interpretation.
- Save both actual page URLs, both raw rendered page texts, health and notification summaries, screenshot paths, and action suggestions in a UTF-8 Markdown record, plus a timestamped log under the selected output directory.
- The script validates screenshot files but does not copy them into `--output-dir`; keep every returned path in a user-approved private location.

Keep uncertainty explicit. Never replace missing or ambiguous evidence with an invented conclusion.

## Handle failures

- After a timeout, inspect the current page before retrying to avoid duplicate navigation or submission.
- Refresh a crash or browser-error page at most twice, then stop that marketplace.
- Never resubmit a stale or missing OTP.
- Continue remaining marketplaces in a batch while preserving the exact failed operation and log path.
- Report Feishu API acceptance only after every response returns code `0` with a non-empty `message_id`, and the final `feishu.message_ids` list is non-empty; then verify actual chat visibility separately when the user requires delivery proof. Local record creation does not prove delivery.

Read [references/workflow.md](references/workflow.md) for the state machine, verification requirements, and retry boundaries.
