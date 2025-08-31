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
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
// client/src/extension.ts
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const node_1 = require("vscode-languageclient/node");
let client;
function getPythonCmd(context) {
    const config = vscode.workspace.getConfiguration('compiscript');
    const configured = config.get('pythonPath');
    if (configured && configured.length > 0)
        return configured;
    // intenta el .venv al nivel del repo (context.extensionPath apunta al folder 'client' en desarrollo)
    const repoRoot = path.resolve(context.extensionPath, '..');
    const venvDir = path.join(repoRoot, '.venv');
    if (fs.existsSync(venvDir)) {
        const pyPathWin = path.join(venvDir, 'Scripts', 'python.exe');
        const pyPathNix = path.join(venvDir, 'bin', 'python');
        if (process.platform === 'win32' && fs.existsSync(pyPathWin))
            return pyPathWin;
        if (process.platform !== 'win32' && fs.existsSync(pyPathNix))
            return pyPathNix;
    }
    // fallback
    return process.platform === 'win32' ? 'python' : 'python3';
}
function activate(context) {
    const serverModule = context.asAbsolutePath(path.join('..', 'server', 'server.py'));
    const pythonCmd = getPythonCmd(context);
    const serverOptions = {
        run: { command: pythonCmd, args: [serverModule], transport: node_1.TransportKind.stdio },
        debug: { command: pythonCmd, args: [serverModule, '--debug'], transport: node_1.TransportKind.stdio }
    };
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'compiscript' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.cps')
        }
    };
    client = new node_1.LanguageClient('compiscriptLS', 'Compiscript Language Server', serverOptions, clientOptions);
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
        if (!editor)
            return vscode.window.showInformationMessage('Open a Compiscript file first.');
        const doc = editor.document;
        await doc.save();
        vscode.window.showInformationMessage('Compiscript: compile triggered (save).');
    });
    context.subscriptions.push(compileCmd);
}
exports.activate = activate;
function deactivate() {
    if (!client)
        return undefined;
    return client.stop();
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map