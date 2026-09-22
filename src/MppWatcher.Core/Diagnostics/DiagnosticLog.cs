using System.Globalization;
using System.Text;

namespace MppWatcher.Core.Diagnostics;

public enum LogLevel { Debug, Info, Warning, Error }

/// <summary>
/// The watcher's own troubleshooting log (not activity events).
/// Written as plain text so an admin can read it in Notepad.
/// </summary>
public interface IDiagnosticLog
{
    void Write(LogLevel level, string source, string message, Exception? ex = null);
}

public static class DiagnosticLogExtensions
{
    public static void Debug(this IDiagnosticLog log, string source, string message) => log.Write(LogLevel.Debug, source, message);
    public static void Info(this IDiagnosticLog log, string source, string message) => log.Write(LogLevel.Info, source, message);
    public static void Warn(this IDiagnosticLog log, string source, string message, Exception? ex = null) => log.Write(LogLevel.Warning, source, message, ex);
    public static void Error(this IDiagnosticLog log, string source, string message, Exception? ex = null) => log.Write(LogLevel.Error, source, message, ex);
}

public sealed class NullDiagnosticLog : IDiagnosticLog
{
    public static readonly NullDiagnosticLog Instance = new();
    public void Write(LogLevel level, string source, string message, Exception? ex = null) { }
}

/// <summary>Keeps log lines in memory. Used by tests.</summary>
public sealed class MemoryDiagnosticLog : IDiagnosticLog
{
    private readonly List<string> _lines = new();
    public IReadOnlyList<string> Lines { get { lock (_lines) return _lines.ToList(); } }

    public void Write(LogLevel level, string source, string message, Exception? ex = null)
    {
        lock (_lines) _lines.Add($"{level} [{source}] {message}{(ex is null ? "" : " :: " + ex.Message)}");
    }
}

/// <summary>
/// Daily rolling text log: diagnostics-YYYY-MM-DD.log. Thread-safe. Never throws:
/// a broken log must not stop the watcher.
/// </summary>
public sealed class FileDiagnosticLog : IDiagnosticLog
{
    private readonly string _folder;
    private readonly Func<bool> _debugEnabled;
    private readonly object _gate = new();

    public FileDiagnosticLog(string folder, Func<bool> debugEnabled)
    {
        _folder = folder;
        _debugEnabled = debugEnabled;
        try { Directory.CreateDirectory(folder); } catch { /* reported on first write */ }
    }

    public string CurrentFilePath => Path.Combine(_folder, $"diagnostics-{DateTime.Now:yyyy-MM-dd}.log");

    public void Write(LogLevel level, string source, string message, Exception? ex = null)
    {
        if (level == LogLevel.Debug && !_debugEnabled()) return;
        var sb = new StringBuilder()
            .Append(DateTimeOffset.Now.ToString("yyyy-MM-dd HH:mm:ss.fff zzz", CultureInfo.InvariantCulture))
            .Append(' ').Append(level.ToString().ToUpperInvariant().PadRight(7))
            .Append(" [").Append(source).Append("] ").Append(message);
        if (ex is not null) sb.AppendLine().Append("    ").Append(ex.ToString().Replace("\n", "\n    "));
        sb.AppendLine();
        try
        {
            lock (_gate) File.AppendAllText(CurrentFilePath, sb.ToString());
        }
        catch
        {
            // Nothing sensible to do; logging must never crash the watcher.
        }
    }

    /// <summary>Deletes diagnostic logs older than the given number of days.</summary>
    public void DeleteOlderThan(int days)
    {
        if (days <= 0) return;
        try
        {
            foreach (var file in Directory.EnumerateFiles(_folder, "diagnostics-*.log"))
            {
                if (File.GetLastWriteTimeUtc(file) < DateTime.UtcNow.AddDays(-days)) File.Delete(file);
            }
        }
        catch (Exception e)
        {
            Write(LogLevel.Warning, "log", "Could not clean old diagnostic logs", e);
        }
    }
}
