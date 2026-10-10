// Builds hair-tryon/dist/hair-tryon.html — ONE file with everything inlined, easy to host or send.
// Run: node hair-tryon/build-single.js
const fs = require('fs'), path = require('path');
const dir = __dirname;
const read = f => fs.readFileSync(path.join(dir, f), 'utf8');
let html = read('index.html');
['data.js', 'engine.js', 'app.js'].forEach(f => {
  const tag = `<script src="${f}"></script>`;
  if (!html.includes(tag)) throw new Error('missing ' + tag);
  html = html.replace(tag, () => '<script>\n' + read(f).replace(/<\/script>/gi, '<\\/script>') + '\n</script>');
});
fs.mkdirSync(path.join(dir, 'dist'), { recursive: true });
fs.writeFileSync(path.join(dir, 'dist', 'hair-tryon.html'), html);
console.log('wrote dist/hair-tryon.html (' + Math.round(html.length / 1024) + ' KB)');
