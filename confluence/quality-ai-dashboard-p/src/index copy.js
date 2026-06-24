import Resolver from '@forge/resolver';


const resolver = new Resolver();


resolver.define(
  'getMetrics',
  async () => {


    const response =
      await fetch(
       "https://raw.githubusercontent.com/yespejo/quality-ai-dashboard/main/data/latest.json"
      );


    return await response.json();

  }
);


export const handler =
 resolver.getDefinitions();