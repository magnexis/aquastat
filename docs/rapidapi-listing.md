# RapidAPI Listing Draft

## Title

AquaStat API

## Subtitle

Water-aware infrastructure analytics for cloud regions

## Suggested Pricing

- Free: 100 requests / month
- Developer: 10,000 requests / month
- Pro: 100,000 requests / month
- Business: custom

## Authentication

- Header: `X-API-Key`
- Alternate: `Authorization: Bearer ...`

## Setup Checklist

1. Import `openapi.json`
2. Configure marketplace auth mapping to `X-API-Key`
3. Validate `/health`
4. Validate `/api/v1/estimate`
5. Document rate limits and 429 behavior
