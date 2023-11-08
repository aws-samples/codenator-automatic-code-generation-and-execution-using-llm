from scanners.base import BaseScanner
import subprocess
import json

class SemgrepScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        self.cmd = [
            "/usr/local/bin/semgrep",
            "scan",
            "-q",
            "--json",
            "--disable-version-check",
            "--disable-nosem",
            "--config=auto"
        ]
        
    def scan(self, script, language):
        results = super().scan(script, language)
        proc = subprocess.Popen(self.cmd + [self.file_name], stdout=subprocess.PIPE)
        scan_results = json.loads(proc.stdout.read())
        output = {}
        for result in scan_results["results"]:
            line_tuple = f'{result["start"]["line"]}:{result["end"]["line"]}'
            if line_tuple not in output:
                output[line_tuple] = ""
            output[line_tuple] += f'{result["extra"]["message"]}\n\n'
        for out in output:
            results.append(
                {
                    "Start line": int(out.split(":")[0]), 
                    "End line": int(out.split(":")[1]), 
                    "Recommendations": output[out]
                }
            )
        return results