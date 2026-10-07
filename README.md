# Floor Visualization

English | [中文](./README.zh.md)

## Overview

An Agent Skill for homeowners and renovation design teams. Start with one floor-plan image, review the reconstructed plan, develop a furniture layout, choose a renovation style visually, and receive an editable 2D/3D workbench and coordinated interior concept images.

Furniture layouts and style references are optional. The Agent reads visible dimensions and asks about consequential uncertainties; missing dimensions are not presented as measured facts. The same scheme supplies the plan, furniture drawings and 3D preview.

## Preview

![Capability illustration: a floor plan, editable 2D/3D workbench and interior concepts](assets/visualize-floorplans-hero-en.png)

Illustration of the workflow; AI interior concepts and the editable 3D preview are separate outputs.

[Explore the bundled Champagne Pearl case](assets/reference-cases/jujian-champagne-pearl/index.html): supplied references, 13 concept images, an editable workbench, drawings and a 56-second tour. Ask the Agent to open the installed local case; GitHub does not execute HTML file pages. Its retained images and tour differ from the current example workbench in lighting and materials; see the [case notes](assets/reference-cases/jujian-champagne-pearl/README.md).

## Features

| Capability | What it helps you do |
| --- | --- |
| Start from one plan | Review rooms, dimensions, walls, windows and access before designing. |
| Furniture planning | Propose wall-backed furniture, usable passages, door clearance and curtain space for your household. |
| Visual style selection | Compare six interior style directions in one image before choosing; requires an available image-generation tool. |
| Editable 2D/3D workbench | Edit furniture, doors, eligible walls and finishes, then inspect the same scheme from above or in a walkthrough. |
| Precise editing | Copy objects, insert components from a context menu, snap alignment, measure and undo/redo. |
| Save and confirm | Save directly to a local project service and confirm a stage; portable HTML supports independent saving and export. |
| Coordinated interior concepts | Generate room and whole-home views using the confirmed layout and style, then review differences. |
| Local delivery | Package the workbench, drawings, scheme data and approved images with an index and file checksums. |
| Optional camera preflight | Plan and capture a continuous H5 tour when requested; video generation is a separate optional branch. |

This is concept design, not measured CAD, structural assessment or construction documentation. Unknown wall types require verification before demolition proposals. Video and Blender are optional; renovation pricing is excluded.

## Installation

### Requirements

The Agent prepares the core environment first; image and video integrations can wait until you need them.

| Item | Requirement |
| --- | --- |
| Agent client | Tested with Codex; designed for Claude Code and OpenClaw, which have not been tested. |
| Core runtime | Python 3.11 or newer; a modern browser for the workbench. |
| Operating system | Tested on macOS. Windows path and invocation compatibility is reviewed, but Windows execution has not been tested. |
| Interior images | An available, authorized image-generation/editing tool that accepts reference images. |
| Browser capture / video | Optional Node.js, browser automation and Chromium; FFmpeg for encoding. |

### Quick Installation

Send this request to your Agent:

```text
Install this Skill: https://github.com/chemny/visualize-floorplans
Check the core environment and prepare anything missing, then install and verify discovery and readiness. Set up optional features when I need them.
```

The Agent should report what is installed and ready, plus any missing tool or permission. See [runtime guidance](references/platform-runtime.md) for detailed requirements.

## Quick Start

Attach a floor-plan image and send:

```text
Help me design this home. I have no furniture layout or style reference.
Check the plan, suggest a practical layout and show style options, then make an editable 2D/3D workbench and interior concepts after confirmation. No video yet.
```

## Usage Examples

### Adjust a furniture layout

```text
Three people will live here. Make the study a guest room too, keep the main passages clear, and show the proposed layout in the workbench.
```

### Choose finishes visually

```text
Show six styles for the confirmed living/dining layout in one comparison image, using the same eye-level view. Recommend one and explain why.
```

Image generation requires the optional tool listed above; workbench palettes alone do not replace interior effect images.

### Continue from workbench edits

```text
I have saved my edits in the local workbench. Read that saved scheme and continue with the confirmed layout.
```

Direct readback uses the local project service. A standalone HTML stores browser edits separately; transfer its saved HTML or scheme when changing environments.

### Make a tour when needed

```text
Create a continuous homeowner tour from this confirmed scheme. Show the main rooms clearly and keep turns smooth.
```

H5 capture requires the optional browser tools; generative final video needs a separately available provider and its own review.

## How It Works

Three concentrated decision rounds: **plan and essential needs → furniture layout → visual style and output scope**. The Agent completes checks and refinements within each round, batches consequential questions with recommendations, and presents final outputs for acceptance.

| Component | Responsibility |
| --- | --- |
| Skill workflow and references | Interpret the source, guide decisions, apply furniture rules and track acceptance. |
| Bundled H5 engine | Keep editable 2D drawings and 3D geometry, materials and furniture in one scheme. |
| Python planning and validation tools | Build workbenches, check layout constraints and prepare delivery. |
| Local project service | Receive saved edits, detect conflicting versions and record stage confirmations. |
| Optional image/video tools | Produce concepts or requested videos from the confirmed scheme; no account or credential is bundled. |
| Bundled reference case | Show concrete outputs without imposing its apartment or choices on new projects. |

You can request individual tasks. Changes to geometry, furniture or finishes invalidate only the dependent confirmations; successful file checks do not grant human approval. See [guided workflow](references/guided-user-workflow.md), [quality gates](references/h5-quality-gates.md) and [save/confirm behavior](references/project-save-confirm.md).

## Repository Structure

```text
SKILL.md                 Agent instructions
assets/h5/               Workbench engine, source, runtime and blank templates
scripts/                 Planning, layout checks and project service
scripts/production/      H5 build, export, capture and optional Blender tools
agents/                  Agent entrypoint metadata
references/              Design, interaction, quality and delivery rules
assets/reference-cases/  Curated example materials and outputs
requirements.txt         Python drawing dependencies
THIRD_PARTY_NOTICES.md    Upstream and dependency notices
CHANGELOG.md              Release history
README.md / README.zh.md  English / Chinese introductions
LICENSE                  Original-work license
```

Installation includes the Skill resources and example; it does not configure optional generation services. See [tools and case schema](references/h5-tools-and-case-schema.md), [furniture rules](references/furniture-placement-principles.md) and [acceptance and handoff](references/h5-acceptance-and-handoff.md).

## License

Original code and documentation use [MIT](LICENSE). Adapted floorplan workbench portions retain the upstream [MIT notice](assets/h5/FLOORPLAN-REFERENCE-LICENSE.txt). Three.js and other dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md). These terms do not relicense external services or third-party materials.

## About Me

Maintained by [chemny](https://github.com/chemny). Questions and feedback can be raised in the [repository issues](https://github.com/chemny/visualize-floorplans/issues).
