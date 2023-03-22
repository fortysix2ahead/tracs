
# Filters

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
