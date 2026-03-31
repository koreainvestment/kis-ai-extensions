#!/bin/bash
PROJECT_ROOT="${1:-$(pwd)}"

mkdir -p "$PROJECT_ROOT/.claude"

cat > "$PROJECT_ROOT/.claude/settings.json" << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(bash $CLAUDE_PROJECT_DIR/.claude/scripts/*)",
      "Bash(uv run $CLAUDE_PROJECT_DIR/.claude/scripts/*)",
      "Bash(uv run $CLAUDE_PROJECT_DIR/strategy_builder/*)",
      "Bash(uv run $CLAUDE_PROJECT_DIR/backtester/*)",
      "Bash(bash $CLAUDE_PROJECT_DIR/strategy_builder/scripts/*)",
      "Bash(bash $CLAUDE_PROJECT_DIR/backtester/scripts/*)",
      "Bash(uv sync)*",
      "Bash(pnpm install)*",
      "Read($CLAUDE_PROJECT_DIR/strategy_builder/*)",
      "Read($CLAUDE_PROJECT_DIR/backtester/*)",
      "Bash(find $CLAUDE_PROJECT_DIR/*)",
      "Bash(ls $CLAUDE_PROJECT_DIR/*)",
      "Bash(curl *127.0.0.1:3846*)",
      "Bash(docker ps*)",
      "Bash(docker info*)",
      "mcp__kis-backtest__list_presets_tool",
      "mcp__kis-backtest__get_preset_yaml_tool",
      "mcp__kis-backtest__validate_yaml_tool",
      "mcp__kis-backtest__list_indicators_tool",
      "mcp__kis-backtest__run_backtest_tool",
      "mcp__kis-backtest__run_preset_backtest_tool",
      "mcp__kis-backtest__get_backtest_result_tool",
      "mcp__kis-backtest__retry_backtest_tool",
      "mcp__kis-backtest__get_report_tool",
      "mcp__kis-backtest__run_batch_backtest_tool",
      "mcp__kis-backtest__optimize_strategy_tool"
    ],
    "deny": [
      "Bash(cat *KIS/config*)*",
      "Bash(less *KIS/config*)*",
      "Bash(more *KIS/config*)*",
      "Bash(head *KIS/config*)*",
      "Bash(tail *KIS/config*)*",
      "Bash(cp *KIS/config*)*",
      "Bash(mv *KIS/config*)*",
      "Bash(git push*)*"
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "uv run \"$CLAUDE_PROJECT_DIR/.claude/status_lines/kis_status_line.py\"",
    "padding": 0
  }
}
EOF

echo "✅ .claude/settings.json 생성 완료"
