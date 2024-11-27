import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
import os
from selenium.webdriver.firefox.options import Options

# Configure Firefox options for headless browsing and disable JavaScript
op = Options()
op.headless = True  # Enable headless mode
op.set_preference('javascript.enabled', False)  # Disable JavaScript for faster loading

# Create the 'data' directory if it doesn't exist
currentdir = os.listdir()
if "data" not in currentdir:
    os.mkdir("data")

# Initialize the Firefox WebDriver with the specified options
driver = webdriver.Firefox(options=op)

# Define the categories to scrape from Media Bias Fact Check
categories = {
    "left", "leftcenter", "center", "right-center",
    "right", "conspiracy", "fake-news", "pro-science", "satire"
}

# Loop through each category to scrape data
for category in categories:
    # Construct the URL for the current category and navigate to it
    url = f'https://mediabiasfactcheck.com/{category}/'
    driver.get(url)

    # Initialize lists to store group names and their corresponding links
    groups = []
    hrefs = []
    links = []

    # Retrieve the page source and parse it with BeautifulSoup
    content = driver.page_source
    soup = BeautifulSoup(content, 'html.parser')

    # Locate the target table by its ID
    table = soup.find('table', id="mbfc-table")
    if not table:
        print(f"Table with id 'mbfc-table' not found for category '{category}'. Skipping.")
        continue  # Skip to the next category if the table isn't found

    # Extract all rows from the table
    rows = table.find_all('tr')

    # Iterate through each row to extract group names and href links
    for row in rows:
        # Extract text for the group name
        group_text = row.get_text(strip=True)
        groups.append(group_text)

        # Attempt to extract the href link
        try:
            href = row.find('a')['href']
            links.append(f"{href}")
        except (AttributeError, TypeError):
            # If href extraction fails, append a blank string to indicate an advert or malformed row
            links.append(" ")

    # Create a DataFrame from the extracted data
    df = pd.DataFrame({
        'Group': groups,
        'Link': links,
        "Type": category
    })

    # Remove rows that likely correspond to adverts or empty entries
    no_advert = df[df["Link"] != " "]
    
    # Save the cleaned DataFrame to a CSV file within the 'data' directory
    csv_path = os.path.join("data", f"{category}.csv")
    no_advert.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"Data for category '{category}' saved to '{csv_path}'.")

# Close the WebDriver session
driver.quit()

# Consolidate all individual category CSV files into a single 'all.csv' file
data_dir = "data"
all_csv_path = os.path.join(data_dir, "all.csv")

# List all CSV files in the 'data' directory excluding 'all.csv' itself
csv_files = [file for file in os.listdir(data_dir) if file.endswith('.csv') and file != "all.csv"]

# Read and concatenate all CSV files into a single DataFrame
all_data = pd.concat([pd.read_csv(os.path.join(data_dir, file)) for file in csv_files], ignore_index=True)

# Save the consolidated data to 'all.csv'
all_data.to_csv(all_csv_path, index=False, encoding="utf-8")
print(f"All data consolidated into '{all_csv_path}'.")
