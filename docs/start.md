
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

## Basic Workflow

A basic workflow looks like this:

```bash
tracs import
```

This will fetch activity information from one or more remote services (currently Bikecitizens, Polar Flow, Strava, and
Waze, but the latter one is special). This command basically checks what activities are available, fetches activity
metadata like ids, times, distances etc. and downloads all known resources belonging to those activities (GPX, TCX
recordings, HRV data and so on).

Next we can check what we did this month: 

```bash
tracs list thismonth
```

This command lists activities based on certain filters (read more on the page about filters).
In this example it will list activities from the current month and display them in table. A typical output looks
like this:

```generic
  id   │ name            │ type    │ local time          │ uids
╶──────┼─────────────────┼─────────┼─────────────────────┼────────────────────╴
  1407 │ Afternoon Drive │ Cycling │ 22.06.2021 16:36:35 │ ['polar:123456001']
  1408 │ Evening Run     │ Run     │ 22.06.2021 19:30:52 │ ['polar:123456002']
  1409 │ Morning Cycling │ Cycling │ 24.06.2021 08:24:17 │ ['polar:123456003']
  1410 │ Afternoon Hike  │ Hiking  │ 24.06.2021 16:44:50 │ ['polar:123456004']
```

Finally, it's possible to show details for an activity. Each activity has an id, and we display the activity by
providing an id (1409 in this example).

```bash
tracs show 1409
```

The show command displays information about an activity. A typical output will look like this:

```generic
  field              │ value
╶────────────────────┼──────────────────────────────╴
  ID                 │ 1409
  Name               │ Morning Cycle
  Type               │ Cycling
  Time (local)       │ 24.06.2021, 08:24:17
  Time (UTC)         │ 24.06.2021, 06:24:17
  Duration           │ 00:15:28
  Distance           │ 3690
  Calories           │ 138
```

## Next steps

After running through the quickstart it's time to learn about the basic concepts of tracs, which are
[activities](activities.md), [resources](resources.md) and [filters](filters.md).
