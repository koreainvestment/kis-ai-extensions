#!/usr/bin/env node

'use strict'

const path = require('path')

// ── Constants ──────────────────────────────────────────────────────────────────

const VERSION = require('../package.json').version
const PLUGIN_ROOT = path.resolve(__dirname, '..')
const PKG_NAME = '@koreainvestment/kis-quant-plugin'

const AGENT_VARS = {
  claude: {
    AGENT_DIR: '.claude',
    PROJECT_DIR_VAR: 'CLAUDE_PROJECT_DIR',
    LOG_DIR: '.claude/logs',
    BLOCK_EXIT: '1',
    SCRIPTS_PATH: '.claude/scripts',
  },
  cursor: {
    AGENT_DIR: '.cursor',
    PROJECT_DIR_VAR: 'CURSOR_PROJECT_DIR',
    LOG_DIR: '.cursor/logs',
    BLOCK_EXIT: '1',
    SCRIPTS_PATH: '.cursor/scripts',
  },
  codex: {
    AGENT_DIR: '.codex',
    PROJECT_DIR_VAR: 'CODEX_PROJECT_DIR',
    LOG_DIR: '.codex/logs',
    BLOCK_EXIT: '1',
    SCRIPTS_PATH: '.codex/scripts',
  },
  gemini: {
    AGENT_DIR: '.gemini',
    PROJECT_DIR_VAR: 'GEMINI_PROJECT_DIR',
    LOG_DIR: '.gemini/logs',
    BLOCK_EXIT: '2',
    SCRIPTS_PATH: '.gemini/scripts',
  },
}

const AGENT_LABELS = {
  claude: 'Claude Code',
  cursor: 'Cursor',
  codex: 'Codex',
  gemini: 'Gemini CLI',
}

// ── Default Dependencies ────────────────────────────────────────────────────────

const defaultDeps = {
  fs: require('fs'),
  execSync: require('child_process').execSync,
  cwd: () => process.cwd(),
  exit: (code) => process.exit(code),
  env: process.env,
  isTTY: { stdin: process.stdin.isTTY, stdout: process.stdout.isTTY },
  homedir: () => require('os').homedir(),
  print: (...args) => console.log(...args),
  printErr: (...args) => console.error(...args),
  createReadline: () => require('readline').createInterface({
    input: process.stdin, output: process.stdout,
  }),
}

// ── Utility ────────────────────────────────────────────────────────────────────

function log(deps, msg) { deps.print(`  ${msg}`) }
function success(deps, msg) { deps.print(`  \u2713 ${msg}`) }
function warn(deps, msg) { deps.print(`  \u26a0 ${msg}`) }
function error(deps, msg) { deps.printErr(`  \u2717 ${msg}`) }

function banner(deps) {
  const useColor = deps.isTTY.stdout && deps.env.TERM !== 'dumb' && !deps.env.NO_COLOR
  const blue = (line) => useColor ? `\x1b[34m${line}\x1b[0m` : line

  deps.print()
  deps.print(blue('  _  ___ ____'))
  deps.print(blue(' | |/ /_ _/ ___|'))
  deps.print(blue(" | ' / | |\\___ \\"))
  deps.print(blue(' | . \\ | | ___) |'))
  deps.print(blue(' |_|\\_\\___|____/'))
  deps.print(blue('  Korea Investment & Securities'))
  deps.print(blue(`  KIS Plugin Installer v${VERSION}`))
  deps.print()
}

function commandExists(cmd, deps = defaultDeps) {
  try {
    deps.execSync(`which ${cmd}`, { stdio: 'ignore' })
    return true
  } catch {
    return false
  }
}

function getCommandVersion(cmd, deps = defaultDeps) {
  try {
    return deps.execSync(`${cmd} --version`, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] }).trim().split('\n')[0]
  } catch {
    return null
  }
}

function copyRecursive(src, dest, deps = defaultDeps) {
  const stat = deps.fs.statSync(src)
  if (stat.isDirectory()) {
    deps.fs.mkdirSync(dest, { recursive: true })
    for (const entry of deps.fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry), deps)
    }
  } else {
    deps.fs.mkdirSync(path.dirname(dest), { recursive: true })
    deps.fs.copyFileSync(src, dest)
  }
}

function parseArgs(argv) {
  const args = { _: [], agent: null, help: false, version: false, force: false }
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '--help' || arg === '-h') {
      args.help = true
    } else if (arg === '--version' || arg === '-v') {
      args.version = true
    } else if (arg === '--force' || arg === '-f') {
      args.force = true
    } else if (arg === '--agent' || arg === '-a') {
      args.agent = argv[++i]
    } else if (arg.startsWith('--agent=')) {
      args.agent = arg.split('=')[1]
    } else if (!arg.startsWith('-')) {
      args._.push(arg)
    }
  }
  return args
}

// ── Template Engine ───────────────────────────────────────────────────────────

function renderTemplate(content, vars) {
  return Object.entries(vars).reduce(
    (text, [key, value]) => text.replaceAll(`{{${key}}}`, value),
    content
  )
}

// ── chmod helper ──────────────────────────────────────────────────────────────

function chmodShellScripts(dir, deps) {
  if (!deps.fs.existsSync(dir)) return
  for (const entry of deps.fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      chmodShellScripts(full, deps)
    } else if (entry.name.endsWith('.sh')) {
      deps.fs.chmodSync(full, 0o755)
    }
  }
}

// ── assembleAgent ─────────────────────────────────────────────────────────────

function assembleAgent(agentKey, cwd, args, deps) {
  const vars = AGENT_VARS[agentKey]
  const agentDir = path.join(cwd, vars.AGENT_DIR)
  let copied = 0

  function install(srcPath, destPath) {
    if (!deps.fs.existsSync(srcPath)) {
      warn(deps, `Source not found: ${path.relative(PLUGIN_ROOT, srcPath)} (skipped)`)
      return false
    }
    const destExists = deps.fs.existsSync(destPath)
    if (destExists && !args.force) {
      warn(deps, `Already exists: ${path.relative(cwd, destPath)} (use --force to overwrite)`)
      return false
    }
    copyRecursive(srcPath, destPath, deps)
    success(deps, path.relative(cwd, destPath))
    copied++
    return true
  }

  function installRendered(srcPath, destPath) {
    if (!deps.fs.existsSync(srcPath)) {
      warn(deps, `Source not found: ${path.relative(PLUGIN_ROOT, srcPath)} (skipped)`)
      return false
    }
    const destExists = deps.fs.existsSync(destPath)
    if (destExists && !args.force) {
      warn(deps, `Already exists: ${path.relative(cwd, destPath)} (use --force to overwrite)`)
      return false
    }
    const content = deps.fs.readFileSync(srcPath, 'utf8')
    const rendered = renderTemplate(content, vars)
    deps.fs.mkdirSync(path.dirname(destPath), { recursive: true })
    deps.fs.writeFileSync(destPath, rendered)
    success(deps, path.relative(cwd, destPath))
    copied++
    return true
  }

  // ── Common: scripts ──
  const sharedScripts = path.join(PLUGIN_ROOT, 'shared', 'scripts')
  for (const py of ['api_client.py', 'auth.py', 'do_auth.py', 'setup_check.py']) {
    install(path.join(sharedScripts, py), path.join(agentDir, 'scripts', py))
  }

  // ── Common: skills (with template rendering) ──
  const sharedSkills = path.join(PLUGIN_ROOT, 'shared', 'skills')
  if (deps.fs.existsSync(sharedSkills)) {
    for (const skillName of deps.fs.readdirSync(sharedSkills)) {
      const skillSrc = path.join(sharedSkills, skillName)
      const skillDest = path.join(agentDir, 'skills', skillName)
      if (deps.fs.statSync(skillSrc).isDirectory()) {
        installRenderedDir(skillSrc, skillDest, vars, args, cwd, deps, () => { copied++ })
      }
    }
  }

  // ── Common: commands (with override pattern) ──
  // Codex: uses agents/codex/commands/ entirely (directory-based skills)
  // Gemini: uses agents/gemini/commands/ entirely (TOML format)
  // Claude/Cursor: shared/commands/*.md with agent-specific overrides
  if (agentKey === 'codex') {
    // Codex commands go to skills/ (directory-based)
    const codexCmds = path.join(PLUGIN_ROOT, 'agents', 'codex', 'commands')
    if (deps.fs.existsSync(codexCmds)) {
      for (const cmdDir of deps.fs.readdirSync(codexCmds)) {
        const cmdSrc = path.join(codexCmds, cmdDir)
        if (deps.fs.statSync(cmdSrc).isDirectory()) {
          install(cmdSrc, path.join(agentDir, 'skills', cmdDir))
        }
      }
    }
  } else if (agentKey === 'gemini') {
    // Gemini commands are TOML, no rendering needed
    const geminiCmds = path.join(PLUGIN_ROOT, 'agents', 'gemini', 'commands')
    if (deps.fs.existsSync(geminiCmds)) {
      for (const toml of deps.fs.readdirSync(geminiCmds)) {
        install(
          path.join(geminiCmds, toml),
          path.join(agentDir, 'commands', toml)
        )
      }
    }
  } else {
    // Claude / Cursor: shared commands with optional overrides
    const sharedCmds = path.join(PLUGIN_ROOT, 'shared', 'commands')
    const overrideCmds = path.join(PLUGIN_ROOT, 'agents', agentKey, 'commands')
    if (deps.fs.existsSync(sharedCmds)) {
      for (const cmdFile of deps.fs.readdirSync(sharedCmds)) {
        const overridePath = path.join(overrideCmds, cmdFile)
        if (deps.fs.existsSync(overridePath)) {
          // Use override (already has correct paths, render template just in case)
          installRendered(overridePath, path.join(agentDir, 'commands', cmdFile))
        } else {
          installRendered(path.join(sharedCmds, cmdFile), path.join(agentDir, 'commands', cmdFile))
        }
      }
    }
  }

  // ── Common: logs directory ──
  deps.fs.mkdirSync(path.join(agentDir, 'logs'), { recursive: true })

  // ── Common: AGENTS.md ──
  install(path.join(PLUGIN_ROOT, 'shared', 'agents.md'), path.join(cwd, 'AGENTS.md'))

  // ── Agent-specific steps ──
  if (agentKey === 'claude') {
    assembleClaude(agentDir, cwd, vars, args, deps, install, installRendered, () => { copied++ })
  } else if (agentKey === 'cursor') {
    assembleCursor(agentDir, cwd, vars, args, deps, install, installRendered, () => { copied++ })
  } else if (agentKey === 'codex') {
    assembleCodex(agentDir, cwd, args, deps, install)
  } else if (agentKey === 'gemini') {
    assembleGemini(agentDir, cwd, vars, args, deps, install, installRendered, () => { copied++ })
  }

  // ── chmod all .sh files under {AGENT_DIR}/hooks/ ──
  chmodShellScripts(path.join(agentDir, 'hooks'), deps)

  // ── chmod codex-local.sh if present ──
  const localLauncher = path.join(cwd, 'codex-local.sh')
  if (deps.fs.existsSync(localLauncher)) {
    try { deps.fs.chmodSync(localLauncher, 0o755) } catch { /* ignore */ }
  }

  return copied
}

function installRenderedDir(srcDir, destDir, vars, args, cwd, deps, onCopy) {
  if (!deps.fs.existsSync(srcDir)) return
  deps.fs.mkdirSync(destDir, { recursive: true })
  for (const entry of deps.fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name)
    const destPath = path.join(destDir, entry.name)
    if (entry.isDirectory()) {
      installRenderedDir(srcPath, destPath, vars, args, cwd, deps, onCopy)
    } else {
      const destExists = deps.fs.existsSync(destPath)
      if (destExists && !args.force) {
        warn(deps, `Already exists: ${path.relative(cwd, destPath)} (use --force to overwrite)`)
        continue
      }
      const content = deps.fs.readFileSync(srcPath, 'utf8')
      const rendered = renderTemplate(content, vars)
      deps.fs.mkdirSync(path.dirname(destPath), { recursive: true })
      deps.fs.writeFileSync(destPath, rendered)
      success(deps, path.relative(cwd, destPath))
      onCopy()
    }
  }
}

function assembleClaude(agentDir, cwd, vars, args, deps, install, installRendered, onCopy) {
  // hooks from templates
  const sharedHooks = path.join(PLUGIN_ROOT, 'shared', 'hooks')
  if (deps.fs.existsSync(sharedHooks)) {
    for (const tmpl of deps.fs.readdirSync(sharedHooks).filter((f) => f.endsWith('.sh.tmpl'))) {
      const destName = tmpl.replace('.tmpl', '')
      installRendered(
        path.join(sharedHooks, tmpl),
        path.join(agentDir, 'hooks', destName)
      )
    }
  }

  // hooks.json
  install(
    path.join(PLUGIN_ROOT, 'agents', 'claude', 'hooks.json'),
    path.join(agentDir, 'hooks', 'hooks.json')
  )

  // .mcp.json at project root
  const mcpDest = path.join(cwd, '.mcp.json')
  const mcpExists = deps.fs.existsSync(mcpDest)
  if (!mcpExists || args.force) {
    const mcpContent = JSON.stringify({
      mcpServers: {
        'kis-backtest': {
          type: 'http',
          url: 'http://127.0.0.1:3846/mcp',
          description: 'KIS 전략 백테스팅 MCP 서버 — backtester 로컬 실행 필요 (bash backtester/scripts/start_mcp.sh)',
        },
      },
    }, null, 2) + '\n'
    deps.fs.writeFileSync(mcpDest, mcpContent)
    success(deps, '.mcp.json')
    onCopy()
  } else {
    warn(deps, 'Already exists: .mcp.json (use --force to overwrite)')
  }

  // status_lines
  install(
    path.join(PLUGIN_ROOT, 'agents', 'claude', 'status_lines', 'kis_status_line.py'),
    path.join(agentDir, 'status_lines', 'kis_status_line.py')
  )

  // create_settings.sh
  install(
    path.join(PLUGIN_ROOT, 'shared', 'scripts', 'create_settings.sh'),
    path.join(agentDir, 'scripts', 'create_settings.sh')
  )
}

function assembleCursor(agentDir, cwd, vars, args, deps, install, installRendered, onCopy) {
  // Cursor-specific hooks (not from templates)
  const cursorHooksSrc = path.join(PLUGIN_ROOT, 'agents', 'cursor', 'hooks')
  if (deps.fs.existsSync(cursorHooksSrc)) {
    for (const f of deps.fs.readdirSync(cursorHooksSrc)) {
      install(
        path.join(cursorHooksSrc, f),
        path.join(agentDir, 'hooks', 'cursor', f)
      )
    }
  }

  // hooks.json
  install(
    path.join(PLUGIN_ROOT, 'agents', 'cursor', 'hooks.json'),
    path.join(agentDir, 'hooks', 'hooks.json')
  )

  // .mcp.json at project root
  const mcpDest = path.join(cwd, '.mcp.json')
  const mcpExists = deps.fs.existsSync(mcpDest)
  if (!mcpExists || args.force) {
    const mcpContent = JSON.stringify({
      mcpServers: {
        'kis-backtest': {
          type: 'http',
          url: 'http://127.0.0.1:3846/mcp',
          description: 'KIS 전략 백테스팅 MCP 서버 — backtester 로컬 실행 필요 (bash backtester/scripts/start_mcp.sh)',
        },
      },
    }, null, 2) + '\n'
    deps.fs.writeFileSync(mcpDest, mcpContent)
    success(deps, '.mcp.json')
    onCopy()
  } else {
    warn(deps, 'Already exists: .mcp.json (use --force to overwrite)')
  }

  // rules
  install(
    path.join(PLUGIN_ROOT, 'agents', 'cursor', 'rules', 'kis-safety.mdc'),
    path.join(agentDir, 'rules', 'kis-safety.mdc')
  )
}

function assembleCodex(agentDir, cwd, args, deps, install) {
  // config.toml
  install(
    path.join(PLUGIN_ROOT, 'agents', 'codex', 'config.toml'),
    path.join(agentDir, 'config.toml')
  )

  // rules
  install(
    path.join(PLUGIN_ROOT, 'agents', 'codex', 'rules', 'default.rules'),
    path.join(agentDir, 'rules', 'default.rules')
  )

  // codex-local.sh
  install(
    path.join(PLUGIN_ROOT, 'agents', 'codex', 'codex-local.sh'),
    path.join(cwd, 'codex-local.sh')
  )
}

function assembleGemini(agentDir, cwd, vars, args, deps, install, installRendered, onCopy) {
  // hooks from templates
  const sharedHooks = path.join(PLUGIN_ROOT, 'shared', 'hooks')
  if (deps.fs.existsSync(sharedHooks)) {
    for (const tmpl of deps.fs.readdirSync(sharedHooks).filter((f) => f.endsWith('.sh.tmpl'))) {
      const destName = tmpl.replace('.tmpl', '')
      installRendered(
        path.join(sharedHooks, tmpl),
        path.join(agentDir, 'hooks', destName)
      )
    }
  }

  // settings.json from template
  installRendered(
    path.join(PLUGIN_ROOT, 'agents', 'gemini', 'settings.json.tmpl'),
    path.join(agentDir, 'settings.json')
  )

  // gemini-extension.json
  install(
    path.join(PLUGIN_ROOT, 'agents', 'gemini', 'extension.json'),
    path.join(cwd, 'gemini-extension.json')
  )
}

// ── Interactive helpers ─────────────────────────────────────────────────────────

function askYesNo(prompt, deps = defaultDeps) {
  const rl = deps.createReadline()
  return new Promise((resolve) => {
    rl.question(`  ${prompt}`, (answer) => {
      rl.close()
      resolve(answer.trim().toLowerCase().startsWith('y'))
    })
  })
}

function selectAgentInteractive(detected, deps = defaultDeps) {
  const choices = Object.keys(AGENT_VARS)
  deps.print()
  log(deps, 'Select agent(s) to install:')
  deps.print()
  choices.forEach((key, i) => {
    const marker = detected.includes(key) ? ' (detected)' : ''
    log(deps, `  ${i + 1}) ${AGENT_LABELS[key]}${marker}`)
  })
  log(deps, `  ${choices.length + 1}) all`)
  deps.print()

  const rl = deps.createReadline()

  return new Promise((resolve) => {
    rl.question('  Enter number(s), comma-separated [default: detected or all]: ', (answer) => {
      rl.close()
      const trimmed = answer.trim()
      if (!trimmed) {
        resolve(detected.length > 0 ? detected : choices)
        return
      }
      const nums = trimmed.split(',').map((s) => parseInt(s.trim(), 10))
      const selected = nums
        .map((n) => (n === choices.length + 1 ? choices : [choices[n - 1]]))
        .flat()
        .filter(Boolean)
      resolve([...new Set(selected)])
    })
  })
}

// ── Commands ───────────────────────────────────────────────────────────────────

async function cmdInit(args, deps = defaultDeps) {
  banner(deps)

  if (args.agent === undefined || args.agent === '' || (typeof args.agent === 'string' && args.agent.startsWith('-'))) {
    error(deps, '--agent requires a value: claude, cursor, codex, gemini, or all')
    deps.exit(1); return
  }

  // 1. Validate cwd is open-trading-api
  let cwd = deps.cwd()
  let subdirMode = null
  const hasStrategyBuilder = deps.fs.existsSync(path.join(cwd, 'strategy_builder'))
  const hasBacktester = deps.fs.existsSync(path.join(cwd, 'backtester'))
  const cloneTarget = path.join(cwd, 'open-trading-api')
  const cloneTargetExists = deps.fs.existsSync(cloneTarget)
  const cloneTargetHasSB = deps.fs.existsSync(path.join(cloneTarget, 'strategy_builder'))
  const cloneTargetHasBT = deps.fs.existsSync(path.join(cloneTarget, 'backtester'))

  if (!hasStrategyBuilder || !hasBacktester) {
    if (cloneTargetHasSB && cloneTargetHasBT) {
      log(deps, 'Found existing open-trading-api subdirectory. Reusing it.')
      cwd = cloneTarget
      subdirMode = 'reused'
    } else {
      if (cloneTargetExists) {
        error(deps, `Existing subdirectory is not a valid open-trading-api checkout: ${cloneTarget}`)
        log(deps, 'Remove it, fix it, or cd into the correct repo and run init again.')
        deps.exit(1); return
      }

      const missing = [
        !hasStrategyBuilder && 'strategy_builder/',
        !hasBacktester && 'backtester/',
      ].filter(Boolean)

      error(deps, 'open-trading-api repo not detected.')
      log(deps, `Missing: ${missing.join(', ')}`)
      deps.print()

      if (hasStrategyBuilder || hasBacktester) {
        log(deps, 'Current directory looks like an incomplete open-trading-api checkout.')
        log(deps, 'Fix the checkout or move to a clean parent directory and run init again.')
        deps.exit(1); return
      }

      if (deps.isTTY.stdin) {
        const shouldClone = await askYesNo('Clone open-trading-api here? (y/n): ', deps)
        if (shouldClone) {
          log(deps, 'Cloning open-trading-api...')
          deps.print()
          try {
            deps.execSync('git clone https://github.com/koreainvestment/open-trading-api open-trading-api', {
              stdio: 'inherit',
              cwd,
            })
            deps.print()
            success(deps, 'Clone complete!')
            deps.print()

            cwd = cloneTarget
            subdirMode = 'cloned'

            const postCloneHasSB = deps.fs.existsSync(path.join(cwd, 'strategy_builder'))
            const postCloneHasBT = deps.fs.existsSync(path.join(cwd, 'backtester'))
            if (!postCloneHasSB || !postCloneHasBT) {
              const stillMissing = [
                !postCloneHasSB && 'strategy_builder/',
                !postCloneHasBT && 'backtester/',
              ].filter(Boolean)
              error(deps, `Clone succeeded but missing: ${stillMissing.join(', ')}`)
              deps.exit(1); return
            }
          } catch {
            error(deps, 'git clone failed. Check your network or git installation.')
            deps.exit(1); return
          }
        } else {
          log(deps, 'Aborted. Run again inside the open-trading-api directory.')
          deps.exit(0); return
        }
      } else {
        log(deps, 'Please clone and cd into the repo first:')
        deps.print()
        log(deps, '  git clone https://github.com/koreainvestment/open-trading-api')
        log(deps, '  cd open-trading-api')
        log(deps, `  npx ${PKG_NAME} init`)
        deps.print()
        deps.exit(1); return
      }
    }
  }

  success(deps, `open-trading-api detected: ${cwd}`)

  // 2. Determine target agents
  let targetAgents
  const allAgents = Object.keys(AGENT_VARS)

  if (args.agent) {
    const requested = args.agent.toLowerCase()
    if (requested === 'all') {
      targetAgents = allAgents
    } else {
      const keys = requested.split(',').map((s) => s.trim())
      const invalid = keys.filter((k) => !AGENT_VARS[k])
      if (invalid.length > 0) {
        error(deps, `Unknown agent(s): ${invalid.join(', ')}`)
        log(deps, `Available: ${allAgents.join(', ')}, all`)
        deps.exit(1); return
      }
      targetAgents = keys
    }
  } else {
    const detected = allAgents
      .filter((key) => deps.fs.existsSync(path.join(cwd, AGENT_VARS[key].AGENT_DIR)))

    if (detected.length > 0) {
      log(deps, `Detected agents: ${detected.map((k) => AGENT_LABELS[k]).join(', ')}`)
    }

    if (deps.isTTY.stdin) {
      targetAgents = await selectAgentInteractive(detected, deps)
    } else {
      targetAgents = detected.length > 0 ? detected : allAgents
    }
  }

  if (targetAgents.length === 0) {
    error(deps, 'No agents selected.')
    deps.exit(1); return
  }

  deps.print()
  log(deps, `Installing for: ${targetAgents.map((k) => AGENT_LABELS[k]).join(', ')}`)
  deps.print()

  // 3. Assemble each agent
  let totalCopied = 0

  for (const agentKey of targetAgents) {
    log(deps, `\u2500\u2500 ${AGENT_LABELS[agentKey]} \u2500\u2500`)
    totalCopied += assembleAgent(agentKey, cwd, args, deps)
    deps.print()
  }

  // 4. Summary
  deps.print('  \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550')
  success(deps, `Done! ${totalCopied} file(s) installed.`)
  deps.print()
  if (subdirMode === 'cloned') {
    log(deps, 'Cloned to subdirectory. Move into it first:')
    log(deps, '  cd open-trading-api')
    deps.print()
  } else if (subdirMode === 'reused') {
    log(deps, 'Using existing subdirectory. Move into it first:')
    log(deps, '  cd open-trading-api')
    deps.print()
  }
  log(deps, 'Next steps:')
  deps.print()
  log(deps, '  1. Set up Python environment:')
  log(deps, '     uv sync')
  deps.print()
  log(deps, '  2. Authenticate with KIS API:')
  log(deps, '     /auth vps          # \ubaa8\uc758\ud22c\uc790')
  log(deps, '     /auth prod         # \uc2e4\uc804\ud22c\uc790')
  deps.print()
  log(deps, '  3. Check environment:')
  log(deps, '     /kis-setup')
  deps.print()
  log(deps, '  4. Start MCP server (for backtesting):')
  log(deps, '     bash backtester/scripts/start_mcp.sh')
  deps.print()
}

function cmdDoctor(args, deps = defaultDeps) {
  banner(deps)
  log(deps, 'Environment Diagnosis')
  deps.print('  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')
  deps.print()

  const checks = [
    { name: 'Python', cmd: 'python3', versionCmd: 'python3 --version', required: true },
    { name: 'uv', cmd: 'uv', versionCmd: 'uv --version', required: true },
    { name: 'Node.js', cmd: 'node', versionCmd: 'node --version', required: true },
    { name: 'Docker', cmd: 'docker', versionCmd: 'docker --version', required: false },
    { name: 'Git', cmd: 'git', versionCmd: 'git --version', required: true },
  ]

  let hasError = false

  for (const check of checks) {
    const exists = commandExists(check.cmd, deps)
    const version = exists ? getCommandVersion(check.cmd, deps) : null
    const tag = check.required ? '(required)' : '(optional)'

    if (exists) {
      success(deps, `${check.name}: ${version || 'found'} ${tag}`)
    } else if (check.required) {
      error(deps, `${check.name}: not found ${tag}`)
      hasError = true
    } else {
      warn(deps, `${check.name}: not found ${tag}`)
    }
  }

  deps.print()
  log(deps, 'Project Structure')
  deps.print('  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')

  const cwd = deps.cwd()

  // Common checks
  const commonChecks = [
    { path: 'strategy_builder', label: 'strategy_builder/', required: true },
    { path: 'backtester', label: 'backtester/', required: true },
  ]

  for (const check of commonChecks) {
    const exists = deps.fs.existsSync(path.join(cwd, check.path))
    if (exists) {
      success(deps, check.label)
    } else {
      error(deps, `${check.label} \u2014 not found`)
      hasError = true
    }
  }

  // Determine which agents to check
  let agentsToCheck
  if (args && args.agent) {
    const requested = args.agent.toLowerCase()
    if (requested === 'all') {
      agentsToCheck = Object.keys(AGENT_VARS)
    } else {
      agentsToCheck = requested.split(',').map((s) => s.trim()).filter((k) => AGENT_VARS[k])
    }
  } else {
    // Auto-detect installed agents
    agentsToCheck = Object.keys(AGENT_VARS)
      .filter((key) => deps.fs.existsSync(path.join(cwd, AGENT_VARS[key].AGENT_DIR)))
  }

  const DOCTOR_AGENT_CHECKS = {
    claude: (ad) => [
      { path: `${ad}/hooks/hooks.json`, label: `${ad}/hooks/ (hooks config)` },
      { path: `${ad}/hooks/kis-secret-guard.sh`, label: `${ad}/hooks/ (security hooks)` },
      { path: `${ad}/commands/auth.md`, label: `${ad}/commands/` },
      { path: '.mcp.json', label: '.mcp.json (MCP config)' },
    ],
    cursor: (ad) => [
      { path: `${ad}/hooks/hooks.json`, label: `${ad}/hooks/ (hooks config)` },
      { path: `${ad}/commands/auth.md`, label: `${ad}/commands/` },
      { path: `${ad}/rules/kis-safety.mdc`, label: `${ad}/rules/ (safety rules)` },
      { path: '.mcp.json', label: '.mcp.json (MCP config)' },
    ],
    codex: (ad) => [
      { path: `${ad}/config.toml`, label: `${ad}/config.toml (Codex config)` },
      { path: `${ad}/rules/default.rules`, label: `${ad}/rules/ (approval rules)` },
    ],
    gemini: (ad) => [
      { path: `${ad}/settings.json`, label: `${ad}/settings.json (Gemini settings)` },
      { path: `${ad}/commands/auth.toml`, label: `${ad}/commands/ (TOML)` },
    ],
  }

  for (const agentKey of agentsToCheck) {
    const vars = AGENT_VARS[agentKey]
    const ad = vars.AGENT_DIR
    deps.print()
    log(deps, `${AGENT_LABELS[agentKey]} (${ad}/)`)

    // Per-agent common checks
    const perAgent = [
      { path: `${ad}/scripts/setup_check.py`, label: `${ad}/scripts/` },
      { path: `${ad}/skills/kis-strategy-builder/SKILL.md`, label: `${ad}/skills/` },
      { path: `${ad}/logs`, label: `${ad}/logs/` },
    ]

    const agentSpecific = DOCTOR_AGENT_CHECKS[agentKey] ? DOCTOR_AGENT_CHECKS[agentKey](ad) : []
    const allChecks = [...perAgent, ...agentSpecific]

    for (const check of allChecks) {
      const exists = deps.fs.existsSync(path.join(cwd, check.path))
      if (exists) {
        success(deps, check.label)
      } else {
        warn(deps, `${check.label} \u2014 not found`)
      }
    }
  }

  if (agentsToCheck.length === 0) {
    deps.print()
    warn(deps, 'No agent directories found. Run init first:')
    log(deps, `  npx ${PKG_NAME} init --agent claude`)
  }

  deps.print()
  log(deps, 'MCP Server')
  deps.print('  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')

  try {
    deps.execSync('curl -sf http://127.0.0.1:3846/health -o /dev/null', { timeout: 3000 })
    success(deps, 'kis-backtest MCP server: running (port 3846)')
  } catch {
    warn(deps, 'kis-backtest MCP server: not running')
    log(deps, '  Start with: bash backtester/scripts/start_mcp.sh')
  }

  deps.print()

  log(deps, 'KIS Authentication')
  deps.print('  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500')

  const kisConfigPath = path.join(deps.homedir(), 'KIS', 'config', 'kis_devlp.yaml')
  if (deps.fs.existsSync(kisConfigPath)) {
    success(deps, `KIS config: ${kisConfigPath}`)
  } else {
    warn(deps, `KIS config not found: ${kisConfigPath}`)
    log(deps, '  Run /auth vps or /auth prod to set up authentication.')
  }

  deps.print()

  if (hasError) {
    error(deps, 'Some required items are missing. Please install them before proceeding.')
  } else {
    success(deps, 'Environment looks good!')
  }
  deps.print()
}

function cmdUpdate(deps = defaultDeps) {
  banner(deps)
  log(deps, `Installed version: ${VERSION}`)
  deps.print()

  try {
    const latest = deps.execSync(`npm view ${PKG_NAME} version 2>/dev/null`, { encoding: 'utf8' }).trim()
    if (latest && latest !== VERSION) {
      log(deps, `Latest version:    ${latest}`)
      deps.print()
      log(deps, 'To update, run:')
      log(deps, `  npx ${PKG_NAME}@latest init --force`)
      log(deps, '  # or')
      log(deps, `  bunx ${PKG_NAME}@latest init --force`)
    } else if (latest) {
      success(deps, 'You are on the latest version.')
    } else {
      warn(deps, 'Could not fetch latest version from npm.')
    }
  } catch {
    warn(deps, 'Could not check npm registry. Package may not be published yet.')
    log(deps, 'Current version: ' + VERSION)
  }
  deps.print()
}

function showHelp(deps = defaultDeps) {
  banner(deps)
  deps.print(`  Usage: ${PKG_NAME} <command> [options]`)
  deps.print()
  deps.print('  Commands:')
  deps.print('    init              Install plugin files into open-trading-api')
  deps.print('    doctor            Diagnose environment (Python, Docker, MCP, etc.)')
  deps.print('    update            Check for newer versions')
  deps.print()
  deps.print('  Options (init):')
  deps.print('    --agent, -a       Target agent: claude, cursor, codex, gemini, all')
  deps.print('    --force, -f       Overwrite existing files')
  deps.print()
  deps.print('  Options (doctor):')
  deps.print('    --agent, -a       Check specific agent: claude, cursor, codex, gemini, all')
  deps.print()
  deps.print('  Options (global):')
  deps.print('    --help, -h        Show this help')
  deps.print('    --version, -v     Show version')
  deps.print()
  deps.print('  Examples:')
  deps.print(`    npx ${PKG_NAME} init`)
  deps.print(`    npx ${PKG_NAME} init --agent claude`)
  deps.print(`    npx ${PKG_NAME} init --agent claude,cursor --force`)
  deps.print(`    npx ${PKG_NAME} doctor`)
  deps.print(`    npx ${PKG_NAME} doctor --agent claude`)
  deps.print(`    npx ${PKG_NAME} update`)
  deps.print()
}

// ── Main ───────────────────────────────────────────────────────────────────────

async function main(argv = process.argv.slice(2), deps = defaultDeps) {
  const args = parseArgs(argv)

  if (args.version) {
    deps.print(`kis-plugin v${VERSION}`)
    return
  }

  const command = args._[0]

  if (args.help || !command) {
    showHelp(deps)
    return
  }

  switch (command) {
    case 'init':
      await cmdInit(args, deps)
      break
    case 'doctor':
      cmdDoctor(args, deps)
      break
    case 'update':
      cmdUpdate(deps)
      break
    default:
      error(deps, `Unknown command: ${command}`)
      deps.print()
      showHelp(deps)
      deps.exit(1); return
  }
}

if (require.main === module) {
  main().catch((err) => {
    defaultDeps.printErr(`  \u2717 ${err.message}`)
    defaultDeps.exit(1)
  })
}

module.exports = {
  parseArgs, main, cmdInit, cmdDoctor, cmdUpdate, showHelp,
  commandExists, getCommandVersion, copyRecursive, renderTemplate,
  assembleAgent, chmodShellScripts,
  AGENT_VARS, AGENT_LABELS, VERSION, PKG_NAME,
}
