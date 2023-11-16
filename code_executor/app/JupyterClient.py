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

# class JupyterNotebook:
#     def __init__(self, kernel_name: str = "python3", startup_timeout: float = 60):
#         self.km = KernelManager(kernel_name=kernel_name)
#         self.km.start_kernel()
#         self.kc = self.km.client()
#         self.kc = next(run_kernel(kernel_name).gen)
#         self.kc.start_channels()
#         try:
#             self.kc.wait_for_ready(timeout=startup_timeout)
#         except RuntimeError:
#             self.kc.stop_channels()
#             self.km.shutdown_kernel()
#             raise
        
#     def restart(self):
#         self.km.restart_kernel(now=True)

#     def clean_output(self, outputs):
#         outputs_only_str = list()
#         for i in outputs:
#             if type(i) == dict:
#                 if "text/plain" in list(i.keys()):
#                     outputs_only_str.append(i["text/plain"])
#             elif type(i) == str:
#                 outputs_only_str.append(i)
#             elif type(i) == list:
#                 error_msg = "\n".join(i)
#                 error_msg = re.sub(r"\x1b\[.*?m", "", error_msg)
#                 outputs_only_str.append(error_msg)

#         return "\n".join(outputs_only_str).strip()

#     def add_and_run(self, code_string, timeout=10):
#         # This inner function will be executed in a separate thread
#         def run_code_in_thread(timeout=timeout):
#             nonlocal outputs, error_flag

#             # Execute the code and get the execution count
#             msg_id = self.kc.execute(code_string)

#             while True:
#                 try:
#                     msg = self.kc.get_iopub_msg(timeout=timeout)

#                     msg_type = msg["header"]["msg_type"]
#                     content = msg["content"]

#                     if msg_type == "execute_result":
#                         outputs.append(content["data"])
#                     elif msg_type == "stream":
#                         outputs.append(content["text"])
#                     elif msg_type == "error":
#                         error_flag = True
#                         outputs.append(content["traceback"])

#                     # If the execution state of the kernel is idle, it means the cell finished executing
#                     if msg_type == "status" and content["execution_state"] == "idle":
#                         break
#                 except:
#                     break

#         outputs = []
#         error_flag = False

#         # Start the thread to run the code
#         thread = threading.Thread(target=run_code_in_thread)#, args=(timeout))
#         thread.start()

#         # Wait for 10 seconds for the thread to finish
#         thread.join(timeout=timeout)

#         # If the thread is still alive after 10 seconds, it's a timeout
#         if thread.is_alive():
#             outputs = [f"Timeout after {timeout} seconds"]
#             error_flag = True

#         return self.clean_output(outputs), error_flag

#     def close(self):
#         """Shutdown the kernel."""
#         self.km.shutdown_kernel()