#!/usr/bin/env python3
"""
Example usage of the Indeed Package Freshness Checker.

This script demonstrates how to use the freshness checker in a real-world scenario.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to import freshness_checker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from freshness_checker import NexusClient, CloudsmithClient, format_date_for_display

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("freshness-example")

# Load environment variables
load_dotenv()

def main():
    """
    Example of how to use the freshness checker programmatically.
    """
    print("=== Indeed Package Freshness Checker Example ===\n")
    
    # Initialize clients
    nexus_client = NexusClient()
    cloudsmith_client = CloudsmithClient()
    
    # Define a list of package groups to check
    package_groups_to_check = [
        {"groupId": "com.indeed", "artifactId": "util-core"},
        {"groupId": "org.example", "artifactId": "test-lib"}
    ]
    
    # Check each package group
    for pkg in package_groups_to_check:
        group_id = pkg['groupId']
        artifact_id = pkg['artifactId']
        package_key = f"{group_id}:{artifact_id}"
        
        print(f"Checking package: {package_key}")
        
        # Get Nexus date
        try:
            nexus_date = nexus_client.get_last_updated_date(group_id, artifact_id)
            print(f"  Nexus last updated: {format_date_for_display(nexus_date)}")
        except Exception as e:
            logger.error(f"Failed to get Nexus date: {e}")
            nexus_date = None
            print(f"  Nexus last updated: Error retrieving date")
        
        # Get Cloudsmith date (excluding packages with nexus-upstream tag)
        try:
            cloudsmith_date = cloudsmith_client.get_last_updated_date(
                group_id, artifact_id, exclude_tags=["nexus-upstream"]
            )
            print(f"  Cloudsmith last updated: {format_date_for_display(cloudsmith_date)}")
        except Exception as e:
            logger.error(f"Failed to get Cloudsmith date: {e}")
            cloudsmith_date = None
            print(f"  Cloudsmith last updated: Error retrieving date")
        
        # Determine the freshness date (take the later of the two)
        fresh_date = None
        date_source = None
        
        if nexus_date and cloudsmith_date:
            if nexus_date > cloudsmith_date:
                fresh_date = nexus_date
                date_source = "Nexus"
            else:
                fresh_date = cloudsmith_date
                date_source = "Cloudsmith"
        elif nexus_date:
            fresh_date = nexus_date
            date_source = "Nexus"
        elif cloudsmith_date:
            fresh_date = cloudsmith_date
            date_source = "Cloudsmith"
        else:
            fresh_date = None
            date_source = "Unknown"
        
        print(f"  Final freshness date: {format_date_for_display(fresh_date)} (from {date_source})")
        print()


if __name__ == "__main__":
    main()
