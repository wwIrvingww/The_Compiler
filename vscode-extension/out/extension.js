"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = __importStar(require("vscode"));
const outputChannel = vscode.window.createOutputChannel('CompiScript TAC');
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
function activate(context) {
    const diagnostics = vscode.languages.createDiagnosticCollection('cps');
    context.subscriptions.push(diagnostics);
    vscode.workspace.onDidSaveTextDocument(doc => runDiagnostics(doc, diagnostics));
    context.subscriptions.push(vscode.commands.registerCommand('mylang.generateQuadrupletTac', () => runGenerator('quadruplet')));
    context.subscriptions.push(vscode.commands.registerCommand('mylang.generatePrettyTac', () => runGenerator('pretty')));
}
async function runGenerator(mode) {
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
        const data = await resp.json();
        outputChannel.clear();
        outputChannel.appendLine(`=== ${mode.toUpperCase()} GENERATION ===`);
        outputChannel.appendLine(data.result);
        outputChannel.show(true);
        vscode.window.showInformationMessage(`${mode} generation complete.`);
    }
    catch (err) {
        vscode.window.showErrorMessage(`Error: ${err}`);
    }
}
async function runDiagnostics(doc, diagnostics) {
    if (doc.languageId !== 'cps')
        return;
    const fetch = (await import('node-fetch')).default;
    const resp = await fetch('http://localhost:8000/diagnostics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: doc.getText() }),
    });
    const data = await resp.json();
    const vsDiags = data.diagnostics.map(d => {
        const line = doc.lineAt(d.line - 1); // convert 1-based line to 0-based
        const range = new vscode.Range(line.range.start, line.range.end);
        return new vscode.Diagnostic(range, d.message, vscode.DiagnosticSeverity.Error);
    });
    diagnostics.set(doc.uri, vsDiags);
}
// This method is called when your extension is deactivated
function deactivate() { }
//# sourceMappingURL=extension.js.map