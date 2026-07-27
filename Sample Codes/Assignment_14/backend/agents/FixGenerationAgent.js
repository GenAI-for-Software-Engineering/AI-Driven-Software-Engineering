const fs = require("fs");
const path = require("path");
const { analyzeWithGroq } = require("../utils/groqClient");

class FixGenerationAgent {
  constructor(emit) {
    this.emit = emit;
  }

  async generateFixes(repoInfo, testResults, staticResults, iteration = 1, previousFixes = []) {
    this.emit("log", `🤖 Fix Generation Agent: Preparing LLM prompt (iteration ${iteration})...`);

    const { repoPath, mainSourceFiles, language } = repoInfo;

    const localizedBugs = this._localizeBugs(testResults.errors, staticResults.static_issues || [], repoPath);
    this.emit("log", `📍 Bug Localization: mapped ${localizedBugs.length} bug location(s)`);

    const relevantFiles = this._selectRelevantFiles(mainSourceFiles, localizedBugs, repoPath);
    const fileContents = this._readFiles(relevantFiles, repoPath);

    const mode = iteration === 1 ? "bug_fix" : "iteration";
    const prompt = this._buildPrompt({
      language,
      iteration,
      testOutput: testResults.output?.slice(-3000) || "",
      errors: testResults.errors,
      staticIssues: staticResults.static_issues || [],
      fileContents,
      previousFixes,
      passed: testResults.passed,
      failed: testResults.failed,
      syntheticTests: testResults.syntheticTestsGenerated || false,
    });

    this.emit("log", `📤 Sending to Groq LLM (llama-3.3-70b-versatile)...`);

    let llmResult;
    try {
      llmResult = await analyzeWithGroq(prompt, mode);
    } catch (err) {
      this.emit("log", `❌ LLM call failed: ${err.message}`);
      return { bugs: [], summary: err.message, fix_strategy: "LLM unavailable" };
    }

    const bugCount = llmResult.bugs?.length || 0;
    this.emit("log", `🔎 LLM identified ${bugCount} bug(s) with fixes`);
    this.emit("log", `📊 LLM confidence summary: ${llmResult.summary}`);

    return llmResult;
  }

  applyFixes(repoPath, llmResult) {
    const applied = [];
    const failed = [];

    if (!llmResult.bugs || llmResult.bugs.length === 0) {
      return { applied, failed };
    }

    for (const bug of llmResult.bugs) {
      if (!bug.file || !bug.original_code || !bug.fixed_code) {
        failed.push({ bug, reason: "Missing file, original_code, or fixed_code" });
        continue;
      }

      const possiblePaths = [
        path.join(repoPath, bug.file),
        ...this._findFile(repoPath, path.basename(bug.file)),
      ];

      let targetPath = null;
      for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
          targetPath = p;
          break;
        }
      }

      if (!targetPath) {
        failed.push({ bug, reason: `File not found: ${bug.file}` });
        continue;
      }

      try {
        let content = fs.readFileSync(targetPath, "utf8");
        const originalNorm = bug.original_code.trim().replace(/\r\n/g, "\n");

        if (content.includes(originalNorm)) {
          fs.writeFileSync(targetPath + ".bak", content);
          content = content.replace(originalNorm, bug.fixed_code.trim());
          fs.writeFileSync(targetPath, content, "utf8");
          applied.push({
            bug,
            targetPath: path.relative(repoPath, targetPath),
            backup: path.relative(repoPath, targetPath) + ".bak",
          });
          this.emit("log", `✅ Applied fix: ${bug.id} → ${path.relative(repoPath, targetPath)}`);
        } else {
          const lineApplied = this._applyLineBasedFix(targetPath, content, bug);
          if (lineApplied) {
            applied.push({ bug, targetPath: path.relative(repoPath, targetPath) });
            this.emit("log", `✅ Applied line-based fix: ${bug.id} → ${path.relative(repoPath, targetPath)}`);
          } else {
            failed.push({ bug, reason: "Could not find original_code in file (exact or line-based)" });
            this.emit("log", `⚠️  Could not apply fix for ${bug.id} — original code not found`);
          }
        }
      } catch (err) {
        failed.push({ bug, reason: err.message });
        this.emit("log", `❌ Error applying fix for ${bug.id}: ${err.message}`);
      }
    }

    return { applied, failed };
  }

  generateDiff(repoPath, applied) {
    const diffs = [];
    for (const fix of applied) {
      const backupPath = path.join(repoPath, fix.backup || fix.targetPath + ".bak");
      const fixedPath = path.join(repoPath, fix.targetPath);
      try {
        const before = fs.existsSync(backupPath) ? fs.readFileSync(backupPath, "utf8") : "";
        const after = fs.readFileSync(fixedPath, "utf8");
        diffs.push({
          file: fix.targetPath,
          bugId: fix.bug.id,
          before: before.slice(0, 2000),
          after: after.slice(0, 2000),
          description: fix.bug.description,
          explanation: fix.bug.explanation,
        });
      } catch (_) {}
    }
    return diffs;
  }

  _localizeBugs(errors, staticIssues, repoPath) {
    const bugs = [];
    for (const err of errors) {
      if (err.file) bugs.push({ file: err.file, line: err.line, source: "dynamic", trace: err.trace });
    }
    for (const issue of staticIssues) {
      if (issue.file) bugs.push({ file: issue.file, line: issue.line, source: "static", issue: issue.issue });
    }
    return bugs;
  }

  _selectRelevantFiles(sourceFiles, localizedBugs, repoPath) {
    const bugFiles = new Set(localizedBugs.map((b) => b.file).filter(Boolean));
    const relevant = sourceFiles.filter((f) => {
      const base = path.basename(f);
      return bugFiles.has(f) || bugFiles.has(base) || [...bugFiles].some((bf) => f.endsWith(bf));
    });
    const others = sourceFiles.filter((f) => !relevant.includes(f)).slice(0, 3);
    return [...new Set([...relevant, ...others])];
  }

  _readFiles(relPaths, repoPath) {
    const result = {};
    for (const relPath of relPaths) {
      const absPath = path.join(repoPath, relPath);
      try {
        const content = fs.readFileSync(absPath, "utf8");
        // 🐛 INTENTIONAL BUG 2: The "Large File Truncator".
        // Slices the file read at 40 lines instead of 400. LLM won't see bugs at the bottom of files.
        result[relPath] = content.split("\n").slice(0, 40).join("\n"); 
      } catch (_) {}
    }
    return result;
  }

  _buildPrompt({ language, iteration, testOutput, errors, staticIssues, fileContents, previousFixes, passed, failed, syntheticTests }) {
    let prompt = `AUTOMATED BUG ANALYSIS — Iteration ${iteration}\nLanguage: ${language}\n`;

    if (passed === 0 && failed === 0 && errors.length === 0) {
      prompt += `Test Results: No tests were executed — relying on static analysis for bug detection\n\n`;
    } else {
      prompt += `Test Results: ${passed} passed, ${failed} failed`;
      if (syntheticTests) prompt += ` (LLM-generated synthetic tests)`;
      prompt += `\n\n`;
    }

    if (iteration > 1 && previousFixes.length > 0) {
      prompt += `=== PREVIOUS FIX ATTEMPTS (These did NOT fully resolve the issue) ===\n`;
      previousFixes.forEach((fix, i) => {
        prompt += `Attempt ${i + 1}: ${fix.summary}\n`;
        fix.bugs?.forEach((b) => { prompt += `  - Fixed ${b.file} line ${b.line}: ${b.description}\n`; });
      });
      prompt += `\n`;
    }

    if (testOutput && testOutput.trim()) {
      prompt += `=== TEST / EXECUTION OUTPUT ===\n${testOutput}\n\n`;
    } else {
      prompt += `=== TEST / EXECUTION OUTPUT ===\n(No test output — no tests were found or run in this repository)\n\n`;
    }

    if (errors.length > 0) {
      prompt += `=== DYNAMIC ERRORS CAPTURED ===\n`;
      errors.forEach((e, i) => { prompt += `Error ${i + 1}:\n${e.trace}\n\n`; });
    }

    if (staticIssues.length > 0) {
      prompt += `=== STATIC ANALYSIS ISSUES ===\n`;
      staticIssues.forEach((s) => { prompt += `[${s.severity}] ${s.file}:${s.line || "?"} — ${s.issue}\n`; });
      prompt += `\n`;
    }

    prompt += `=== SOURCE FILES ===\n`;
    for (const [filePath, content] of Object.entries(fileContents)) {
      prompt += `\n--- FILE: ${filePath} ---\n${content}\n`;
    }

    if (passed === 0 && failed === 0) {
      prompt += `\nIMPORTANT: This repository has no test files. Identify bugs using static analysis issues above and code inspection. Look for: incorrect logic, missing error handling, type errors, undefined variables, incorrect API usage, and other defects visible from the source code alone.`;
    } else {
      prompt += `\nAnalyze all the above and generate fixes. Focus on bugs that directly cause test failures or runtime errors.`;
    }

    return prompt;
  }

  _findFile(baseDir, filename) {
    const results = [];
    const walk = (dir) => {
      try {
        for (const entry of fs.readdirSync(dir)) {
          const full = path.join(dir, entry);
          const stat = fs.statSync(full);
          if (stat.isDirectory() && !["node_modules", ".git", "__pycache__"].includes(entry)) {
            walk(full);
          } else if (entry === filename) {
            results.push(full);
          }
        }
      } catch (_) {}
    };
    walk(baseDir);
    return results;
  }

  _applyLineBasedFix(targetPath, content, bug) {
    if (!bug.line) return false;
    const lines = content.split("\n");
    const lineIdx = bug.line - 1;
    if (lineIdx < 0 || lineIdx >= lines.length) return false;

    const fixedLines = bug.fixed_code.split("\n");
    lines.splice(lineIdx, 1, ...fixedLines);
    fs.writeFileSync(targetPath, lines.join("\n"), "utf8");
    return true;
  }
}

module.exports = FixGenerationAgent;