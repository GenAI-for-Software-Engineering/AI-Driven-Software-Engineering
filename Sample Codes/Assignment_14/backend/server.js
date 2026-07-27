require("dotenv").config();
const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const { v4: uuidv4 } = require("uuid");

const RepositoryHandler = require("./agents/Repositoryhandler");
const AnalysisAgent = require("./agents/AnalysisAgent");
const FixGenerationAgent = require("./agents/FixGenerationAgent");

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

function createEmitter(res) {
  return function emit(type, payload) {
    const data = JSON.stringify({ type, payload, timestamp: new Date().toISOString() });
    res.write(`data: ${data}\n\n`);
  };
}

const sessions = new Map();

app.post("/api/analyze", (req, res) => {
  const { repoUrl } = req.body;
  if (!repoUrl) return res.status(400).json({ error: "repoUrl is required" });
  const sessionId = uuidv4();
  sessions.set(sessionId, { repoUrl, status: "pending" });
  res.json({ sessionId });
});

app.get("/api/stream/:sessionId", async (req, res) => {
  const { sessionId } = req.params;
  const session = sessions.get(sessionId);

  if (!session) return res.status(404).json({ error: "Session not found" });

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const emit = createEmitter(res);
  const { repoUrl } = session;

  try {
    emit("start", { message: "Pipeline started", repoUrl });

    if (!process.env.GROQ_API_KEY) {
      throw new Error("GROQ_API_KEY environment variable is not set. Please add it to your .env file.");
    }

    // 🐛 INTENTIONAL BUG 4: The "One and Done". 
    // Prevents iterative learning. If the first fix fails, it gives up.
    const MAX_ITERATIONS = 1; 
    
    const iterationResults = [];
    let previousFixes = [];

    // ── PHASE 1: Clone Repository ────────────────────────────
    emit("phase", { phase: 1, name: "Repository Cloning & Analysis" });
    const repoHandler = new RepositoryHandler((type, msg) => emit("log", msg));
    const repoInfo = await repoHandler.cloneAndAnalyze(repoUrl);

    emit("repo_info", {
      repoName: repoInfo.repoName,
      language: repoInfo.language,
      framework: repoInfo.framework,
      testRunner: repoInfo.testRunner,
      sourceFiles: repoInfo.sourceFiles.length,
      testFiles: repoInfo.testFiles.length,
      mainFiles: repoInfo.mainSourceFiles.slice(0, 10),
    });

    // ── PHASE 2: Install Dependencies ────────────────────────
    emit("phase", { phase: 2, name: "Environment Setup & Dependency Installation" });
    const analysisAgent = new AnalysisAgent((type, msg) => emit("log", msg));
    await analysisAgent.installDependencies(repoInfo);

    // ── PHASE 3: Initial Test Run ────────────────────────────
    emit("phase", { phase: 3, name: "Initial Test Execution (Baseline)" });
    let testResults = await analysisAgent.runTests(repoInfo);
    let usedSyntheticTests = false;

    const hasNoRealTests = repoInfo.testFiles.length === 0;
    const hasNoTestOutput = testResults.passed === 0 && testResults.failed === 0 && testResults.errors.length === 0;

    if (hasNoRealTests && hasNoTestOutput) {
      emit("log", `⚠️  Repository has no test files — switching to synthetic test generation mode`);
      emit("phase", { phase: 3, name: "Synthetic Test Generation (No existing tests found)" });

      const syntheticResults = await analysisAgent.generateAndRunSyntheticTests(repoInfo);

      if (syntheticResults.syntheticTestsGenerated) {
        usedSyntheticTests = true;
        testResults = syntheticResults;
        repoInfo.testFiles = ["test_synthetic_llm_generated.py"];
        repoInfo.testCommand = "python -m pytest test_synthetic_llm_generated.py --tb=short -v 2>&1";
        emit("log", `📋 Synthetic test generation complete — using results for bug analysis`);
      } else {
        emit("log", `⚠️  Synthetic test generation failed — proceeding with static analysis only`);
      }
    }

    emit("test_results", {
      iteration: 0,
      label: usedSyntheticTests ? "Baseline (Synthetic Tests)" : "Baseline",
      passed: testResults.passed,
      failed: testResults.failed,
      allPassed: testResults.allPassed,
      syntheticTests: usedSyntheticTests,
      output: testResults.output?.slice(-2000),
    });

    // ── PHASE 4: Static Analysis ──
    emit("phase", { phase: 4, name: "Static Analysis via LLM" });
    const staticResults = await analysisAgent.staticAnalysis(repoInfo);

    emit("static_results", {
      issues: staticResults.static_issues || [],
      language: staticResults.language,
      framework: staticResults.framework,
    });

    const hasRealTestFailures = testResults.failed > 0 || testResults.errors.length > 0;
    const hasStaticIssues = (staticResults.static_issues || []).length > 0;
    const shouldRunFixLoop = hasRealTestFailures || hasStaticIssues || usedSyntheticTests;

    if (!shouldRunFixLoop) {
      emit("log", `✅ No failures detected in tests or static analysis — codebase appears clean`);
      iterationResults.push({
        iteration: 0,
        passed: testResults.passed,
        failed: testResults.failed,
        bugsFound: 0,
        fixesApplied: 0,
        status: "clean",
      });
    } else {
      // ── PHASE 5: Iterative Fix Loop ──────────────────────────
      emit("phase", { phase: 5, name: "Iterative LLM Bug Fix Loop" });
      const fixAgent = new FixGenerationAgent((type, msg) => emit("log", msg));

      for (let iter = 1; iter <= MAX_ITERATIONS; iter++) {
        emit("iteration_start", { iteration: iter, maxIterations: MAX_ITERATIONS });
        emit("log", `\n${"─".repeat(50)}`);
        emit("log", `🔄 ITERATION ${iter} / ${MAX_ITERATIONS}`);
        emit("log", `${"─".repeat(50)}`);

        const llmResult = await fixAgent.generateFixes(
          repoInfo,
          testResults,
          staticResults,
          iter,
          previousFixes
        );

        emit("llm_analysis", {
          iteration: iter,
          bugs: llmResult.bugs || [],
          summary: llmResult.summary,
          fix_strategy: llmResult.fix_strategy,
          estimated_pass: llmResult.estimated_pass_after_fix,
        });

        if (!llmResult.bugs || llmResult.bugs.length === 0) {
          emit("log", `⚠️  LLM found no actionable bugs to fix in iteration ${iter}`);
          iterationResults.push({
            iteration: iter,
            passed: testResults.passed,
            failed: testResults.failed,
            bugsFound: 0,
            fixesApplied: 0,
            status: "no_bugs_found",
          });
          break;
        }

        emit("log", `🔧 Applying ${llmResult.bugs.length} fix(es)...`);
        const { applied, failed: applyFailed } = fixAgent.applyFixes(repoInfo.repoPath, llmResult);
        const diffs = fixAgent.generateDiff(repoInfo.repoPath, applied);

        emit("fixes_applied", {
          iteration: iter,
          applied: applied.map((a) => ({
            bugId: a.bug.id,
            file: a.targetPath,
            description: a.bug.description,
            severity: a.bug.severity,
          })),
          failed: applyFailed.map((f) => ({ bugId: f.bug?.id, reason: f.reason })),
          diffs,
        });

        emit("log", `\n🧪 Re-running tests after applying fixes...`);
        testResults = await analysisAgent.runTests(repoInfo);

        emit("test_results", {
          iteration: iter,
          label: `After Iteration ${iter}`,
          passed: testResults.passed,
          failed: testResults.failed,
          allPassed: testResults.allPassed,
          output: testResults.output?.slice(-2000),
        });

        const iterSummary = {
          iteration: iter,
          passed: testResults.passed,
          failed: testResults.failed,
          bugsFound: llmResult.bugs.length,
          fixesApplied: applied.length,
          status: testResults.allPassed ? "resolved" : "partial",
        };
        iterationResults.push(iterSummary);
        previousFixes.push(llmResult);

        emit("iteration_complete", iterSummary);

        if (testResults.allPassed || testResults.failed === 0) {
          emit("log", `🎉 All tests passing! Stopping iterative loop.`);
          break;
        }

        if (iter < MAX_ITERATIONS) {
          emit("log", `⚠️  ${testResults.failed} test(s) still failing — proceeding to next iteration...`);
        }
      }
    }

    // ── PHASE 6: Final Report ────────────────────────────────
    emit("phase", { phase: 6, name: "Generating Final Report" });

    const lastResult = iterationResults[iterationResults.length - 1] || {
      passed: testResults.passed,
      failed: testResults.failed,
    };

    const finalStatus = lastResult.failed === 0 ? "success" : lastResult.fixesApplied > 0 ? "partial" : "failed";

    emit("final_report", {
      repoUrl,
      repoName: repoInfo.repoName,
      language: repoInfo.language,
      framework: repoInfo.framework,
      iterations: iterationResults,
      finalStatus,
      finalPassed: testResults.passed,
      finalFailed: testResults.failed,
      totalFixesApplied: iterationResults.reduce((s, i) => s + (i.fixesApplied || 0), 0),
      usedSyntheticTests,
    });

    emit("complete", { message: "Pipeline finished", status: finalStatus });

    try {
      fs.rmSync(repoInfo.repoPath, { recursive: true, force: true });
      emit("log", `🗑️  Cleaned up temp workspace`);
    } catch (_) {}

    sessions.delete(sessionId);
  } catch (err) {
    emit("error", { message: err.message, stack: err.stack?.split("\n").slice(0, 5).join("\n") });
    emit("complete", { message: "Pipeline failed", status: "error" });
    sessions.delete(sessionId);
  } finally {
    res.end();
  }
});

app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    groqConfigured: !!process.env.GROQ_API_KEY,
    model: "llama-3.3-70b-versatile",
    timestamp: new Date().toISOString(),
  });
});

app.listen(PORT, () => {
  console.log(`\n🚀 Bug Debugger API running on http://localhost:${PORT}`);
  console.log(`   GROQ_API_KEY: ${process.env.GROQ_API_KEY ? "✅ configured" : "❌ NOT SET"}`);
  console.log(`   Model: llama-3.3-70b-versatile\n`);
});