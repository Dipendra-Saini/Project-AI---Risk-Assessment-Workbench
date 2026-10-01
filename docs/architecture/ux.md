# UX decisions

| Decision | Reason |
|---|---|
| One case page with a **gate checklist** at the top (G0, G1, G1b, G2, G3 ticks) | The analyst always knows what blocks progress |
| Every AI value carries an **"AI" badge**, confidence and a clickable source (span or chunk id) | Avoid automation bias; make provenance one click away |
| Override is an inline action that **forces a reason** | Brief: a human can disagree and record why |
| Tier shown as text + colour (never colour only) | Accessibility |
| Committee view shows **no AI outcome**, only scores, trace, narrative, overrides | ADR-006 |
| Persona switcher on the login page | Demo all three personas in one browser |

## Wireframe: analyst case page
```
+--------------------------------------------------------------------+
| CR-2026-0007  Cross-border instant payouts      [ANALYST_REVIEW]   |
| Gates: [x] G0 intake  [ ] G1 factors (2 AI)  [ ] G2 narrative  ... |
+------------------+-------------------------------------------------+
| Tabs: Factors | Controls | Narrative | Intake | Overrides | Audit   |
+--------------------------------------------------------------------+
| Dim  L  I  Inherent  Mitigation  Residual  Origin     Actions      |
| GEO  5  5    25        42%        14.5     rule GEO-02 [Override]   |
| TPV  3  4    12        20%         9.6     AI  [Accept][Override]   |
| Overall inherent 19.2 (High) -> residual 11.0 (Medium)  [trace v]  |
+--------------------------------------------------------------------+
| [Request info]  [Rerun]  [Submit to committee] (disabled + reason) |
+--------------------------------------------------------------------+
```
