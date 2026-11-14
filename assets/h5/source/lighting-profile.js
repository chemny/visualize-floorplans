// Presentation illumination, shared by both viewing modes. Not measured lux values.
export const LIGHTING_PROFILE={
 day:{hemisphere:.62,ambient:.16,exposure:.94,mainGain:1,sunScale:.58},
 night:{hemisphere:.18,ambient:.16,exposure:1.1,mainGain:1.65,sun:.03},
 maxGroupIntensity:9.5,ceilingLift:.14,
 // Each room light only reaches its own room (farthest corner x reach), and its strength follows the room size so
 // a 2 m² corridor is not lit like a 16 m² living room. Strength = base x (area/10 m²)^exponent, clamped; the
 // exponent stays below 1 so small rooms are not left dim.
 roomLight:{reach:1.1,minRange:3,base:3.64,exponent:.45,minScale:1.82,maxScale:7},
};
export const lightingProfile=night=>LIGHTING_PROFILE[night?'night':'day'];
export function roomLightScale(areaM2){const p=LIGHTING_PROFILE.roomLight;return Math.min(p.maxScale,Math.max(p.minScale,p.base*Math.pow(Math.max(areaM2,0)/10,p.exponent)));}
export function roomLightRange(reachM,heightM){const p=LIGHTING_PROFILE.roomLight;return Math.max(p.minRange,Math.hypot(reachM,heightM)*p.reach);}
