# Synthetic checks

External liveness probing. Our internal Prometheus + Grafana stack runs on
the same VPS as the API — useful for everything except the one failure
mode where the whole VPS is offline. External synthetic checks cover that
gap.

## Provider: BetterStack (was Better Uptime)

Free tier supports a single monitor at 60-second intervals, which is what
we need.

## One-time setup

1. Sign up at https://betterstack.com/.
2. Monitors → Create monitor → "HTTP / HTTPS".
3. Use the values from [`betterstack-monitor.json`](./betterstack-monitor.json)
   for URL, frequency, expected status, etc.
4. Replace `api.example.com` with your actual `app_domain`.
5. Notifications:
   - Add an email contact.
   - Add a Discord webhook (same one used by `api-deploy.yml`).
6. Status page: optional. Free tier supports one.

## What to verify after setup

- Trigger a `:fire:` test by SSH'ing to the VPS and stopping the API:
  ```
  ssh ops@<host> sudo systemctl stop gymapp-app.service
  ```
  Within 2 minutes, BetterStack should alert. Restart immediately:
  ```
  ssh ops@<host> sudo systemctl start gymapp-app.service
  ```
- Recovery alert should fire within ~90 seconds of the API coming back up.

## Why not self-hosted?

A check running on the same VPS as the API can't tell you when the VPS
itself is offline. Even a check on a sibling VPS or in CI would tell us
less than an external service whose only job is to ping endpoints
worldwide.

GitHub Actions cron *could* work but the 5-minute scheduling cap and
the runner spin-up latency make it noisy.
