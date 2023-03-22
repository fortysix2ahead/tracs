
# Tracs

Tracs is a command line application for managing GPS tracks (data recorded from GPS/Galileo and the like)
and simultaneously a command line client for sports online services which allow creation/recording/uploading etc.
of such tracks. Currently, Polar Flow, Strava, Bikecitizens and Waze are supported.

Tracs downloads activities, manages them, displays information and, well, does also a bit more than that (at least
that's the plan). The role model for Tracs is the command line music organizer [beets](https://github.com/beetbox/beets).
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

## Getting Started

The impatient go here: [Getting Started](start.md)

