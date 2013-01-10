

class Config(object):

    def __init__(self):
        self.php_version = (5, 3)

    def _freeze_(self):
        return True
