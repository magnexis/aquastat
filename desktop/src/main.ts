import { AquaStatDesktopClient } from "./api.js";

const client = new AquaStatDesktopClient("http://127.0.0.1:8080");

async function run(): Promise<void> {
  const facility = await client.fetchFacility("fac_syn_ashburn");
  const templates = await client.fetchPublicRecordTemplates("fac_syn_ashburn");

  const output = {
    connectedMode: "local",
    facilityName: facility.facility.name,
    primaryFigure: facility.primary_water_figure?.figure_type ?? "unknown",
    evidenceClass: facility.primary_water_figure?.evidence_class ?? "Level U",
    contradictionCount: facility.contradictory_claims.length,
    publicRecordAuthorities: templates.known_holders.map((holder) => holder.authority),
  };

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(output, null, 2);
  document.body.append(pre);
}

void run();
