using MppWatcher.Core.Configuration;
using MppWatcher.Core.Events;
using MppWatcher.Core.Privacy;

namespace MppWatcher.Core.Tests;

public class SensitiveFieldDetectorTests
{
    private readonly SensitiveFieldDetector _detector = new(new[] { "wholesale price" });

    [Theory]
    [InlineData("Password")]
    [InlineData("Enter PIN")]
    [InlineData("CVV")]
    [InlineData("Card number")]
    [InlineData("Social Security Number")]
    [InlineData("Verification code")]
    [InlineData("Bank account number")]
    [InlineData("Routing number")]
    [InlineData("API key")]
    [InlineData("Wholesale price")] // extra term from config
    public void Sensitive_labels_are_blocked(string label) =>
        Assert.True(_detector.Evaluate(new FieldDescriptor(Name: label)).IsSensitive);

    [Theory]
    [InlineData("txtCardNumber")]
    [InlineData("user_password")]
    [InlineData("ap_password")]
    [InlineData("otp-input")]
    public void Sensitive_automation_ids_are_blocked(string id) =>
        Assert.True(_detector.Evaluate(new FieldDescriptor(AutomationId: id)).IsSensitive);

    [Theory]
    [InlineData("Search")]
    [InlineData("SKU")]
    [InlineData("Shipping address")]   // contains "pin" inside a word: must NOT match
    [InlineData("Product title")]
    [InlineData("Spinner")]
    [InlineData("Keywords")]
    public void Normal_business_fields_are_allowed(string label) =>
        Assert.False(_detector.Evaluate(new FieldDescriptor(Name: label, Value: "personalized stationery")).IsSensitive);

    [Fact]
    public void Password_flag_always_wins() =>
        Assert.True(_detector.Evaluate(new FieldDescriptor(Name: "Search", IsPassword: true)).IsSensitive);

    [Theory]
    [InlineData("4111 1111 1111 1111")]
    [InlineData("123-45-6789")]
    [InlineData("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk")]
    public void Secret_looking_values_are_blocked_even_with_harmless_label(string value) =>
        Assert.True(_detector.Evaluate(new FieldDescriptor(Name: "Notes", Value: value)).IsSensitive);

    [Fact]
    public void Sku_and_asin_values_are_not_mistaken_for_secrets()
    {
        Assert.False(_detector.Evaluate(new FieldDescriptor(Name: "Search", Value: "MA023")).IsSensitive);
        Assert.False(_detector.Evaluate(new FieldDescriptor(Name: "Search", Value: "B0CXYZ1234")).IsSensitive);
        Assert.False(_detector.Evaluate(new FieldDescriptor(Name: "Listing", Value: "1234567890")).IsSensitive);
    }

    [Fact]
    public void Config_cannot_remove_built_in_terms()
    {
        var d = new SensitiveFieldDetector(Array.Empty<string>());
        Assert.True(d.Evaluate(new FieldDescriptor(LabelText: "Password")).IsSensitive);
    }
}

public class UrlSanitizerTests
{
    private readonly UrlSanitizer _s = new();

    [Fact]
    public void Removes_token_parameters_and_keeps_business_parameters()
    {
        var r = _s.Sanitize("https://sellercentral.amazon.com/skucentral?mSku=MA023&session_id=abc&access_token=xyz&ref=nav")!;
        Assert.Equal("https://sellercentral.amazon.com/skucentral?mSku=MA023&ref=nav", r.Url);
        Assert.Equal("sellercentral.amazon.com", r.Domain);
        Assert.True(r.WasModified);
    }

    [Theory]
    [InlineData("https://www.amazon.com/dp/B0CXYZ1234/ref=sr_1_1?keywords=stationery&session-id=123-456", "https://www.amazon.com/dp/B0CXYZ1234/ref=sr_1_1?keywords=stationery")]
    [InlineData("https://example.com/p?sessionToken=abc&x_auth=1&userPassword=2&id=7", "https://example.com/p?id=7")]
    [InlineData("https://example.com/p?author=jane&sku=MA023", "https://example.com/p?sku=MA023")] // "author" contains "auth": dropped, harmless
    public void Parameter_names_containing_sensitive_words_are_removed(string raw, string expected) =>
        Assert.Equal(expected, _s.Sanitize(raw)!.Url);

    [Fact]
    public void Removes_credentials_and_oauth_fragments()
    {
        var r = _s.Sanitize("https://user:pw@example.com/cb#access_token=abc&state=1")!;
        Assert.Equal("https://example.com/cb", r.Url);
        Assert.True(r.WasModified);
    }

    [Fact]
    public void Keeps_keepa_style_fragments()
    {
        var r = _s.Sanitize("https://keepa.com/#!product/1-B0CXYZ1234")!;
        Assert.Equal("https://keepa.com/#!product/1-B0CXYZ1234", r.Url);
        Assert.False(r.WasModified);
    }

    [Fact]
    public void Adds_scheme_to_bare_address_bar_text_and_strips_www()
    {
        var r = _s.Sanitize("www.etsy.com/your/shops/me/tools/listings/123456789")!;
        Assert.Equal("https://www.etsy.com/your/shops/me/tools/listings/123456789", r.Url);
        Assert.Equal("etsy.com", r.Domain);
    }

    [Theory]
    [InlineData("personalized stationery")]
    [InlineData("file:///C:/secret.txt")]
    [InlineData("")]
    public void Non_web_text_returns_null(string text) => Assert.Null(_s.Sanitize(text));

    [Fact]
    public void Removes_amazon_signed_url_parameters()
    {
        var r = _s.Sanitize("https://bucket.s3.amazonaws.com/report.csv?X-Amz-Signature=abc&X-Amz-Credential=def&X-Amz-Date=1")!;
        Assert.Equal("https://bucket.s3.amazonaws.com/report.csv", r.Url);
    }

    [Fact]
    public void Extra_parameters_from_config_are_removed()
    {
        var r = new UrlSanitizer(new[] { "mons_sel_mkid" }).Sanitize("https://sellercentral.amazon.com/home?mons_sel_mkid=abc&x=1")!;
        Assert.Equal("https://sellercentral.amazon.com/home?x=1", r.Url);
    }
}

public class WildcardMatcherTests
{
    [Theory]
    [InlineData("KeePass", "KeePass*", true)]
    [InlineData("keepassxc", "KeePass*", true)]
    [InlineData("sellercentral.amazon.com", "*.amazon.com", true)]
    [InlineData("amazon.com", "*.amazon.com", false)]
    [InlineData("a.b", "a?b", true)]
    [InlineData("chrome", "", false)]
    public void Matches(string text, string pattern, bool expected) => Assert.Equal(expected, WildcardMatcher.IsMatch(text, pattern));
}

public class PrivacyFilterTests
{
    private readonly WatcherConfig _config = new();
    private PrivacyFilter Filter => new(() => _config);

    private static WatchEvent Session(string process, string title, string? url = null) => new WatchEvent
    {
        EventType = EventTypes.AppSessionEnd,
        ProcessName = process,
        Application = process,
        ProcessId = 5,
        WindowTitle = title,
        Url = url,
    }.Set("duration_seconds", 42.0).Set("executable_path", @"C:\x.exe").Set("end_reason", "foreground_changed");

    [Fact]
    public void Blocked_app_is_redacted_but_timing_is_kept()
    {
        var e = Filter.Apply(Session("KeePassXC.exe", "Database - KeePassXC"))!;
        Assert.Equal(PrivacyFilter.RedactedText, e.Application);
        Assert.Equal(PrivacyFilter.RedactedText, e.WindowTitle);
        Assert.Null(e.ProcessId);
        Assert.Equal(42.0, e.Metadata["duration_seconds"]!.GetValue<double>());
        Assert.Null(e.Metadata["executable_path"]);
        Assert.True(e.Metadata["excluded"]!.GetValue<bool>());
        Assert.Equal("blocked_application", e.Metadata["excluded_reason"]!.GetValue<string>());
    }

    [Fact]
    public void Drop_mode_removes_the_event()
    {
        _config.Privacy.BlockedMode = "drop";
        Assert.Null(Filter.Apply(Session("KeePass", "x")));
    }

    [Fact]
    public void Blocked_title_is_redacted()
    {
        _config.Privacy.BlockedWindowTitles.Add("*Payroll*");
        Assert.Equal(PrivacyFilter.RedactedText, Filter.Apply(Session("chrome", "Payroll - ADP"))!.WindowTitle);
    }

    [Fact]
    public void Url_is_sanitized_and_blocked_urls_are_redacted()
    {
        var kept = Filter.Apply(Session("chrome", "Keepa", "https://keepa.com/?token=abc"))!;
        Assert.Equal("https://keepa.com/", kept.Url);
        Assert.Equal("keepa.com", kept.Domain);
        Assert.True(kept.Metadata["url_sanitized"]!.GetValue<bool>());

        var blocked = Filter.Apply(Session("chrome", "Sign in", "https://www.amazon.com/ap/signin?x=1"))!;
        Assert.Null(blocked.Url);
        Assert.Equal("blocked_url", blocked.Metadata["excluded_reason"]!.GetValue<string>());
    }

    [Fact]
    public void Allowed_domain_list_redacts_everything_else()
    {
        _config.Privacy.AllowedDomains.AddRange(new[] { "amazon.com", "keepa.com" });
        Assert.Equal("https://sellercentral.amazon.com/inventory", Filter.Apply(Session("chrome", "Inventory", "https://sellercentral.amazon.com/inventory"))!.Url);
        var other = Filter.Apply(Session("chrome", "News", "https://news.example.org/"))!;
        Assert.Equal("domain_not_in_allowed_list", other.Metadata["excluded_reason"]!.GetValue<string>());
    }

    [Fact]
    public void Name_of_a_blocked_next_app_is_hidden()
    {
        var e = Session("chrome", "Keepa").Set("next_process_name", "KeePass").Set("next_application", "KeePass Password Safe");
        var kept = Filter.Apply(e)!;
        Assert.Equal("Keepa", kept.WindowTitle);
        Assert.Equal(PrivacyFilter.RedactedText, kept.Metadata["next_application"]!.GetValue<string>());
    }
}
