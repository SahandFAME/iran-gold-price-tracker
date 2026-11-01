# Iran 18K Gold Workbook Updater

Daily GitHub Actions updater for `اسناد/Geram18-tahlil-updated.xlsm` in a personal OneDrive account.

The job:

- reads TGJU's 18K-gold **Highest Price** and converts the published rial value to the workbook's toman unit;
- appends every Tehran calendar date;
- carries the last available price forward when TGJU has no observation;
- reconciles late TGJU observations from the previous 14 days;
- extends the workbook's shared formulas, cached formula values, and all six chart ranges/caches;
- verifies that the VBA project is byte-for-byte unchanged before uploading;
- refuses to upload if the OneDrive source changed while the job was running.

The workflow runs at 17:30 UTC (21:00 Tehran) every day. It can also be started manually from the repository's **Actions** tab.

## One-time personal OneDrive authorization

Install [rclone](https://rclone.org/install/) on a trusted computer, then run:

```text
rclone config
```

Create a new remote with these choices:

1. Name: `onedrive_personal`
2. Storage: `onedrive`
3. Client ID and client secret: leave both blank
4. Advanced configuration: `n`
5. Use a web browser to authenticate: `y`
6. Sign in with the personal Microsoft account that owns the workbook
7. Select the personal OneDrive drive and confirm the configuration

Locate the resulting configuration file with:

```text
rclone config file
```

In the GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**. Create a secret named `RCLONE_CONFIG` and paste the complete contents of that rclone configuration file as its value.

The configuration contains a sensitive OAuth refresh token. Store it only in the GitHub secret; never commit it, paste it into an issue, or send it in chat.

## Activation

The workflow file must be present on the repository's default branch for scheduled runs. After adding the secret and merging the updater, open **Actions → Update 18K gold workbook → Run workflow** once. Confirm the run succeeds and that OneDrive shows a new workbook version.
