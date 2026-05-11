# Proposal: Car-Interior CPL Look Trial

## Summary

Add a batch pipeline option that approximates a CPL/anti-glare look for car interior photos. The feature targets the common carsmeet/8891 pain point where automotive interior shots have noise plus glossy reflections on black trim, instrument glass, center screens, and windows.

## Motivation

Photoshop/Camera Raw Reflection Removal can separate some plate-glass reflections, but frame-processor needs a practical server-side trial that can be applied in existing batch versions. For car interiors, a full reflection-separation model is not required for the first version; reducing bright low-saturation glare while preserving dark trim and screen UI is a useful testable step.

## Scope

- Add `cpl_strength` to processing jobs and AI version settings.
- Add a `cpl_look` pipeline step after crop/detail restoration and before color grading.
- Expose `none` / `low` / `medium` / `high` in Preview processing settings.
- Preserve immutable AI version behavior so each CPL setting creates or matches the correct version.
- Document that this is anti-glare/CPL look, not true reflection removal or detail recovery from clipped highlights.

## Non-Goals

- No Adobe Reflection Removal equivalent glass-scene separation.
- No generative fill or hallucinated reconstruction.
- No per-region manual brush controls in this trial.
