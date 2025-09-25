# AutomationSEQ — Shopify AI Support App Scaffold

This repository contains a FastAPI scaffold for a public Shopify app that automates email-based support with OpenAI. It includes OAuth installation, usage tracking with quota enforcement, basic billing helpers, spam filtering, and starter prompts for intent classification and reply generation.

## Features

- Public Shopify OAuth flow (`/install` and `/callback`).
- Usage tracking per merchant with quota enforcement and soft blocking once limits are reached.
- Usage-based billing helpers for recurring charges and overage usage charges.
- Email webhook endpoint that classifies intents, looks up Shopify orders, performs simple automations, and generates AI replies.
- Spam filtering so unwanted messages do not count against quotas.
- Dashboard-ready JSON endpoints for usage stats and ticket history.
- Prompt templates for the classifier and reply generator.
- SMTP helper for sending automated replies (replace with Gmail/Microsoft integrations as you iterate).

## Project Structure

```
app/
  ai.py               # OpenAI helpers for classification and reply generation
  billing.py          # Shopify billing utilities
  email_service.py    # SMTP helper for outbound replies
  main.py             # FastAPI application entrypoint
  models.py           # SQLAlchemy models for merchants, usage, and tickets
  shopify_api.py      # Shopify REST helper functions
  shopify_auth.py     # OAuth install + token exchange helpers
  utils.py            # Shared helpers (plan limits, month keys, etc.)
prompts/
  intent_classifier_prompt.txt
  reply_generator_prompt.txt
requirements.txt
.env.example
README.md
```

## Getting Started

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and populate the values (Shopify keys, OpenAI key, database URL, SMTP settings).

3. For local development you can use SQLite by setting `DATABASE_URL=sqlite:///./local.db`.

4. Start the FastAPI server:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Expose the server over HTTPS (e.g., `ngrok http 8000`) and configure your Shopify Partner app settings with the callback URL `https://<your-domain>/callback`.

6. Forward support emails to the `/emails/webhook` endpoint or integrate with Gmail/Outlook polling. The endpoint will classify the message, check quota, fetch Shopify context, send a reply, and log the interaction.

## Next Steps

- Store the activated `recurring_charge_id` to support real usage-based billing.
- Replace the SMTP helper with Gmail API or Microsoft Graph integrations per merchant.
- Add authentication for dashboard endpoints and build a frontend (React/Next.js, etc.).
- Implement robust error handling, observability, and retry logic for Shopify actions.
- Expand policy management and multilingual support as you gather requirements.
