# Iran 18K Gold Workbook Updater

Cloud-only Vercel Cron updater for `اسناد/Geram18-tahlil-updated.xlsm` in a personal OneDrive account.

The job:

- reads TGJU's 18K-gold **Highest Price** and converts the published rial value to the workbook's toman unit;
- appends every Tehran calendar date;
- carries the last available price forward when TGJU has no observation;
- reconciles late TGJU observations from the previous 14 days;
- extends the workbook's shared formulas, cached formula values, and all six chart ranges/caches;
- verifies that the VBA project is byte-for-byte unchanged before uploading;
- writes with the Microsoft Graph eTag so it cannot overwrite a concurrent workbook edit.

The Vercel Cron runs at 17:30 UTC (21:00 Tehran) every day. The endpoint accepts Vercel's automatically supplied `CRON_SECRET` bearer token.

## Personal Microsoft authorization

The Microsoft application is registered for personal accounts and uses OAuth device authorization. The user signs in at Microsoft's device-login page once; no local application or client secret is required.

The refresh token and any temporary device code are encrypted before being placed in a private Vercel Blob store. The encryption key and setup secret are sensitive production environment variables. Provider access tokens are never logged or returned by an API route.

Required production configuration:

- `MS_CLIENT_ID`
- `TOKEN_ENCRYPTION_KEY`
- `SETUP_SECRET`
- `CRON_SECRET`
- `GRAPH_DRIVE_ID`
- `GRAPH_ITEM_ID`
- the project-connected private Blob credential

The project is separate from other deployments, so its schedule, credentials, and failures cannot affect them.

## Persian Telegram bot

The same isolated project also exposes a Persian Telegram bot. Telegram sends signed webhook updates to `/api/telegram`; the endpoint rejects requests that do not contain the configured Telegram secret header.

Access is approval-only:

- the numeric `TELEGRAM_ADMIN_ID` is the protected root administrator;
- new users are recorded as pending after they send `/start` and cannot open reports; every access request notifies all approved administrators with Approve and Deny buttons;
- administrators can approve, deny, promote, demote, or remove users, and can add a member by known username or numeric Telegram ID;
- user records and admin audit events are encrypted before being written to the existing private Blob store.

The main menu uses Telegram's persistent bottom keyboard outside the chat messages, with Report available to every approved user and the Admin Dashboard added for administrators. User messages are never deleted. The bot tracks only its latest transient answer: each new menu or admin answer deletes the preceding answer before it is sent. Reports are intentionally not tracked or deleted, so users retain their report history. Returning to the main menu shows a compact menu message instead of repeating the welcome text. The admin dashboard shows only relevant access statistics and actions. Authorized users, pending requests, and user/role management all use a consistent numbered list with three accounts per page, numbered action buttons, page navigation, and dashboard/main-menu return buttons.

The report reads two independent sources: TGJU's live 18K quote and the latest cached calculation row in the macro-enabled workbook. It displays only the requested analytical values with their Persian labels and explanations; historical reports remain in the Telegram chat.

Additional sensitive production configuration:

- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_ADMIN_ID`

The non-secret `TELEGRAM_CONNECTOR` value identifies a Telegram connector attached to this project in Vercel Connect. The BotFather token is entered directly into that connector and is requested at runtime with the deployment's project OIDC identity; it is never stored in project environment variables.

The Persian display name, short description, full description, and branded avatar are versioned in the application. The protected setup route and the `/start` handler synchronize them through Telegram's Bot API; an encrypted Blob marker prevents duplicate profile-photo updates. Approved users receive the full Persian introduction and keyboard on `/start`, while pending users receive the access-approval introduction.

After those values are configured, call the protected `/api/telegram_setup` endpoint once with the existing setup bearer secret. It registers the webhook and the Persian `/start` and `/report` commands without returning either Telegram secret.
