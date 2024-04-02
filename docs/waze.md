
# Waze

[Waze](https://waze.com) is a turn-by-turn navigation app available for Android and iOS. It incorporates user-submitted travel times and route details and allows to create so-called takeouts, which contain travel data of the last 90 days. Tracs allows to import those takeouts, however there's a catch: the creation of takeouts is a manual activity.

## Takeout Creation

The takeout archive for the last 90 days can be created from the user account page at [https://www.waze.com/account/download_data](https://www.waze.com/account/download_data). You can request an archive, after a short time a password protected zip file will be provided.

Tracs provides a special folder for takeout data. The data from the takeout archive needs to be extracted in the Waze takeout data folder.
Go to `<TRACS_CONFIG_DIR>/takeouts/waze` (create the folder in case it does not exist). Waze takeout files do not have any unique
name, so it's recommended to put the takeouts you collect over time in separate subfolders. A directory structure might look like this:

```dirtree
[TRACS_CONFIG_DIR]/takeouts/waze/
├── 2020-01/
│   └── account_activity_3.csv
│   └── account_info.csv
├── 2020-02/
│   └── account_activity_3.csv
│   └── account_info.csv
├── 2020-03/
├── ...
```

## Takeout Import

The import command of Tracs tries to fetch data from remote sources. For this reason running `tracs import waze` does nothing (this may change as Waze might provide the GPS data
via API). The import  of (local) takeout data is only triggered upon request. Use the `-t` switch for importing Waze takeout data:

```
tracs import -t waze
```

Tracs will scan the Waze takeout directory recursively for `account_activity_3.csv`files and import all data from those files. Takeouts might contain overlapping data (a drive might
be contained in several takeout files). You do not need to care about that, Tracs will import such drives only once.
