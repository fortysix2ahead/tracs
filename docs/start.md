
# Getting Started

## Installation and Quickstart

First clone git repository (installation via pip is not yet supported):

```bash
git clone https://github.com/fortysix2ahead/tracs.git
```

Navigate to cloned repository and create a new virtual environment:

```bash
cd tracs
python3 -m venv venv
```

Activate the virtual environment:

```bash
(Linux/Mac OS)
source venv/bin/activate

(Windows)
.\venv\Scripts\activate.bat
```

Make tracs module executable and install dependencies:

```bash
pip3 install -e .
```

Check that everything works by running the version command. This should display the current version and exit:

```bash
tracs version
```

Run tracs setup and follow instructions:

```bash
tracs setup
```

## Workflow

The usual workflow is the following:

```bash
tracs fetch
```

This will fetch activity information from one or more remote services (currently Bikecitizens, Polar Flow, Strava, and
Waze, but the latter one is special). This command basically checks what activities
are available online and stores this information in the internal database. Only
metadata is downloaded.

```bash
tracs download
```

This will download the actual activities from the remote services. After this step .gpx and .tcx files will be created,
in case of Polar Flow also .csv and .hrv files.

```bash
tracs link
```

This step is optional. The download command creates files in a directory structure based on activity identifiers, which
is not very user-friendly. The link command creates a parallel directory structure based on year/month/day and creates
links to the original files. It's easier to traverse from a user perspective and can be re-created easily.

The three steps from above can be done in a combined way by running:

```bash
tracs sync
```

This will execute fetch, download and link in one go. Afterwards you can examine what ended up on your hard disk:

```bash
tracs list time:lastmonth
```

This command lists activities based on certain filters. In this example it will list activities from the last month.
A typical output would look like this:

```generic
  id   │ name            │ type    │ local time          │ uid
╶──────┼─────────────────┼─────────┼─────────────────────┼────────────────────╴
  1407 │ Afternoon Drive │ Cycling │ 22.06.2021 16:36:35 │ ['polar:123456001']
  1408 │ Evening Run     │ Run     │ 22.06.2021 19:30:52 │ ['polar:123456002']
  1409 │ Morning Cycling │ Cycling │ 24.06.2021 08:24:17 │ ['polar:123456003']
  1410 │ Afternoon Hike  │ Hiking  │ 24.06.2021 16:44:50 │ ['polar:123456004']
```

Finally, it's possible to show details for an activity:

```bash
tracs show 1409
```

The show command displays information about a certain activity. A typical output will look like this:

```generic
  field              │ value
╶────────────────────┼──────────────────────────────╴
  ID                 │ 1326
  Name               │ 00:15:27;3.69039990234375 km
  Type               │ Cycling
  Time (local)       │ 24.06.2021, 08:24:16
  Time (UTC)         │ 24.06.2021, 06:24:16
  Timezone¹          │ CEST
  Duration (elapsed) │ 00:15:28
  Distance           │ 3690.39990234375
  Calories           │ 138
```
