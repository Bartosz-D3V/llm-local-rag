import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from local_mcp.file.handler import URLHandler


class TestURLHandler(unittest.TestCase):
    def test_url_handler_skips_if_already_exists(self):
        mock_repo = MagicMock()
        mock_repo.exists.return_value = True

        handler = URLHandler(mock_repo)
        handler.process("/tmp/test.url", "my_table")

        mock_repo.exists.assert_called_once_with(
            file_path="/tmp/test.url", table_name="my_table"
        )
        mock_repo.save.assert_not_called()

    def test_url_handler_raises_for_non_llms_txt(self):
        mock_repo = MagicMock()
        mock_repo.exists.return_value = False

        handler = URLHandler(mock_repo)

        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("https://example.com/docs")
            f.flush()
            temp_path = f.name

        try:
            with self.assertRaises(NotImplementedError):
                handler.process(temp_path, "my_table")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_url_handler_fetches_and_indexes_links(self):
        mock_repo = MagicMock()
        mock_repo.exists.return_value = False

        handler = URLHandler(mock_repo)

        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("https://example.com/llms.txt\n")
            f.flush()
            temp_path = f.name

        llms_txt_content = """# My Project
> A test project

## Documentation
- [Overview](/docs/overview.md): High level overview
- [Guide](https://example.com/guide.md): Quickstart guide
"""

        overview_md = (
            "This is the overview page. It provides details on how the system works."
        )
        guide_md = "This is the guide page. Step 1: Install. Step 2: Run."

        def fake_get(url, timeout=10):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if url == "https://example.com/llms.txt":
                resp.text = llms_txt_content
            elif url == "https://example.com/docs/overview.md":
                resp.text = overview_md
            elif url == "https://example.com/guide.md":
                resp.text = guide_md
            else:
                raise requests.RequestException(f"Not found: {url}")
            return resp

        try:
            with patch(
                "local_mcp.file.handler.requests.get", side_effect=fake_get
            ) as mock_get:
                handler.process(temp_path, "my_table")

                self.assertEqual(mock_get.call_count, 3)
                mock_repo.save.assert_called_once()
                _, kwargs = mock_repo.save.call_args
                self.assertEqual(kwargs["table_name"], "my_table")
                self.assertEqual(kwargs["file_path"], temp_path)
                self.assertEqual(len(kwargs["chunks"]), 2)
                self.assertEqual(kwargs["page_numbers"], [1, 2])
                self.assertIn(
                    "[Overview](https://example.com/docs/overview.md)",
                    kwargs["chunks"][0],
                )
                self.assertIn("This is the overview page.", kwargs["chunks"][0])
                self.assertIn(
                    "[Guide](https://example.com/guide.md)", kwargs["chunks"][1]
                )
                self.assertIn("This is the guide page.", kwargs["chunks"][1])
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
