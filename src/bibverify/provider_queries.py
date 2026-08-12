"""Academic metadata provider queries."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests


class ProviderQueriesMixin:
    def _crossref_headers(self):
        use_polite = (
            self.config.get("platforms", {}).get("crossref", {}).get("use_polite_pool", True)
        )
        user_agent = (
            f"{self.app_name}/2.0 (mailto:{self.user_email})"
            if use_polite
            else f"{self.app_name}/2.0"
        )
        return {"User-Agent": user_agent}

    def _crossref_params(self):
        use_polite = (
            self.config.get("platforms", {}).get("crossref", {}).get("use_polite_pool", True)
        )
        if use_polite and self.user_email:
            return {"mailto": self.user_email}
        return {}

    def query_crossref_by_doi(self, doi, title=None):
        doi = self.canonicalize_doi(doi)
        if not doi:
            return None

        try:
            base_url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(
                base_url,
                params=self._crossref_params(),
                headers=self._crossref_headers(),
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            item = data.get("message", {})

            if title:
                candidate_title = item.get("title", [""])
                candidate_title = candidate_title[0] if candidate_title else ""
                if not candidate_title or not self.is_title_match(title, candidate_title):
                    return None

            return ("crossref", item) if item else None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='CrossRef')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 404:
                print(
                    f"    {self.lang.get_text('http_error', platform='CrossRef', code=e.response.status_code)}"
                )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='CrossRef', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='CrossRef', error=str(e)[:50])}"
            )
            return None

    def query_crossref(self, title):
        try:
            base_url = "https://api.crossref.org/works"
            clean_title = self.clean_title(title)
            params = {"query.title": clean_title, "rows": 5}
            params.update(self._crossref_params())

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(
                base_url, params=params, headers=self._crossref_headers(), timeout=timeout
            )
            response.raise_for_status()
            data = response.json()

            if data["message"]["items"]:
                for item in data["message"]["items"]:
                    if item.get("title"):
                        candidate_title = item["title"][0]
                        if self.is_title_match(title, candidate_title):
                            return ("crossref", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='CrossRef')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='CrossRef', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='CrossRef', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='CrossRef', error=str(e)[:50])}"
            )
            return None

    def query_arxiv(self, title):
        try:
            base_url = "https://export.arxiv.org/api/query"
            clean_title = self.clean_title(title)
            params = {"search_query": f'ti:"{clean_title}"', "max_results": 5}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", namespace)

            for entry in entries:
                title_elem = entry.find("atom:title", namespace)
                if title_elem is not None:
                    candidate_title = title_elem.text.strip().replace("\n", " ")
                    if self.is_title_match(title, candidate_title):
                        return ("arxiv", entry, namespace)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='arXiv')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='arXiv', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='arXiv', error=str(e)[:50])}")
            return None
        except ET.ParseError:
            print(f"    {self.lang.get_text('xml_parse_error', platform='arXiv')}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='arXiv', error=str(e)[:50])}")
            return None

    def query_openalex(self, title):
        try:
            base_url = "https://api.openalex.org/works"
            clean_title = self.clean_title(title)
            params = {"filter": f"title.search:{clean_title}", "per_page": 5}
            use_polite = (
                self.config.get("platforms", {}).get("openalex", {}).get("use_polite_pool", True)
            )
            if use_polite:
                params["mailto"] = self.user_email
            api_key = self.config.get("platforms", {}).get("openalex", {}).get("api_key", "")
            if api_key:
                params["api_key"] = api_key

            headers = {"User-Agent": f"{self.app_name}/2.0", "Accept": "application/json"}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("results"):
                for item in data["results"]:
                    candidate_title = item.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("openalex", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='OpenAlex')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"    {self.lang.get_text('access_denied_403', platform='OpenAlex')}")
            else:
                print(
                    f"    {self.lang.get_text('http_error', platform='OpenAlex', code=e.response.status_code)}"
                )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='OpenAlex', error=str(e)[:50])}"
            )
            return None
        except json.JSONDecodeError:
            print(f"    {self.lang.get_text('json_parse_error', platform='OpenAlex')}")
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='OpenAlex', error=str(e)[:50])}"
            )
            return None

    def query_semantic_scholar(self, title):
        try:
            base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            clean_title = self.clean_title(title)
            params = {
                "query": clean_title,
                "limit": 5,
                "fields": "title,authors,year,venue,doi,externalIds,publicationTypes,journal,publicationDate",
            }

            headers = {"User-Agent": f"{self.app_name}/2.0"}
            api_key = (
                self.config.get("platforms", {}).get("semantic_scholar", {}).get("api_key", "")
            )
            if api_key:
                headers["x-api-key"] = api_key

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("data"):
                for item in data["data"]:
                    candidate_title = item.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("semantic_scholar", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Semantic Scholar')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"    {self.lang.get_text('rate_limit_429', platform='Semantic Scholar')}")
            else:
                print(
                    f"    {self.lang.get_text('http_error', platform='Semantic Scholar', code=e.response.status_code)}"
                )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='Semantic Scholar', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='Semantic Scholar', error=str(e)[:50])}"
            )
            return None

    def query_dblp(self, title):
        try:
            base_url = "https://dblp.org/search/publ/api"
            clean_title = self.clean_title(title)
            params = {"q": clean_title, "format": "json", "h": 5}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if "result" in data and "hits" in data["result"] and "hit" in data["result"]["hits"]:
                for hit in data["result"]["hits"]["hit"]:
                    info = hit.get("info", {})
                    candidate_title = info.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("dblp", info)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='DBLP')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='DBLP', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='DBLP', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='DBLP', error=str(e)[:50])}")
            return None

    def query_pubmed(self, title):
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            clean_title = self.clean_title(title)
            params = {"db": "pubmed", "term": clean_title, "retmode": "json", "retmax": 5}
            api_key = self.config.get("platforms", {}).get("pubmed", {}).get("api_key", "")
            if api_key:
                params["api_key"] = api_key

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(search_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if "esearchresult" in data and "idlist" in data["esearchresult"]:
                pmids = data["esearchresult"]["idlist"]
                if pmids:
                    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    fetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
                    if api_key:
                        fetch_params["api_key"] = api_key

                    fetch_response = self.http.get(fetch_url, params=fetch_params, timeout=timeout)
                    fetch_response.raise_for_status()
                    fetch_data = fetch_response.json()

                    if "result" in fetch_data:
                        for pmid in pmids:
                            if pmid in fetch_data["result"]:
                                item = fetch_data["result"][pmid]
                                candidate_title = item.get("title", "")
                                if candidate_title and self.is_title_match(title, candidate_title):
                                    return ("pubmed", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='PubMed')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='PubMed', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='PubMed', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='PubMed', error=str(e)[:50])}"
            )
            return None

    def query_europe_pmc(self, title):
        try:
            base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            clean_title = self.clean_title(title)
            params = {"query": f'TITLE:"{clean_title}"', "format": "json", "pageSize": 5}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if "resultList" in data and "result" in data["resultList"]:
                for item in data["resultList"]["result"]:
                    candidate_title = item.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("europe_pmc", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Europe PMC')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='Europe PMC', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='Europe PMC', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='Europe PMC', error=str(e)[:50])}"
            )
            return None

    def query_core(self, title):
        try:
            base_url = "https://api.core.ac.uk/v3/search/works"
            clean_title = self.clean_title(title)
            params = {"q": f'title:"{clean_title}"', "limit": 5}
            headers = {"User-Agent": f"{self.app_name}/2.0"}
            api_key = self.config.get("platforms", {}).get("core", {}).get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if "results" in data:
                for item in data["results"]:
                    candidate_title = item.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("core", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='CORE')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"    {self.lang.get_text('auth_failed_401', platform='CORE')}")
            else:
                print(
                    f"    {self.lang.get_text('http_error', platform='CORE', code=e.response.status_code)}"
                )
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='CORE', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='CORE', error=str(e)[:50])}")
            return None

    def query_unpaywall(self, title, doi=None):
        if not doi:
            return None
        try:
            base_url = f"https://api.unpaywall.org/v2/{doi}"
            params = {"email": self.user_email}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("title"):
                if self.is_title_match(title, data["title"]):
                    return ("unpaywall", data)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Unpaywall')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                print(
                    f"    {self.lang.get_text('http_error', platform='Unpaywall', code=e.response.status_code)}"
                )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='Unpaywall', error=str(e)[:50])}"
            )
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='Unpaywall', error=str(e)[:50])}"
            )
            return None

    def query_base(self, title):
        try:
            base_url = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
            clean_title = self.clean_title(title)
            params = {
                "func": "PerformSearch",
                "query": f'dctitle:"{clean_title}"',
                "format": "json",
                "hits": 5,
            }

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if "response" in data and "docs" in data["response"]:
                for item in data["response"]["docs"]:
                    candidate_title = (
                        item.get("dctitle", [""])[0]
                        if isinstance(item.get("dctitle"), list)
                        else item.get("dctitle", "")
                    )
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("base", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='BASE')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='BASE', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='BASE', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='BASE', error=str(e)[:50])}")
            return None

    def query_biorxiv(self, title):
        try:
            base_url = "https://api.biorxiv.org/details/biorxiv"
            clean_title = self.clean_title(title)
            params = {"query": clean_title, "limit": 5}

            headers = {"User-Agent": f"{self.app_name}/2.0", "Accept": "application/json"}

            timeout = self.config.get("query_settings", {}).get("timeout", 10)
            response = self.http.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("collection"):
                for item in data["collection"]:
                    candidate_title = item.get("title", "")
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ("biorxiv", item)

            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='bioRxiv')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"    {self.lang.get_text('http_error', platform='bioRxiv', code=e.response.status_code)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            print(
                f"    {self.lang.get_text('network_error', platform='bioRxiv', error=str(e)[:50])}"
            )
            return None
        except json.JSONDecodeError:
            print(f"    {self.lang.get_text('json_parse_error', platform='bioRxiv')}")
            return None
        except Exception as e:
            print(
                f"    {self.lang.get_text('unknown_error', platform='bioRxiv', error=str(e)[:50])}"
            )
            return None

    def query_google_scholar(self, title):
        try:
            try:
                from scholarly import scholarly
            except ImportError:
                print(
                    f"    {self.lang.get_text('missing_optional_dependency', platform='Google Scholar', dependency='scholarly')}"
                )
                return None

            search_query = scholarly.search_pubs(self.clean_title(title))
            pub = next(search_query, None)

            if pub and self.is_title_match(title, pub["bib"].get("title", "")):
                return ("google_scholar", scholarly.bibtex(pub))

        except Exception as e:
            # Let the caller handle or just log it
            print(
                f"    {self.lang.get_text('platform_error', platform='Google Scholar', error=str(e)[:50])}"
            )

        return None

    def query_multi_platform(self, title, entry=None):
        stop_on_first = self.config.get("query_settings", {}).get("stop_on_first_match", True)
        best_result = None

        for platform in self._rank_platforms_for_entry(title, entry):
            try:
                print(f"    {self.lang.get_text('querying_platform', platform=platform.upper())}")

                if platform == "crossref":
                    doi = entry.get("doi", "") if entry else ""
                    result = self.query_crossref_by_doi(doi, title=title) if doi else None
                    if not result:
                        result = self.query_crossref(title)
                elif platform == "unpaywall":
                    print(
                        f"    {self.lang.get_text('skip_enrichment_only', platform=platform.upper())}"
                    )
                    continue
                else:
                    provider = self.provider_registry.get(platform)
                    if provider is None:
                        print(
                            f"    {self.lang.get_text('platform_not_implemented', platform=platform.upper())}"
                        )
                        continue
                    result = provider(title)

                if result:
                    print(f"    {self.lang.get_text('found_match', platform=platform.upper())}")
                    if stop_on_first:
                        return result
                    if best_result is None:
                        best_result = result
                else:
                    print(f"    {self.lang.get_text('not_found', platform=platform.upper())}")

            except Exception as e:
                print(
                    f"    {self.lang.get_text('platform_error', platform=platform.upper(), error=str(e)[:50])}"
                )

        return best_result
