using Microsoft.Data.Sqlite;
using MppWatcher.Core.Events;

namespace MppWatcher.Core.Storage;

/// <summary>
/// SQLite store (WAL mode, so the live viewer can read while the watcher writes).
/// The full event is kept as JSON; a few columns are copied out for fast queries.
/// </summary>
public sealed class SqliteEventStore : IEventStore
{
    public const int SchemaVersion = 1;

    private const int StatusPending = 0;
    private const int StatusUploaded = 1;

    private readonly SqliteConnection _conn;
    private readonly string _fallbackFolder;
    private readonly object _gate = new();

    public SqliteEventStore(string databasePath, string fallbackFolder, bool readOnly = false)
    {
        DatabasePath = databasePath;
        _fallbackFolder = fallbackFolder;
        if (!readOnly) Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(databasePath))!);
        var cs = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = readOnly ? SqliteOpenMode.ReadWrite : SqliteOpenMode.ReadWriteCreate,
            Cache = SqliteCacheMode.Private,
            Pooling = false,
        }.ToString();
        _conn = new SqliteConnection(cs);
        _conn.Open();
        Exec("PRAGMA busy_timeout = 5000;");
        if (!readOnly)
        {
            Exec("PRAGMA journal_mode = WAL;");
            Exec("PRAGMA synchronous = NORMAL;");
            CreateSchema();
        }
    }

    public string DatabasePath { get; }

    private void CreateSchema()
    {
        Exec("""
            CREATE TABLE IF NOT EXISTS events (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id                TEXT NOT NULL UNIQUE,
                timestamp_utc           TEXT NOT NULL,
                event_type              TEXT NOT NULL,
                session_id              TEXT,
                application             TEXT,
                json                    TEXT NOT NULL,
                upload_status           INTEGER NOT NULL DEFAULT 0,
                retry_count             INTEGER NOT NULL DEFAULT 0,
                last_upload_attempt_utc TEXT,
                uploaded_at_utc         TEXT,
                last_upload_error       TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_events_upload ON events(upload_status, id);
            CREATE INDEX IF NOT EXISTS ix_events_time ON events(timestamp_utc);
            CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            """);
        Exec($"INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '{SchemaVersion}');");
    }

    public void Append(IReadOnlyList<WatchEvent> events)
    {
        if (events.Count == 0) return;
        lock (_gate)
        {
            using var tx = _conn.BeginTransaction();
            using var cmd = _conn.CreateCommand();
            cmd.Transaction = tx;
            cmd.CommandText = """
                INSERT OR IGNORE INTO events(event_id, timestamp_utc, event_type, session_id, application, json)
                VALUES ($id, $ts, $type, $session, $app, $json);
                """;
            var pId = cmd.Parameters.Add("$id", SqliteType.Text);
            var pTs = cmd.Parameters.Add("$ts", SqliteType.Text);
            var pType = cmd.Parameters.Add("$type", SqliteType.Text);
            var pSession = cmd.Parameters.Add("$session", SqliteType.Text);
            var pApp = cmd.Parameters.Add("$app", SqliteType.Text);
            var pJson = cmd.Parameters.Add("$json", SqliteType.Text);
            foreach (var e in events)
            {
                pId.Value = e.EventId;
                pTs.Value = TimeFormat.IsoUtc(e.TimestampUtc);
                pType.Value = e.EventType;
                pSession.Value = (object?)e.SessionId ?? DBNull.Value;
                pApp.Value = (object?)e.Application ?? DBNull.Value;
                pJson.Value = EventJson.Serialize(e);
                cmd.ExecuteNonQuery();
            }
            tx.Commit();
        }
    }

    public IReadOnlyList<StoredEvent> GetPending(int limit) =>
        Query("SELECT id, json, retry_count FROM events WHERE upload_status = 0 ORDER BY id LIMIT $limit;", ("$limit", limit));

    public IReadOnlyList<StoredEvent> ReadAfter(long afterRowId, int limit) =>
        Query("SELECT id, json, retry_count FROM events WHERE id > $after ORDER BY id LIMIT $limit;", ("$after", afterRowId), ("$limit", limit));

    /// <summary>Most recent rows (newest last). Used by the viewer on open.</summary>
    public IReadOnlyList<StoredEvent> ReadLatest(int count) =>
        Query("SELECT id, json, retry_count FROM (SELECT id, json, retry_count FROM events ORDER BY id DESC LIMIT $n) ORDER BY id;", ("$n", count));

    public void MarkUploaded(IEnumerable<long> rowIds, DateTimeOffset when) =>
        UpdateRows(rowIds, "UPDATE events SET upload_status = 1, uploaded_at_utc = $when, last_upload_attempt_utc = $when, last_upload_error = NULL WHERE id = $id;", when, null);

    public void MarkUploadFailed(IEnumerable<long> rowIds, DateTimeOffset when, string error) =>
        UpdateRows(rowIds, "UPDATE events SET retry_count = retry_count + 1, last_upload_attempt_utc = $when, last_upload_error = $err WHERE id = $id;", when, error);

    public int DeleteUploadedBefore(DateTimeOffset cutoff)
    {
        lock (_gate)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = "DELETE FROM events WHERE upload_status = 1 AND timestamp_utc < $cutoff;";
            cmd.Parameters.AddWithValue("$cutoff", TimeFormat.IsoUtc(cutoff));
            return cmd.ExecuteNonQuery();
        }
    }

    public StoreStats GetStats()
    {
        lock (_gate)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = """
                SELECT COUNT(*),
                       COALESCE(SUM(CASE WHEN upload_status = 0 THEN 1 ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN upload_status = 1 THEN 1 ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN upload_status = 0 AND retry_count > 0 THEN 1 ELSE 0 END), 0),
                       (SELECT MIN(timestamp_utc) FROM events WHERE upload_status = 0)
                FROM events;
                """;
            using var r = cmd.ExecuteReader();
            r.Read();
            return new StoreStats(r.GetInt64(0), r.GetInt64(1), r.GetInt64(2), r.GetInt64(3), r.IsDBNull(4) ? null : r.GetString(4));
        }
    }

    public void WriteFallback(IReadOnlyList<WatchEvent> events)
    {
        try
        {
            Directory.CreateDirectory(_fallbackFolder);
            var file = Path.Combine(_fallbackFolder, $"pending-{DateTime.UtcNow:yyyyMMdd}.jsonl");
            File.AppendAllLines(file, events.Select(EventJson.Serialize));
        }
        catch
        {
            // Disk completely unusable; nothing more can be done here. The pipeline counts these.
        }
    }

    public int ImportFallback()
    {
        if (!Directory.Exists(_fallbackFolder)) return 0;
        var imported = 0;
        foreach (var file in Directory.GetFiles(_fallbackFolder, "pending-*.jsonl").OrderBy(f => f, StringComparer.Ordinal))
        {
            var events = new List<WatchEvent>();
            foreach (var line in File.ReadLines(file))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                try { events.Add(EventJson.Deserialize(line)); } catch { /* skip a torn last line */ }
            }
            Append(events); // INSERT OR IGNORE makes a repeated import harmless
            imported += events.Count;
            File.Delete(file);
        }
        return imported;
    }

    private IReadOnlyList<StoredEvent> Query(string sql, params (string Name, object Value)[] args)
    {
        lock (_gate)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = sql;
            foreach (var (n, v) in args) cmd.Parameters.AddWithValue(n, v);
            using var r = cmd.ExecuteReader();
            var list = new List<StoredEvent>();
            while (r.Read()) list.Add(new StoredEvent(r.GetInt64(0), EventJson.Deserialize(r.GetString(1)), r.GetInt32(2)));
            return list;
        }
    }

    private void UpdateRows(IEnumerable<long> rowIds, string sql, DateTimeOffset when, string? error)
    {
        lock (_gate)
        {
            using var tx = _conn.BeginTransaction();
            using var cmd = _conn.CreateCommand();
            cmd.Transaction = tx;
            cmd.CommandText = sql;
            var pId = cmd.Parameters.Add("$id", SqliteType.Integer);
            cmd.Parameters.AddWithValue("$when", TimeFormat.IsoUtc(when));
            if (error is not null) cmd.Parameters.AddWithValue("$err", error.Length > 500 ? error[..500] : error);
            foreach (var id in rowIds)
            {
                pId.Value = id;
                cmd.ExecuteNonQuery();
            }
            tx.Commit();
        }
    }

    private void Exec(string sql)
    {
        using var cmd = _conn.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    public void Dispose()
    {
        lock (_gate)
        {
            try
            {
                // Fold the WAL back into the main file so a copied .db is complete.
                using var cmd = _conn.CreateCommand();
                cmd.CommandText = "PRAGMA wal_checkpoint(TRUNCATE);";
                cmd.ExecuteNonQuery();
            }
            catch { /* read-only or busy: fine */ }
            _conn.Dispose();
        }
    }
}
