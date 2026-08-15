from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .runtime import RuntimeManager
from .workspace import Workspace, WorkspaceError, now_iso, read_json, write_json


CACHE_SCHEMA = 2
CACHE_LIMIT_BYTES = 5 * 1024**3
TABLE_KEYS = {"Household": "HhId", "Vehicle": "VehId", "Worker": "WkrId", "Azone": "Azone", "Bzone": "Bzone", "Marea": "Marea"}


def _safe_table(variable: str) -> str:
    return "v_" + hashlib.sha256(variable.encode()).hexdigest()[:20]


class ComparisonCache:
    def __init__(self, workspace: Workspace, runtime: RuntimeManager, extractor: Path):
        self.workspace, self.runtime, self.extractor = workspace, runtime, extractor.resolve()
        self.root = workspace.exchange / "comparison-cache" / "v2"
        self.root.mkdir(parents=True, exist_ok=True)
        self.locks: dict[str, threading.RLock] = {}
        self.guard = threading.RLock()
        self.pinned: set[Path] = set()
        self.memory: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()

    def _record(self, root: Path) -> dict[str, Any]:
        resolved = root.resolve()
        record = next((item for item in self.workspace.catalog(False)["datastores"] if Path(item.get("path", "")).resolve() == resolved), None)
        return record or {"id": hashlib.sha256(str(resolved).encode()).hexdigest()[:16], "path": str(resolved)}

    @staticmethod
    def _stat(path: Path) -> str:
        if not path.is_file(): return "missing"
        stat = path.stat(); return f"{stat.st_size}:{stat.st_mtime_ns}"

    def _identity(self, root: Path, year: str, table: str) -> tuple[str, Path, dict[str, Any]]:
        record = self._record(root)
        registration = hashlib.sha256(json.dumps({k:v for k,v in record.items() if k != "path"}, sort_keys=True, default=str).encode()).hexdigest()
        token = hashlib.sha256(f"{record['id']}|{year}|{table}|{registration}".encode()).hexdigest()
        return token, self.root / f"{token}.sqlite", record

    def _lock(self, token: str) -> threading.RLock:
        with self.guard: return self.locks.setdefault(token, threading.RLock())

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=60)
        connection.execute("PRAGMA journal_mode=WAL"); connection.execute("PRAGMA synchronous=OFF")
        connection.execute("CREATE TABLE IF NOT EXISTS cache_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS cache_keys (row_index INTEGER PRIMARY KEY, entity_key TEXT NOT NULL UNIQUE)")
        connection.execute("CREATE TABLE IF NOT EXISTS cache_variables (name TEXT PRIMARY KEY, table_name TEXT NOT NULL, kind TEXT NOT NULL, source_fingerprint TEXT NOT NULL, cached_at TEXT NOT NULL)")
        return connection

    def _extract_command(self, root: Path, year: str, table: str, key: str, output: Path, variables: list[str]) -> tuple[list[str], dict[str, str]]:
        return self.runtime.r_command(self.extractor, str(root), year, table, key or "-", str(output), *variables)

    def ensure(self, root: Path, year: str, table: str, variables: list[str]) -> dict[str, Any]:
        variables = list(dict.fromkeys(item for item in variables if item))
        if not variables: return {"cacheHit": True, "extractionMs": 0.0, "importMs": 0.0}
        token, path, record = self._identity(root, year, table); key_name = TABLE_KEYS.get(table, "Region" if table == "Region" else "")
        with self._lock(token):
            connection = self._connect(path); self.pinned.add(path)
            try:
                expected_key = self._stat(root / year / table / f"{key_name}.Rda") if key_name and table != "Region" else f"synthetic:{table}"
                stored_key = connection.execute("SELECT value FROM cache_meta WHERE key='key_fingerprint'").fetchone()
                if stored_key and stored_key[0] != expected_key:
                    connection.close(); path.unlink(missing_ok=True); connection = self._connect(path); stored_key = None
                missing = []
                for variable in variables:
                    source = root / year / table / f"{variable}.Rda"; fingerprint = self._stat(source)
                    row = connection.execute("SELECT source_fingerprint FROM cache_variables WHERE name=?", (variable,)).fetchone()
                    if not row or row[0] != fingerprint: missing.append(variable)
                if not missing and stored_key:
                    connection.execute("INSERT OR REPLACE INTO cache_meta VALUES ('last_access',?)", (now_iso(),)); connection.commit()
                    return {"cacheHit": True, "extractionMs": 0.0, "importMs": 0.0, "path": path}
                staging = self.root / f"staging-{token[:12]}-{time.time_ns()}"; staging.mkdir()
                started = time.perf_counter()
                invocation = self._extract_command(root, year, table, key_name, staging, missing)
                command, environment = invocation if isinstance(invocation, tuple) else (invocation, None)
                result = subprocess.run(command, capture_output=True, text=True, env=environment)
                extraction_ms = (time.perf_counter()-started)*1000
                if result.returncode: raise WorkspaceError((result.stderr or result.stdout).strip() or "Comparison cache extraction failed")
                started = time.perf_counter()
                skipped: dict[str, str] = {}
                skipped_path = staging / "skipped.tsv"
                if skipped_path.is_file():
                    with skipped_path.open(encoding="utf-8", newline="") as handle:
                        skipped = {row["variable"]: row["reason"] for row in csv.DictReader(handle, delimiter="\t")}
                if not stored_key:
                    with (staging/"keys.tsv").open(encoding="utf-8", newline="") as handle:
                        reader=csv.DictReader(handle, delimiter="\t"); rows=[(int(row["row_index"]), row["entity_key"]) for row in reader]
                    connection.executemany("INSERT INTO cache_keys(row_index,entity_key) VALUES (?,?)", rows)
                    connection.execute("INSERT OR REPLACE INTO cache_meta VALUES ('key_fingerprint',?)", (expected_key,))
                key_count = connection.execute("SELECT COUNT(*) FROM cache_keys").fetchone()[0]
                for index, variable in enumerate(missing, 1):
                    table_name = _safe_table(variable); temporary = table_name + "_new"
                    connection.execute(f'DROP TABLE IF EXISTS "{temporary}"')
                    if variable in skipped:
                        continue
                    connection.execute(f'CREATE TABLE "{temporary}" (row_index INTEGER PRIMARY KEY, is_null INTEGER NOT NULL, numeric_value REAL, text_value TEXT, compare_value REAL)')
                    def records():
                        with (staging/f"column_{index}.tsv").open(encoding="utf-8", newline="") as handle:
                            for row in csv.DictReader(handle, delimiter="\t"):
                                yield (int(row["row_index"]), int(row["is_null"]), float(row["numeric_value"]) if row["numeric_value"] else None, row["text_value"] or None, float(row["compare_value"]) if row["compare_value"] else None)
                    connection.executemany(f'INSERT INTO "{temporary}" VALUES (?,?,?,?,?)', records())
                    if connection.execute(f'SELECT COUNT(*) FROM "{temporary}"').fetchone()[0] != key_count: raise WorkspaceError(f"Key/value length mismatch for {table}/{variable}")
                    connection.execute(f'DROP TABLE IF EXISTS "{table_name}"'); connection.execute(f'ALTER TABLE "{temporary}" RENAME TO "{table_name}"')
                    kind=(staging/f"column_{index}.kind").read_text().strip()
                    connection.execute("INSERT OR REPLACE INTO cache_variables VALUES (?,?,?,?,?)", (variable,table_name,kind,self._stat(root/year/table/f"{variable}.Rda"),now_iso()))
                for key,value in (("schema",str(CACHE_SCHEMA)),("datastore_id",str(record["id"])),("year",year),("table",table),("last_access",now_iso())): connection.execute("INSERT OR REPLACE INTO cache_meta VALUES (?,?)",(key,value))
                connection.commit(); import_ms=(time.perf_counter()-started)*1000
                self._write_manifest(path, connection); return {"cacheHit": False, "extractionMs": extraction_ms, "importMs": import_ms, "path": path, "skipped": skipped}
            except Exception:
                connection.rollback(); raise
            finally:
                connection.close(); self.pinned.discard(path)
                if 'staging' in locals(): shutil.rmtree(staging, ignore_errors=True)
                self.enforce_limit()

    def _write_manifest(self, path: Path, connection: sqlite3.Connection) -> None:
        meta=dict(connection.execute("SELECT key,value FROM cache_meta")); variables=[{"name":r[0],"table":r[1],"kind":r[2],"sourceFingerprint":r[3],"cachedAt":r[4]} for r in connection.execute("SELECT name,table_name,kind,source_fingerprint,cached_at FROM cache_variables")]
        write_json(path.with_suffix(".manifest.json"), {"schemaVersion":CACHE_SCHEMA,"database":path.name,"metadata":meta,"rowCount":connection.execute("SELECT COUNT(*) FROM cache_keys").fetchone()[0],"variables":variables})

    def column(self, root: Path, year: str, table: str, variable: str) -> dict[str, Any]:
        metrics=self.ensure(root,year,table,[variable]); path=metrics["path"]; connection=self._connect(path)
        try:
            row=connection.execute("SELECT table_name,kind FROM cache_variables WHERE name=?",(variable,)).fetchone()
            if not row:
                reason = (metrics.get("skipped") or {}).get(variable)
                raise WorkspaceError(reason or f"Missing cached variable {table}/{variable}")
            table_name,kind=row; values=[]; order=[]; mapped={}
            key_name=TABLE_KEYS.get(table, "")
            key_fingerprint=self._stat(root/year/table/f"{key_name}.Rda") if key_name else f"synthetic:{table}"
            memory_key=(str(path),variable,self._stat(root/year/table/f"{variable}.Rda")+"|"+key_fingerprint)
            if memory_key in self.memory:
                cached=self.memory.pop(memory_key); self.memory[memory_key]=cached
                return {**cached,"metrics":metrics}
            for key,numeric,text,is_null in connection.execute(f'SELECT k.entity_key,v.numeric_value,v.text_value,v.is_null FROM cache_keys k JOIN "{table_name}" v USING(row_index) ORDER BY k.row_index'):
                value=None if is_null else numeric if kind=="numeric" else text; order.append(key); values.append(value); mapped[key]=value
            cached={"keyName":TABLE_KEYS.get(table,"Region" if table=="Region" else "Row"),"order":order,"values":mapped,"list":values,"kind":kind}
            self.memory[memory_key]=cached
            while len(self.memory)>6: self.memory.popitem(last=False)
            return {**cached,"metrics":metrics}
        finally: connection.close()

    def report(self) -> dict[str, Any]:
        databases=list(self.root.glob("*.sqlite"))
        files=[path for path in self.root.rglob("*") if path.is_file()]
        return {"bytes":sum(path.stat().st_size for path in files),"entries":len(databases),"limitBytes":CACHE_LIMIT_BYTES}

    @staticmethod
    def _belongs_to_database(candidate: Path, database: Path) -> bool:
        return candidate == database or candidate.name.startswith(database.name + "-") or candidate == database.with_suffix(".manifest.json")

    def clear(self) -> dict[str, Any]:
        self.memory.clear()
        removed=0
        for path in list(self.root.glob("*")):
            if any(self._belongs_to_database(path, database) for database in self.pinned): continue
            if path.is_dir(): shutil.rmtree(path,ignore_errors=True)
            else: path.unlink(missing_ok=True)
            removed+=1
        return {"cleared":True,"removed":removed,**self.report()}

    def remove_datastore(self, datastore_id: str) -> dict[str, int]:
        """Remove only disposable cache files whose manifest names this datastore."""
        removed_files = 0
        removed_bytes = 0
        database_paths: list[Path] = []
        for manifest in self.root.glob("*.manifest.json"):
            payload = read_json(manifest, {})
            if str((payload.get("metadata") or {}).get("datastore_id", "")) != datastore_id:
                continue
            database = self.root / str(payload.get("database", ""))
            if database.is_file() and database not in self.pinned:
                database_paths.append(database)
        with self.guard:
            doomed = {str(path) for path in database_paths}
            self.memory = OrderedDict((key, value) for key, value in self.memory.items() if key[0] not in doomed)
        for database in database_paths:
            for candidate in list(self.root.glob("*")):
                if not candidate.is_file() or not self._belongs_to_database(candidate, database):
                    continue
                try:
                    removed_bytes += candidate.stat().st_size
                except OSError:
                    pass
                candidate.unlink(missing_ok=True)
                removed_files += 1
        return {"cacheFilesRemoved": removed_files, "cacheBytesRemoved": removed_bytes}

    def enforce_limit(self) -> None:
        summaries=list((self.root / "summaries").glob("*.json")) if (self.root / "summaries").is_dir() else []
        files=sorted([*(path for path in self.root.glob("*.sqlite") if path not in self.pinned), *summaries], key=lambda p:p.stat().st_atime_ns)
        total=self.report()["bytes"]
        for path in files:
            if total<=CACHE_LIMIT_BYTES: break
            if path.suffix == ".json":
                size=path.stat().st_size; path.unlink(missing_ok=True); total-=size; continue
            related=[candidate for candidate in self.root.glob("*") if candidate.is_file() and self._belongs_to_database(candidate,path)]
            size=sum(candidate.stat().st_size for candidate in related)
            for candidate in related: candidate.unlink(missing_ok=True)
            total-=size
