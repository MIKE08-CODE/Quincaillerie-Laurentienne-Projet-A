// Contrôle d'audit npm CIBLÉ (aucune exception globale).
//
// Le contrôle échoue si `npm audit` signale :
//   - une vulnérabilité de gravité élevée ou critique;
//   - un avis de sécurité qui n'est pas dans la liste ci-dessous;
//   - n'importe quel avis après la date de réévaluation (l'exception expire).
//
// Exceptions documentées (mobile/README.md, ADR-007) : outillage en ligne de commande d'Expo et de Jest,
// non embarqué dans l'application installée; seule correction proposée par npm : rétrograder vers
// Expo 52, ou monter glob et minimatch d'une version majeure dans les dépendances d'Expo.
import { execFileSync } from "node:child_process";

const ALLOWED = new Map([
  ["GHSA-3g3m-2fjr-6pw4", "glob : contournement de l'annulation par AbortSignal (modérée)"],
  ["GHSA-g3hv-75wg-m249", "minimatch : déni de service par amplification de motifs (modérée)"],
]);
const REVIEW_BY = "2026-12-21"; // réévaluer au plus tard à cette date (mise à jour d'Expo)

let raw;
try {
  raw = execFileSync("npm", ["audit", "--json"], { encoding: "utf8", shell: process.platform === "win32" });
} catch (error) {
  raw = error.stdout; // npm audit sort avec un code non nul dès qu'il trouve une vulnérabilité
}
const report = JSON.parse(raw);
const advisories = new Map();
for (const vulnerability of Object.values(report.vulnerabilities ?? {})) {
  for (const via of vulnerability.via) {
    if (typeof via === "object") advisories.set(via.url.split("/").pop(), via);
  }
}

const problems = [];
const today = new Date().toISOString().slice(0, 10);
for (const [id, advisory] of advisories) {
  if (advisory.severity === "high" || advisory.severity === "critical") {
    problems.push(`${id} (${advisory.name}) : gravité ${advisory.severity}`);
  } else if (!ALLOWED.has(id)) {
    problems.push(`${id} (${advisory.name}) : avis non documenté (${advisory.severity})`);
  } else if (today > REVIEW_BY) {
    problems.push(`${id} (${advisory.name}) : exception expirée le ${REVIEW_BY}, à réévaluer`);
  }
}

console.log(`Avis trouvés : ${advisories.size} — ${[...advisories.keys()].join(", ") || "aucun"}`);
for (const [id, reason] of ALLOWED) {
  console.log(`  exception ${advisories.has(id) ? "utilisée" : "inutile (à retirer)"} : ${id} — ${reason}`);
}
if (problems.length > 0) {
  console.error("Échec de l'audit :\n  " + problems.join("\n  "));
  process.exit(1);
}
console.log(`Audit conforme (exceptions ciblées valables jusqu'au ${REVIEW_BY}).`);
