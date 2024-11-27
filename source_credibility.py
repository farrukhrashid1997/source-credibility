from urllib.parse import urlparse
import ssl
import socket
import whois
import pandas as pd
from typing import Dict
import logging
import requests
logging.basicConfig(level=logging.INFO)

class SourceCredibility:
    # def __init__(self):
        
        
    def extract_domain(self, url):
        """Extracts the domain from a URL."""
        parsed_uri = urlparse(url)
        domain = parsed_uri.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    
    def get_ssl_status(self, domain):
        """Checks if the domain has a valid SSL certificate."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain):
                    return True
        except Exception as e: 
            print(e)
            return False
        
    def get_open_page_rank(self, domain: str) -> float:
        """Gets the Open PageRank score for the given domain. 
        The score is from 1-10, a higher score means that `domain` is referenced by several 
        reputable websites."""
        
        url = "https://openpagerank.com/api/v1.0/getPageRank"
        headers = {
            'API-OPR': "08ok8co4o48cwo8w0gg4cc0swo0084cckwgwco8o"
        }
        params = {
            'domains[]': domain
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['response'][0]['status_code'] == 200:
                    return data['response'][0]['page_rank_integer']
            logging.warning(f"No PageRank data found for {domain}")
            return None
        except Exception as e:
            logging.error(f"Error retrieving Open PageRank for {domain}: {e}")
            return None

    
    def get_domain_age(self, domain: str) -> float:
        """Calculates the age of the domain in years. The older the better."""
        try:
            w = whois.whois(domain)
            creation_date = w.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            if creation_date is None:
                logging.warning(f"No creation date found for domain {domain}")
                return 0
            age = (pd.Timestamp.now() - pd.to_datetime(creation_date)).days / 365
            return age
        except Exception as e:
            logging.error(f"Error getting domain age for {domain}: {e}")
            return 0
        
    def check_social_media_presence(self, url: str) -> Dict:
            """Check if the website has a Wikipedia presence """
            domain = self.extract_domain(url)
            wikipedia_api_url = f"https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': domain,
                'format': 'json',
                'utf8': 1
            }
            
            try:
                response = requests.get(wikipedia_api_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data['query']['search']:
                        page_title = data['query']['search'][0]['title']
                        wikipedia_page_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                        return {
                            'domain': domain,
                            'wikipedia_presence': True,
                            'wikipedia_page_url': wikipedia_page_url
                        }
                return {'domain': domain, 'wikipedia_presence': False}
            except Exception as e:
                logging.error(f"Error checking Wikipedia presence for {domain}: {e}")
                return {'domain': domain, 'wikipedia_presence': False}

    def get_tld_score(self, domain: str) -> float:
        """Assigns a credibility score based on the TLD of the domain."""
        tld_scores = {
            'gov': 10.0,
            'edu': 9.5,
            'org': 8.0,
            'com': 7.0,
        }
        
        tld = domain.split('.')[-1]
        return tld_scores.get(tld)



    def get_media_bias(self, url):
        """
        paper: https://aclanthology.org/D18-1389/ - this paper uses MBFC as a reference in creating the dataset, in order to get the bias 
        of a certain news source. 
        
        Get the media bias and factual reporting rating for a given URL from the scrubbed results.
        The bias rating ranges from -30 to +30, extreme-left to extreme-right
        Args:
            url (str): The URL to check
            
 
        
        Returns:
            tuple: (bias_rating, factual_rating) or (None, None) if not found
        """
        try:
            # Read the CSV file
            df = pd.read_csv('bias_data/media-bias-scrubbed-results.csv')
            domain = self.extract_domain(url)
            match = df[df['url'].apply(lambda x: domain in x)]
            if not match.empty:
                return (
                    url,
                    match.iloc[0]['bias_rating'],  # Bias rating (-30 to +30) ()
                    match.iloc[0]['factual_reporting_rating']  # Factual rating (HIGH/MIXED/etc)
                )
            return None, None
        except Exception as e:
            print(f"Error reading bias data: {e}")
            return None, None


        



if __name__ == "__main__":
    url_list = [
        'https://www.bbc.com',
    ]
    
    credibility_checker = SourceCredibility()
    results = []
    for url in url_list:
        domain = credibility_checker.extract_domain(url)
        ssl_status = credibility_checker.get_ssl_status(domain)
        domain_age = credibility_checker.get_domain_age(domain)
        wikipedia_presence = credibility_checker.check_social_media_presence(url)
        page_rank = credibility_checker.get_open_page_rank(domain)
        tld = credibility_checker.get_tld_score(domain)
        
        results.append({
            'url': url,
            'ssl_status': ssl_status,
            'domain_age': domain_age,
            'wikipedia_presence': wikipedia_presence,
            'page_rank': page_rank,
            "tld_score": tld
        })
        
    for result in results:
        print(result)
