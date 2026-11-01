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
