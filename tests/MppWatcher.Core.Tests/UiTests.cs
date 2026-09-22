using MppWatcher.Core.Configuration;
using MppWatcher.Core.Events;
using MppWatcher.Core.Presentation;
using MppWatcher.Core.Ui;

namespace MppWatcher.Core.Tests;

public class UiCapturePolicyTests
{
    private readonly WatcherConfig _cfg = new();
    private UiCapturePolicy Policy => new(() => _cfg);

    private static UiElementInfo Edit(string name, string? value, string? id = null, bool password = false) => new()
    {
        ControlType = "Edit", Name = name, AutomationId = id, HasValuePattern = true, Value = value, IsPassword = password,
        ProcessName = "chrome", ApplicationName = "Google Chrome", WindowTitle = "Keepa - Google Chrome",
    };

    private static UiElementInfo Button(string? name, string type = "Button") => new()
    {
        ControlType = type, Name = name, ProcessName = "chrome", WindowTitle = "Etsy",
    };

    [Fact]
    public void Business_search_field_value_is_logged()
    {
        var d = Policy.EvaluateField(Edit("Search", "personalized stationery"));
        Assert.True(d.Log);
        Assert.True(d.IncludeValue);
        Assert.Equal("personalized stationery", d.Value);
    }

    [Fact]
    public void Sku_field_is_logged() => Assert.Equal("MA023", Policy.EvaluateField(Edit("SKU", "MA023")).Value);

    [Theory]
    [InlineData("Search", "hunter2", null, true)]          // marked password by Windows
    [InlineData("Password", "hunter2", null, false)]
    [InlineData("Enter the code we sent", "123456", "otp", false)]
    [InlineData("Card number", "4111 1111 1111 1111", null, false)]
    [InlineData("Notes", "4111 1111 1111 1111", null, false)] // value looks like a card
    [InlineData("CVV", "123", null, false)]
    public void Sensitive_fields_are_never_logged(string name, string value, string? id, bool password)
    {
        var d = Policy.EvaluateField(Edit(name, value, id, password));
        Assert.False(d.Log);
        Assert.True(d.IsSensitive);
        Assert.Null(d.Value);
    }

    [Fact]
    public void Long_or_multiline_values_are_logged_without_value()
    {
        var d = Policy.EvaluateField(Edit("Message", "Hi there,\nthanks for the order"));
        Assert.True(d.Log);
        Assert.False(d.IncludeValue);
        Assert.Null(d.Value);
        Assert.True(d.ValueLength > 10);
        Assert.False(Policy.EvaluateField(Edit("Description", new string('x', 300))).IncludeValue);
    }

    [Fact]
    public void Address_bar_value_is_sanitized()
    {
        var d = Policy.EvaluateField(Edit("Address and search bar", "sellercentral.amazon.com/inventory?sid=abc&sku=MA023"));
        Assert.Equal("https://sellercentral.amazon.com/inventory?sku=MA023", d.Value);
    }

    [Fact]
    public void Blocked_controls_apps_and_titles_are_refused()
    {
        _cfg.Privacy.BlockedControls.Add("*Customer note*");
        Assert.Equal("blocked control", Policy.EvaluateField(Edit("Customer note", "call me")).Reason);
        Assert.Equal("blocked application", Policy.EvaluateField(Edit("Search", "x") with { ProcessName = "KeePassXC" }).Reason);
        _cfg.Privacy.BlockedWindowTitles.Add("*Payroll*");
        Assert.Equal("blocked window title", Policy.EvaluateAction(Button("Save") with { WindowTitle = "Payroll - ADP" }).Reason);
        _cfg.Collectors.UiAutomation.IgnoreApplications.Add("game*");
        Assert.False(Policy.EvaluateAction(Button("Play") with { ProcessName = "game.exe" }).Log);
    }

    [Fact]
    public void Non_fields_and_hidden_values_are_skipped()
    {
        Assert.False(Policy.EvaluateField(Button("Save")).Log);
        Assert.False(Policy.EvaluateField(Edit("Search", null) with { HasValuePattern = false }).Log);
        Assert.False(Policy.EvaluateField(Edit("Search", "   ")).Log);
    }

    [Fact]
    public void Combo_box_selection_is_used_when_there_is_no_value()
    {
        var combo = new UiElementInfo { ControlType = "ComboBox", Name = "Date range", SelectedItems = "Last 30 days", ProcessName = "chrome" };
        Assert.Equal("Last 30 days", Policy.EvaluateField(combo).Value);
    }

    [Theory]
    [InlineData("Button", "Save", "button_clicked", true)]
    [InlineData("Button", "Publish listing", "button_clicked", true)]
    [InlineData("Hyperlink", "Inventory", "link_clicked", false)]
    [InlineData("TabItem", "Personalization", "tab_selected", false)]
    [InlineData("MenuItem", "Export As...", "menu_item_clicked", true)]
    [InlineData("CheckBox", "Gift wrap", "checkbox_toggled", false)]
    [InlineData("Button", "Address book", "button_clicked", false)] // "add" only as a whole word
    public void Actions_are_classified(string type, string name, string action, bool key)
    {
        var d = Policy.EvaluateAction(Button(name, type));
        Assert.True(d.Log);
        Assert.Equal(action, d.Action);
        Assert.Equal(key, d.IsKeyAction);
    }

    [Fact]
    public void Unnamed_or_non_actionable_controls_are_not_actions()
    {
        Assert.False(Policy.EvaluateAction(Button(null)).Log);
        Assert.False(Policy.EvaluateAction(Button("Panel", "Pane")).Log);
        Assert.False(Policy.EvaluateAction(Button("Show password")).Log);
    }

    [Fact]
    public void Switches_in_config_turn_capture_off()
    {
        _cfg.Collectors.UiAutomation.CaptureFieldValues = false;
        _cfg.Collectors.UiAutomation.CaptureActions = false;
        Assert.False(Policy.EvaluateField(Edit("Search", "x")).Log);
        Assert.False(Policy.EvaluateAction(Button("Save")).Log);
    }
}

public class FocusedFieldTrackerTests
{
    private readonly FocusedFieldTracker _t = new(() => TimeSpan.FromSeconds(4));
    private static UiElementInfo F(string id, string? value = "") => new() { ControlType = "Edit", Name = id, RuntimeId = id, Value = value };

    [Fact]
    public void Value_is_committed_when_focus_leaves()
    {
        Assert.Null(_t.OnFocus(F("search"), T.Start));
        _t.OnValue("personalized", T.Start.AddSeconds(1));
        _t.OnValue("personalized stationery", T.Start.AddSeconds(2));
        var c = _t.OnFocus(F("sku"), T.Start.AddSeconds(3))!;
        Assert.Equal("personalized stationery", c.Element.Value);
        Assert.Equal("focus_left", c.Trigger);
        Assert.Equal("search", c.Element.Name);
    }

    [Fact]
    public void Settled_value_is_committed_once_while_focus_stays()
    {
        _t.OnFocus(F("search"), T.Start);
        _t.OnValue("stationery", T.Start.AddSeconds(1));
        Assert.Null(_t.OnTick(T.Start.AddSeconds(3)));
        Assert.Equal("value_settled", _t.OnTick(T.Start.AddSeconds(5.5))!.Trigger);
        Assert.Null(_t.OnTick(T.Start.AddSeconds(9)));
        Assert.Null(_t.OnFocus(null, T.Start.AddSeconds(10))); // same value already committed

        _t.OnFocus(F("search2"), T.Start.AddSeconds(11));
        _t.OnValue("notebooks", T.Start.AddSeconds(12));
        Assert.NotNull(_t.OnTick(T.Start.AddSeconds(17)));
        _t.OnValue("notebooks gift", T.Start.AddSeconds(18)); // second search in the same box
        Assert.Equal("notebooks gift", _t.OnTick(T.Start.AddSeconds(23))!.Element.Value);
    }

    [Fact]
    public void Unchanged_or_emptied_fields_are_not_reported()
    {
        _t.OnFocus(F("search", "already there"), T.Start);
        Assert.Null(_t.OnFocus(null, T.Start.AddSeconds(2)));
        _t.OnFocus(F("search", "abc"), T.Start);
        _t.OnValue("", T.Start.AddSeconds(1));
        Assert.Null(_t.OnFocus(null, T.Start.AddSeconds(2)));
    }

    [Fact]
    public void Refocusing_the_same_element_is_ignored()
    {
        _t.OnFocus(F("search"), T.Start);
        _t.OnValue("abc", T.Start.AddSeconds(1));
        Assert.Null(_t.OnFocus(F("search"), T.Start.AddSeconds(2)));
        Assert.Equal("abc", _t.Flush()!.Element.Value);
    }
}

public class UiEventFactoryTests
{
    [Fact]
    public void Field_event_has_structured_metadata()
    {
        var e = new UiElementInfo
        {
            ControlType = "Edit", Name = "Search", AutomationId = "searchInput", FrameworkId = "Chrome", ProcessName = "chrome",
            ApplicationName = "Google Chrome", WindowTitle = "Keepa", AncestorPath = new[] { "Group 'Product Finder'", "Document 'Keepa'" },
        };
        var ev = UiEventFactory.FieldValue(e, new UiFieldDecision(true, true, "personalized stationery", 23, false, "ok"), "focus_left", true, T.Start);
        Assert.Equal(EventTypes.UiFieldValue, ev.EventType);
        Assert.Equal("Google Chrome", ev.Application);
        Assert.Equal("personalized stationery", ev.Metadata["value"]!.GetValue<string>());
        Assert.Equal("Search", ev.Metadata["label"]!.GetValue<string>());
        Assert.Equal(2, ev.Metadata["context_path"]!.AsArray().Count);
        Assert.Equal("Google Chrome: field \"Search\" = \"personalized stationery\"", EventSummaryFormatter.Summarize(ev));
    }

    [Fact]
    public void Omitted_value_is_marked_and_absent()
    {
        var e = new UiElementInfo { ControlType = "Edit", Name = "Message", ProcessName = "chrome" };
        var ev = UiEventFactory.FieldValue(e, new UiFieldDecision(true, false, null, 540, false, "too long"), "focus_left", true, T.Start);
        Assert.Null(ev.Metadata["value"]);
        Assert.True(ev.Metadata["value_omitted"]!.GetValue<bool>());
        Assert.Contains("value not stored", EventSummaryFormatter.Summarize(ev));
    }

    [Fact]
    public void Action_event_reads_naturally()
    {
        var e = new UiElementInfo { ControlType = "Button", Name = "Save", ProcessName = "chrome", ApplicationName = "Google Chrome" };
        var ev = UiEventFactory.Action(e, new UiActionDecision(true, "button_clicked", "Save", true, "ok"), "click", T.Start);
        Assert.Equal("Google Chrome: button clicked \"Save\" ★", EventSummaryFormatter.Summarize(ev));
    }

    [Fact]
    public void Inspection_report_hides_sensitive_values()
    {
        var pw = new UiElementInfo { ControlType = "Edit", Name = "Password", HasValuePattern = true, Value = "hunter2", IsPassword = true, ProcessName = "chrome" };
        var policy = new UiCapturePolicy(() => new WatcherConfig());
        var report = UiEventFactory.InspectionReport(pw, policy.EvaluateField(pw), policy.EvaluateAction(pw));
        Assert.DoesNotContain("hunter2", report);
        Assert.Contains("Sensitive?", report);
        Assert.Contains("YES", report);
    }

    [Fact]
    public void Redaction_removes_ui_values_in_blocked_apps()
    {
        var cfg = new WatcherConfig();
        var e = new UiElementInfo { ControlType = "Edit", Name = "Search", ProcessName = "KeePass" };
        var ev = UiEventFactory.FieldValue(e, new UiFieldDecision(true, true, "secret thing", 12, false, "ok"), "focus_left", true, T.Start);
        var filtered = new MppWatcher.Core.Privacy.PrivacyFilter(() => cfg).Apply(ev)!;
        Assert.DoesNotContain("secret thing", EventJson.Serialize(filtered));
    }
}
