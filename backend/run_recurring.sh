#!/usr/bin/env bash
# MoneyManagement - Recurring Transactions Runner

# Resolve script directory (handles spaces and Unicode properly)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
LOG_FILE="$SCRIPT_DIR/recurring_transactions.log"

echo "----------------------------------------" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Đang quét các giao dịch định kỳ đến hạn..." | tee -a "$LOG_FILE"
"$PYTHON_BIN" manage.py process_recurring_transactions "$@" 2>&1 | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Hoàn tất." | tee -a "$LOG_FILE"
