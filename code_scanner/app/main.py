import argparse
import json
import logging as logger
from fastapi import FastAPI, Request
import uvicorn
from scanners.semgrep import SemgrepScanner
import traceback

app = FastAPI()

scanners = {
    "semgrep": SemgrepScanner()
}

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

@app.post("/scan")
async def scan(request: Request):
    params = await request.json()
    script = params.get("script")
    language = params.get("language")
    scanner_name = params.get("scanner", "semgrep")
    if scanner_name not in scanners.keys():
        return {"error": f"UnSupported security scanner {scanner_name}, supported scanners are {scanners.keys()}"}
    scanner = scanners[scanner_name]
    try:
        return scanner.scan(script, language)
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\nStackTrace: {tb}")
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb}

    
if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    logger.info(f"args: {args}")
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )