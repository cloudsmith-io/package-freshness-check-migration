#!/usr/bin/env python3
"""
Maven-specific example for the Indeed Package Freshness Checker.

This script demonstrates how the freshness checker works specifically
for Maven packages, including handling of maven-metadata.xml.
"""

import os
import sys
import logging
import xml.dom.minidom
import xmltodict
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
logger = logging.getLogger("maven-example")

# Load environment variables
load_dotenv()

def print_maven_metadata_example():
    """
    Print an example of maven-metadata.xml and how it's used.
    """
    print("\n=== Maven Metadata Example ===\n")
    
    # Create a sample maven-metadata.xml content
    metadata_xml = """
    <metadata>
        <groupId>com.indeed</groupId>
        <artifactId>util-core</artifactId>
        <versioning>
            <latest>2.1.1</latest>
            <release>2.1.1</release>
            <versions>
                <version>1.0.0</version>
                <version>2.0.0</version>
                <version>2.1.0</version>
                <version>2.1.1</version>
            </versions>
            <lastUpdated>20250326120000</lastUpdated>
        </versioning>
    </metadata>
    """
    
    # Pretty-print the XML
    dom = xml.dom.minidom.parseString(metadata_xml)
    pretty_xml = dom.toprettyxml(indent="  ")
    print("Maven metadata.xml example:")
    print(pretty_xml)
    
    # Parse the XML to dict
    metadata_dict = xmltodict.parse(metadata_xml)
    
    # Extract relevant information
    group_id = metadata_dict["metadata"]["groupId"]
    artifact_id = metadata_dict["metadata"]["artifactId"]
    latest_version = metadata_dict["metadata"]["versioning"]["latest"]
    last_updated = metadata_dict["metadata"]["versioning"]["lastUpdated"]
    
    print(f"Group ID: {group_id}")
    print(f"Artifact ID: {artifact_id}")
    print(f"Latest Version: {latest_version}")
    print(f"Last Updated: {format_date_for_display(last_updated)}")
    
    print("\nThis is how Indeed currently determines package freshness.")
    print("The 'lastUpdated' field in the maven-metadata.xml file is crucial for freshness tracking.")
    print("During migration to Cloudsmith, this date needs to be preserved correctly.")

def show_maven_comparison():
    """
    Show a comparison between Nexus and Cloudsmith Maven packages.
    """
    print("\n=== Maven Package Comparison: Nexus vs Cloudsmith ===\n")
    
    print("Scenario 3: Upstream Package cached in Cloudsmith")
    print("------------------------------------------------")
    print("In this scenario, the package exists in Nexus and has been cached in Cloudsmith.")
    print("The expected behavior is that we should use the Nexus date for freshness calculation.")
    print()
    
    # Mock data
    package_key = "com.indeed:util-core"
    nexus_date = "20250326120000"
    cloudsmith_date = "20250401120000"  # more recent due to caching
    
    # Format dates for display
    nexus_display_date = format_date_for_display(nexus_date)
    cloudsmith_display_date = format_date_for_display(cloudsmith_date)
    
    print(f"Package: {package_key}")
    print(f"  Nexus lastUpdated: {nexus_display_date}")
    print(f"  Cloudsmith uploadedAt (for cached package): {cloudsmith_display_date}")
    print()
    
    print("Problem:")
    print("  The Cloudsmith date is more recent than the Nexus date due to caching,")
    print("  which would incorrectly report the package as fresher than it is.")
    print()
    
    print("Solution:")
    print("  1. Tag packages cached from Nexus with 'nexus-upstream' tag")
    print("  2. Use the '--exclude-tag nexus-upstream' option when checking freshness")
    print("  3. If no Cloudsmith date is available (all packages are tagged), use the Nexus date")
    print()
    
    # Simulate solution
    print("After applying the solution:")
    print(f"  Nexus lastUpdated: {nexus_display_date}")
    print(f"  Cloudsmith uploadedAt (excluding tagged packages): N/A (all packages are from Nexus)")
    print(f"  Final freshness date: {nexus_display_date} (from Nexus)")

def main():
    """
    Main function demonstrating Maven-specific freshness checking.
    """
    print("=== Maven Package Freshness Example ===\n")
    print("This example is running...")
    
    # Show an example of maven-metadata.xml
    print_maven_metadata_example()
    
    # Show a comparison between Nexus and Cloudsmith
    show_maven_comparison()
    
    # Initialize clients
    print("\n=== Real Package Check ===\n")
    
    nexus_client = NexusClient()
    cloudsmith_client = CloudsmithClient()
    
    # Check a specific package
    group_id = "com.indeed"
    artifact_id = "util-core"
    package_key = f"{group_id}:{artifact_id}"
    
    print(f"Checking Maven package: {package_key}")
    
    # Get Nexus date
    try:
        nexus_metadata = nexus_client.get_maven_metadata(group_id, artifact_id)
        nexus_date = nexus_metadata["metadata"]["versioning"]["lastUpdated"]
        print(f"  Nexus maven-metadata.xml:")
        print(f"    Latest version: {nexus_metadata['metadata']['versioning']['latest']}")
        print(f"    Last updated: {format_date_for_display(nexus_date)}")
    except Exception as e:
        logger.error(f"Failed to get Nexus metadata: {e}")
        nexus_date = None
        print("  Nexus maven-metadata.xml: Error retrieving data")
    
    # Get Cloudsmith date
    try:
        cloudsmith_date = cloudsmith_client.get_last_updated_date(
            group_id, artifact_id, exclude_tags=["nexus-upstream"]
        )
        print(f"  Cloudsmith last updated: {format_date_for_display(cloudsmith_date)}")
    except Exception as e:
        logger.error(f"Failed to get Cloudsmith date: {e}")
        cloudsmith_date = None
        print("  Cloudsmith last updated: Error retrieving data")
    
    # Determine the freshness date
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


if __name__ == "__main__":
    main()
