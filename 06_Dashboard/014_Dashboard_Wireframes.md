# Dashboard wireframes

Static desktop layouts for review. Page headers and selected scopes stay visible. Bracketed items are interactive controls. Figures in the first frame come from the verified full workbook.

## Executive Overview

```text
▌ Last-mile dispatch intelligence                         Workbook v1
  Executive Overview   Route Performance   Distance & Quality
  Timing cohort [Full workbook ▾]                    [Definitions]

 ┌────────────────┬────────────────┬─────────────────┬────────────────┐
 │ LATE DELIVERIES│ ROUTES WITH    │ LATENESS        │ CHANGED ADDRESS│
 │ 11.13%         │ LATE ARRIVAL   │ 47.94 min median│ ORDER          │
 │ 23,718/213,122  │ 43.27%         │ P90 206.09 min  │ 73.18%         │
 │ eligible        │ 8,387/19,383   │ n = 23,718      │ 14,378/19,647  │
 └────────────────┴────────────────┴─────────────────┴────────────────┘
 ┌──────────────────────────────┬───────────────────────────────────────┐
 │ Arrival-window outcomes      │ Late routes by address order          │
 │ Early | In window | Late     │ Crude         Changed / Unchanged     │
 │ 100% stacked bar             │ Standardized  Changed / Unchanged     │
 │ Counts + eligible total      │ Paired dots · 6 of 8 strata supported │
 └──────────────────────────────┴───────────────────────────────────────┘
  Timing sensitivity · Removed routes / eligible visits / late visits
```

## Route Performance & Exceptions

```text
▌ Route Performance & Exceptions                   Timing [Full ▾]
  Compare by [Country ▾] [Route size ▾]

 ┌──────────────────────────────┬───────────────────────────────────────┐
 │ Changed vs unchanged         │ Displacement · All countries/sizes    │
 │ Late routes / eligible routes│ [Address order ▾] [Visit order ▾]     │
 │ Paired bars by size/country  │ Dot plot · late / eligible deliveries │
 │ Show both group counts       │ Position bands 0 · 1 · 2–3 · 4–6 · 7+│
 └──────────────────────────────┴───────────────────────────────────────┘

 ┌─ Route exceptions ─────────────────────────┬─ Selected route ────────┐
 │ [Route ID] [Address order ▾] [Flags ▾]      │ Planned/actual position │
 │ Route · country · size · address match     │ Stop/address · depot     │
 │ Moved visits · late/eligible · timing flags│ Window · arrival · flags │
 │ [Select route]                 [Next page]  │ Relative minutes         │
 └────────────────────────────────────────────┴─────────────────────────┘
```

## Distance Deviations & Data Quality

```text
▌ Distance Deviations & Data Quality                Timing [Full ▾]
  [Country ▾] [Route size ▾] [Address order ▾]

 ┌─────────────────────────────┬────────────────────────────────────────┐
 │ Recorded Haversine changes  │ Arrival outcomes by distance category  │
 │ Shorter | Equal | Longer    │ Late routes      Late deliveries       │
 │ Count bars + route counts   │ Separate aligned bars with samples     │
 └─────────────────────────────┴────────────────────────────────────────┘
 ┌─────────────────────────────┬────────────────────────────────────────┐
 │ Paired difference (km)      │ Timing and distance review             │
 │ P05 ─── Median ─── P95      │ [Distance category ▾] [Review flags ▾] │
 │          │ 0 reference       │ Route · planned · actual · signed km  │
 │ Selected cohort + route n   │ Abs km · % · leg flags · timing flags │
 └─────────────────────────────┴────────────────────────────────────────┘
  Geodesic leg sums · Relative minutes · Observational comparisons
```

Use deep slate for the title and card labels, muted slate blue for measures and comparison groups, and burnt orange for late outcomes or flagged records. Pair color with text and shapes. Make comparison scope and units visible rather than relying on hover.
