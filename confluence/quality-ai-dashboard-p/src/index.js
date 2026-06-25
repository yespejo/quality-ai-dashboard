import Resolver from '@forge/resolver';

const BASE_URL = "https://raw.githubusercontent.com/yespejo/quality-ai-dashboard/main/data";

const resolver = new Resolver();


// Fetch the full historical time-series data so the frontend can draw
// trend curves (health, coverage, snyk) for each pod.
// history.json shape:
//   { pods: { [podName]: { dates[], codescene: { health[], coverage[] }, snyk: { critical[], high[], medium[] } } } }
resolver.define(
  'getHistory',
  async () => {
    const response = await fetch(`${BASE_URL}/history.json`);
    return await response.json();
  }
);


// Fetch the latest snapshot so the frontend can show the per-repo detail table.
// latest.json shape:
//   { date, pods: [ { name, codescene, snyk, repos: [ { name, codescene, snyk } ] } ] }
resolver.define(
  'getLatest',
  async () => {
    const response = await fetch(`${BASE_URL}/latest.json`);
    return await response.json();
  }
);


export const handler = resolver.getDefinitions();