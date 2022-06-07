
# Polar Flow

Access to Polar is done via their inofficial Web API. Activities are accessed the same way as the Browser does. This is
so far the only way to get access to activities from the past and download the associated GPX and TCX files.

Polar offers a REST API called AccessLink (see https://www.polar.com/accesslink-api for more information). However,
this API cannot be used for searching activities or getting access to things from the past, only for data from the point
of time of the first access onwards. It simply lacks the necessary functionality to download arbitrary data, most likely
on purpose. Polar does not seem to like have external applications get access to this data.

## Timestamps

This collects some information about times of activities stored in (my own) Polar Flow account. There are some open
issues when it comes to time processing in Polar Flow ...

- for new/current activities synched from Flow to Strava, there's a time difference of 1 second (apart from the wrong UTC/local timestamp)
- in 2012/14/15 there's a gap of 360x/720x seconds, these activities have been imported manually into Strava.

## Example for 2012

- command: gtrac list date:2012-01-31

### Polar

This activity has been imported from Polar Personal Trainer into Flow by their migration tool. The datetime shown below
matches the local time when the activity has begun. This means the time carries the wrong timezone, Z is UTC, but
actually it's CET.

- "timestamp": 1328044537000
- "start": 1328044537
- "end": 1328046832
- "datetime": "2012-01-31T21:15:37.000Z"

The .tcx file also contains CET, with .37 as starting second.

```xml
<Id>2012-01-31T21:15:37.000Z</Id>
<Lap StartTime="2012-01-31T21:15:37.000Z">
</Lap>
```
### Strava

This has been imported into Strava manually (by uploading TCX?). Timezone and offset are correct, but start_date and
start_date_local are not, they carry a winter time offset by 1 hour. The external_id matches the polar start in CET
plus the ID of the activity in Flow (Question: where's that ID coming from?). Question here is how to find out that
the time is wrong.

- "external_id": "2012-01-31T21_15_37.000Z_POLARID.tcx"
- "start_date": "2012-01-31T21:15:38Z"
- "start_date_local": "2012-01-31T22:15:38Z"
- "timezone": "(GMT+01:00) Europe/Berlin"
- "utc_offset": 3600.0

The .tcx file contains the same (wrong) CET time, again with .37 as starting second. However, the first track point
carries .38. Strava seems to derive the start time from the first track point, not from the lap start.

```xml
<Id>2012-01-31T21:15:37.000Z</Id>
<Lap StartTime="2012-01-31T21:15:37.000Z">
...
<Trackpoint>
  <Time>2012-01-31T21:15:38.000Z</Time>
  <SensorState>Absent</SensorState>
</Trackpoint>
</Lap>
```

## Example for 2016

- command: gtrac list time:2016-11-15

### Polar

Again, the datetime is Z, but actually shows CET.

- "timestamp": 1479243691000
- "start": 1479243691
- "end": 1479245282
- "datetime": "2016-11-15T21:01:31.000Z"

The .tcx file does not match the datetime, there is a gap of 1 second.

```xml
<Lap StartTime="2016-11-15T20:01:32.000Z">
...
<Trackpoint>
	<Time>2016-11-15T20:01:32.000Z</Time>
	<DistanceMeters>0.0</DistanceMeters>
	<SensorState>Present</SensorState>
</Trackpoint>
...
</Lap>
```

### Strava

This is correct. The JSON contains a key external_id which probably carries the sync time in UTC plus some GUID
which is not helpful.

- "external_id": "2016-11-15_21-34-59_GUID.tcx",
- "start_date": "2016-11-15T20:01:32Z"
- "start_date_local": "2016-11-15T21:01:32Z"
- "timezone": "(GMT+01:00) Europe/Berlin"
- "utc_offset": 3600.0

Surprisingly in the .tcx file the lap start and the first track point do not match, there's a gap of 1 second.

```xml
<Lap StartTime="2016-11-15T20:01:31.000Z">
...
<Trackpoint>
	<Time>2016-11-15T20:01:32.000Z</Time>
	<DistanceMeters>0.0</DistanceMeters>
	<SensorState>Present</SensorState>
</Trackpoint>
...
</Lap>
```
