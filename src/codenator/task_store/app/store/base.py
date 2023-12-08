class BaseStore:
    def __init__(self):
        config = self.get_config()
        for key, value in config.items():
            setattr(self, key, value)
    
    def save(self):
        raise NotImplementedError("Not implemented in base model, make sure to override this method.")
    
    def search(self):
        raise NotImplementedError("Not implemented in base model, make sure to override this method.")
        
    def get_config(self):
        return {}
