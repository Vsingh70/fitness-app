# Deploy runbook

Day-to-day API deploys triggered by CI; this doc covers what happens, how to
trigger it manually, and how to roll back.

## Image promotion

CI publishes new images on every merge to `main` as:

```
ghcr.io/<org>/gymapp-api:<git-sha>
ghcr.io/<org>/gymapp-api:latest
```

`app-compose.yml` pins `latest` so a `docker compose pull` + restart picks up
the newest image without editing the compose file.

## Automatic deploy

Triggered from CI by SSH-ing to the host as `ops` and running:

```
sudo systemctl start gymapp-app-deploy.service
```

The systemd unit invokes `/usr/local/bin/gymapp-app-deploy`, which:

1. `docker compose pull` the new image.
2. `docker compose up -d --no-deps api` (recreates the api container).
3. Polls `http://127.0.0.1:8000/v1/health/ready` for up to 90s. Aborts if
   the new container never becomes healthy.
4. Repeats for the `worker` container.

## Manual deploy

SSH and run:

```
sudo /usr/local/bin/gymapp-app-deploy
```

Or pin to a specific image tag for the duration of the deploy:

```
sudo docker pull ghcr.io/<org>/gymapp-api:<git-sha>
sudo docker tag ghcr.io/<org>/gymapp-api:<git-sha> ghcr.io/<org>/gymapp-api:latest
sudo systemctl start gymapp-app-deploy.service
```

## Rollback

Roll back by re-tagging the previous image as `latest`:

```
sudo docker tag ghcr.io/<org>/gymapp-api:<previous-sha> ghcr.io/<org>/gymapp-api:latest
sudo /usr/local/bin/gymapp-app-deploy
```

Or restore the prior compose by editing `/etc/gymapp/app-compose.yml` to pin
the SHA directly:

```
image: ghcr.io/<org>/gymapp-api:<previous-sha>
```

Then `sudo systemctl reload gymapp-app.service`.

## Smoke test after deploy

```
curl -fs https://api.<domain>/v1/health/ready
curl -fs https://api.<domain>/v1/health/live
sudo docker logs --tail=50 gymapp-api
sudo docker logs --tail=50 gymapp-worker
```

If any of those fail, roll back immediately.

## Database migrations

The API container runs `alembic upgrade head` on startup (or as a separate
`gymapp-migrate` init container if the compose file is updated later). Long
or destructive migrations should be deployed separately under a maintenance
window — coordinate with the user before merging.
