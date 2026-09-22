namespace MppWatcher.Core.Ui;

/// <param name="Edited">True when the value was seen changing; false when focus was noticed late and the starting value is unknown.</param>
public sealed record FieldCommit(UiElementInfo Element, string Trigger, bool Edited);

/// <summary>
/// Decides when a text field's value is "finished" — without keystrokes. The Windows layer
/// reports which field has focus and re-reads its value a couple of times per second.
/// A value is committed when the user leaves the field (focus_left), or when a changed
/// value stays the same for a few seconds while the field keeps focus (value_settled,
/// e.g. a search typed and submitted with Enter). Unchanged fields are not reported.
/// </summary>
public sealed class FocusedFieldTracker
{
    private readonly Func<TimeSpan> _settle;
    private UiElementInfo? _field;
    private string? _initial, _last, _lastCommitted;
    private bool _initialKnown = true;
    private DateTimeOffset _lastChange;

    public FocusedFieldTracker(Func<TimeSpan> settle) => _settle = settle;

    public UiElementInfo? Current => _field;

    /// <summary>Focus moved. <paramref name="field"/> is the new field, or null if focus went to something that is not a tracked field.</summary>
    /// <param name="initialValueKnown">
    /// False when the focus was only noticed after the fact (Windows did not announce it): the person may
    /// already have typed, so the first value read is not treated as the starting value.
    /// </param>
    public FieldCommit? OnFocus(UiElementInfo? field, DateTimeOffset now, bool initialValueKnown = true)
    {
        if (field is not null && _field is not null && field.RuntimeId is not null && field.RuntimeId == _field.RuntimeId) return null;
        var commit = Commit("focus_left");
        _field = field;
        _initialKnown = initialValueKnown;
        _last = field?.Value;
        _initial = initialValueKnown ? _last : null;
        _lastCommitted = null;
        _lastChange = now;
        return commit;
    }

    /// <summary>Latest value read from the focused field.</summary>
    public void OnValue(string? value, DateTimeOffset now)
    {
        if (_field is null || value == _last) return;
        _last = value;
        _lastChange = now;
    }

    /// <summary>Call regularly; returns a commit when a changed value has settled.</summary>
    public FieldCommit? OnTick(DateTimeOffset now)
    {
        if (_field is null || now - _lastChange < _settle()) return null;
        return Commit("value_settled");
    }

    /// <summary>The field disappeared or the collector stops: commit what we have.</summary>
    public FieldCommit? Flush()
    {
        var c = Commit("focus_left");
        _field = null;
        return c;
    }

    private FieldCommit? Commit(string trigger)
    {
        if (_field is null) return null;
        if (_last == _initial || _last == _lastCommitted || string.IsNullOrWhiteSpace(_last)) return null;
        _lastCommitted = _last;
        return new FieldCommit(_field with { Value = _last }, trigger, Edited: _initialKnown);
    }
}
