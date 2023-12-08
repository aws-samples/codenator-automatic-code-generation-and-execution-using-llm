# Code Scanner
This component is responsible for implementing static security scan on generated script to detect any vulnerabilities. It currently supports scans powered by *Amazon CodeGuru* and *SemGrep*.

## Starting the server
To start API Layer server, you can use the below command:
```
$ main.py [optional args]
```

`[optional args]` can be any combination of:<br>
`--host`: host url, default value `localhost`<br>
`--port`: host port, default value `8080`<br>
`--workers`: number of uvicorn workers, default value `3`<br>
`--namespace`: namespace used to publish CloudWatc Metrics, default value `Codenator/api-layer/`<br>

## API endpoints

Code executor has the following API endpoints:
- `/ping` (GET): A standard health check endpoint.
- `/scan` (POST): Execute encripted script.
    - Required parameters:
        `script`: script to scan.<br>
        `language`: programing language of the script.<br>
    - Optional parameters:
        `scanner`: defaults to `semgrep`. valid values `codeguru` or `semgrep`
