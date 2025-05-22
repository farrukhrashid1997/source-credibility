# source-credibility

This repo is for calculating a credibility score of a news source – the score will be used in the automated fact checking pipeline.

## 🔍 Overview

This repository provides a framework for evaluating the **credibility of news sources** using a variety of signals such as:

- **Domain metadata** (age, TLD, SSL)
- **Popularity and authority metrics** (Open PageRank)
- **Presence on public platforms** (e.g., Wikipedia)
- **Media bias and factual accuracy ratings** (via MBFC dataset)

The final credibility score can be plugged into downstream automated fact-checking pipelines to improve decision-making about source reliability.

---

## 🧠 Features

### ✅ Domain Extraction
Extracts normalized domain names from any input URL.

### 🔐 SSL Verification
Checks if the domain has a valid SSL certificate using socket-level checks.

### 🌐 Open PageRank
Fetches a domain’s PageRank from the [OpenPageRank API](https://www.domcop.com/openpagerank/), indicating backlink authority.

### 📅 Domain Age
Uses WHOIS records to calculate the age of a domain (older domains are typically more reputable).

### 🧾 TLD Reputation Scoring
Assigns credibility based on the domain’s Top-Level Domain (e.g., `.gov`, `.edu`, `.com`, etc.) using an internally curated scoring list.

### 📖 Wikipedia Presence
Checks whether the domain has a corresponding Wikipedia page to assess public visibility and trustworthiness.

### 📰 Media Bias & Factual Reporting
Uses [MBFC (Media Bias/Fact Check)](https://mediabiasfactcheck.com/) data to classify domains by:
- Bias (`left`, `center`, `right`, etc.)
- Factual reporting score (`low` to `very high`)
- MBFC’s own credibility rating

---

## 🛠️ Setup

```bash
pip install -r requirements.txt
