"""
Standalone test script for the web search + LLM pipeline
"""
import asyncio
import aiohttp
import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WebSearchService:
    def __init__(self):
        self.search_url = "https://api.bing.microsoft.com/v7.0/search"
        self.api_key = os.getenv("BING_SEARCH_API_KEY")
        
    async def search(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Perform web search using Bing Search API"""
        if not self.api_key:
            raise ValueError("BING_SEARCH_API_KEY not configured")
            
        headers = {
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        params = {
            'q': query,
            'count': count,
            'responseFilter': 'webPages',
            'textFormat': 'HTML',
            'safeSearch': 'Moderate'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.search_url,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_search_results(data)
                    else:
                        print(f"Search API error: {response.status}")
                        return []
        except Exception as e:
            print(f"Web search failed: {e}")
            return []
    
    def _format_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format search results for LLM consumption"""
        results = []
        
        if 'webPages' in data and 'value' in data['webPages']:
            for item in data['webPages']['value']:
                result = {
                    'title': item.get('name', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('snippet', ''),
                    'date_published': item.get('datePublished', ''),
                    'display_url': item.get('displayUrl', '')
                }
                results.append(result)
        
        return results
    
    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """Format search results as context for LLM"""
        if not results:
            return "No search results found."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_result = f"""
                Result {i}:
                Title: {result['title']}
                URL: {result['url']}
                Snippet: {result['snippet']}
                Date: {result.get('date_published', 'N/A')}
                ---
                """
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)

class OpenAIClient:
    def __init__(self):
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_KEY")

        if self.azure_endpoint and self.azure_api_key:
            print("Using Azure OpenAI")
            self.client = OpenAI(
                api_key=self.azure_api_key,
                base_url=f"{self.azure_endpoint}/openai/deployments/gpt-4o/",
                default_headers={"api-key": self.azure_api_key}
            )
            self.model = "gpt-4o"
        else:
            raise ValueError("No OpenAI API key configured")
    
    def generate_response(self, system_prompt: str, user_message: str) -> str:
        """Generate response using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {e}"

class WebSearchPipeline:
    def __init__(self):
        self.search_service = WebSearchService()
        self.openai_client = OpenAIClient()
        
        self.system_prompt = """You are a helpful AI assistant with access to real-time web search capabilities. 

            When responding to user queries:
            1. Use the provided search results to give accurate, up-to-date information
            2. Always cite your sources by mentioning the title and URL of relevant results
            3. If search results are insufficient or contradictory, mention this limitation
            4. Synthesize information from multiple sources when appropriate
            5. Be critical of information quality and mention if sources seem unreliable
            6. If no relevant search results are found, acknowledge this and provide general knowledge if applicable

            Search Results Context:
            {search_results}

            User Query: {user_query}

            Provide a comprehensive response based on the search results above, making sure to cite specific sources and be transparent about the limitations of the information."""
    
    async def process_query(self, query: str, search_count: int = 10) -> Dict[str, Any]:
        """Process a query through the complete pipeline"""
        print(f"Searching for: {query}")
        
        # Perform web search
        search_results = await self.search_service.search(query, count=search_count)
        print(f"Found {len(search_results)} search results")
        
        # Format results for LLM
        search_context = self.search_service.format_results_for_llm(search_results)
        
        # Create system prompt with search context
        formatted_prompt = self.system_prompt.format(
            search_results=search_context,
            user_query=query
        )
        
        # Generate LLM response
        print("Generating AI response...")
        ai_response = self.openai_client.generate_response(formatted_prompt, query)
        
        return {
            "query": query,
            "search_results": search_results,
            "ai_response": ai_response,
            "search_count": len(search_results)
        }

async def main():
    """Test the web search pipeline"""
    print("Starting Web Search Pipeline Test\n")
    
    # Check environment variables
    required_vars = ["BING_SEARCH_API_KEY"]
    openai_key = os.getenv("AZURE_OPENAI_KEY")
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    if not openai_key:
        print(f"Missing OpenAI configuration. Need either Azure OpenAI or OpenAI API key")
        return
    
    print("Environment variables configured\n")
    
    # Initialize pipeline
    try:
        pipeline = WebSearchPipeline()
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")
        return
    
    # Test queries
    test_queries = [
        "latest AI developments 2024",
        "current weather in New York",
        "recent SpaceX launches",
        "Python programming best practices"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*50}")
        print(f"Test {i}: {query}")
        print('='*50)
        
        try:
            result = await pipeline.process_query(query, search_count=5)
            
            print(f"\nSearch Results ({result['search_count']} found):")
            print("-" * 30)
            for j, search_result in enumerate(result['search_results'][:3], 1):
                print(f"{j}. {search_result['title']}")
                print(f"   URL: {search_result['url']}")
                print(f"   Snippet: {search_result['snippet'][:100]}...")
                print()
            
            print("AI Response:")
            print("-" * 30)
            print(result['ai_response'])
            
        except Exception as e:
            print(f"Error processing query: {e}")
        
        print("\n" + "="*50)
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main())