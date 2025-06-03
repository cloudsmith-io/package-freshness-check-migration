#!/usr/bin/env python3
"""
Tests for the Indeed Package Freshness Checker.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from freshness_checker import NexusClient, CloudsmithClient, format_date_for_display


class TestFormatDateForDisplay(unittest.TestCase):
    """Test the date formatting function."""
    
    def test_format_valid_date(self):
        """Test formatting a valid date string."""
        result = format_date_for_display("20250326120000")
        self.assertEqual(result, "2025-03-26 12:00:00")
    
    def test_format_invalid_date(self):
        """Test formatting an invalid date string."""
        result = format_date_for_display("invalid")
        self.assertEqual(result, "invalid")
    
    def test_format_none_date(self):
        """Test formatting a None date."""
        result = format_date_for_display(None)
        self.assertEqual(result, "N/A")


class TestNexusClient(unittest.TestCase):
    """Test the NexusClient class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.client = NexusClient()
    
    def test_list_package_groups(self):
        """Test listing package groups."""
        groups = self.client.list_package_groups()
        self.assertIsInstance(groups, list)
        self.assertTrue(len(groups) > 0)
        self.assertIn("groupId", groups[0])
        self.assertIn("artifactId", groups[0])
    
    def test_get_maven_metadata(self):
        """Test getting maven metadata."""
        metadata = self.client.get_maven_metadata("com.indeed", "util-core")
        self.assertIsInstance(metadata, dict)
        self.assertIn("metadata", metadata)
        self.assertEqual(metadata["metadata"]["groupId"], "com.indeed")
        self.assertEqual(metadata["metadata"]["artifactId"], "util-core")
    
    def test_get_last_updated_date(self):
        """Test getting the last updated date."""
        date = self.client.get_last_updated_date("com.indeed", "util-core")
        self.assertEqual(date, "20250325120000")


class TestCloudsmithClient(unittest.TestCase):
    """Test the CloudsmithClient class."""
    
    @patch('freshness_checker.requests.get')
    def test_list_package_groups(self, mock_get):
        """Test listing package groups from Cloudsmith."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "format": "maven",
                "identifiers": {
                    "maven_group_id": "com.indeed",
                    "maven_artifact_id": "util-core"
                }
            },
            {
                "format": "maven",
                "identifiers": {
                    "maven_group_id": "com.indeed",
                    "maven_artifact_id": "util-io"
                }
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = CloudsmithClient(api_key="test_key")
        groups = client.list_package_groups()
        
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["groupId"], "com.indeed")
        self.assertEqual(groups[0]["artifactId"], "util-core")
    
    @patch('freshness_checker.requests.get')
    def test_get_last_updated_date(self, mock_get):
        """Test getting the last updated date from Cloudsmith."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "uploaded_at": "2025-03-26T12:00:00Z",
                "tags": []
            },
            {
                "uploaded_at": "2025-03-25T12:00:00Z",
                "tags": ["nexus-upstream"]
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = CloudsmithClient(api_key="test_key")
        date = client.get_last_updated_date("com.indeed", "util-core")
        
        self.assertEqual(date, "20250326120000")
    
    @patch('freshness_checker.requests.get')
    def test_get_last_updated_date_with_exclusion(self, mock_get):
        """Test getting the last updated date with tag exclusion."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "uploaded_at": "2025-03-26T12:00:00Z",
                "tags": ["nexus-upstream"]
            },
            {
                "uploaded_at": "2025-03-25T12:00:00Z",
                "tags": []
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = CloudsmithClient(api_key="test_key")
        date = client.get_last_updated_date("com.indeed", "util-core", exclude_tags=["nexus-upstream"])
        
        # Should skip the first one due to tag and use the second one
        self.assertEqual(date, "20250325120000")


if __name__ == "__main__":
    unittest.main()
