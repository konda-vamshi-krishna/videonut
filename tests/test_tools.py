import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.check_env import check_command, check_import

class TestEnvironment(unittest.TestCase):
    def test_check_command_exists(self):
        # python should definitely be in path
        self.assertTrue(check_command("python", "Python"))

    def test_check_import_exists(self):
        self.assertTrue(check_import("sys"))

    def test_check_import_missing(self):
        self.assertFalse(check_import("non_existent_module_xyz"))

class TestImageGrabber(unittest.TestCase):
    @patch('requests.get')
    def test_download_image(self, mock_get):
        # Import dynamically to avoid top-level side effects if any
        from tools.downloaders import image_grabber
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'fake', b'image', b'data']
        mock_get.return_value = mock_response

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            image_grabber.download_image("http://test.com/img.png", "test_output.png")
            mock_file.assert_called_with("test_output.png", "wb")

if __name__ == '__main__':
    unittest.main()