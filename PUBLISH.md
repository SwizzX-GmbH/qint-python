# Publishing the Qint Python SDK to PyPI

> ## ⛔ Blocked: the name `qint` is taken on PyPI
>
> **Verified 2026-09-15.** <https://pypi.org/project/qint/> is **not ours**. It is
> `qint` **0.2.0**, *"Quantized Integer type in Python!"*, published by **Neural
> Dynamics** — an unrelated project.
>
> **Do not request maintainer access to it, and do not try to upload to it.** An
> earlier version of this file said the prerequisite was being "maintainer of the
> `qint` project on PyPI". That was wrong: it pointed at a stranger's package.
>
> This is **not** a missing-token problem. The distribution has to be **renamed**
> before anything can be published. `qint-sdk` and `qint-payments` were both
> confirmed available on 2026-09-15.
>
> **Blocked on decision NEW-1** — see `qint-api/docs/GO-LIVE.md`, blocker P1-3.
> Until that decision is made, the release steps below cannot be run.

Until then, the SDK installs from git:

```bash
pip install "git+https://github.com/SwizzX-GmbH/qint-python.git@v0.1.0"
```

The **import** name stays `qint` either way (`from qint import QintClient`) — only
the distribution name on PyPI changes. Below, `<dist-name>` is whatever NEW-1
settles on.

## Once NEW-1 is decided — rename first

Change the distribution name in every place it appears, in one commit:

- `pyproject.toml` → `[project].name`
- `README.md` → the `pip install` line
- this file
- any CI workflow that references the distribution

Re-check availability immediately before uploading — an available name can be taken
by anyone at any time:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/<dist-name>/json
# 404 = still free, 200 = taken, pick another
```

## Prerequisites

- A PyPI account that will **own the newly created** `<dist-name>` project. The
  first upload creates the project and makes that account its owner.
- A PyPI API token (scoped to the project after first upload), ideally as a
  `~/.pypirc` entry or exported per-shell.
- Build tooling:

  ```bash
  python -m pip install --upgrade build twine
  ```

## 1. Bump the version

Update the version in **two** places so they stay in sync:

- `pyproject.toml` → `[project].version`
- `src/qint/_version.py` → `__version__`

Follow SemVer. Commit the bump.

> v0.1.0 carries the **breaking** required-`idempotencyKey` change relative to
> earlier drafts. Whatever version ships first, say so in the release notes.

## 2. Build the distributions

```bash
rm -rf dist build ./*.egg-info
python -m build            # produces dist/<dist-name>-<version>.tar.gz and .whl
```

## 3. Check the artifacts

```bash
python -m twine check dist/*
```

Both the sdist and wheel must report `PASSED`. Optionally inspect contents:

```bash
tar -tzf dist/*.tar.gz          # sdist should include LICENSE + src/qint
python -m zipfile -l dist/*.whl # wheel should include qint/py.typed
```

## 4. (Recommended) Upload to TestPyPI first

TestPyPI is a separate index with its own namespace — confirm the name is free
there too.

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ <dist-name>
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
pip install <dist-name>==<version>
python -c "from qint import QintClient; print(QintClient('qk_live_x').base_url)"
```

Confirm the PyPI project page shows **SwizzX GmbH** as owner and links to
`SwizzX-GmbH/qint-python` — not to any pre-existing project.

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
must enable the trusted publisher on PyPI first — and the project must exist
under the renamed distribution before that can be configured.
