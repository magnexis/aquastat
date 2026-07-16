const baseUrl = process.env.AQUASTAT_BASE_URL || "http://localhost:8080";
const apiKey = process.env.AQUASTAT_API_KEY;

if (!apiKey) throw new Error("AQUASTAT_API_KEY is required");

const response = await fetch(`${baseUrl}/api/v1/estimate?provider=aws&region=us-east-1&load_mw=2.5`, {
  headers: { "X-API-Key": apiKey }
});

if (!response.ok) {
  console.error(await response.text());
  process.exit(1);
}

console.log(await response.json());
