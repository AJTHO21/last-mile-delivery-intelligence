# Streamlit localhost smoke test

**Task 015 · Ubuntu WSL2 ARM64 · PostgreSQL 18.6**

Task 014's dashboard contract and live SQL QA passed per the handoff. The [smoke app](smoke_app.py) reads the `full` row from `reporting.dashboard_overview` as `p002_report`. It displays real query results and a generic error if the connection or overview validation fails. The [reader](dashboard_smoke_data.py) fixes PostgreSQL to IPv4 loopback, sets read-only transactions, and applies bounded connection and statement timeouts.

## Environment and dependencies

The session exposed Ubuntu WSL2 on `aarch64` and system CPython 3.14.4. The project-local `.venv` was created with pip 25.1.1. ARM64 `libpq.so.5` is installed. The pinned direct dependencies are Streamlit 1.67.0 and pure-Python Psycopg 3.3.9. Pure-Python Psycopg uses the installed system libpq. PyPI lists a CPython 3.14 Linux aarch64 wheel for PyArrow, a Streamlit dependency. Full resolver and import checks remain pending because this session could not resolve PyPI and installation could not fetch candidates. [Pinned dependencies](requirements-smoke.txt) · [Streamlit release](https://pypi.org/project/streamlit/1.67.0/) · [Psycopg release](https://pypi.org/project/psycopg/3.3.9/) · [ARM64 PyArrow wheels](https://pypi.org/project/pyarrow/26.0.1/)

## Install from a normal Ubuntu WSL terminal

```bash
# Run from the repository root.
test -x .venv/bin/python || python3 -m venv .venv
.venv/bin/python -m pip --isolated install --index-url https://pypi.org/simple \
  --only-binary=:all: -r 06_Dashboard/requirements-smoke.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import platform, streamlit, psycopg; print(platform.machine(), streamlit.__version__, psycopg.__version__, psycopg.pq.__impl__)'
```

Expect `aarch64`, `1.67.0`, `3.3.9` and `python` from the final command. Stop on any failure.

## Configure the local reporting credential

Create the private passfile outside the project. Edit it locally and substitute the existing reporting password for the placeholder. Escape a literal colon or backslash within the password with a preceding backslash. Preserve any existing entries.

```bash
install -d -m 700 "$HOME/.config/p002"
(umask 077; touch "$HOME/.config/p002/pgpass")
chmod 600 "$HOME/.config/p002/pgpass"
nano "$HOME/.config/p002/pgpass"
```

```text
127.0.0.1:5432:p002_last_mile:p002_report:<existing reporting password>
```

The app uses this user-private libpq passfile and the existing database role. Keep its contents out of terminal commands, Git, and shared logs. [PostgreSQL password file documentation](https://www.postgresql.org/docs/18/libpq-pgpass.html)

## Verify and launch

Run all four checks, including the live reporting query. An incomplete login or incompatible view shape fails the test.

```bash
# Run from the repository root.
env -u PGPASSWORD P002_SMOKE_LIVE=1 \
  .venv/bin/python -B 05_Quality_Assurance/Tests/test_dashboard_smoke.py -v
```

Start Streamlit from its config directory. The [config](.streamlit/config.toml) and explicit command bind it to IPv4 loopback and disable usage statistics.

```bash
# Start from the repository root.
cd 06_Dashboard
env -u PGPASSWORD ../.venv/bin/python -m streamlit run smoke_app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

From a second normal WSL terminal, check the listener and health endpoint.

```bash
ss -ltn 'sport = :8501'
curl --fail --silent --show-error http://127.0.0.1:8501/_stcore/health
```

The listener should be `127.0.0.1:8501` and the health endpoint should return `ok`. Open `http://127.0.0.1:8501` in the Windows browser. Confirm the green `PostgreSQL connected as p002_report` label, **19,647 routes**, **213,122 eligible deliveries**, **23,718 late deliveries**, and **11.13%** late-delivery rate. HTTP health alone checks the web listener. The green status and four cards verify the end-to-end query. Stop the process with Ctrl+C when finished. [WSL localhost networking](https://learn.microsoft.com/en-us/windows/wsl/networking)

## Observed QA

Three [offline tests](../05_Quality_Assurance/Tests/test_dashboard_smoke.py) passed. They checked the loopback reporting connection arguments, full-cohort query, exact KPI formatting, and failure on missing, duplicate, inconsistent, or unauthorized results. The opt-in live check was skipped. Python source parsing passed. The sandbox denied PostgreSQL Unix sockets, loopback TCP connections, and binding a local listener. Dependency installation, live authentication, and Windows browser verification remain pending in the normal WSL terminal.
