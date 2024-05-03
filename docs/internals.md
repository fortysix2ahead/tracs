# Technical Details

## Configuration

The configuration file with its default values looks like this. See below to learn where to place this file. A valid 
configuration file can be created by running `tracs setup`. The meaning of the configuration keys are placed into
each comment.

```yaml

# main keys, values can be overwritten via command line argument

debug: no # enables debug mode
fetch_from: 2000 # year to start from when attempting to fetch all activities
force: no # enable force mode, which does not ask any questions
library: # absolute path to the activity library
pretend: no # pretend mode, simulates all commands, but does not persist changes
verbose: no # verbose mode, displays more log information

# database configuration

db:
  cache: yes
  cache_size: 100

# configuration for printing activity information

formats:
  locale: 'en'
  date: medium # allowed values: short, medium, long, full
  datetime: medium # allowed values: short, medium, long, full
  time: medium # allowed values: short, medium, long, full
  timedelta: short  # allowed values: narrow, short, long
  list:
    default: id raw_id name time type service

# experimental: allow predefined filters

filters:
  default:

# gpx parser configuration

gpx:
  parser: gpxpy # allowed values: internal, gpxpy

# plugin configuration

plugins:

  bikecitizens:
    username:
    password:

  polar:
    username:
    password:

  strava:
    username:
    password:
    client_id:
    client_secret:

  waze:
    field_size_limit: 131072
```

## Directory Layout

Tracs stores all of its files in two directories: the configuration directory and the library directory. By default,
both reside in one and the same directory. On Windows this is `~/AppData/Roaming/tracs/`, on Linux/Mac OS X it's
`~/.config/tracs/`. Inside you will find downloaded files from external services, configuration, logs and cache data.
Both directories can be separated by providing locations via the **-c** and the **-l** parameters.

### Configuration Directory

All configuration data is stored in the tracs configuration directory. This is located in `~/.config/tracs/` in
Linux/Mac OS X and in `~/AppData/Roaming/tracs/` in Windows as configuration root folder. The content of the
directory is the following:

```dirtree
[configuration root]/
├── backup/
│   └── db.<backup-timestamp>.json    # backup of the tracs database, including timestamp
├── config.yaml                       # configuration file
├── db.json                           # database containing all information about activities
├── logs/                             # log directory
│   └── tracs.log                  # log file
└── state.yaml                        # application state file containing transitive data
```

It's possible to point to a different configuration directory by using the **-c** switch. An example looks like this:

```bash
tracs -c [CONFIG_FOLDER]
```

When providing a different configuration directory, the configuration files are not searched for in the directory
itself, but in a subdirectory `.tracs`. So, when using `tracs -c /home/user/mydir`, the configuration file
must be present at `/home/user/mydir/.tracs/config.yaml`.

### Activity Library

The activity library is the second directory where files are stored. By default, it's the same as the configuration
folder, but can be moved to a different folder by using the **-l** parameter. An example is this:

```bash
tracs -l [LIBRARY_ROOT_FOLDER]
```

Instead of providing path to the library via the command line, the path can also be defined in the configuration file
(see above, section about the configuration file).

The content of the folder is the following: there are subfolders named after the supported services (currently polar,
strava and waze). Inside those folders all downloaded files can be found, but no other files (meaning nothing provided
not by external services).

When creating links, new subfolders for all years/months/days will be created, which point to the actual files. These
subfolders can be removed safely and recreated on request. A sample library with example files looks like this:

```dirtree
[library root]/
├── 2020/
├── 2021/                                     # Directory for a certain year
│   └── 04/                                   # Directory for a certain month
│       └── 21/                               # Directory for a certain day
│           └── 151651.polar.gpx              # link pointing to Polar .gpx file, named after time (if activity has no name)
│           └── 063731 - My Ru️n.strava.gpx    # link pointing to Strava .gpx file, named after name and time (if the activity has a name)
│           └── 063731 - My Ru️n.strava.tcx    # link pointing to Strava .tcx file, named after name and time (if the activity has a name)
│           └── 123427.waze.gpx               # link pointing to Waze .gpx file, named after time
├── polar/                                    # archive with Polar Flow activities
│   └── 1/
│       └── 2/
│           └── 3/
│               └── 123456789/                # directory containing files of a single Polar activity
│                   ├── 123456789.csv         # CSV data
│                   ├── 123456789.gpx         # GPX track (might be missing)
│                   ├── 123456789.hrv.csv     # HRV data (might be missing)
│                   └── 123456789.tcx         # TCX data
├── strava/                                   # archive with Strava activities
│   └── 1/
│       └── 2/
│           └── 3/
│               └── 123456789/                # directory containing files of a single Strava activity
│                   ├── 123456789.gpx         # GPX track (might be empty or missing)
│                   └── 123456789.tcx         # TCX data
├── waze/
│   └── Takeouts/                             # Directory containing all Waze takeouts
│   │   └── Takeout 2021-03-03/               # Directory containing a single Waze takeout
│   │       ├── account_activity_3.csv        # CSV containing all Waze tracks
│   │       └── account_info.csv              # Account data from Waze (always contained in takeout)
│   └── 2021/                                 # Directory for a certain year
│       └── 01/                               # Directory for a certain month
│           └── 21/                           # Directory for a certain day
│               └── 073044.gpx                # generated .gpx file for a certain drive, named after the point of time
```

## Open Issues

Issues can be reported via GitHub: [issues](https://github.com/fortysixandtwoahead/tracs/issues).

### Testing

Currently, testing is done mainly manually, a proper test suite exists, but is nowhere near complete. For Strava testing
a test account can be set up and populated. This is hardly possible for Polar Flow as they do not allow the manual
upload of activities. Their service needs to be mocked. Mock services exist (see test directory), but are not very
complete yet.

## Planned Features

See [issues](https://github.com/fortysixandtwoahead/tracs/issues) for planned future features.

## Hidden Commands

There are a couple of commands that are hidden by default and are not going to be displayed when running
`tracs --help`. However, they are not so incredibly secret that a documentation for needs also to be hidden.

### db

```bash
tracs db [OPTIONS]

Options:
  -b, --backup
  -m, --migrate MIGRATION_FUNCTION
  -r, --restore
  -s, --status
```

Tracs will keep all information fetched from remote services in an internal JSON-based db. This command carries out
some database operations. The option **-b** creates a backup of the internal database. Mainly used during development,
but might be useful to save certain states of the db. See technical information in [internals.md](internals.md) to learn
where the backups are stored.

The option **-r** restores the last state of the database from the backup folder and overwrites the current one (but
asks before overwriting).

The optione **-s** prints some internal database information. A sample output looks like this:

```generic
---------------------------  ----------------------------------------------------------------
activities in database:      2978
activities from Polar Flow:  1425
activities from Strava:      1433
activities from Waze:        526
activities linked:           
activities without name:     676
---------------------------  ----------------------------------------------------------------
```

The switch **-m** updates the internal database scheme by executing the provided migration function. This might be
necessary from time to time, when new database fields are added (and will be automated in the future).

### validate

```bash
tracs validate
```

This is work in progress and runs several checks in order to ensure database integrity (or at least list things that
appear strange).

## Requirements

- Python 3.10

### Required Third-Party Libraries

- arrow
- attrs
- beautifulsoup4
- babel
- bottle
- cattrs
- click
- click-shell
- confuse
- datetimerange
- fs
- geojson
- gpxpy
- lxml
- oauthlib
- platformdirs
- pytest
- python-dateutil
- pyyaml
- orjson
- requests
- requests-cache
- requests-oauthlib
- rich
- rule-engine
- stravalib
- tcxreader
- tzlocal

### Required Third-Party Libraries for Development

- bumpver
- flit
- mkdocs
- mkdocs-click
- mkdocs-material
