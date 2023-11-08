class BaseScanner:
    file_ext = {
        "Python": ".py",
        "JavaScript": ".js",
        "Java": ".java",
        "Shell": ".sh",
        "Bash": ".sh",
        "R": ".r"
    }
    scan_path = "/opt/ml/code/script"
        
    def save_script(self, script, language):
        self.file_name = self.scan_path + self.file_ext[language]
        with open(self.file_name, "w") as scan_script:
            scan_script.write(script)
            
    def validate(self, language):
        if language not in self.file_ext.keys():
            raise f"UnSupported programming language {language}, supported languages are {self.file_ext.keys()}"
    
    def scan(self, script, language):
        self.validate(language)
        self.save_script(script, language)
        return []