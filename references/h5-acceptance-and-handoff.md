# H5 quality, acceptance, and handoff

Use this reference when closing an approved editable H5 scheme, interior image
set, or deterministic walkthrough. It supplements `h5-production-workflow.md`.
It does not authorize new images, external generation, or publication.

Use `h5-quality-gates.md` and the executable `h5.py quality` records for source,
image and tour stages. Four facts remain separate: technical, geometry, visual
and explicit human acceptance. `handoff/package --accepted` enforce these gates;
an ordinary preview manifest cannot grant acceptance with a boolean.

## Shared scheme and drawing modes

- Keep one scheme authority for structure, openings, objects, materials, and
  installation heights. Derive drawings and 3D from it; do not independently
  redraw the apartment for a render.
- Give every drawing an explicit visibility contract. A structure drawing can
  show openings without interior door leaves when agreed; a furniture drawing
  shows furniture and operation; a hard-finish drawing shows ceiling, lighting,
  and agreed equipment points. Do not stack hidden furniture labels or selection
  overlays into another drawing. Preserve the actual opening geometry.
- A hidden presentation detail stays in scheme data unless removal was agreed.
  Decide whether to show a component by its value to the current presentation,
  not by whether it existed in a previous example.
- Distinguish purchased building area, reconstructed suite outline including
  walls, and net room-floor sum. Store each definition, unit, calculation basis,
  and source. Never force agreement by scaling a plan from a guessed area ratio.

## Object and lighting checks

- Store footprint, body height, mounting elevation, and finished ceiling height
  separately. Attach dimension ranges to product type as design defaults, not
  universal product maxima. Preserve the confirmed usage: a vanity is not an
  office desk, and a wall-fixed cabinet is not a freestanding four-leg table.
- Check modeled envelope against declared dimensions, ceiling clearance, door
  movement, and available room space. Wall-to-wall custom furniture uses actual
  wall contacts and its agreed support construction.
- Inspect lights from below using the actual lens and housing meshes. Enabled
  lights, emissive lens material, and a visible emitting face are separate facts.
  Avoid opaque housings, ceiling backboards, or coplanar faces hiding the lens;
  preserve the recessed trim rather than exposing a fixture on top of a ceiling.
- Check ceiling material role and texture independently from floor finishes.
  A white ceiling can appear brown under warm environment lighting. Diagnose
  material assignment, normals/occlusion, environment colors, and fixture output
  before globally raising exposure or making the ceiling emissive.
- Compare same-camera before/after frames in several rooms. Record color
  management, environment light, fixture temperature/intensity, and lens emission
  separately from the scheme hash. A lighting-only update does not silently
  confirm regenerated images or unrelated geometry.

## Homeowner walkthrough

- Start with the viewing purpose, then assign each chapter a subject, functional
  point, observation angle, route connection, and approximate time. Prefer major
  furniture, custom storage, circulation, and room function for a renovation
  presentation. Avoid repeatedly introducing the same furniture or turning
  toward blank walls without a subject.
- Use shallow entry where it gives a complete useful view. Keep necessary
  dead-end returns but use offset walking lines where clearances allow. Passage
  must use the opening's actual clear side and leaf pose.
- Choose duration from distance, comfortable walking pace, turns, and subject
  readability. Do not pad a target duration or accelerate the route just to fit.
  Record actual mean/max/min speeds and angular motion. Eye height, field of
  view, projection shift, and any head motion are explicit case parameters.
- Smooth position and gaze offline, then check the smoothed route and its
  inter-frame segments against actual walls, door leaves, and furniture. Graph
  connectivity alone does not prove clear passage. Report the sampled body
  envelope and limitations, not a full human-clearance certification.
- A continuous walkthrough has no cuts, teleports, or hidden disconnected
  transitions. UI chapter jumps are viewer navigation, not edits in the video.
  Verify important subjects are visible, not merely that the route covers rooms.

## Freeze and deliver

1. Separate technical checks, internal visual review, and explicit human
   acceptance. Bind acceptance to the exact displayed artifact, quote the user
   evidence, and record confirmer, scope, content hashes, and recording time.
   A generic authorization to generate is not acceptance of unseen results.
2. Preserve source snapshots and previous statuses. Mark the current accepted
   version clearly in the main index; keep rejected/older assets outside the
   accepted package. Do not overwrite old review history to make it appear current.
3. Deliver a relocatable index, standalone workbench, editable scheme JSON,
   current drawings, accepted image subset, requested video and script, and
   compact review/acceptance records. Include the actual exported mesh bundle
   when needed for downstream reproduction; lossless compression is acceptable
   when decompression restores its recorded bytes.
4. Export plan and pre-render furniture layout as SVG plus same-revision PNG.
   Export hard-finish drawings and other presentation images as PNG/JPG only.
   Preserve accepted generated image bytes and native aspect ratio; no cropping
   or redraw merely for handoff.
5. Compare the delivered scheme to the approved video source, exercise JSON
   import, and test local-file browsing, drawing switches, 2D/3D, image links,
   video playback, narrow layout, and absence of external dependencies for an
   offline package. Hash copied assets and validate the archive contents.
6. Record representation differences honestly. An older accepted AI image can
   retain its own source scheme and lighting profile; do not rebind it to a new
   scheme hash or claim it was regenerated. List the changed scopes and current
   authoritative representation. Ask only if a substantive visual discrepancy
   requires a new design decision.
7. Keep palettes, product dimensions, apartment geometry, route waypoints,
   durations, filenames, and approval evidence in the case. Shared Skill rules
   describe contracts and checks, not a user's particular apartment.

## Completion boundary

A successful H5 replay records that case's technical preview result, not the
capability of every host or a photorealistic generative video chain. Seedance
remains a separate branch requiring current provider capability, inputs,
execution authorization, and result review. Do not start paid generation,
construction detailing, procurement, or publication as handoff cleanup.
