# Marketplace and UI Label Map

## Marketplaces

| Code | Host suffix | Simplified Chinese | Traditional Chinese | English | Marketplace ID |
|---|---|---|---|---|---|
| us | `com` | 美国 | 美國 | United States / US | ATVPDKIKX0DER |
| ca | `ca` | 加拿大 | 加拿大 | Canada | A2EUQ1WTGCTBG2 |
| mx | `com.mx` | 墨西哥 | 墨西哥 | Mexico / México | A1AM78C64UM0Y8 |
| uk | `co.uk` | 英国 | 英國 | United Kingdom / UK | A1F83G8C2ARO7P |
| de | `de` | 德国 | 德國 | Germany | A1PA6795UKMFR9 |
| fr | `fr` | 法国 | 法國 | France | A13V1IB3VIYZZH |
| it | `it` | 意大利 | 義大利 | Italy | APJ6JRA9NG5V4 |
| es | `es` | 西班牙 | 西班牙 | Spain | A1RKKUPIHCS9HS |
| nl | `nl` | 荷兰 | 荷蘭 | Netherlands | A1805IZSGTT6HS |

## Common controls

| Function | Simplified Chinese | Traditional Chinese | English | Selector or detection |
|---|---|---|---|---|
| Sign in | 登录 | 登入 | Sign in / Log in | `#signInSubmit`, `#auth-signin-button` |
| Continue | 继续 | 繼續 | Continue | `#continue` |
| Select account | 选择账户 | 選取帳戶 | Select account | second visible `kat-button` |
| Account switcher row | 账户 / 账号 | 帳戶 / 帳號 | Select an account | `.full-page-account-switcher-account button` |
| One-time password | 一次性密码 | 一次性密碼 | One Time Password / OTP | `#auth-mfa-otpcode` |
| Account health | 账户健康 | 帳戶健康 | Account health | `/performance/dashboard` |
| Performance notifications | 绩效通知 | 績效通知 | Performance notifications | `/performance/notifications` |

The page may render in English, Spanish, French, German, Italian, Dutch, Simplified Chinese, or Traditional Chinese. Detection requires a valid workbench route and rendered country label, plus either the target host or marketplace ID; do not rely on one translated string or the domain alone.
