---
applyTo: "**/*.py"
---
## Python

When writing Python:

* Assume the latest python, version 3.13.
* Prefer Pathlib methods (including read and write methods, like `read_text`) over `os.path`, `open`, `write`, etc.
* Use Pydantic models over dataclass or a typed dict.
* Use SQLAlchemy for generating any SQL queries.
* Use `click` for command line argument parsing.
* Use `log.info("the message", the_variable=the_variable)` instead of `log.info("The message: %s", the_variable)` or `print` for logging. This object can be found at `from app import log`.
  * Log messages should be lowercase with no leading or trailing whitespace.
  * No variable interpolation in log messages.
  * Do not coerce database IDs, dates, or Path objects to `str`
* Do not fix import ordering or other linting issues.
* Never edit or create any files in `migrations/versions/`
* Place all comments on dedicated lines immediately above the code statements they describe. Avoid inline comments appended to the end of code lines.
* Do not `try/catch` raw `Exceptions` unless explicitly told to. Prefer to let exceptions raise and cause an explicit error.

### Typing

* Assume the latest pyright version
* Prefer modern typing: `list[str]` over `List[str]`, `dict[str, int]` over `Dict[str, int]`, etc.
* Prefer to keep typing errors in place than eliminate type specificity:
  * Do not add ignore comments such as `# type: ignore`
  * Never add an `Any` type.
  * Do not `cast(object, ...)`

### Data Manipulation

* Prefer `funcy` utilities to complex list comprehensions or repetitive python statements.
* `import funcy as f` and `import funcy_pipe as fp`
* Some utilities to look at: `f.compact`

For example, instead of:

```python
params: dict[str, str] = {}
if city:
    params["city"] = city
if state_code:
    params["stateCode"] = state_code
```

Use:

```python
params = f.compact({"city": city, "stateCode": stateCode})
```

### Date & DateTime

* Use the `whenever` library for datetime + time instead of the stdlib date library. `Instant.now().format_iso()`
* DateTime mutation should explicitly opt in to a specific timezone `SystemDateTime.now().add(days=-7)`

### Database & ORM

When accessing database records:

* SQLModel (wrapping SQLAlchemy) is used
* `Model.one(primary_key)` or `Model.get(primary_key)` should be used to retrieve a single record
* Do not manage database sessions, these are managed by a custom tool
  * Use `TheModel(...).save()` to persist a record
  * Use `TheModel.where(...).order_by(...)` to query records. `.where()` returns a SQLAlchemy select object that you can further customize the query.
  * To iterate over the records, you'll need to end your query chain with `.all()` which returns an interator: `TheModel.where(...)...all()`
* Instead of repulling a record `order = HostScreeningOrder.one(order.id)` refresh it using `order.refresh()`

When writing database models:

* Don't use `Field(...)` unless required (i.e. when specifying a JSON type for a `dict` or pydantic model using `Field(sa_type=JSONB)`). For instance, use `= None` instead of `= Field(default=None)`.
* Add enum classes close to where they are used, unless they are used across multiple classes (then put them at the top of the file)
* Use `ModelName.foreign_key()` when generating a foreign key field
* Store currency as an integer, e.g. $1 = 100.
* `before_save`, `after_save(self):`, `after_updated(self):` are lifecycle methods (modelled after ActiveRecord) you can use.

Example:

```python
class Distribution(
    BaseModel, TimestampsMixin, SoftDeletionMixin, TypeIDMixin("dst"), table=True
):
    """Triple-quoted strings for multi-line class docstring"""

    date_field_with_comment: datetime | None = None
    "use a string under the field to add a comment about the field"

    # no need to add a comment about an obvious field; no need for line breaks if there are no field-level docstrings
    title: str = Field(unique=True)
    state: str

    optional_field: str | None = None

    # here's how relationships are constructed
    doctor_id: TypeIDType = Doctor.foreign_key()
    doctor: Doctor = Relationship()

    @computed_field
    @property
    def order_count(self) -> int:
        return self.where(Order.distribution_id == self.id).count()
```
