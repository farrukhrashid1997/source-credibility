from urllib.parse import urlparse
import ssl
import socket
import whois
import pandas as pd
from typing import Dict
import logging
import requests
import time
import random
logging.basicConfig(level=logging.INFO)


class SourceCredibility:
    def __init__(self):
        self.full_df = pd.read_csv('bias_data/media-bias.csv')
        self.credibility_scores_map = {
            'LOW CREDIBILITY': 1,
            'MIXED CREDIBILITY': 2,
            'MEDIUM CREDIBILITY': 3,
            'HIGH': 4,
            'HIGH CREDIBILITY': 4,
        }

        self.factual_ratings_map = {
            'VERY HIGH': 6,
            'VERY-HIGH': 6,
            "HIGH": 5,    
            "MOSTLY FACTUAL": 4,            
            "MIXED": 3,    
            "VERY-LOW": 2,                
            "VERY LOW": 2,           
            "LOW": 1,                
        }

        self.bias_scores_map = {
            "left": 1,
            "leftcenter": 2,
            "center": 3,
            "right-center": 4,
            "right": 5,
            "pro-science": 3,
            "conspiracy": 5,
            "fake-news": 5,
        }

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
            logging.error(f"Error getting SSL status for {domain}: {e}")
            return False
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
        time.sleep(random.uniform(0, 1))
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['response'][0]['status_code'] == 200:
                    return data['response'][0]['page_rank_integer']
            logging.warning(f"No PageRank data found for {domain}")
            return 0
        except Exception as e:
            logging.error(f"Error retrieving Open PageRank for {domain}: {e}")
            return None
        
    def get_domain_age(self, domain: str) -> float:
        """Calculates the age of the domain in years. The older the better."""
        max_retries = 3
        
        # Add random initial delay to help prevent concurrent requests
        time.sleep(random.uniform(0, 1))
        
        for attempt in range(max_retries):
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
                if attempt < max_retries - 1:
                    # Randomize retry delay to help prevent concurrent retries
                    time.sleep(random.uniform(0, 0.5))
                    continue
                logging.error(f"Error getting domain age for {domain} after {max_retries} attempts: {e}")
                return None
        
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
                            'wikipedia_presence': True,
                            'wikipedia_page_url': wikipedia_page_url
                        }
                return {'wikipedia_presence': False, 'wikipedia_page_url': None}
            except Exception as e:
                logging.error(f"Error checking Wikipedia presence for {domain}: {e}")
                return {'wikipedia_presence': False, 'wikipedia_page_url': None}

    def get_tld_score(self, domain: str) -> float:
        """Assigns a credibility score based on the Top Level Domain (TLD)"""
        # tld_scores = {
        #     # Highly restricted TLDs (hardest to obtain)
        #     'gov': 10.0,    # U.S. government entities
        #     'mil': 10.0,     # U.S. military
        #     'edu': 9.5,     # Accredited postsecondary U.S. institutions
        #     'int': 9.5,     # International treaty-based organizations
        #     'arpa': 9.5,    # Advanced research projects

        #     # Country-code TLDs with strict regulations
        #     'gov.uk': 9.0,  # UK government entities
        #     'ac.uk': 9.0,   # UK academic institutions
        #     'gov.au': 9.0,  # Australian government entities
        #     'edu.au': 9.0,  # Australian educational institutions
        #     'go.jp': 9.0,   # Japanese government entities

        #     # Sponsored TLDs (moderately restricted)
        #     'org': 8.0,     # Non-profit organizations
        #     'net': 7.5,     # Network providers
        #     'coop': 7.5,    # Cooperatives
        #     'museum': 7.5,  # Museums

        #     # Generic TLDs (widely available but have authority)
        #     'com': 7.0,     # Commercial entities
        #     'co': 7.0,      # Recognized as "company"
        #     'us': 6.8,      # United States entities
        #     'uk': 6.8,      # United Kingdom entities
        #     'ca': 6.8,      # Canadian entities
        #     'de': 6.8,      # German entities
        #     'fr': 6.8,      # French entities
        #     'au': 6.8,      # Australian entities
        #     'jp': 6.8,      # Japanese entities

        #     # Specialized TLDs (industry-specific, less authoritative)
        #     'info': 6.0,    # Information services
        #     'biz': 6.0,     # Business use
        #     'pro': 6.0,     # Licensed professionals
        #     'name': 5.5,    # Personal names
        #     'me': 5.5,      # Personal blogs or resumes
        #     'io': 5.5,      # Tech startups, originally British Indian Ocean Territory
        #     'ai': 5.5,      # Artificial Intelligence, originally Anguilla
        #     'tech': 5.0,    # Technology sector
        #     'dev': 5.0,     # Developers
        #     'app': 5.0,     # Applications

        #     # Generic and niche TLDs (easily obtainable)
        #     'blog': 4.5,    # Blogs
        #     'online': 4.5,  # Online services
        #     'site': 4.5,    # Websites
        #     'shop': 4.0,    # E-commerce sites
        #     'club': 4.0,    # Clubs and membership organizations
        #     'space': 4.0,   # Space-related content or open-ended use
        #     'xyz': 3.5,     # General use
        #     'live': 3.5,    # Live events or streaming
        #     'world': 3.5,   # Global organizations
        #     'today': 3.0,   # News and updates

        #     # Less authoritative TLDs (least restricted)
        #     'website': 3.0,
        #     'biz': 3.0,
        #     'top': 3.0,
        #     'win': 2.5,
        #     'men': 2.5,
        #     'party': 2.5,

        #     # Free or low-cost TLDs (least authoritative)
        #     'tk': 2.0,      # Tokelau, free domains
        #     'ml': 2.0,      # Mali, free domains
        #     'ga': 2.0,      # Gabon, free domains
        #     'cf': 2.0,      # Central African Republic, free domains
        #     'gq': 2.0,      # Equatorial Guinea, free domains
        # }

        tld_scores_extended = {
            # Sponsored / restricted TLDs (very high authority)
            'gov': 10.0,           # U.S. government only
            'mil': 10.0,           # U.S. military only
            'edu': 9.5,            # Accredited U.S. educational institutions
            'int': 9.5,            # International organizations
            'aq': 9.0,             # Antarctica (must be affiliated with Antarctica)
            'bank': 9.0,           # Financial institutions (restricted)
            'cern': 9.5,           # Reserved for CERN
            'google': 9.5,         # Brand TLD
            'va': 9.5,             # Vatican City
            'gop': 8.5,            # Political party use (restricted)
            'ngo': 8.0,            # Non-Governmental Organizations
            'law': 8.0,            # Often restricted to licensed legal entities

            # Sponsored / moderately restricted
            'aero': 7.5,           # Aerospace industry
            'coop': 7.5,           # Cooperative associations
            'cpa': 7.5,            # Certified Public Accountants (restricted)
            'realtor': 7.5,        # National Assoc. of Realtors (restricted)
            'travel': 7.5,         # Travel and tourism (sponsored)
            'org': 8.0,            # Non-profit organizations (historically)
            'net': 7.5,            # Network service providers (historically)
            'cat': 7.0,            # Catalan linguistic/cultural community (restricted)

            # Well-known generics (widely used, still fairly authoritative)
            'com': 7.0,
            'co': 7.0,             # Recognized as commercial/company
            'uk': 6.5,             # United Kingdom
            'us': 6.5,             # United States
            'au': 6.5,             # Australia
            'jp': 6.5,             # Japan
            'de': 6.5,             # Germany
            'fr': 6.5,             # France
            'se': 6.5,             # Sweden
            'nl': 6.5,             # Netherlands
            'cz': 6.5,             # Czech Republic
            'ie': 6.5,             # Ireland
            'it': 6.5,             # Italy

            # Other country-code TLDs (ccTLDs) generally open or lightly restricted
            'at': 6.0,             # Austria
            'be': 6.0,             # Belgium
            'br': 6.0,             # Brazil
            'ch': 6.8,             # Switzerland
            'cl': 6.0,             # Chile
            'cn': 6.0,             # China
            'dk': 6.0,             # Denmark
            'es': 6.0,             # Spain
            'eu': 6.0,             # European Union
            'fi': 6.0,             # Finland
            'gr': 6.0,             # Greece
            'hk': 6.0,             # Hong Kong
            'id': 6.0,             # Indonesia
            'in': 6.0,             # India
            'is': 6.0,             # Iceland
            'kr': 6.0,             # South Korea
            'lt': 6.0,             # Lithuania
            'lu': 6.0,             # Luxembourg
            'lv': 6.0,             # Latvia
            'mx': 6.0,             # Mexico
            'my': 6.0,             # Malaysia
            'no': 6.0,             # Norway
            'nz': 6.0,             # New Zealand
            'pl': 6.0,             # Poland
            'ro': 6.0,             # Romania
            'ru': 6.0,             # Russia
            'sg': 6.0,             # Singapore
            'sk': 6.0,             # Slovakia
            'tr': 6.0,             # Turkey
            'tw': 6.0,             # Taiwan
            'ua': 6.0,             # Ukraine
            'vn': 6.0,             # Vietnam
            'za': 6.0,             # South Africa
            'ph': 5.5,             # Philippines
            'pk': 5.5,             # Pakistan
            've': 5.5,             # Venezuela
            'ma': 5.5,             # Morocco
            'md': 5.5,             # Moldova (.md used by medical)
            'sv': 5.5,             # El Salvador
            'ag': 5.5,             # Antigua & Barbuda
            'ke': 5.5,             # Kenya
            'kz': 5.5,             # Kazakhstan
            'la': 5.5,             # Laos (often used for "LA")
            'lb': 5.5,             # Lebanon
            'mk': 5.5,             # North Macedonia
            'mn': 5.5,             # Mongolia
            'na': 5.5,             # Namibia
            'ng': 5.5,             # Nigeria
            'nu': 5.5,             # Niue
            'nyc': 5.5,            # New York City
            'pe': 5.5,             # Peru
            'qa': 5.5,             # Qatar
            'scot': 5.5,           # Scotland
            'sv': 5.5,             # El Salvador
            'to': 5.5,             # Tonga
            'tz': 5.5,             # Tanzania
            'ug': 5.5,             # Uganda
            'ws': 5.5,             # Western Samoa

            # Industry-specific or brand/generic TLDs (moderately authoritative)
            'inc': 5.5,            # .inc for businesses
            'io': 5.5,             # Tech usage (originally British Indian Ocean Territory)
            'fm': 5.5,             # Often used by radio/podcasting
            'je': 5.5,             # Jersey (sometimes used as personal or brand)
            'studio': 4.5,         # Creative, design, or media
            'media': 5.0,          # Media organizations
            'education': 5.0,      # Education-related (open registration)
            'engineering': 5.5,    # Engineering field
            'health': 5.5,         # Health sector
            'foundation': 5.0,     # Foundations / philanthropic orgs
            'institute': 5.0,      # Institutes (open usage)
            'money': 4.5,          # Financial service or personal finance
            'news': 5.5,           # News sites
            'press': 4.5,          # Press releases/journalism
            'pub': 4.5,            # Publications
            'report': 4.5,         # Reporting or analytics
            'guide': 4.5,          # Tutorials / guides
            'guru': 4.5,           # Expertise or coaching
            'training': 5.0,       # Training and instruction
            'energy': 5.0,         # Energy sector
            'codes': 4.5,          # Programming or discount codes
            'company': 4.5,        # Companies (generic)
            'international': 4.5,  # Generic for “global” brand or org
            'business': 5.0,       # Generic
            'care': 4.5,           # Healthcare / personal care
            'auto': 5.0,           # Automotive sector
            'africa': 4.5,         # Africa-based content or brand
            'asia': 5.0,           # Asia-based content or brand
            'global': 5.0,         # Branding as global
            'earth': 3.5,          # Environmental or novelty use
            'faith': 3.0,          # Religious communities (open registration)
            'farm': 4.5,           # Agriculture
            'me': 4.0,             # Personal use

            # Common “specialty” gTLDs
            'info': 6.0,
            'pro': 6.0,
            'biz': 6.0,            # Historically “business” usage
            'blog': 4.5,
            'online': 4.5,
            'space': 4.0,
            'top': 3.0,
            'today': 3.0,
            'best': 4.0,
            'red': 3.5,
            'vote': 4.5,
            'wiki': 4.5,
            'works': 4.5,

            # City or geographic TLDs
            'nyc': 5.5,
            'rugby': 4.5,
            'scot': 5.5,
            # (already listed .cat, .asia, etc.)

            # Misc. brand / marketing or niche TLDs
            'auto': 5.0,
            'app': 5.0,            # Often used for mobile/web applications
            'digital': 4.5,

            # Lower-tier or novel TLDs
            'website': 3.0,
            'biz': 3.0,
            'top': 3.0,
            'win': 2.5,
            'men': 2.5,
            'party': 2.5,

            # Free or low-cost TLDs (least authoritative)
            'tk': 2.0,      # Tokelau, free domains
            'ml': 2.0,      # Mali, free domains
            'ga': 2.0,      # Gabon, free domains
            'cf': 2.0,      # Central African Republic, free domains
            'gq': 2.0,      # Equatorial Guinea, free domains
        }


        tld_with_port = domain.split('.')[-1]
        tld = tld_with_port.split(':')[0]
        return tld_scores_extended.get(tld, 3.0) # We assume a low-level TLD if it is not in the list



    def get_media_bias(self, domain: str) -> tuple:
        """
        paper: https://aclanthology.org/D18-1389/ - this paper uses MBFC as a reference in creating the dataset, in order to get the bias 
        of a certain news source. 
        """
        try:
            # match = df[df['url'].apply(lambda x: domain in x)]
            # We should cache self.full_df['Group'] so that we don't have to do this every time 
            match = self.full_df[self.full_df['Group'].str.lower().apply(lambda x: domain.lower() in x if pd.notnull(x) else False)]

            if not match.empty:
                val = (
                    match.iloc[0]['Group'],
                    match.iloc[0]['Type'],  
                    match.iloc[0]['Factual Reporting'],  
                    match.iloc[0]['MBFC Credibility Rating']
                )
                return val
        except Exception as e:
            logging.error(f"Error getting media bias for {domain}: {e}")
        return (None, None, None, None)
