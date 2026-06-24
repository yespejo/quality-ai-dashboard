import Resolver from '@forge/resolver';


const resolver = new Resolver();


// Fetch the full historical time-series data so the frontend can draw
// trend curves (health, coverage, snyk) for each pod.
// history.json shape:
//   { pods: { [podName]: { dates[], codescene: { health[], coverage[] }, snyk: { critical[], high[], medium[] } } } }
resolver.define(
  'getHistory',
  async () => {

    const response = await fetch(
      "https://raw.githubusercontent.com/yespejo/quality-ai-dashboard/main/data/history.json"
    );

    return await response.json();

  }
);


export const handler = resolver.getDefinitions();