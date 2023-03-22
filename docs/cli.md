
# Command Line Interface Reference

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

**Commands (NEEDS UPDATE!):**

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

## Commands and Options (COPY FROM README - OUTDATED!)

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

# Reference

Please see sections below for further details on each command. There are additional hidden commands which do not show
up in the help, but are documented below as well.

This page provides documentation for CLI.

::: mkdocs-click
    :module: tracs.cli
    :command: config
    :depth: 1
    :style: table
    :show_hidden: False

::: mkdocs-click
    :module: tracs.cli
    :command: fields
    :depth: 1
    :style: table
    :show_hidden: False

::: mkdocs-click
    :module: tracs.cli
    :command: ls
    :depth: 1
    :style: table
    :show_hidden: False

::: mkdocs-click
    :module: tracs.cli
    :command: show
    :depth: 1
    :style: table
    :show_hidden: True

::: mkdocs-click
    :module: tracs.cli
    :command: version
    :depth: 1
    :style: table
    :show_hidden: False
