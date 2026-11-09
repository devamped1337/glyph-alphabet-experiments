"""Content-free errors safe to show in the terminal."""


class KitError(ValueError):
    def __init__(self, rule, detail, message=None):
        self.rule, self.detail, self.message = rule, detail, message
        where = "message %d; " % message if message is not None else ""
        super().__init__(where + "rule " + rule + ": " + detail)
