# 06.02 AI meal photo recognition

## Context

User snaps a photo of their plate; we estimate foods and portions. Self-hosted vision model via Ollama.

## Goal

Meal photo upload + recognition pipeline that returns candidate meal items the user can confirm or edit.

## Model

- LLaVA (`llava:13b` or `llava-llama3:8b`) on the Ollama VPS.
- Prompt: ask for a JSON-only response listing detected foods with estimated grams and confidence.
- Validate output with a Pydantic schema; reject malformed responses, fall back to "couldn't recognize, please log manually".

## Endpoints

- `POST /v1/meals/recognize` multipart upload `photo`.
  - Returns:
    ```json
    {
      "candidates": [
        { "name": "grilled chicken breast", "grams_estimate": 180, "confidence": 0.8, "food_id_suggestions": ["uuid", "uuid"] },
        ...
      ],
      "raw_caption": "a plate with grilled chicken, white rice, and broccoli"
    }
    ```
  - `food_id_suggestions`: for each detected food name, do a trigram search against `foods` and return top 3 matches.

## Storage

- Photos go to local disk on the VPS under `/var/lib/gymapp/meal-photos/<user>/<yyyy>/<mm>/<uuid>.jpg`. Use a signed URL pattern when serving (HMAC of path + exp, validated in middleware).
- Resize on upload to max 1024px on the long edge, store JPEG quality 85.
- EXIF stripped.

## Rate limit

Per `api-conventions.md` AI endpoints: 60 photo recognitions per user per hour. Add a separate cap of 6 concurrent recognitions across the whole VPS to keep Ollama responsive.

## Deliverables

1. Image upload handler + storage layout.
2. Ollama vision client.
3. Prompt template + JSON validator.
4. Trigram suggestion logic.
5. Tests:
   - Malformed model output -> graceful fallback.
   - Concurrent requests respect the cap (queue or 429).
   - Suggestions match expected foods on a small fixture.

## Acceptance criteria

- For a clear photo of a standard plate (chicken, rice, vegetables), the response contains plausible candidates within 8 seconds on the VPS.
- Photo storage rejects non-images and files > 10 MB.
- The raw caption field is always present and useful even when structured candidates are empty.

## Dependencies

- `06.01 Food database, barcode, and search`
- A working Ollama instance with the vision model pulled.

## Out of scope

- Volume estimation from depth / multiple angles (just one photo).
- Training a custom model on user feedback (later).
