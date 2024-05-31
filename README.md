# FLUQ (FLUent Queries) - Python style API for heavy SQL users

FLUQ provides a set of utilities and an intuitive API for constructing SQL queries programmatically, making it easier to build, read, and maintain complex SQL statements.

## Installation

```sh
pip install fluq
```

## Usage

Fluq was built borrowing from its inspiring packages to write SQL from left to right. 
The package does not connect to data bases or run queries for the user, rather, it prevents users from having to create huge blobs of text that are hard to read, re-use and manage.

Where usually a query might look like this:
```sql
SELECT id -- starting from what columns we want
FROM db.schema.table1 -- but we should start from where we want them
```

The fluq way goes logically left-to-right:
```python
from fluq.sql import *

query = table("db.schema.table1").select("id")

print(query.sql) # returns: SELECT id FROM db.schema.table1
```

### The API:

### Starting from tables: `table` method

Fluq allows you to start from sources

```python
from fluq.sql import table

query = table("db.schema.table1") # this defines a Frame object
print(type(query)) 
# Output: <class 'fluq.frame.Frame'>
```
`Frame` has many methods, among the rest is the `sql` property that renders the SQL code to run the query.

```python
print(t.sql)
# Output: SELECT * FROM db.schema.table1
```

#### Select specific columns
```python
from fluq.sql import table, col

query = table("db.schema.table1").select("id", "name")
```

Or, by using the `col` method:
```python
query = table("db.schema.table1").select(col("id"), col("name"))
```

By using `col`, we get back a `Column` object, that allows to perform multiple operations over columns among the rest we can give them a different alias:

```python
query = table("db.schema.table1").select(
    col("id").as_("`customer id`"), 
    col("name").as_("`customer name`"))

print(query.sql)
# Output: SELECT id AS `customer id`, name AS `customer name` FROM db.schema.table1
```


### Specifying columns and literals

* `col` - a method to represent a column by name
* `lit` - a method to represent primitives (`str`, `bool`, `int`, `float`) as SQL literals
* `select` - standalone method to select without a FROM clause (good for examples)

```python
from fluq.sql import select, col, lit

query = select(col("a"))
print(type(query)) 
# Output: <class 'fluq.frame.Frame'>

print(query.sql)
# Output: SELECT a -- will result in an error over any db since "a" is not defined
```

### Selecting literals using `lit`
```python
from fluq.sql import select, lit

query = select(lit(2).as_("two"))

print(query.sql)
# Output: SELECT 2 AS two
```

### Arithmetics and functions:

```python
from fluq.sql import table, col, lit, functions as fn
from datetime import date

# create a literal with the current year
current_year = lit(date.today().year)

query = table("some.table").select(
    (current_year - col("year_joined")).as_("years_since_joined"),
    (col("orders")**2).as_("orders_squared"),
    col("sum_transactions")*lit(1-0.17).as_("sum_transactions_net"),
    fn.exp(3)
)

print(query.sql)
# Output: SELECT 2024 - year_joined AS years_since_joined, POWER( orders, 2 ) AS orders_squared, sum_transactions * 0.83, EXP( 3 ) FROM some.table
```

### Logical operators: `==, >, >=, <>, <, <=, &, |`:
```python
from fluq.sql import table, col

query = table("db.customers").where(
    (col("date_joined") > '2024-01-01') &
    (col("salary") < 5000) &
    (col("address").is_not_null()) & 
    (col("country") == 'US') &
    (col("indutry").is_in('food', 'services'))
).select("id", "name", "address")

print(query.sql)
# Output: SELECT id, name, address FROM db.customers WHERE ( ( ( ( date_joined > '2024-01-01' ) AND ( salary < 5000 ) ) AND ( address IS NOT NULL ) ) AND ( country = 'US' ) ) AND ( indutry IN ( 'food', 'services' ) )
```

NOTE: the `__eq__` magic method was 'kidnapped' in order to have a very python like approach. This is not void of potential issues. When comparing `Column` objects, use the `_equals` method instead of `==`.


## Inspiration and rationale

We wished to create a left-to-right API to write the huge SQL queries that sometimes dominate python code, without working with SQLAlchemy or spark which is a pain on its own

 - [Spark](https://spark.apache.org/examples.html)
 - [Polars](https://docs.pola.rs/)

## SQL flavour

Version 0.1.0 was built over BigQuery syntax, with the aim of supporting more flavours in future versions.

## Contributing

Please be aware of the package dependency structure:
![dependency structure](/fluq/module%20relationship.png)

## License

This project is licensed under the MIT License. See the LICENSE file.

## Contact
For any inquiries, please contact [aviad.klein@gmail.com](mailto:aviad.klein@gmail.com) - don't hope for high SLA...