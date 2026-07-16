# Square Setup

This project already supports real Square-hosted checkout links and Square webhook verification. To finish the live hookup, configure a Square Developer application and copy the resulting values into AquaStat.

## Required AquaStat environment variables

Set these values in local `.env` and in Render:

- `AQUASTAT_BILLING_ENABLED=true`
- `AQUASTAT_CASH_APP_PAY_ENABLED=true`
- `AQUASTAT_BILLING_CHECKOUT_BASE_URL=https://aquastat-api.onrender.com`
- `AQUASTAT_SQUARE_ENVIRONMENT=sandbox` or `production`
- `AQUASTAT_SQUARE_APPLICATION_ID=...`
- `AQUASTAT_SQUARE_ACCESS_TOKEN=...`
- `AQUASTAT_SQUARE_LOCATION_ID=...`
- `AQUASTAT_SQUARE_WEBHOOK_SIGNATURE_KEY=...`
- `AQUASTAT_SQUARE_WEBHOOK_NOTIFICATION_URL=https://aquastat-api.onrender.com/api/v1/billing/webhooks/square`
- `AQUASTAT_PUBLIC_SQUARE_APPLICATION_ID=...`
- `AQUASTAT_PUBLIC_SQUARE_LOCATION_ID=...`

## Where each value comes from

According to Square’s official docs:

- Access token:
  Open your Square app in the Developer Console, choose `Credentials`, then copy the Sandbox or Production access token.
- Location ID:
  Open your Square app in the Developer Console, choose `Locations`, then copy the location ID for the seller account you want to use.
- Webhook signature key:
  Open your Square app in the Developer Console, choose `Webhooks`, open the webhook subscription, then reveal and copy the signature key.

Sources:

- https://developer.squareup.com/docs/build-basics/access-tokens
- https://developer.squareup.com/docs/locations-api
- https://developer.squareup.com/docs/webhooks/step2subscribe
- https://developer.squareup.com/docs/webhooks/step3validate

## Recommended webhook subscriptions

Create a webhook subscription with:

- Notification URL:
  `https://aquastat-api.onrender.com/api/v1/billing/webhooks/square`
- Event types:
  `payment.created`
  `payment.updated`

The backend validates the `x-square-hmacsha256-signature` header using the configured notification URL and raw request body.

Behavior:

- `payment.created` is accepted by the same handler and recorded as an incoming Square payment event.
- Prepaid quota is not issued on an early created/pending state.
- Quota is issued after the webhook payload reflects a settled payment state such as `COMPLETED`, `PAID`, or `SUCCEEDED`, which typically arrives on `payment.updated`.

## Verify the connection

After saving the env vars, run:

```bash
python scripts/verify_square_setup.py
```

Expected behavior:

- It calls Square `GET /v2/locations`.
- It confirms that the configured location ID is valid for the configured access token.
- It reports whether billing, public IDs, and webhook signature configuration are present.

## Render settings

Add the same variables in Render for the live service. After updating them, redeploy and verify:

```bash
curl https://aquastat-api.onrender.com/health
curl -H "X-API-Key: YOUR_KEY" https://aquastat-api.onrender.com/api/v1/billing/packages
```

## Current limitation

Square credentials and webhook secrets must come from your Square account. AquaStat cannot generate or retrieve them automatically.
