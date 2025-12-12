# EDTF to Date Range Translation

This page documents by example the conversions between EDTF date and Solr 
[DateRange] values that the Solrizer [dates indexer] performs. These 
examples are taken from the [unit tests](../tests/indexers/test_dates.py) 
for the dates indexer.

## Supported

| EDTF                    | Solr DateRange               |
|-------------------------|------------------------------|
| `1605-11-05`            | `1605-11-05`                 |
| `2000-11`               | `2000-11`                    |
| `1984`                  | `1984`                       |
| `2000-11-01/2014-12-01` | `[2000-11-01 TO 2014-12-01]` |
| `2004-06/2006-08`       | `[2004-06 TO 2006-08]`       |
| `1964/2008`             | `[1964 TO 2008]`             |
| `2014/2014-12-01`       | `[2014 TO 2014-12-01]`       |
| `../1985-04-12`         | `[* TO 1985-04-12]`          |
| `../1985-04`            | `[* TO 1985-04]`             |
| `../1985`               | `[* TO 1985]`                |
| `1985-04-12/..`         | `[1985-04-12 TO *]`          |
| `1985-04/..`            | `[1985-04 TO *]`             |
| `1985/..`               | `[1985 TO *]`                |
| `-0009`                 | `-0009`                      |

### Date and Time

Normalized to UTC, with the "Z" notation for the time zone.

| EDTF                        | Solr DateRange         |
|-----------------------------|------------------------|
| `2024-11-18T11:49:32-05:00` | `2024-11-18T16:49:32Z` |

### Seasons (With Hemisphere)

Note about year-wrapping (taken from a comment in 
[edtf.appsettings]):

> winter in the northern hemisphere wraps the end of the year, so
> Winter 2010 could wrap into 2011.
> 
> For simplicity, we assume it falls at the end of the year, esp since the
> spec says that sort order goes spring > summer > autumn > winter

#### Northern Hemisphere

| EDTF      | Solr DateRange               | Season |
|-----------|------------------------------|--------|
| `2001-25` | `[2001-03-01 TO 2001-05-31]` | spring |
| `2001-26` | `[2001-06-01 TO 2001-08-31]` | summer |
| `2001-27` | `[2001-09-01 TO 2001-11-30]` | autumn |
| `2001-28` | `[2001-12-01 TO 2001-12-31]` | winter |

#### Southern Hemisphere

| EDTF      | Solr DateRange               | Season |
|-----------|------------------------------|--------|
| `2001-29` | `[2001-09-01 TO 2001-11-30]` | spring |
| `2001-30` | `[2001-12-01 TO 2001-12-31]` | summer |
| `2001-31` | `[2001-03-01 TO 2001-05-31]` | autumn |
| `2001-32` | `[2001-06-01 TO 2001-08-31]` | winter |

### Other Year Subdivisions

#### Quarters (3-month blocks)

| EDTF      | Solr DateRange               |
|-----------|------------------------------|
| `2001-33` | `[2001-01-01 TO 2001-03-31]` |
| `2001-34` | `[2001-04-01 TO 2001-06-30]` |
| `2001-35` | `[2001-07-01 TO 2001-09-30]` |
| `2001-36` | `[2001-10-01 TO 2001-12-31]` |

#### Quadrimesters (4-month blocks)

| EDTF      | Solr DateRange               |
|-----------|------------------------------|
| `2001-37` | `[2001-01-01 TO 2001-04-30]` |
| `2001-38` | `[2001-05-01 TO 2001-08-31]` |
| `2001-39` | `[2001-09-01 TO 2001-12-31]` |

#### Semesters  (6-month blocks)

| EDTF      | Solr DateRange               |
|-----------|------------------------------|
| `2001-40` | `[2001-01-01 TO 2001-06-30]` |
| `2001-41` | `[2001-07-01 TO 2001-12-31]` |

### Unspecified Digits

| EDTF         | Solr DateRange               |
|--------------|------------------------------|
| `1992-09-XX` | `[1992-09-01 TO 1992-09-30]` |
| `1992-XX`    | `[1992-01-01 TO 1992-12-31]` |
| `199X`       | `[1990-01-01 TO 1999-12-31]` |
| `19XX`       | `[1900-01-01 TO 1999-12-31]` |
| `1XXX`       | `[1000-01-01 TO 1999-12-31]` |
| `XXXX`       | `[0000-01-01 TO 9999-12-31]` |

### Exponential Years

These are supported, as long as they are between -9999 and 9999.

| EDTF    | Solr DateRange                 |
|---------|--------------------------------|
| `Y1E3`  | `[1000-01-01 TO 1000-12-31]`   |
| `Y5E2`  | `[0500-01-01 TO 0500-12-31]`   |
| `Y6E1`  | `[0060-01-01 TO 0060-12-31]`   |
| `Y-1E3` | `[-1000-01-01 TO -1000-12-31]` |
| `Y-5E2` | `[-500-01-01 TO -500-12-31]`   |
| `Y-6E1` | `[-060-01-01 TO -060-12-31]`   |

## Not Supported

These values, while valid EDTF, cannot be converted to Solr DateRange 
values and are thus not supported by Solrizer:

### Long Year

Years with more than 4 digits. For example:

  * `Y21000`
  * `Y-18000`

### Exponential Years ≥ 1E4

When the exponent is greater than 3. For example:

  * `Y1E5`
  * `Y-2E6`

## Not Implemented

Conversion of these types of EDTF values is not yet implemented. Any 
translation would likely be just a "good-enough" approximation.

### One of a Set

e.g., `[2001,2002,2005]`

### Multiple Dates

e.g., `{1966,1979,1983}`

[DateRange]: https://solr.apache.org/guide/solr/9_6/indexing-guide/date-formatting-math.html
[dates indexer]: https://umd-lib.github.io/solrizer/solrizer/indexers/dates.html
[edtf.appsettings]: https://github.com/ixc/python-edtf/blob/main/edtf/appsettings.py#L15-L28
