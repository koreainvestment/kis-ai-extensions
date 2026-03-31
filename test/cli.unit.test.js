'use strict'

const { describe, it } = require('node:test')
const assert = require('node:assert/strict')
const { parseArgs, renderTemplate } = require('../bin/cli.js')

describe('parseArgs', () => {
  it('returns defaults for empty array', () => {
    const result = parseArgs([])
    assert.deepStrictEqual(result, { _: [], agent: null, help: false, version: false, force: false })
  })

  it('parses init command', () => {
    const result = parseArgs(['init'])
    assert.ok(result._.includes('init'))
  })

  it('parses --agent with space-separated value', () => {
    const result = parseArgs(['--agent', 'claude'])
    assert.strictEqual(result.agent, 'claude')
  })

  it('parses --agent= form with comma values and --force', () => {
    const result = parseArgs(['--agent=claude,cursor', '--force'])
    assert.strictEqual(result.agent, 'claude,cursor')
    assert.strictEqual(result.force, true)
  })

  it('parses --help', () => {
    const result = parseArgs(['--help'])
    assert.strictEqual(result.help, true)
  })

  it('parses -h shorthand', () => {
    const result = parseArgs(['-h'])
    assert.strictEqual(result.help, true)
  })

  it('parses --version', () => {
    const result = parseArgs(['--version'])
    assert.strictEqual(result.version, true)
  })

  it('parses -v shorthand', () => {
    const result = parseArgs(['-v'])
    assert.strictEqual(result.version, true)
  })

  it('handles --agent with no following value', () => {
    const result = parseArgs(['--agent'])
    assert.strictEqual(result.agent, undefined)
  })
})

describe('renderTemplate', () => {
  it('replaces all template variables', () => {
    const content = 'LOG_DIR="${{{PROJECT_DIR_VAR}}:-$(pwd)}/{{LOG_DIR}}"'
    const vars = { PROJECT_DIR_VAR: 'CLAUDE_PROJECT_DIR', LOG_DIR: '.claude/logs' }
    const result = renderTemplate(content, vars)
    assert.strictEqual(result, 'LOG_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/logs"')
  })

  it('replaces multiple occurrences of same variable', () => {
    const content = '{{AGENT_DIR}}/scripts and {{AGENT_DIR}}/hooks'
    const vars = { AGENT_DIR: '.claude' }
    assert.strictEqual(renderTemplate(content, vars), '.claude/scripts and .claude/hooks')
  })

  it('returns unchanged content when no variables match', () => {
    const content = 'no templates here'
    const vars = { AGENT_DIR: '.claude' }
    assert.strictEqual(renderTemplate(content, vars), 'no templates here')
  })

  it('handles empty content', () => {
    assert.strictEqual(renderTemplate('', { AGENT_DIR: '.claude' }), '')
  })
})
