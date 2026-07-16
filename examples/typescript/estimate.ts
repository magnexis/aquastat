const baseUrl = process.env.AQUASTAT_BASE_URL || "http://localhost:8080";
const apiKey = process.env.AQUASTAT_API_KEY;

if (!apiKey) {
  throw new Error("AQUASTAT_API_KEY is required");
}

async function main(): Promise<void> {
  const response = await fetch(`${baseUrl}/api/v1/estimate?provider=aws&region=us-east-1&load_mw=2.5`, {
    headers: { "X-API-Key": apiKey }
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  console.log(await response.json());
}

void main();
