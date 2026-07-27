
import subprocess
import json

def create_mutant(code):
    return code.replace(">", ">=")

def run_tests():
    result = subprocess.run(["pytest"], capture_output=True)
    return result.returncode == 0

def main():
    with open("source_code.py") as f:
        code = f.read()

    mutant = create_mutant(code)

    with open("mutant.py", "w") as f:
        f.write(mutant)

    success = run_tests()

    report = {
        "killed": not success
    }

    with open("mutation_report.json", "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    main()
