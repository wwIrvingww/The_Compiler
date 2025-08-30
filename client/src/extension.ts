import * as path from 'path';
import * as vscode from 'vscode';
import { LanguageClient, TransportKind, LanguageClientOptions, ServerOptions } from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

function getPythonCmd(): string {
  const config = vscode.workspace.getConfiguration('compiscript');
  const configured = config.get<string>('pythonPath');
  if (configured && configured.length > 0) return configured;
  return process.platform === 'win32' ? 'python' : 'python3';
}

export function activate(context: vscode.ExtensionContext) {
  const serverModule = context.asAbsolutePath(path.join('..','server','server.py'));
  const pythonCmd = getPythonCmd();

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

  // start devuelve Thenable<void>, así que llamamos start() y registramos un disposable
  client.start();

  // Registramos un disposable que detiene el cliente cuando la extensión se desactiva
  const stopDisposable = {
    dispose: () => {
      if (client) {
        // stop devuelve Thenable<void>, esto es aceptable dentro de dispose
        client.stop();
      }
    }
  };
  context.subscriptions.push(stopDisposable);

  // Command: run compile (simple)
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
