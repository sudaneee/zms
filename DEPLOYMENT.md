# Deploying ZMS (Zaria Merit School) — RynoB Exams Pro

The live database is the school's only copy of 4,400 students, 251,000 results
and 22,600 behavioural assessments. Every step below either leaves it
untouched or is preceded by a verified backup. **Never upload, copy or
`git checkout` a `db.sqlite3` over the server's file.**

Values in `<angle brackets>` are filled in once the VPS and repository are known.

## What the upgrade changes in the database

| Migration | Effect on data |
|---|---|
| `src.0012`–`0017` | New columns and tables only (sections, archive flag, review log). `src_studentclass` is rebuilt to rename `class_name` to `name`; ids, names and rows are preserved. |
| `src.0018` | Creates the sections **Nursery & Primary** and **Secondary**, puts each class in one by its name (`Class 1`, `________` and `2616` get none), and archives the 43 classes with no 2025/2026 results. Recorded in the data-review log; undone by migrating back. |
| `src.0019` | Soft-delete columns, audit trail and role profiles (new tables/columns only). |
| `src.0020` | A role for every account: superusers become Administrators; `zmsnp1-5` Staff in Nursery & Primary; `teacher1-13` Staff in Secondary; anyone else Staff without a section (sees nothing until given one on the Users page). |
| `src.0021`–`0023` | E-signature/approval table, the exam ABS flag, and two indexes on results. |
| `eval.0004` | New evaluation tables; the 3 existing evaluations (60 rows) are copied in. The old table is kept unchanged. |

Rehearsal on a copy of the database (2026-11-10): every original value in
`src_student`, `src_studentresult`, `src_studentbehaviouralassessment` and
`src_studentclass` was identical before and after; `PRAGMA integrity_check`
ok; no foreign-key errors. Report cards and broadsheets for 25 class/term
combinations matched the old system, except where the old system was wrong
(students without a behaviour record were left off; broadsheet scores shifted
into the wrong subject column when a student missed a subject).

The fees tables (`fees_*`) are left untouched; nothing in the code uses them.

## Server layout

| What | Where |
|---|---|
| Code (git clone) | `/var/www/zms/app` |
| Python environment | `/var/www/zms/venv` (Python 3.12) |
| Settings / secrets (not in git) | `/var/www/zms/.env` (root:www-data, 640) |
| SQLite database | `/var/www/zms/data/db.sqlite3` |
| Uploaded media (report headers, signatures) | `/var/www/zms/media` |
| Collected static files | `/var/www/zms/staticfiles` |
| Backups (daily, 30 kept) | `/var/www/zms/backups` |
| Service | `zms.service` (gunicorn, user www-data), socket `/run/zms/gunicorn.sock` |
| nginx site | `/etc/nginx/sites-available/<domain>` |

### `.env`

```
DJANGO_SECRET_KEY=<long random string: python -c "import secrets; print(secrets.token_urlsafe(60))">
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=<domain>,www.<domain>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<domain>,https://www.<domain>
DJANGO_DB_PATH=/var/www/zms/data/db.sqlite3
DJANGO_MEDIA_ROOT=/var/www/zms/media
DJANGO_STATIC_ROOT=/var/www/zms/staticfiles
DJANGO_BACKUP_DIR=/var/www/zms/backups
DJANGO_SSL_REDIRECT=1
DJANGO_HSTS_SECONDS=31536000
# Optional
# DJANGO_SCHOOL_NAME=Zaria Merit School
# DJANGO_REPORT_SHOW_CLASS_POSITION=0
# DJANGO_EMAIL_HOST=smtp.gmail.com
# DJANGO_EMAIL_USER=<mailbox>
# DJANGO_EMAIL_PASSWORD=<app password>
```

Set `DJANGO_HSTS_SECONDS` only once HTTPS works for the domain and every subdomain.

### `zms.service`

```ini
[Unit]
Description=ZMS (gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/zms/app
EnvironmentFile=/var/www/zms/.env
RuntimeDirectory=zms
ExecStart=/var/www/zms/venv/bin/gunicorn school.wsgi:application --bind unix:/run/zms/gunicorn.sock --workers 2 --timeout 120
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Two workers suit SQLite. The 120-second timeout covers the heaviest pages
(Data Review over all sections takes about 6 seconds today).

### nginx

```nginx
server {
    listen 80;
    server_name <domain> www.<domain>;
    client_max_body_size 6M;          # Excel uploads are limited to 5 MB
    location /static/ { alias /var/www/zms/staticfiles/; }
    location /media/  { alias /var/www/zms/media/; }
    location / {
        proxy_pass http://unix:/run/zms/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then `certbot --nginx -d <domain> -d www.<domain>`. If other sites share the
server, never `systemctl restart nginx`; use `nginx -t && systemctl reload nginx`.

## First deployment

1. **Freeze the old site** (maintenance window, ideally outside term-entry
   weeks) so nobody enters results during the move.
2. **Take the live database and media** from the current host
   (PythonAnywhere: Files tab or `scp`): `db.sqlite3` and the `media/` folder.
   Keep this original copy untouched somewhere safe.
3. **Rehearse on a copy** on the VPS before the real thing:
   ```bash
   cp db.sqlite3 /tmp/rehearsal.sqlite3
   DJANGO_DB_PATH=/tmp/rehearsal.sqlite3 venv/bin/python app/manage.py migrate
   python app/tools/db_fingerprint.py diff db.sqlite3 /tmp/rehearsal.sqlite3
   ```
   Only the tables listed above may change.
4. **Install**:
   ```bash
   mkdir -p /var/www/zms/{data,media,backups,staticfiles}
   git clone <repo> /var/www/zms/app
   python3.12 -m venv /var/www/zms/venv
   /var/www/zms/venv/bin/pip install -r /var/www/zms/app/requirements.txt
   cp db.sqlite3 /var/www/zms/data/ && cp -r media/* /var/www/zms/media/
   chown -R www-data:www-data /var/www/zms/{data,media,backups,staticfiles}
   cd /var/www/zms/app && set -a && . ../.env && set +a
   sudo -u www-data -E ../venv/bin/python manage.py backup_db --label pre-upgrade
   sudo -u www-data -E ../venv/bin/python manage.py migrate
   ../venv/bin/python manage.py collectstatic --noinput
   ../venv/bin/python manage.py check --deploy
   systemctl enable --now zms
   ```
5. **Daily backup** — `/etc/cron.d/zms`:
   ```
   30 1 * * * www-data cd /var/www/zms/app && set -a && . ../.env && set +a && ../venv/bin/python manage.py backup_db
   ```
6. **Point DNS** at the VPS and switch off the old site.
7. **After go-live** (administrator, on the Users page):
   - review the 11 superuser accounts and remove those no longer needed;
   - replace the shared `teacher1-13` / `zmsnp1-5` logins with personal accounts;
   - give `Hantama`, `mahmadzms` and `maahad` a section or deactivate them;
   - choose a section for `Class 1`, `________` and `2616` in the admin panel.

## Updating the code

```bash
cd /var/www/zms
sudo -u www-data ./venv/bin/python app/manage.py backup_db --label pre-update   # with .env loaded
git -C app pull
venv/bin/pip install -r app/requirements.txt
cd app && set -a && . ../.env && set +a
sudo -u www-data -E ../venv/bin/python manage.py migrate
../venv/bin/python manage.py collectstatic --noinput
systemctl restart zms
```

## Restoring a backup

```bash
systemctl stop zms
gunzip -c /var/www/zms/backups/db-<timestamp>.sqlite3.gz > /var/www/zms/data/db.sqlite3
chown www-data:www-data /var/www/zms/data/db.sqlite3
systemctl start zms
```
