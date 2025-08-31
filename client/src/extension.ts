// client/src/extension.ts
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { LanguageClient, TransportKind, LanguageClientOptions, ServerOptions } from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

function getPythonCmd(context: vscode.ExtensionContext): string {
  const config = vscode.workspace.getConfiguration('compiscript');
  const configured = config.get<string>('pythonPath');
  if (configured && configured.length > 0) return configured;

  // intenta el .venv al nivel del repo (context.extensionPath apunta al folder 'client' en desarrollo)
  const repoRoot = path.resolve(context.extensionPath, '..');
  const venvDir = path.join(repoRoot, '.venv');
  if (fs.existsSync(venvDir)) {
    const pyPathWin = path.join(venvDir, 'Scripts', 'python.exe');
    const pyPathNix = path.join(venvDir, 'bin', 'python');
    if (process.platform === 'win32' && fs.existsSync(pyPathWin)) return pyPathWin;
    if (process.platform !== 'win32' && fs.existsSync(pyPathNix)) return pyPathNix;
  }

  // fallback
  return process.platform === 'win32' ? 'python' : 'python3';
}

export function activate(context: vscode.ExtensionContext) {
  const serverModule = context.asAbsolutePath(path.join('..','server','server.py'));
  const pythonCmd = getPythonCmd(context);

  const serverOptions: ServerOptions = {
    run:   { command: pythonCmd, args: [serverModule], transport: TransportKind.stdio },
    debug: { command: pythonCmd, args: [serverModule, '--debug'], transport: TransportKind.stdio }
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: 'file', language: 'compiscript' }],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher('**/*.cps')
    }
  };

  client = new LanguageClient('compiscriptLS', 'Compiscript Language Server', serverOptions, clientOptions);

  client.start();

  const stopDisposable = {
    dispose: () => {
      if (client) {
        client.stop();
      }
    }
  };
  context.subscriptions.push(stopDisposable);

  const compileCmd = vscode.commands.registerCommand('compiscript.compileFile', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return vscode.window.showInformationMessage('Open a Compiscript file first.');
    const doc = editor.document;
    await doc.save();
    vscode.window.showInformationMessage('Compiscript: compile triggered (save).');
  });
  context.subscriptions.push(compileCmd);
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) return undefined;
  return client.stop();
}
