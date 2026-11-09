# Design System and Mobile UI Specification

**Owner:** Disha Gudup (design system and frontend foundation)  
**Feature-screen implementation:** Vidula Gote  
**Product direction:** Mobile-first responsive application; farmer-first, agronomist-capable.

## 1. Design principles

1. **Mobile first:** A farmer may only have a smartphone. Design for narrow screens and touch use first; desktop is an expanded layout, not the primary reference.
2. **Action before analytics:** The default screen answers what is happening and what needs attention. Technical charts are secondary.
3. **Progressive disclosure:** Farmer-friendly summary first; evidence and technical analysis on tap.
4. **Trust through provenance:** Show source, observation date and whether a value is measured, estimated, derived or simulated.
5. **Multilingual from the start:** English and Marathi are first-release priorities; Hindi uses the same i18n architecture.
6. **Field-friendly:** Large touch targets, legible text, simple labels, clear contrast and graceful offline/stale states.
7. **Consistent meaning:** Status colours and component behaviour are identical across all screens.

## 2. Colour tokens

### Brand palette

| Token | Hex | Use |
|---|---|---|
| `color.brand.forest` | `#2E5A36` | Brand, primary buttons, active navigation |
| `color.accent.harvest` | `#D97706` | Attention, warnings, secondary emphasis |
| `color.neutral.sage` | `#818E72` | Secondary surfaces, muted icons |
| `color.neutral.sand` | `#E6DFD3` | Warm card surfaces and separators |
| `color.background.warm` | `#F9F8F6` | Main application background |
| `color.text.primary` | `#1E2B22` | Main text |
| `color.surface.white` | `#FFFFFF` | Cards and sheets |

### Status palette

| Token | Hex | Meaning |
|---|---|---|
| `status.healthy` | `#2E7D4F` | Healthy/acceptable |
| `status.attention` | `#D97706` | Monitor/review |
| `status.critical` | `#B5473E` | High stress/urgent assessment |
| `status.info` | `#3576A8` | Information/weather/system state |
| `status.unavailable` | `#667085` | Missing, unknown or unavailable |

Do not use colour as the only status indicator. Always include text and, where helpful, an icon. Check actual text/background combinations against WCAG 2.2 AA contrast before release. Amber and sage often need dark text; do not put small white text on light sage or sand.

## 3. Typography

- English: Inter.
- Marathi/Hindi: Noto Sans Devanagari.
- Use system fallbacks if web fonts fail to load.
- Use responsive type scale rather than fixed desktop typography.
- Avoid condensed decorative typefaces for data or instructions.
- Ensure Devanagari matras and line height remain readable; test actual Marathi/Hindi strings, not only Latin placeholders.

Suggested scale:

| Token | Size | Use |
|---|---:|---|
| `text.xs` | 12 px | Metadata, timestamps (not critical instructions) |
| `text.sm` | 14 px | Supporting text |
| `text.base` | 16 px | Body and controls |
| `text.lg` | 18 px | Section titles |
| `text.xl` | 20 px | Screen subheadings |
| `text.2xl` | 24 px | Main screen title |
| `text.3xl` | 30 px | Key status/hero value |

## 4. Layout and component rules

- Mobile screen horizontal padding: 16–20 px.
- Common spacing scale: 4, 8, 12, 16, 20, 24, 32 px.
- Cards: 14–18 px radius; use subtle border or shadow, not both heavily.
- Primary buttons: minimum 48 px height; full width for critical mobile actions.
- Inputs: visible labels, clear validation and large touch targets.
- Bottom navigation: five destinations — Home, Farm, Irrigation, Insights, More.
- Notification icon in app header.
- Contextual `+` action may open Add Farm, Record Irrigation, Add Observation or Report Crop Issue; do not use it as an unexplained decorative button.
- Use Lucide-style outline icons consistently.
- Maps must provide a legend, selectable zones, accessible zone list alternative and data timestamp.

## 5. Primary navigation and screen inventory

| Screen | Purpose | Primary owner |
|---|---|---|
| 01 Splash / language | Brand and language selection | Disha |
| 02 Farm setup | Farm details and crop context | Disha |
| 03 Dashboard | Overall status, map preview, priorities | Disha |
| 04 Farm digital twin | Full map and layers | Vidula |
| 05 Zone intelligence | Zone evidence and analysis | Vidula |
| 06 Irrigation planner | Zone-level plan and schedule | Vidula |
| 07 Recommendation details | Amount/range, assumptions and action | Vidula |
| 08 Farm insights | Trends and comparisons | Vidula |
| 09 Alerts | Alerts and notifications | Vidula |
| 10 History | Analysis and action history | Vidula |
| 11 Profile/settings | Profile, farm switching and preferences | Vidula |
| 12 Language/preferences | English, Marathi, Hindi and units | Vidula; framework by Disha |

Screens 09–12 may be reached through the notification/profile/menu areas; not every function requires a permanent bottom-navigation item.

## 6. Screen 03 — Farm Dashboard specification

### Goal

Within approximately ten seconds, a farmer should understand the selected farm's latest known condition, know whether any zones require attention and find the next action.

### Mobile content order

1. **App header:** FarmShield mark/name, active language, notification icon.
2. **Greeting/title:** Short farmer-friendly heading; do not rely on time-of-day greeting if local time is unavailable.
3. **Farm selector card:** Farm name, location, area, crop and season; tap to switch farm.
4. **Overall condition card:** Status text, short explanation, count of zones needing review and data-freshness hint.
5. **Summary metrics:** Number of zones and number needing review. Avoid unsupported percentage metrics.
6. **Farm health map preview:** Zone polygons with labels, legend, map freshness and `View full map` action.
7. **Today's priorities:** Ordered list of zones and safe next actions.
8. **Weather summary:** Current/forecast summary with provider and update time.
9. **Bottom navigation:** Home, Farm, Irrigation, Insights, More.

### Desktop adaptation

- Left navigation rail/sidebar.
- Header with farm selector, language and notifications.
- Summary cards across the top.
- Map in the main area, priority list beside it.
- Weather and recent observations below.
- Advanced evidence can appear in a side panel.

Desktop must use the same data contracts and status meanings.

## 7. Screen interactions

| Element | Tap/click result |
|---|---|
| Farm selector | Open farm list and switch active farm |
| Overall status | Open farm health summary and evidence |
| Zone map preview | Open full digital twin |
| Zone polygon/list item | Open zone intelligence detail |
| Priority action | Open linked recommendation/zone |
| Weather card | Open forecast and weather history |
| Notification icon | Open alert list |
| Advanced Analysis | Reveal indices, calculations, inputs and uncertainty |
| Record action | Open irrigation/action form and save event |

### Zone detail progressive disclosure

- **Default:** Status, crop, concise explanation, next action.
- **Evidence:** NDVI/vegetation trend, rainfall, soil evidence, dates and source.
- **Advanced analysis:** ET₀, Kc, ETc, root-zone assumptions, water balance, irrigation efficiency and model/quality notes.

## 8. Data display rules

Every data card should support:

- Human-readable value and unit.
- Observation/forecast/calculation timestamp.
- Source label.
- Provenance type: measured, farmer-entered, satellite-derived, modelled, derived or simulated.
- Quality/freshness state.
- Empty/unavailable state.

Do not display a value as `0` when it is missing. Use `—`, `Not available` or `Insufficient data`.

## 9. Required screen states

Every data-driven screen must design:

1. Initial loading/skeleton.
2. Loaded state.
3. Empty state (no farm/no zone/no observation).
4. Partial data state.
5. Stale data state.
6. Offline/cached state.
7. Provider/API error state with retry.
8. Permission/location denied state where applicable.

## 10. Localization

- Use i18next with translation keys.
- Suggested namespaces: `common`, `onboarding`, `dashboard`, `farm`, `zones`, `irrigation`, `insights`, `alerts`, `history`, `settings`.
- Never concatenate translated sentence fragments.
- Keep stable machine values in English in API payloads; translate labels in the UI.
- Format dates/numbers/units according to locale, but retain canonical stored units.
- Test long Marathi/Hindi labels and avoid clipping.
- Language switch should apply immediately and persist in the user/device preference.

## 11. Accessibility and usability

- Target WCAG 2.2 AA contrast.
- Minimum touch target: 44×44 CSS px; prefer 48 px for primary controls.
- Do not rely only on colour; label map zones and provide a list alternative.
- Support browser/system text scaling.
- Use clear focus indicators and semantic controls.
- Charts need a text summary/table alternative.
- Avoid tiny timestamps and low-contrast secondary text for essential information.

## 12. Out of scope for the dashboard

Do not add market prices, tractor/equipment management, social feeds or unrelated farm accounting to the MVP dashboard. Keep the dashboard focused on health, zones, irrigation decision support, weather and evidence.
