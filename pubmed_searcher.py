import requests
import xml.etree.ElementTree as ET
import time

class PubMedSearcher:
    def __init__(self):
        self.base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.retry_limit = 5  # Number of retries in case of rate-limiting or errors

    def fetch_all_pubmed_ids(self, term):
        """Fetches all PubMed IDs for a given search term, with retries on server errors."""
        all_ids = []
        retstart = 0
        retries = 0

        while True:
            search_params = {
                "db": "pubmed",
                "term": term,
                "retmode": "xml",
                "retmax": 100,
                "retstart": retstart
            }

            try:
                search_response = requests.get(self.base_search_url, params=search_params)
                
                if search_response.status_code == 200:
                    search_xml = ET.fromstring(search_response.text)
                    id_list = [id_elem.text for id_elem in search_xml.findall(".//Id")]
                    if not id_list:
                        break  # No more IDs found, exit the loop
                    all_ids.extend(id_list)
                    retstart += 100
                    retries = 0
                else:
                    raise Exception(f"Failed to search PubMed: HTTP Status Code {search_response.status_code}")

            except Exception as e:
                retries += 1
                if retries < self.retry_limit:
                    time.sleep(2 ** retries)  # Exponential backoff
                    print(f"Retrying... ({retries}/{self.retry_limit}) due to error: {e}")
                else:
                    raise Exception(f"Failed to search PubMed after {self.retry_limit} retries: {e}")

        return all_ids

    def fetch_article_details(self, pubmed_ids):
        """Fetches detailed information for a list of PubMed IDs, including Title, Abstract, Keywords, Year, First Author, PubMed link, and Access Type."""
        articles = []
        batch_size = 100

        for i in range(0, len(pubmed_ids), batch_size):
            batch_ids = pubmed_ids[i:i + batch_size]
            retries = 0
            while retries < self.retry_limit:
                try:
                    params = {
                        "db": "pubmed",
                        "retmode": "xml",
                        "id": ",".join(batch_ids)
                    }
                    response = requests.get(self.base_fetch_url, params=params)
                    
                    if response.status_code == 200:
                        xml_data = response.text
                        root = ET.fromstring(xml_data)

                        for article in root.findall(".//PubmedArticle"):
                            article_dict = {}

                            # Extract Title
                            title_element = article.find(".//ArticleTitle")
                            article_dict["Title"] = title_element.text if title_element is not None else "No title available"

                            # Extract Abstract
                            abstract_sections = article.findall(".//AbstractText")
                            abstract_text = " ".join([section.text for section in abstract_sections if section.text])
                            article_dict["Abstract"] = abstract_text if abstract_text else "No abstract available"

                            # Extract Keywords
                            keywords = [keyword.text for keyword in article.findall(".//Keyword") if keyword.text]
                            article_dict["Keywords"] = ", ".join(keywords) if keywords else "No keywords available"

                            # Extract Pub Date (Year)
                            pub_date = article.find(".//PubDate")
                            year_element = pub_date.find("Year") if pub_date is not None else None
                            article_dict["Year"] = year_element.text if year_element is not None else "Unknown"

                            # Extract First Author
                            authors = article.findall(".//Author")
                            if authors:
                                first_author_element = authors[0].find(".//LastName")
                                first_author = first_author_element.text if first_author_element is not None else "Unknown"
                                if len(authors) > 1:
                                    first_author += " et al."
                                article_dict["First Author"] = first_author
                            else:
                                article_dict["First Author"] = "No author information available"

                            # Extract PubMed Link
                            pmid_element = article.find(".//PMID")
                            if pmid_element is not None:
                                pmid = pmid_element.text
                                article_dict["Link"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

                                # Check if article is free access (by checking if there's a PMC ID)
                                pmc_id = article.find(".//ArticleId[@IdType='pmc']")
                                article_dict["Access Type"] = "Free Access" if pmc_id is not None else "Restricted Access"
                            else:
                                article_dict["Link"] = "No link available"
                                article_dict["Access Type"] = "Unknown"

                            articles.append(article_dict)
                        break
                    elif response.status_code == 429:
                        retries += 1
                        wait_time = 2 ** retries
                        print(f"Rate limit reached. Retrying in {wait_time} seconds... ({retries}/{self.retry_limit})")
                        time.sleep(wait_time)
                    else:
                        raise Exception(f"Failed to fetch article details from PubMed: HTTP Status Code {response.status_code}")

                except Exception as e:
                    retries += 1
                    if retries >= self.retry_limit:
                        raise Exception(f"Failed to fetch article details after {self.retry_limit} retries: {e}")

        return articles
