using System.Text.RegularExpressions;

namespace MppWatcher.Core.Privacy;

/// <summary>What is known about a UI field. Filled from Windows UI Automation in Phase 2.</summary>
public sealed record FieldDescriptor(
    string? Name = null,
    string? AutomationId = null,
    string? LabelText = null,
    string? ControlType = null,
    string? ClassName = null,
    string? HelpText = null,
    bool IsPassword = false,
    string? Value = null);

public sealed record SensitivityVerdict(bool IsSensitive, string? Reason);

/// <summary>
/// Decides whether a field must never be recorded. The built-in rules are ALWAYS on and
/// cannot be removed by configuration; config can only add more terms.
/// </summary>
public sealed class SensitiveFieldDetector
{
    /// <summary>Built-in terms. Matched as whole words / word parts in name, id, label and help text.</summary>
    public static readonly IReadOnlyList<string> BuiltInTerms = new[]
    {
        "password", "passwd", "pwd", "passcode", "passphrase", "pass phrase", "pin", "pin code",
        "secret", "security code", "security question", "security answer", "cvv", "cvc", "cvv2", "cid",
        "card number", "cardnumber", "credit card", "debit card", "cc number", "ccnum", "card no", "expiry", "expiration date", "exp date",
        "ssn", "social security", "tax id", "tin", "ein", "national id", "passport",
        "bank account", "account number", "routing number", "iban", "swift", "sort code", "bsb",
        "otp", "one-time code", "one time code", "verification code", "auth code", "authentication code", "2fa", "mfa", "totp",
        "token", "api key", "apikey", "access key", "private key", "client secret", "credential",
        "mother's maiden", "date of birth", "dob",
    };

    // Values that look like secrets even if the field label gives no hint.
    private static readonly Regex CardNumberLike = new(@"^(?:\d[ -]?){13,19}$", RegexOptions.Compiled);
    private static readonly Regex SsnLike = new(@"^\d{3}-\d{2}-\d{4}$", RegexOptions.Compiled);
    private static readonly Regex LongTokenLike = new(@"^(?:eyJ[\w-]+\.[\w-]+\.[\w-]+|[A-Za-z0-9_\-]{40,})$", RegexOptions.Compiled);

    private readonly IReadOnlyList<Regex> _termPatterns;

    public SensitiveFieldDetector(IEnumerable<string>? extraTerms = null)
    {
        _termPatterns = BuiltInTerms
            .Concat(extraTerms ?? Array.Empty<string>())
            .Where(t => !string.IsNullOrWhiteSpace(t))
            .Select(t => t.Trim().ToLowerInvariant())
            .Distinct()
            .Select(BuildTermRegex)
            .ToList();
    }

    public SensitivityVerdict Evaluate(FieldDescriptor field)
    {
        if (field.IsPassword) return new(true, "control is marked as password/protected");

        foreach (var (label, text) in new[]
                 {
                     ("name", field.Name), ("automation_id", field.AutomationId), ("label", field.LabelText),
                     ("help_text", field.HelpText), ("class_name", field.ClassName),
                 })
        {
            if (string.IsNullOrWhiteSpace(text)) continue;
            var normalized = SplitIdentifier(text);
            foreach (var p in _termPatterns)
            {
                if (p.IsMatch(normalized)) return new(true, $"{label} matches sensitive term '{p}'");
            }
        }

        if (!string.IsNullOrWhiteSpace(field.Value))
        {
            var v = field.Value.Trim();
            if (CardNumberLike.IsMatch(v) && LuhnValid(v)) return new(true, "value looks like a payment card number");
            if (SsnLike.IsMatch(v)) return new(true, "value looks like a social security number");
            if (LongTokenLike.IsMatch(v)) return new(true, "value looks like a token/key");
        }

        return new(false, null);
    }

    /// <summary>Turns "txtCardNumber" / "card_number" / "card-number" into "txt card number".</summary>
    internal static string SplitIdentifier(string text)
    {
        var spaced = Regex.Replace(text, "([a-z0-9])([A-Z])", "$1 $2");
        spaced = Regex.Replace(spaced, @"[_\-.:/\\\[\]()]+", " ");
        return " " + Regex.Replace(spaced.ToLowerInvariant(), @"\s+", " ").Trim() + " ";
    }

    private static Regex BuildTermRegex(string term)
    {
        // Word-boundary match so "pin" hits "PIN" and "Enter PIN" but not "shipping" or "spinner".
        var escaped = Regex.Escape(term).Replace(@"\ ", @"\s?");
        return new Regex($@"(?<![a-z]){escaped}(?![a-z])", RegexOptions.Compiled | RegexOptions.CultureInvariant);
    }

    private static bool LuhnValid(string digitsWithSeparators)
    {
        var digits = digitsWithSeparators.Where(char.IsDigit).Select(c => c - '0').ToArray();
        if (digits.Length < 13) return false;
        var sum = 0;
        for (var i = 0; i < digits.Length; i++)
        {
            var d = digits[digits.Length - 1 - i];
            if (i % 2 == 1) { d *= 2; if (d > 9) d -= 9; }
            sum += d;
        }
        return sum % 10 == 0;
    }
}
