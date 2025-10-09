// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
const outputChannel = vscode.window.createOutputChannel('CompiScript TAC');
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
	const diagnostics = vscode.languages.createDiagnosticCollection('cps');
	context.subscriptions.push(diagnostics);
	vscode.workspace.onDidSaveTextDocument(doc => runDiagnostics(doc, diagnostics));

  context.subscriptions.push(vscode.commands.registerCommand('mylang.generateQuadrupletTac', () => runGenerator('quadruplet')));
  context.subscriptions.push(vscode.commands.registerCommand('mylang.generatePrettyTac', () => runGenerator('pretty')));


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
