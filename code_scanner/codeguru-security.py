import boto3
import requests
import zipfile
import time
import random
import json


def lambda_handler(event, context):
    codeguru_sec = boto3.client('codeguru-security')
    MAX_RETRIES = 15
    DELAY_SECONDS = 1

    scanName = str(random.randint(10 ** 15, (10 ** 16) - 1))

    # Create PreSign S3 URL to store test code
    upload_url_response = codeguru_sec.create_upload_url(
        scanName=scanName
    )

    upload_url = upload_url_response['s3Url']
    codeArtifactId = upload_url_response['codeArtifactId']
    headers = upload_url_response['requestHeaders']

    print(headers)
    print(upload_url)
    print(codeArtifactId)

    # zip python code as Zip

    lang = event['lang']
    lang_suffix_mapping = {
        'Python': '.py',
        'Java': '.java',
        'JavaScript': '.js'
    }

    file_name = scanName + lang_suffix_mapping[lang]

    #code_content_json = json.loads(event)

    code_content = event['code_content']
    file_path = '/tmp/'+file_name

    with open(file_path, 'w') as file:
        # Write the string to the file
        file.write(code_content)

    zip_name = scanName + '.zip'
    zip_path = '/tmp/'+zip_name

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # Add the file to the zip
        zipf.write(file_path)

    # Upload the test code to S3

    with open(zip_path, "rb") as file:
        response = requests.put(upload_url, headers=headers, data=file,
                                verify=False)  # verify=False is equivalent to curl's -k

    # Create a code scan using code uploaded to an S3 bucket

    code_scan = codeguru_sec.create_scan(
        analysisType='All',
        resourceId={
            'codeArtifactId': codeArtifactId,
        },
        scanName=scanName,
        scanType='Express'
    )

    # Function checking if the scanning job is completed
    def is_job_complete():
        scan_status = codeguru_sec.get_scan(
            scanName=scanName
        )
        return scan_status['scanState'] != 'InProgress'  # Adjust this based on actual API response structure

    retry_count = 0

    # Polling security scan results
    while retry_count < MAX_RETRIES:
        if is_job_complete():
            print("Job is complete!")
            scan_status = codeguru_sec.get_scan(
                scanName=scanName
            )
            if scan_status['scanState'] == 'Successful':
                print("Job succeeded!")
                finding = codeguru_sec.get_findings(
                    scanName=scanName
                )
                if finding['findings']:
                    print("Found Vulnerabilities")
                    print(finding['findings'])
                else:
                    print("No Vulnerabilities Found")
            else:
                print("Job failed!")
            break
        print(f"Job not complete yet. Waiting {DELAY_SECONDS} seconds before checking again...")
        time.sleep(DELAY_SECONDS)
        retry_count += 1

    if retry_count == MAX_RETRIES:
        print("Max retries reached. Job may still be running or there might be an issue.")