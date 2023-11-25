class BaseStore:
    
    def save(self):
        raise NotImplementedError("Not implemented in base model, make sure to override this method.")
    
    def search(self):
        raise NotImplementedError("Not implemented in base model, make sure to override this method.")
