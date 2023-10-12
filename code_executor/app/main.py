import json
import argparse
import logging as logger
from typing import Union
from fastapi import FastAPI, Request
import uvicorn
import pkg_resources
from JupyterClient import JupyterNotebook, JupyterKernels

app = FastAPI()

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

# list of packages
@app.get("/list_packages")
def list_packages():
    try:
        installed_packages = pkg_resources.working_set
        installed_packages_list = sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])
        return installed_packages_list
    
    except Exception as e:
        # Handle any exceptions that occur during execution
        return f"An error occurred from packages: {str(e)}"

@app.get("/list_kernel_specs")
def list_kernel_specs():
    try:
        return jk.ks
    
    except Exception as e:
        # Handle any exceptions that occur during execution
        return f"An error occurred from packages: {str(e)}"

# code
@app.post("/execute_code")
async def execute_code(request: Request):
    params = await request.json()
    code = params.get("code")
    timeout = params.get("timeout")
    kernel_name = params.get("kernel_name", "python3")
    if code:
        try:
            if not timeout:
                timeout = 10
            out, error_flag = nbs[kernel_name].add_and_run(code, timeout)            
            return {"output": out, "error": error_flag}

        # java? https://github.com/SpencerPark/IJava
        # bash script? https://pypi.org/project/bash_kernel/

        except Exception as e:
            # Handle any exceptions that occur during execution
            return f"An error occurred: {str(e)}"
        
@app.post("/restart_kernel")
async def restart_kernel(request: Request):
    # if python logic
    params = await request.json()
    code = params.get("code")
    timeout = params.get("timeout")
    kernel_name = params.get("kernel_name", "python3")
    if code:
        try:
            nbs[kernel_name].restart()       
            return {"output": f"Kernel {kernel_name} restarted!", "error": False}

        except Exception as e:
            # Handle any exceptions that occur during execution
            return f"An error occurred: {str(e)}"
    
if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    jk = JupyterKernels()
    nbs = {}
    for ks in jk.ks:
        nbs[ks] = JupyterNotebook(ks)
    logger.info(f"args: {args}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")