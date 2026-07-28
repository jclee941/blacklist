# Blacklist Frontend Design System

## 1. Atmosphere & Identity

An operational security console: restrained, information-dense, and explicit about system state. Status colors and clear action labels carry meaning; decoration never competes with operational data.

## 2. Color

The interface uses the existing Tailwind gray ramp for surfaces and text, green for healthy or successful state, red for failed state, blue for information, and amber for caution. New components must reuse these semantic roles rather than introducing raw color values.

## 3. Typography

Use the existing application font stack. Page headings use the shared `PageHeader`; card titles use `text-lg font-semibold`; body text uses `text-sm` or the inherited base size; metadata uses `text-xs`. Operational copy must remain direct and concise.

## 4. Spacing & Layout

Spacing follows Tailwind's 4px base scale. Pages use vertical stacks, cards use 24px padding, form controls use 16px vertical grouping, and action clusters use 8px gaps. Management grids collapse to one column before expanding at the existing `lg` breakpoint.

## 5. Components

### Button

- Variants: primary, secondary, ghost, destructive where already provided.
- States: default, hover, focus, disabled, and loading.
- Accessibility: native button semantics and visible labels; icon-only actions require an accessible name.

### Input

- Structure: visible label, control, optional hint, validation error.
- States: default, focus, disabled, invalid, required.
- Accessibility: every control is associated with a label; errors are rendered adjacent to the control.

### Modal

- Structure: title, form content, cancel action, primary action.
- States: open, closed, saving, invalid.
- Accessibility: keyboard dismissal and focus containment are owned by the shared component.

### Collector Card

- Structure: source identity, configured/connection badge, metrics, status metadata, actions.
- States: unconfigured, configured, connected, failed, disabled, testing, collecting.
- Accessibility: unavailable operations are disabled rather than hidden; state is always expressed in text as well as color.

## 6. Motion & Interaction

Use only the shared component transitions. Motion communicates state changes and must respect reduced-motion preferences. Do not animate layout dimensions.

## 7. Depth & Surface

Use the existing mixed strategy: tonal gray surfaces with restrained borders on cards, inputs, and status messages. Modals may use the shared elevated treatment. Do not add new shadows or materials for feature-level changes.

## 8. Accessibility Constraints & Accepted Debt

Target WCAG 2.2 AA. All controls must be keyboard reachable, form fields labeled, disabled actions discernible, and status meaning available without color perception.

Accepted debt: the existing collection page mixes light card internals with the dark application shell. This task preserves that established surface and introduces no new visual debt.
