import json
import boto3
import requests
import zipfile
import time
import random
from scanners.base import BaseScanner

MAX_RETRIES = 10
DELAY_SECONDS = 5

class CodeGuruScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        self.codeguru_sec = boto3.client('codeguru-security')
        self.zip_name = "/opt/ml/code/script.zip"
        self.file_ext = {
            "Python": ".py",
            "JavaScript": ".js",
            "Java": ".java"
        }
        
    def scan(self, script, language):
        scanName = str(random.randint(10 ** 15, (10 ** 16) - 1))
        results = super().scan(script, language)
        if len(results) > 0:
            return results
        # Create PreSign S3 URL to store test code
        upload_url_response = self.codeguru_sec.create_upload_url(
            scanName = scanName
        )
        upload_url = upload_url_response['s3Url']
        codeArtifactId =  upload_url_response['codeArtifactId']
        headers = upload_url_response['requestHeaders']
        with zipfile.ZipFile(self.zip_name, 'w') as zipf:
            # Add the file to the zip
            zipf.write(self.file_name)
        # Upload the test code to S3

        with open(self.zip_name, "rb") as file:
            response = requests.put(
                upload_url,
                headers=headers,
                data=file,
                verify=False  # verify=False is equivalent to curl's -k
            )

        # Create a code scan using code uploaded to an S3 bucket

        code_scan = self.codeguru_sec.create_scan(
            analysisType = 'All',
            resourceId={
                'codeArtifactId': codeArtifactId,
            },
            scanName = scanName,
            scanType = 'Express'
        )

        # Function checking if the scanning job is completed
        def is_job_complete():
            scan_status = self.codeguru_sec.get_scan(
                scanName = scanName
            )
            return scan_status  # Adjust this based on actual API response structure

        retry_count = 0

        # Polling security scan results
        while retry_count < MAX_RETRIES:
            scan_status = is_job_complete()
            if scan_status['scanState'] != 'InProgress':
                print("Job is complete!")
                if scan_status['scanState'] == 'Successful':
                    print("Job succeeded!")
                    finding = self.codeguru_sec.get_findings(
                        scanName=scanName
                    )
                    output = {}
                    for result in finding['findings']:
                        line_tuple = f'{result["vulnerability"]["filePath"]["startLine"]}:{result["vulnerability"]["filePath"]["endLine"]}'
                        if line_tuple not in output:
                            output[line_tuple] = ""
                        output[line_tuple] += f'{result["remediation"]["recommendation"]["text"]}\n\n'
                    for out in output:
                        results.append(
                            {
                                "Start line": int(out.split(":")[0]), 
                                "End line": int(out.split(":")[1]), 
                                "Recommendations": output[out]
                            }
                        )
                    return results
                else:
                    raise Exception("Job failed!")
                break
            print(f"Job not complete yet. Waiting {DELAY_SECONDS} seconds before checking again...")
            time.sleep(DELAY_SECONDS)
            retry_count += 1

        if retry_count == MAX_RETRIES:
            raise "Max retries reached. Job may still be running or there might be an issue."