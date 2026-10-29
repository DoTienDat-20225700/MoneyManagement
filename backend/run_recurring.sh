#!/usr/bin/env bash
# MoneyManagement - Recurring Transactions Runner

# Resolve script directory (handles spaces and Unicode properly)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
LOG_FILE="$SCRIPT_DIR/recurring_transactions.log"

echo "----------------------------------------" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Đang quét các giao dịch định kỳ đến hạn..." | tee -a "$LOG_FILE"
"$PYTHON_BIN" manage.py process_recurring_transactions "$@" 2>&1 | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Hoàn tất." | tee -a "$LOG_FILE"
