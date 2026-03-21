---
name: event-extractor
description: Extracts structured event data from natural language text. Use when the user provides an event description and needs it parsed into structured fields like title, date, time, location, and organizer.
---

# Event Extractor

Extract event details from text. Return ONLY a fenced JSON code block. Do NOT write any text before or after the JSON.

## Output Format

```json
{
  "title": "Event Name",
  "date": "the date or null",
  "time": "start time - end time or null",
  "location": "full location or null",
  "organizer": "person or organization or null",
  "notes": "additional events or null"
}
```

## Critical Rules

- **ONLY output a ```json code block.** Nothing else. No explanation. No intro text.
- Use JSON null (no quotes) when info is missing. Never invent data.
- **title**: Capitalize properly. Use the event name from the text.
- **date**: Copy the date exactly from the text. If a date was RESCHEDULED or MOVED, use ONLY the NEW date, ignore the old one. For recurring events, write the pattern like "Every Tuesday in October".
- **time**: Include start AND end time if both are given. Example: "9:00 AM - 5:00 PM". If only one time, write just that time like "6:30 PM".
- **location**: Copy the FULL location. Include room numbers, building names, city, etc. Example: "Community Arts Center, Room 204" not just "Community Arts Center".
- **organizer**: The host, company, instructor, or sender. Check email signatures for the name. An instructor IS the organizer.
- **notes**: If there is a second event mentioned (like a reception or follow-up), describe it here. Otherwise null.

## Example 1: Simple event

Input: "Join us for the Spring Picnic hosted by ABC Inc on May 1, 2025 from 2pm to 5pm at Central Park."

```json
{
  "title": "Spring Picnic",
  "date": "May 1, 2025",
  "time": "2:00 PM - 5:00 PM",
  "location": "Central Park",
  "organizer": "ABC Inc",
  "notes": null
}
```

## Example 2: Missing fields use null

Input: "The charity gala at The Grand Ballroom, Hilton Downtown. Doors open at 6:30 PM."

```json
{
  "title": "Charity Gala",
  "date": null,
  "time": "6:30 PM",
  "location": "The Grand Ballroom, Hilton Downtown",
  "organizer": null,
  "notes": null
}
```

## Example 3: Rescheduled event from email

Input: "Subject: Meeting Moved\n\nThe project review has been moved from Jan 5 to Jan 12, 2025. Time: 3:00 PM. Location: Room 401, Building A.\n\nBest,\nAlex Chen\nProject Manager"

```json
{
  "title": "Project Review",
  "date": "January 12, 2025",
  "time": "3:00 PM",
  "location": "Room 401, Building A",
  "organizer": "Alex Chen",
  "notes": null
}
```

## Example 4: Recurring event with instructor

Input: "Workshop: Beginner Pottery\nWhen: Every Saturday in March, 1pm-3pm\nWhere: Art Studio, Room 12\nInstructor: Tom Bell"

```json
{
  "title": "Beginner Pottery",
  "date": "Every Saturday in March",
  "time": "1:00 PM - 3:00 PM",
  "location": "Art Studio, Room 12",
  "organizer": "Tom Bell",
  "notes": null
}
```

## Example 5: Multiple events

Input: "Dr. Smith presents 'Climate Change Solutions' on Feb 10, 2025 at 4:00 PM in Hall C, Science Building. A Q&A session follows at 5:30 PM."

```json
{
  "title": "Climate Change Solutions",
  "date": "February 10, 2025",
  "time": "4:00 PM",
  "location": "Hall C, Science Building",
  "organizer": "Dr. Smith",
  "notes": "Q&A session follows at 5:30 PM"
}
```
