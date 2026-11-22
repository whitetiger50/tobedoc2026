const ts = require('/Applications/Cursor.app/Contents/Resources/app/extensions/node_modules/typescript/lib/typescript.js');
const path = require('path');
const types = '/Users/ohs/.cursor/projects/empty-window/canvases/node_modules/@types';
const file = path.join(__dirname, 'patient-speech-v06-examples.canvas.tsx');
const options = {
  target: ts.ScriptTarget.ES2021, module: ts.ModuleKind.ESNext,
  moduleResolution: ts.ModuleResolutionKind.Bundler, jsx: ts.JsxEmit.ReactJSX,
  strict: true, noEmit: true, skipLibCheck: true, typeRoots: [types],
  paths: {'cursor/canvas': ['/Users/ohs/.cursor/skills-cursor/canvas/sdk/index.d.ts'],
    react: [types + '/react/index.d.ts'], 'react/jsx-runtime': [types + '/react/jsx-runtime.d.ts']}
};
const diagnostics = ts.getPreEmitDiagnostics(ts.createProgram([file], options));
for (const d of diagnostics.slice(0, 12)) process.stdout.write(ts.flattenDiagnosticMessageText(d.messageText, '\n') + '\n');
process.stdout.write(`TypeScript diagnostics: ${diagnostics.length}\n`);
process.exitCode = diagnostics.length ? 1 : 0;
