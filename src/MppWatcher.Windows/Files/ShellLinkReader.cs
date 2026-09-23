using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

namespace MppWatcher.Windows.Files;

/// <summary>Reads the target path of a Windows shortcut (.lnk) through the Shell's own COM object.</summary>
internal static class ShellLinkReader
{
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    private class ShellLink { }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
    private interface IShellLinkW
    {
        // Only the first method of the interface is needed; COM calls go by position.
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder file, int maxPath, IntPtr findData, uint flags);
    }

    public static string? TargetOf(string lnkPath)
    {
        object? link = null;
        try
        {
            link = new ShellLink();
            ((IPersistFile)link).Load(lnkPath, 0 /* STGM_READ */);
            var sb = new StringBuilder(1024);
            ((IShellLinkW)link).GetPath(sb, sb.Capacity, IntPtr.Zero, 0x4 /* SLGP_RAWPATH */);
            var target = Environment.ExpandEnvironmentVariables(sb.ToString());
            return string.IsNullOrWhiteSpace(target) ? null : target;
        }
        catch (Exception e) when (e is COMException or UnauthorizedAccessException or FileNotFoundException or IOException)
        {
            return null;
        }
        finally
        {
            if (link is not null) Marshal.ReleaseComObject(link);
        }
    }
}
