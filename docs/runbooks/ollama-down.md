# Ollama down

Ollama hosts the LLM that powers recommendation rationales and meal photo
recognition. Both code paths fall back to safe defaults if Ollama fails, so
**Ollama being down is not user-visible immediately**. The system continues
to serve requests; rationales come from `fallbacks.yaml` and photo recognition
returns an empty candidates list with a "could not analyze" caption.

That said: rationales become repetitive and photo recognition is unusable.
Fix it within an hour.

## Verify it's actually down

From your laptop:

```
ssh ops@<host> curl -sS http://127.0.0.1:11434/api/version
```

Expected: `{"version":"0.5.x"}`. If you get connection refused or a timeout,
Ollama is down.

Check systemd:

```
ssh ops@<host> sudo systemctl status ollama
ssh ops@<host> sudo journalctl -u ollama --no-pager -n 100
```

## Common causes

### 1. Out of memory

Ollama loads models into memory. With both `qwen2.5:7b-instruct` and
`llava-llama3:8b` resident on an 8 GB CCX33, OOM is the most common cause.

```
ssh ops@<host> free -h
ssh ops@<host> sudo dmesg | grep -i "killed process" | tail -5
```

Mitigation:

```
ssh ops@<host> sudo systemctl restart ollama
# Pre-warm only one model to free memory:
ssh ops@<host> ollama run qwen2.5:7b-instruct "hello" </dev/null
```

If OOM keeps recurring, drop one model from `ollama_models` in
`group_vars/all.yml` and re-run Ansible. Long-term fix: bigger VPS.

### 2. Disk full (model storage in /var/lib/ollama)

```
ssh ops@<host> df -h /var/lib/ollama
ssh ops@<host> du -sh /var/lib/ollama/manifests/*
```

If full: `ollama rm <unused-tag>` for models you don't need anymore.

### 3. Update went sideways

If the host auto-updated Ollama via `install.sh`:

```
ssh ops@<host> ollama --version
ssh ops@<host> sudo systemctl restart ollama
```

If a specific version is broken, pin the previous one by editing the
ollama role's `install.sh` invocation.

## Fall back to templates (no action required)

The application code is already defensive:

- `app/services/ai/rationales.py::generate_rationale` catches `OllamaError`
  and falls back to `fallbacks.yaml` templates.
- `app/services/ai/photo_recognition.py::recognize_meal_photo` returns an
  empty candidates list with a synthetic caption.

You don't need to do anything in the app to enable fallbacks; they kick in
automatically on every Ollama failure.

## Verify after recovery

```
ssh ops@<host> curl -sS http://127.0.0.1:11434/api/version
ssh ops@<host> ollama list   # confirms models are loaded
```

Then trigger a real rationale by finishing a test workout — check that
`recommendations.rationale` is filled with non-template text within 30s.
