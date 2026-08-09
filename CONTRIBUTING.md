# Contributing

Keep contributions deterministic, local, and non-executing. Do not add provider
credentials, endpoints, shell commands, automatic fallback, retries, recursive
invocation, or background runners. Add tests for every change to selection or
approval semantics.

Run the complete suite from an environment installed with the test extra:

```sh
python3 -m pip install -e '.[test]'
python3 -m unittest discover -s tests -v
```
