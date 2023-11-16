import json
import argparse
import logging as logger
from typing import Union
from fastapi import FastAPI, Request
import uvicorn
import pkg_resources
from JupyterClient import JupyterNotebook, JupyterKernels
import traceback

app = FastAPI()

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

# # list of packages
# @app.get("/list_packages")
# def list_packages():
#     try:
#         installed_packages = pkg_resources.working_set
#         installed_packages_list = sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])
#         return installed_packages_list
    
#     except Exception as e:
#         # Handle any exceptions that occur during execution
#         return f"An error occurred from packages: {str(e)}"

@app.get("/list_kernel_specs")
def list_kernel_specs():
    try:
        return jk.ks
    
    except Exception as e:
        # Handle any exceptions that occur during execution
        return {"error": f"An error occurred: {str(e)}", "stacktrace": traceback.format_exc()}

@app.post("/execute_code")
async def execute_code(request: Request):
    params = await request.json()
    code = params.get("code")
    timeout = params.get("timeout", 10)
    kernel_name = params.get("kernel_name", "python3")
    if code:
        try:
            nb = JupyterNotebook(kernel_name=kernel_name)
            out, error = nb.run_cell(code, timeout)            
            return {"output": out, "error": error}

        # java? https://github.com/SpencerPark/IJava
        # bash script? https://pypi.org/project/bash_kernel/

        except Exception as e:
            # Handle any exceptions that occur during execution
            return {"error": f"An error occurred: {str(e)}", "stacktrace": traceback.format_exc()}

if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    jk = JupyterKernels()
    logger.info(f"args: {args}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")