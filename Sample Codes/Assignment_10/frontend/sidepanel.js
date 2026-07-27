const API_BASE = "http://127.0.0.1:8000"

let requirements = ""
let stories = ""
let prototypeHTML = ""
let prototypeJS = ""
let prototypeData = "{}"
let currentOutput = ""
let testCases = []
let testResults = {}

const status = document.getElementById("status")
const output = document.getElementById("output")
const specBox = document.getElementById("spec")
const audioInput = document.getElementById("audio")
const testChecklist = document.getElementById("testChecklist")
const downloadReportBtn = document.getElementById("downloadReport")

// ======================
// SHARED HELPER
// ======================

async function postJSON(path, body) {

  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  })

  if (!res.ok) {
    let detail = ""
    try {
      const errJson = await res.json()
      detail = errJson.detail || JSON.stringify(errJson)
    } catch (e) {
      detail = await res.text()
    }
    throw new Error(`Server error ${res.status}: ${detail}`)
  }

  return res.json()
}

// ======================
// STAGE 1 (text OR audio)
// ======================

document.getElementById("generateReq").onclick = async () => {

  try {

    const file = audioInput.files[0]

    let data

    if (file) {

      status.innerText = "Transcribing audio and generating requirements..."

      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(API_BASE + "/extract_audio", {
        method: "POST",
        body: formData
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Server error ${res.status}: ${text}`)
      }

      data = await res.json()

    } else {

      const text = specBox.value.trim()

      if (!text) {
        status.innerText = "Please paste a specification or choose a .wav file first"
        return
      }

      status.innerText = "Generating requirements..."

      data = await postJSON("/extract_text", { text: text })
    }

    requirements = data.requirements
    currentOutput = requirements
    output.innerText = requirements
    status.innerText = "Requirements generated"

  } catch (e) {
    console.error("Requirements error:", e)
    status.innerText = "Failed to generate requirements: " + e.message
  }

}

// ======================
// STAGE 2A
// ======================

document.getElementById("generateStories").onclick = async () => {

  try {

    if (!requirements) {
      status.innerText = "Generate requirements first"
      return
    }

    status.innerText = "Generating user stories..."

    const data = await postJSON("/generate_user_stories", { requirements: requirements })

    stories = data.stories
    currentOutput = stories
    output.innerText = stories
    status.innerText = "Stories generated"

  } catch (e) {
    console.error("Stories error:", e)
    status.innerText = "Failed to generate stories: " + e.message
  }

}

// ======================
// STAGE 2B
// ======================

document.getElementById("verifyInvest").onclick = async () => {

  try {

    if (!stories) {
      status.innerText = "Generate user stories first"
      return
    }

    status.innerText = "Evaluating INVEST..."

    const data = await postJSON("/verify_invest", { stories: stories })

    currentOutput = data.invest
    output.innerText = data.invest
    status.innerText = "INVEST verified"

  } catch (e) {
    console.error("INVEST error:", e)
    status.innerText = "Failed to verify INVEST: " + e.message
  }

}

// ======================
// STAGE 3
// ======================

document.getElementById("generatePrototype").onclick = async () => {

  try {

    if (!requirements || !stories) {
      status.innerText = "Generate requirements and user stories first"
      return
    }

    status.innerText = "Generating prototype..."

    const data = await postJSON("/generate_prototype", {
      requirements: requirements,
      stories: stories
    })

    console.log("Prototype response:", data)

    if (!data.html) {
      throw new Error(data.error || "Prototype not returned")
    }

    prototypeHTML = data.html
    prototypeJS = data.js
    prototypeData = data.data || "{}"

    currentOutput = prototypeHTML
    output.innerText = prototypeHTML

    status.innerText = "Prototype generated"

  } catch (e) {
    console.error("Prototype error:", e)
    status.innerText = "Prototype generation failed: " + e.message
  }

}

// ======================
// PREVIEW
// ======================

document.getElementById("previewPrototype").onclick = () => {

  if (!prototypeHTML) {
    alert("Generate prototype first")
    return
  }

  let mockData = {}
  try {
    mockData = JSON.parse(prototypeData)
  } catch (e) {
    console.warn("Mock data was not valid JSON, using empty object instead:", e)
    mockData = {}
  }

  const tab = window.open()

  if (!tab) {
    alert("Preview popup was blocked. Please allow popups for this extension.")
    return
  }

  tab.document.open()

  const pageHTML = [
    "<html><head>",
    '<script src="https://cdn.tailwindcss.com"><' + "/script>",
    "</head><body>",
    prototypeHTML,
    "<script>const mockData = " + JSON.stringify(mockData) + ";<" + "/script>",
    "<script>" + (prototypeJS || "") + "<" + "/script>",
    "</body></html>"
  ].join("\n")

  tab.document.write(pageHTML)
  tab.document.close()

}

// ======================
// STAGE 4
// ======================

function renderTestChecklist() {

  testChecklist.innerHTML = ""

  testCases.forEach(tc => {

    const box = document.createElement("div")
    box.className = "test-case"

    const stepsHTML = tc.steps.map(s => `<li>${escapeHTML(s)}</li>`).join("")

    box.innerHTML = `
      <strong>${escapeHTML(tc.id)}: ${escapeHTML(tc.title)}</strong>
      <ol>${stepsHTML}</ol>
      <div><em>Expected:</em> ${escapeHTML(tc.expected)}</div>
      <select data-id="${escapeHTML(tc.id)}">
        <option value="Not Run">Not Run</option>
        <option value="Pass">Pass</option>
        <option value="Fail">Fail</option>
      </select>
    `

    testChecklist.appendChild(box)
  })

  testChecklist.querySelectorAll("select").forEach(sel => {
    sel.value = testResults[sel.dataset.id] || "Not Run"
    sel.addEventListener("change", () => {
      testResults[sel.dataset.id] = sel.value
    })
  })

  downloadReportBtn.style.display = testCases.length ? "block" : "none"
}

function escapeHTML(str) {
  const div = document.createElement("div")
  div.innerText = str == null ? "" : String(str)
  return div.innerHTML
}

document.getElementById("generateTests").onclick = async () => {

  try {

    if (!stories) {
      status.innerText = "Generate user stories first"
      return
    }

    status.innerText = "Generating test cases..."

    const data = await postJSON("/generate_tests", { stories: stories })

    testCases = data.tests || []
    testResults = {}
    testCases.forEach(tc => { testResults[tc.id] = "Not Run" })

    currentOutput = JSON.stringify(testCases, null, 2)
    output.innerText = `${testCases.length} test case(s) generated. Open "Preview Prototype" in one tab and work through the checklist below, marking each Pass/Fail as you go.`

    renderTestChecklist()

    status.innerText = "Test cases generated - execute them against the preview below"

  } catch (e) {
    console.error("Test generation error:", e)
    status.innerText = "Failed to generate tests: " + e.message
  }

}

// ======================
// TEST EXECUTION REPORT
// ======================

downloadReportBtn.onclick = () => {

  const lines = ["Test Execution Report", "======================", ""]

  testCases.forEach(tc => {
    lines.push(`${tc.id}: ${tc.title}`)
    lines.push("Steps:")
    tc.steps.forEach((s, i) => lines.push(`  ${i + 1}. ${s}`))
    lines.push(`Expected: ${tc.expected}`)
    lines.push(`Result: ${testResults[tc.id] || "Not Run"}`)
    lines.push("")
  })

  const passCount = Object.values(testResults).filter(r => r === "Pass").length
  const failCount = Object.values(testResults).filter(r => r === "Fail").length
  const notRunCount = Object.values(testResults).filter(r => r === "Not Run" || !r).length

  lines.push(`Summary: ${passCount} passed, ${failCount} failed, ${notRunCount} not run`)

  const blob = new Blob([lines.join("\n")], { type: "text/plain" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")

  a.href = url
  a.download = "test_execution_report.txt"
  a.click()

  URL.revokeObjectURL(url)

}

// ======================
// DOWNLOAD
// ======================

document.getElementById("download").onclick = () => {

  if (!currentOutput) {
    alert("Nothing to download yet")
    return
  }

  const blob = new Blob([currentOutput], { type: "text/plain" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")

  a.href = url
  a.download = "artifact.txt"
  a.click()

  URL.revokeObjectURL(url)

}
