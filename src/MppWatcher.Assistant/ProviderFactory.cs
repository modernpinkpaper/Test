namespace MppWatcher.Assistant;

/// <summary>Picks the brain: real Claude when ANTHROPIC_API_KEY is set, else the built-in stand-in.</summary>
public static class ProviderFactory
{
    public static bool HasApiKey => !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY"));

    public static ILlmProvider Create(bool forceHeuristic = false, string? model = null, int repeatThreshold = 8)
    {
        if (!forceHeuristic && HasApiKey)
            return new ClaudeLlmProvider(model: string.IsNullOrWhiteSpace(model) ? ClaudeLlmProvider.DefaultModel : model!);
        return new HeuristicLlmProvider(repeatThreshold);
    }

    public static string Describe(ILlmProvider provider, string? model) =>
        provider is ClaudeLlmProvider
            ? $"Claude ({(string.IsNullOrWhiteSpace(model) ? ClaudeLlmProvider.DefaultModel : model)})"
            : "built-in heuristic (set ANTHROPIC_API_KEY for the real Claude brain)";
}
