# Main-fixture style linkage

Supported main bodies: `ceilinground` and `ceilingsquare`. Existing type IDs stay
stable while `lampShape` resolves the rendered body and hard-finish plan symbol.
Pendant, downlight, track, strip, task and wall/table lamps keep their mechanisms.

- `lampStyleMode: follow|fixed`; `lampShape: flat|dome|crystal|crystal_classic`.
- Defaults live in `source/lamp-style.js`, with complete registered style mapping.
  Contemporary French/Paris directions use compact crystal; European luxury uses the
  classic glass-arm/bead-swag model (520mm drop); wood/cream,
  mid-century, Chinese/champagne/Italian use convex opal; modern/legacy greige use flat.
- Classify real room functions/names, not apartment IDs. Kitchen, bathroom,
  balcony, hall, closet and unknown spaces default to practical flat fittings.
- Changing a shape explicitly sets fixed mode. Style changes leave fixed bodies
  alone. Returning to follow applies the current room/style default.
- Keep furniture position, count, footprint, room finishes, openings and lamp
  switch/intensity/temperature. Fixture body depth comes from the chosen model,
  with elevation derived from the same finished ceiling plane. Avoid generic
  height stretching. `lampLightOffset` preserves the prior light-source offset
  below that plane; ceiling changes carry the light with its installation.
- Body downhang below a 2100mm conceptual clearance falls back to flat only for
  automatic defaults. An explicitly fixed unsafe selection fails validation.
  This is an editor safeguard, not product/site/building-code acceptance.
- Plan, mesh, undo/redo, JSON import/export and portable HTML must preserve the
  same fields. Validate invalid enums rather than silently changing them.
- Fixture visibility still follows ceiling/walk rules; actual sources stay
  independent. No extra point lights, shadows, refraction passes or textures.
  Visual opal/crystal materials do not prove transmittance or photometric coverage.

Repeated beads/drops may use instancing; production mesh export must expand each
instance with its composed world matrix. Test instance counts and distinct poses.
The stored body height must match actual modeled bounds, not a loose visual budget.

Verification: `node --test scripts/test_lamp_style.mjs`; geometry tests are bundled
with the existing esbuild/Three dependencies in maintenance. Actual final-page
clicks, saved JSON and same-scope screenshots remain separate from unit checks.
