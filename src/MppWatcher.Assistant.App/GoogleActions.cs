using System.Net.Http;
using System.Text;
using System.Text.Json.Nodes;
using Google.Apis.Auth.OAuth2;
using Google.Apis.Calendar.v3;
using Google.Apis.Calendar.v3.Data;
using Google.Apis.Services;
using Google.Apis.Sheets.v4;
using Google.Apis.Sheets.v4.Data;
using MppWatcher.Assistant;

namespace MppWatcher.Assistant.App;

/// <summary>
/// The account-connected actions. Writes a recommendation to Dalia's "AI MT LOG RECS" tab and adds a
/// Google Calendar reminder — using a Google credentials file (service account JSON) pointed to by the
/// GOOGLE_APPLICATION_CREDENTIALS env var or %LOCALAPPDATA%\MT Log\google-credentials.json. If no creds
/// are present or a call fails, these return false and the caller falls back to opening the link / copying.
/// Share the sheet and the calendar with the service account's email so it can write.
/// </summary>
internal static class GoogleActions
{
    // Override these without a rebuild via env vars MPP_TRACKER_SHEET_ID and MPP_TRACKER_TAB.
    private static string TrackerSheetId =>
        Environment.GetEnvironmentVariable("MPP_TRACKER_SHEET_ID") is { Length: > 0 } s
            ? s : "1nGa74uHh2yhcNdsSgtldylfhL2d7yxhzzYlwvEGPfvw";
    private static string RecsTab =>
        Environment.GetEnvironmentVariable("MPP_TRACKER_TAB") is { Length: > 0 } t ? t : "AI MT LOG RECS";

    public static string? CredentialsPath()
    {
        var env = Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS");
        if (!string.IsNullOrWhiteSpace(env) && File.Exists(env)) return env;
        var local = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MT Log", "google-credentials.json");
        return File.Exists(local) ? local : null;
    }

    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(15) };

    /// <summary>
    /// Append [when, title, why, urgency] to the tracker. Simplest path (no Google Cloud / service
    /// account): set MPP_TRACKER_WEBHOOK_URL to a Google Apps Script Web App that appends the row.
    /// Falls back to the Sheets API (service-account creds) if the webhook isn't set. Returns false so
    /// the caller can open/copy instead.
    /// </summary>
    public static bool TryAddToTracker(Recommendation rec)
    {
        var hook = Environment.GetEnvironmentVariable("MPP_TRACKER_WEBHOOK_URL");
        if (!string.IsNullOrWhiteSpace(hook))
        {
            try { return PostToWebhook(hook!, rec); } catch { /* fall through to Sheets API / caller fallback */ }
        }

        var path = CredentialsPath();
        if (path is null) return false;
        try
        {
            var credential = GoogleCredential.FromFile(path).CreateScoped(SheetsService.Scope.Spreadsheets);
            using var svc = new SheetsService(new BaseClientService.Initializer
            {
                HttpClientInitializer = credential,
                ApplicationName = "MPP Assistant",
            });
            var body = new ValueRange
            {
                Values = new List<IList<object>> { new List<object> { DateTime.Now.ToString("yyyy-MM-dd HH:mm"), rec.Title, rec.Why } },
            };
            var req = svc.Spreadsheets.Values.Append(body, TrackerSheetId, $"'{RecsTab}'!A:C");
            req.ValueInputOption = SpreadsheetsResource.ValuesResource.AppendRequest.ValueInputOptionEnum.USERENTERED;
            req.Execute();
            return true;
        }
        catch { return false; }
    }

    /// <summary>POST the recommendation as JSON to an Apps Script Web App that appends it to the sheet.</summary>
    private static bool PostToWebhook(string url, Recommendation rec)
    {
        var payload = new JsonObject
        {
            ["time"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm"),
            ["title"] = rec.Title,
            ["why"] = rec.Why,
            ["urgency"] = rec.Urgency,
        }.ToJsonString();
        using var content = new StringContent(payload, Encoding.UTF8, "application/json");
        var resp = Http.PostAsync(url, content).GetAwaiter().GetResult();
        return resp.IsSuccessStatusCode;
    }

    /// <summary>Create a short calendar event ~1 hour out. Returns false to let the caller fall back.</summary>
    public static bool TryAddReminder(Recommendation rec)
    {
        var path = CredentialsPath();
        if (path is null) return false;
        try
        {
            var credential = GoogleCredential.FromFile(path).CreateScoped(CalendarService.Scope.Calendar);
            using var svc = new CalendarService(new BaseClientService.Initializer
            {
                HttpClientInitializer = credential,
                ApplicationName = "MPP Assistant",
            });
            var start = DateTimeOffset.Now.AddHours(1);
            var ev = new Event
            {
                Summary = rec.Title,
                Description = rec.Why,
                Start = new EventDateTime { DateTimeDateTimeOffset = start },
                End = new EventDateTime { DateTimeDateTimeOffset = start.AddMinutes(15) },
            };
            svc.Events.Insert(ev, "primary").Execute();
            return true;
        }
        catch { return false; }
    }
}
