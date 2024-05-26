# Spar-kit - Python style API for heavy SQL users

Spark-kit provides a set of utilities and an intuitive API for constructing SQL queries programmatically, making it easier to build, read, and maintain complex SQL statements.

## Installation

```sh
pip install sparkit
```

## Usage

Sparkit was built borrowing from its inspiring packages to write SQL from left to right. Although a query might look like this:
```sql
SELECT id -- starting from what columns we want
FROM db.schema.table1 -- but we should start from where we want them
```

### Simplest entry point `table` and `col`
Sparkit allows you to start from sources:

```python
from sparkit.sql import table, col
from sparkit.column import Column

t = table("db.schema.table1")
print(t.sql)
# Output: SELECT * FROM db.schema.table1

t = table("db.schema.customers").select(col("id"), col("name"))
print(t.sql)
# Output: SELECT id, name FROM db.schema.customers

# declaring columns as objects
customer_id: Column = col("id")
```

### Operators and literals

All the basic python operators can be used on the `Column` object: `==,!=,>,>=,<.<=,&,|,+,-,...`

```python
from sparkit.sql import table, col, lit

query = table("db.schema.customers").select(
        col("id"), 
        (col("first_name") == lit("john")).as_("is_john"),
        (col("last_name") == lit("doe")).as_("is_doe"),
        (col("age") - col("years_since_joined")).as_("age when joined")
    )
print(query.sql)
# Output: SELECT id, first_name = 'john' AS is_john, last_name = 'doe' AS is_doe, age - years_since_joined AS `age when joined` FROM db.schema.customers
```

### Joins:
```python
t1 = table("db.schema.table1").as_("t1")
t2 = table("db.schema.table2").as_("t2")
inner = t1.join(t2, col("t1.id") == col("t2.id"))
print(inner.sql)
# Output: SELECT * FROM db.schema.table1 AS t1 INNER JOIN db.schema.table2 AS t2 ON t1.id = t2.id
```

## Inspiration and rationale

We wished to create a left-to-right API to write the huge SQL queries that sometimes dominate python code, without working with SQLAlchemy or spark which is a pain on its own

 - [Spark](https://spark.apache.org/examples.html)
 - [Polars](https://docs.pola.rs/)

## SQL flavour

Version 0.1.0 was built over BigQuery syntax, with the aim of supporting more flavours in future versions.

## Contributing

Please be aware of the package dependency structure:
![dependency structure](/sparkit/module%20relationship.png)

## License

This project is licensed under the MIT License. See the LICENSE file.

## Contact
For any inquiries, please contact [aviad.klein@gmail.com](mailto:aviad.klein@gmail.com) - don't hope for high SLA...