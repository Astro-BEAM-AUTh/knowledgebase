<!-- omit in toc -->
# Python Guidelines & Development Conventions

<!-- omit in toc -->
## Table of Contents
- [Tools](#tools)
- [Code Style](#code-style)


## Tools
- **Editor**: `VS Code`  or `PyCharm`
- **Dependency & Environment Management**: I suggest using `uv`, it is honestly the best tool for the job right now. It skips the need of `pip` , `pipenv` and `poetry` and combines virtual environment management, dependency management and packaging in a single tool. More info can be found [here](https://docs.astral.sh/uv/).
- **Linting & Formatting**: `uv` comes with built-in linting using `ruff`. Ruff is a blazing fast Python linter written in Rust. It supports a wide range of linting rules and is highly configurable. More info can be found [here](https://docs.astral.sh/ruff/).
> See also [this toml configuration file]()
<!-- TODO @dyka3773: Add a sample ruff.toml file for our project conventions -->

## Code Style
> I'm not gonna mention [PEP8](https://www.python.org/dev/peps/pep-0008/), it's a given and `ruff` enforces it anyway

Due to the fact that python is a loosely typed and multi-paradigm language, and has no strict rules regarding code structure, the following conventions are suggested to be followed in order to maintain code consistency across the organization:
- **Type Hints**: Use type hints as much as possible. If no type hint is possible, use `Any` from the `typing` module or try to create a custom type using whatever the current python version supports (e.g. `NewType` in python 3.10+). This will help with code readability and maintainability.
- **Documentation**: Use docstrings everywhere. IDK what the docstyle I use is called, but it's the same that comes by default with `ruff`:
```python
def my_function(param1: int, param2: str) -> int:
    """
    Brief description of the function.

    Args:
        param1 (int): Description of param1.
        param2 (str): Description of param2.

    Returns:
        int: Description of the return value.
    """
```
- **Importing**: Use absolute imports whenever possible. If relative imports are necessary, use explicit relative imports (e.g. `from .module import Class` instead of `from .. import module`). Also, import only what is necessary. Avoid using `from module import *`. This might lead to namespace pollution and make it harder to track where a specific function or class came from.
- **Classes vs Modules vs Functions**: This will be a bit subjective, but in general:
  1. If you want to describe a data structure with no logic to its attributes, use a `@dataclass`.
  2. If you want to describe a data structure that has some logic to its attributes, then use a regular `class` where the attributes with logic are defined as `@property`.
  3. If you want to describe a data structure with instance logic (i.e. methods that operate on the instance), then use a `@dataclass` and just add the methods to it.
  4. If you want to create a functionality that is not related to an instance of a class, then define a `function` in a module. **Unless** it is tightly coupled with a specific class, in which case it should be defined as a `@staticmethod` or `@classmethod` of that class.
- I consider static programming to be very readable, so I prefer having modules with many functions inside instead of useless classes that just wrap those functions as methods.
- In general, design patterns are mostly used in OOP languages like Java or C#, **but** I do believe that some of them can have adaptations in functional or imperative programming as well. So whenever you feel that a design pattern can help with code readability and maintainability, feel free to use it, but always keep in mind the pythonic way of doing things.
- Python lets you do quite a lot of "magic" with metaprogramming, decorators, and other advanced features. While these can be powerful tools, they can also make code harder to read and maintain. Use them sparingly, only when they provide a clear benefit and always document their usage thoroughly.