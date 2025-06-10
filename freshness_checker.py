#!/usr/bin/env python3
"""
Indeed Package Freshness Checker

This script helps Indeed track the freshness of packages during migration
from Nexus to Cloudsmith by comparing upload dates from both sources and determining
the correct freshness date for each package group.
"""

import os
import sys
import json
import argparse
import logging
import re
from datetime import datetime
import requests
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("freshness-checker")

# Load environment variables
load_dotenv()

# Environment variables
CLOUDSMITH_BASE_URL = os.getenv("CLOUDSMITH_BASE_URL", "https://api.cloudsmith.io")
CLOUDSMITH_API_KEY = os.getenv("CLOUDSMITH_API_KEY")
CLOUDSMITH_ORG = os.getenv("CLOUDSMITH_ORG", "indeed")
CLOUDSMITH_REPO = os.getenv("CLOUDSMITH_REPO", "maven-repo")

# Constants
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

class NexusClient:
    """
    Client for interacting with Nexus repositories.
    For testing purposes, this mocks the Nexus API responses.
    """
    def list_package_groups(self, format_type: str) -> List[Dict[str, str]]:
        """
        List all package groups (versionless packages) from Nexus.
        
        Args:
            format_type: Package format (maven, npm, or python)
        
        Returns:
            List of dictionaries with package identifiers.
        """
        fixtures_file = os.path.join(FIXTURES_DIR, format_type, "packages.json")
        try:
            with open(fixtures_file, 'r') as f:
                fixture_data = json.load(f)
            logger.info(f"Loaded {len(fixture_data)} {format_type} packages from fixtures")
        except FileNotFoundError:
            logger.error(f"Fixtures file not found: {fixtures_file}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse fixtures file: {fixtures_file}")
            return []

        if format_type == "maven":
            return fixture_data
        elif format_type in ["npm", "python"]:
            return [{"name": pkg["name"]} for pkg in fixture_data]
        else:
            logger.warning(f"Unsupported format type: {format_type}")
            return []

    def get_last_updated_date(self, identifier: Dict[str, str], format_type: str) -> str:
        """
        Get the lastUpdated date for a specific package group.
        
        Args:
            identifier: Package identifier (groupId:artifactId for Maven, name for npm/python)
            format_type: Package format (maven, npm, or python)
        
        Returns:
            lastUpdated date string in format YYYYMMDDHHMMSS
        """
        fixtures_file = os.path.join(FIXTURES_DIR, format_type, "packages.json")
        try:
            with open(fixtures_file, 'r') as f:
                fixture_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Fixtures file not found: {fixtures_file}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Failed to parse fixtures file: {fixtures_file}")
            return None

        if format_type == "maven":
            group_id = identifier.get("groupId")
            artifact_id = identifier.get("artifactId")
            for pkg in fixture_data:
                if pkg.get("groupId") == group_id and pkg.get("artifactId") == artifact_id:
                    return pkg.get("lastUpdated")
        elif format_type in ["npm", "python"]:
            name = identifier.get("name")
            for pkg in fixture_data:
                if pkg.get("name") == name:
                    return pkg.get("lastUpdated")
        else:
            logger.warning(f"Unsupported format type: {format_type}")
            return None

        logger.warning(f"Package not found in Nexus fixtures")
        return None


class CloudsmithClient:
    """
    Client for interacting with Cloudsmith API.
    """
    
    def __init__(self, base_url: str = CLOUDSMITH_BASE_URL, api_key: str = CLOUDSMITH_API_KEY, org: str = CLOUDSMITH_ORG, repo: str = CLOUDSMITH_REPO, mock: bool = False):
        """
        Initialize the Cloudsmith client.
        
        Args:
            base_url: Base URL for Cloudsmith API
            api_key: Cloudsmith API key
            org: Organization name
            repo: Repository name
            mock: Whether to use mock data instead of real API
        """
        self.base_url = base_url
        self.api_key = api_key
        self.org = org
        self.repo = repo
        self.mock = mock

    def list_package_groups(self, format_type: str, ignore_tag: str | None = None) -> List[Dict]:
        """
        Get all package groups from Cloudsmith.
        
        Args:
            format_type: Package format (maven, npm, or python)
        
        Returns:
            List of package groups
        """
        endpoint = f"/packages/{self.org}/{self.repo}/groups/"
        params = {
            "page": 1,
            "page_size": 100,
            "query": f"format:{format_type} AND NOT tag:{ignore_tag}",
            "sort": "-last_push"
        }

        all_groups = []
        while True:
            response = self._make_request(endpoint, params)
            results = response.get("results", [])
            if not results:
                break
            all_groups.extend(results)
            if len(results) < params.get("page_size", 100):
                break
            params["page"] += 1

        return all_groups

    def get_last_updated_date(self, identifier: Dict[str, str], format_type: str, ignore_tag: str) -> str:
        """
        Get the last updated date for a package group.
        
        Args:
            identifier: Package identifier (groupId:artifactId for Maven, name for npm/python)
            format_type: Package format (maven, npm, or python)
            ignore_tag: Tag to ignore when fetching the last updated date

        Returns:
            Last updated date as YYYYMMDDHHMMSS string
        """
        if format_type == "maven":
            group_id = identifier.get("groupId")
            artifact_id = identifier.get("artifactId")
            pakage_query = f'maven_group_id:^{group_id}$ AND name:^{artifact_id}$'
        else:
            name = identifier.get("name")
            pakage_query = f'name:^{name}$'

        endpoint = f"/packages/{self.org}/{self.repo}/groups/"
        params = {
            "query": f"format:{format_type} AND {pakage_query} AND NOT tag:{ignore_tag}",
        }

        response = self._make_request(endpoint, params)
        results = response.get("results", [])
        assert len(results) <= 1, f"Expected at most one package for query: {params['query']}"
        if results:
            last_push = results[0].get("last_push")
            return datetime.fromisoformat(last_push).strftime("%Y%m%d%H%M%S")
        return None

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Cloudsmith API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as a dictionary
        """
        if self.mock:
            logger.info(f"Using mock data for Cloudsmith API request to {endpoint}")
            return self.fixture_data
        
        url = f"{self.base_url}/v1{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def format_date_for_display(date_str: str) -> str:
    """
    Format date string for display.
    
    Args:
        date_str: Date in format YYYYMMDDHHMMSS
        
    Returns:
        Formatted date string as YYYY-MM-DD HH:MM:SS
    """
    if not date_str:
        return "N/A"
    
    try:
        # Check if the string matches the expected pattern (14 digits)
        if not re.match(r'^\d{14}$', date_str):
            return date_str
            
        year = date_str[0:4]
        month = date_str[4:6]
        day = date_str[6:8]
        hour = date_str[8:10]
        minute = date_str[10:12]
        second = date_str[12:14]
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"
    except (IndexError, ValueError):
        return date_str


def compare_dates(nexus_date: str, cloudsmith_date: str) -> Tuple[str, str]:
    """
    Compare two dates and return the older one along with the source.
    
    Args:
        nexus_date: Date from Nexus in YYYYMMDDHHMMSS format
        cloudsmith_date: Date from Cloudsmith in YYYYMMDDHHMMSS format
        
    Returns:
        Tuple of (older_date, source)
    """
    if not nexus_date and not cloudsmith_date:
        return None, "unknown"
    
    if not nexus_date:
        return cloudsmith_date, "cloudsmith"
    
    if not cloudsmith_date:
        return nexus_date, "nexus"
    
    # Compare dates and return the older one (larger value)
    if int(nexus_date) > int(cloudsmith_date):
        return nexus_date, "nexus"
    else:
        return cloudsmith_date, "cloudsmith"


def main():
    """Main function to run the freshness check script."""
    parser = argparse.ArgumentParser(description='Check package freshness during migration')
    parser.add_argument('--format', choices=['maven', 'npm', 'python', 'all'], default='maven',
                      help='Package format to check (default: maven)')
    parser.add_argument('--upstream-tag-to-exclude', default='upstream',
                      help='Tag to use for excluding packages from Cloudsmith fetch')
    args = parser.parse_args()
    
    formats_to_check = [args.format] if args.format != 'all' else ['maven', 'npm', 'python']
    results = []

    nexus_client = NexusClient()
    cloudsmith_client = CloudsmithClient()

    for format_type in formats_to_check:
        logger.info(f"Starting freshness check for {format_type} packages")
        
        # Step 1: Get all versionless packages from Nexus
        nexus_packages = []
        logger.info(f"Step 1: Fetching all versionless {format_type} packages from Nexus")
        nexus_packages = nexus_client.list_package_groups(format_type=format_type)
        logger.info(f"Found {len(nexus_packages)} {format_type} packages in Nexus")
        
        # Get Latest updatedAt for each package
        for pkg in nexus_packages:
            # Step 2: Get lastUpdated date from Nexus for each package
            pkg_name = pkg.get("name") if format_type != "maven" else f"{pkg.get('groupId')}:{pkg.get('artifactId')}"
            logger.info(f"Step 2: Getting lastUpdated date from Nexus for {pkg_name}")
            nexus_date = nexus_client.get_last_updated_date(pkg, format_type=format_type)

            logger.info(f"Nexus date for {pkg_name}: {format_date_for_display(nexus_date)}")

            logger.info(f"Step 3: Querying Cloudsmith Package Group API for {pkg_name}")
            cloudsmith_date = cloudsmith_client.get_last_updated_date(pkg, format_type=format_type, ignore_tag=args.upstream_tag_to_exclude)

            logger.info(f"Cloudsmith date for {pkg_name}: {format_date_for_display(cloudsmith_date)}")

            # Step 4: Pick older of the 2 dates
            logger.info("Step 4: Comparing dates and selecting the older one")
            freshness_date, date_source = compare_dates(nexus_date, cloudsmith_date)            
            
            logger.info(f"Freshness date for {pkg_name}: {format_date_for_display(freshness_date)} (from {date_source})")
            
            # Store the results
            results.append({
                'format': format_type,
                'name': pkg_name,
                'nexus_date': nexus_date,
                'cloudsmith_date': cloudsmith_date,
                'freshness_date': freshness_date,
                'source': date_source
            })
            
            # Print details
            logger.info(f"Package: {pkg_name}")
            logger.info(f"  Nexus date: {format_date_for_display(nexus_date)}")
            logger.info(f"  Cloudsmith date: {format_date_for_display(cloudsmith_date)}")
            logger.info(f"  Freshness date: {format_date_for_display(freshness_date)} (from {date_source})")
            logger.info("")
        
    # Step 5: Log results
    logger.info("Step 5: Logging results summary")
    
    # Print summary
    logger.info("")
    logger.info("-" * 40)
    logger.info("Summary:")
    logger.info("-" * 40)
    logger.info(f"Total packages: {len(results)}")
    logger.info(f"Using Nexus date: {sum(1 for r in results if r['source'] == 'nexus')}")
    logger.info(f"Using Cloudsmith date: {sum(1 for r in results if r['source'] == 'cloudsmith')}")
    logger.info(f"Missing date: {sum(1 for r in results if r['source'] == 'unknown')}")


if __name__ == "__main__":
    main()
