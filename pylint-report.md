# Pylint report

Tested with Pylint 4.1.3 (Python 3.14).

```sh
pylint .

------------------------------------
Your code has been rated at 10.00/10
```

## Disabled check

`config.py` turns off *too-few-public-methods* (R0903), they dont need public
methods as they are configs.
