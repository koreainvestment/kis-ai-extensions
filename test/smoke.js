'use strict'

const { spawnSync } = require('child_process')
const assert = require('node:assert/strict')
const path = require('path')
const fs = require('fs')
const os = require('os')

function run(...args) {
  return spawnSync('node', ['bin/cli.js', ...args], { encoding: 'utf8', timeout: 5000 })
}

// 1. --help → exit 0
assert.strictEqual(run('--help').status, 0, '--help should exit 0')

// 2. --version → exit 0
assert.strictEqual(run('--version').status, 0, '--version should exit 0')

// 3. import safety — require should not auto-execute
const importResult = spawnSync('node', ['-e', "require('./bin/cli.js')"], {
  encoding: 'utf8',
  timeout: 5000,
})
assert.strictEqual(importResult.status, 0, 'require should not auto-execute')

// 4. unknown command → exit 1
assert.strictEqual(run('bogus').status, 1, 'unknown command should exit 1')

// 5. shared/ directory structure exists in source
assert.ok(fs.existsSync('shared/skills/kis-strategy-builder/SKILL.md'), 'shared skills must exist')
assert.ok(fs.existsSync('shared/commands/auth.md'), 'shared commands must exist')
assert.ok(fs.existsSync('shared/scripts/api_client.py'), 'shared scripts must exist')
assert.ok(fs.existsSync('shared/hooks/kis-secret-guard.sh.tmpl'), 'shared hook templates must exist')
assert.ok(fs.existsSync('shared/agents.md'), 'shared agents.md must exist')

// 6. agents/ directory structure exists
assert.ok(fs.existsSync('agents/claude/hooks.json'), 'Claude hooks.json must exist')
assert.ok(fs.existsSync('agents/cursor/hooks.json'), 'Cursor hooks.json must exist')
assert.ok(fs.existsSync('agents/codex/config.toml'), 'Codex config.toml must exist')
assert.ok(fs.existsSync('agents/gemini/settings.json.tmpl'), 'Gemini settings template must exist')
assert.ok(fs.existsSync('agents/gemini/commands/auth.toml'), 'Gemini TOML commands must exist')
assert.ok(fs.existsSync('agents/codex/commands/auth/SKILL.md'), 'Codex command overrides must exist')

// 7. init --agent claude in temp directory (requires strategy_builder/ and backtester/)
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kis-smoke-'))
fs.mkdirSync(path.join(tmpDir, 'strategy_builder'))
fs.mkdirSync(path.join(tmpDir, 'backtester'))
const initResult = spawnSync('node', [path.join(process.cwd(), 'bin/cli.js'), 'init', '--agent', 'claude'], {
  encoding: 'utf8',
  timeout: 10000,
  cwd: tmpDir,
})
assert.strictEqual(initResult.status, 0, `init --agent claude should exit 0. stderr: ${initResult.stderr}`)
assert.ok(fs.existsSync(path.join(tmpDir, '.claude', 'scripts', 'setup_check.py')), '.claude/scripts/ must be created')
assert.ok(fs.existsSync(path.join(tmpDir, '.claude', 'skills', 'kis-strategy-builder', 'SKILL.md')), '.claude/skills/ must be created')
assert.ok(fs.existsSync(path.join(tmpDir, '.claude', 'commands', 'auth.md')), '.claude/commands/ must be created')
assert.ok(fs.existsSync(path.join(tmpDir, '.claude', 'hooks', 'kis-secret-guard.sh')), '.claude/hooks/ must be created')
assert.ok(fs.existsSync(path.join(tmpDir, '.claude', 'hooks', 'hooks.json')), '.claude/hooks/hooks.json must be created')
assert.ok(fs.existsSync(path.join(tmpDir, '.mcp.json')), '.mcp.json must be created')
assert.ok(fs.existsSync(path.join(tmpDir, 'AGENTS.md')), 'AGENTS.md must be created')

// 8. Verify hook content has correct env var
const hookContent = fs.readFileSync(path.join(tmpDir, '.claude', 'hooks', 'kis-prod-guard.sh'), 'utf8')
assert.ok(hookContent.includes('CLAUDE_PROJECT_DIR'), 'Claude hooks must use CLAUDE_PROJECT_DIR')
assert.ok(!hookContent.includes('{{'), 'hooks must not contain unrendered template variables')

// 9. Verify create_settings.sh has new MCP prefixes
const settingsScript = fs.readFileSync(path.join(tmpDir, '.claude', 'scripts', 'create_settings.sh'), 'utf8')
assert.ok(!settingsScript.includes('mcp__plugin_'), 'create_settings.sh must not contain plugin-era prefix')
assert.ok(settingsScript.includes('mcp__kis-backtest__'), 'create_settings.sh must use new MCP prefix')

// 10. doctor in the temp directory
const doctorResult = spawnSync('node', [path.join(process.cwd(), 'bin/cli.js'), 'doctor'], {
  encoding: 'utf8',
  timeout: 10000,
  cwd: tmpDir,
})
assert.strictEqual(doctorResult.status, 0, 'doctor should exit 0')

// Cleanup
fs.rmSync(tmpDir, { recursive: true, force: true })

console.log('Smoke tests passed.')
