import re
import json
import time
import requests
import bibtexparser
import os
import sys
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from datetime import datetime
import xml.etree.ElementTree as ET
import html
from scholarly import scholarly


class LanguageSupport:
    def __init__(self, language='CN'):
        self.language = language
        self.texts = {
            'CN': {
                'warning_config_not_found': '警告: 配置文件 {config_file} 不存在，使用默认配置',
                'loaded_entries': '已加载 {count} 条文献记录',
                'checking_entry': '[{current}/{total}] 正在检查: {key}',
                'original_title': '原标题: {title}',
                'querying_platform': '[{platform}] 查询中...',
                'found_match': '[{platform}] ✓ 找到匹配',
                'not_found': '[{platform}] ✗ 未找到',
                'skip_no_doi': '[{platform}] ✗ 跳过（需要 DOI）',
                'platform_not_implemented': '[{platform}] ✗ 平台未实现',
                'platform_error': '✗ {platform} 严重错误: {error}',
                'matched_title': '✓ 匹配到: {title}',
                'need_update': '→ 需要更新 ({count} 个字段有差异)',
                'verified_no_update': '→ 验证通过，无需更新',
                'all_platforms_no_match': '✗ 所有平台均未找到匹配',
                'unknown_platform': '✗ 未知平台: {platform}',
                'timeout': '{platform} 查询超时',
                'http_error': '{platform} HTTP 错误: {code}',
                'network_error': '{platform} 网络错误: {error}',
                'json_parse_error': '{platform} JSON 解析错误',
                'unknown_error': '{platform} 未知错误: {error}',
                'xml_parse_error': '{platform} XML 解析错误',
                'access_denied_403': '{platform} 访问被拒绝 (403) - 可能达到速率限制',
                'rate_limit_429': '{platform} 速率限制 - 建议添加 API key',
                'auth_failed_401': '{platform} 认证失败 - 请检查 API key',
                'not_found_404': '{platform} 未找到 (404)',
                'tool_title': 'Bibverify - BibTeX 文献检查工具',
                'enabled_platforms': '启用平台 ({count}): {platforms}',
                'start_verification': '开始验证文献...',
                'verification_complete': '检查完成！',
                'total_checked': '总计检查: {count} 条文献',
                'verified_passed': '✓ 验证通过: {count} 条',
                'need_update_count': '↻ 需要更新: {count} 条',
                'not_found_count': '✗ 未找到: {count} 条',
                'errors_count': '错误: {count} 条',
                'verified_sources': '验证通过的数据来源:',
                'update_sources': '更新数据的来源:',
                'generating_files': '正在生成文件...',
                'report_generated': '报告已生成: {file}',
                'backup_generated': '[1/3] 原始完整备份已生成: {file}',
                'updated_generated': '[2/3] 更新文献已生成: {file}',
                'updated_count': '包含: {count} 条找到并更新的文献',
                'no_update_skip': '[2/3] 无需更新的文献，跳过生成 updated 文件',
                'wrong_generated': '[3/3] 问题文献已生成: {file}',
                'wrong_count': '包含: {not_found} 条未找到 + {errors} 条错误',
                'no_wrong_skip': '[3/3] 无问题文献，跳过生成 wrong 文件'
            },
            'EN': {
                'warning_config_not_found': 'Warning: Configuration file {config_file} not found, using default config',
                'loaded_entries': 'Loaded {count} bibliographic entries',
                'checking_entry': '[{current}/{total}] Checking: {key}',
                'original_title': 'Original title: {title}',
                'querying_platform': '[{platform}] Querying...',
                'found_match': '[{platform}] ✓ Found match',
                'not_found': '[{platform}] ✗ Not found',
                'skip_no_doi': '[{platform}] ✗ Skip (DOI required)',
                'platform_not_implemented': '[{platform}] ✗ Platform not implemented',
                'platform_error': '✗ {platform} critical error: {error}',
                'matched_title': '✓ Matched: {title}',
                'need_update': '→ Need update ({count} fields differ)',
                'verified_no_update': '→ Verified, no update needed',
                'all_platforms_no_match': '✗ No match found on all platforms',
                'unknown_platform': '✗ Unknown platform: {platform}',
                'timeout': '{platform} query timeout',
                'http_error': '{platform} HTTP error: {code}',
                'network_error': '{platform} network error: {error}',
                'json_parse_error': '{platform} JSON parse error',
                'unknown_error': '{platform} unknown error: {error}',
                'xml_parse_error': '{platform} XML parse error',
                'access_denied_403': '{platform} access denied (403) - possibly rate limited',
                'rate_limit_429': '{platform} rate limit - recommend adding API key',
                'auth_failed_401': '{platform} authentication failed - please check API key',
                'not_found_404': '{platform} not found (404)',
                'tool_title': 'Bibverify - BibTeX Literature Checker',
                'enabled_platforms': 'Enabled platforms ({count}): {platforms}',
                'start_verification': 'Starting literature verification...',
                'verification_complete': 'Verification complete!',
                'total_checked': 'Total checked: {count} entries',
                'verified_passed': '✓ Verified: {count} entries',
                'need_update_count': '↻ Need update: {count} entries',
                'not_found_count': '✗ Not found: {count} entries',
                'errors_count': 'Errors: {count} entries',
                'verified_sources': 'Verified data sources:',
                'update_sources': 'Update data sources:',
                'generating_files': 'Generating files...',
                'report_generated': 'Report generated: {file}',
                'backup_generated': '[1/3] Original backup generated: {file}',
                'updated_generated': '[2/3] Updated entries generated: {file}',
                'updated_count': 'Contains: {count} found and updated entries',
                'no_update_skip': '[2/3] No updates needed, skipping updated file generation',
                'wrong_generated': '[3/3] Problem entries generated: {file}',
                'wrong_count': 'Contains: {not_found} not found + {errors} errors',
                'no_wrong_skip': '[3/3] No problem entries, skipping wrong file generation'
            }
        }
    
    def get_text(self, text_key, **kwargs):
        text = self.texts.get(self.language, self.texts['CN']).get(text_key, text_key)
        return text.format(**kwargs) if kwargs else text
    
    def get_platform_description(self, platform_config):
        description = platform_config.get('description', '')
        if self.language == 'EN':
            if ' / ' in description:
                return description.split(' / ')[1]
            else:
                return description
        else:
            if ' / ' in description:
                return description.split(' / ')[0]
            else:
                return description

class BibTeXChecker:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.bib_file = self.config.get('bib_file', 'sample.bib')
        self.file_encoding = 'utf-8'
        self.db = None
        self.results = {
            'verified': [],
            'updated': [],
            'not_found': [],
            'errors': []
        }
        self.user_email = self.config.get('user_info', {}).get('email', 'research@example.com')
        self.app_name = self.config.get('user_info', {}).get('app_name', 'Bibverify')
        self.enabled_platforms = self._get_enabled_platforms()
        
        language = self.config.get('language', 'CN')
        self.lang = LanguageSupport(language)
        
    def load_config(self, config_file):
        if not os.path.exists(config_file):
            print(f"警告: 配置文件 {config_file} 不存在，使用默认配置")
            return self._get_default_config()
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_default_config(self):
        return {
            'bib_file': 'sample.bib',
            'user_info': {
                'email': 'research@example.com',
                'app_name': 'Bibverify'
            },
            'platforms': {
                'google_scholar': {'enabled': True, 'priority': 0.5},
                'crossref': {'enabled': True, 'priority': 1, 'use_polite_pool': True},
                'arxiv': {'enabled': True, 'priority': 2},
                'openalex': {'enabled': True, 'priority': 3, 'use_polite_pool': True}
            },
            'query_settings': {
                'delay_between_requests': 0.5,
                'timeout': 10,
                'max_retries': 3,
                'stop_on_first_match': True
            }
        }
    
    def _get_enabled_platforms(self):
        platforms = self.config.get('platforms', {})
        enabled = []
        for name, settings in platforms.items():
            if settings.get('enabled', False):
                enabled.append((name, settings.get('priority', 999)))
        enabled.sort(key=lambda x: x[1])
        return [name for name, _ in enabled]
    
    def load_bib_file(self):
        encodings = ['utf-8', 'gbk', 'gb18030', 'latin1']
        success = False
        
        for encoding in encodings:
            try:
                with open(self.bib_file, 'r', encoding=encoding) as bibfile:
                    parser = BibTexParser(common_strings=True)
                    parser.ignore_nonstandard_types = False
                    self.db = bibtexparser.load(bibfile, parser)
                success = True
                self.file_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Warning: Failed to load with encoding {encoding}: {e}")
                continue
        
        if not success:
            raise ValueError(f"无法加载文件 {self.bib_file}。请检查文件编码 (尝试了: {', '.join(encodings)})")

        print(self.lang.get_text('loaded_entries', count=len(self.db.entries)))
    
    def clean_title(self, title):
        title = re.sub(r'\{|\}', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    def normalize_title(self, title):
        title = self.clean_title(title)
        title = title.lower()
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    def normalize_for_comparison(self, title):
        title = self.normalize_title(title)
        title = re.sub(r'[^\w\s]', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    def is_title_match(self, original_title, candidate_title):
        norm_original = self.normalize_for_comparison(original_title)
        norm_candidate = self.normalize_for_comparison(candidate_title)
        
        if norm_original == norm_candidate:
            return True
        
        if norm_original in norm_candidate:
            return True
        
        return False
    
    def query_crossref(self, title):
        try:
            base_url = "https://api.crossref.org/works"
            clean_title = self.clean_title(title)
            params = {
                'query.title': clean_title,
                'rows': 5
            }
            use_polite = self.config.get('platforms', {}).get('crossref', {}).get('use_polite_pool', True)
            user_agent = f'{self.app_name}/2.0 (mailto:{self.user_email})' if use_polite else f'{self.app_name}/2.0'
            headers = {
                'User-Agent': user_agent
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if data['message']['items']:
                for item in data['message']['items']:
                    if 'title' in item and item['title']:
                        candidate_title = item['title'][0]
                        if self.is_title_match(title, candidate_title):
                            return ('crossref', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='CrossRef')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='CrossRef', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='CrossRef', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='CrossRef', error=str(e)[:50])}")
            return None
    
    def query_arxiv(self, title):
        try:
            base_url = "http://export.arxiv.org/api/query"
            clean_title = self.clean_title(title)
            params = {
                'search_query': f'ti:"{clean_title}"',
                'max_results': 5
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', namespace)
            
            for entry in entries:
                title_elem = entry.find('atom:title', namespace)
                if title_elem is not None:
                    candidate_title = title_elem.text.strip().replace('\n', ' ')
                    if self.is_title_match(title, candidate_title):
                        return ('arxiv', entry, namespace)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='arXiv')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='arXiv', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='arXiv', error=str(e)[:50])}")
            return None
        except ET.ParseError as e:
            print(f"    {self.lang.get_text('xml_parse_error', platform='arXiv')}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='arXiv', error=str(e)[:50])}")
            return None
    
    def query_openalex(self, title):
        try:
            base_url = "https://api.openalex.org/works"
            clean_title = self.clean_title(title)
            params = {
                'filter': f'title.search:{clean_title}',
                'per_page': 5
            }
            use_polite = self.config.get('platforms', {}).get('openalex', {}).get('use_polite_pool', True)
            if use_polite:
                params['mailto'] = self.user_email
            
            headers = {
                'User-Agent': f'{self.app_name}/2.0',
                'Accept': 'application/json'
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and data['results']:
                for item in data['results']:
                    candidate_title = item.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('openalex', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='OpenAlex')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"    {self.lang.get_text('access_denied_403', platform='OpenAlex')}")
            else:
                print(f"    {self.lang.get_text('http_error', platform='OpenAlex', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='OpenAlex', error=str(e)[:50])}")
            return None
        except json.JSONDecodeError:
            print(f"    {self.lang.get_text('json_parse_error', platform='OpenAlex')}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='OpenAlex', error=str(e)[:50])}")
            return None
    
    def query_semantic_scholar(self, title):
        try:
            base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            clean_title = self.clean_title(title)
            params = {
                'query': clean_title,
                'limit': 5,
                'fields': 'title,authors,year,venue,doi,externalIds,publicationTypes,journal,publicationDate'
            }
            
            headers = {'User-Agent': f'{self.app_name}/2.0'}
            api_key = self.config.get('platforms', {}).get('semantic_scholar', {}).get('api_key', '')
            if api_key:
                headers['x-api-key'] = api_key
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                for item in data['data']:
                    candidate_title = item.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('semantic_scholar', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Semantic Scholar')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"    {self.lang.get_text('rate_limit_429', platform='Semantic Scholar')}")
            else:
                print(f"    {self.lang.get_text('http_error', platform='Semantic Scholar', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='Semantic Scholar', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='Semantic Scholar', error=str(e)[:50])}")
            return None
    
    def query_dblp(self, title):
        try:
            base_url = "https://dblp.org/search/publ/api"
            clean_title = self.clean_title(title)
            params = {
                'q': clean_title,
                'format': 'json',
                'h': 5
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'result' in data and 'hits' in data['result'] and 'hit' in data['result']['hits']:
                for hit in data['result']['hits']['hit']:
                    info = hit.get('info', {})
                    candidate_title = info.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('dblp', info)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='DBLP')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='DBLP', code=e.response.status_code)}")
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
            params = {
                'db': 'pubmed',
                'term': clean_title,
                'retmode': 'json',
                'retmax': 5
            }
            api_key = self.config.get('platforms', {}).get('pubmed', {}).get('api_key', '')
            if api_key:
                params['api_key'] = api_key
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(search_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'esearchresult' in data and 'idlist' in data['esearchresult']:
                pmids = data['esearchresult']['idlist']
                if pmids:
                    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    fetch_params = {
                        'db': 'pubmed',
                        'id': ','.join(pmids),
                        'retmode': 'json'
                    }
                    if api_key:
                        fetch_params['api_key'] = api_key
                    
                    fetch_response = requests.get(fetch_url, params=fetch_params, timeout=timeout)
                    fetch_response.raise_for_status()
                    fetch_data = fetch_response.json()
                    
                    if 'result' in fetch_data:
                        for pmid in pmids:
                            if pmid in fetch_data['result']:
                                item = fetch_data['result'][pmid]
                                candidate_title = item.get('title', '')
                                if candidate_title and self.is_title_match(title, candidate_title):
                                    return ('pubmed', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='PubMed')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='PubMed', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='PubMed', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='PubMed', error=str(e)[:50])}")
            return None
    
    def query_europe_pmc(self, title):
        try:
            base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            clean_title = self.clean_title(title)
            params = {
                'query': f'TITLE:"{clean_title}"',
                'format': 'json',
                'pageSize': 5
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'resultList' in data and 'result' in data['resultList']:
                for item in data['resultList']['result']:
                    candidate_title = item.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('europe_pmc', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Europe PMC')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='Europe PMC', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='Europe PMC', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='Europe PMC', error=str(e)[:50])}")
            return None
    
    def query_core(self, title):
        try:
            base_url = "https://api.core.ac.uk/v3/search/works"
            clean_title = self.clean_title(title)
            params = {
                'q': f'title:"{clean_title}"',
                'limit': 5
            }
            headers = {'User-Agent': f'{self.app_name}/2.0'}
            api_key = self.config.get('platforms', {}).get('core', {}).get('api_key', '')
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data:
                for item in data['results']:
                    candidate_title = item.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('core', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='CORE')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"    {self.lang.get_text('auth_failed_401', platform='CORE')}")
            else:
                print(f"    {self.lang.get_text('http_error', platform='CORE', code=e.response.status_code)}")
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
            params = {'email': self.user_email}
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('title'):
                if self.is_title_match(title, data['title']):
                    return ('unpaywall', data)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='Unpaywall')}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                print(f"    {self.lang.get_text('http_error', platform='Unpaywall', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='Unpaywall', error=str(e)[:50])}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='Unpaywall', error=str(e)[:50])}")
            return None
    
    def query_base(self, title):
        try:
            base_url = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
            clean_title = self.clean_title(title)
            params = {
                'func': 'PerformSearch',
                'query': f'dctitle:"{clean_title}"',
                'format': 'json',
                'hits': 5
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data and 'docs' in data['response']:
                for item in data['response']['docs']:
                    candidate_title = item.get('dctitle', [''])[0] if isinstance(item.get('dctitle'), list) else item.get('dctitle', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('base', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='BASE')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='BASE', code=e.response.status_code)}")
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
            params = {
                'query': clean_title,
                'limit': 5
            }
            
            headers = {
                'User-Agent': f'{self.app_name}/2.0',
                'Accept': 'application/json'
            }
            
            timeout = self.config.get('query_settings', {}).get('timeout', 10)
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'collection' in data and data['collection']:
                for item in data['collection']:
                    candidate_title = item.get('title', '')
                    if candidate_title and self.is_title_match(title, candidate_title):
                        return ('biorxiv', item)
            
            return None
        except requests.exceptions.Timeout:
            print(f"    {self.lang.get_text('timeout', platform='bioRxiv')}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"    {self.lang.get_text('http_error', platform='bioRxiv', code=e.response.status_code)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"    {self.lang.get_text('network_error', platform='bioRxiv', error=str(e)[:50])}")
            return None
        except json.JSONDecodeError:
            print(f"    {self.lang.get_text('json_parse_error', platform='bioRxiv')}")
            return None
        except Exception as e:
            print(f"    {self.lang.get_text('unknown_error', platform='bioRxiv', error=str(e)[:50])}")
            return None

    def query_google_scholar(self, title):
        try:
            search_query = scholarly.search_pubs(self.clean_title(title))
            pub = next(search_query, None)
            
            if pub and self.is_title_match(title, pub['bib'].get('title', '')):
                return ('google_scholar', scholarly.bibtex(pub))
                
        except Exception as e:
            # Let the caller handle or just log it
            print(f"    {self.lang.get_text('platform_error', platform='Google Scholar', error=str(e)[:50])}")
            
        return None

    
    def query_multi_platform(self, title, entry=None):
        stop_on_first = self.config.get('query_settings', {}).get('stop_on_first_match', True)
        
        for platform in self.enabled_platforms:
            try:
                print(f"    {self.lang.get_text('querying_platform', platform=platform.upper())}")
                
                if platform == 'crossref':
                    result = self.query_crossref(title)
                elif platform == 'arxiv':
                    result = self.query_arxiv(title)
                elif platform == 'openalex':
                    result = self.query_openalex(title)
                elif platform == 'semantic_scholar':
                    result = self.query_semantic_scholar(title)
                elif platform == 'dblp':
                    result = self.query_dblp(title)
                elif platform == 'pubmed':
                    result = self.query_pubmed(title)
                elif platform == 'europe_pmc':
                    result = self.query_europe_pmc(title)
                elif platform == 'core':
                    result = self.query_core(title)
                elif platform == 'unpaywall':
                    doi = entry.get('doi', '') if entry else None
                    if doi:
                        result = self.query_unpaywall(title, doi)
                    else:
                        print(f"    {self.lang.get_text('skip_no_doi', platform=platform.upper())}")
                        continue
                elif platform == 'base':
                    result = self.query_base(title)
                elif platform == 'biorxiv':
                    result = self.query_biorxiv(title)
                elif platform == 'google_scholar':
                    result = self.query_google_scholar(title)
                else:
                    print(f"    {self.lang.get_text('platform_not_implemented', platform=platform.upper())}")
                    continue
                
                if result:
                        print(f"    {self.lang.get_text('found_match', platform=platform.upper())}")
                        if stop_on_first:
                            return result
                        else:
                            print(f"    {self.lang.get_text('not_found', platform=platform.upper())}")
                
            except Exception as e:
                print(f"    {self.lang.get_text('platform_error', platform=platform.upper(), error=str(e)[:50])}")
        
        return None
    
    def format_field_value(self, value, protect_case=True):
        if value is None:
            return ''
        value = str(value).strip()
        # 解码 HTML 实体 (如 &amp; -> &)
        value = html.unescape(value)
        
        if not value:
            return ''
        value = re.sub(r'\{+', '{', value)
        value = re.sub(r'\}+', '}', value)
        value = value.strip('{}')
        
        if protect_case:
            return '{{' + value + '}}'
        return value
    
    def clean_entry(self, entry):
        """清理条目，移除空值和None值"""
        cleaned = {}
        for key, value in entry.items():
            if value is not None and str(value).strip():
                cleaned[key] = str(value).strip()
        return cleaned
    
    def clean_entry_for_writing(self, entry):
        """为写入 BibTeX 清理条目，确保所有字段都是字符串"""
        cleaned = {}
        for key, value in entry.items():
            if value is None:
                # 跳过 None 值，不添加到输出中
                continue
            elif isinstance(value, str):
                # 字符串值，去除首尾空格
                cleaned_value = value.strip()
                if cleaned_value:  # 只添加非空字符串
                    cleaned[key] = cleaned_value
            else:
                # 其他类型，转换为字符串
                cleaned_value = str(value).strip()
                if cleaned_value:  # 只添加非空字符串
                    cleaned[key] = cleaned_value
        return cleaned
    
    def semantic_scholar_to_bibtex(self, ss_data, original_key):
        entry = {'ID': original_key}
        
        pub_types = ss_data.get('publicationTypes', [])
        if 'JournalArticle' in pub_types:
            entry['ENTRYTYPE'] = 'article'
        elif 'Conference' in pub_types:
            entry['ENTRYTYPE'] = 'inproceedings'
        else:
            entry['ENTRYTYPE'] = 'article'
        
        if 'title' in ss_data and ss_data['title']:
            entry['title'] = self.format_field_value(ss_data['title'], protect_case=True)
        
        if 'authors' in ss_data and ss_data['authors']:
            authors = [author.get('name', '') for author in ss_data['authors'] if author.get('name')]
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'year' in ss_data and ss_data['year']:
            entry['year'] = str(ss_data['year'])
        
        if 'venue' in ss_data and ss_data['venue']:
            if entry['ENTRYTYPE'] == 'article':
                entry['journal'] = self.format_field_value(ss_data['venue'], protect_case=True)
            elif entry['ENTRYTYPE'] == 'inproceedings':
                entry['booktitle'] = self.format_field_value(ss_data['venue'], protect_case=True)
        
        if 'journal' in ss_data and ss_data['journal'] and 'name' in ss_data['journal']:
            entry['journal'] = self.format_field_value(ss_data['journal']['name'], protect_case=True)
        
        if 'doi' in ss_data and ss_data['doi']:
            entry['doi'] = ss_data['doi']
        
        if 'externalIds' in ss_data:
            ext_ids = ss_data['externalIds']
            if 'ArXiv' in ext_ids:
                entry['eprint'] = ext_ids['ArXiv']
                entry['archiveprefix'] = 'arXiv'
        
        return self.clean_entry(entry)
    
    def dblp_to_bibtex(self, dblp_data, original_key):
        entry = {'ID': original_key}
        
        entry_type = dblp_data.get('type', 'article')
        type_mapping = {
            'Conference and Workshop Papers': 'inproceedings',
            'Journal Articles': 'article',
            'Informal Publications': 'article',
            'Parts in Books or Collections': 'incollection'
        }
        entry['ENTRYTYPE'] = type_mapping.get(entry_type, 'article')
        
        if 'title' in dblp_data and dblp_data['title']:
            entry['title'] = self.format_field_value(dblp_data['title'], protect_case=True)
        
        if 'authors' in dblp_data:
            authors_data = dblp_data['authors'].get('author', [])
            if not isinstance(authors_data, list):
                authors_data = [authors_data]
            authors = [a.get('text', '') for a in authors_data if a.get('text')]
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'year' in dblp_data:
            entry['year'] = str(dblp_data['year'])
        
        if 'venue' in dblp_data and dblp_data['venue']:
            if entry['ENTRYTYPE'] == 'article':
                entry['journal'] = self.format_field_value(dblp_data['venue'], protect_case=True)
            elif entry['ENTRYTYPE'] == 'inproceedings':
                entry['booktitle'] = self.format_field_value(dblp_data['venue'], protect_case=True)
        
        if 'volume' in dblp_data:
            entry['volume'] = str(dblp_data['volume'])
        
        if 'pages' in dblp_data:
            entry['pages'] = dblp_data['pages'].replace('-', '--')
        
        if 'doi' in dblp_data:
            entry['doi'] = dblp_data['doi']
        
        if 'ee' in dblp_data:
            entry['url'] = dblp_data['ee']
        
        return self.clean_entry(entry)
    
    def pubmed_to_bibtex(self, pubmed_data, original_key):
        entry = {'ID': original_key}
        entry['ENTRYTYPE'] = 'article'
        
        if 'title' in pubmed_data and pubmed_data['title']:
            entry['title'] = self.format_field_value(pubmed_data['title'], protect_case=True)
        
        if 'authors' in pubmed_data:
            authors = []
            for author in pubmed_data['authors']:
                name = author.get('name', '')
                if name:
                    authors.append(name)
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'pubdate' in pubmed_data:
            pubdate = pubmed_data['pubdate']
            year_match = re.search(r'\d{4}', pubdate)
            if year_match:
                entry['year'] = year_match.group(0)
        
        if 'fulljournalname' in pubmed_data and pubmed_data['fulljournalname']:
            entry['journal'] = self.format_field_value(pubmed_data['fulljournalname'], protect_case=True)
        elif 'source' in pubmed_data and pubmed_data['source']:
            entry['journal'] = self.format_field_value(pubmed_data['source'], protect_case=True)
        
        if 'volume' in pubmed_data:
            entry['volume'] = str(pubmed_data['volume'])
        
        if 'issue' in pubmed_data:
            entry['number'] = str(pubmed_data['issue'])
        
        if 'pages' in pubmed_data:
            entry['pages'] = pubmed_data['pages'].replace('-', '--')
        
        if 'elocationid' in pubmed_data:
            doi_match = re.search(r'doi:\s*(.+)', pubmed_data['elocationid'])
            if doi_match:
                entry['doi'] = doi_match.group(1)
        
        if 'articleids' in pubmed_data:
            for article_id in pubmed_data['articleids']:
                if article_id.get('idtype') == 'doi':
                    entry['doi'] = article_id.get('value', '')
                elif article_id.get('idtype') == 'pubmed':
                    entry['pmid'] = article_id.get('value', '')
        
        return self.clean_entry(entry)
    
    def europe_pmc_to_bibtex(self, epmc_data, original_key):
        entry = {'ID': original_key}
        entry['ENTRYTYPE'] = 'article'
        
        if 'title' in epmc_data and epmc_data['title']:
            entry['title'] = self.format_field_value(epmc_data['title'], protect_case=True)
        
        if 'authorString' in epmc_data and epmc_data['authorString']:
            authors = epmc_data['authorString'].split(', ')
            entry['author'] = ' and '.join(authors)
        
        if 'pubYear' in epmc_data:
            entry['year'] = str(epmc_data['pubYear'])
        
        if 'journalTitle' in epmc_data and epmc_data['journalTitle']:
            entry['journal'] = self.format_field_value(epmc_data['journalTitle'], protect_case=True)
        
        if 'journalVolume' in epmc_data:
            entry['volume'] = str(epmc_data['journalVolume'])
        
        if 'issue' in epmc_data:
            entry['number'] = str(epmc_data['issue'])
        
        if 'pageInfo' in epmc_data:
            entry['pages'] = epmc_data['pageInfo'].replace('-', '--')
        
        if 'doi' in epmc_data:
            entry['doi'] = epmc_data['doi']
        
        if 'pmid' in epmc_data:
            entry['pmid'] = epmc_data['pmid']
        
        return self.clean_entry(entry)
    
    def core_to_bibtex(self, core_data, original_key):
        entry = {'ID': original_key}
        entry['ENTRYTYPE'] = 'article'
        
        if 'title' in core_data and core_data['title']:
            entry['title'] = self.format_field_value(core_data['title'], protect_case=True)
        
        if 'authors' in core_data:
            authors = [author.get('name', '') for author in core_data['authors'] if author.get('name')]
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'yearPublished' in core_data:
            entry['year'] = str(core_data['yearPublished'])
        elif 'publishedDate' in core_data:
            year_match = re.search(r'\d{4}', core_data['publishedDate'])
            if year_match:
                entry['year'] = year_match.group(0)
        
        if 'journals' in core_data and core_data['journals']:
            entry['journal'] = self.format_field_value(core_data['journals'][0], protect_case=True)
        
        if 'doi' in core_data:
            entry['doi'] = core_data['doi']
        
        if 'downloadUrl' in core_data:
            entry['url'] = core_data['downloadUrl']
        
        return self.clean_entry(entry)
    
    def arxiv_to_bibtex(self, arxiv_entry, namespace, original_key):
        entry = {'ID': original_key}
        entry['ENTRYTYPE'] = 'article'
        
        title_elem = arxiv_entry.find('atom:title', namespace)
        if title_elem is not None:
            title_text = title_elem.text.strip().replace('\n', ' ')
            entry['title'] = self.format_field_value(title_text, protect_case=True)
        
        authors = []
        for author_elem in arxiv_entry.findall('atom:author', namespace):
            name_elem = author_elem.find('atom:name', namespace)
            if name_elem is not None:
                authors.append(name_elem.text.strip())
        if authors:
            entry['author'] = ' and '.join(authors)
        
        published_elem = arxiv_entry.find('atom:published', namespace)
        if published_elem is not None:
            year = published_elem.text.strip()[:4]
            entry['year'] = year
        
        arxiv_id = None
        arxiv_id_elem = arxiv_entry.find('atom:id', namespace)
        if arxiv_id_elem is not None:
            arxiv_url = arxiv_id_elem.text.strip()
            arxiv_id = arxiv_url.split('/')[-1]
            arxiv_id_base = re.sub(r'v\d+$', '', arxiv_id)
            entry['eprint'] = arxiv_id
            entry['archiveprefix'] = 'arXiv'
        
        primary_category = arxiv_entry.find('arxiv:primary_category', {'arxiv': 'http://arxiv.org/schemas/atom'})
        if primary_category is not None:
            entry['primaryclass'] = primary_category.get('term', '')
        
        journal_elem = arxiv_entry.find('arxiv:journal_ref', {'arxiv': 'http://arxiv.org/schemas/atom'})
        if journal_elem is not None and journal_elem.text:
            entry['journal'] = self.format_field_value(journal_elem.text.strip(), protect_case=True)
        else:
            entry['journal'] = self.format_field_value('arXiv', protect_case=True)
        
        doi_elem = arxiv_entry.find('arxiv:doi', {'arxiv': 'http://arxiv.org/schemas/atom'})
        if doi_elem is not None and doi_elem.text:
            entry['doi'] = doi_elem.text.strip()
        elif arxiv_id:
            arxiv_id_base = re.sub(r'v\d+$', '', arxiv_id)
            entry['doi'] = f'10.48550/arxiv.{arxiv_id_base}'
        
        return self.clean_entry(entry)
    
    def openalex_to_bibtex(self, openalex_data, original_key):
        entry = {'ID': original_key}
        
        work_type = openalex_data.get('type', 'article')
        type_mapping = {
            'journal-article': 'article',
            'book-chapter': 'incollection',
            'book': 'book',
            'proceedings-article': 'inproceedings',
            'article': 'article'
        }
        entry['ENTRYTYPE'] = type_mapping.get(work_type, 'article')
        
        if 'title' in openalex_data and openalex_data['title']:
            entry['title'] = self.format_field_value(openalex_data['title'], protect_case=True)
        
        if 'authorships' in openalex_data and openalex_data['authorships']:
            authors = []
            for authorship in openalex_data['authorships']:
                if 'author' in authorship and authorship['author']:
                    author_name = authorship['author'].get('display_name', '')
                    if author_name:
                        authors.append(author_name)
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'publication_year' in openalex_data and openalex_data['publication_year']:
            entry['year'] = str(openalex_data['publication_year'])
        
        if 'primary_location' in openalex_data and openalex_data['primary_location']:
            location = openalex_data['primary_location']
            if 'source' in location and location['source']:
                source = location['source']
                if source.get('display_name'):
                    if entry['ENTRYTYPE'] == 'article':
                        entry['journal'] = self.format_field_value(source['display_name'], protect_case=True)
                    elif entry['ENTRYTYPE'] == 'inproceedings':
                        entry['booktitle'] = self.format_field_value(source['display_name'], protect_case=True)
        
        if 'biblio' in openalex_data and openalex_data['biblio']:
            biblio = openalex_data['biblio']
            if biblio.get('volume'):
                entry['volume'] = str(biblio['volume'])
            if biblio.get('issue'):
                entry['number'] = str(biblio['issue'])
            if biblio.get('first_page') and biblio.get('last_page'):
                entry['pages'] = f"{biblio['first_page']}--{biblio['last_page']}"
            elif biblio.get('first_page'):
                entry['pages'] = str(biblio['first_page'])
        
        if 'doi' in openalex_data and openalex_data['doi']:
            doi = openalex_data['doi'].replace('https://doi.org/', '')
            entry['doi'] = doi
        
        if 'host_organization' in openalex_data and openalex_data.get('host_organization'):
            entry['publisher'] = openalex_data['host_organization'].get('display_name', '')
        
        return self.clean_entry(entry)
    
    def crossref_to_bibtex(self, crossref_data, original_key):
        entry = {'ID': original_key}
        
        entry_type = crossref_data.get('type', 'article')
        type_mapping = {
            'journal-article': 'article',
            'book-chapter': 'incollection',
            'book': 'book',
            'proceedings-article': 'inproceedings',
            'posted-content': 'unpublished'
        }
        entry['ENTRYTYPE'] = type_mapping.get(entry_type, 'article')
        
        if 'title' in crossref_data and crossref_data['title']:
            entry['title'] = self.format_field_value(crossref_data['title'][0], protect_case=True)
        
        if 'author' in crossref_data:
            authors = []
            for author in crossref_data['author']:
                if 'family' in author:
                    if 'given' in author:
                        author_name = f"{author['family']}, {author['given']}"
                    else:
                        author_name = author['family']
                    authors.append(author_name)
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'published' in crossref_data:
            date_parts = crossref_data['published'].get('date-parts', [[]])[0]
            if date_parts:
                entry['year'] = str(date_parts[0])
        elif 'published-print' in crossref_data:
            date_parts = crossref_data['published-print'].get('date-parts', [[]])[0]
            if date_parts:
                entry['year'] = str(date_parts[0])
        
        if 'container-title' in crossref_data and crossref_data['container-title']:
            container = crossref_data['container-title'][0]
            if entry['ENTRYTYPE'] == 'article':
                entry['journal'] = self.format_field_value(container, protect_case=True)
            elif entry['ENTRYTYPE'] == 'inproceedings':
                entry['booktitle'] = self.format_field_value(container, protect_case=False)
        
        if 'volume' in crossref_data:
            entry['volume'] = str(crossref_data['volume'])
        
        if 'issue' in crossref_data:
            entry['number'] = str(crossref_data['issue'])
        
        if 'page' in crossref_data:
            entry['pages'] = crossref_data['page'].replace('-', '--')
        
        if 'publisher' in crossref_data:
            entry['publisher'] = crossref_data['publisher']
        
        if 'DOI' in crossref_data:
            entry['doi'] = crossref_data['DOI']
        
        return self.clean_entry(entry)
    
    def biorxiv_to_bibtex(self, biorxiv_data, original_key):
        entry = {'ID': original_key}
        entry['ENTRYTYPE'] = 'article'
        
        if 'title' in biorxiv_data and biorxiv_data['title']:
            entry['title'] = self.format_field_value(biorxiv_data['title'], protect_case=True)
        
        if 'authors' in biorxiv_data and biorxiv_data['authors']:
            authors = []
            for author in biorxiv_data['authors']:
                if isinstance(author, dict):
                    name = author.get('name', '')
                else:
                    name = str(author)
                if name:
                    authors.append(name)
            if authors:
                entry['author'] = ' and '.join(authors)
        
        if 'date' in biorxiv_data and biorxiv_data['date']:
            date_str = biorxiv_data['date']
            year_match = re.search(r'\d{4}', date_str)
            if year_match:
                entry['year'] = year_match.group(0)
        
        if 'journal' in biorxiv_data and biorxiv_data['journal']:
            entry['journal'] = self.format_field_value(biorxiv_data['journal'], protect_case=True)
        else:
            entry['journal'] = self.format_field_value('bioRxiv', protect_case=True)
        
        if 'doi' in biorxiv_data and biorxiv_data['doi']:
            entry['doi'] = biorxiv_data['doi']
        
        if 'biorxiv_url' in biorxiv_data and biorxiv_data['biorxiv_url']:
            entry['url'] = biorxiv_data['biorxiv_url']
        
        if 'preprint_url' in biorxiv_data and biorxiv_data['preprint_url']:
            entry['url'] = biorxiv_data['preprint_url']
        
        if 'version' in biorxiv_data and biorxiv_data['version']:
            entry['note'] = f"Version {biorxiv_data['version']}"
        
        if 'category' in biorxiv_data and biorxiv_data['category']:
            entry['keywords'] = biorxiv_data['category']
        
        return self.clean_entry(entry)
    
    def clean_bibtex_braces(self, bibtex_str):
        """
        Remove double curly braces {{...}} from BibTeX string.
        """
        lines = bibtex_str.split('\n')
        cleaned_lines = []
        for line in lines:
            # Match field assignment: key = {{value}} or key = {{value}},
            match = re.search(r'(\s*\w+\s*=\s*)\{\{(.*?)\}\}(,?.*)', line)
            if match:
                prefix = match.group(1)
                content = match.group(2)
                suffix = match.group(3)
                # Reconstruct with single braces
                cleaned_line = f"{prefix}{{{content}}}{suffix}"
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def google_scholar_to_bibtex(self, bibtex_str, original_key):
        # Clean braces first
        cleaned_bibtex_str = self.clean_bibtex_braces(bibtex_str)
        parser = BibTexParser(common_strings=True)
        
        try:
            db = bibtexparser.loads(cleaned_bibtex_str, parser)
        except Exception:
            try:
                db = bibtexparser.loads(bibtex_str, parser)
            except:
                return {'ID': original_key, 'ENTRYTYPE': 'misc', 'note': 'Failed to parse'}

        if not db.entries:
            return {'ID': original_key, 'ENTRYTYPE': 'misc'}
            
        entry = db.entries[0]
        result = {'ID': original_key, 'ENTRYTYPE': entry.get('ENTRYTYPE', 'article')}
        
        for key, value in entry.items():
            if key not in ['ID', 'ENTRYTYPE']:
                result[key] = self.format_field_value(value, protect_case=True)
            
        return self.clean_entry(result)

    
    def compare_entries(self, original, updated):
        differences = {}
        all_keys = set(original.keys()) | set(updated.keys())
        
        for key in all_keys:
            if key in ['ID']:
                continue
            
            orig_val = str(original.get(key, '') or '').strip()
            upd_val = str(updated.get(key, '') or '').strip()
            
            orig_val_clean = re.sub(r'\{|\}', '', orig_val).lower()
            upd_val_clean = re.sub(r'\{|\}', '', upd_val).lower()
            
            if orig_val_clean != upd_val_clean:
                differences[key] = {
                    'original': orig_val,
                    'updated': upd_val
                }
        
        return differences
    
    def check_all_entries(self):
        total = len(self.db.entries)
        
        for idx, entry in enumerate(self.db.entries, 1):
            entry_key = entry['ID']
            title = entry.get('title', '')
            
            print(f"\n{self.lang.get_text('checking_entry', current=idx, total=total, key=entry_key)}")
            print(f"  {self.lang.get_text('original_title', title=self.clean_title(title))}")
            
            query_result = self.query_multi_platform(title, entry)
            
            if query_result:
                platform = query_result[0]
                
                if platform == 'crossref':
                    crossref_data = query_result[1]
                    matched_title = crossref_data.get('title', [''])[0]
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.crossref_to_bibtex(crossref_data, entry_key)
                elif platform == 'arxiv':
                    arxiv_entry = query_result[1]
                    namespace = query_result[2]
                    title_elem = arxiv_entry.find('atom:title', namespace)
                    matched_title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else ''
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.arxiv_to_bibtex(arxiv_entry, namespace, entry_key)
                elif platform == 'openalex':
                    openalex_data = query_result[1]
                    matched_title = openalex_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.openalex_to_bibtex(openalex_data, entry_key)
                elif platform == 'semantic_scholar':
                    ss_data = query_result[1]
                    matched_title = ss_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.semantic_scholar_to_bibtex(ss_data, entry_key)
                elif platform == 'dblp':
                    dblp_data = query_result[1]
                    matched_title = dblp_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.dblp_to_bibtex(dblp_data, entry_key)
                elif platform == 'pubmed':
                    pubmed_data = query_result[1]
                    matched_title = pubmed_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.pubmed_to_bibtex(pubmed_data, entry_key)
                elif platform == 'europe_pmc':
                    epmc_data = query_result[1]
                    matched_title = epmc_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.europe_pmc_to_bibtex(epmc_data, entry_key)
                elif platform == 'core':
                    core_data = query_result[1]
                    matched_title = core_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.core_to_bibtex(core_data, entry_key)
                elif platform == 'biorxiv':
                    biorxiv_data = query_result[1]
                    matched_title = biorxiv_data.get('title', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.biorxiv_to_bibtex(biorxiv_data, entry_key)
                elif platform == 'google_scholar':
                    bibtex_str = query_result[1]
                    updated_entry = self.google_scholar_to_bibtex(bibtex_str, entry_key)
                    matched_title = updated_entry.get('title', '').replace('{', '').replace('}', '')
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                else:
                    print(f"  {self.lang.get_text('unknown_platform', platform=platform)}")
                    self.results['errors'].append({
                        'key': entry_key,
                        'title': title,
                        'entry': entry,
                        'error': f"未知平台: {platform}"
                    })
                    continue
                
                differences = self.compare_entries(entry, updated_entry)
                
                if differences:
                    print(f"  {self.lang.get_text('need_update', count=len(differences))}")
                    self.results['updated'].append({
                        'key': entry_key,
                        'original': entry,
                        'updated': updated_entry,
                        'differences': differences,
                        'platform': platform
                    })
                else:
                    print(f"  {self.lang.get_text('verified_no_update')}")
                    self.results['verified'].append({
                        'key': entry_key,
                        'entry': entry,
                        'platform': platform
                    })
            else:
                print(f"  {self.lang.get_text('all_platforms_no_match')}")
                self.results['not_found'].append({
                    'key': entry_key,
                    'title': title,
                    'entry': entry
                })
            
            delay = self.config.get('query_settings', {}).get('delay_between_requests', 0.5)
            time.sleep(delay)
    
    def generate_report(self):
        timestamp_format = self.config.get('output_settings', {}).get('timestamp_format', '%Y%m%d_%H%M%S')
        timestamp = datetime.now().strftime(timestamp_format)
        report_file = f'bib_check_report_{timestamp}.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("BibTeX 文献检查报告 - 全平台版\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"启用平台: {', '.join([p.upper() for p in self.enabled_platforms])}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"总计检查: {len(self.db.entries)} 条文献\n")
            f.write(f"验证通过: {len(self.results['verified'])} 条\n")
            f.write(f"需要更新: {len(self.results['updated'])} 条\n")
            f.write(f"未找到: {len(self.results['not_found'])} 条\n")
            f.write(f"错误: {len(self.results['errors'])} 条\n\n")
            
            if self.results['updated']:
                f.write("=" * 80 + "\n")
                f.write("需要更新的文献\n")
                f.write("=" * 80 + "\n\n")
                
                for item in self.results['updated']:
                    f.write(f"文献键值: {item['key']}\n")
                    f.write(f"标题: {self.clean_title(item['original'].get('title', ''))}\n")
                    f.write(f"数据来源: {item.get('platform', 'unknown').upper()}\n\n")
                    f.write("字段差异:\n")
                    for field, diff in item['differences'].items():
                        f.write(f"  {field}:\n")
                        f.write(f"    原值: {diff['original']}\n")
                        f.write(f"    新值: {diff['updated']}\n")
                    f.write("\n" + "-" * 80 + "\n\n")
            
            if self.results['not_found']:
                f.write("=" * 80 + "\n")
                f.write("未找到的文献（可能需要手动检查）\n")
                f.write("=" * 80 + "\n\n")
                
                for item in self.results['not_found']:
                    f.write(f"文献键值: {item['key']}\n")
                    f.write(f"标题: {self.clean_title(item['title'])}\n")
                    f.write(f"类型: {item['entry'].get('ENTRYTYPE', 'unknown')}\n")
                    f.write("\n" + "-" * 80 + "\n\n")
            
            if self.results['errors']:
                f.write("=" * 80 + "\n")
                f.write("处理错误的文献\n")
                f.write("=" * 80 + "\n\n")
                
                for item in self.results['errors']:
                    f.write(f"文献键值: {item['key']}\n")
                    f.write(f"标题: {self.clean_title(item.get('title', ''))}\n")
                    f.write(f"错误信息: {item.get('error', 'unknown error')}\n")
                    f.write("\n" + "-" * 80 + "\n\n")
        
        print(f"\n{self.lang.get_text('report_generated', file=report_file)}")
        return report_file
    
    def generate_updated_bib(self):
        timestamp_format = self.config.get('output_settings', {}).get('timestamp_format', '%Y%m%d_%H%M%S')
        timestamp = datetime.now().strftime(timestamp_format)
        backup_file = f'sample_backup_{timestamp}.bib'
        updated_file = f'sample_updated_{timestamp}.bib'
        wrong_file = f'sample_wrong_{timestamp}.bib'
        
        with open(self.bib_file, 'r', encoding=self.file_encoding) as f:
            original_content = f.read()
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"\n{self.lang.get_text('backup_generated', file=backup_file)}")
        
        updated_db = BibDatabase()
        wrong_db = BibDatabase()
        
        # 清理更新条目中的 None 值
        for item in self.results['updated']:
            cleaned_entry = self.clean_entry_for_writing(item['updated'])
            updated_db.entries.append(cleaned_entry)
        
        # 清理未找到条目中的 None 值
        for item in self.results['not_found']:
            cleaned_entry = self.clean_entry_for_writing(item['entry'])
            wrong_db.entries.append(cleaned_entry)
        
        # 清理错误条目中的 None 值
        for item in self.results['errors']:
            cleaned_entry = self.clean_entry_for_writing(item['entry'])
            wrong_db.entries.append(cleaned_entry)
        
        writer = BibTexWriter()
        writer.indent = '  '
        writer.order_entries_by = None
        writer.common_strings = True
        
        field_order = [
            'title', 'author', 'editor', 'journal', 'booktitle',
            'volume', 'number', 'pages', 'year', 'month',
            'publisher', 'organization', 'institution', 'address',
            'edition', 'chapter', 'series', 'note', 'doi', 'url',
            'eprint', 'archiveprefix', 'primaryclass', 'pmid', 'howpublished', 'school'
        ]
        writer.COMMON_STRINGS = []
        writer.display_order = field_order
        
        if self.results['updated']:
            with open(updated_file, 'w', encoding='utf-8') as bibfile:
                content = writer.write(updated_db)
                content = content.replace('arXiv (Cornell University)', 'arXiv')
                bibfile.write(content)
            print(f"{self.lang.get_text('updated_generated', file=updated_file)}")
            print(f"      {self.lang.get_text('updated_count', count=len(self.results['updated']))}")
        else:
            print(self.lang.get_text('no_update_skip'))
        
        if self.results['not_found'] or self.results['errors']:
            with open(wrong_file, 'w', encoding='utf-8') as bibfile:
                content = writer.write(wrong_db)
                content = content.replace('arXiv (Cornell University)', 'arXiv')
                bibfile.write(content)
            print(f"{self.lang.get_text('wrong_generated', file=wrong_file)}")
            print(f"      {self.lang.get_text('wrong_count', not_found=len(self.results['not_found']), errors=len(self.results['errors']))}")
        else:
            print(self.lang.get_text('no_wrong_skip'))
        
        return updated_file if self.results['updated'] else None, wrong_file if (self.results['not_found'] or self.results['errors']) else None
    
    def run(self):
        print("=" * 80)
        print(self.lang.get_text('tool_title'))
        print(self.lang.get_text('enabled_platforms', count=len(self.enabled_platforms), platforms=', '.join([p.upper() for p in self.enabled_platforms])))
        print("=" * 80)
        
        self.load_bib_file()
        
        print(f"\n{self.lang.get_text('start_verification')}")
        self.check_all_entries()
        
        print("\n" + "=" * 80)
        print(self.lang.get_text('verification_complete'))
        print("=" * 80)
        print(f"\n{self.lang.get_text('total_checked', count=len(self.db.entries))}")
        print(f"{self.lang.get_text('verified_passed', count=len(self.results['verified']))}")
        print(f"{self.lang.get_text('need_update_count', count=len(self.results['updated']))}")
        print(f"{self.lang.get_text('not_found_count', count=len(self.results['not_found']))}")
        if self.results['errors']:
            print(f"{self.lang.get_text('errors_count', count=len(self.results['errors']))}")
        
        if self.results['verified']:
            platforms = {}
            for item in self.results['verified']:
                platform = item.get('platform', 'unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
            print(f"\n{self.lang.get_text('verified_sources')}")
            for platform, count in platforms.items():
                print(f"  {platform.upper()}: {count} 条")
        
        if self.results['updated']:
            platforms = {}
            for item in self.results['updated']:
                platform = item.get('platform', 'unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
            print(f"\n{self.lang.get_text('update_sources')}")
            for platform, count in platforms.items():
                print(f"  {platform.upper()}: {count} 条")
        
        print("\n" + "=" * 80)
        print(self.lang.get_text('generating_files'))
        print("=" * 80)
        
        self.generate_report()
        self.generate_updated_bib()


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    checker = BibTeXChecker(config_file)
    checker.run()
