# Olostep

Olostep is web data infrastructure for AI. It provides live web search, scraping and crawling API to extract and structure data.

This plugin brings Olostep to Dify agents, chatflows and workflows. Scrape any page into clean markdown, search the web, get answers with sources, and map, crawl or batch scrape websites.

Source repository: https://github.com/olostep-api/olostep-dify-plugin

## Tools

| Tool | What it does |
|---|---|
| Scrape URL | Scrape a page and return clean markdown (JavaScript rendering included) |
| Search Web | Search the live web and return titles, URLs and descriptions |
| Answer Question | Answer a question from the live web, with source URLs |
| Map Website | List the URLs on a website |
| Crawl Website | Crawl a website and return the markdown of each page |
| Batch Scrape | Scrape up to 100 URLs in one batch and return the markdown of each page |
| Get Results | Get the pages of a crawl or batch that was still running |

## Setup

1. Sign up at [olostep.com](https://www.olostep.com) and copy your API key from the [Olostep dashboard](https://www.olostep.com/dashboard).
2. In Dify, go to **Plugins**, find **Olostep** in the Marketplace and click **Install**.
3. Open the plugin, click **Authorize** and paste your API key.

## Usage

- **Agents:** add the Olostep tools to an agent app. The agent picks the tool it needs, for example Search Web to find pages and Scrape URL to read them.
- **Workflows and chatflows:** add a tool node, choose an Olostep tool and map its inputs. Every tool returns JSON for later nodes and readable text for LLM nodes.

Example: a research workflow that runs **Search Web** for a topic, then **Batch Scrape** on the result URLs, then summarizes the pages with an LLM node.

### Crawls and batches

Crawl Website and Batch Scrape wait for results for up to 2 minutes by default (configurable up to 4 minutes). If the job is still running, the tool returns its `id` with `status` set to `in_progress`. Pass that id to **Get Results** later to get the pages.

## Connection requirements

The plugin connects only to the Olostep API at `https://api.olostep.com` over HTTPS. Your Dify instance needs outbound network access to that host. Rate limits and server errors are retried automatically.

## Credentials

The plugin needs an Olostep API key. It is stored by Dify as a secret and sent to the Olostep API in the `Authorization` header.

## Support

- Documentation: https://docs.olostep.com
- Email: info@olostep.com
- Privacy: see [PRIVACY.md](PRIVACY.md) and https://www.olostep.com/privacy-policy
