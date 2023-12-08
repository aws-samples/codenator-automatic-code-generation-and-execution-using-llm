# Code Executor
As its name implies, this component is used to execute code generated from LLM, it requires permission to `kms:decrypt` action.
A script is allowed to save or interact with fales in `tmp/` direcroty (`/opt/code/tmp/`)

## Starting the server
To start API Layer server, you can use the below command:
```
$ main.py [optional args]
```

`[optional args]` can be any combination of:<br>
`--host`: host url, default value `localhost`<br>
`--port`: host port, default value `8080`<br>
`--kms`: *Amazon KMS* key id or alias, this key is used to decrypt the script to be executed.<br>

## API endpoints

Code executor has the following API endpoints:
- `/ping` (GET): A standard health check endpoint.
- `list_kernel_specs` (GET): Lists all available kernels that can be used for execution
- `/execute_code` (POST): Execute encripted script.
     - Required parameters:<br>
     `code`: script encrypted with kms key.<br>
     `kernel_name`: name of kernel to run the code<br>
