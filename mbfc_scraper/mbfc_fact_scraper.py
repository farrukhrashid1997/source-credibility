import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm
import time
import re
import os
import random

def setup_driver():
    firefox_options = Options()
    firefox_options.add_argument("--headless")  # Run in headless mode
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Firefox(options=firefox_options)

def scrape_fact_check(url, retries=3, min_delay=1, max_delay=3):
    """
    Function to scrape fact-check details from a URL using Selenium with retry logic and random delay.
    """
    for attempt in range(retries):
        try:
            driver = setup_driver()
            driver.get(url)
            
            # Wait for content to load
            wait = WebDriverWait(driver, 10)
            content = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "entry-content")))
            
            # Extract relevant information
            fact_check_text = content.text
            return fact_check_text
        
        except Exception as e:
            print(f"Error scraping {url} on attempt {attempt + 1}: {str(e)}")
            # Introduce random delay before retrying
            time.sleep(random.uniform(min_delay, max_delay))
            
        finally:
            driver.quit()
    
    print(f"Failed to scrape {url} after {retries} attempts.")
    return None

def extract_detailed_report(text):
    """
    Extracts fields from the Detailed Report section.
    Returns a dictionary with the extracted fields.
    """
    data = {
        'Bias Rating': None,
        'Factual Reporting': None,
        'Country': None,
        'Media Type': None,
        'Traffic/Popularity': None,
        'MBFC Credibility Rating': None
    }
    
    try:
        # Find the "Detailed Report" section
        detailed_report_start = text.find("Detailed Report")
        if detailed_report_start == -1:
            print("Detailed Report section not found.")
            return data
        
        # Extract the text after "Detailed Report"
        detailed_text = text[detailed_report_start:]
        
        # Define regex patterns for each field
        patterns = {
            'Bias Rating': r'Bias Rating:\s*(.*)',
            'Factual Reporting': r'Factual Reporting:\s*(.*)',
            'Country': r'Country:\s*(.*)',
            'Media Type': r'Media Type:\s*(.*)',
            'Traffic/Popularity': r'Traffic/Popularity:\s*(.*)',
            'MBFC Credibility Rating': r'MBFC Credibility Rating:\s*(.*)'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, detailed_text)
            if match:
                data[field] = match.group(1).strip()
            else:
                print(f"Field '{field}' not found in Detailed Report.")
        
    except Exception as e:
        print(f"Error extracting detailed report: {str(e)}")
    
    return data

def scrape_and_extract(url):
    """
    Scrape the URL and extract data, returning a dictionary with the extracted data.
    """
    content = scrape_fact_check(url)
    if content:
        return extract_detailed_report(content)
    else:
        print(f"No content scraped for {url}")
        return None

def save_progress(df, path, lock):
    """
    Saves the DataFrame progress to a CSV file with a lock to ensure thread-safety.
    """
    with lock:
        if os.path.exists(path):
            existing_df = pd.read_csv(path)
            df_combined = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset='Link')
            df_combined.to_csv(path, index=False)
        else:
            df.to_csv(path, index=False)
    print("Progress saved.")

def main():
    # Read the CSV file
    df = pd.read_csv('../bias_data/all.csv')
    
    # Check if results file exists and read already scraped URLs
    scraped_results_path = '../bias_data/scraped_results.csv'
    if os.path.exists(scraped_results_path):
        df_scraped = pd.read_csv(scraped_results_path)
        scraped_urls = set(df_scraped['Link'].tolist())
    else:
        df_scraped = pd.DataFrame(columns=df.columns)
        scraped_urls = set()

    # Filter URLs that haven't been scraped
    df_to_scrape = df[~df['Link'].isin(scraped_urls)]

    # Initialize manager for lock and scraped data buffer
    manager = Manager()
    lock = manager.Lock()
    
    # Use multiprocessing to scrape URLs with reduced parallelism (quarter of available cores)
    num_cores = max(cpu_count() // 4, 1)
    with Pool(num_cores) as pool:
        chunk_size = 10  # Save progress after every 10 rows
        for i in range(0, len(df_to_scrape), chunk_size):
            # Scrape a chunk of URLs
            chunk = df_to_scrape.iloc[i:i+chunk_size]
            results = list(tqdm(pool.imap(scrape_and_extract, chunk['Link']), total=len(chunk), desc="Scraping URLs"))

            # Append results to DataFrame
            for j, result in enumerate(results):
                if result:
                    for key, value in result.items():
                        chunk.loc[chunk.index[j], key] = value  # Using .loc to avoid SettingWithCopyWarning

            # Save progress for the current chunk
            save_progress(chunk, scraped_results_path, lock)

    print("Scraping completed. Results saved to 'bias_data/scraped_results.csv'.")

if __name__ == "__main__":
    main()
