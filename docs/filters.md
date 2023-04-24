
# Filters

Filtering activities is most likely the core concept of Tracs. Almost all commands (apart from a few exceptions) work
based on filters, like for instance listing activities. Commands apply filters on all known activities and work on
the subset of activities which match those filters. The general form of a filter is this

```generic
[FIELD][OPERATOR][EXPRESSION]
```

There are exceptions to this form for convenience, which are explained later in this section. Multiple filters can
be combined and are treated with a logical **AND**.

## Fields

As you have learned in the [section about activities](activities.md), each activity has a number of attributes. Those
can be used as fields in filters. Note that there are more fields than attributes! An obvious example for an
attribute is `time` which is the time when an activity took place. However, there is a field `year`, which represents
the year of the activity. There is no attribute `year` (at least no physical one, which is stored in the db), however
it still can be used as a filter.

Filters (and attributes) have types like string, int or dates, which obviously restrict the expressions which can be
used with them. A `duration` cannot be a string like `Berlin`. If you try things like that, a rule syntax error
will be shown.

Valid field names can only consist of lower case letters, underscores and numbers. The first character must be a letter.

## Operators

An operator compares a field against an expression. Currently, the following operators are supported:

| Operator | Explanation                                                           |
|----------|-----------------------------------------------------------------------|
| ==       | Equal, matches if field has an equal value compared to the expression |
| =        | Short form of ==, for convenience                                     |
| :        | "Smart" equal, see below for further explaination                     |
| !=       | Not equal, matches if field and expression have non-equal values      |
| =~       | Same as equal, but expression represents a regular expression         |
| !~       | Same as not equal, but expression represents a regular expression     |
| >=       | Greater than or equal, only works with numeric fields                 |
| \>       | Greater than, only works with numeric fields                          |
| <=       | Less than or equal, only works with numeric fields                    |
| <        | Less than, only works with numeric fields                             |

**Important:** note that depending on the shell you are using the filter needs to be escaped, as the shell may for example interpret
the character `>` as a pipe. 

### Colon Operator, or Smart Equal Operator

Filters are based on an underlying rules of a rule engine, which is responsible for evaluation if an activity matches
a filter or not (see
[https://zerosteiner.github.io/rule-engine/syntax.html](https://zerosteiner.github.io/rule-engine/syntax.html))
for more details. A filter is parsed and handed to the rule engine more or less unchanged - with one exception:
the colon operator. The colon operator plays the role of a "smart equal" operator and allows shorter and more
convenient expressions. Without the colon operator, the filter for finding activities from 2022 would look like this:

```
'time>=d"2022-01-01 00:00:00"' 'time<=d"2022-12-31 23:59:59"'
```

With the colon operator and in conjunction with the virtual attribute `year` this expression becomes:

```
year:2022
```

... which should save some typing. The actual behaviour of the colon operator depends on the type of the field.
The table below outlines its abilities.

| Expression               | Used with fields of type | Explanation                                                                        |
|--------------------------|--------------------------|------------------------------------------------------------------------------------|
| string                   | string                   | Matches if the lowercase string is contained in the field value                    |
| string                   | list                     | Matches if the lowercase string is contained as element in the list                |
| int                      | datetime                 | Considered as year                                                                 |
| int-int                  | datetime                 | Considered as year + month                                                         |
| int-int-int              | datetime                 | Considered as year + month + day                                                   |
| int,int ...              | int                      | Considered as list of numbers, matches if the field value is contained in the list |
| int..int                 | int                      | Considered as range of numbers, matches if the field value is within the range     |
| int..                    | int                      | Considered as range of numbers, with open end                                      |
| ..int                    | int                      | Considered as range of numbers, with open beginning                                |
| int-int-int..int-int-int | datetime                 | Considered as range of dates (missing month and day values are valid)              |
| int-int-int..            | datetime                 | Considered as range of dates, with open end                                        |
| ..int-int-int            | datetime                 | Considered as range of dates, with open beginning                                  |
| \<empty\>                | datetime                 | Matches if the field value is empty                                                |

For examples see the examples section below.

## Expressions

Expressions are the parts of filters against which the value of fields are compared. Depending on the type of the field, several expressions
are valid (apart from the forms explained in the previous section about the colon operator).

| Expression | Explanation                                                                 |
|------------|-----------------------------------------------------------------------------|
| bool       | may be \"true\" or \"false\"                                                |
| int        | Treated as number                                                           |
| float      | Treated as number                                                           |
| string     | Treated as string, whitespaces need to be escaped with \"                   |
| iso date   | Treated a datetime, must comply to the isoformat and may need to be escaped |

## Filterless expressions and Keywords

As mentioned above, there are exceptions to the general form of filters, which save even more typing. In some cases the filter field and the operator can
be omitted, which results in a certain predefined filter (\"filterless expression\"):

| Filterless Expression | Effect                                                                      |
|-----------------------|-----------------------------------------------------------------------------|
| int                   | Is considered as activity _id_                                              |
| 2000..2023            | Is considered as year of an activity (and overrules _id_ from above!)       |

In addition, alphanumeric strings are considered _keywords_. Behind each keyword, there's a
predefined filter, so the keyword can be used as a shortcut.

| Keyword      | Filter Expression                  |
|--------------|------------------------------------|
| afternoon    | time is between 13:00 and 18:00    |
| bikecitizens | origin is bikecitizens service     |
| evening      | time is between 18:00 and 22:00    |
| last7days    | time is within the last 7 days     |
| last14days   | time is within the last 14 days    |
| last30days   | time is within the last 30 days    |
| last60days   | time is within the last 60 days    |
| last90days   | time is within the last 90 days    |
| lastweek     | time is within the last week       |
| lastmonth    | time is within the last month      |
| lastquarter  | time is within the last quarter    |
| lastyear     | time is within the last year       |
| morning      | time is between 06:00 and 11:00    |
| night        | time is between 22:00 and 06:00    |
| noon         | time is between 11:00 and 13:00    |
| polar        | origin is polar service            |
| strava       | origin is strava service           |
| thisweek     | time is within the current week    |
| thismonth    | time is within the current month   |
| thisquarter  | time is within the current quarter |
| thisyear     | time is within the current year    |
| today        | time is today                      |
| waze         | origin is waze                     |

### Examples

In order to get a notion of how filters work, here are a few examples, by using the list command.

Matches the activity with id = 100:

```bash
tracs list 100
tracs list id:100
```

Matches everything retrieved from Polar:

```bash
tracs list polar
tracs list classifier:polar
tracs list service:polar
```

Matches everything from June 2020:

```bash
tracs list date:2020-06
```

Matches everything from 2022:

```bash
tracs list 2022
tracs list year:2022
tracs list lastyear
```

Matches everything which has `redbike` as equipment and is tagged with `race`:

```bash
tracs list equipment:redbike tag:race
```

Matches everything from 2020 which misses a distance:

```bash
tracs list year:2020 distance:
```

Matches everything which happened last week in the morning where the average heartrate was between 160 and 180:

```bash
tracs list lastweek morning heartrate:160..180
```
