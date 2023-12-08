# Codenator 🤖️
**Automatic code generation and execustion using Large Language Models**<br><br>
Codenator is a scalible AWS cloud solution for generating, testing, scanning and executing code.
## Codenator in Action
![Codenator demo](assets/codenator.gif)
## Features
It currently supports the following features:
- LLM Agent interaction Code generation using *Bedrock* or models hosted on *Amazon SageMaker endpoints*.
- Easy integration with new released models.
- Code security scan with Amazon *CodeGuru* or [*SemGrep*](https://semgrep.dev/).
- Code execution in sandboxed docker container with encrypted input powered by *Amazon KMS*.
- Automatic execution failure feedback and correction.
- Code execution requires manual approval for increased security.
- Task storage and retrieval powered by *Amazon Opensearch Serverless*, to allow interaction with a task at later time.
- Shared storage folder to allow exchanging files between agent and code executor.
## Architecture
![Codenator Architecture](assets/codenator-architecture.png)
Below is an overview description of each component. To dive deep into each one, click on the provided link for each componsent.
* [API layer (LLM Service)](src/codenator/api_layer/README.md): Responsible for unifing LLM invocations. It uses *ECS Fragate* and *Amazon DynamoDB* to interact with various LLM service providers and add new ones without the need to change code.
* [Prompt Store](src/codenator/controller/app/prompt/README.md): Powered by *DynamoDB*, enables storage, modification, versioning and retrieval of prompts at runtime.
* [Controller (orchestration layer)](src/codenator/controller/README.md): Holds the the main logic for the Codenator agent and acts as a central component for the solution.  
* WebUI (UI layer): Gradio app web ui.
* [Code Executor (task executor)](src/codenator/code_executor/README.md): Executes code in sandbox, script must be encrypted with *Amazon KMS*. Currently supports *Python*, *Java*, *JavaScript*, *R*, *Julia*, *Bash* and *Shell*.
* [Task store](src/codenator/task_store/README.md): Powered by *Amazon Opensearch Serverless*, to save and retrieve tasks.
* [Code scanner (Security Check/Guradrail)](src/codenator/code_scanner/README.md): Performs static code scanning to detect any vulnerabilities in generated code. Currently supports *Amazon CodeGuru* and *SemGrep* scanners.
* feedback: User feedback hosted on S3.
* logging: Conversation logging to S3.
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
