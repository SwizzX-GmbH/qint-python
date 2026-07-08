# Publishing `qint` to PyPI

The package is **not** auto-published from this repo — the PyPI token is held by
the SwizzX GmbH owner. These are the exact steps to cut a release.

## Prerequisites

- Maintainer of the `qint` project on [PyPI](https://pypi.org/project/qint/)
  (and, recommended, [TestPyPI](https://test.pypi.org/)).
- A PyPI API token, ideally as a `~/.pypirc` entry or exported per-shell.
- Build tooling:

  ```bash
  python -m pip install --upgrade build twine
  ```

## 1. Bump the version

Update the version in **two** places so they stay in sync:

- `pyproject.toml` → `[project].version`
- `src/qint/_version.py` → `__version__`

Follow SemVer. Commit the bump.

## 2. Build the distributions

```bash
rm -rf dist build ./*.egg-info
python -m build            # produces dist/qint-<version>.tar.gz and .whl
```

## 3. Check the artifacts

```bash
python -m twine check dist/*
```

Both the sdist and wheel must report `PASSED`. Optionally inspect contents:

```bash
tar -tzf dist/qint-*.tar.gz         # sdist should include LICENSE + src/qint
python -m zipfile -l dist/qint-*.whl # wheel should include qint/py.typed
```

## 4. (Recommended) Upload to TestPyPI first

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ qint
```

Smoke-test in a throwaway venv:

```bash
python -c "from qint import QintClient; print(QintClient('qk_live_x').base_url)"
```

## 5. Upload to PyPI

```bash
python -m twine upload dist/*
# Username: __token__
# Password: <your PyPI API token, incl. the pypi- prefix>
```

Or non-interactively:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-XXXX python -m twine upload dist/*
```

## 6. Verify

```bash
pip install qint==<version>
```

## 7. Tag & release on GitHub

The `v0.1.0` git tag is already pushed. For subsequent releases:

```bash
git tag v<version> && git push origin v<version>
gh release create v<version> --generate-notes
```

## Optional: automate via GitHub Actions (Trusted Publishing)

Configure PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
for `SwizzX-GmbH/qint-python`, then a `release`-triggered workflow using
`pypa/gh-action-pypi-publish` can publish with no long-lived token. The owner
must enable the trusted publisher on PyPI first.
