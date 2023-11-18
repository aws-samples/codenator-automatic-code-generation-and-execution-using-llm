from jupyter_client import KernelManager, run_kernel
from jupyter_client.kernelspec import KernelSpecManager
import threading
import re

class JupyterKernels:
    def __init__(self):
        self.ksm = KernelSpecManager()
        self.ks = {}
        all_specs = self.ksm.get_all_specs()
        for ks in all_specs:
            self.ks[ks] = {
                "display_name": all_specs[ks]["spec"]["display_name"],
                "language": all_specs[ks]["spec"]["language"]
            }

class JupyterNotebook:
    def __init__(self, kernel_name: str = "python3"):
        self.kc = run_kernel(kernel_name=kernel_name).gen

    def clean_output(self, outputs):
        outputs_only_str = list()
        for i in outputs:
            if type(i) == dict:
                if "text/plain" in list(i.keys()):
                    outputs_only_str.append(i["text/plain"])
            elif type(i) == str:
                outputs_only_str.append(i)
            elif type(i) == list:
                error_msg = "\n".join(i)
                error_msg = re.sub(r"\x1b\[.*?m", "", error_msg)
                outputs_only_str.append(error_msg)

        return "\n".join(outputs_only_str).strip()

    def run_cell(self, code_string, timeout=10):
        # Execute the code and get the execution count
        outputs = []
        error_flag = False
        client = next(self.kc)
        msg_id = client.execute(code_string)

        while True:
            try:
                msg = client.get_iopub_msg(timeout=timeout)

                msg_type = msg["header"]["msg_type"]
                content = msg["content"]

                if msg_type == "execute_result":
                    outputs.append(content["data"])
                elif msg_type == "stream":
                    outputs.append(content["text"])
                elif msg_type == "error":
                    error_flag = True
                    outputs.append(content["traceback"])

                # If the execution state of the kernel is idle, it means the cell finished executing
                if msg_type == "status" and content["execution_state"] == "idle":
                    break
            except:
                break

        return self.clean_output(outputs), error_flag