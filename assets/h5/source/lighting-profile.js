// Presentation illumination, shared by both viewing modes. Not measured lux values.
export const LIGHTING_PROFILE={
 day:{hemisphere:.62,ambient:.16,exposure:.94,mainGain:1,sunScale:.58},
 night:{hemisphere:.12,ambient:.12,exposure:1,mainGain:1.65,sun:.03},
 maxGroupIntensity:9.5,ceilingLift:.14,
};
export const lightingProfile=night=>LIGHTING_PROFILE[night?'night':'day'];
