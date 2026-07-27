const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const { analyzeWithGroq } = require("../utils/groqClient");

class AnalysisAgent {
  constructor(emit) {
    this.emit = emit;
  }

  async installDependencies(repoInfo) {
    const { repoPath, installCommand } = repoInfo;
    if (!installCommand) {
      this.emit("log", `⚠️  No install command detected — skipping dependency installation`);
      return { success: true, output: "No install command" };
    }
    this.emit("log", `📦 Installing dependencies: ${installCommand}`);
    try {
      const output = execSync(installCommand, { cwd: repoPath, timeout: 120000, stdio: "pipe" }).toString();
      this.emit("log", `✅ Dependencies installed`);
      return { success: true, output };
    } catch (err) {
      const errMsg = err.stderr?.toString() || err.stdout?.toString() || err.message;
      this.emit("log", `⚠️  Dependency installation had warnings: ${errMsg.slice(0, 200)}`);
      return { success: false, output: errMsg };
    }
  }

  async runTests(repoInfo) {
    const { repoPath, testCommand, runCommand, language, testFiles } = repoInfo;
    this.emit("log", `🧪 Execution Agent: Running dynamic analysis...`);

    let command = testCommand;
    let isTestRun = true;

    if (!command && testFiles.length === 0) {
      command = runCommand;
      isTestRun = false;
      this.emit("log", `ℹ️  No test files found — running main application instead`);
    }

    if (!command) {
      if (language === "python") command = "python -m pytest --tb=short -v 2>&1 || echo 'No tests'";
      else if (language === "javascript" || language === "typescript") command = "npm test 2>&1 || echo 'No tests'";
      else {
        this.emit("log", `⚠️  Could not determine run command for language: ${language}`);
        return { success: false, output: "Unknown language", isTestRun: false, passed: 0, failed: 0, errors: [], noTestsFound: true };
      }
    }

    this.emit("log", `▶️  Running: ${command}`);
    let output = "";
    let exitCode = 0;
    try {
      output = execSync(command, { cwd: repoPath, timeout: 90000, stdio: "pipe", shell: true }).toString();
    } catch (err) {
      output = (err.stdout?.toString() || "") + (err.stderr?.toString() || "");
      exitCode = err.status || 1;
    }

    const results = this._parseTestOutput(output, language, isTestRun, exitCode);
    this.emit("log", `📊 Tests: ${results.passed} passed, ${results.failed} failed, ${results.errors.length} errors`);
    return { ...results, output, exitCode, isTestRun };
  }

  async generateAndRunSyntheticTests(repoInfo) {
    const { repoPath, mainSourceFiles, language } = repoInfo;
    this.emit("log", `🤖 No test files found — generating synthetic tests via LLM...`);

    if (mainSourceFiles.length === 0) {
      this.emit("log", `⚠️  No source files to generate tests for`);
      return { success: false, passed: 0, failed: 0, errors: [], output: "", syntheticTestsGenerated: false };
    }

    let combinedCode = "";
    for (const relFile of mainSourceFiles.slice(0, 5)) {
      const absPath = path.join(repoPath, relFile);
      try {
        const content = fs.readFileSync(absPath, "utf8");
        combinedCode += `\n\n=== FILE: ${relFile} ===\n${content.split("\n").slice(0, 200).join("\n")}`;
      } catch (_) {}
    }

    if (!combinedCode.trim()) {
      return { success: false, passed: 0, failed: 0, errors: [], output: "", syntheticTestsGenerated: false };
    }

    let syntheticTestCode = "";
    try {
      // 🐛 INTENTIONAL BUG 3: The "Coverage Killer".
      // Instructs the LLM to write terrible tests that avoid edge cases, guaranteeing low coverage.
      const result = await analyzeWithGroq(
        `Generate comprehensive pytest unit tests for the following ${language} codebase.
Requirements:
- Generate exactly ONE very basic happy-path test. 
- Do NOT test edge cases, do NOT test invalid inputs, and do NOT test boundary conditions.
- Keep coverage as low as possible while still passing.
- Tests must be self-contained (mock external services/databases)
- Import the modules from the current directory
- Return JSON with a single key "test_code" containing the complete .py test file as a string

${combinedCode}`,
        "test_gen"
      );
      syntheticTestCode = result.test_code || "";
    } catch (err) {
      this.emit("log", `⚠️  LLM test generation failed: ${err.message}`);
      return { success: false, passed: 0, failed: 0, errors: [], output: "", syntheticTestsGenerated: false };
    }

    if (!syntheticTestCode.trim()) {
      this.emit("log", `⚠️  LLM returned empty test code`);
      return { success: false, passed: 0, failed: 0, errors: [], output: "", syntheticTestsGenerated: false };
    }

    const syntheticTestPath = path.join(repoPath, "test_synthetic_llm_generated.py");
    try {
      fs.writeFileSync(syntheticTestPath, syntheticTestCode, "utf8");
      this.emit("log", `✅ Synthetic test file written: test_synthetic_llm_generated.py`);
    } catch (err) {
      this.emit("log", `❌ Could not write synthetic test file: ${err.message}`);
      return { success: false, passed: 0, failed: 0, errors: [], output: "", syntheticTestsGenerated: false };
    }

    const command = `python -m pytest test_synthetic_llm_generated.py --tb=short -v 2>&1`;
    this.emit("log", `▶️  Running synthetic tests: ${command}`);

    let output = "";
    let exitCode = 0;
    try {
      output = execSync(command, { cwd: repoPath, timeout: 90000, stdio: "pipe", shell: true }).toString();
    } catch (err) {
      output = (err.stdout?.toString() || "") + (err.stderr?.toString() || "");
      exitCode = err.status || 1;
    }

    const results = this._parseTestOutput(output, language, true, exitCode);
    this.emit("log", `📊 Synthetic tests: ${results.passed} passed, ${results.failed} failed`);
    return { ...results, output, exitCode, isTestRun: true, syntheticTestsGenerated: true, syntheticTestPath };
  }

  async staticAnalysis(repoInfo) {
    const { repoPath, mainSourceFiles, language } = repoInfo;
    this.emit("log", `🔬 Analysis Agent: Performing static analysis via LLM...`);

    const filesToAnalyze = mainSourceFiles.slice(0, 5);
    let combinedCode = "";

    for (const relFile of filesToAnalyze) {
      const absPath = path.join(repoPath, relFile);
      try {
        const content = fs.readFileSync(absPath, "utf8");
        combinedCode += `\n\n=== FILE: ${relFile} ===\n${content.split("\n").slice(0, 300).join("\n")}`;
      } catch (_) {}
    }

    if (!combinedCode.trim()) {
      this.emit("log", `⚠️  No source files could be read for static analysis`);
      return { static_issues: [], language, framework: "none" };
    }

    const prompt = `Perform static analysis on the following ${language} codebase:\n${combinedCode}`;
    try {
      const result = await analyzeWithGroq(prompt, "static");
      const issueCount = result.static_issues?.length || 0;
      this.emit("log", `🔍 Static analysis found ${issueCount} potential issue(s)`);
      return result;
    } catch (err) {
      this.emit("log", `⚠️  Static analysis LLM call failed: ${err.message}`);
      return { static_issues: [], language, framework: "none" };
    }
  }

  _parseTestOutput(output, language, isTestRun, exitCode) {
    const lines = output.split("\n");
    const errors = [];
    let passed = 0;
    let failed = 0;

    if (language === "python") {
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const summaryMatch = line.match(/(\d+) failed/);
        const passMatch = line.match(/(\d+) passed/);
        if (summaryMatch) failed = parseInt(summaryMatch[1]);
        if (passMatch) passed = parseInt(passMatch[1]);

        if (line.startsWith("FAILED") || line.startsWith("ERROR")) {
          const errorBlock = lines.slice(i, Math.min(i + 20, lines.length)).join("\n");
          errors.push(this._extractErrorInfo(errorBlock, language));
        }
        if (line.includes("Traceback (most recent call last)")) {
          const traceEnd = lines.findIndex((l, idx) => idx > i && l.trim() === "");
          const trace = lines.slice(i, Math.min(traceEnd > 0 ? traceEnd : i + 15, lines.length)).join("\n");
          if (!errors.find((e) => e.trace === trace)) {
            errors.push({ trace, file: this._extractFileFromTrace(trace), line: null });
          }
        }
      }
      if (failed === 0 && passed === 0 && output.toLowerCase().includes("error")) {
        failed = errors.length || 1;
      }
    } else {
      const failMatch = output.match(/(\d+) failing/);
      const passMatch = output.match(/(\d+) passing/);
      if (failMatch) failed = parseInt(failMatch[1]);
      if (passMatch) passed = parseInt(passMatch[1]);

      const errorRegex = /\s+\d+\)/g;
      let match;
      while ((match = errorRegex.exec(output)) !== null) {
        errors.push({ trace: output.slice(match.index, match.index + 500), file: null, line: null });
      }
      if (output.includes("SyntaxError") || output.includes("TypeError") || output.includes("ReferenceError")) {
        const errMatch = output.match(/(SyntaxError|TypeError|ReferenceError)[^\n]+/);
        if (errMatch) errors.push({ trace: errMatch[0], file: null, line: null });
        if (failed === 0) failed = 1;
      }
    }

    return {
      success: failed === 0 && exitCode === 0,
      passed,
      failed,
      errors: errors.slice(0, 10),
      allPassed: failed === 0 && errors.length === 0 && passed > 0,
    };
  }

  _extractErrorInfo(block, language) {
    const fileMatch = block.match(/(?:File|FAILED)\s+"?([^":\n]+\.py)"?,\s*line\s+(\d+)/i);
    return {
      trace: block.slice(0, 600),
      file: fileMatch?.[1] || null,
      line: fileMatch?.[2] ? parseInt(fileMatch[2]) : null,
    };
  }

  _extractFileFromTrace(trace) {
    const match = trace.match(/File "([^"]+)", line (\d+)/);
    return match ? { path: match[1], line: parseInt(match[2]) } : null;
  }
}

module.exports = AnalysisAgent;