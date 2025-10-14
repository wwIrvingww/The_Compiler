// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
const outputChannel = vscode.window.createOutputChannel('CompiScript TAC');

let tacPanel: vscode.WebviewPanel | undefined;

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
	const diagnostics = vscode.languages.createDiagnosticCollection('cps');
	context.subscriptions.push(diagnostics);
	vscode.workspace.onDidSaveTextDocument(doc => runDiagnostics(doc, diagnostics));

  context.subscriptions.push(vscode.commands.registerCommand('mylang.generateQuadrupletTac', () => runGenerator('quadruplet')));
  context.subscriptions.push(vscode.commands.registerCommand('mylang.generatePrettyTac', () => runGenerator('pretty')));

  context.subscriptions.push(vscode.commands.registerCommand('cps.genPTAC', () => runGeneratorWebView('pretty')));
  context.subscriptions.push(vscode.commands.registerCommand('cps.genQTAC', () => runGeneratorWebView('quadruplet')));
}
function highlightQuad(tac: string): string {
  const lines = tac.split("\n");

  const colWidth = [10,10,10,10];

  const header = ["RESULT", "OP", "ARG1", "ARG2"]
  .map((h, i)=> `<span style="display:inline-block; width:${colWidth[i]}ch; font-weight:bold;">${h}</span>`)
  .join("");

  const htmlLines = lines.map((line, index) => {
    const parts = line.split(",").map(p => p.trim());
    
    while (parts.length < 4) {parts.push("");};
    const lineHtml = parts
      .map((part, i) => {
        if (part === "None"){ part = "";}; // <-- skip None
        return `<span style="display:inline-block; width:${colWidth[i]}ch;">${part}</span>`;
      })
      .join("");
    
    const lineNumber = `<span style="color:#858585; user-select:none; display:inline-block; width:3ch;">${index + 1}</span>`;
    
    return lineNumber + lineHtml;
  });
  return [header, ...htmlLines].join("\n");
}

function highlightTac(tac: string): string{
  const unary = [
    "uminus", "not", 
    "CREATE_ARRAY", 
    "goto", "label",
    "call", "return","print"
  ];
  const bin = [
    "*", "/", "%", "+", "-",
    "||", "&&",
    "==", "!=", "<", ">", "<=", ">=",
    "load", "store", "move",
    "if", 
  ];

  const styles = {
    temp: 'color:#4FC1FF;',
    label: 'color:#ffc91a; font-weight:bold;',
    unary: 'color:#D19A66; font-style:italic;',
    binary: 'color:#C586C0;',
    assign: 'color:#E5C07B;',
    deref: 'color:#f13546;',
    comment: 'color:#6A9955; opacity:0.8;'
  };
  const lines = tac.split("\n");
  let comment_flag = false;
const htmlLines = lines.map((line, index) => {
    const parts = line.split(/(\s+)/); // keep whitespace as tokens
    const highlightedParts = parts.map(part => {
      const trimmed = part.trim();

      if (comment_flag) {
        return `<span style="${styles["comment"]}">${part}</span>`;
      }
      if (trimmed.startsWith("#")) {
        comment_flag = true;
        return `<span style="${styles["comment"]}">${part}</span>`;
      }
      if (unary.includes(trimmed)){
        return `<span style="${styles["unary"]}">${part}</span>`;
      }
      if (bin.includes(trimmed)){
        return `<span style="${styles["binary"]}">${part}</span>`;
      }
      if(trimmed === "="){
        return `<span style="${styles["assign"]}">${part}</span>`;
      }
      if (trimmed.startsWith('*')){
        return `<span style="${styles["deref"]}">${part}</span>`;
      }
      if (/^\b[tT]\d+\b$/.test(trimmed)) {
        return `<span style="${styles["temp"]}">${part}</span>`;
      }

      if (/^\b[lL]\d+\b$/.test(trimmed)) {
        return `<span style="${styles["label"]}">${part}</span>`;
      }

      return part; // default (no coloring)
    });
    const lineNumber = `<span style="color:#858585; user-select:none; display:inline-block; width:3em;">${index + 1}</span>`;
    comment_flag = false;
    return lineNumber + highlightedParts.join("");
  });
 
  return htmlLines.join("\n");
}


async function runGeneratorWebView(mode: 'quadruplet' | 'pretty') {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage('No active editor');
    return;
  }

  const doc = editor.document;
  if (doc.languageId !== 'cps') {
    vscode.window.showInformationMessage('Active file is not a CPS file.');
    return;
  }

  try {
    const endpoint = mode === 'quadruplet' ? '/tac/quadruplet' : '/tac/pretty';
    const resp = await fetch(`http://localhost:8000${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: doc.getText() }),
    });

    if (!resp.ok) {
      const txt = await resp.text();
      vscode.window.showErrorMessage(`Generation failed: ${txt}`);
      return;
    }

    const data = (await resp.json()) as { result: string; errors?: string[] };

 
    if (!tacPanel) {
      tacPanel = vscode.window.createWebviewPanel(
        'tacViewer',
        `CompiScript TAC (${mode})`,
        vscode.ViewColumn.Beside,
        { enableScripts: true }
      );

      // Clean up when panel is closed
      tacPanel.onDidDispose(() => {
        tacPanel = undefined;
      });
    };
    var highlighted;
    if (mode === 'quadruplet'){
      highlighted = highlightQuad(data.result);
    } else{
      highlighted = highlightTac(data.result);
    }
    

    tacPanel.webview.html = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <style>
          body {
            font-family: monospace;
            background-color: #202330;
            color: #dcdcdc;
            padding: 1rem;
            white-space: pre;
          }
        </style>
      </head>
      <body><pre>${highlighted}</pre></body>
      </html>
    `;

    vscode.window.showInformationMessage(`${mode} generation complete.`);
  } catch (err) {
    vscode.window.showErrorMessage(`Error: ${err}`);
  }
}



async function runGenerator(mode: 'quadruplet' | 'pretty') {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage('No active editor');
    return;
  }

  const doc = editor.document;
  if (doc.languageId !== 'cps') {
    vscode.window.showInformationMessage('Active file is not a CPS file.');
    return;
  }

  try {
    const endpoint = mode === 'quadruplet' ? '/tac/quadruplet' : '/tac/pretty';
    const resp = await fetch(`http://localhost:8000${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: doc.getText() }),
    });

    if (!resp.ok) {
      const txt = await resp.text();
      vscode.window.showErrorMessage(`Generation failed: ${txt}`);
      return;
    }

    const data = await resp.json() as { result: string; errors?: string[] };
    outputChannel.clear();
    outputChannel.appendLine(`=== ${mode.toUpperCase()} GENERATION ===`);
    outputChannel.appendLine(data.result);
    outputChannel.show(true); 

    vscode.window.showInformationMessage(`${mode} generation complete.`);
  } catch (err) {
    vscode.window.showErrorMessage(`Error: ${err}`);
  }
}




async function runDiagnostics(doc: vscode.TextDocument, diagnostics: vscode.DiagnosticCollection) {
  if (doc.languageId !== 'cps') return;
	const fetch = (await import('node-fetch')).default;
  	const resp = await fetch('http://localhost:8000/diagnostics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: doc.getText() }),
  });

  const data = await resp.json() as { diagnostics: { line: number; message: string }[] };

  const vsDiags = data.diagnostics.map(d => {
    const line = doc.lineAt(d.line - 1); // convert 1-based line to 0-based
    const range = new vscode.Range(line.range.start, line.range.end);
    return new vscode.Diagnostic(range, d.message, vscode.DiagnosticSeverity.Error);
  });

  diagnostics.set(doc.uri, vsDiags);
}




// This method is called when your extension is deactivated
export function deactivate() {}
