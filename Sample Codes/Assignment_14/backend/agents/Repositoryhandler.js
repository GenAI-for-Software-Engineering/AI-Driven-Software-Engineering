const { execSync, exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

class RepositoryHandler {
  constructor(emit) {
    this.emit = emit;
  }

  async cloneAndAnalyze(repoUrl) {
    this.emit("log", `📦 Repository Handler Agent starting...`);
    this.emit("log", `🔗 Target URL: ${repoUrl}`);

    if (!repoUrl.includes("github.com")) {
      throw new Error("Only GitHub URLs are supported (e.g., https://github.com/user/repo)");
    }

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bug-debugger-"));
    this.emit("log", `📁 Created temp workspace: ${tmpDir}`);

    this.emit("log", `⬇️  Cloning repository...`);
    try {
      execSync(`git clone --depth=1 "${repoUrl}" "${tmpDir}"`, {
        timeout: 60000,
        stdio: "pipe",
      });
    } catch (err) {
      throw new Error(`Git clone failed: ${err.stderr?.toString() || err.message}`);
    }

    this.emit("log", `✅ Repository cloned successfully`);

    const structure = this._analyzeStructure(tmpDir);
    this.emit("log", `🔍 Detected language: ${structure.language}`);
    this.emit("log", `🔍 Framework: ${structure.framework}`);
    this.emit("log", `📄 Source files found: ${structure.sourceFiles.length}`);

    return {
      repoPath: tmpDir,
      repoUrl,
      repoName: repoUrl.split("/").pop().replace(".git", ""),
      ...structure,
    };
  }

  _analyzeStructure(repoPath) {
    const files = this._walkDir(repoPath, [".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"]);

    const extCounts = {};
    files.forEach((f) => {
      const ext = path.extname(f).toLowerCase();
      if (ext) extCounts[ext] = (extCounts[ext] || 0) + 1;
    });

    let language = "unknown";
    let framework = "none";
    let testRunner = "none";
    let installCommand = null;
    let testCommand = null;
    let runCommand = null;

    if ((extCounts[".py"] || 0) > (extCounts[".js"] || 0)) {
      language = "python";
      const allContent = this._safeReadFiles(repoPath, ["requirements.txt", "setup.py", "pyproject.toml", "setup.cfg"]);
      if (allContent.includes("flask")) framework = "flask";
      else if (allContent.includes("django")) framework = "django";
      else if (allContent.includes("fastapi")) framework = "fastapi";

      if (fs.existsSync(path.join(repoPath, "requirements.txt"))) installCommand = "pip install -r requirements.txt";
      else if (fs.existsSync(path.join(repoPath, "setup.py"))) installCommand = "pip install -e .";

      testRunner = "pytest";
      testCommand = "python -m pytest --tb=short -v 2>&1 || python -m pytest --tb=short 2>&1";

      const mainFiles = ["main.py", "app.py", "run.py", "manage.py"];
      for (const mf of mainFiles) {
        if (fs.existsSync(path.join(repoPath, mf))) {
          runCommand = `python ${mf}`;
          break;
        }
      }
    } else if ((extCounts[".js"] || 0) > 0 || (extCounts[".ts"] || 0) > 0) {
      language = extCounts[".ts"] > extCounts[".js"] ? "typescript" : "javascript";

      const pkgJson = this._safeReadFile(path.join(repoPath, "package.json"));
      if (pkgJson) {
        try {
          const pkg = JSON.parse(pkgJson);
          const deps = { ...pkg.dependencies, ...pkg.devDependencies };
          if (deps.react) framework = "react";
          else if (deps.express) framework = "express";
          else if (deps.next) framework = "nextjs";
          else if (deps.vue) framework = "vue";

          if (pkg.scripts?.test) {
            testCommand = "npm test -- --watchAll=false 2>&1";
            testRunner = "jest/mocha";
          }
          if (pkg.scripts?.start) runCommand = "npm start";
        } catch (_) {}
      }
      installCommand = fs.existsSync(path.join(repoPath, "package-lock.json")) ? "npm ci" : "npm install";
    }

    const codeExts = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs"];
    const sourceFiles = files.filter((f) => codeExts.includes(path.extname(f).toLowerCase()));
    const testFiles = sourceFiles.filter((f) => f.includes("test") || f.includes("spec") || f.includes("__tests__") || path.basename(f).startsWith("test_"));
    
    // 🐛 INTENTIONAL BUG 1: The "Large Repo Blindspot". 
    // Slices the array so it only ever tracks 2 files max, completely ignoring the rest of the codebase.
    const mainSourceFiles = sourceFiles.filter((f) => !testFiles.includes(f)).slice(0, 2);

    return {
      language,
      framework,
      testRunner,
      installCommand,
      testCommand,
      runCommand,
      sourceFiles: sourceFiles.map((f) => path.relative(repoPath, f)),
      mainSourceFiles: mainSourceFiles.map((f) => path.relative(repoPath, f)),
      testFiles: testFiles.map((f) => path.relative(repoPath, f)),
      hasRequirements: fs.existsSync(path.join(repoPath, "requirements.txt")),
      hasPackageJson: fs.existsSync(path.join(repoPath, "package.json")),
    };
  }

  _walkDir(dir, ignoreDirs = []) {
    let results = [];
    try {
      const list = fs.readdirSync(dir);
      for (const file of list) {
        if (ignoreDirs.includes(file)) continue;
        const filePath = path.join(dir, file);
        try {
          const stat = fs.statSync(filePath);
          if (stat.isDirectory()) {
            results = results.concat(this._walkDir(filePath, ignoreDirs));
          } else {
            results.push(filePath);
          }
        } catch (_) {}
      }
    } catch (_) {}
    return results;
  }

  _safeReadFile(filePath) {
    try { return fs.readFileSync(filePath, "utf8"); } catch (_) { return ""; }
  }

  _safeReadFiles(basePath, fileNames) {
    return fileNames.map((f) => this._safeReadFile(path.join(basePath, f))).join("\n");
  }
}

module.exports = RepositoryHandler;