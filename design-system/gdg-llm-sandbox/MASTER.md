# GDG LLM Sandbox Design System

## Direction

The interface is a professional adversarial AI lab, not a game dashboard. It should feel like a quiet control room documented by an editorial photographer: exact, tactile, serious, and human.

Design dials:

- Design variance: 8/10
- Motion intensity: 5/10
- Visual density: 5/10

## Principles

1. Lead with a real environment and a clear mission.
2. Use one oxide-orange signal accent. Reserve semantic colors for state and failure.
3. Prefer strong composition, image crops, rules, and negative space over floating cards.
4. Keep technical metadata compact and monospaced. Keep human instructions plain and readable.
5. Preserve the same hierarchy and interaction vocabulary in both themes.

## Color

| Role | Dark | Light |
| --- | --- | --- |
| Canvas | `#101112` | `#e9e7e2` |
| Surface | `#17191a` | `#f6f4f0` |
| Raised surface | `#202223` | `#fffdf9` |
| Primary text | `#f3f0ea` | `#171716` |
| Muted text | `#98958f` | `#69665f` |
| Border | `#3a3b39` | `#c7c3ba` |
| Signal accent | `#e36b45` | `#a83f24` |
| Accent action | `#f47a50` | `#c65030` |
| Success | `#acd8a3` | `#316538` |
| Danger | `#ff806e` | `#9b2e23` |

Do not introduce blue-purple gradients, neon green, or secondary decorative accents.

## Typography

- Display: Aptos Display, Avenir Next, Segoe UI Variable Display, sans-serif.
- Body: Aptos, Avenir Next, Segoe UI Variable Text, sans-serif.
- Technical: Cascadia Mono, SFMono-Regular, Consolas, monospace.
- Headlines use tight tracking and compact line height.
- Eyebrows and metadata use uppercase mono at 9px to 11px with generous tracking.
- Body copy stays between 12px and 16px depending on hierarchy.

## Geometry

- Global radius: 3px.
- Borders are 1px and structural.
- Shadows are limited to modal depth. Avoid decorative card shadows.
- Controls are at least 44px tall.
- Responsive page gutters: 36px desktop, 20px tablet, 12px mobile.

## Composition

### Admission

- Desktop: asymmetric image-led briefing with a narrower admission panel.
- Mobile: hero first, admission second.
- Hero contains one eyebrow, one two-line maximum headline, and one short sentence.
- The form includes round status, access code, model route, primary action, and a compact scope note.

### Workspace

- Header facts appear as one structured strip, not three floating cards.
- Mission context combines an infrastructure photograph with the objective and session controls.
- Prompt and response panes share one bordered console.
- Success appears as a full-width console state.

## Imagery

Use photorealistic editorial images with credible materials, practical lighting, and restrained grading.

- Hero: human security researcher in a real server laboratory, subject in the right third, dark negative space for copy.
- Workspace: macro infrastructure detail with braided fiber, matte graphite hardware, and restrained oxide-orange indicators.
- Avoid fake UI, holograms, cyberpunk neon, Matrix code, hoodies, stock smiles, logos, and readable screen text.
- Hero loads eagerly with explicit dimensions. Supporting photography loads lazily.
- Every meaningful image needs descriptive alternative text.

## Motion

- Use opacity and transform only for page and response entry reveals.
- Hover image scale stays below 1.02.
- No scroll-driven animation.
- Honor `prefers-reduced-motion` by reducing transitions and animations to effectively zero.

## States and Accessibility

- Every async surface has loading, empty, success, and error states.
- Maintain visible keyboard focus with a 2px signal-color outline.
- Keep form labels explicit, status changes live, and icon-only controls named.
- Never rely on color alone for state communication.
- Do not store session tokens or provider credentials in browser storage.

## Copy Rules

- Sound direct, precise, and calm.
- No em dashes or en dashes in visible interface copy.
- Avoid hype, gamer slang, and vague claims.
- Buttons use clear verbs: Start challenge, Run attempt, Retry same attempt, End session.
