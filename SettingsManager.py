import json


class SettingsManager:
    def __init__(self, settings_path: str = ''):
        self.settings: dict = {}
        if settings_path != '':
            self.load_settings(settings_path)

    def load_settings(self, settings_path):
        """
        
        :param settings_path: Path to the settings file
        :return: Returns a JSON-string containing the settings
        """
        with open(settings_path) as settings_file:
            self.settings = json.load(settings_file)
