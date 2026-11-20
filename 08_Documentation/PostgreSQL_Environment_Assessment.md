# PostgreSQL environment assessment

**P002 Phase 2, Task 004 · 2026-11-19**

Use Ubuntu's native ARM64 PostgreSQL 18 packages in WSL2. The cached package plan resolves successfully, and the observed resources are adequate for P002's 249,231 visits. Confirm host service and port status in an ordinary WSL terminal before installation.

## Environment and availability

| Check | Observation |
|---|---|
| Distribution | Ubuntu 26.04.1 LTS (Resolute Raccoon) |
| Kernel and architecture | `6.18.58.1-microsoft-standard-WSL2`, kernel `aarch64`, dpkg `arm64` |
| Resources | 8 logical CPUs, 7.5 GiB RAM with 6.8 GiB available at inspection, 2.0 GiB swap. The Linux volume had 952 GiB available for the project and `/var/lib`. |
| Service configuration | `/etc/wsl.conf` enables systemd. PID 1 in this session appeared as `codex`. `systemctl` could not access the system bus and `ss` could not open a netlink socket. |
| Installed tools | `postgres`, `psql`, `pg_config`, and `pg_lsclusters` were absent from PATH. dpkg showed no installed PostgreSQL or libpq packages. |
| Server and client APT candidates | The `postgresql` and `postgresql-client` metapackages resolve to `postgresql-18` and `postgresql-client-18`. The versioned ARM64 candidates are `18.6-0ubuntu0.26.04.1` from the Ubuntu updates and security pockets. |
| Cluster tools and build headers | `postgresql-common` candidate `290ubuntu1` supplies `pg_lsclusters`. Ubuntu's `libpq-dev` candidate `18.6-0ubuntu0.26.04.1` provides `pg_config` for native builds. Add it only if a later dependency needs it. |
| Package simulation | `apt-get -s install postgresql postgresql-client` resolved from cached indexes. Archive hostname resolution returned no addresses in this session, so package downloads remain unverified. |

## Existing services and preservation

The visible process list contained no `postgres` or `postmaster`, and no PostgreSQL units were found in the inspected unit-file directories. Standard configuration, data, binaries, and runtime directories were absent at `/etc/postgresql`, `/var/lib/postgresql`, `/usr/lib/postgresql`, and `/run/postgresql`. No existing database was identified in the inspected WSL locations. The sandbox prevents a complete listener and service inventory. Windows services, other WSL distributions, and nonstandard cluster locations were outside the verified inventory.

Before installing from a normal WSL terminal, confirm service state and whether TCP port 5432 is occupied. If any cluster is discovered, inventory its version, databases, and owner and preserve its configuration and data. Choose a separate port for a new cluster if the existing listener conflicts.

## Recommended installation in a later task

In a normal Ubuntu WSL2 session with administrator access and working Ubuntu archive connectivity, refresh package indexes and install the distribution's supported server and client.

```bash
sudo apt update
sudo apt install postgresql postgresql-client
```

Ubuntu's packaged setup provides native ARM64 binaries, Ubuntu security updates, and standard cluster management. Package installation may create and start a default cluster. After installation, use `pg_lsclusters` to identify the created or existing cluster, `psql --version` to confirm the client, and `pg_isready` against the identified local port. Establish service health before provisioning P002.

## Proposed P002 isolation and access

- **Database** `p002_last_mile`, separate from other projects. Use dedicated schemas for staging, core tables, and reporting.
- **Development login** `p002_dev`, the owner of the project schemas. The database is owned by the separate non-login role `p002_owner`. Grant the development login connection and temporary-table access in P002. Keep cluster-wide superuser, role creation, database creation, and replication privileges disabled. Reserve cluster administration for the local PostgreSQL administrator.
- **Reporting login** `p002_report`, if a dashboard connects directly. Grant connection to P002, usage of the reporting schema, and select on approved reporting views. Remove broad default database/schema grants as needed and verify this login cannot read staging or write data.
- **Connection** Use loopback TCP from WSL for SQL and future Python clients, with database name and role supplied explicitly. Keep listeners local and use SCRAM password authentication for project logins. Use an interactive password prompt or a private user-owned `~/.pgpass` with mode `0600` outside the repository. Confirm the selected port before using this example.

```bash
psql -h 127.0.0.1 -p 5432 -U p002_dev -d p002_last_mile
```

The SQL model and load design are in the [implementation plan](PostgreSQL_Implementation_Plan.md). Baseline counts and QA evidence are available in the [copied feasibility report](../05_Quality_Assurance/Phase_0_Evidence/P002_Dataset_Feasibility_Report.md) and [companion audit script](../05_Quality_Assurance/Phase_0_Evidence/audit_workbook.py).

## Task 005 installation and verification · 2026-11-19

**Initial Task 005 attempt was blocked before installation.** The session runs as UID 1000 and `sudo -n -l` reported that the `no new privileges` flag prevents elevation. HTTP HEAD requests to the configured Ubuntu archive and security repository also failed at hostname resolution. No packages were installed or services changed.

| Check | Result |
|---|---|
| WSL2 and systemd | The ARM64 WSL2 kernel remains visible and `/etc/wsl.conf` enables systemd. PID 1 appears as `codex` in this session. `systemctl is-system-running` and the PostgreSQL unit listing failed with system-bus access denied. |
| TCP 5432 | `ss` failed with netlink access denied. No listening entry for 5432 appeared in the visible `/proc/net/tcp` or `/proc/net/tcp6` tables. Host WSL listener status remains unverified. |
| Existing clusters | No PostgreSQL process, `pg_lsclusters`, or standard configuration, data, runtime, or binary directory was visible. A host-level cluster inventory remains pending. |
| Package versions | The cached Ubuntu ARM64 candidate for both `postgresql-18` and `postgresql-client-18` is `18.6-0ubuntu0.26.04.1`. The release pocket also lists `18.3-1`. The cached `apt-get -s install postgresql-18 postgresql-client-18` simulation resolved 16 new packages and zero removals. |
| Client, cluster and SQL checks | `psql` remains absent. Cluster status, `SELECT version();`, `SELECT 1;`, and the effective listener configuration could not be verified. |

### Commands for an ordinary Ubuntu WSL terminal

Check service availability, cluster inventory, and port occupancy. Proceed with the installation block only if the service manager is reachable, port 5432 is free, and the inventory shows no existing cluster requiring preservation. The conditional cluster listing is skipped if its tool is absent.

```bash
ps -p 1 -o comm=
systemctl is-system-running
sudo ss -ltnp 'sport = :5432'
if command -v pg_lsclusters >/dev/null; then sudo pg_lsclusters; fi
sudo ls -ld /etc/postgresql /var/lib/postgresql /usr/lib/postgresql /run/postgresql
```

Missing standard directories are expected on a fresh installation. Refresh APT indexes, verify Ubuntu is the source of both candidates, then install the versioned server and client.

```bash
sudo apt-get update --error-on=any &&
apt-cache policy postgresql-18 postgresql-client-18
# After confirming the update succeeded and both candidates are from Ubuntu:
sudo apt-get install postgresql-18 postgresql-client-18
```

Check the installed client and cluster. If the newly installed `18/main` cluster exists and is down, inspect its configured TCP scope before starting it. A configured `localhost` or loopback-only address list is expected. An empty setting indicates Unix-socket-only access. Investigate any other address before starting. The command below assumes Ubuntu's standard `18/main` paths.

```bash
psql --version
sudo pg_lsclusters
# Only if 18/main exists and is down:
sudo -u postgres /usr/lib/postgresql/18/bin/postgres \
  -D /var/lib/postgresql/18/main \
  -c config_file=/etc/postgresql/18/main/postgresql.conf -C listen_addresses
# After confirming the configured scope is local:
sudo pg_ctlcluster 18 main start
```

Verify the online cluster, local socket access as the `postgres` system user, both SQL results, and the effective bind configuration. These commands assume the cluster uses port 5432. If `pg_lsclusters` reports another port, use that port for each check.

```bash
sudo pg_lsclusters
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -h /var/run/postgresql -p 5432 -d postgres \
  -c 'SELECT version();' -c 'SELECT 1;' -c 'SHOW listen_addresses;'
sudo ss -ltnp 'sport = :5432'
```

Expect the PostgreSQL 18 server version and a single value of `1`. Local-only TCP verification requires PostgreSQL listeners to be limited to `127.0.0.1` and/or `::1`. A Unix-socket-only instance has no PostgreSQL TCP listener. Wildcard or non-loopback binds fail verification. Keep WSL port forwarding and external exposure out of this setup. The checks use the existing `postgres` maintenance database.

## Task 005 completion and Task 006 session recheck · 2026-11-19

The user completed installation in the normal Ubuntu WSL terminal and reported PostgreSQL 18.6, cluster `18/main` online, successful `SELECT version();` and `SELECT 1;`, `listen_addresses = localhost`, and TCP listening at `127.0.0.1:5432`. This confirms the requested loopback bind in the user's WSL terminal. The checks above document the earlier restricted-session attempt.

This session independently verified `psql (PostgreSQL) 18.6 (Ubuntu 18.6-0ubuntu0.26.04.1)` and the presence of the `18/main` cluster record and socket path. Its own `pg_lsclusters` displayed `down` with owner `nobody`. The socket connection returned `Operation not permitted` and sudo remained blocked by `no new privileges`. The restricted view cannot confirm the current host cluster state. Follow the [P002 provisioning runbook](PostgreSQL_Database_Provisioning.md) from the normal WSL terminal.
