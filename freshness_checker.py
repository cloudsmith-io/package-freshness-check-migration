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
NEXUS_BASE_URL = os.getenv("NEXUS_BASE_URL", "https://nexus.corp.indeed.com")
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
    
    def __init__(self, base_url: str = NEXUS_BASE_URL, format_type: str = "maven"):
        """
        Initialize the Nexus client.
        
        Args:
            base_url: Base URL for Nexus
            format_type: Package format (maven, npm, or python)
        """
        self.base_url = base_url
        self.format_type = format_type
        self.fixtures_file = os.path.join(FIXTURES_DIR, format_type, "packages.json")
        
        # Load fixture data
        try:
            with open(self.fixtures_file, 'r') as f:
                self.fixture_data = json.load(f)
            logger.info(f"Loaded {len(self.fixture_data)} {format_type} packages from fixtures")
        except FileNotFoundError:
            logger.error(f"Fixtures file not found: {self.fixtures_file}")
            self.fixture_data = []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse fixtures file: {self.fixtures_file}")
            self.fixture_data = []

    def list_package_groups(self) -> List[Dict[str, str]]:
        """
        List all package groups (versionless packages) from Nexus.
        
        Returns:
            List of dictionaries with package identifiers.
        """
        logger.info(f"Fetching {self.format_type} package groups from Nexus")
        
        if self.format_type == "maven":
            # Return the data as-is for Maven
            return self.fixture_data
        elif self.format_type == "npm":
            # Convert npm fixtures to the standard format
            return [{"name": pkg["name"]} for pkg in self.fixture_data]
        elif self.format_type == "python":
            # Convert python fixtures to the standard format
            return [{"name": pkg["name"]} for pkg in self.fixture_data]
        else:
            logger.warning(f"Unsupported format type: {self.format_type}")
            return []
    
    def get_last_updated_date(self, identifier: Dict[str, str]) -> str:
        """
        Get the lastUpdated date for a specific package group.
        
        Args:
            identifier: Package identifier (groupId:artifactId for Maven, name for npm/python)
            
        Returns:
            lastUpdated date string in format YYYYMMDDHHMMSS
        """
        if self.format_type == "maven":
            group_id = identifier.get("groupId")
            artifact_id = identifier.get("artifactId")
            package_key = f"{group_id}:{artifact_id}"
            logger.info(f"Fetching lastUpdated date for Maven package {package_key} from Nexus")
            
            # Find the package in the fixture data
            for pkg in self.fixture_data:
                if pkg.get("groupId") == group_id and pkg.get("artifactId") == artifact_id:
                    logger.info(f"Found package {package_key} in Nexus with lastUpdated {pkg.get('lastUpdated')}")
                    return pkg.get("lastUpdated")
                    
            logger.warning(f"Package {package_key} not found in Nexus fixtures")
            return None
        else:
            # For npm and python
            name = identifier.get("name")
            logger.info(f"Fetching lastUpdated date for {self.format_type} package {name} from Nexus")
            
            # Find the package in the fixture data
            for pkg in self.fixture_data:
                if pkg.get("name") == name:
                    logger.info(f"Found package {name} in Nexus with lastUpdated {pkg.get('lastUpdated')}")
                    return pkg.get("lastUpdated")
                    
            logger.warning(f"Package {name} not found in Nexus fixtures")
            return None


class CloudsmithClient:
    """
    Client for interacting with Cloudsmith API.
    """
    
    def __init__(
        self, 
        base_url: str = CLOUDSMITH_BASE_URL,
        api_key: str = CLOUDSMITH_API_KEY,
        org: str = CLOUDSMITH_ORG,
        repo: str = CLOUDSMITH_REPO,
        format_type: str = "maven",
        mock: bool = False
    ):
        """
        Initialize the Cloudsmith client.
        
        Args:
            base_url: Base URL for Cloudsmith API
            api_key: Cloudsmith API key
            org: Organization name
            repo: Repository name
            format_type: Package format (maven, npm, or python)
            mock: Whether to use mock data instead of real API
        """
        self.base_url = base_url
        self.api_key = api_key
        self.org = org
        self.repo = repo
        self.format_type = format_type
        self.mock = mock
        
        if not self.api_key and not self.mock:
            logger.warning("CLOUDSMITH_API_KEY not set and mock mode is disabled. API calls may fail.")
        
        if self.mock:
            self.fixtures_file = os.path.join(FIXTURES_DIR, "cloudsmith", f"{format_type}_groups.json")
            try:
                with open(self.fixtures_file, 'r') as f:
                    self.fixture_data = json.load(f)
                logger.info(f"Loaded {self.format_type} package groups from Cloudsmith fixtures")
            except FileNotFoundError:
                logger.error(f"Cloudsmith fixtures file not found: {self.fixtures_file}")
                self.fixture_data = {"results": []}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Cloudsmith fixtures file: {self.fixtures_file}")
                self.fixture_data = {"results": []}
    
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
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            logger.info(f"Making request to Cloudsmith API: {url}")
            response = requests.get(url, headers=headers, params=params)
            
            # Handle 404 specifically for better user experience
            if response.status_code == 404:
                logger.warning(f"Resource not found at {url}")
                return {"results": []}
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Cloudsmith API: {e}")
            return {"results": []}
    
    def get_package_groups(self) -> List[Dict]:
        """
        Get all package groups from Cloudsmith.
        
        Returns:
            List of package groups
        """
        endpoint = f"/packages/{self.org}/{self.repo}/groups/"
        params = {
            "page": 1,
            "page_size": 100,
            "format": self.format_type,
            "query": "NOT tag:upstream",  # Exclude packages with upstream tag
            "sort": "-last_push_at"  # Sort by last push date descending
        }
        
        logger.info(f"Fetching package groups from Cloudsmith for format {self.format_type}")
        
        all_groups = []
        while True:
            response = self._make_request(endpoint, params)
            
            results = response.get("results", [])
            if not results:
                break
                
            all_groups.extend(results)
            
            # Check if we've reached the last page
            if len(results) < params.get("page_size", 100):
                break
                
            params["page"] += 1
        
        logger.info(f"Found {len(all_groups)} package groups in Cloudsmith")
        return all_groups
    
    def get_last_updated_date(self, identifier: Dict[str, str]) -> str:
        """
        Get the last updated date for a package group.
        
        Args:
            identifier: Package identifier (groupId:artifactId for Maven, name for npm/python)
            
        Returns:
            Last updated date as YYYYMMDDHHMMSS string
        """
        groups = self.get_package_groups()
        
        # Get the identifier based on package format
        if self.format_type == "maven":
            group_id = identifier.get("groupId")
            artifact_id = identifier.get("artifactId")
            package_key = f"{group_id}:{artifact_id}"
            
            # Find the package in the groups
            for group in groups:
                if group.get("identifier") == package_key:
                    last_push_at = group.get("last_push_at")
                    logger.info(f"Found package {package_key} in Cloudsmith with last_push_at {last_push_at}")
                    
                    # Convert ISO format to YYYYMMDDHHMMSS
                    if last_push_at:
                        dt = datetime.fromisoformat(last_push_at.replace('Z', '+00:00'))
                        return dt.strftime("%Y%m%d%H%M%S")
            
            logger.warning(f"Package {package_key} not found in Cloudsmith")
            return None
        else:
            # For npm and python
            name = identifier.get("name")
            
            # Find the package in the groups
            for group in groups:
                if group.get("identifier") == name:
                    last_push_at = group.get("last_push_at")
                    logger.info(f"Found {self.format_type} package {name} in Cloudsmith with last_push_at {last_push_at}")
                    
                    # Convert ISO format to YYYYMMDDHHMMSS
                    if last_push_at:
                        dt = datetime.fromisoformat(last_push_at.replace('Z', '+00:00'))
                        return dt.strftime("%Y%m%d%H%M%S")
            
            logger.warning(f"{self.format_type.capitalize()} package {name} not found in Cloudsmith")
            return None


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
    
    # Compare dates and return the older one (smaller value)
    if int(nexus_date) <= int(cloudsmith_date):
        return nexus_date, "nexus"
    else:
        return cloudsmith_date, "cloudsmith"


def main():
    """Main function to run the freshness check script."""
    parser = argparse.ArgumentParser(description='Check package freshness during migration')
    parser.add_argument('--format', choices=['maven', 'npm', 'python', 'all'], default='maven',
                      help='Package format to check (default: maven)')
    parser.add_argument('--nexus-only', action='store_true', help='Check only Nexus packages')
    parser.add_argument('--cloudsmith-only', action='store_true', help='Check only Cloudsmith packages')
    parser.add_argument('--mock', action='store_true', help='Use mock data for Cloudsmith API')
    parser.add_argument('--output-csv', help='Output results to CSV file')
    args = parser.parse_args()
    
    formats_to_check = [args.format] if args.format != 'all' else ['maven', 'npm', 'python']
    results = []
    
    for format_type in formats_to_check:
        logger.info(f"Starting freshness check for {format_type} packages")
        
        # Initialize clients
        nexus_client = NexusClient(format_type=format_type)
        cloudsmith_client = CloudsmithClient(
            format_type=format_type,
            repo=f"{format_type}-repo",  # Assuming different repos for different formats
            mock=args.mock
        )
        
        # Step 1: Get all versionless packages from Nexus
        nexus_packages = []
        if not args.cloudsmith_only:
            logger.info(f"Step 1: Fetching all versionless {format_type} packages from Nexus")
            nexus_packages = nexus_client.list_package_groups()
            logger.info(f"Found {len(nexus_packages)} {format_type} packages in Nexus")
        
        # Process each package
        for pkg in nexus_packages:
            # Step 2: Get lastUpdated date from Nexus for each package
            logger.info(f"Step 2: Getting lastUpdated date from Nexus for {pkg}")
            nexus_date = nexus_client.get_last_updated_date(pkg)
            
            if format_type == "maven":
                group_id = pkg.get("groupId")
                artifact_id = pkg.get("artifactId")
                package_key = f"{group_id}:{artifact_id}"
                logger.info(f"Nexus date for {package_key}: {format_date_for_display(nexus_date)}")
            else:
                name = pkg.get("name")
                logger.info(f"Nexus date for {name}: {format_date_for_display(nexus_date)}")
            
            # Step 3: Get last updated date from Cloudsmith for each package
            if not args.nexus_only:
                logger.info(f"Step 3: Querying Cloudsmith Package Group API for {pkg}")
                cloudsmith_date = cloudsmith_client.get_last_updated_date(pkg)
                
                if format_type == "maven":
                    logger.info(f"Cloudsmith date for {package_key}: {format_date_for_display(cloudsmith_date)}")
                else:
                    logger.info(f"Cloudsmith date for {name}: {format_date_for_display(cloudsmith_date)}")
            else:
                cloudsmith_date = None
            
            # Step 4: Pick older of the 2 dates
            logger.info("Step 4: Comparing dates and selecting the older one")
            freshness_date, date_source = compare_dates(nexus_date, cloudsmith_date)
            
            if format_type == "maven":
                logger.info(f"Freshness date for {package_key}: {format_date_for_display(freshness_date)} (from {date_source})")
                
                # Store the results
                results.append({
                    'format': format_type,
                    'groupId': group_id,
                    'artifactId': artifact_id,
                    'nexus_date': nexus_date,
                    'cloudsmith_date': cloudsmith_date,
                    'freshness_date': freshness_date,
                    'source': date_source
                })
                
                # Print details
                print(f"Package: {package_key}")
                print(f"  Nexus date: {format_date_for_display(nexus_date)}")
                print(f"  Cloudsmith date: {format_date_for_display(cloudsmith_date)}")
                print(f"  Freshness date: {format_date_for_display(freshness_date)} (from {date_source})")
                print()
            else:
                name = pkg.get("name")
                logger.info(f"Freshness date for {name}: {format_date_for_display(freshness_date)} (from {date_source})")
                
                # Store the results
                results.append({
                    'format': format_type,
                    'name': name,
                    'nexus_date': nexus_date,
                    'cloudsmith_date': cloudsmith_date,
                    'freshness_date': freshness_date,
                    'source': date_source
                })
                
                # Print details
                print(f"Package: {name}")
                print(f"  Nexus date: {format_date_for_display(nexus_date)}")
                print(f"  Cloudsmith date: {format_date_for_display(cloudsmith_date)}")
                print(f"  Freshness date: {format_date_for_display(freshness_date)} (from {date_source})")
                print()
    
    # Output to CSV if requested
    if args.output_csv:
        try:
            import csv
            with open(args.output_csv, 'w', newline='') as f:
                if not results:
                    logger.warning("No results to write to CSV")
                    return
                    
                # Determine the fieldnames based on the format
                if results[0].get('format') == 'maven':
                    fieldnames = ['format', 'groupId', 'artifactId', 'nexus_date', 'cloudsmith_date', 'freshness_date', 'source']
                else:
                    fieldnames = ['format', 'name', 'nexus_date', 'cloudsmith_date', 'freshness_date', 'source']
                    
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            logger.info(f"Results written to {args.output_csv}")
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
    
    # Step 5: Log results
    logger.info("Step 5: Logging results summary")
    
    # Print summary
    print("\nSummary:")
    print(f"Total packages: {len(results)}")
    print(f"Using Nexus date: {sum(1 for r in results if r['source'] == 'nexus')}")
    print(f"Using Cloudsmith date: {sum(1 for r in results if r['source'] == 'cloudsmith')}")
    print(f"Missing date: {sum(1 for r in results if r['source'] == 'unknown')}")


if __name__ == "__main__":
    main()
