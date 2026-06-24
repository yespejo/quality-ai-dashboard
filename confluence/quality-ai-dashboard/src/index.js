import Resolver from '@forge/resolver';


const resolver = new Resolver();


// Fetches the full historical time-series so the frontend can draw
// trend curves (health, coverage, snyk) for each pod.
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