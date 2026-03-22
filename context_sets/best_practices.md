# Terminal Output Best Practices

## Code Search Priority

**USE THESE MCP TOOLS FIRST:**
```python
mcp_precinct_code_search_code("How are percentages calculated?")
mcp_precinct_code_explain_file("flippable_graph_database/test/test_contest_assessor.py")
mcp_precinct_code_list_components("model")  # List all models/routes/tables
mcp_precinct_code_get_schema("flippable")   # Get table schema
```

**PRIORITY ORDER:**
1. 🏆 **precinct_codebase MCP tools** - Check institutional knowledge FIRST
2. 🤖 **codebase LLM query** - Ask specific questions
3. 🔎 **grep_search** - Fast pattern matching
4. 📍 **list_code_usages** - Find all references
5. 🧠 **semantic_search** - Fallback for conceptual matching (uses more tokens)

## Critical Terminal Rules

### 1. ❌ NEVER Pipe to head/tail
**WRONG:** `ls -la | head -20` or `psql -c "SELECT *" | head -10`  
**RIGHT:** `ls -la` or `psql -c "SELECT *"`  
**Why:** Terminal auto-truncates; piping loses full output capability

### 2. 🐘 PostgreSQL: Always Use PAGER=cat
**WRONG:** `psql -c "SELECT *"`  
**RIGHT:** `PAGER=cat psql -c "SELECT *"`  
**Why:** Disables pager, prevents hanging

### 3. 🤖 Full Test Suite: Let n8n Run It
**WHO:** n8n unattended debug workflow ONLY  
**NOT YOU:** Never run `pytest test/` or full suite manually  
**YOU:** Run specific tests from BUG files: `pytest test/file.py::test_case -xvs`  
**WHY:** Full suite takes 5-10min, n8n creates structured BUG reports, you fix specific issues

## Bug Resolution Workflow

**COMPLETE BEFORE MOVING ON:**
1. ✅ Update BUG file - Mark as RESOLVED with status/notes
2. ✅ Git add - Stage all changes: `git add test/file.py TODO/BUG_*.md`
3. ✅ Git commit - Reference bug: `git commit -m "Fix Bug 4ace4cae: Description"`
4. ✅ Git push - Triggers post-commit hook (auto-marks resolved, teaches Ollama)
5. ✅ Move to next bug

**BUG File Format:**
```markdown
## Bug 4ace4cae - ✅ RESOLVED
**Status:** Fixed on 2025-12-22
**Root Cause:** Tests creating users instead of using fixtures
**Fix:** Refactored to use admin_user, county_user, regular_user fixtures
**Commit:** a1b2c3d4
```

## Git Workflow

### Test Before Commit - MANDATORY

1. ✅ Make changes
2. ✅ Test with ACTUAL DATA from database (not just syntax)
3. ✅ Validate JSON/config: `python3 -m json.tool file.json`
4. ✅ Commit after tests pass
5. ✅ Push working code

### Capture Successful Debugging

**After resolving complex bugs:**
1. ✅ Create training example in `local_llm/training_examples/`
2. ✅ Run reindex: `cd local_llm && ./reindex.sh`

**Training Format:**
```json
{
  "question": "What pattern causes gap_ava_pct mismatches?",
  "context": "76 records with calculation errors",
  "answer": "Function returns decimal (0-1) but DB expects percentage (0-100). Multiply by 100.",
  "tags": ["tier3", "calculation", "gap_ava_pct"],
  "files": ["test/test_contest_assessor.py", "data_quality/quality_functions.py"]
}
```

**Workflow:**
1. Systematic debugging (list_code_usages, read_file, etc.)
2. Document and add to training_data.jsonl

**Adding Patterns:**
Say *"Add to debug patterns"* after fixing a bug, or:
```bash
python3 mcp_servers/custom_llm_debugging/add_pattern.py --interactive
```

## Service Management

### Flask Development Server (wsgi.py)

**STARTING wsgi.py NON-INTERACTIVELY:**

wsgi.py prompts for user input if port 5000 is in use, which causes EOFError when run in background/automated:

```bash
# WRONG - Will fail with EOFError if port in use:
python wsgi.py --log_level WARNING &

# RIGHT - Kill existing processes first, then start:
pkill -f "python wsgi.py" 2>/dev/null
sleep 2
cd /home/bren/Home/Projects/HTML_CSS/precinct && source .venv/bin/activate && python wsgi.py --log_level WARNING &
```

**Key Points:**
- Environment variables are loaded by `.bashrc` (see [ENV_SETUP.md](../ENV_SETUP.md))
- Always kill existing wsgi.py processes before starting new one
- Check if port is in use: `lsof -i :5000` or look for PIDs in startup error
- The warning about `dump_bash_state: command not found` is harmless shell noise
- **NEVER** use `instance/.runtime_cache` file (deprecated security risk)

**Checking if server is running:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/login
# Returns 200/302 if running, 000 if not
```

### n8n-bridge Service

**CRITICAL: After updating n8n_bridge.py:**
```bash
systemctl --user restart n8n-bridge.service
systemctl --user status n8n-bridge.service  # Check status
tail -f logs/n8n_bridge.log  # View logs
```

## Test Fixtures

**THREE FIXTURES:**

1. **`app_readonly`** - PostgreSQL read-only, NO SQLite
   - Use for: Tests that ONLY READ from PostgreSQL
   - Fastest, no cleanup needed

2. **`app_with_sqlite`** - SQLite for writes + PostgreSQL read
   - Use for: Tests that CREATE User or need isolated writes
   - SQLite in `/tmp/*.db`, auto-created/deleted

3. **`app`** - DEPRECATED, use `app_with_sqlite`

**Selection:**
```python
# Only reads PostgreSQL
def test_map_query(app_readonly):
    maps = Map.query.filter_by(county='FORSYTH').all()

# Creates User or writes
def test_user_login(app_with_sqlite):
    user = User(username='test', ...)
    db.session.add(user)
```

**instance/ Protection:**
- Directory is `chmod -w` (read-only)
- Prevents accidental SQLite creation in project
- Tests use `/tmp` instead