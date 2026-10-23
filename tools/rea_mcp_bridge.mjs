import { Client } from 'file:///C:/Users/Administrator/AppData/Local/npm-cache/_npx/ad9a3fdbcad992c6/node_modules/@modelcontextprotocol/client/dist/index.mjs';
import { StdioClientTransport } from 'file:///C:/Users/Administrator/AppData/Local/npm-cache/_npx/ad9a3fdbcad992c6/node_modules/@modelcontextprotocol/client/dist/stdio.mjs';

const packageRoot = 'C:/Users/Administrator/AppData/Local/npm-cache/_npx/ad9a3fdbcad992c6/node_modules/rea-agents';
const mode = process.argv[2] || 'list';
const requestText = await new Promise((resolve) => {
  let value = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => value += chunk);
  process.stdin.on('end', () => resolve(value));
});
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [packageRoot + '/scripts/rea.mjs', '--mcp'],
  cwd: 'C:/computer-agent/workspace',
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
    const result = await client.callTool({ name: request.name, arguments: request.arguments });
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
