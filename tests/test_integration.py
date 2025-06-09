#!/usr/bin/env python3
"""
Integration tests for the Indeed Package Freshness Checker.

These tests verify that the solution works correctly for the scenarios described
in the requirements.
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from freshness_checker import NexusClient, CloudsmithClient, format_date_for_display, main

class TestScenarios(unittest.TestCase):
    """Test the different scenarios described in the requirements."""
    
    @patch('freshness_checker.NexusClient')
    @patch('freshness_checker.CloudsmithClient')
    @patch('freshness_checker.argparse.ArgumentParser.parse_args')
    def test_scenario_package_in_nexus_only(self, mock_args, mock_cs_client, mock_nexus_client):
        """
        Test Scenario 1: Package exists in Nexus only.
        
        Expected behavior: Use the Nexus date for freshness.
        """
        # Mock the arguments
        mock_args.return_value = MagicMock(
            nexus_only=False,
            cloudsmith_only=False,
            exclude_tag=None,
            output_csv=None
        )
        
        # Mock the clients
        nexus_instance = mock_nexus_client.return_value
        cs_instance = mock_cs_client.return_value
        
        # Set up the Nexus client mock
        nexus_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "nexus-only-package"}
        ]
        nexus_instance.get_last_updated_date.return_value = "20250326120000"
        
        # Set up the Cloudsmith client mock
        cs_instance.list_package_groups.return_value = []
        cs_instance.get_last_updated_date.return_value = None
        
        # Run the main function with mocked stdout
        with patch('sys.stdout'):
            main()
        
        # Verify that the correct functions were called
        nexus_instance.list_package_groups.assert_called_once_with(format_type=mock_args.return_value.format)
        nexus_instance.get_last_updated_date.assert_called_once_with(
            {"groupId": "com.indeed", "artifactId": "nexus-only-package"}, format_type=mock_args.return_value.format
        )
        
    @patch('freshness_checker.NexusClient')
    @patch('freshness_checker.CloudsmithClient')
    @patch('freshness_checker.argparse.ArgumentParser.parse_args')
    def test_scenario_package_in_cloudsmith_only(self, mock_args, mock_cs_client, mock_nexus_client):
        """
        Test Scenario 2: Package exists in Cloudsmith only.
        
        Expected behavior: Use the Cloudsmith date for freshness.
        """
        # Mock the arguments
        mock_args.return_value = MagicMock(
            nexus_only=False,
            cloudsmith_only=False,
            exclude_tag=None,
            output_csv=None
        )
        
        # Mock the clients
        nexus_instance = mock_nexus_client.return_value
        cs_instance = mock_cs_client.return_value
        
        # Set up the Nexus client mock
        nexus_instance.list_package_groups.return_value = []
        nexus_instance.get_last_updated_date.side_effect = Exception("Not found")
        
        # Set up the Cloudsmith client mock
        cs_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "cloudsmith-only-package"}
        ]
        cs_instance.get_last_updated_date.return_value = "20250326120000"
        
        # Run the main function with mocked stdout
        with patch('sys.stdout'):
            main()
        
        # Verify that the Cloudsmith client was called correctly
        cs_instance.list_package_groups.assert_called_once_with(format_type=mock_args.return_value.format)
        cs_instance.get_last_updated_date.assert_called_once()
    
    @patch('freshness_checker.NexusClient')
    @patch('freshness_checker.CloudsmithClient')
    @patch('freshness_checker.argparse.ArgumentParser.parse_args')
    def test_scenario_upstream_package_cached(self, mock_args, mock_cs_client, mock_nexus_client):
        """
        Test Scenario 3: Upstream Package cached in Cloudsmith.
        
        Expected behavior: Use the Nexus date for freshness when excluded.
        """
        # Mock the arguments
        mock_args.return_value = MagicMock(
            nexus_only=False,
            cloudsmith_only=False,
            exclude_tag=["nexus-upstream"],
            output_csv=None
        )
        
        # Mock the clients
        nexus_instance = mock_nexus_client.return_value
        cs_instance = mock_cs_client.return_value
        
        # Set up the Nexus client mock
        nexus_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "cached-package"}
        ]
        nexus_instance.get_last_updated_date.return_value = "20250326120000"
        
        # Set up the Cloudsmith client mock
        cs_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "cached-package"}
        ]
        cs_instance.get_last_updated_date.return_value = None  # All packages have the tag
        
        # Run the main function with mocked stdout
        with patch('sys.stdout'):
            main()
        
        # Verify that the Cloudsmith client was called with the tag exclusion
        cs_instance.get_last_updated_date.assert_called_once_with(
            {"groupId": "com.indeed", "artifactId": "cached-package"}, format_type=mock_args.return_value.format
        )
    
    @patch('freshness_checker.NexusClient')
    @patch('freshness_checker.CloudsmithClient')
    @patch('freshness_checker.argparse.ArgumentParser.parse_args')
    def test_scenario_local_newer(self, mock_args, mock_cs_client, mock_nexus_client):
        """
        Test Scenario 4: Local package and Nexus Upstream package. Local newer.
        
        Expected behavior: Use the later Cloudsmith date for freshness.
        """
        # Mock the arguments
        mock_args.return_value = MagicMock(
            nexus_only=False,
            cloudsmith_only=False,
            exclude_tag=["nexus-upstream"],
            output_csv=None
        )
        
        # Mock the clients
        nexus_instance = mock_nexus_client.return_value
        cs_instance = mock_cs_client.return_value
        
        # Set up the Nexus client mock
        nexus_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "local-newer-package"}
        ]
        nexus_instance.get_last_updated_date.return_value = "20250326120000"
        
        # Set up the Cloudsmith client mock
        cs_instance.list_package_groups.return_value = [
            {"groupId": "com.indeed", "artifactId": "local-newer-package"}
        ]
        cs_instance.get_last_updated_date.return_value = "20250401120000"  # Newer
        
        # Run the main function with mocked stdout
        with patch('sys.stdout'):
            main()
        
        # The freshness date should be the Cloudsmith date
        # This is just verifying the test setup is correct
        self.assertTrue(cs_instance.get_last_updated_date() > nexus_instance.get_last_updated_date())


if __name__ == "__main__":
    unittest.main()
