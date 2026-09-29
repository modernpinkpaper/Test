# Later

## Character creator kit (pinned)
Turn what we built for her into a reusable kit for new characters:
1. **Prompts document** - the exact ChatGPT prompts for each picture (full body, close-up head, hands sheet,
   expressions, turnaround) + picture rules: white background, flat colours, bold outlines, front view,
   the same character in every picture, big image size.
2. **Python pipeline** - drop the pictures in a folder, run one command: flat-colour tracing, parts, lining up
   head and body pictures, scores per part, grid + side-by-side pictures, a report of parts under 89%.
3. **Process file for Claude** - the polishing steps and checks (grid, 89%+ per part, tapered lines, clean
   edges, the known problem spots) so every session follows the same process.
Test: the pipeline should rebuild this character close to the current one.
