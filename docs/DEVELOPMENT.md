# Developer setup

## Tools

- .NET 8 SDK (`dotnet --version` → 8.0.x)
- Windows 10/11 to run the app. The Core library and its tests also build and run on
  Linux/macOS (`EnableWindowsTargeting` lets the Windows projects compile there too).
- Any editor: Visual Studio 2022, VS Code + C# Dev Kit, or Rider.

## Build and test

```bash
dotnet build
dotnet test                       # 100+ Core unit tests, any OS
```

## Run on Windows (without installing)

```powershell
dotnet run --project src/MppWatcher.App                          # the watcher (tray icon)
dotnet run --project src/MppWatcher.App -- --viewer              # live viewer, in a 2nd terminal
dotnet run --project src/MppWatcher.App -- --smoke-test 20       # self-test report
```

Use a test config and data folder so you do not touch a real install:

```powershell
dotnet run --project src/MppWatcher.App -- --config .\dev-config.json --data .\dev-data
dotnet run --project src/MppWatcher.App -- --viewer --config .\dev-config.json --data .\dev-data
```

## Publish the single exe

```powershell
dotnet publish src/MppWatcher.App -c Release -o publish
# → publish\MPPWatcher.exe (self-contained, win-x64)
```

## CI

`.github/workflows/build.yml`:
- Linux job: Core unit tests.
- Windows job: build, tests, publish, **smoke test of the real exe for 15 s**, and uploads
  the **MPPWatcher-win-x64** artifact (exe + install scripts + docs).

## Code layout

See [ARCHITECTURE.md](ARCHITECTURE.md). Keep decision logic in `MppWatcher.Core` (testable)
and only thin Win32 glue in `MppWatcher.Windows`.

## Conventions

- Event types and end reasons live in `Core/Events/EventTypes.cs`. Document every new one
  in `EVENT_SCHEMA.md`.
- Details go in `metadata` with `snake_case` keys.
- Collectors must never throw out of callbacks; log and continue, or call
  `context.ReportFailure`.
- Nothing may record key presses, passwords, clipboard, screen images or file contents.
