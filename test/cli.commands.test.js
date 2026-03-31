'use strict'

const { describe, it } = require('node:test')
const assert = require('node:assert/strict')
const path = require('path')
const {
  main, cmdDoctor, cmdUpdate, cmdInit, commandExists, getCommandVersion,
  VERSION, PKG_NAME, AGENT_VARS, AGENT_LABELS,
} = require('../bin/cli.js')

const FAKE_CWD = path.join(path.sep, 'fake', 'cwd')
const FAKE_HOME = path.join(path.sep, 'fake', 'home')

function makeDeps(overrides = {}) {
  const output = []
  const exits = []
  const written = {}
  const base = {
    fs: {
      existsSync: () => true,
      mkdirSync: () => {},
      readdirSync: (dir, opts) => {
        if (opts && opts.withFileTypes) return []
        return []
      },
      copyFileSync: () => {},
      statSync: () => ({ isDirectory: () => false }),
      chmodSync: () => {},
      readFileSync: () => '',
      writeFileSync: (p, content) => { written[p] = content },
    },
    execSync: () => '',
    cwd: () => FAKE_CWD,
    exit: (code) => exits.push(code),
    env: { TERM: 'xterm', NO_COLOR: '1' },
    isTTY: { stdin: false, stdout: false },
    homedir: () => FAKE_HOME,
    print: (...args) => output.push(args.join(' ')),
    printErr: (...args) => output.push(`ERR:${args.join(' ')}`),
    createReadline: () => ({ question: (q, cb) => cb(''), close: () => {} }),
  }
  const merged = { ...base, ...overrides }
  if (overrides.fs) {
    merged.fs = { ...base.fs, ...overrides.fs }
  }
  return { deps: merged, output, exits, written }
}

// ── commandExists / getCommandVersion ───────────────────────────────────────

describe('commandExists', () => {
  it('returns true when command exists', () => {
    const { deps } = makeDeps({ execSync: () => '' })
    assert.strictEqual(commandExists('node', deps), true)
  })

  it('returns false when command does not exist', () => {
    const { deps } = makeDeps({
      execSync: () => { throw new Error('not found') },
    })
    assert.strictEqual(commandExists('bogus', deps), false)
  })
})

describe('getCommandVersion', () => {
  it('returns version string', () => {
    const { deps } = makeDeps({ execSync: () => 'v1.0.0\n' })
    assert.strictEqual(getCommandVersion('node', deps), 'v1.0.0')
  })
})

// ── main() ──────────────────────────────────────────────────────────────────

describe('main', () => {
  it('shows help when no args', async () => {
    const { deps, output, exits } = makeDeps()
    await main([], deps)
    assert.strictEqual(exits.length, 0)
    assert.ok(output.some((line) => line.includes('Usage')))
  })

  it('shows version with --version', async () => {
    const { deps, output, exits } = makeDeps()
    await main(['--version'], deps)
    assert.strictEqual(exits.length, 0)
    assert.ok(output.some((line) => line.includes(VERSION)))
  })

  it('exits 1 on unknown command', async () => {
    const { deps, exits } = makeDeps()
    await main(['bogus-command'], deps)
    assert.deepStrictEqual(exits, [1])
  })

  it('shows new package name in help', async () => {
    const { deps, output } = makeDeps()
    await main([], deps)
    assert.ok(output.some((line) => line.includes(PKG_NAME)))
  })
})

// ── cmdDoctor() ─────────────────────────────────────────────────────────────

describe('cmdDoctor', () => {
  it('succeeds when all tools exist', () => {
    const { deps, output, exits } = makeDeps({
      execSync: () => 'v1.0.0\n',
    })
    cmdDoctor({ agent: null }, deps)
    assert.strictEqual(exits.length, 0)
    assert.ok(output.some((line) => line.includes('Environment looks good')))
  })

  it('reports error when required tool is missing', () => {
    const { deps, output } = makeDeps({
      execSync: () => { throw new Error('not found') },
    })
    cmdDoctor({ agent: null }, deps)
    assert.ok(output.some((line) => line.includes('not found') && line.includes('required')))
  })

  it('reports warning for optional tool missing', () => {
    const { deps, output } = makeDeps({
      execSync: (cmd) => {
        if (cmd.includes('docker')) throw new Error('not found')
        return 'v1.0.0\n'
      },
    })
    cmdDoctor({ agent: null }, deps)
    const dockerWarning = output.some((line) => line.includes('Docker') && line.includes('not found'))
    assert.ok(dockerWarning, 'should warn about missing Docker')
  })

  it('accepts --agent option to filter checks', () => {
    const { deps, output } = makeDeps({
      execSync: () => 'v1.0.0\n',
    })
    cmdDoctor({ agent: 'claude' }, deps)
    assert.ok(output.some((line) => line.includes('Claude Code')))
  })
})

// ── cmdUpdate() ─────────────────────────────────────────────────────────────

describe('cmdUpdate', () => {
  it('shows new version available', () => {
    const { deps, output } = makeDeps({
      execSync: () => '99.0.0\n',
    })
    cmdUpdate(deps)
    assert.ok(output.some((line) => line.includes('99.0.0')))
  })

  it('shows latest when version matches', () => {
    const { deps, output } = makeDeps({
      execSync: () => `${VERSION}\n`,
    })
    cmdUpdate(deps)
    assert.ok(output.some((line) => line.includes('latest')))
  })

  it('warns when npm check fails', () => {
    const { deps, output } = makeDeps({
      execSync: () => { throw new Error('network error') },
    })
    cmdUpdate(deps)
    assert.ok(output.some((line) => line.includes('npm registry') || line.includes('not be published')))
  })

  it('uses new package name for npm view', () => {
    let viewedPkg = null
    const { deps } = makeDeps({
      execSync: (cmd) => {
        if (cmd.includes('npm view')) viewedPkg = cmd
        return `${VERSION}\n`
      },
    })
    cmdUpdate(deps)
    assert.ok(viewedPkg.includes(PKG_NAME))
  })
})

// ── cmdInit() (non-interactive) ─────────────────────────────────────────────

describe('cmdInit', () => {
  it('exits 1 when repo not detected and non-TTY', async () => {
    const { deps, exits } = makeDeps({
      fs: { existsSync: () => false },
      isTTY: { stdin: false, stdout: false },
    })
    await cmdInit({ _: ['init'], agent: null, force: false }, deps)
    assert.deepStrictEqual(exits, [1])
  })

  it('exits 1 on unknown agent', async () => {
    const { deps, output, exits } = makeDeps()
    await cmdInit({ _: ['init'], agent: 'bogus', force: false }, deps)
    assert.deepStrictEqual(exits, [1])
    assert.ok(output.some((line) => line.includes('Unknown agent')))
  })

  it('exits 1 when --agent value is missing', async () => {
    const { deps, output, exits } = makeDeps()
    await cmdInit({ _: ['init'], agent: undefined, force: false }, deps)
    assert.deepStrictEqual(exits, [1])
    assert.ok(output.some((line) => line.includes('--agent requires a value')))
  })

  it('succeeds with --agent all', async () => {
    const { deps, output, exits } = makeDeps()
    await cmdInit({ _: ['init'], agent: 'all', force: false }, deps)
    assert.strictEqual(exits.length, 0)
    assert.ok(output.some((line) => line.includes('Done!')))
  })

  it('clones to subdirectory when interactive and user accepts', async () => {
    let clonedCmd = null
    let cloned = false
    const cloneRoot = path.join(FAKE_CWD, 'open-trading-api')
    const cloneSb = path.join(cloneRoot, 'strategy_builder')
    const cloneBt = path.join(cloneRoot, 'backtester')
    const { deps, output, exits } = makeDeps({
      fs: {
        existsSync: (p) => {
          if (p === path.join(FAKE_CWD, 'strategy_builder') || p === path.join(FAKE_CWD, 'backtester')) return false
          if (p === cloneRoot) return cloned
          if (p === cloneSb) return cloned
          if (p === cloneBt) return cloned
          if (p.startsWith(`${cloneRoot}${path.sep}`)) return false
          if (p.startsWith(`${FAKE_CWD}${path.sep}`)) return false
          return true
        },
        mkdirSync: () => {},
        readdirSync: (dir, opts) => {
          if (opts && opts.withFileTypes) return []
          return []
        },
        copyFileSync: () => {},
        statSync: () => ({ isDirectory: () => false }),
        chmodSync: () => {},
        readFileSync: () => '',
        writeFileSync: () => {},
      },
      isTTY: { stdin: true, stdout: true },
      createReadline: () => ({
        question: (_q, cb) => cb('y'),
        close: () => {},
      }),
      execSync: (cmd) => { clonedCmd = cmd; cloned = true; return '' },
    })
    await cmdInit({ _: ['init'], agent: 'all', force: false }, deps)
    assert.strictEqual(exits.length, 0)
    assert.ok(clonedCmd.includes('git clone'))
    assert.ok(output.some((line) => line.includes('Clone complete')))
    assert.ok(output.some((line) => line.includes('Cloned to subdirectory')))
    assert.ok(output.some((line) => line.includes('cd open-trading-api')))
    assert.ok(output.some((line) => line.includes('Done!')))
  })

  it('reuses existing valid open-trading-api subdirectory', async () => {
    let clonedCmd = null
    const cloneRoot = path.join(FAKE_CWD, 'open-trading-api')
    const cloneSb = path.join(cloneRoot, 'strategy_builder')
    const cloneBt = path.join(cloneRoot, 'backtester')
    const { deps, exits, output } = makeDeps({
      fs: {
        existsSync: (p) => {
          if (p === path.join(FAKE_CWD, 'strategy_builder') || p === path.join(FAKE_CWD, 'backtester')) return false
          if (p === cloneRoot) return true
          if (p === cloneSb) return true
          if (p === cloneBt) return true
          if (p.startsWith(`${cloneRoot}${path.sep}`)) return false
          if (p.startsWith(`${FAKE_CWD}${path.sep}`)) return false
          return true
        },
        mkdirSync: () => {},
        readdirSync: (dir, opts) => {
          if (opts && opts.withFileTypes) return []
          return []
        },
        copyFileSync: () => {},
        statSync: () => ({ isDirectory: () => false }),
        chmodSync: () => {},
        readFileSync: () => '',
        writeFileSync: () => {},
      },
      isTTY: { stdin: true, stdout: true },
      execSync: (cmd) => { clonedCmd = cmd; return '' },
    })
    await cmdInit({ _: ['init'], agent: 'all', force: false }, deps)
    assert.strictEqual(exits.length, 0)
    assert.strictEqual(clonedCmd, null, 'should reuse existing subdirectory instead of cloning')
    assert.ok(output.some((line) => line.includes('Reusing it')))
    assert.ok(output.some((line) => line.includes('Using existing subdirectory')))
    assert.ok(output.some((line) => line.includes('Done!')))
  })

  it('exits 1 when existing subdirectory is invalid', async () => {
    const cloneRoot = path.join(FAKE_CWD, 'open-trading-api')
    const { deps, exits, output } = makeDeps({
      fs: {
        existsSync: (p) => {
          if (p === path.join(FAKE_CWD, 'strategy_builder')) return true
          if (p === path.join(FAKE_CWD, 'backtester')) return false
          if (p === cloneRoot) return true
          return false
        },
      },
      isTTY: { stdin: true, stdout: true },
    })
    await cmdInit({ _: ['init'], agent: null, force: false }, deps)
    assert.deepStrictEqual(exits, [1])
    assert.ok(output.some((line) => line.includes('not a valid open-trading-api checkout')))
  })

  it('succeeds with --force (no skip warnings)', async () => {
    const { deps, output, exits } = makeDeps()
    await cmdInit({ _: ['init'], agent: 'all', force: true }, deps)
    assert.strictEqual(exits.length, 0)
    const hasAlreadyExists = output.some((line) => line.includes('Already exists'))
    assert.strictEqual(hasAlreadyExists, false, 'should not have "Already exists" warnings with --force')
    assert.ok(output.some((line) => line.includes('Done!')))
  })
})

// ── MCP prefix regression ──────────────────────────────────────────────────

describe('MCP prefix', () => {
  it('create_settings.sh must not contain plugin-era MCP prefix', () => {
    const fs = require('fs')
    const content = fs.readFileSync(path.join(__dirname, '..', 'shared', 'scripts', 'create_settings.sh'), 'utf8')
    assert.ok(!content.includes('mcp__plugin_'), 'must not contain plugin-era MCP prefix')
  })

  it('create_settings.sh must have exactly 11 MCP permission entries', () => {
    const fs = require('fs')
    const content = fs.readFileSync(path.join(__dirname, '..', 'shared', 'scripts', 'create_settings.sh'), 'utf8')
    const matches = content.match(/mcp__kis-backtest__/g) || []
    assert.strictEqual(matches.length, 11, 'must have exactly 11 MCP permission entries')
  })
})
