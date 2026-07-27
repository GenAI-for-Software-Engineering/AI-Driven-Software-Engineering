const Groq = require("groq-sdk");

let _groq = null;
function getGroq() {
  if (!_groq) {
    if (!process.env.GROQ_API_KEY) {
      throw new Error("GROQ_API_KEY environment variable is not set. Add it to backend/.env");
    }
    _groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
  }
  return _groq;
}

// ─────────────────────────────────────────────
//  SYSTEM PROMPTS
// ─────────────────────────────────────────────

const BUG_ANALYSIS_SYSTEM_PROMPT = `You are an expert software engineer and automated debugging assistant specialized in detecting and fixing bugs across Python, JavaScript, TypeScript, and other common languages.

Your role in this pipeline:
1. You receive a code snippet, error messages, stack traces, and test failures.
2. You must analyze the root cause of each bug with precision.
3. You respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON.

Your JSON response must follow this exact schema:
{
  "bugs": [
    {
      "id": "BUG-001",
      "file": "<relative file path>",
      "line": <line number or null>,
      "type": "<syntax_error | runtime_error | logic_error | import_error | type_error | name_error | assertion_error | other>",
      "severity": "<critical | high | medium | low>",
      "description": "<clear, specific description of what is wrong>",
      "root_cause": "<technical explanation of the underlying cause>",
      "original_code": "<the exact buggy code snippet>",
      "fixed_code": "<the complete corrected replacement code>",
      "explanation": "<step-by-step chain-of-thought reasoning explaining the fix>",
      "confidence": <0.0 to 1.0>
    }
  ],
  "summary": "<overall summary of all bugs found>",
  "fix_strategy": "<overall strategy used to address the bugs>",
  "estimated_pass_after_fix": "<percentage estimate like 80% or high/medium/low>"
}

Rules you MUST follow:
- If original_code spans multiple lines, preserve indentation exactly.
- fixed_code must be a complete drop-in replacement, not a diff or partial snippet.
- Do NOT hallucinate bugs that are not in the error output or code.
- If you detect no bugs in a snippet, return an empty bugs array with a summary explaining why.
- Be surgical — fix only what is broken. Do not refactor unrelated code.
- If context is insufficient, set confidence below 0.5 and note it in explanation.
- Always output raw JSON. Never wrap in \`\`\`json blocks.`;

const STATIC_ANALYSIS_SYSTEM_PROMPT = `You are a static code analysis expert. You receive raw source code files and must identify potential issues without running the code.

Analyze for:
- Syntax errors and typos
- Undefined variables or imports
- Unused variables that may indicate copy-paste bugs
- Type mismatches (where inferrable)
- Missing return statements
- Infinite loop risks
- Security issues (SQL injection, hardcoded secrets)
- Dead code or unreachable branches

Respond ONLY with a valid JSON object:
{
  "static_issues": [
    {
      "file": "<file path>",
      "line": <line number or null>,
      "issue": "<description of the static issue>",
      "severity": "<critical | high | medium | low>",
      "category": "<syntax | import | logic | security | style>"
    }
  ],
  "file_summary": "<brief description of what each analyzed file does>",
  "language": "<detected primary language>",
  "framework": "<detected framework or 'none'>"
}

Output raw JSON only. No markdown. No preamble.`;

const ITERATION_IMPROVEMENT_PROMPT = `You are an automated fix-refinement agent. A previous fix attempt was applied but tests still fail.

You receive:
- The previously attempted fix
- The NEW error output after applying that fix
- The original bug description

Your job is to generate a BETTER fix that addresses both the original bug and any regressions introduced.

Respond ONLY with valid JSON in this exact schema:
{
  "bugs": [
    {
      "id": "BUG-001",
      "file": "<file path>",
      "line": <line number or null>,
      "type": "<error type>",
      "severity": "<critical | high | medium | low>",
      "description": "<what is now wrong after the previous fix>",
      "root_cause": "<why the previous fix was insufficient>",
      "original_code": "<the code as it currently exists (post-previous-fix)>",
      "fixed_code": "<the corrected replacement>",
      "explanation": "<chain-of-thought: what the previous fix missed and why this one works>",
      "confidence": <0.0 to 1.0>
    }
  ],
  "summary": "<what changed vs previous iteration>",
  "fix_strategy": "<revised approach>",
  "estimated_pass_after_fix": "<percentage estimate>"
}

Output raw JSON only.`;

// ✅ NEW: System prompt for generating synthetic tests when none exist
const TEST_GENERATION_SYSTEM_PROMPT = `You are an expert test engineer. You receive source code and must generate comprehensive pytest unit tests.

Requirements:
- Generate tests that cover: normal cases, edge cases, invalid inputs, boundary conditions
- Mock external dependencies (databases, APIs, file systems) using unittest.mock
- Each test function must start with test_
- Import modules using relative paths matching the project structure
- Tests must be runnable with: python -m pytest test_synthetic_llm_generated.py

Respond ONLY with valid JSON:
{
  "test_code": "<complete Python test file as a single string with \\n for newlines>"
}

The test_code value must be a valid Python file. No markdown. No explanation outside JSON.`;

async function analyzeWithGroq(userPrompt, mode = "bug_fix") {
  const systemPrompts = {
    bug_fix: BUG_ANALYSIS_SYSTEM_PROMPT,
    static: STATIC_ANALYSIS_SYSTEM_PROMPT,
    iteration: ITERATION_IMPROVEMENT_PROMPT,
    test_gen: TEST_GENERATION_SYSTEM_PROMPT, // ✅ NEW
  };

  const systemPrompt = systemPrompts[mode] || BUG_ANALYSIS_SYSTEM_PROMPT;

  const grokResponse = await getGroq().chat.completions.create({
    model: "llama-3.1-8b-instant",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    max_tokens: 4000,
    temperature: 0.1,
  });

  const rawText = grokResponse.choices[0]?.message?.content || "{}";
  const cleaned = rawText
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();

  try {
    return JSON.parse(cleaned);
  } catch (e) {
    return {
      bugs: [],
      summary: "LLM response could not be parsed as JSON.",
      raw_response: rawText,
      parse_error: e.message,
    };
  }
}

module.exports = { analyzeWithGroq };
