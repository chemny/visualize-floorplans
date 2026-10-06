// Geometry, room labels, openings and all case decisions are injected by build_h5.py.
export const CASE=JSON.parse(document.getElementById('caseData').textContent);
export const DEFAULT={...CASE.model,walls:CASE.initialState.walls,furniture:CASE.initialState.furniture,areaEstimate:{gross:null,suite:null,note:'按毫米标注概算，未作产权折算',...CASE.areaMetadata}};
export const FOOTPRINT=CASE.model.footprint;
export const CHAINS=CASE.dimensionChains||{top:[DEFAULT.width],bottom:[DEFAULT.width],left:[DEFAULT.depth],right:[DEFAULT.depth]};

export const CHAIN_STARTS=CASE.dimensionChainStarts||{};
