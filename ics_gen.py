from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from parser import create_events
import json

import os
from datetime import datetime
from dateutil import tz

def build_rrule(recurrence: dict, tzname: str) -> str | None:
    """
    Convert structured recurrence JSON into an RRULE string.
    """
    if not recurrence or recurrence.get("type") == "ONE_OFF":
        return None

    # freq = recurrence.get("type", "WEEKLY")  # all your examples are weekly
    freq = "WEEKLY"
    interval = recurrence.get("interval", 1)
    days = recurrence.get("days", [])
    until = recurrence.get("until")

    rrule_parts = [f"FREQ={freq}"]

    if days:
        rrule_parts.append(f"BYDAY={','.join(days)}")

    if interval > 1:
        rrule_parts.append(f"INTERVAL={interval}")

    if until:
        local_tz = tz.gettz(tzname)
        until_dt = datetime.fromisoformat(until).replace(hour=23, minute=59, tzinfo=local_tz)
        rrule_parts.append("UNTIL=" + until_dt.astimezone(tz.UTC).strftime("%Y%m%dT%H%M%SZ"))

    return ";".join(rrule_parts)

def json_to_events(events: str):
    """
    Convert the parsed JSON (from LLM) into a list of ics.Event objects.
    """
    try:
        events_data = json.loads(events)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}")
    
    event_lst = events_data["events"]
    tzname = events_data.get("timezone", "America/Toronto")  # Default timezone
    tzinfo = tz.gettz(tzname)
    
    lst = []

    for e in event_lst:
        # Convert begin and end to timezone-aware datetime objects
        begin = datetime.fromisoformat(e["begin"]).replace(tzinfo=tzinfo)
        end = datetime.fromisoformat(e["end"]).replace(tzinfo=tzinfo)
        recurrence = e.get("recurrence", "")

        event = Event(
            name=e.get("name", "Untitled Event"),
            begin=begin,
            end=end,
            uid=e.get("uid"),
            description=e.get("description"),
            location=e.get("location"),
            status=e.get("status"),
        )

        rrule = build_rrule(recurrence, tzname) if recurrence else None
        if rrule:
            event.extra.append(ContentLine(name="RRULE", value=rrule))

        # EXDATEs (also as ContentLine with value=)
        for ex in e.get("exceptions", {}).get("exdates", []):
            # If only a date is given, use the event's start time
            if "T" not in ex:
                ex = ex + "T" + begin.strftime("%H:%M")
            exdt = datetime.fromisoformat(ex).replace(tzinfo=tzinfo).astimezone(tz.UTC)
            event.extra.append(ContentLine(name="EXDATE", value=exdt.strftime("%Y%m%dT%H%M%SZ")))

        lst.append(event)

    return lst


def add_events_to_calendar(events: list[Event]):
    """
    Given a list of events, add each event to a calendar. Return a 
    calendar object with all the events added.
    """
    cal = Calendar()

    for event in events:
        cal.events.add(event)
        
    return cal

def create_ics_file(calendar: Calendar, filename: str):
    """
    Given a calendar object, write all it's events to an ics file
    and save it to the current directory as calendar.ics
    """
    os.makedirs("calendars", exist_ok=True)

    with open(f'calendars/{filename}.ics', 'w') as f:
        f.writelines(calendar.serialize_iter())


