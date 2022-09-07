# Tracs

Tracs is a command line application for managing GPS tracks (data recorded from GPS/Galileo and the like)
and simultaneously a command line client for sports online services which allow creation/recording/uploading etc.
of such tracks. Currently, Polar Flow, Strava, Bikecitizens and Waze are supported.

Tracs downloads activities, manages them, displays information and, well, does also a bit more than that (at least
that's the plan). The role model for Tracs is the command line music organizer beets (https://github.com/beetbox/beets).
Many ideas are borrowed from beets. Tracs is written in Python and served as my playground for learning the language,
but has evolved heavily since then.

Why Tracs? First, because it's your data. You can create takeouts out of services like Polar or Strava, but you get
a large chunk of machine-only readable data. You need to do the sorting/postprocessing by yourself. Second, because
I am a geo data junkie who likes to keep stuff locally/self-hosted. And third, I would like to add functionality to
Tracs that is not available anywhere else (just copying functionality does not provide any benefits as my time is
limited).

**Important:** Tracs is not yet ready, several things are still broken. There's still some way to go before doing a
first release, so use it at your own risk.

## Features

- fetch activities from Polar Flow, Strava, Bikecitizens and Waze
- download GPX, TCX, CSV and HRV files from Polar Flow, Strava and Bikecitizens
- read and convert takeouts from Waze
- maintain a structured archive containing all activities
- semi-automatically group activities from different services
- list activities based on various filters
- print activity details in a nicely formatted way
- aggregate and export activities to various formats (work in progress)
- plugin-based architecture, ready for future extensions (work in progress)

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

## Usage

Tracs is a command line client. It provides various commands to interact with remote services as well as with the
downloaded files. The following commands/options are currently supported. Please note that the CLI is not yet stable and
names/parameters might change.

The overall command line usage is the following:

```bash
tracs <general options> <command> <command specific options> <parameters>
```

**General Options:**

```generic
-c, --configuration CONFIG_DIR: configuration area location
-d, --debug: enable output of debug messages
-f, --force: forces operations to be carried out
-l, --library LIB_DIR: library location
-p, --pretend: pretend to work, only displays what is happening, but does not persist any changes
-v, --verbose: be more verbose
--help: show help message
```

**Commands:**

```generic
config - prints the current configuration
download - downloads activities (as .gpx, .tcx etc.)
edit - edits activities (like name, type etc.) - WORK IN PROGRESS
export - export activities - WORK IN PROGRESS
fetch - fetches activity metadata from (remote) services
group - groups activities
link - creates links for downloaded resources of activities
list - lists activities
reimport - reimports activities
rename - renames activities
setup - runs the interactive application setup
show - shows details about activities
sync - synchronizes activities (fetch, download and link in one go)
version - prints version information
```

Please see sections below for further details on each command. There are additional hidden commands which do not show
up in the help, but are documented below as well.

### Workflow

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

## Commands and Options

Below all commands are documented in alphabetical order.

### config

```bash
tracs config
```

This prints the current configuration to the console. Please note that stored passwords are included.

### download

```bash
tracs download [OPTIONS] FILTERS

Options:
```

Downloads activities, namely .gpx, .tcx files etc. The download will be triggered for either all activities or only
activities matching the provided filters. See the section below on filtering activities to
learn about existing filters.

### fetch

```bash
tracs fetch [OPTIONS]

Options:
  -r, --restrict [bikecitizens|polar|strava|waze]   restricts fetching to only one source
```

Fetches activity metadata. Note that Tracs only checks what activities exist by downloading their metadata, but does
not yet download any gpx or tcx file. The downloaded metadata is stored in the internal database. By default, only
activities from the current year are checked. The sources to be checked can be restricted by using the **-r** switch
with one of the parameters **bikecitizens**, **polar**, **strava** or **waze**. By default, all configured services
are checked.

Important note for Waze: currently the process of requesting and downloading the takeouts cannot be automated due to
captchas used on the Waze site. For this reason Waze takeouts need to be downloaded manually and put into the Waze
library folder (see section below about library layout), named preferably ```Takeout <download timestamp>```.

### help

```bash
tracs --help
tracs COMMAND --help
```

The first command shows all available general options and commands. The second displays help on a specific command.

### group

```bash
tracs group [OPTIONS] [FILTERS]...

Options:
  -r, --revert  reverts groups and creates separate activities (again)
```

The group command is rather special. It's supposed to relate activities that have been downloaded from different
services. For example a Polar account might be linked to a Strava account. When downloading activities from Polar and
from Strava, you will end up with two recordings representing the same activity. If treated as two activities this would
lead to the paradox that two activities happened at the same time (which is impossible). That's why two or more
so-called activities can be grouped and marked as *being the same*. Why support such a construct? It's because data
provided by different service might be different. So you can fetch the duration and distance from Polar
and the ascent/descent from Strava.

Grouping activities is interactive, Tracs will ask for necessary information. Before grouping, you might have
something like this:

```generic
  ID  Name                         Date                 Type               Polar ID    Strava ID
----  ---------------------------  -------------------  -----------------  ----------  -----------
1408  Evening Run                  22.06.2021 19:30:52  Run                1000000002
1409  Evening Run                  22.06.2021 19:30:53  Run                            2000000002
```

After grouping the result is this:

```generic
  ID  Name                         Date                 Type               Polar ID    Strava ID  
----  ---------------------------  -------------------  -----------------  ----------  -----------
1408  Evening Run                  22.06.2021 19:30:52  Run                1000000002  2000000002
```

Grouped activities can be broken up again by using the **-r** parameter.

### link

```bash
tracs link [OPTIONS] [FILTERS]...

Options:
  -a, --all                          creates links for all activities (instead of recent ones only), overriding provided filters
```

This command creates a second directory structure parallel to the one where all downloaded files are stored and creates
symbolic links to those files, based on year, month and day or activites. See [internals.md](internals.md) to learn
how this structure looks like in detail. This is supposed to be more user-friendly when looking up certain files in the
file system. Note that symbolic linking works both on Windows and Unix-like systems.

### list

```bash
tracs list [OPTIONS] [FILTERS]...

Options:
  -s, --sort [id|name|date|type]  sorts the output according to an attribute
```

This lists activities according to one or more provided filters. The sort order option can be used to customize the
order of items. The default is to sort by id.

### rename

```bash
tracs rename [OPTIONS] [FILTERS]...

Options:
  --help  Show this message and exit.
```

Renames activities. The rename command works interactively and asks for a new name for an activity. The default name
is created out of activity names of either Polar and/or Strava exercises.

### setup

```bash
tracs setup
```

Performs a guided setup of the application. Credentials for Polar and Strava can be entered and a proper configuration
file is created. See [internals.md](internals.md) to learn where configuration data is stored.

### show

```bash
tracs show [OPTIONS] [FILTERS]...
```

The show command displays information about a certain activity. A typical output will look like this:

```generic
-----------------  ---------------------------------------------------
Id                 1409
Name               Morning Cycling
Type               Cycling
Time (local)       24.06.2021 08:24:17
Time (UTC)         24.06.2021 06:24:17
Timezone           CEST
...
Polar Activities   1000000003
Strava Activities  2000000003
Waze Activities
URLs               https://flow.polar.com/training/analysis/1000000003
                   https://www.strava.com/activities/2000000003
-----------------  ---------------------------------------------------
```

### version

```bash
tracs version
```

Prints version information and exits.

## Filtering Activities

Filtering activities is most likely the most important concept of Tracs. Always all commands (apart from a few
exceptions) work based on filters, like for instance listing activities. A filter takes the form of

```generic
[NEGATION][FIELD][:|::][VALUE|RANGE]
```

There are exceptions to this form for convenience, which are explained below. Multiple filters can be combined
and are treated with a logical **AND**. Filters can be negated by preceding a **^**. However, this might not work
depending on the shell that is used. See this issue: <https://github.com/fortysix2ahead/tracs/issues/15>

| Filter Name      | Filter Value         | Explanation                                                                                                                                                                                                                                                                                                                                   | Example                               |
|------------------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| \[id\]           | number               | The number is treated as an identifier. This number can be an activity id (usually in the range of 1 to 9999) or as id for an external service like 60001234. Depending on what is found as a result either an activity or an external activity is returned. This filter is purely for convenience, and id as the filter name can be omitted. | tracs list 100                     |
| name             | string               | Matches activities that have the provided string in their name (case-insensitive).                                                                                                                                                                                                                                                            | tracs list name:Marathon           |
| service          | string               | Matches activities which have references to recording from the provided external service.                                                                                                                                                                                                                                                     | tracs list service:polar           |
| \[service name\] | number               | Matches activities having the provided external id. Service name needs to be one of the supported services                                                                                                                                                                                                                                    | tracs list polar:10001234          |
| time             | \[date\]\.\.\[date\] | Matches activities that started in the provided time range. The date must be in the form of year-month-day. Month and day are optional, as well as the start and end range.                                                                                                                                                                   | tracs list time:2020\.\.2021-07-01 |
| time             | string               | In addition to the form above taking fixed dates as values there are predefined time ranges: *latest, lastweek, lastmonth, lastquarter, lastyear*. This matches the last activity, the last 7 days, last 31 days, last 3 months and the last 12 months respectively.                                                                          | tracs list time:lastweek           |
| type             | string               | Matches activities having the provided type (case-insensitive).                                                                                                                                                                                                                                                                               | tracs list type:run                |

### Examples

In order to get a notion of how filters work, here are a few examples, by using the list command.

```bash
# matches activity id = 100
tracs list 100
# same as above
tracs list id:100
# matches everything retrieved from Polar
tracs list service:polar
# matches everything from June 2020
tracs list date:2020-06
# matches everything which happened last week in the morning where the heartrate was between 160 and 180
tracs list date:lastweek time:morning heartrate:160..180
```

## Technical Details

For technical details go here: [internals.md](internals.md).
