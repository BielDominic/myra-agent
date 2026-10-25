import { createRequire } from 'node:module';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const mode = process.argv[2] || 'list';
const requestedPackage = process.env.MYRA_REA_PACKAGE || 'rea-agents@6.5.0';
const expectedVersion = requestedPackage.match(/@([0-9]+\.[0-9]+\.[0-9]+)$/)?.[1] || null;

function findPackageRoot() {
  const explicit = process.env.MYRA_REA_PACKAGE_ROOT;
  if (explicit) {
    const manifest = path.join(explicit, 'package.json');
    if (!existsSync(manifest)) throw new Error('MYRA_REA_PACKAGE_ROOT nao contem package.json.');
    return path.resolve(explicit);
  }
  const npmCache = process.env.npm_config_cache || path.join(os.homedir(), 'AppData', 'Local', 'npm-cache');
  const npxRoot = path.join(npmCache, '_npx');
  if (!existsSync(npxRoot)) throw new Error('Cache npx nao encontrado; execute a analise REA uma vez para baixar o pacote fixado.');
  const candidates = [];
  for (const entry of readdirSync(npxRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const root = path.join(npxRoot, entry.name, 'node_modules', 'rea-agents');
    const manifest = path.join(root, 'package.json');
    if (!existsSync(manifest)) continue;
    try {
      const pkg = JSON.parse(readFileSync(manifest, 'utf8'));
      if (!expectedVersion || pkg.version === expectedVersion) candidates.push({ root, version: pkg.version, mtime: existsSync(path.join(root, 'scripts', 'rea.mjs')) ? 1 : 0 });
    } catch {}
  }
  candidates.sort((a, b) => b.mtime - a.mtime);
  if (!candidates.length) throw new Error(`Pacote ${requestedPackage} nao encontrado no cache npx. Execute rea_analyze_javascript primeiro ou defina MYRA_REA_PACKAGE_ROOT.`);
  return candidates[0].root;
}

const packageRoot = findPackageRoot();
const packageManifest = JSON.parse(readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
if (expectedVersion && packageManifest.version !== expectedVersion) throw new Error(`Versao REA inesperada: ${packageManifest.version}; esperada ${expectedVersion}.`);
const clientEntry = path.join(path.dirname(packageRoot), '@modelcontextprotocol', 'client', 'dist', 'index.mjs');
const transportEntry = path.join(path.dirname(packageRoot), '@modelcontextprotocol', 'client', 'dist', 'stdio.mjs');
const { Client } = await import(pathToFileURL(clientEntry).href);
const { StdioClientTransport } = await import(pathToFileURL(transportEntry).href);

const requestText = await new Promise((resolve) => {
  let value = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => value += chunk);
  process.stdin.on('end', () => resolve(value));
});
// MCP SDK intentionally filters inherited environment variables by default.
// Forward only the standard Windows runtime values and explicit REA/Ghidra
// configuration; do not leak unrelated process secrets into the analyzer.
const childEnv = {};
const forwardedEnvNames = new Set([
  'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
  'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA',
  'COMSPEC', 'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'PROCESSOR_LEVEL',
  'PROCESSOR_REVISION', 'PROCESSOR_IDENTIFIER', 'NUMBER_OF_PROCESSORS', 'OS',
  'JAVA_HOME', 'GHIDRA_INSTALL_DIR', 'REA_ANALYSIS_PROVIDER',
  'REA_GHIDRA_STARTUP_TIMEOUT_MS', 'REA_GHIDRA_LANGUAGE_ID',
  'REA_GHIDRA_COMPILER_SPEC_ID', 'REA_GHIDRA_DISABLED_ANALYZERS',
  'REA_GHIDRA_SEED_FILE', 'REA_GHIDRA_NATIVEAOT_JAR', 'REA_IDA_MCP_CONFIG',
  'REA_MCP_MAX_RESPONSE_BYTES', 'REA_MCP_INPUT_SCHEMA_PROFILE',
  'REA_MCP_OUTPUT_SCHEMA_PROFILE', 'REA_LOG_LEVEL',
  'MYRA_REA_ALLOWED_ROOTS', 'MYRA_WORKSPACE'
]);
for (const [key, value] of Object.entries(process.env)) {
  if (forwardedEnvNames.has(key.toUpperCase())) childEnv[key] = value;
}
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [path.join(packageRoot, 'scripts', 'rea.mjs'), '--mcp'],
  cwd: process.env.MYRA_WORKSPACE || process.cwd(),
  env: childEnv,
  stderr: 'pipe'
});
const client = new Client({ name: 'myra-rea-bridge', version: '0.1.0' });
try {
  await client.connect(transport);
  if (mode === 'list') {
    const result = await client.listTools();
    console.log(JSON.stringify({ status: 'ok', count: result.tools.length, tools: result.tools.map(t => ({ name: t.name, description: t.description || '', inputSchema: t.inputSchema || {} })) }));
  } else if (mode === 'call') {
    const request = JSON.parse(requestText || '{}');
    if (typeof request.name !== 'string' || !request.arguments || typeof request.arguments !== 'object' || Array.isArray(request.arguments)) throw new Error('Formato de chamada invalido.');
    const timeoutMs = request.timeoutMs === undefined ? 60000 : request.timeoutMs;
    if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 300000) {
      throw new Error('timeoutMs precisa ser um inteiro entre 1000 e 300000.');
    }
    const deadlineAt = Date.now() + timeoutMs;
    const callOptions = () => {
      const remainingMs = Math.max(1, deadlineAt - Date.now());
      return { timeout: remainingMs, maxTotalTimeout: remainingMs, resetTimeoutOnProgress: true };
    };
    // Each CLI invocation owns a fresh MCP process. Re-open a previously validated
    // target in this same session before context-dependent read-only operations.
    if (typeof request.openTarget === 'string' && request.openTarget.length > 0 && request.name !== 'open_binary') {
      const opened = await client.callTool(
        { name: 'open_binary', arguments: { path: request.openTarget } },
        callOptions()
      );
      if (opened.isError) throw new Error('Nao foi possivel restaurar o alvo REA ativo: ' + JSON.stringify(opened.content || []).slice(0, 1000));
    }
    const result = await client.callTool(
      { name: request.name, arguments: request.arguments },
      callOptions()
    );
    console.log(JSON.stringify({ status: result.isError ? 'erro' : 'ok', result }));
  } else {
    throw new Error('Modo nao suportado.');
  }
} catch (error) {
  console.log(JSON.stringify({ status: 'erro', result: String(error?.message || error).slice(0, 3000) }));
  process.exitCode = 1;
} finally {
  await transport.close().catch(() => {});
}
