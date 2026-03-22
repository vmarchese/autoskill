---
name: event-extractor
description: Extracts structured event data from natural language text. Use when the user provides an event description and needs it parsed into structured fields like title, date, time, location, and organizer.
---

# Event Data Extractor

Extract event information from the provided text and return it as JSON.

## Output format

Return ONLY a JSON code block with these fields:

```json
{
  "title": "event name",
  "date": "date or null if not mentioned",
  "time": "time or null",
  "location": "location or null",
  "organizer": "organizer or null"
}
```

## Rules

- Use null for any field not mentioned in the text
- If a date was rescheduled/moved, use the NEW date only
- The organizer includes: the host, speaker, instructor, or email sender/signer
- For recurring events, keep the recurrence pattern (e.g. "Every Tuesday in October")
- If there are multiple events (e.g. a keynote followed by a reception), include a "notes" field describing additional events
